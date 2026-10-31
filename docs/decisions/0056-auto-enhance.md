---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0056: Every video enhances the process for the next one

- Status: accepted (2026-10-31), from the operator's request: a new rule, auto-enhance mode, default on, where every
  agent that builds a video implements an enhancement to the process when the video ends so the next one is better,
  with a gate, and with the mode off the video is simply delivered
- Deciders: the operator (pedroanisio), recorded by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator does not review @tuxmeme reels: quality comes from the engine, the agents and the gates. Lessons from a
build lived in reports and memory, so a video could finish without leaving anything behind for the next one.

## Decision

1. `episodes/auto_enhance.json` holds the mode. Absent means on. Anything unreadable refuses the delivery: a broken
   setting never reads as off. `srstudio enhance on|off` writes it, and only the operator changes it.
2. An enhancement is a commit on `develop` with the trailers `Enhances: <slug>` and `Enhancement-Kind: <kind>`.
   `auto_enhance.KINDS` is the closed list of possibilities.
3. The gate reads the commit, not a claim about it. One slug and one kind. It changes the library or tools and adds a
   test, or it changes the skill and bumps `schema_version`. It touches none of the video's own files.
4. `deliver` and `publish_pilots.py` run the gate on a video's first delivery, before anything is written. A video in
   the delivery manifest, or on Drive for a pilot, owes nothing, so the published catalog needs no list and a fix to a
   delivered reel is not held up. A reel delivered while the mode is off stays clear when it comes back on.
5. Pilots are covered, and their enhancement must reach `develop` like any other, even while a kit waits on a branch.

Each commit message is model output, so it gets the five controls of the project rules: a typed parse into
`Enhancement`, semantic checks against the diff, a typed `EnhanceError` or refusal, failing-input tests in
`tests/test_auto_enhance.py`, and a `git` call bounded by `GIT_SECONDS`.

## Alternatives rejected

- **A ledger file per video.** It records a claim, not a change. A commit hash in it breaks on the rebases and
  cherry-picks this repository uses, and trailers travel with the commit.
- **Gating `check` as well.** `check` runs in the Drive unit. It already refuses a video that was never delivered, so
  a second gate there adds nothing, and it would hold back a reel delivered with the mode off.
- **A closed list of published reels, as ADR 0048 keeps.** The delivery manifest already says what has been delivered.
- **One enhancement for a whole batch.** The rule says every video. A batch of ten leaves ten changes behind.
- **Scoring whether the next video is better.** ADR 0015 rejected a model as the judge of what is funny, and the
  account's numbers lag a reel by days.
- **An environment variable for off.** The Drive unit and a build would see different modes, and an agent could set
  it for one command. A tracked file shows in the diff.

## Consequences

- The gate proves that a tested change landed, not that it helps. A weak change passes, and merge review is what
  catches it. The ledger from `srstudio enhance` makes those changes easy to read in one place.
- A video can be held up by a merge. That is deliberate: an unmerged enhancement helps no later video.
- The skill grows if every enhancement is a skill rule, so prefer a tested library change where one fits.
- A file edit can still turn the mode off. Nothing mechanical stops it, but the change shows in the history.
