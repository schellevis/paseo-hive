# Goals

**ID scheme.** Seats number their own items without a prefix (`C1`, `I1`, `N1`, `Q1`). The moderator stores every item in the ledger with the seat letter as prefix (`A-C1`, `B-I2`, `C-N1`, `A-Q3`), and those prefixed IDs are what targets, attacks, builds, challenges, and checkpoints cite. Exceptions: decide options are shared and numbered once by the moderator from the subject (`O1`, `O2`, …); an option a seat adds is written `NEW <option>` and the moderator gives it the next `O` number in the ledger. Explore: the moderator merges the seats' maps into areas numbered `M1`, `M2`, … with the contributing seat IDs listed per area; follow-up targets and challenges cite `M` IDs, and additions a seat makes in a follow-up are numbered by the seat (`Q7`) and prefixed in the ledger (`B-Q7`). User items are `U1`, `U2`, … .

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

## Universal checks

Before presenting a checkpoint, run the goal's minimum-engagement check above plus two universal checks: every crux is resolved or has a "what would settle it"; every user answer and user item (`U…`) was addressed by at least one seat. If a check fails and the round cap allows another round, run one **targeted** extra round: only the seats and items that failed (for example "Seat B: nobody attacked A-C2; attack it"). If the cap is reached, present the checkpoint marked `Debate incomplete: <which check failed>`.
