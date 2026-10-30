---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0050: Organic head motion: a head split at the neck, moved by springs, speech, noise and glances

- Status: accepted; the operator approved the motion from its proof page, 2026-10-30; implemented on the sloth (`srstudio.head_motion`, `srstudio.toon_head`,
  `tools/build_stress.py`, `assets/stress/`, `toon_critters.SLOTH_RIG`, `Torso.under`; `tests/test_head_motion.py`, `tests/test_toon_head.py`,
  `tests/support/spring_curve.py`).
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Builds on [ADR 0049](0049-toon-torso-one-smooth-body.md) (the torso) and
  [ADR 0020](0020-toon-lip-synced-cast.md) (lip sync)
- Back to the [library README](../../README.md)

## Context

A Toon character's head holds still while it talks. The operator asked for head movement as organic as possible,
developed and tested on the sloth. The drawing bakes the head's 7 degree tilt into the vertices of one outline, so
nothing can turn at the neck, and the published reels must not change by a byte.

## Decision

1. **A rig splits the character at the neck.** A `HeadRig` supplies three drawings: `skull` (the head closed under the
   chin), `face` (what slides over it) and `trunk` (the body, whose top is a shaggy ruff, from `Torso.under`). The
   skull sits behind the trunk, so the ruff hides the seam at every bound the style allows. `toon_head.figure` draws
   it and `toon_cast.figure` is untouched, so motion is opt-in: `SLOTH` keeps its one outline.
2. **Nested groups carry one kind of motion each.** Outermost first: `lean`, `breath`, then behind the body `turn`
   (the drawn tilt plus glances and the trail), `nod`, `idle` and `lift`. No property has two sources, because two
   additive channels on one property are untested in the engine.
3. **The engine evaluates the motion from sparse keys.** Nods, glances and leans are targets on `spring` keys with
   `carry="true"`; the idle uses `catmull-rom` and the breath `sine-in-out`. Nothing is baked per frame. A `Spring` is
   named by frequency and damping ratio.
4. **Speech drives the nods.** Following Graf, Cosatto, Strom and Huang, *Visual Prosody* (2002): an accent is a content
   word whose stressed syllable stands over the phrase's median loudness; about 80 % of accents nod; a nod spans about
   three phones and leads its syllable; a phrase after a pause opens with a dip; a character keeps one movement type
   (`^`, `~` or `/`). Two rules are added. The last content word of a phrase is always an accent and always nods
   (the nuclear accent), because a line trailing off into its point would otherwise lose it, and the other accents
   are drawn so the share stays about 80 %. Intensifiers nod 1.5 times bigger. A negation head-shake is not used.
5. **The idle is two octaves of hashed 1-D gradient noise, ducked while speaking, and a breath.** The breath is taken
   in the pauses and let out across the phrases, or an uneven cycle in silence, and a shot ends wherever the last
   breath has got to.
6. **Glances are hold keys on the eyes with the head following late.** Pupils jump; the head turns through its spring
   and the face slides across the skull. Only a drawing with a `pupil` of its own can glance.
7. **Determinism and bounds belong to ordinary code.** Every draw comes from `hash_unit` (seed, channel, ordinal), so no
   channel shifts another and no clock is read. `limit` states each channel's most, overshoot included, and a Python
   copy of the engine's spring (`tests/support/spring_curve.py`) proves the keys stay inside it.
8. **Word stress comes from a vendored table.** `assets/stress/cmudict-stress.txt.gz` holds each word's stress digits,
   built by `tools/build_stress.py` from the CMU Pronouncing Dictionary data under its BSD-style licence
   (`assets/stress/CMUDICT-LICENSE`). The table replaces the stress lookup the project would otherwise write by hand.
   It adds no package.

## Consequences

- Only the sloth moves, through `toon_head.figure`. `sketch` does not cast it yet: a reel needs a decision to do so.
- A character needs its head separated before it can join: a skull, a face layer, a ruff or collar, and a `HeadStyle`.
- The glance is a 2D slide of the face over the skull. It is not a turn in depth.
- `toon_cast.figure` now calls `_draw_mouth` and `_draw_blinks`, extracted for reuse. Digests in
  `tests/test_toon_head.py` pin the flat figure, and the rebuild proof pins the episodes.

## Alternatives rejected

- **Pre-drawn tilted heads swapped on hold keys.** Pose-to-pose steps cannot give a settle or a lag.
- **Leaning the whole figure with a separate face group.** The body would move with every nod, and the head would
  never turn about its neck.
- **Per-frame baked keys.** Large scene files, and the engine's own springs would be unused.
- **The Cartoon Animation Filter, or a neural model of motion.** The filter needs a baked signal to work on, and a model
  would add an unverifiable, nondeterministic source for what a few rules do here.
- **The `cmudict` Python package.** It is GPL-3.0-or-later, though the dictionary data is BSD-style, so the data is
  vendored without the package. [ADR 0019](0019-lip-sync.md) rejected CMUdict for lip sync because a dependency and
  data files would only repeat what character timestamps already give. Stress is different: a character timestamp says
  nothing about which syllable carries it, and spelling rules guess it badly.
- **A negation head-shake.** It needs a second movement type, and one signature per character is the point of rule 4.
