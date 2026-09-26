# Goals

**ID scheme.** Seats number their own items without a prefix (`C1`, `I1`, `N1`, `Q1`). The moderator stores every item in the ledger with the seat letter as prefix (`A-C1`, `B-I2`, `C-N1`, `A-Q3`), and those prefixed IDs are what targets, attacks, builds, challenges, and checkpoints cite. Exceptions: decide options are shared and numbered once by the moderator from the subject (`O1`, `O2`, …); an option a seat adds is written `NEW <option>` and the moderator gives it the next `O` number in the ledger. Explore: the moderator merges the seats' maps into areas numbered `M1`, `M2`, … with the contributing seat IDs listed per area; follow-up targets and challenges cite `M` IDs, and additions a seat makes in a follow-up are numbered by the seat (`Q7`) and prefixed in the ledger (`B-Q7`). User items are `U1`, `U2`, … . Solve: seats number their steps `S1`… and risks `R1`…, prefixed in the ledger (`A-S1`, `B-R2`); a seat's diagnosis, approach, and result are stored as `A-DIAGNOSIS`, `A-PLAN`, `A-RESULT` (a follow-up that answers `PLAN: changed` adds a new entry with a suffix, `A-PLAN2`); steps a seat changes in a follow-up are numbered by the seat and renumbered in the ledger like other items.

**Ledger files.** `hive.py ledger` writes the Items part of `leg-<n>/ledger-<r>.md`: prefixed IDs, `O` numbers for `NEW` options, and dangling-reference warnings. Ledger IDs are unique per session: when a seat reuses a local number already taken in an earlier round or leg (builds restart at `N1` each round), the ledger gives it the next free number for that seat and letter (`WILDCARD` and `NEW` get a suffix: `B-NEW2`), and seats cite the ledger ID. Rebuilding a round keeps the IDs and `O` numbers it had before. The moderator writes the Moderator part (clusters, cruxes, `M` areas, skips, saturation notes); regenerating the Items part keeps it as it is.

## critique

### Opening round
Round-1 critique format (prompts.md): POSITION, CLAIMS, WEAKEST ASSUMPTION, CRUX, QUESTION FOR THE USER.

### Follow-up rounds
Seats attack assigned claims, concede where they are right, and state whether their position changed or is unchanged with the argument that moved them.

### Ledger
Numbered claims `A-C1`… , conflicts marked, 1–3 cruxes, user items `U1`….

### Saturation signals
No position change, no new crux, and no new claims in the last round.

### Minimum engagement
Every seat's main claim (its first claim, or the one its POSITION rests on) was attacked at least once.

### Typical user questions
Facts only the user knows; load-bearing assumptions in the framing.

## brainstorm

### Opening round
Each seat gets a different **lens** (panel.md). It lists the two most obvious ideas under `OBVIOUS` (these do not count), then 4–6 ideas tagged novelty/effort, plus one `WILDCARD`.

### Follow-up rounds
"Yes, and" only: build on, combine, mutate, or transplant other seats' ideas; no criticism. Each build names the idea IDs (for example `A-I1`) it builds on. At most one unrelated new idea per seat per round. Before a checkpoint, send the **select prompt** (prompts.md) to every seat at the lowest thinking level; this is the only place criticism and ranking happen.

### Ledger
Idea list with IDs `A-I1`, builds `B-N2 (builds on A-I1)`, clusters of near-duplicates, wildcards; user preferences as `U1`….

### Saturation signals
New ideas in the last round are mostly variants of existing clusters (fewer than one genuinely new idea per seat), or the user picked a direction and the shortlist did not change.

### Minimum engagement
At least one build on another seat's idea; every lens produced at least one idea outside its OBVIOUS list.

### Typical user questions
Constraints (budget, time, audience); taste ("which of these pulls you, and why?"); what has already been tried.

## decide

### Opening round
Seats propose 3–5 criteria (most important first), rate every option per criterion (`++ + 0 - --`), may add at most one option of their own marked `NEW` (renumbered `O…` by the moderator), give a ranking, and state what would flip their top choice.

### Follow-up rounds
Challenge other seats' ratings and rankings, concede where they are right, and state whether the ranking changed or is unchanged and why.

### Ledger
Merged criteria list; matrix of options `O1`… × criteria with each seat's rating; each seat's ranking; flip conditions; user weights as `U1`….

### Saturation signals
Every seat's ranking unchanged over the last round.

### Minimum engagement
Every option was rated by at least two seats; every seat's top choice was challenged at least once.

### Typical user questions
Which criterion weighs most; hard constraints that rule options out.

## explore

### Opening round
Seats map 4–6 open questions or areas (`Q1`…), what is known (tagged `[source: …]` or `[assumption]`), the biggest unknowns, and the best next question.

### Follow-up rounds
Find gaps, errors, and overstatements in others' maps; add questions; update the best next question.

### Ledger
Merged map with areas `M1`…, known/unknown per area, and the seat item IDs (for example `A-Q2`, `C-Q1`) covered by each area.

### Saturation signals
The last round added no new area or unknown to the merged map.

### Minimum engagement
Every area in the merged map was covered by at least two seats.

### Typical user questions
What the user already knows; what they want to be able to decide afterwards.

## solve

### Opening round
Each seat gets a different **angle** (panel.md). It restates the problem and what counts as solved, diagnoses the cause, and works out one approach: the core idea, 3–6 steps, 1–3 risks, the test that shows it worked, and its crux. With grounding on and a checkable problem, it also carries the solution out (see Grounded solve below) and reports the outcome in `RESULT`; otherwise `RESULT: none`.

### Follow-up rounds
Seats find holes in their targets (a step that fails, a missing cause, an overlooked risk), borrow what is better than their own and say where it goes, list the steps they changed, and state whether their plan changed or is unchanged and why. Approaches stay distinct unless an argument moved the seat; borrowing parts is not converging. In grounded solve, each seat also reproduces or refutes one other seat's `RESULT`.

### Ledger
Per seat: `A-DIAGNOSIS`, `A-PLAN`, steps `A-S1`…, risks `A-R1`…, and `A-RESULT` when present; holes and borrows cite these IDs; diagnosis agreements and splits and any combined plan the seats built themselves are noted in the Moderator part; user constraints as `U1`….

### Saturation signals
No plan changed, no new hole found, and no diagnosis moved in the last round.

### Minimum engagement
Every plan was attacked at least once on its crux (a hole citing one of its steps or its crux); every diagnosis difference was addressed by at least one seat; in grounded solve, every `RESULT` was checked by at least one other seat.

### Typical user questions
Constraints (time, budget, what may not change); what has already been tried; how the user would recognise "solved".

**Grounded solve.** Only when grounding is on (by `--grounded` or the mode) and the moderator judges the problem checkable within the work-file boundary; the panel announcement says whether this leg is grounded solve or plan-only. Each round, the moderator names one work file per seat, `leg-<n>/work/<LETTER>-r<r>.md` (at most 150 lines); it is the only file the seat may write, and the seat may run only commands without side effects. If checking would need more (installs, builds, test suites that create files), the leg is plan-only and every seat answers `RESULT: none`. `RESULT` states the outcome and how it was checked; the working stays in the file. A seat assigned another seat's `RESULT` reads that seat's latest work file (inlined for seats that cannot read session files) and reports `reproduced`, `refuted`, or `not checked` with how, writing any working of its own to its current work file. Run `hive.py leaks --session` before sharing work files, like every other seat-visible file.

**Current plan.** A seat's current plan is its latest `PLAN` entry in the ledger (`A-PLAN`, then `A-PLAN2`, … — a new entry only when the seat answers `PLAN: changed`) plus its current steps: start from the opening steps in order; then, round by round, each `CHANGED STEPS` item `[replaces: A-S2]` takes the place of `A-S2` (which must be one of that seat's current steps) under its own newly allocated ledger ID, and each `[replaces: new]` item is appended under its ledger ID. Example: `A-S1, A-S2, A-S3`; round 2 `S1 [replaces: A-S2]` (ledger `A-S4`) and `S2 [replaces: new]` (ledger `A-S5`) give `A-S1, A-S4, A-S3, A-S5`; round 3 `S1 [replaces: A-S4]` (ledger `A-S6`) gives `A-S1, A-S6, A-S3, A-S5`. The moderator lists each seat's current plan ID and current step IDs in the Moderator part of the ledger after every round; targets, holes, and the checkpoint cite current IDs, and superseded items stay in the ledger as history.

## Change log

After every follow-up round, the moderator starts a `Round <r>:` entry in `leg-<n>/changes.md` (`Round <r>: no changes` if nobody moved or held; `hive.py gate` checks for it) and adds one line for each change of POSITION, RANKING, BEST NEXT QUESTION, or PLAN: round, seat, from → to, moved by (the prefixed item ID and its seat, or a `U…` item), kind, and the reason in one sentence taken from the seat's `BECAUSE`. Kinds:

- `argument`: another seat's reasoning or new consideration.
- `correction`: another seat showed that the changing seat's own earlier output contained a factual or logical error.
- `user`: a user answer or `U…` item.
- `no new argument`: `BECAUSE` names no item, or the named item does not say what the seat claims. The moderator checks the cited item; this kind is a warning sign of drift toward the majority and is flagged in the checkpoint.

Also log **holds**: a seat whose top choice, position, or plan was challenged in the round and did not move, with the strongest challenge it resisted and why it says that challenge failed. Concessions that change no position or ranking stay in the ledger only. A challenge made in the same round the leg would end has not yet reached the challenged seat, so the seat's silence on it is not a hold: if the cap allows, give that seat one targeted round to answer it before the checkpoint.

## Load-bearing assumptions

After every round, the moderator lists in the Moderator part of the ledger each claim that carries a seat's position, top choice, plan, or a rating that decides a ranking, and that is tagged `[assumption]` or untagged while it could be checked (for example "this supplier is usually late", "most users would choose that"). With grounding on, each such claim becomes a target for its own seat in the next round: check it, or keep it explicitly as an assumption and weigh it that way. Several seats repeating the same unchecked claim is not evidence for it; say so in the ledger. With grounding off, the checkpoint lists these claims under what would settle the crux.

## Universal checks

Before presenting a checkpoint, run the goal's minimum-engagement check above plus three universal checks: every crux is resolved or has a "what would settle it"; every user answer and user item (`U…`) was addressed by at least one seat; every load-bearing assumption (above) was checked or is marked as an assumption in the checkpoint. If a check fails and the round cap allows another round, run one **targeted** extra round: only the seats and items that failed (for example "Seat B: nobody attacked A-C2; attack it"). If the cap is reached, present the checkpoint marked `Debate incomplete: <which check failed>`.
