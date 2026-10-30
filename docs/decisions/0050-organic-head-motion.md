---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0050: Organic head motion: a head split at the neck, moved by springs, speech, noise and glances

- Status: accepted; the operator approved the motion from its proof page, 2026-10-30, and asked for it to be usable
  and reusable. Implemented in `srstudio.head_motion`, `srstudio.toon_head`, `srstudio.toon_rigs`, `tools/build_stress.py`,
  `assets/stress/`, `toon_critters.Split`, `toon_critters.torso_rig`, `Torso.under`, `sketch.write_speech` and
  `toon_sketch.Staging.heads`; `tests/test_head_motion.py`, `tests/test_toon_head.py`, `tests/test_toon_sketch_heads.py`,
  `tests/support/spring_curve.py`. The sloth, the goat, the hamster and the inked fox have rigs; the looks of the
  last three wait for the operator's judgement.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Builds on [ADR 0049](0049-toon-torso-one-smooth-body.md) (the torso) and
  [ADR 0020](0020-toon-lip-synced-cast.md) (lip sync)
- Back to the [library README](../../README.md)

## Context

A Toon character's head holds still while it talks. The operator asked for head movement as organic as possible,
developed and tested on the sloth. The drawing bakes the head's 7 degree tilt into the vertices of one outline, so
nothing can turn at the neck, and the published reels must not change by a byte.

The operator then asked for it to be used and reused: a writer turns it on in a normal sketch without building a
scene, and a rig comes from what any drawing supplies rather than from sloth code.

## Decision

1. **A rig splits the character at the neck.** A `HeadRig` supplies three drawings: `skull` (the head closed under the
   chin), `face` (what slides over it) and `trunk` (the body). What covers the seam is the drawing's choice: the
   sloth's ruff goes over the head (`head_over=False`); the goat, the hamster and the fox put the head over the body
   so the chin covers it (`head_over=True`) and the trunk's top runs up behind the head. `toon_head.figure` draws it
   and `toon_cast.figure` is untouched, so motion is opt-in: `SLOTH` keeps its one outline. `toon_head.open_seam`
   proves the seam shut at the corners of the style's bounds, for every rig; `free` is how far from each end of the
   cover line it stops checking: the corners where a head may part from the shoulders.
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
   and the face slides across the skull. A drawing glances if it has a `looking(dx, dy)`, which the `Glancing`
   protocol names; `Critter` and `Inked` have one, so no shared code knows which character it draws.
7. **Determinism and bounds belong to ordinary code.** Every draw comes from `hash_unit` (seed, channel, ordinal), so no
   channel shifts another and no clock is read. `limit` states each channel's most, overshoot included, and a Python
   copy of the engine's spring (`tests/support/spring_curve.py`) proves the keys stay inside it.
8. **Word stress comes from a vendored table.** `assets/stress/cmudict-stress.txt.gz` holds each word's stress digits,
   built by `tools/build_stress.py` from the CMU Pronouncing Dictionary data under its BSD-style licence
   (`assets/stress/CMUDICT-LICENSE`). The table replaces the stress lookup the project would otherwise write by hand.
   It adds no package.
9. **A writer asks for it in one line.** `Staging.heads` names the characters that move: `heads=("sloth", "goat")`.
   The default is empty, so an episode that says nothing is drawn exactly as before. `build` takes the plan from
   `voiced/speech.json`, which the recording run writes beside `beats.json`: each kept take's letters, speaker and
   place. A project recorded before this needs its recording run again (cached takes cost no request). A silent
   build has no takes, so its heads only idle.
10. **A rig is data, and the registry refuses by name.** `toon_rigs.RIGS` maps a registered part to its `HeadRig`.
    `rig_of` raises `ToonDataError` naming the character for one with no rig, because a character asked to move and
    drawn still would look like a choice. `toon_critters.Split` and `torso_rig` build a rig from a `Torso` with the
    chin, the neck top, the hand the body is drawn in and the three layers, so a `toon_torso` character takes a rig
    without touching the shared path.
11. **A plan is one continuous performance, played a shot at a time.** The plan covers the whole sketch and
    `HeadPlan.during` gives each shot its slice, so a cut lands on whatever the head was doing. A character hears the
    other speakers (`heard`): the phrase ends it hears add smaller nods (`LISTEN_SHARE` of a full one, late by
    `LISTEN_LAG`), and the gaze and the idle treat those spans as busy. A listener's breath still follows its own
    speech.
12. **Each character keeps one signature in its `HeadStyle`.** The sloth is slow; the goat abrupt, with a stiff
    spring and long holds; the hamster quick and small; the fox a slow, loose tilt with a long sideways look.

## Consequences

- Motion stays opt-in per cast member, and no published reel changes: `Staging.heads` is empty on all of them.
- A new character supplies a `skull`, a `face`, a `trunk`, the head contour, the neck pivot, the tilt, what `cover`s
  the seam and a `HeadStyle`, and registers in `toon_rigs.RIGS`. A `toon_torso` character gets most of that from
  `Split`; the seam test and the bounds test run on every entry of `RIGS` with no further code.
- A rig's skull and trunk are a second drawing of the character, so a rig can drift from the flat look. The inked fox's
  first rig drew a collar across the chest; its proof clip caught that, and `tests/test_toon_head.py` now pins the
  white running into the bib. Character versions pin the flat drawing, not this one.
- The motion is seeded per character, so a character's idle noise repeats from reel to reel.
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
- **A second head chain drawn over the trunk for the goat's beard.** It keeps the ruff order everywhere but needs two
  groups to play the same motion. `head_over` is one flag and costs the shared path a single branch.
- **Head motion on by default for every Toon character.** A character with no rig would have to be refused or drawn
  still, and a rebuilt published reel would change.
- **Building the plan from `voice-transcript.json`.** It has no character timings, and the nods and the stress lookup
  read those, so the recording run writes them to a file of their own.
