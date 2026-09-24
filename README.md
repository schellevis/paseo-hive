# paseo-hive

A [Paseo](https://paseo.sh) skill that runs a small panel of agents on different models toward one of four goals: **critique** a claim, plan, text, or piece of code; **brainstorm** ideas; **decide** between options; or **explore** a problem space. Seats analyse independently, cross-examine each other anonymously, and occasionally put a sharp counter-question back to you. Instead of a single final report, the panel pauses at a **checkpoint**: your feedback — new information, a focus, a disagreement, even a goal switch — starts the next leg with the same live panel. It does not produce a manufactured consensus.

## How it works

- an independent opening round, where seats never see each other's work;
- anonymous follow-up rounds, where seats attack, build on, challenge, or probe each other's contributions;
- counter-questions, asked only when your answer can move something;
- a checkpoint that shows where the panel stands and what is still open;
- your feedback starts the next leg — same panel, possibly a new goal.

At the start you are asked whether you want to give input along the way, and you can add context before the panel begins. You choose how many reaction rounds a leg may take (1–10); `--auto` lets the panel run without pausing for you until the checkpoint. The user-facing report names each seat by its model; the seats themselves only see letters.

```text
/paseo-hive Small open-source projects should reject AI-generated pull requests by default.
/paseo-hive --goal brainstorm How could a public library attract more teenagers?
/paseo-hive --goal decide --quick SQLite or Postgres for a single-user desktop app?
/paseo-hive --goal explore --deep What would we need to know before moving a team to a four-day week?
/paseo-hive --auto --rounds 5 Should a neighbourhood association own its community garden or lease it?
```

Status: early draft.
