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


# --- ingest -------------------------------------------------------------------

_LIST_ITEM = re.compile(r"^\s*([-*]|\d+[.)])\s")


def _is_answer_start(region: list[str], i: int, first: str) -> bool:
    line = region[i]
    if MARKER.match(line) or PLACEHOLDER.search(line):
        return False
    hit = field_at(line, [first])
    if not hit:
        return False
    if not hit[1]:  # "BUILDS:" alone: a template if the next line has placeholders
        nxt = next((l for l in region[i + 1:] if l.strip()), "")
        if PLACEHOLDER.search(nxt):
            return False
    return True


def _answer_from(region: list[str], start: int, fmt: dict) -> str:
    names = field_names(fmt)
    last, last_kind = names[-1], fmt["fields"][-1]["kind"]
    out: list[str] = []
    in_last = False
    for j in range(start, len(region)):
        line = region[j]
        if MARKER.match(line):
            break
        hit = field_at(line, names)
        if in_last:
            if last_kind in ("line", "choice"):
                if not (hit and hit[0] == last):
                    break
            elif not line.strip():
                nxt = next((l for l in region[j + 1:] if l.strip()), None)
                if nxt is None or MARKER.match(nxt) or not (
                        field_at(nxt, [last]) or _LIST_ITEM.match(nxt)):
                    break
        if hit and hit[0] == last:
            in_last = True
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def extract_answer(log_text: str, fmt: dict) -> str | None:
    """The seat's answer from `paseo logs --filter text` output, or None."""
    lines = log_text.splitlines()
    users = [i for i, l in enumerate(lines) if l.startswith("[User]")]
    region = lines[users[-1] + 1:] if users else lines
    names = field_names(fmt)
    starts = [i for i in range(len(region)) if _is_answer_start(region, i, names[0])]
    if not starts:
        return None
    # The answer follows the echoed template: ignore starts before its last line.
    floor = max((i for i, l in enumerate(region) if PLACEHOLDER.search(l) and i < starts[-1]),
                default=-1)
    starts = [s for s in starts if s > floor]
    best = None
    for i in reversed(starts):
        while (i - 1 > floor and field_at(region[i - 1], names[:1])
               and not PLACEHOLDER.search(region[i - 1])):
            i -= 1
        answer = _answer_from(region, i, fmt)
        if best is None:
            best = answer
        if all(n in parse_answer(answer, fmt)["fields"] for n in names):
            return answer
    return best


def seat_path(session: Path, leg: int, rnd: str, seat: str) -> Path:
    sub = "select" if rnd == "select" else f"round-{rnd}"
    return Path(session) / f"leg-{leg}" / sub / f"{seat}.md"


def atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def keep_previous(path: Path) -> Path:
    n = 1
    while (old := path.with_name(f"{path.stem}.v{n}{path.suffix}")).exists():
        n += 1
    shutil.copy2(path, old)
    return old


def read_log(args) -> str:
    if args.log:
        return read_text(args.log)
    paseo = shutil.which("paseo")
    if not paseo:
        raise HiveError("paseo CLI not found; use --log")
    proc = subprocess.run([paseo, "logs", args.agent, "--filter", "text"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise HiveError(f"paseo logs failed: {proc.stderr.strip()}")
    return proc.stdout


def _setup_ingest(p) -> None:
    p.add_argument("--session", required=True)
    p.add_argument("--seat", required=True)
    p.add_argument("--leg", type=int, required=True)
    p.add_argument("--round", required=True, help="round number or 'select'")
    p.add_argument("--format", required=True)
    p.add_argument("--mode", default="standard", choices=MODES)
    p.add_argument("--force", action="store_true", help="replace; keep the old file as <SEAT>.vN.md")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--agent", help="agent ID; runs `paseo logs <id> --filter text`")
    src.add_argument("--log", help="file with `paseo logs --filter text` output")


def cmd_ingest(args) -> int:
    if not re.fullmatch(r"[A-Z]", args.seat):
        raise HiveError("--seat must be one capital letter")
    if not (args.round == "select" or args.round.isdigit()):
        raise HiveError("--round must be a number or 'select'")
    formats = load_formats()
    fmt = get_format(formats, args.format)
    if fmt.get("kind") == "fairness":
        raise HiveError("fairness replies are checked with `check --format fairness`, not ingested")
    answer = extract_answer(read_log(args), fmt)
    if answer is None:
        emit(args, {"status": "invalid", "line": "invalid: answer not found"})
        return EXIT_ACTION
    session = Path(args.session)
    target = seat_path(session, args.leg, args.round, args.seat)
    if target.exists():
        if not args.force:
            raise HiveError(f"{target} exists; use --force to replace it")
        keep_previous(target)
    atomic_write(target, answer)
    known = known_ids(session) if any(session.glob("leg-*/items.json")) else None
    res = check_answer(answer, args.format, formats, args.mode, known)
    res["file"] = str(target)
    emit(args, res)
    return exit_for(res["status"])


# --- ledger -------------------------------------------------------------------

CHOICE_FIELDS = ("POSITION", "RANKING", "BEST NEXT QUESTION")


def _renumber(base: str, taken: set[str]) -> str:
    """`base` if free, else the next free number for the same seat and item letter."""
    if base not in taken:
        return base
    stem = re.fullmatch(r"([A-Z]-[A-Z]+)\d+", base).group(1)
    used = [int(t[len(stem):]) for t in taken if t.startswith(stem) and t[len(stem):].isdigit()]
    return f"{stem}{max(used) + 1}"


def _suffix(base: str, taken: set[str]) -> str:
    """`base`, `base2`, `base3`, ...: the first one not taken (WILDCARD and NEW items)."""
    cand, n = base, 2
    while cand in taken:
        cand, n = f"{base}{n}", n + 1
    return cand


def _entries(answers: dict[str, str], fmt: dict) -> list[tuple[str, dict, dict]]:
    """(seat, field spec, item) for every ledger-producing item, in seat-letter order."""
    out = []
    for seat in sorted(answers):
        fields = parse_answer(answers[seat], fmt)["fields"]
        for spec in fmt["fields"]:
            field = fields.get(spec["name"])
            if field is None:
                continue
            if spec["kind"] == "items":
                items, _ = parse_items(field["lines"], spec)
                out += [(seat, spec, it) for it in items]
            elif spec.get("ledger_id"):
                text = " ".join(field["lines"]).strip()
                if text and text.strip('". ').lower() != "none":
                    out.append((seat, spec, {"local": spec["ledger_id"], "n": None, "tags": [],
                                             "text": text, "builds_on": [], "new": False}))
    return out


def build_items(answers: dict[str, str], rnd: str, fmt: dict, existing: list[dict],
                elsewhere: list[dict] = (), previous: list[dict] = ()) -> list[dict]:
    """Ledger records for one round: session-unique IDs, O numbers for NEW options.

    `existing` holds this leg's records of other rounds, `elsewhere` the records of other
    legs, and `previous` this round's records from an earlier run. Previous IDs are reserved
    and reused first; only then are fresh IDs allocated (spec C1, C3). Ratings cite an
    option; they never allocate or reserve its number.
    """
    others = [*existing, *elsewhere]
    taken = {i["id"] for i in others if i["kind"] != "rating"}
    entries = _entries(answers, fmt)

    def key(seat, spec, it):
        if spec.get("id") == "O":
            return (seat, "NEW") if it["new"] else None  # ratings cite the shared option
        return (seat, it["local"])

    prev = {(i["seat"], "NEW" if i["kind"] == "option" else i.get("local")): i["id"]
            for i in previous if i["kind"] != "rating"}
    ids: dict[int, str] = {}
    for n, (seat, spec, it) in enumerate(entries):  # pass 1: shared ratings, reused IDs
        k = key(seat, spec, it)
        if k is None:
            ids[n] = it["local"]
        elif k in prev and prev[k] not in taken:
            ids[n] = prev[k]
            taken.add(prev[k])
    o_numbers = {int(x[1:]) for x in taken | {i["id"] for i in others} if re.fullmatch(r"O\d+", x)}
    o_numbers |= {it["n"] for _, sp, it in entries if sp.get("id") == "O" and it["n"] is not None}
    for n, (seat, spec, it) in enumerate(entries):  # pass 2: fresh IDs
        if n in ids:
            continue
        if spec.get("id") == "O":
            o_numbers.add(max(o_numbers, default=0) + 1)
            ids[n] = f"O{max(o_numbers)}"
        elif spec.get("ledger_id"):
            ids[n] = _suffix(f"{seat}-{spec['ledger_id']}", taken)
        else:
            ids[n] = _renumber(f"{seat}-{it['local']}", taken)
        taken.add(ids[n])
    out = []
    for n, (seat, spec, it) in enumerate(entries):
        if spec.get("id") == "O":
            kind = "option" if it["new"] else "rating"
        elif spec.get("ledger_id"):
            kind = spec["ledger_id"].lower()
        else:
            kind = spec["name"].lower()
        out.append({"id": ids[n], "local": it["local"], "seat": seat, "round": rnd, "kind": kind,
                    "tags": it["tags"], "text": it["text"], "builds_on": it["builds_on"]})
    return out


def session_dangling(session: Path, formats: dict, mode: str) -> list[str]:
    """References to unknown IDs in every ledgered round of the session (spec C3, C4)."""
    known = known_ids(session)
    out = []
    for leg in sorted(Path(session).glob("leg-*")):
        rounds = leg / "rounds.json"
        if not rounds.exists():
            continue
        for rnd, fmt_id in load_json(rounds).items():
            rnd_dir = seat_path(session, int(leg.name[4:]), rnd, "A").parent
            for path in sorted(p for p in rnd_dir.glob("*.md") if re.fullmatch(r"[A-Z]\.md", p.name)):
                res = check_answer(read_text(path), fmt_id, formats, mode, known)
                out += [f"{leg.name} round {rnd}: {path.stem} cites {r}" for r in res["unknown"]]
    return out


def render_ledger(leg: int, rnd: str, items: list[dict], moderator: str) -> str:
    lines = [f"# Ledger, leg {leg}, round {rnd}", "",
             "## Items (generated by hive.py; do not edit)", ""]
    for seat in sorted({i["seat"] for i in items}):
        lines.append(f"### Seat {seat}")
        for i in (x for x in items if x["seat"] == seat):
            tags = " ".join(f"[{k}: {v}]" if k else f"[{v}]" for k, v in i["tags"])
            label = f"{i['id']} (NEW from {seat})" if i["kind"] == "option" else i["id"]
            text = i["text"] if len(i["text"]) <= 120 else i["text"][:117] + "..."
            lines.append(" ".join(p for p in (label, tags, text) if p) + f" (round {i['round']})")
        lines.append("")
    return "\n".join(lines) + "\n" + (moderator or f"{MOD_HEADER}\n\n")


def change_lines(answers: dict[str, str], fmt: dict) -> list[str]:
    """Per seat: the position/ranking choice and the IDs its BECAUSE cites."""
    kinds = {f["name"]: f["kind"] for f in fmt["fields"]}
    choice = next((n for n in CHOICE_FIELDS if kinds.get(n) == "choice"), None)
    if not choice or "BECAUSE" not in kinds:
        return []
    out = []
    for seat in sorted(answers):
        fields = parse_answer(answers[seat], fmt)["fields"]
        value = fields.get(choice, {}).get("first", "").split()
        because = sorted(set(ID_RE.findall(" ".join(fields.get("BECAUSE", {}).get("lines", [])))))
        out.append(f"{seat}: {choice} {value[0] if value else '?'}; "
                   f"BECAUSE {', '.join(because) or 'no id'}")
    return out


def _setup_ledger(p) -> None:
    p.add_argument("--session", required=True)
    p.add_argument("--leg", type=int, required=True)
    p.add_argument("--round", required=True, help="round number or 'select'")
    p.add_argument("--format", required=True)
    p.add_argument("--mode", default="standard", choices=MODES)


def cmd_ledger(args) -> int:
    formats = load_formats()
    fmt = get_format(formats, args.format)
    session = Path(args.session)
    leg_dir = session / f"leg-{args.leg}"
    rnd_dir = seat_path(session, args.leg, args.round, "A").parent
    files = sorted(p for p in rnd_dir.glob("*.md") if re.fullmatch(r"[A-Z]\.md", p.name))
    if not files:
        raise HiveError(f"no seat files in {rnd_dir}")
    answers = {}
    for path in files:
        text = read_text(path)
        res = check_answer(text, args.format, formats, args.mode)
        if res["status"] == "invalid":
            emit(args, {"status": "invalid", "line": f"invalid: {path}: {res['line']}"})
            return EXIT_ACTION
        answers[path.stem] = text
    items_path = leg_dir / "items.json"
    items = load_json(items_path) if items_path.exists() else []
    previous = [i for i in items if i["round"] == args.round]
    items = [i for i in items if i["round"] != args.round]
    elsewhere = [i for leg in sorted(session.glob("leg-*"))
                 if leg != leg_dir and (leg / "items.json").exists()
                 for i in load_json(leg / "items.json")]
    new_items = build_items(answers, args.round, fmt, items, elsewhere, previous)
    items += new_items
    atomic_write(items_path, json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    ledger_path = leg_dir / f"ledger-{args.round}.md"
    old = read_text(ledger_path) if ledger_path.exists() else ""
    atomic_write(ledger_path, render_ledger(args.leg, args.round, items, moderator_section(old)))
    rounds_path = leg_dir / "rounds.json"
    rounds = load_json(rounds_path) if rounds_path.exists() else {}
    rounds[args.round] = args.format
    atomic_write(rounds_path, json.dumps(rounds, indent=1) + "\n")
    dangling = session_dangling(session, formats, args.mode)
    changes = change_lines(answers, fmt)
    lines = [f"ledger: {len(new_items)} items this round, {len(items)} in leg {args.leg} -> {ledger_path}"]
    lines += [f"dangling: {d}" for d in dangling] + changes
    emit(args, {"status": "invalid" if dangling else "ok", "line": "\n".join(lines),
                "items": new_items, "dangling": dangling, "changes": changes,
                "file": str(ledger_path)})
    return EXIT_ACTION if dangling else EXIT_OK


# --- leaks --------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")
LOCAL_PATH_RE = re.compile(r"/(?:home|Users|workspace)/")
SEAT_VISIBLE = ("checkpoint-*.md", "leg-*/ledger-*.md", "leg-*/round-*/*.md", "leg-*/select/*.md")
REPO_SKIP = {"LICENSE", "AGENTS.md"}


def session_patterns(seats: dict) -> list[tuple[str, re.Pattern]]:
    """Model, label and provider names (any case), role names (exact case)."""
    pats, seen = [], set()
    for seat in seats.get("seats", []):
        for key in ("model", "label", "provider"):
            value = seat.get(key)
            if value and value.lower() not in seen:
                seen.add(value.lower())
                pats.append((value, re.compile(rf"(?<![\w-]){re.escape(value)}(?![\w-])", re.IGNORECASE)))
        role = seat.get("role")
        if role and role not in seen:
            seen.add(role)
            pats.append((role, re.compile(rf"(?<!\w){re.escape(role)}(?!\w)")))
    return pats


def _scan(path: Path, pats, label: str, skip_binary: bool = False) -> list[str]:
    """Hits in one file. Unreadable text is an error, never a clean result."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        if skip_binary:
            return []
        raise HiveError(f"{label}: not UTF-8 text; cannot scan it") from None
    except OSError as e:
        raise HiveError(f"{label}: {e.strerror or e}") from e
    return [f"{label}:{n}: {name}"
            for n, line in enumerate(text.splitlines(), 1)
            for name, pat in pats if pat.search(line)]


def leaks_session(session: Path, files: list[Path] | None = None) -> list[str]:
    session = Path(session)
    seats = load_json(session / "seats.json")
    validate_seats(seats, session / "seats.json")
    pats = session_patterns(seats)
    if not files:
        files = sorted({p for g in SEAT_VISIBLE for p in session.glob(g)})
    hits = []
    for f in files:
        label = str(f.relative_to(session)) if f.is_relative_to(session) else str(f)
        hits += _scan(f, pats, label)
    return hits


def leaks_repo(root: Path) -> list[str]:
    root = Path(root)
    try:
        proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                              capture_output=True, check=False)
    except FileNotFoundError:
        raise HiveError("git not found") from None
    if proc.returncode != 0:
        raise HiveError(f"{root}: not a git checkout")
    pats = [("email", EMAIL_RE), ("local path", LOCAL_PATH_RE)]
    extra = root / ".opsec-extra"
    if extra.exists():
        for term in read_text(extra).splitlines():
            term = term.strip()
            if term and not term.startswith("#"):
                pats.append((term, re.compile(re.escape(term), re.IGNORECASE)))
    hits = []
    for rel in proc.stdout.decode("utf-8").split("\0"):
        if rel and rel not in REPO_SKIP:
            hits += _scan(root / rel, pats, rel, skip_binary=True)
    return hits


def _setup_leaks(p) -> None:
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--session", help="session directory with seats.json")
    mode.add_argument("--repo", nargs="?", const=".", metavar="ROOT",
                      help="scan tracked files of a git checkout")
    p.add_argument("files", nargs="*", help="session mode: files to scan instead of the defaults")


def cmd_leaks(args) -> int:
    if args.repo:
        hits = leaks_repo(Path(args.repo))
    else:
        hits = leaks_session(Path(args.session), [Path(f) for f in args.files])
    emit(args, {"status": "invalid" if hits else "ok",
                "line": "\n".join(hits) if hits else "ok: no leaks", "hits": hits})
    return EXIT_ACTION if hits else EXIT_OK


# --- lint ---------------------------------------------------------------------

HEADINGS = ("Opening round", "Follow-up rounds", "Ledger", "Saturation signals",
            "Minimum engagement", "Typical user questions")
VERBATIM = (
    "Preserve diversity: disagreement in critique and decide, divergence in brainstorm "
    "and explore. Never converge prematurely.",
    "Stop when another round cannot settle anything.",
    "Skill files and panel prompts are in English.",
)


def lint(root: Path) -> list[str]:
    """The AGENTS.md "Checks before committing", as a list of failures."""
    root = Path(root)
    skill_dir = root / "paseo-hive"
    skill = read_text(skill_dir / "SKILL.md")
    prompts = read_text(skill_dir / "references" / "prompts.md")
    goals = read_text(skill_dir / "references" / "goals.md")
    agents = read_text(root / "AGENTS.md")
    formats = load_formats(skill_dir / "references" / "formats.json")
    fails = []
    n = len(skill.splitlines())
    if n > 200:
        fails.append(f"SKILL.md has {n} lines (max 200)")
    for link in re.findall(r"\]\((references/[^)#]+)", skill):
        if not (skill_dir / link).exists():
            fails.append(f"SKILL.md links to missing {link}")
    status = sum(1 for l in prompts.splitlines() if l.startswith("STATUS: continue | nothing new"))
    if status != 4:
        fails.append(f"prompts.md has {status} STATUS lines (want 4)")
    for h in HEADINGS:
        count = sum(1 for l in goals.splitlines() if l.startswith(f"### {h}"))
        if count != 4:
            fails.append(f"goals.md has {count} '### {h}' headings (want 4)")
    fails += format_drift(prompts, formats)
    rule = next((l for l in agents.splitlines() if "Keep field names and IDs identical" in l), "")
    all_fields = {f["name"] for fm in formats["formats"].values() for f in fm.get("fields", [])}
    for name in re.findall(r"`([^`{}]+)`", rule):
        if name not in prompts:
            fails.append(f"field {name} missing from prompts.md")
        if name not in all_fields:
            fails.append(f"field {name} missing from formats.json")
    for sentence in VERBATIM:
        if sentence not in skill:
            fails.append(f"SKILL.md lost the verbatim sentence: {sentence}")
    return fails


def _setup_lint(p) -> None:
    p.add_argument("root", nargs="?", default=str(SKILL_DIR.parent), help="repository root")


def cmd_lint(args) -> int:
    fails = lint(Path(args.root))
    emit(args, {"status": "invalid" if fails else "ok",
                "line": "\n".join(fails) if fails else "ok: lint passed", "failures": fails})
    return EXIT_ACTION if fails else EXIT_OK


# --- CLI ----------------------------------------------------------------------

COMMANDS: dict = {
    "check": (_setup_check, cmd_check),
    "ingest": (_setup_ingest, cmd_ingest),
    "ledger": (_setup_ledger, cmd_ledger),
    "leaks": (_setup_leaks, cmd_leaks),
    "lint": (_setup_lint, cmd_lint),
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
