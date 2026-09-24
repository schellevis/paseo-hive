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


# Synthetic seat answers. Generic subjects across domains; no real names.

CRITIQUE_R1 = """POSITION: A nightly batch export is safer than streaming for this invoice feed.
CLAIMS:
C1 [likely] Batch runs are easier to replay after a failure. The export already has idempotent keys.
C2 [certain] Streaming adds a broker the team does not run today.
C3 [guess] Most customers read the export the next morning.
WEAKEST ASSUMPTION: That nobody needs invoices within the hour.
CRUX: Whether any contract promises same-hour invoices.
QUESTION FOR THE USER: Does any contract promise same-hour invoices?
"""

CRITIQUE_FOLLOWUP = """ATTACKS:
B-C2: A managed broker removes most of the operating burden.
CONCESSIONS:
B-C1: Replays are simpler in batch.
POSITION: changed — Batch first, streaming only for the two contracts that need it.
BECAUSE: B-C1 showed the replay cost I had ignored.
CRUX: How many contracts need same-hour invoices.
STATUS: continue
QUESTION FOR THE USER: none
"""

BRAINSTORM_R1 = """OBVIOUS: Longer opening hours; more events.
IDEAS:
I1 [novelty: mid] [effort: low] Homework corner: Volunteers staff a corner two evenings a week.
I2 [novelty: high] [effort: mid] Repair night: Neighbours fix bikes and lamps while children read.
I3 [novelty: low] [effort: low] Quiet hour: One silent hour for people who work from home.
I4 [novelty: mid] [effort: mid] Late loans: Items borrowed after six are due a day later.
WILDCARD: Let teenagers run the library one evening a month.
QUESTION FOR THE USER: Is there budget for evening staff?
"""

BRAINSTORM_FOLLOWUP = """BUILDS:
N1 [builds on: B-I1] [novelty: mid] [effort: low] Homework corner with loans: The corner lends laptops for the evening.
N2 [builds on: B-I1, B-I2] [novelty: high] [effort: mid] Fix-and-learn night: Children do homework while volunteers repair bikes.
NEW: none
STATUS: continue
QUESTION FOR THE USER: none
"""

DECIDE_R1 = """CRITERIA: monthly cost, flexibility, long-term wealth
OPTIONS:
O1 Rent: monthly cost +, flexibility ++, long-term wealth - — Easy to move for a new job.
O2 Buy: monthly cost -, flexibility --, long-term wealth + — Builds equity after about seven years.
NEW Rent and invest the difference: monthly cost +, flexibility ++, long-term wealth + — Keeps options open.
RANKING: NEW > O1 > O2
WHAT WOULD FLIP IT: A job that is certain to stay in this city for ten years.
QUESTION FOR THE USER: How likely is a move within five years?
"""

SELECT = """SHORTLIST: B-I2 — Draws adults and children at once.
SHORTLIST: A-I1 — Cheap and uses existing volunteers.
SHORTLIST: A-I3 — Almost free to try.

WILDCARD KEEP: A-WILDCARD — Risky but could change habits.

DROP: A-I4 — Late loans shift the problem to staff.
"""
