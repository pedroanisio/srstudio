---
generated-by: Claude Fable 5.1 (claude-fable-5-1) in Claude Code
---

# ADR 0014: Toon coworkers — characters drawn in code with a hand-inked brush, on the cat's contract

- Status: accepted and implemented, 2026-10-28 (`srstudio.brush`, `srstudio.toon_cast`, `tests/test_brush.py`,
  `tests/test_toon_cast.py`, `episodes/toon_coworkers*.py`, `tests/test_toon_coworkers.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md); follows [ADR 0010](0010-toon-style.md)

## Context

The operator asked for two more Toon characters, "more polished". The Toon cat is traced from a recording
([ADR 0010](0010-toon-style.md), decision 2 as revised), so there is no drawing to trace a second character from,
and the first hand-written rig had already been judged not polished enough. What the style needs is a way to draw
a new character in code that looks inked by hand rather than plotted: varying line weight, soft corners, flat
fills, and the same contract as the cat so one pose list drives any of them.

## Decision

1. **A brush module, not more path strings.** `srstudio.brush` turns point lists into closed cubic `Shape`s:
   `spline` (Catmull-Rom through the points), `stroke` (a band whose half-width follows a `Pressure` profile —
   start, end, swell in the middle, a slow wobble — with round caps), `outline` (a closed fill through the points)
   and `rim` (the same points pushed outward by the ink weight, outward whichever way they wind), `ellipse`,
   `shift`, `rotate`, `flip` and `bounds`. Pressure never drops below 0.15 of the weight, so no line vanishes.
   Bad input (fewer points than a curve needs, coincident points, non-finite values, a non-positive weight) raises
   `BrushError`.
2. **Figures are stacks of flat layers.** A character is drawn as `(Shape, colour)` layers, bottom to top: ink rim,
   coat, markings, limbs (each an ink stroke under a coat stroke, a rimmed paw, two toe strokes), face. Everything
   is filled with `toon.flat`; nothing is a stroked path, so the ink reads as drawn, not as an outline effect, and
   the engine's shape count stays flat per pose.
3. **The cat's contract, exactly.** `toon_cast.figure_shapes(look, eyes, mouth, arms, frame)` accepts only the cat's
   `EYES`, `MOUTHS` and `ARMS` and the two typing frames; `dog(...)`/`frog(...)` take the same `(cv, parent, poses,
   duration, taps)` as `toon.cat` and use `toon.runs` and `toon.swap_frames`, so the pose lists, the keystroke
   swaps and the episode scripts are interchangeable. One addition, `enter=`, puts a character on from a later
   project second with its poses counted from then, which a sheet with two characters needs; an entrance at or past
   the end is refused.
4. **A `Look` is data, two looks ship.** `Look` holds the name, three coat colours, the silhouette, the eye and
   mouth placement, the limb weight, the ears, the markings and the nose. `DOG` (orange, drop ears outside the
   head, a light muzzle, a black nose with a highlight) and `FROG` (green, a pale belly, three spots, eyes on the
   bumps of its head, a wide mouth, two nostrils) are registered as `toon-dog` and `toon-frog`, characters of the
   Toon style, with `toon-coworkers` as their episode.
5. **Expressions are built, not drawn per character.** Eyes are a ring, a white and a pupil offset by kind, with a
   lid (straight for `half`, `down` and `side`, angled for `narrow`, an arc stroke for `closed`, a larger ring and a
   pinpoint pupil for `shock`); mouths are strokes and fills by kind, with the cat's lip colour for the open ones;
   `sigh` drops the whole figure by `SIGH_DROP`, `lean` turns it `LEAN_DEGREES` clockwise about the hips, `face`
   and `face2` bring the paws over the mouth. Every look × eyes × mouth × arms combination is tested to stay inside
   the character's corner of the room.
6. **A silent sheet episode shows them.** `episodes/toon_coworkers.py` (slug `toon-coworkers`, 24 s) runs the dog
   for the first half and the frog for the second with twelve captions in the style's pills, every kind of arms
   shown, keystrokes derived from the typing beats so the frames swap. Its data module `toon_coworkers_data.py`
   checks the beats (`SheetDataError`) and writes the project files. The room, desk and pills are registered with
   this episode too; the cat is not in it. It ships an Instagram post like every episode (`test_every_episode_script_ships_its_post`).

## Rejected alternatives

- **Tracing the new characters from found drawings.** Rejected: there is no reference the library may trace for an
  original character, and traced art cannot change expression beyond what was traced.
- **Stroked SVG paths with a fixed width.** Rejected: a fixed width reads as plotted, and the engine's contrast and
  shape accounting are simpler with fills; the brush gives the weight variation that reads as ink.
- **Reusing the cat's traced body with a recoloured coat.** Rejected: the silhouette, ears and muzzle are what make
  a dog a dog; a palette swap would give three blue cats.
- **A separate pose vocabulary per character.** Rejected: a sheet, a script or a narration placed for the cat must
  work unchanged for a coworker.

## Consequences

- A new Toon character is a `Look` plus, where it needs them, extra markings; the expressions, limbs, swaps and
  registry come from `toon_cast`. A new brush figure outside Toon can use `srstudio.brush` directly.
- `srstudio catalog --style toon` lists six parts; the catalog gallery shows the two coworkers with their poses
  from `toon-coworkers`.
- The sheet is silent; a narrated episode with the coworkers follows the survey's pattern (a data module naming the
  words its segments start on, `employee_survey_audio.py` as the model).

## Addendum, 2026-10-28: the sheet episode is retired

The operator retired `toon-coworkers`: the sketches *The Report* (T3) and *Logo Bigger* (T4) replace it, with the
same two characters in voiced comedies. `episodes/toon_coworkers*.py`, `tests/test_toon_coworkers.py` and its
Instagram post are removed. The dog, the frog and the Toon room, desk and captions now list the two sketches as
their episodes. Items 6 and 7 of the decision above describe the retired episode and are kept as its record.
