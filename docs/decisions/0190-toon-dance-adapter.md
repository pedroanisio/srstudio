---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0190: Toon characters dance on their approved head rig

- Status: proposed (2026-11-02); arms amended (2026-11-02) after the operator refused the first proof's arms
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

The first proof drew the arms as the limbs package's tubes: one width from shoulder to paw, a ball at each joint,
rooted at shoulder joints outside the drawn body. The operator refused it: the arms had regressed, came apart from
the body and read as insect legs. The approved arms of `toon-dog@2` are the target: the torso's coat stroke tapering
into the body over a single ink line, the shade under the forearm, the dog's own paw, rooted inside the torso's
silhouette. A dance arm differs from them only in that it moves, and it keeps each gesture's timing and acceleration
as the skeleton dances it.

## Decision

`srstudio.toon_dance` is the second drawing-style adapter. It drives existing parts only; no drawing changes.

- A `ToonFit` is data: a character's `SkeletonProfile` measured on its drawing (lengths in reference pixels over a
  scale), its rest values, the head rig, the seat and an expression table that names the faces a routine may ask
  for. Construction checks that the profile's head joint lands on the rig's neck pivot within one reference pixel,
  that both arms and hands exist, that the rig's drawing has a torso that draws its arms, that both shoulder joints
  lie inside the torso's drawn silhouette, that at rest each elbow and wrist lands on the approved desk arm within one
  reference pixel, and that every face is a drawing the rig has.
- `perform(fit, move_or_routine, groove, start, end)` samples the dance once per picture (25 a second) with
  `dance_pose(base=fit.base)` and reads each pose three ways:
  - **body**: the hips' displacement and the turn of the chain from the hips to the head joint become one rigid
    transform of the whole figure about its seat, keyed per picture with held interpolation;
  - **head**: what the neck and head do beyond that chain becomes the rig's `turn`, `nod` and `face_x`, inside the
    rig's envelope or refused with `HeadReachError` (`clamp=True` clamps and counts instead); a move with no neck or
    head channel leaves them still, so within a beat the head moves only with the body;
  - **arms**: the pose with the body transform undone places each arm's root, elbow, wrist and paw on the solved
    bones. The root and the paw are carried from the approved desk arm: the root as a fixed point in the shoulder's
    frame (the torso's root, inside the silhouette), the paw as a fixed point in the hand's frame. The arm is then
    drawn by the drawing's own torso (`Torso.drawn`) and paw: the same coat stroke over one ink line, the same shade,
    no joint caps. The taper is laid bone by bone: a point on the upper arm or the forearm is as wide as the same
    place on that bone of the desk arm, however long the bone is drawn on screen. One drawing per picture, shown from
    that picture to the next, with nothing smoothed, resampled or held, so the drawn paw keeps the skeleton's speed
    and acceleration. The arms are drawn inside the body's groups, so an arm rides the body on the same picture;
    where a wrist is above its shoulder the arm is drawn in front of the head.
- Faces are held. An entry's `expression` is looked up in the fit's table before anything is sampled; an unknown name
  raises `ExpressionError`. The face switches where the routine's entries switch.
- A routine or move that needs feet raises `SupportError` on a fit without legs.
- `toon_head.figure` gains `arms=`: a callback that draws both arms itself into the body's group over the trunk and
  its group in front of the head, for desk poses only; each pose run records the two hands it draws (ADR 0174).
- `brush.stroke` takes any `brush.Profile` (anything with `at(s)`) as its pressure, so the dance can lay the torso's
  taper bone by bone without a new drawing; `Torso.drawn` draws an arm along a path the caller places.
- `draw(cv, parent, performance)` puts a performance on a canvas through `figure`. `ToonDance.measure` reads the groove
  from the projected head with `measure_dance`; `silhouette_series` reads it from rendered PNGs, so a proof checks the
  numbers and what the engine drew.
- `DOG_FIT` fits `toon-dog@2`, whose v2 drawing and head rig are approved. Its shoulder joints lie 24 to 26 reference
  pixels inside the drawn body; at rest its elbows, wrists and paws land on the desk arms within 0.004 px. It has no
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
- **The limbs package's arms (the first proof).** A tube of one width with a ball at every joint is a generic arm: it
  has neither the torso's taper nor its single ink line, and its shoulder joints sat outside the body. The operator
  refused it. Drawing the approved arm needs the torso's own stroke; the Toon adapter draws it, and the limbs
  package is not changed.
- **The approved arm's taper along the whole stroke.** `TAPER` runs along the arc's share; when a bone is drawn
  longer or shorter than at rest, the thin part slides along the arm, and a raised upper arm measured thinner than
  any the approved drawing draws. Laying it bone by bone keeps each bone's width.
- **Sampling limb motion through the limbs solver from sparse keys.** Keys interpolate between solved poses and drift
  from the skeleton between pictures; playing one solved pose per picture keeps the arm on the skeleton exactly.

## Consequences

- Any toon character with a head rig whose drawing has a torso can dance once someone writes its `ToonFit`; the fit
  is checked against the drawing, not trusted.
- The tests hold the arms to the approved drawing with bars measured on it: the shoulders at least as deep inside the
  silhouette as the approved arms' root; at rest an intersection over union with the approved arms no lower than the
  approved arms against themselves shifted by one reference pixel; mid-bone widths within the least and the most the
  approved drawing draws across its two-bone poses, on bones drawn at least as long as its shortest; the approved
  arm's layers and nothing more; and a drawn paw whose speed and acceleration over a beat match the skeleton's
  within what the drawing's 0.01 px rounding allows.
- A bone that points at the camera is drawn short; its width across its middle is then the bend's, which no approved
  pose shows. The proof page asks the operator to judge the arm pump for this.
- The dance draws one group per arm per picture that changes. The limbs package is not involved.
- The dance presets assume arms that hang at rest. On a desk rest pose, moves that lift the arms need a hold
  (`ToonFit.hold`) to reach the height the move means.
- Head-only moves (`head-nod`) move the `nod` channel and never rotate the head in the plane; a shimmy reads weakly from
  the front because its motion is mostly along the character's depth.
- The fit's crown lies about 32 reference pixels below the drawn crown. The groove is measured on the head joint and on
  the silhouette, so this does not change the check, but a move that reads the crown should not trust it.
- The proof is a candidate look. It merges only after the operator approves the rendered clip.
