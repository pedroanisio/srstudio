---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0190: Toon characters dance on their approved head rig

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The dance SDK poses any character on one skeleton ([ADR 0185](0185-shared-skeleton.md)) and keeps moves as data timed
by a groove ([ADR 0186](0186-dance-moves-on-the-beat.md)). A drawing style still has to turn a skeleton pose into its
own drawing. Toon characters are drawn by a head rig: `toon_head.figure` draws a seated torso with desk arms, and the
head moves only on the channels its envelope allows (`turn`, `nod`, `face_x`, and the face drawings). A dance cannot
ask that rig for a rotation of the torso, for a raised arm, or for a head that rolls on every beat.

The measured seat groove sets the target: 129 BPM, one cycle per beat, a near-sine bob of 0.26 to 0.50 head radius
peak to peak (down in about 0.19 s, up in about 0.26 s), a sway with a snap of about 0.12 s and a return of about
0.32 s, landing on the drop. A raised arm rides the body with no lag. The head does not rotate within a beat; faces and
head turns change at phrase level.

## Decision

`srstudio.toon_dance` is the second drawing-style adapter. It drives existing parts only; no drawing changes.

- A `ToonFit` is data: a character's `SkeletonProfile` measured on its drawing (lengths in reference pixels over a
  scale), its rest values, the head rig, the seat, the arm width and appearance for limb tracks, and an expression
  table that names the faces a routine may ask for. Construction checks that the profile's head joint lands on the
  rig's neck pivot within one reference pixel, that both arms and hands exist, and that every face is a drawing the
  rig has.
- `perform(fit, move_or_routine, groove, start, end)` samples the dance once per picture (25 a second) with
  `dance_pose(base=fit.base)` and reads each pose three ways:
  - **body**: the hips' displacement and the turn of the chain from the hips to the head joint become one rigid
    transform of the whole figure about its seat, keyed per picture with held interpolation;
  - **head**: what the neck and head do beyond that chain becomes the rig's `turn`, `nod` and `face_x`, inside the
    rig's envelope or refused with `HeadReachError` (`clamp=True` clamps and counts instead); a move with no neck or
    head channel leaves them still, so within a beat the head moves only with the body;
  - **arms**: the pose with the body transform undone goes through the skeleton's limbs bridges, one exact solved pose
    per picture, into a `LimbTrack` per arm. The tracks replace the drawn arms and are drawn inside the body's groups,
    so an arm rides the body on the same picture. Where a wrist is above its shoulder the arm is drawn in front of the
    head.
- Faces are held. An entry's `expression` is looked up in the fit's table before anything is sampled; an unknown name
  raises `ExpressionError`. The face switches where the routine's entries switch.
- A routine or move that needs feet raises `SupportError` on a fit without legs.
- `toon_head.figure` gains `limbs=`: limb tracks drawn once inside the figure's body groups, for desk poses only.
- `draw(cv, parent, performance)` puts a performance on a canvas through `figure`. `ToonDance.measure` reads the groove
  from the projected head with `measure_dance`; `silhouette_series` reads it from rendered PNGs, so a proof checks the
  numbers and what the engine drew.
- `DOG_FIT` fits `toon-dog@2`, whose v2 drawing and head rig are approved and whose arms are limbs-capable. It has no
  legs, so it dances seated.
- All errors subclass `ToonDanceError`, which subclasses `SrstudioError` and `ValueError`.

`examples/toon_dance.py` builds the proof: eight bars of seat groove with the left arm raised for the last four, then
head nod, shoulder shimmy and arm pump, on a track from `music.render`, encoded with `--hw software --strict`, with the
groove measured on the numbers and on rendered pictures of a 270 x 480 check scene.

## Rejected alternatives

- **Drawing arms in the rig's own arm poses.** The rig has desk, wave and point arms, keyed per pose. A raised arm that
  follows the bob would need a new drawing per picture, and the arm would lag the body by a pose change.
- **Rotating the head group per picture to follow the skeleton's neck.** The rig's envelope allows a turn of about
  3 degrees and the target says the head holds within a beat. Following every neck delta would either break the
  envelope or roll the head on the beat.
- **Clamping silently.** A routine that asks the head for more than the envelope allows is refused by default;
  `clamp=True` is explicit and the count is reported in `ToonDance.clamped`.
- **A separate drawing of the character for dancing.** The task drives existing parts; a new look waits for the
  operator.
- **Sampling limb motion through the limbs solver from sparse keys.** Keys interpolate between solved poses and drift
  from the skeleton between pictures; playing one solved pose per picture keeps the arm on the skeleton exactly.

## Consequences

- Any toon character with a head rig and limbs-capable arms can dance once someone writes its `ToonFit`; the fit is
  checked against the drawing, not trusted.
- Arm tracks are played through a private `Motion` subclass that returns the solved sample for each picture. The
  limbs package has no public keyed-pose motion yet; when it gains one, the adapter moves to it.
- The dance presets assume arms that hang at rest. On a desk rest pose, moves that lift the arms need a hold
  (`ToonFit.hold`) to reach the height the move means.
- Head-only moves (`head-nod`) move the `nod` channel and never rotate the head in the plane; a shimmy reads weakly from
  the front because its motion is mostly along the character's depth.
- The fit's crown lies about 32 reference pixels below the drawn crown. The groove is measured on the head joint and on
  the silhouette, so this does not change the check, but a move that reads the crown should not trust it.
- The proof is a candidate look. It merges only after the operator approves the rendered clip.
