---
pilot: choice-blindness
main-trigger: surprise
generated-by: claude-opus-5-5 in Claude Code
date: 2026-10-31
---

# Notes: Choice Blindness

## Main trigger

Surprise, the finding up front. The claim is the first thing said and read, "Most people will explain a choice they
never made.", over a goat with two cones in front of him. Everything after it is that sentence happening to him: he
orders vanilla, gets mint and explains mint, then gets toothpaste and explains toothpaste. The name is a small
signature over the last hold, after the laugh. There is no card and no dark stage.

The observation: hand someone a thing they didn't pick and they'll tell you why it was the obvious choice. The line
written first, and the one the reel exists for, is "Vanilla has never once protected my enamel." It calls back to the
order he really gave.

## What is claimed, and what is comedy

Claimed, and tracing to `sources.md`:

- **The hook, "Most people will explain a choice they never made."** This is an inference, not a figure any paper
  states, and the caption keeps its scope: simple choices, in experiments. It rests on three things:
  - about two in three shoppers missed their one swap and were asked to justify it (Hall et al., 2010; rows 9, 10);
  - at least about 80% in every 2005 group missed at least one swap (row 5);
  - the 2005 authors' suggestion, offered as a possibility, that "delivering an M report came naturally to most of the
    participants in our task" (p. 118).
- **The stamp, "Only 13% of swaps spotted at the time. Johansson et al., 2005".** 46 of 354 swaps were caught
  concurrently. The figure counts swaps, not people, and the study used photos of faces.
- **The turn, "When we explain a choice, we may be building the reason, not remembering it."** It keeps the paper's
  "may", and it does not tell the viewer they are lying.

Comedy, with no study attached:

- The parlour, the cones and the toothpaste. Nobody in the study ate anything; the caption says the ice cream is ours.
- The goat's reasons. "Toothpaste person" and "enamel" are the detail only the swapped thing has. In the study only
  13.3% of reports cited something like that, so no line calls it typical and no number sits near a reason.
- The fox only ever asks why, once each time, because nobody in the studies was challenged. "Defend" appears nowhere.
- The political study is left out, and the jam and tea study was not needed for a second beat.

## Parts reused

Goat version 1 and fox version 2, both with their head rigs. `toon-ledge`, in a new `parlour` finish.
`toon_cars.drive_past` for the street. From the mind kit: `mind-captions`, the far blur, the grade and the sting. The
signature cactus and code. `mind_kit.py` was not changed.

## Parts new (all proposed)

`toon-cone`, `toon-toothpaste-cone`, `toon-parlour-case`, `toon-parlour-front` and `toon-parlour-back`, with catalog
titles, plus `toon_parlour.held`, the forearm that carries a cone. Three additive library changes come with them, and
all default to no change: `toon_house.LEDGES["parlour"]`, `toon_house.ledge(inset=)` and the `on_face` hook on
`toon_head.figure` and `Staging`.

## What I would change

- The longest stretch without a joke is the turn, about 4.2 s of narration over a slow push. The goat shifts his gaze
  and the street moves, but he does nothing funny while it plays.
- The narrator's stamp line is the only caption the reel does not repeat; a muted viewer reads the stamp instead.
- The silent taste beat runs 1.15 s. It is the look of a goat realising, and it is after the first 5 s.
- The master sits at -14.7 LUFS, a little under the -14 target.
- The arm with the cone is drawn apart from the rigged body, so it does not follow his head or his breathing.

## Watch gate

Watch gate: Pedro watched it and approved it (31 Oct).

The gate questions have no written answers.

## Enhancement

`srstudio craft` now reports silence in the first five seconds, including the wait before the first line. Kind: checks.
