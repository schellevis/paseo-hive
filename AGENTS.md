# AGENTS.md

Guidance for AI agents and humans working on this repository.

## What this is

`paseo-hive` is a [Paseo](https://paseo.sh) skill. A moderator agent runs a small panel (3–5 seats) of agents on different model families toward one of five goals: `critique`, `brainstorm`, `decide`, `explore`, `solve`. Seats work independently first, then react to each other anonymously. The moderator asks the user counter-questions only when an answer can move a crux, and pauses at checkpoints where user feedback starts the next leg with the same live panel.

The deliverable is mostly instruction text that other agents follow, so precision and internal consistency are the quality bar. A small standard-library Python tool (`paseo-hive/scripts/hive.py`, Python 3.10+) does the moderator's mechanical steps and checks formats; its tests live in `tests/`.

## Layout

```text
paseo-hive/SKILL.md                  entry point, always loaded (keep ≤ 200 lines)
paseo-hive/references/goals.md       ID scheme; per-goal rounds, ledger, saturation, minimum engagement
paseo-hive/references/panel.md       roles, brainstorm lenses, solve angles, per-goal seat rules, model assignment
paseo-hive/references/prompts.md     every prompt template seats receive
paseo-hive/references/checkpoint.md  checkpoint report template per goal
paseo-hive/references/formats.json  machine-readable seat answer formats (must match prompts.md)
paseo-hive/references/seats.example.json  example of the per-session seats.json
paseo-hive/scripts/hive.py           ingest, check, ledger, gate, leaks, lint (standard library only)
tests/                               unittest suite with synthetic fixtures (public: keep them generic)
README.md                            public description and example invocations
```

`docs/` holds local planning notes and is intentionally untracked (`.gitignore`). Tool run directories such as `.paseo-autopilot/` and `.paseo-hive/` are ignored too; never commit them.

## Design principles (do not regress)

1. **Independence before exposure.** The opening round of a leg is blind; seats see each other's work only in follow-up rounds.
2. **Model diversity over persona count.** Three seats on three model families beat five seats on one. With one family available, the checkpoint says "Limited diversity".
3. **Preserve diversity.** "Preserve diversity: disagreement in critique and decide, divergence in brainstorm, explore, and solve. Never converge prematurely." No manufactured consensus.
4. **Neutral, anonymising moderator.** Seats see letters (A, B, C), never roles or models. The seat-to-model mapping lives only in the session's `brief.md` and `seats.json`, the user-only `transcript.md`, and messages to the user, never in `checkpoint-<n>.md` (new seats read that file).
5. **Moderator-judged ending.** "Stop when another round cannot settle anything." Saturation signals, `STATUS: continue | nothing new` lines, and minimum-engagement checks guide the judgement; a round cap the user picks (1–10, suggested per mode) forces a checkpoint.
6. **Token discipline.** One agent per seat for the whole session (later rounds via `send_agent_prompt`), strict word limits, IDs instead of quotes, files instead of copying text through the moderator, lowest thinking level for select and fairness prompts, early stopping.

## Editing rules

- **English only** in skill files and prompt templates. The skill talks to users in their own language at runtime; the files stay English. Trigger phrases in other languages in the `description` are allowed.
- **Keep field names and IDs identical across files.** When you touch one, grep the others: `POSITION`, `CLAIMS`, `CRUX`, `STATUS`, `BECAUSE`, `QUESTION FOR THE USER`, `OBVIOUS`, `WILDCARD`, `BUILDS`, `SHORTLIST`, `RANKING`, `MAP`, `BEST NEXT QUESTION`, `{IDEA_LEDGER}`, `PROBLEM`, `DIAGNOSIS`, `APPROACH`, `STEPS`, `RISKS`, `TEST`, `RESULT`, `HOLES`, `BORROWS`, `CHANGED STEPS`, `PLAN`, `RESULT CHECKS`.
- **Formats live twice.** A change to an answer format in `prompts.md` needs the same change in `references/formats.json`; `hive.py lint` fails otherwise.
- **ID scheme** (defined once in `goals.md`): seats number their own items unprefixed (`C1`, `I1`, `N1`, `Q1`, `S1`, `R1`); the ledger prefixes them with the seat letter (`A-C1`, `B-I2`); decide options are shared (`O1`, …) and a seat's `NEW` option gets the next `O` number; explore areas are merged as `M1`, …; user items are `U1`, …; solve uses `A-DIAGNOSIS`, `A-PLAN`, `A-RESULT` and prefixed steps and risks (`A-S1`, `B-R2`).
- **Verbatim sentences** that other text relies on: the core rule (principle 3), the stop principle (principle 5), and the language rule in `SKILL.md`. Change them deliberately, everywhere at once.
- `SKILL.md` stays short and links to references; details and templates live only in `references/`.
- Bump `metadata.version` in `SKILL.md` for any behavioural change.

## OPSEC: this repository is public

- No personal data: no names, email addresses, employers, organisations, or hints about anyone's profession in files, examples, or commit messages. The copyright line in `LICENSE` is the one deliberate exception.
- No installation-specific details: no local paths, account or organisation IDs, numbered or custom provider-entry names, quota figures, or usage numbers.
- Examples must be generic and span domains (software, product, community or public sector, research, personal decisions).
- Commit with the repo-local neutral identity (`paseo-hive contributors <noreply@example.invalid>`); check `git config user.email` before committing.
- Before every push, scan tracked files for email-like strings, local paths, and any name or identifier from your own environment:

```bash
python3 paseo-hive/scripts/hive.py leaks --repo
```

- List names or identifiers from your own environment, one per line, in an untracked `.opsec-extra` file at the repo root; `leaks --repo` flags them in tracked files too. Test fixtures are public: keep them synthetic.

## Checks before committing

Run these and read the diff:

```bash
python3 paseo-hive/scripts/hive.py lint
python3 paseo-hive/scripts/hive.py leaks --repo
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

For larger changes, have a reviewer on a different model family read the diff against the principles above; same-family review misses the same things.

## Paseo runtime lessons (from building and testing this skill)

- Discover providers, models, modes, and thinking options at runtime; never hard-code them in the skill.
- A returned agent ID is not a running agent: confirm real activity (a first turn or tool call) before treating a seat as working.
- An agent waiting for a permission still reports `running`. Query pending permissions on every check instead of waiting on status alone.
- Some providers' read-only or "accept edits" modes still ask permission for every shell command, which floods the moderator. Seats should not need tools unless grounding is on; say so in the prompt.
- Plan-style modes that end by asking to leave plan mode can deadlock an unattended agent. Avoid them for seats unless verified.
- Provider streams occasionally end without a finish reason. One focused reprompt of the same agent usually recovers it without losing context.
- `paseo logs <id> --filter text` can move a seat's output into a file without passing it through the moderator's context. The log also contains the prompt (and, for some providers, the model's thoughts), so the answer has to be cut out. `hive.py ingest` does this: it cuts from the last line that starts the format's first field (for example `POSITION:` or `ATTACKS:`), after the echoed prompt, to the end of the format's last field (`QUESTION FOR THE USER` in every format except `select`, which ends at `DROP`), or to a `[User]` or `[Thought]` marker. Some providers log the model's thoughts after its final answer, sometimes with a formatted draft in them; `ingest` ignores a start line inside a `[Thought]` block unless there is no other.
- Some sandboxed providers cannot read files outside their workspace, so a seat given only file paths may answer blind. Check for that in the answer ("If this…") and paste the other seats' output inline for such seats; inlining for every seat also avoids per-file permission prompts in ask-style modes.
- Seats may try to load their own skills or plugins before answering. Say "Do not use any tools or skills" in follow-up prompts that carry everything inline. Exception: grounded solve, where that seat may still write its one work file for the current round and run commands without side effects, and nothing else.
- Some hosts do not show text written in the same turn as a multiple-choice dialog; the counter-question rule in `SKILL.md` covers this.
- A tool call can fail without any user action ("interrupted", often when another seat's notification arrives mid-call, or a call sent without its prompt). A moderator in a live run read such failures as the user blocking the call and said so to the user. `SKILL.md` now treats them as failures to retry once, never as refusals.
- Moderators skip the scripts and write summaries into seat files and ledgers by hand, which loses the seats' actual answers. `hive.py gate` blocks the next round until every answer is ingested and the ledger is built by the script; `ingest` and `ledger` record content hashes in `records.json`, so hand-written or edited files are caught.
- Several seats can repeat the same unchecked claim against an option until the user asks about it. `goals.md` makes such load-bearing assumptions targets for the next round.
- Moderators drift into process-only updates ("round 3 runs", "1 of 6 in") and launch the next round without saying what the seats argued, especially when seat output goes straight to files by script. `SKILL.md` requires a substantive per-seat update before the next round's prompts go out.

## Status and next steps

v0.4.0 adds a fifth goal, `solve`: seats diagnose a problem and work out competing plans, find holes in each other's plans, borrow, and revise; with grounding and a checkable problem they also carry the solution out and check each other's results (grounded solve untested live). v0.4.1, from a plan-only solve trial on three low-cost model families (one follow-up round): seats followed both solve formats, used `[replaces: …]` and changed-plan IDs, borrowed without converging, and again overran 250 words by about 10%; fixes: `ingest` ignores drafts inside a `[Thought]` block logged after the answer, a choice word such as `Changed.` counts the same in check and ledger, only a free-standing dash separates a choice from its text, and a clearer `[replaces: …]` template. v0.3.2: four goals, moderator-judged ending, and the checkpoint loop are specified and have been reviewed on paper by agents on two model families. One full critique leg has run live on three model families (opening round, two counter-questions, four follow-up rounds, checkpoint). Seats followed the formats, overran the 250-word limit by roughly 10–25%, conceded and refined positions without converging falsely, and engaged each other's claims once they could actually read them. v0.2.1 added from that run: context before choice dialogs, model names toward the user, a user-only `transcript.md`, a user-chosen round cap (1–10), and `--auto`. Since then, untested live: progress updates per seat and round (v0.2.2), thinking levels relative to each model's default (v0.2.2), a change log with the reason for every position change (v0.2.3), and an intake question before launch on whether the user wants to give input, asked together with the round cap (v0.2.4), and a required substantive update between rounds (v0.2.5). v0.3.0 added `hive.py` (ingest, check, ledger, leaks, lint) with a unittest suite on synthetic fixtures, `formats.json`, and `seats.example.json` (an example of the per-session `seats.json`). It is verified by tests and review only and has not been used in a live session yet. v0.3.1 lets the user pick the goal in the intake question, with "you choose" as an exit (untested live). v0.3.2, from a live decide run on three model families: `hive.py gate` before every follow-up round and checkpoint, failed tool calls retried instead of reported as refusals, no plan-style modes for seats, a premise check against sources in FRAME, and load-bearing assumptions as targets and as a third universal check (untested live).

Open work:
1. Simulated end-to-end run per goal (critique, brainstorm, decide, explore, solve), including one goal switch; check that v0.2.2–v0.2.5 behave as specified and that `hive.py` (ingest, ledger, leaks) works on real `paseo logs` output from each provider.
2. Measure cost per mode (agent turns; tokens where Paseo reports them) and tune word limits (all seats overran 250 words in the live run).
3. Grounded mode test (a file subject and a web subject).
4. Permission behaviour per provider mode: which modes let seats answer without prompts, and which can read session files.
5. A small eval set of subjects with known weak spots: does the panel find them without converging falsely?
6. Open questions: how long idle panel agents survive between checkpoints; whether 10 minutes is the right stall timeout for a seat.
