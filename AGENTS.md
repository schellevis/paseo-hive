# AGENTS.md

Guidance for AI agents and humans working on this repository.

## What this is

`paseo-hive` is a Markdown-only [Paseo](https://paseo.sh) skill. A moderator agent runs a small panel (3–5 seats) of agents on different model families toward one of four goals: `critique`, `brainstorm`, `decide`, `explore`. Seats work independently first, then react to each other anonymously. The moderator asks the user counter-questions only when an answer can move a crux, and pauses at checkpoints where user feedback starts the next leg with the same live panel.

There is no code, build, or test suite. The deliverable is instruction text that other agents follow, so precision and internal consistency are the quality bar.

## Layout

```text
paseo-hive/SKILL.md                  entry point, always loaded (keep ≤ 200 lines)
paseo-hive/references/goals.md       ID scheme; per-goal rounds, ledger, saturation, minimum engagement
paseo-hive/references/panel.md       roles, brainstorm lenses, per-goal seat rules, model assignment
paseo-hive/references/prompts.md     every prompt template seats receive
paseo-hive/references/checkpoint.md  checkpoint report template per goal
README.md                            public description and example invocations
```

`docs/` holds local planning notes and is intentionally untracked (`.gitignore`). Tool run directories such as `.paseo-autopilot/` and `.paseo-hive/` are ignored too; never commit them.

## Design principles (do not regress)

1. **Independence before exposure.** The opening round of a leg is blind; seats see each other's work only in follow-up rounds.
2. **Model diversity over persona count.** Three seats on three model families beat five seats on one. With one family available, the checkpoint says "Limited diversity".
3. **Preserve diversity.** "Preserve diversity: disagreement in critique and decide, divergence in brainstorm and explore. Never converge prematurely." No manufactured consensus.
4. **Neutral, anonymising moderator.** Seats see letters (A, B, C), never roles or models. The seat-to-model mapping lives only in the session's `brief.md`, the user-only `transcript.md`, and messages to the user, never in `checkpoint-<n>.md` (new seats read that file).
5. **Moderator-judged ending.** "Stop when another round cannot settle anything." Saturation signals, `STATUS: continue | nothing new` lines, and minimum-engagement checks guide the judgement; a round cap the user picks (1–10, suggested per mode) forces a checkpoint.
6. **Token discipline.** One agent per seat for the whole session (later rounds via `send_agent_prompt`), strict word limits, IDs instead of quotes, files instead of copying text through the moderator, lowest thinking level for select and fairness prompts, early stopping.

## Editing rules

- **English only** in skill files and prompt templates. The skill talks to users in their own language at runtime; the files stay English. Trigger phrases in other languages in the `description` are allowed.
- **Keep field names and IDs identical across files.** When you touch one, grep the others: `POSITION`, `CLAIMS`, `CRUX`, `STATUS`, `BECAUSE`, `QUESTION FOR THE USER`, `OBVIOUS`, `WILDCARD`, `BUILDS`, `SHORTLIST`, `RANKING`, `MAP`, `BEST NEXT QUESTION`, `{IDEA_LEDGER}`.
- **ID scheme** (defined once in `goals.md`): seats number their own items unprefixed (`C1`, `I1`, `N1`, `Q1`); the ledger prefixes them with the seat letter (`A-C1`, `B-I2`); decide options are shared (`O1`, …) and a seat's `NEW` option gets the next `O` number; explore areas are merged as `M1`, …; user items are `U1`, … .
- **Verbatim sentences** that other text relies on: the core rule (principle 3), the stop principle (principle 5), and the language rule in `SKILL.md`. Change them deliberately, everywhere at once.
- `SKILL.md` stays short and links to references; details and templates live only in `references/`.
- Bump `metadata.version` in `SKILL.md` for any behavioural change.

## OPSEC: this repository is public

- No personal data: no names, email addresses, employers, organisations, or hints about anyone's profession in files, examples, or commit messages. The copyright line in `LICENSE` is the one deliberate exception.
- No installation-specific details: no local paths, account or organisation IDs, numbered or custom provider-entry names, quota figures, or usage numbers.
- Examples must be generic and span domains (software, product, community or public sector, research, personal decisions).
- Commit with the repo-local neutral identity (`paseo-hive contributors <noreply@example.invalid>`); check `git config user.email` before committing.
- Before every push, grep tracked files for email-like strings and for any name or identifier from your own environment:

```bash
git grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' -- ':!LICENSE' ':!AGENTS.md'
git grep -niE '/home/|/Users/|/workspace/' -- ':!AGENTS.md'
```

## Checks before committing

There is no test suite; run these and read the diff:

```bash
wc -l paseo-hive/SKILL.md                                    # ≤ 200
grep -o '](references/[^)]*)' paseo-hive/SKILL.md            # every linked file must exist
grep -c '^STATUS: continue | nothing new' paseo-hive/references/prompts.md   # 4 (one per follow-up format)
for h in 'Opening round' 'Follow-up rounds' 'Ledger' 'Saturation signals' 'Minimum engagement' 'Typical user questions'; do
  printf '%s: ' "$h"; grep -c "^### $h" paseo-hive/references/goals.md   # 4 each
done
```

For larger changes, have a reviewer on a different model family read the diff against the principles above; same-family review misses the same things.

## Paseo runtime lessons (from building and testing this skill)

- Discover providers, models, modes, and thinking options at runtime; never hard-code them in the skill.
- A returned agent ID is not a running agent: confirm real activity (a first turn or tool call) before treating a seat as working.
- An agent waiting for a permission still reports `running`. Query pending permissions on every check instead of waiting on status alone.
- Some providers' read-only or "accept edits" modes still ask permission for every shell command, which floods the moderator. Seats should not need tools unless grounding is on; say so in the prompt.
- Plan-style modes that end by asking to leave plan mode can deadlock an unattended agent. Avoid them for seats unless verified.
- Provider streams occasionally end without a finish reason. One focused reprompt of the same agent usually recovers it without losing context.
- `paseo logs <id> --filter text` can move a seat's output into a file without passing it through the moderator's context. The log also contains the prompt (and, for some providers, the model's thoughts): cut from the last line that starts the answer format (for example `POSITION:` or `ATTACKS:`) to the last `QUESTION FOR THE USER` line.
- Some sandboxed providers cannot read files outside their workspace, so a seat given only file paths may answer blind. Check for that in the answer ("If this…") and paste the other seats' output inline for such seats; inlining for every seat also avoids per-file permission prompts in ask-style modes.
- Seats may try to load their own skills or plugins before answering. Say "Do not use any tools or skills" in follow-up prompts that carry everything inline.
- Some hosts do not show text written in the same turn as a multiple-choice dialog; the counter-question rule in `SKILL.md` covers this.

## Status and next steps

v0.2.1: four goals, moderator-judged ending, and the checkpoint loop are specified and have been reviewed on paper by agents on two model families. One full critique leg has run live on three model families (opening round, two counter-questions, four follow-up rounds, checkpoint). Seats followed the formats, overran the 250-word limit by roughly 10–25%, conceded and refined positions without converging falsely, and engaged each other's claims once they could actually read them. v0.2.1 added from that run: context before choice dialogs, model names toward the user, a user-only `transcript.md`, a user-chosen round cap (1–10), and `--auto`.

Open work:
1. Simulated end-to-end run per goal, including one goal switch.
2. Measure cost per mode (agent turns; tokens where Paseo reports them) and tune word limits (all seats overran 250 words in the live run).
3. Grounded mode test (a file subject and a web subject).
4. Permission behaviour per provider mode: which modes let seats answer without prompts, and which can read session files.
5. A small eval set of subjects with known weak spots: does the panel find them without converging falsely?
6. Open questions: how long idle panel agents survive between checkpoints; whether 10 minutes is the right stall timeout for a seat.
