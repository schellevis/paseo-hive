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


# --- CLI ----------------------------------------------------------------------

COMMANDS: dict = {}


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
