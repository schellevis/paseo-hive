#!/usr/bin/env python3
"""paseo-hive helper: ingest, check, ledger, leaks and lint for hive sessions.

Standard library only, Python 3.10+. Nothing here talks to the network. The
only external commands are `paseo logs` (ingest --agent) and `git ls-files`
(leaks --repo). Exit codes: 0 ok or note only, 1 action needed, 2 usage or
I/O error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FORMATS_PATH = SKILL_DIR / "references" / "formats.json"

EXIT_OK, EXIT_ACTION, EXIT_ERROR = 0, 1, 2
SEVERITY = {"ok": 0, "note": 1, "trim": 2, "blind?": 3, "invalid": 4}
MODES = ("quick", "standard", "deep")


class HiveError(Exception):
    """A usage or I/O problem. main() turns it into exit code 2."""


def read_text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HiveError(f"{path}: not UTF-8 text") from None
    except OSError as e:
        raise HiveError(f"{path}: {e.strerror or e}") from e


def load_json(path):
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise HiveError(f"{path}: invalid JSON: {e}") from e


_FIELD_KINDS = ("line", "block", "refs", "choice", "items")


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def validate_formats(data, path) -> None:
    """Raise HiveError naming the offending entry if formats.json has the wrong shape."""
    def bad(where, what):
        raise HiveError(f"{path}: {where}: {what}")
    if not isinstance(data, dict) or not isinstance(data.get("formats"), dict):
        bad("top level", "expected an object with a 'formats' object")
    limits = data.get("word_limits")
    if not isinstance(limits, dict) or not all(
            isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in limits.values()):
        bad("word_limits", "expected an object of positive integers")
    tol = data.get("tolerance", 0.25)
    if not isinstance(tol, (int, float)) or isinstance(tol, bool) or tol < 0:
        bad("tolerance", "expected a non-negative number")
    for fid, fmt in data["formats"].items():
        if not isinstance(fmt, dict):
            bad(f"format {fid}", "expected an object")
        if fmt.get("kind") == "fairness":
            continue
        limit = fmt.get("limit")
        if not (limit is None or limit == "mode" or limit in limits
                or (isinstance(limit, int) and not isinstance(limit, bool) and limit > 0)):
            bad(f"format {fid}", f"limit {limit!r} is not 'mode', a word_limits key, or a positive integer")
        fields = fmt.get("fields")
        if not isinstance(fields, list) or not fields:
            bad(f"format {fid}", "'fields' must be a non-empty list")
        for f in fields:
            if not isinstance(f, dict) or not isinstance(f.get("name"), str) or f.get("kind") not in _FIELD_KINDS:
                bad(f"format {fid}", f"field {f!r} needs a string name and a kind in {_FIELD_KINDS}")
            where = f"format {fid} field {f['name']}"
            if f["kind"] == "choice" and not (_is_str_list(f.get("values")) and f["values"]):
                bad(where, "choice fields need a non-empty 'values' list of strings")
            if f["kind"] == "items":
                if not (isinstance(f.get("id"), str) and re.fullmatch(r"[A-Z]", f["id"])):
                    bad(where, "items fields need an 'id' of one capital letter")
                lo, hi = f.get("min", 0), f.get("max")
                if not isinstance(lo, int) or not (hi is None or isinstance(hi, int)):
                    bad(where, "'min' and 'max' must be integers ('max' may be null)")
                tags = f.get("tags", [])
                if not isinstance(tags, list) or not all(
                        isinstance(t, dict) and (t.get("key") is None or isinstance(t.get("key"), str))
                        and (t.get("refs") is True or _is_str_list(t.get("values"))) for t in tags):
                    bad(where, "'tags' must be objects with an optional string key and either refs: true or a values list")


def validate_seats(seats, path) -> None:
    """Raise HiveError if seats.json has the wrong shape; the name fields must be strings."""
    if not (isinstance(seats, dict) and isinstance(seats.get("seats"), list)):
        raise HiveError(f"{path}: expected an object with a 'seats' list")
    for n, seat in enumerate(seats["seats"]):
        if not isinstance(seat, dict):
            raise HiveError(f"{path}: seats[{n}]: expected an object")
        for key in ("model", "label", "provider", "role"):
            if key in seat and seat[key] is not None and not isinstance(seat[key], str):
                raise HiveError(f"{path}: seats[{n}].{key}: expected a string")


def load_formats(path=FORMATS_PATH) -> dict:
    data = load_json(path)
    validate_formats(data, path)
    return data


def get_format(formats: dict, fmt_id: str) -> dict:
    try:
        return formats["formats"][fmt_id]
    except KeyError:
        raise HiveError(f"unknown format: {fmt_id}") from None


def field_names(fmt: dict) -> list[str]:
    return [f["name"] for f in fmt.get("fields", [])]


# --- prompts.md <-> formats.json -------------------------------------------

_SECTION_KIND = {"Round-1 formats": "r1", "Follow-up formats": "followup"}
_TEMPLATE_FIELD = re.compile(r"^([A-Z][A-Z ]*[A-Z]):")


def prompt_formats(text: str) -> dict[str, list[str]]:
    """Field names, in order, of every answer-format block in prompts.md."""
    out: dict[str, list[str]] = {}
    section = goal = block_id = None
    in_block = False
    names: list[str] = []
    for line in text.splitlines():
        if not in_block and line.startswith("## "):
            section, goal = line[3:].strip(), None
            continue
        if not in_block:
            m = re.fullmatch(r"(critique|brainstorm|decide|explore):", line.strip())
            if m:
                goal = m.group(1)
            elif line.startswith("```"):
                in_block, names = True, []
                if section in _SECTION_KIND and goal:
                    block_id = f"{goal}-{_SECTION_KIND[section]}"
                elif section == "Brainstorm select prompt":
                    block_id = "select"
                else:
                    block_id = None
            continue
        if line.startswith("```"):
            if block_id:
                out[block_id] = names
            in_block, block_id, goal = False, None, None
            continue
        m = _TEMPLATE_FIELD.match(line)
        if m and (not names or names[-1] != m.group(1)):
            names.append(m.group(1))
    return out


def format_drift(prompts_text: str, formats: dict) -> list[str]:
    """Differences between prompts.md format blocks and formats.json."""
    found = prompt_formats(prompts_text)
    fails = []
    for fid, fmt in formats["formats"].items():
        if fmt.get("kind") == "fairness":
            continue
        want, got = field_names(fmt), found.get(fid)
        if got is None:
            fails.append(f"{fid}: no format block in prompts.md")
        elif got != want:
            fails.append(f"{fid}: prompts.md has {got}, formats.json has {want}")
    for fid in found:
        if fid not in formats["formats"]:
            fails.append(f"{fid}: in prompts.md but not in formats.json")
    return fails


# --- answers -----------------------------------------------------------------

_LEAD = re.compile(r"^[\s#*>\-]+")
PLACEHOLDER = re.compile(r"<[a-z][^>]*>")
MARKER = re.compile(r"^\[(User|Thought)\]")
ID_RE = re.compile(r"\b(?:[A-Z]-(?:[A-Z]+\d+|WILDCARD|NEW\d*)|[OMU]\d+)\b")
M_LINE = re.compile(r"^\s*[-*]?\s*(M\d+)\b", re.MULTILINE)
MOD_HEADER = "## Moderator"
_TAG = re.compile(r"^\s*\[([^\]]*)\]")
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
_BLIND_START = re.compile(r"(^|:\s*)if this\b", re.IGNORECASE)
BLIND_PHRASES = ("i cannot see", "i can't see", "cannot access", "can't access",
                 "unable to read", "not able to read", "no files were provided",
                 "files were not provided", "file was not provided")


def normalize(line: str) -> str:
    """Strip markdown decoration for matching; never used for saved text."""
    return _LEAD.sub("", line).replace("**", "").strip()


def field_at(line: str, names: list[str]) -> tuple[str, str] | None:
    """(field name, rest of line) if the line starts one of the fields."""
    n = normalize(line)
    for name in sorted(names, key=len, reverse=True):
        if n.startswith(name + ":"):
            return name, n[len(name) + 1:].strip()
    return None


def parse_answer(text: str, fmt: dict) -> dict:
    """Split an answer into fields; consecutive repeats of a field merge."""
    names = field_names(fmt)
    fields: dict[str, dict] = {}
    order: list[str] = []
    dupes: list[str] = []
    current = None
    for line in text.splitlines():
        hit = field_at(line, names)
        if hit:
            name, rest = hit
            if name != current and name in fields:
                dupes.append(name)
            if name not in fields:
                fields[name] = {"first": rest, "lines": []}
                order.append(name)
            if rest:
                fields[name]["lines"].append(rest)
            current = name
        elif current is not None and line.strip():
            fields[current]["lines"].append(line.strip())
    return {"fields": fields, "order": order, "dupes": dupes}


def _item(local: str, n, rest: str, spec: dict, problems: list) -> dict:
    raw_tags = []
    while (m := _TAG.match(rest)):
        raw_tags.append(m.group(1).strip())
        rest = rest[m.end():]
    want = spec.get("tags", [])
    if len(raw_tags) < len(want):
        problems.append(("invalid", f"{local}: expected {len(want)} tags, found {len(raw_tags)}"))
    tags, builds = [], []
    for tag, w in zip(raw_tags, want):
        key, value = w.get("key"), tag
        if key:
            k, _, value = tag.partition(":")
            if k.strip().lower() != key:
                problems.append(("invalid", f"{local}: expected [{key}: …], found [{tag}]"))
                continue
            value = value.strip()
        if w.get("refs"):
            builds = [x.strip() for x in value.split(",") if x.strip()]
        elif value.lower() not in w["values"]:
            problems.append(("invalid", f"{local}: [{tag}] not in {'|'.join(w['values'])}"))
        tags.append([key, value])
    return {"local": local, "n": n, "tags": tags, "text": rest.strip(),
            "builds_on": builds, "new": False}


def parse_items(lines: list[str], spec: dict) -> tuple[list[dict], list[tuple[str, str]]]:
    """Parse numbered items (C1, I1, N1, O1, Q1) and NEW options of one field."""
    prefix = spec["id"]
    item_re = re.compile(rf"^{prefix}(\d+)\b\s*(.*)$")
    items: list[dict] = []
    problems: list[tuple[str, str]] = []
    for raw in lines:
        line = normalize(raw)
        m = item_re.match(line)
        if m:
            items.append(_item(f"{prefix}{m.group(1)}", int(m.group(1)), m.group(2), spec, problems))
        elif spec.get("new") and re.match(r"^NEW\b", line):
            item = _item("NEW", None, line[3:].strip(), spec, problems)
            item["new"] = True
            items.append(item)
        elif items:
            items[-1]["text"] = (items[-1]["text"] + " " + line).strip()
    name, lo, hi = spec["name"], spec.get("min", 0), spec.get("max")
    if len(items) < lo or (hi is not None and len(items) > hi):
        expected = f"{lo}-{hi}" if hi is not None else f"at least {lo}"
        problems.append(("invalid", f"{name}: {len(items)} items, expected {expected}"))
    nums = [i["n"] for i in items if i["n"] is not None]
    if spec.get("sequential", True) and nums != list(range(1, len(nums) + 1)):
        problems.append(("invalid", f"{name}: numbered {nums}, expected 1..{len(nums)}"))
    if sum(1 for i in items if i["new"]) > 1:
        problems.append(("invalid", f"{name}: more than one NEW option"))
    limit = spec.get("sentences")
    if limit:
        for i in items:
            k = len(_SENTENCE_END.findall(i["text"]))
            if k > limit:
                problems.append(("note", f"{i['local']} has {k} sentences"))
    return items, problems


def word_limit(fmt: dict, formats: dict, mode: str):
    limit = fmt.get("limit")
    if limit is None:
        return None
    if isinstance(limit, int):
        return limit
    key = mode if limit == "mode" else limit
    try:
        return formats["word_limits"][key]
    except KeyError:
        raise HiveError(f"unknown word limit: {key}") from None


def ref_known(ref: str, known: set[str]) -> bool:
    if ref in known:
        return True
    m = re.fullmatch(r"[A-Z]-(O\d+)", ref)
    return bool(m and m.group(1) in known)


def moderator_section(text: str) -> str:
    """The hand-written part of a ledger file, from '## Moderator' to the end."""
    m = re.search(rf"^{re.escape(MOD_HEADER)}\b", text, re.MULTILINE)
    return text[m.start():] if m else ""


def known_ids(session: Path) -> set[str]:
    """Every ID a seat may cite: ledger items, user items, M areas, all legs."""
    ids: set[str] = set()
    for leg in sorted(Path(session).glob("leg-*")):
        items = leg / "items.json"
        if items.exists():
            ids |= {i["id"] for i in load_json(items)}
        users = leg / "user-items.json"
        if users.exists():
            ids |= set(load_json(users))
        for md in leg.glob("ledger-*.md"):
            ids |= set(M_LINE.findall(moderator_section(read_text(md))))
    return ids


def _result(problems, words, limit, refs, unknown) -> dict:
    status = max((s for s, _ in problems), key=SEVERITY.__getitem__, default="ok")
    head = status
    if words is not None and limit is not None:
        head += f" {words}/{limit}"
        if words > limit:
            head += f" (+{round(100 * (words - limit) / limit)}%)"
    details = [(s, m) for s, m in problems if m != "words"]
    line = head + "".join(f"; {s}: {m}" for s, m in details)
    return {"status": status, "line": line, "words": words, "limit": limit,
            "problems": [{"status": s, "message": m} for s, m in details],
            "refs": sorted(set(refs)), "unknown": unknown}


def check_answer(text: str, fmt_id: str, formats: dict, mode: str = "standard",
                 known: set[str] | None = None) -> dict:
    """Check one seat answer against its format; see the spec for the rules."""
    fmt = get_format(formats, fmt_id)
    problems: list[tuple[str, str]] = []
    refs: list[str] = []
    if fmt.get("kind") == "fairness":
        first = next((l.strip() for l in text.splitlines() if l.strip()), "")
        if not re.fullmatch(r"(?i)fair|unfair: .+", first):
            problems.append(("invalid", "expected 'fair' or 'unfair: …'"))
        return _result(problems, None, None, refs, [])
    parsed = parse_answer(text, fmt)
    names = field_names(fmt)
    for name in names:
        if name not in parsed["fields"]:
            problems.append(("invalid", f"missing {name}"))
    if parsed["order"] != [n for n in names if n in parsed["fields"]]:
        problems.append(("invalid", "fields out of order: " + ", ".join(parsed["order"])))
    for name in parsed["dupes"]:
        problems.append(("invalid", f"{name} appears twice"))
    for spec in fmt["fields"]:
        field = parsed["fields"].get(spec["name"])
        if field is None:
            continue
        kind = spec["kind"]
        if kind in ("line", "block", "refs") and not field["lines"]:
            problems.append(("invalid", f"{spec['name']} is empty"))
        if kind == "choice":
            value = field["first"].lower()
            if not any(re.match(rf"{re.escape(v)}\b", value) for v in spec["values"]):
                problems.append(("invalid", f"{spec['name']}: expected {' | '.join(spec['values'])}"))
        if kind == "items":
            items, item_problems = parse_items(field["lines"], spec)
            problems += item_problems
            for item in items:
                refs += ID_RE.findall(", ".join(item["builds_on"]))
        if kind == "refs" or spec.get("refs"):
            refs += ID_RE.findall(" ".join(field["lines"]))
    unknown: list[str] = []
    if known is not None:
        unknown = sorted({r for r in refs if not ref_known(r, known)})
        problems += [("invalid", f"unknown id {r}") for r in unknown]
    first_line = next((normalize(l) for l in text.splitlines() if l.strip()), "")
    lowered = text.lower()
    if _BLIND_START.search(first_line) or any(p in lowered for p in BLIND_PHRASES):
        problems.append(("blind?", "answer suggests the seat could not read the material"))
    limit = word_limit(fmt, formats, mode)
    words = len(text.split())
    if limit is not None and words > limit:
        over = "trim" if words > limit * (1 + formats.get("tolerance", 0.25)) else "note"
        problems.append((over, "words"))
    return _result(problems, words, limit, refs, unknown)


def emit(args, result: dict) -> None:
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result["line"])


def exit_for(status: str) -> int:
    return EXIT_OK if SEVERITY[status] <= SEVERITY["note"] else EXIT_ACTION


def _setup_check(p) -> None:
    p.add_argument("file")
    p.add_argument("--format", required=True)
    p.add_argument("--mode", default="standard", choices=MODES)
    p.add_argument("--session", help="session directory; enables reference checks")


def cmd_check(args) -> int:
    formats = load_formats()
    known = known_ids(Path(args.session)) if args.session else None
    res = check_answer(read_text(args.file), args.format, formats, args.mode, known)
    res["file"] = args.file
    emit(args, res)
    return exit_for(res["status"])


# --- CLI ----------------------------------------------------------------------

COMMANDS: dict = {
    "check": (_setup_check, cmd_check),
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="hive.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    for name, (setup, _run) in COMMANDS.items():
        sp = sub.add_parser(name)
        sp.add_argument("--json", action="store_true", help="print a JSON result")
        setup(sp)
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return EXIT_OK if e.code in (0, None) else EXIT_ERROR
    if not args.command:
        parser.print_usage(sys.stderr)
        return EXIT_ERROR
    try:
        return COMMANDS[args.command][1](args)
    except HiveError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as e:  # e.g. a failed write; the path is in the message
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
