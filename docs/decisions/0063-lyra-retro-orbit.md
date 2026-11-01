---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0063: Lyra and the Retro Orbit parts, drawn as flat print plates

- Status: accepted for Lyra (2026-11-01). The operator asked for this port and approved her: "Lyra is approved". The
  `toon-lyra` record and `LYRA_RIG` are `approved` on those words. They named Lyra, so the seven Retro Orbit sets and
  props stay `proposed` and wait for their own decision. The clips are in `generated/character-proofs/lyra/`.
  Implemented: `srstudio.toon_plate`, `srstudio.toon_orbit`, `srstudio.toon_lyra`;
  `tests/test_toon_orbit.py`, `tests/test_toon_lyra.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0047](0047-character-versions.md), [ADR 0050](0050-organic-head-motion.md) and
  [ADR 0020](0020-toon-lip-synced-cast.md)
- Back to the [library README](../../README.md)

## Context

The Retro Orbit pack is a mid-century concept set supplied by the operator: Lyra, an owl who presents astronomy, two
places, five objects, six moods, eight eye poses. It is built as flat spot colours with a screen-print grain, with no
ink line, in a palette of its own. The brief keeps that look: she must not be flattened into the older cast's style.

The Toon parts are brush shapes with pressed ink. Three things had to give way to carry a poster look through them:

- A plate has fills with hard edges and rules of constant width, and no clip paths.
- The rig path does not validate `Pose`, while `toon_cast.figure_layers` validates the shared `EYES` and `MOUTHS`, so
  a pose in one of her moods can only go through the rig.
- The pack's sets are landscape boards and the Toon frame is 9:16.

## Decision

1. **Plates are ordinary brush shapes.** `toon_plate.shape` turns an absolute path into a closed cubic `Shape`, so a
   plate goes through `Canvas` and into a digest like every other part. Nothing from the pack is vendored; its geometry
   is ported into code, and its colours stay literal so a plate keeps its palette on any canvas.
2. **Clipping is geometry.** `toon_plate.clip` cuts a polygon against a convex outline and `inside` drops what crosses
   it. The result is plain polygons with no clip path for a digest to depend on.
3. **The sets are recomposed for 9:16, not cropped.** Everything in them sits behind her. Salon: the window runs off
   the right edge with Saturn inside it, so the paper barrel of the telescope stands against the navy glass and her
   tufts against bare wall. Terrace: the crescent and its orbit fill the sky, the pod sits behind her left side, and
   the telescope stands clear of her raised wing. Neither set signs: the marks stay on the desk
   ([ADR 0001](0001-signature.md)), and a reel in these rooms gives its shots a `Staging.desk`.
4. **The finish is one function.** `toon_orbit.print_finish` fits `Staging.finish`, runs the pack's two-plate grain at
   the pack's density, and is seeded. No set or prop adds grain of its own.
5. **Lettering is live text.** Bebas Neue 400 and DM Sans 700, the pack's two faces under OFL, come through
   `fonts.install` into `generated/fonts`. With no `Lettering` a sign stands blank; a sign is never outlined by hand and
   no font file is vendored.
6. **Moods and eye poses are typed data.** `MOODS` and `EYE_POSES` hold `Mood` and `EyePose`; `mood()` and `eye_pose()`
   refuse an unknown name. The shared vocabulary maps onto the same states, so she keeps the `Drawing` contract and a
   pose that names `teary` or `hearts` still draws. Those few states are new: the pack has no drawing of them.
7. **Her beak stays drawn and the gape opens under it.** Lip sync follows ADR 0020 with `LIP_SYNCED` naming her. `open`
   is the talking gape, `round` the round one, `teeth` the small one.
8. **The rig's seam is the head's own chin over the scarf, with the uniform's neckline raised behind it.** `LYRA_RIG`
   puts the whole head over the body (`head_over`) with `free=0`, so `open_seam` must find no point open at any of the
   rig's bounds. The drawing's own neckline opened seven seam points at the corners of the swing, and a higher neckline
   behind the head closed them. Measured at `(-14.075, -3.6)`, `(-14.075, 9.975)`, `(10.075, -3.6)`, `(10.075, 9.975)`:

   | Neckline: start, end, control height | Open points |
   | --- | --- |
   | as drawn (`231,455`, `372,452`, 396) | 7 |
   | `222,440`, `380,440`, 380 | 4 |
   | `226,436`, `378,436`, 380 | 2 |
   | `232,432`, `372,432`, 390 | 0 |

   The bounds rest on a swing of turn 8.0, roll 3.375, idle 0.7 and a nod down of 9.375. The rest tilt is -2.

9. **She moves like an owl.** `LYRA_MOTION` (seed 6301) snaps round and is slow to leave; `mood_plan` turns her head to
   each mood's tilt, bounded by the rig's limits.

## Alternatives rejected

- **The older cast's pressed ink line.** It would change the look the brief keeps. The plates draw with constant-width
  rules.
- **Vendoring the pack's SVG plates or scripts.** A file outside `Canvas` has no digest, and the library would carry a
  second drawing path.
- **Outlined lettering.** It freezes text as shapes, and the brief refuses it.
- **Grain per set.** A second caller would drift; one function has one test.
- **A new shared arm kind for her wings.** Only the `desk` arms are the pack's drawing, and a shared `ARMS` entry would
  bind every character to an owl's pose. Her other arms use a tapered generic wing, inside her module.
- **Moods through the flat `figure`.** It validates the shared names and would refuse them. Widening it would loosen a
  check for every character, so `lyra()` draws through the rig with a still plan.
- **Moods as gated figures, one per mood.** It would multiply records for what is one drawing with six states.
- **An allowance for the open seam (`free` above 0).** A raised neckline hides the seam with no allowance, and it never
  shows at rest.

## Consequences

- Any new poster-look part can use `toon_plate`, and nothing in the brush cast changes.
- She is on no reel and in no release. A reel may draw her and her rig; the sets and props still need a decision.
- The port differs from the pack where 9:16 and the rig required it: the sets above, the raised neckline, the mint
  terrace table top, FIELD STATION on two lines, and the flat drawing's head tilt of 0 with the rig's rest at -2.
- At the extreme of a turn the scarf slips out from under one side of the chin. That is a limit of a rigid head over a
  body that does not move.
