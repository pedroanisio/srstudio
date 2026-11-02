---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0214: A 2D dance track reaches a drawn figure through the shared skeleton, by bone direction, with named rules for what the picture cannot say

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The dance study ([ADR 0203](0203-dance-style-from-reference-video.md)) reads a real dancer from one camera. The tracker
writes a cleaned record, `dancepose.motion.clean`: fifteen joints per frame (head, neck, shoulders, elbows, wrists,
hips, knees, ankles, pelvis) as picture pixels, plain and stabilised, and nothing about depth. A record holds a real
person's motion frame by frame, so it stays on the machine that made it; only fitted numbers enter the repository.

Putting that motion on a drawn character needs three steps the library did not have:

1. reading the record as untrusted data, with typed errors;
2. lifting the 2D points onto the shared 55-joint mannequin, deciding by rule what one picture cannot say (depth,
   which way a foreshortened bone leans, the hinges' planes, the floor, the feet's direction);
3. driving the drawn figure from the lifted skeleton.

## Decision

### The reader: `srstudio.pose_clean`

`pose_clean.load`, `parse` and `from_data` read one strict JSON object (no NaN or Infinity, no repeated key, at most
64 MB) of exactly the record's fields. They refuse with `pose_track`'s typed errors a wrong shape, an unknown or
missing field, a wrong type, a number that is not finite, joints other than the fifteen in their order, bones other
than the fourteen, frames out of order or off the clock, a point more than one picture side outside the picture, and a
duration, source span or source time that disagrees with the frames. Every bound is a constant: 36,000 frames, 240 fps,
16,384 px a side.

### The lift: `srstudio.pose_lift.lift`

The camera is orthographic and level, looking at the dancer's front. One picture length per metre for the take, from
the full thigh and shin (the 0.95 quantile of each bone's picture length) against the mannequin's. A bone shorter in
the picture than its full length leans out of the picture's plane by the length it lost, `|dz| = sqrt(L^2 - l^2)`.

The sign of that lean is not in the picture. Each bone takes the common way (`DEPTH_SIGNS`: arms, thighs, torso and
head toward the camera, a shin away from its knee), except where a limb's upper bone would twist about itself by more
than `FLIP_COST` (0.35 rad) more than another of its four sign pairs; changing pair from the frame before costs the same
again, so a sign changes only where a twist demands it. Measured on the 60 s take (1,439 frames at 23.976 fps), against
always leaning the common way:

| upper arm | twist p50 | twist p95 | max | frames over 1 rad |
|---|---|---|---|---|
| left, common way only | 0.795 | 2.240 | 3.121 | 508 |
| left, with `FLIP_COST` | 0.361 | 1.262 | 2.065 | 158 |
| right, common way only | 0.818 | 2.359 | 3.134 | 561 |
| right, with `FLIP_COST` | 0.516 | 1.433 | 2.071 | 236 |

The legs never flip on that take (0 frames each); the arms take the other pair in 567 (left) and 544 (right) frames.

An elbow or knee bends in the plane of its two bones; under a 10 degree bend that plane eases to the frame before's.
The hips face the camera, turned only by the torso line; the hands follow the forearm; the feet stay level and forward
in the clip. The result is a `motion_bridge.MotionClip` whose source is `kind` "lifted", with the SHA-256 of the points
it was lifted from. A lifted clip is built in memory and never read from a record.

### Contacts: a local floor

`pose_lift.contacts` plants a foot where its ankle is within 6 cm of the floor, slower than 0.35 m/s, for at least
0.12 s. The floor is local: the lower ankle's lowest place within 1.2 s centred on the frame (`CONTACT_FLOOR_S`). A
dancer who steps toward the camera moves both feet down the picture. One floor for the whole take would put an entire
earlier stand in the air, and a test shows that case: one floor finds the first plant at frame 91 of 180, and the local
floor finds it at frame 0.

### The drive: bone direction, not the clamped retarget

The drawn figure is driven by each lifted bone's direction: every canon bone of the Stick is laid along its lifted bone
at the canon's own length, projected by the shot's camera. The figure keeps its proportions, and its limbs point where
the dancer's did. The library gives the lifted joints' world places (`MotionClip.positions`); the video's build lays
the bones and the foot locks on them.

Rejected: retargeting the lifted clip onto the Stick's controls (`retarget.perform`), which clamps each control to its
range. On the same take, resampled to 1,800 samples at 30 fps, the clamped controls were off by about 2.7 rad on
`upper_arm.down_up` in about 600 of the 1,800 samples, and by about 3.4 rad on twist in about 700. A dance whose arms
point somewhere else a third of the time is not the dance. The clamp is right for a character's own moves, which stay
inside its ranges. It is wrong for a reading of a person, who reaches past them.

### The feet's direction: `pose_lift.foot_headings`

The lifted hips hold no yaw, so the feet's direction has to come from the picture:

- **Facing.** The pelvis turns from the camera by `acos(w / W)`. `w` is the picture's hip width (left hip x minus right
  hip x: positive facing the camera, negative facing away). `W` is its 0.95 quantile over the take. The value passes a
  7-frame running median.
- **Direction.** The width gives no direction. A bent knee points the way the body faces, so a direction is read where
  both knees bow off their hip-ankle lines the same way by more than 4% of the leg's picture length (`KNEE_BOW`). A
  frame takes the reads within ±8 frames (`TURN_WINDOW`) when one way wins two to one or better. Elsewhere no turn is
  invented, and the feet face the camera.
- **Plants.** A planted foot holds the heading of its plant's first frame. A foot in the air keeps the heading it had
  when last planted. Before its first plant, a foot takes the first frame's heading.

Measured on the 60 s take:

- **The knee bow is a turn signal.** Where the width says 50–90 degrees, 239 of 242 bent-knee frames bow the same way;
  under 20 degrees, 5 of 73 do.
- **Read and signed share.**

  | | direction read | signed |
  |---|---|---|
  | night short cut (19.5 s) | 7.9% of frames | 26.5% |
  | whole take | 31.3% of frames | 47.8% |

The drawing turns the heading by the shot's yaw. `stick.RigPose.toes` (optional, `None` for every published pose) then
draws each foot along ankle→toe:

- foreshortened to `sin(heading)` of the 46 px canon run;
- no shorter than `FOOT_MIN` (23 px, the run at 30 degrees);
- splayed outward by up to `FOOT_MIN` where the run is near zero, so a foot aimed at the lens never draws as a dot.

A pose without toes draws the legacy 46 px forward and 4 px down, byte for byte.

The test names carry these thresholds: 4% of the leg, ±8 frames, two to one, the 7-frame median, 6 cm, 1.2 s.

## Consequences

- Any 2D track of these fifteen joints can drive a drawn figure without new code. Its limbs follow the dancer, at the
  cost of poses outside the character's control ranges, which the clamped retarget would have refused.
- What the picture cannot say stays visible as rules and counters (`in_depth`, `straight`, `flipped`, `read`,
  `signed`), never as tuned numbers hidden in a clip.
- The feet face the camera wherever no direction is read: 73.5% of the night short cut. The rig's splay keeps those
  feet readable; it does not claim a direction the picture did not give.
- The record and anything derived one to one from it stay out of the repository. The tests build their own tracks.

## Alternatives rejected

- **The clamped retarget** onto the character's controls: about 2.7 rad off on `upper_arm.down_up` in about a third of
  the samples (above).
- **One floor for the take**, for contacts: it misses every plant made off that floor's depth (the frame 91 against
  frame 0 case above).
- **Always leaning the common way in depth**: upper-arm twist p95 2.24 to 2.36 rad against 1.26 to 1.43 rad with
  `FLIP_COST`.
- **A foot direction from the hip width alone, with an assumed side**: it would turn every narrow-hip frame one way,
  inventing a twist the picture does not show.
