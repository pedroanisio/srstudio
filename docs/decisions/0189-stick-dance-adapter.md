---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0189: The Stick style dances through the shared skeleton, one rig pose a picture

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

[ADR 0186](0186-dance-moves-on-the-beat.md) holds dance moves as data on canonical joints, and `dance_pose` turns a
frame into a pose of any character's skeleton ([ADR 0185](0185-shared-skeleton.md)). No drawing style dances yet. The
Stick style is the first. Its figure, `stick.rig` ([ADR 0009](0009-stick-rig.md)), is a set of held pose
drawings: a `RigPose` of head, neck, hip, knees, feet, elbows and hands in frame pixels, and a `RigKey` for each pose
change, with a face per key.

The groove measured from the reference reel has to survive the drawing. At 129 beats a minute and 25 pictures a
second, the body drops in 0.19 s and rises in 0.26 s, and the sideways snap takes 0.12 s. A held pose at the style's
usual 12 drawings a second cannot show a 0.12 s stroke. The face is held for a phrase, and the head does not turn
inside a beat.

## Decision

`srstudio.stick_dance` reads a dance as the Stick rig draws it.

- **One rig pose for every picture.** `perform(source, groove, start, end)` samples a `Move` or `Routine` at `fps`
  (25 by default) and adds each frame onto a base pose with `dance_pose`. It projects the joints with
  `skeleton.project` through a front, orthographic camera at `stick.HEAD_R` pixels to the profile's head radius, and
  reads one `RigPose` from each picture. `draw` keys the rig once a picture, so the rig's key budget bounds the dance:
  `perform` refuses more than `MAX_KEYS - 1` pictures before sampling any.
- **The profile has the cast's bones.** The default profile is the `stick` preset of `srstudio.skeleton`, whose torso,
  arm and leg bones are the Stick cast's at `stick.HEAD_R` pixels to its head radius: a 333 px torso, arm bones of
  `stick.ARM` (155 px) and leg bones of 255 px, as `stick.STANDING` draws them. A standing figure then stands as tall
  as the cast's "stand". `perform` takes any profile.
- **Reading the joints.** The rig's head is the head circle's centre on the head bone, and the neck and hip are the
  `neck` and `hips` joints. The rig draws both arms from one shoulder point under the neck, so each arm is moved by the
  constant offset that puts its shoulder there in the base pose. A shrug and a raised arm still ride the body. Legs
  run from the hip point. The arm and leg on screen left are the rig's far pair.
- **Base poses.** `SEATED` puts thighs forward and shins down, and turns the arms out to the windshield's "sit".
  `STANDING_BASE` softens the knees, so a dance that drops the hips bends them. A seat dance sits and any other stands,
  unless `seated` says otherwise. The base pose's hips land on `hip`: `SEAT` (540, 1370) seated, which puts the neck on
  the windshield's "sit" neck, and standing on the point that puts the ankles on the room's floor (y 1700).
- **Planted feet.** `dance_pose` does not plant feet. The adapter keeps a mark for each foot from the picture it is
  planted until it lifts; a seated figure keeps both. A two-bone reach in 3D solves the knee toward the danced knee,
  or forward when that knee lies on the line. A foot is never drawn through the floor. A planted foot stays on its mark
  even when the leg falls short, and `reach` records the largest shortfall in pixels.
- **A raised arm does not take the shrug.** A dance's `shoulder.*` channels turn the whole arm about the shoulder. On
  an arm held up, seat-groove's 0.05 rad shrug swung the hand 0.70 head radius against the head's 0.38, where the
  reference reel's raised hand moved 0.32 against 0.50. The adapter fades a side's shoulder channels as that arm is
  held past horizontal (`upper_arm.down_up` above 0), to `SHRUG_RAISED` (0) at `RAISED_FULL` (π/4), so the raised
  hand rides the body and moves as the head does. A counter-shrug that would move it less was rejected: it swings the
  hand sideways (0.33 head radius at half a shrug against), which the reference does not show. Neither `dance.py` nor
  the move files change.
- **Faces by phrase.** `EXPRESSIONS` maps a routine entry's `expression` to a `stick.Face` looking at the viewer. The
  face switches only on the picture where an entry opens. A held head turn or nod in the entry's `hold` turns the face's
  look, `turn / (π/4)` and `-nod / (π/6)`, each clamped to -1..1. A name outside the table raises `ExpressionError`
  before anything is danced, and so does an unknown `rest_face`. A single `Move` is one phrase.
- **`stick.rig(held_faces=True)`.** The rig drew one face for every key and placed a blink only inside a key's span, so
  a body keyed every 0.04 s would draw a face a picture and never blink. The rig now takes `held_faces`. With it, a run
  of neighbouring keys with an equal face draws one face, one lips position and one blink track. The default is
  `False`, and published figures draw byte for byte as before (tested). This is the only change to `stick.py`.
- **The groove is checked on the drawing.** `StickDance.track("head", "up")` and `track("hip", "right")` give the
  drawn positions in head radii. `SEAT_GROOVE_BOB` and `SEAT_GROOVE_SWAY` must find no miss on them. The test reads
  rendered frames too: `head_centroids` decodes the engine's PNGs with ffmpeg and takes the centre of the skin pixels,
  inside a `box` when a frame holds several figures. The centre of two heads together moves with how many pixels of
  each read as skin, and a change of a few pixels in one head moves it by a share of the distance between them: on
  the car proof, the pooled sway reads 29 ms late while each head alone lands within 3 ms of the beat.
  For two bars of seat-groove, the head must cycle once a beat (± 0.02) and its low point and sideways extreme must land
  within 0.02 s of the beat, which is half a picture.
- **Errors.** `StickDanceError(SrstudioError, ValueError)` is the base. Its children are `ExpressionError` and
  `RenderedTrackError` (a frame that cannot be read, is too big, or has no head). Every loop runs over a count fixed
  before it starts.

Measured on the drawing, seat-groove reads 1.000 cycles a beat on both channels. The head drops in 0.198 s, rises in
0.267 s and moves 0.380 head radius peak to peak, with its low point 1 ms after the beat. The hips snap in 0.136 s and
return in 0.329 s over 0.200 head radius. From the engine's frames of a single figure, the bob reads 0.195 s down,
0.270 s up and 0.381 peak to peak, with its low point 2 ms after the beat. The sway reads 0.132 s and 0.333 s, with
its extreme 2 ms before the beat. On the car proof's engine frames, each friend's head read in its own half lands its
low point within 5 ms of the beat and its sideways extreme within 3 ms (0.38 and 0.20 head radius peak to peak).

## Rejected alternatives

- **Hold rig poses at the style's 12 drawings a second.** A held stroke lasts a whole number of drawings, 0.083 or
  0.167 s for the snap. Both fall outside the sway's 0.12 ± 0.025 s.
- **Tween between a few key poses.** The rig's keys hold by design (ADR 0009), and the limbs are drawn paths. Tweening
  them would be a new rig.
- **Draw the dance with `limbs` or `body` tracks.** Those are profile figures with their own anatomy records. The Stick
  cast is the rig, and a dance must look like the cast.
- **An adapter-only profile with the rig's bones.** The preset's arms reached 456 px against the rig's 310, its legs
  were 32 % longer than every standing pose the style has drawn and its torso 393 px against 333. Fixing that only in
  the adapter would leave every other user of the `stick` preset (retargeted takes, the three-plane views) drawing a
  figure that is not the cast.
- **Keep one face per key.** That gives 25 face drawings a second, and blinks could never land, because a blink needs
  more than its 0.14 s inside one span.
- **Plant the feet in `dance_pose`.** Contacts are the body's job, and the skeleton module is shared by every style.
  The adapter plants in its own pass and reports what it could not reach.

## Consequences

- A seated or standing Stick figure dances any preset or routine at any tempo. Its expressions and held head turns
  change by phrase.
- A dance costs one body drawing a picture: eight bars at 129 BPM are 373 groups of five strokes for each figure.
  `MAX_KEYS` bounds a single figure's dance to 13 minutes at 25 pictures a second.
- A standing figure's arms hang from the single shoulder point the rig draws, while the skeleton's shoulders stay
  1.77 head radii apart. The arm gestures are tuned for those shoulders: on the cast's arms `clap` crosses the hands
  by 0.44 head radius at intensity 1 and meets at 0.75, and `point-up` clears the crown by 0.74 head radius.
- A held raised arm keeps its height through a shrug, so a shoulder move (seat-groove, bounce, shoulder-roll,
  shoulder-shimmy) under a raised arm moves only the arm that hangs.
- The non-seat presets have no measured reference. Their numbers in the study are readings, not targets.
- Nothing merges on a look until the operator approves the proof clip.
