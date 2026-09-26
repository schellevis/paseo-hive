# Panel composition

## Seats

A seat is a role or lens plus a provider/model. Fill the roster from the domain library below and the per-goal rules. Name each role by its question, not its personality.

## Core roles

| role | question it owns |
|---|---|
| Advocate | What is the strongest version of this idea, and what do critics miss? |
| Skeptic | Which assumptions are wrong, and what evidence cuts against this? |
| Alternative | What entirely different explanation or approach fits the facts at least as well? |
| Evidence critic | What do we actually know, what are we assuming, and how would we check? |
| Pragmatist | What breaks when this meets real people, budgets, deadlines, and incentives? |
| Synthesist | What is the actual point, once the noise is stripped away? |

## Per-goal seat rules

- **critique**: at least one seat attacking the subject (Skeptic or a domain equivalent) and one Alternative; at most one Advocate. Drop the Advocate when the subject is already the default view; a panel with no defending seat on a contested claim converges immediately, so include an Advocate when the claim is contested.
- **brainstorm**: every seat gets a different lens (below); no Skeptic.
- **decide**: one seat per major stakeholder or criterion family, plus one "what option is missing?" seat.
- **explore**: a mix of domain lenses plus one Evidence critic.
- **solve**: every seat gets a different angle (below); no separate Skeptic, since every seat attacks the other plans in follow-ups.

## Brainstorm lens library

| lens | question it owns |
|---|---|
| Budget is zero | What would we do with no money at all? |
| Invert the problem | What would make this fail on purpose, and what does that rule out or suggest? |
| Borrow from another field | How does an unrelated domain solve a similar problem? |
| 10x scale | What changes if this had to work at ten times the size? |
| Naive outsider | What would someone with no history here try first? |
| Remove a constraint | What becomes possible if the biggest constraint disappears? |
| Worst idea first (then flip it) | What is the worst possible idea, and what does flipping it suggest? |

## Solve angle library

| angle | question it owns |
|---|---|
| Root cause | What is the actual cause, and how do we remove it? |
| Smallest change | What is the smallest change that solves the problem? |
| Redesign | How would we do this if we started over today? |
| Work around it | How do we make the problem harmless without solving it? |
| Who solved this before | How have others, including in other fields, solved this? |

## Domain libraries (examples, adapt freely)

- **Software architecture:** security, maintainability, performance, simplicity ("do we need this at all?"), operability.
- **Research or analysis:** source critic, methodologist, rival-hypothesis seat, legal/ethical risk, Synthesist.
- **Product or strategy:** user advocate, economist (costs, incentives), competitor's view, execution risk.
- **Policy or community:** affected-party view, unintended consequences, precedent and consistency, enforcement.
- **Personal decision:** future-self view, opportunity cost, reversibility, "what would you advise a friend?".

## Grounding

With grounding on, seats may read the subject files and search the web when their provider supports it, and must tag each claim `[source: …]` or `[assumption]`. For fact-heavy subjects in `--deep`, one seat may be an **Evidence scout**: it gathers the few facts the cruxes depend on and states no opinion. Grounding costs tool calls; allow it only in seats whose role needs it.

## Model assignment

1. Discover the usable provider/model pairs. Prefer pairs from different model families (Anthropic, OpenAI, Google, Z.ai/GLM, Mistral, Qwen, and so on) and different accounts when quota is tight.
2. Put the most capable available model on the seat that attacks the subject hardest (critique) or owns the widest scope (other goals); in solve, usually Root cause; diversity matters more than raw capability for the other seats.
3. Respect the user's model preferences and any stated quota limits. Avoid a provider the user says is nearly exhausted.
4. If only one model family is available, continue, and write "Limited diversity: all seats run on <family>" at the top of the checkpoint.
5. Keep a fallback order per seat. A seat whose model is rejected at launch moves to its next fallback; never retry a rejected model in the same session.

## Panel announcement (to the user)

```text
Panel (brainstorm, standard, ~3 seats x 2-3 turns):
A  Budget is zero          <provider/model>
B  Invert the problem      <provider/model>
C  Borrow from another field  <provider/model>
```
