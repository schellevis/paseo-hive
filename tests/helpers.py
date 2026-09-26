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

# Subject is fixed: a municipal permit queue. No names or real organisations.

SOLVE_R1 = """PROBLEM: A municipal permit queue takes eight weeks, and solved means a routine permit is decided within two weeks.
DIAGNOSIS: One shared review desk holds every permit [assumption].
APPROACH: Decide routine permits on a short checklist away from that desk.
STEPS:
S1 Sort each permit into routine or exception on arrival.
S2 Decide routine permits from a fixed checklist within ten days.
S3 Send exceptions to the shared desk with a written reason.
RISKS:
R1 The checklist misses a safety issue.
TEST: Median routine permits are decided within two weeks for a month.
RESULT: none
CRUX: Whether most permits are routine.
QUESTION FOR THE USER: What share of permits are routine?
"""

SOLVE_R1_RESULT = """PROBLEM: A municipal permit queue takes eight weeks, and solved means a routine permit is decided within two weeks.
DIAGNOSIS: Applicants arrive missing the same three facts [assumption].
APPROACH: Publish the checklist and refuse incomplete applications the same day.
STEPS:
S1 Publish the checklist where people apply.
S2 Return incomplete applications the day they arrive.
S3 Decide complete routine permits within ten days.
RISKS:
R1 Applicants cannot find the checklist.
R2 Staff still review incomplete files out of habit.
TEST: A month of routine permits shows a median under two weeks.
RESULT: Nine of ten routine permits in a two-week sample were decided within ten days, counted from the work file.
CRUX: Whether applicants will use the checklist.
QUESTION FOR THE USER: none
"""

SOLVE_FOLLOWUP = """HOLES:
A-S2: The ten-day checklist still needs the same scarce reviewer.
B-PLAN: Publishing the checklist does not add anyone to decide permits.
BORROWS:
A-DIAGNOSIS: Keep the shared-desk cause and staff a second clerk for routine permits.
CHANGED STEPS:
S1 [replaces: A-S2] Decide routine permits on a checklist staffed by a second clerk.
S2 [replaces: new] Publish the checklist so applicants arrive with complete files.
PLAN: changed — Staff a second clerk for routine permits and publish the checklist.
BECAUSE: B-S2 showed the checklist still depended on one reviewer.
RESULT CHECKS: none
CRUX: Whether a second clerk is available.
STATUS: continue
QUESTION FOR THE USER: none
"""

SOLVE_FOLLOWUP_UNCHANGED = """HOLES:
A-PLAN2: Funding for the second clerk is not settled.
BORROWS:
none
CHANGED STEPS:
none
PLAN: unchanged — The second clerk and the published checklist still stand.
BECAUSE: A-PLAN2 does not show the checklist itself is wrong.
RESULT CHECKS: none
CRUX: Whether a second clerk can be funded.
STATUS: nothing new
QUESTION FOR THE USER: none
"""

SOLVE_FOLLOWUP_REVISE = """HOLES:
A-PLAN2: The routine step still needs weekday cover.
BORROWS:
none
CHANGED STEPS:
S1 [replaces: A-S4] Staff the checklist with two clerks on weekdays.
PLAN: changed
BECAUSE: A-PLAN2 showed the second clerk belongs in the routine step.
RESULT CHECKS: none
CRUX: Whether weekday staffing is enough.
STATUS: continue
QUESTION FOR THE USER: none
"""

SOLVE_FOLLOWUP_B = """HOLES:
B-S2: Same-day returns still leave the decision to one desk.
BORROWS:
A-PLAN: Take the split between routine permits and exceptions.
CHANGED STEPS:
S1 [replaces: B-S2] Return incomplete files and book a routine slot the same day.
S2 [replaces: new] Count median decision time every Friday.
PLAN: changed — Book a routine slot when an incomplete file is returned.
BECAUSE: A-S2 showed one desk cannot clear the routine pile.
RESULT CHECKS: none
CRUX: Whether a same-day slot is real capacity.
STATUS: continue
QUESTION FOR THE USER: none
"""
