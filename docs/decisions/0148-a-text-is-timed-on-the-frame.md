---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0148: A text is timed on the frame, not per layer

- Status: accepted (2026-11-01), ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0078](0078-strict-findings-at-first-delivery.md) and
  [ADR 0147](0147-a-caption-does-not-run-across-a-sentence-end.md)
- Back to the [library README](../../README.md)

## Context

arc4d3: "Make structural errors impossible in the SDK and kit, not caught in review." Rule 8: "Text timing across cuts:
measure on screen time on the composited frames, not per layer." The ruling on the strict gate said the same: "the
text's real time on screen from the frames (first to last frame it's legible) against the rule's minimum".

The engine's `LEG-SHORT` times each text layer alone, so a card carried across a cut into a second layer is reported
short (`docs/engine-bug-legibility-across-cuts.md`). Filing that bug is the operator's call, and nothing here needs a
change to the engine.

## Decision

1. **The rule is `text-short`, the check `text-timing`.** A text is its words, ignoring case and spacing. It is on screen
   from the first frame it is legible to the last, whichever layers draw it. Its longest run must reach `MINIMUM`,
   0.8333 s, the limit `LEG-SHORT` reports.
2. **Legible is measured on the frames `scene-render eval` gives.** The node has the words and at least half its opacity,
   at least half its box is on the frame, and less than half of that is under a solid shape in front.
3. **A gap of up to 2 frames does not end a run**, so a card flipping in a shot is one text.
4. **A burned caption track is read from `scene-render captions`.** It is not a node of the frame, it sits over the whole
   picture, and the engine's own paging says when each page is up.
5. **The pass is cheap, and exact where it counts.** Every 0.25 s and one frame after each `start` and each opacity key,
   on the reel's own frames. A run that may be short is then read frame by frame at both edges.
6. **It runs after the build and at first delivery.** `srstudio build` measures when it has an engine, and exits 1 on a
   fault. With no engine it says it did not measure. `text_rules.timing_defects` holds the publish gate either way.
7. **The strict gate is unchanged.** `LEG-SHORT` stays a finding, and an agent cannot clear it from here. This check is a
   second, stricter reading that needs no master, and its number can stand as the evidence a person signs under ADR 0078.

## What it would have caught

Measured with this code over the 237 built scenes in `generated/episodes`, none of them unreadable:

- **16 reels, 41 texts** stay on screen under the minimum. 15 are published and listed, 39 rows.
  `what-my-dad-does` is pulled, so it is not listed: its 2 texts stop a rebuild until they are held longer.
- **The 80 `LEG-SHORT` rows of the 140 reports**, 13 reels, read on the frames around each row: 38 are false, because the
  text stays up longer than the layer; 36 are real; 6 could not be matched, 4 of them because `check-with-my-team` has no
  scene left. Some of those reports are older than their scene.
- 8 of the 13 reels clear on the frames, `no-thanks`, `four-coats` and `no-pad` among them. 4 stay at fault:
  `repeat-after-me`, `the-family-photo`, `good-you` and `the-stove`. 12 of the 16 reels at fault have no such row, and 11
  of those have no report at all.

The two scenes of the engine bug report and a third, short on any reading, run against the real engine in
`tests/test_text_rules.py`: one layer passes, the card carried across a cut passes, the short card fails. No frame of a
master was viewed for these counts.

## Limits

- `scene-render eval` gives each node's place and opacity, not pixels. A text is timed on the placing the engine would
  composite. An effect, a matte or a blend that hides a text is not seen, and `in_front` counts only solid shapes.
- A flash that starts on no `start` and no opacity key, and falls between two frames of the pass, is missed: a text moved
  on from off the frame, for instance.
- A text animator keeps the whole words on the node from its first frame, so a typewriter is timed as if it were fully up.
- `TXT-FIT`, the 79 rows of the same reports, is not read here. It measures whether a text fits, not how long it stays.
- A text that repeats is judged by its longest run, so a word held once may flash later.
- A cut inside a cue is not a fault here. The rule reads time on screen, so a text carried over a cut counts as one.

## Alternatives rejected

- **Clear `LEG-SHORT` rows from the frames in the strict gate.** It would let code waive a finding that ADR 0078 keeps
  for a named reviewer, which weakens a check.
- **Read the master with OCR.** It is a new dependency, slow and wrong on styled type. The engine already knows the words.
- **Patch the engine.** Filing it is the operator's call, and the build rule does not wait on it.
- **Every frame of every reel.** One `eval` takes about 0.14 s, so 24 fps would cost about 3.4 s for each second of reel.
  The two passes reach the same times on what can be short.
- **The per-reel minimum by word count.** The reports use one limit, and the rule says "the rule's minimum".
