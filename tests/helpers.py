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


DEBUG_R1 = """SYMPTOM: Choir attendance drops by a third every spring; working means attendance stays near winter levels.
KNOWN: Attendance falls from March [source: sign-in sheets]; members say they like rehearsals [source: survey]; rehearsal time moved to 19:00 last year [assumption].
HYPOTHESES:
H1 [possible] Spring evening sports clash with rehearsal night. It explains the March start.
H2 [likely] Daylight saving makes the 19:00 start feel rushed after work. It explains why members still like rehearsals.
LEADING: H2, because the drop starts the week the clocks change.
TESTS:
T1 Compare sign-ins for the two weeks around the clock change. A step at that week supports H2 over H1.
RESULT: none
CRUX: Whether the drop starts exactly at the clock change.
QUESTION FOR THE USER: Did the rehearsal start time change in the last two years?
"""

DEBUG_R1_RESULT = """SYMPTOM: Attendance drops every spring; working means a stable turnout all year.
KNOWN: Sign-in sheets for three years exist [source: sign-in sheets].
HYPOTHESES:
H1 [likely] The spring concert repertoire is too hard, so members stay away. It explains the timing.
H2 [unlikely] The hall heating is switched off in March. Members would then mention the cold.
LEADING: H1, because the drop follows the repertoire handout.
TESTS:
T1 Count sign-ins in the week before and after the repertoire handout. A step there supports H1.
RESULT: T1: sign-ins fell from 42 to 30 in the handout week, counted on the sheets in the work file.
CRUX: Whether the handout week and the clock change coincide.
QUESTION FOR THE USER: none
"""

DEBUG_FOLLOWUP = """RULES OUT:
A-H1: B-RESULT — the step falls in the handout week, which no sports fixture change explains.
B-H2: [source: hall bookings] heating ran all spring — the cold cannot explain the drop.
SUPPORTS:
B-H1: B-RESULT shows the step in the handout week.
NEW HYPOTHESES:
H1 [likely] The handout and the clock change fall in the same week, and members blame the new pieces. It explains both signals.
TESTS:
T1 Ask five members who left which change made them stop. Naming the pieces supports the new hypothesis.
LEADING: changed — H1
BECAUSE: B-RESULT showed a step in the handout week, which my clock-change account did not predict.
RESULT: none
RESULT CHECKS: B-RESULT: reproduced — the same counts appear on the scanned sheets.
CRUX: Whether members name the pieces or the dark evenings.
STATUS: continue
QUESTION FOR THE USER: none
"""

DEBUG_FOLLOWUP_B = """RULES OUT:
none
SUPPORTS:
none
NEW HYPOTHESES:
none
TESTS:
none
LEADING: unchanged — B-H1
BECAUSE: A-H2 claims the clock change, but B-RESULT shows the step in the handout week.
RESULT: A-T1: the clock-change week shows no step of its own, checked on the sheets.
RESULT CHECKS: none
CRUX: Whether the handout week is the clock-change week every year.
STATUS: nothing new
QUESTION FOR THE USER: none
"""

DEBUG_R1_MAX = """SYMPTOM: Loaves from the shop's deck oven come out pale and dense on about one morning in four; working means every batch browns evenly.
KNOWN: Pale batches cluster on cold mornings [source: baking log]; the oven reaches its set temperature before loading [source: oven display]; the flour supplier changed in autumn [assumption].
HYPOTHESES:
H1 [likely] The oven display reads the air temperature while the stone floor is still cold on winter mornings. Cold stone steals heat from the first loaves of the day and leaves their crust pale.
H2 [possible] The new flour absorbs less water than the old one at the usual hydration for this recipe. A wetter dough would then be slack and would spread out dense on the peel.
H3 [unlikely] The proofing cabinet door seal has worn out and lets the humidity drop overnight in the shop. Dry dough skins would then block the oven spring and keep the crumb tight and dense.
LEADING: H1, because pale batches follow the cold mornings in the baking log.
TESTS:
T1 Preheat the oven for an extra forty minutes on three cold mornings and bake the usual recipe. Even browning on all three mornings would support H1 over both H2 and H3 clearly.
T2 Bake one batch from the old flour and one from the new flour on the same warm morning. A visible difference between the two loaves of bread would then support H2 over H1.
RESULT: T1: after the longer preheat, two of three cold mornings gave evenly browned loaves, recorded in the baking log with oven photos.
CRUX: Whether the third cold morning failed because of stone temperature or because of the flour.
QUESTION FOR THE USER: Did the pale batches begin in the same week that the new flour arrived?
"""

DEBUG_FOLLOWUP_MAX = """RULES OUT:
A-H2: B-RESULT — the longer preheat fixed two cold mornings with unchanged flour, so a flour-only cause no longer fits.
B-H2: [source: hall bookings] the heating ran all spring, so cold hall air cannot explain a drop that follows the handout.
SUPPORTS:
B-H1: B-RESULT shows a clear step of twelve sign-ins in the handout week, exactly where this hypothesis predicts it.
NEW HYPOTHESES:
H1 [likely] Members may blame the new pieces, because the handout and the clock change fall in the same week. Separating the two causes needs one year in which the two dates differ by a week.
TESTS:
T1 Compare the handout dates and the clock-change dates for the last three years of sign-in sheets. Years with different weeks would show which of the two changes the drop really follows.
T2 Ask five members who left which change made them stop attending the rehearsals every week. Answers that name the new pieces would support the new hypothesis over the clock change.
LEADING: changed — H1
BECAUSE: B-RESULT showed a step in the handout week, which my clock-change account did not predict at all.
RESULT: T1: the handout and the clock change fell in the same week in all three years, counted from the dated sheets.
RESULT CHECKS: B-RESULT: reproduced — the same counts appear when the sheets are totalled again from the scans.
CRUX: Whether any year exists in which the handout and the clock change fall in different weeks.
STATUS: continue
QUESTION FOR THE USER: Were the repertoire handouts ever sent on a different week than the clock change?
"""
