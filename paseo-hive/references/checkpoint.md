# Checkpoint report

Write `checkpoint-<n>.md` to the session directory and show it to the user in their conversational language, under about 600 words; keep tables terse and point to the ledger files for detail. No manufactured consensus: if the panel split, the checkpoint shows the split.

## Common frame

```markdown
# Hive checkpoint <n>: <subject in one line>

Goal: <goal> · Mode: <mode> · Seats: <n> · Leg: <n> · Rounds this leg: <n>
<"Limited diversity: …" if applicable> <"Debate incomplete: <failed check>" if applicable> <"Skipped seats: …" if any>

## In one paragraph
<where the panel stands, including what stays open; no recommendation unless the panel converged on one with arguments>

<goal-specific sections>

## What changed this leg
<position/ranking changes with the argument that caused them; flag changes without a new argument>

## Questions for you
<open questions only the user can answer>

## What next?
Reply with any of: new information · a focus ("dig into X") · where you disagree · a goal switch ("critique idea B-I2", "decide between the top two") · add or replace a seat · done.
```

Below the checkpoint, **only in the message to the user and never in `checkpoint-<n>.md`**, the moderator appends the panel mapping:

```markdown
<details><summary>Panel</summary>

| seat | role or lens | provider/model |
|---|---|---|
</details>
```

Rule: `checkpoint-<n>.md` never contains role or model names, so seats (including new seats reading it through the catch-up prompt) stay anonymous. The seat-to-role/model mapping lives only in `brief.md` and in the Panel block of the user message.

## Goal-specific sections

- critique: `## Agreement`, `## Live disagreements` (each with "Settled by:"), `## Most fragile assumption`, `## What would settle it`.
- brainstorm: `## Shortlist` (table: idea id, name, from seats, novelty, effort, why it made the list), `## Wildcards`, `## Dropped` (one line each), `## Directions to pick from` (2–3 directions the user can choose for the next leg).
- decide: `## Criteria` (with any user weights), `## Decision matrix` (options × criteria, consensus rating, or a split shown as the seats' ratings separated by slashes, e.g. `++/+/--` for seats A/B/C), `## Ranking` (per seat; show the split), `## What would flip it`.
- explore: `## Map` (area ID `M…`, area, known, unknown), `## Biggest unknowns`, `## Best next questions` (ranked, with how to answer), `## Where the maps disagree`.
