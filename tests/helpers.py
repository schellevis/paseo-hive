"""Shared test helpers: import hive.py, run its CLI, hold synthetic answers."""

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "paseo-hive" / "scripts"))

import hive  # noqa: E402


def run(argv):
    """Run hive.main(argv); return (exit code, captured stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = hive.main(argv)
    return code, out.getvalue()
