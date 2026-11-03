---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0188: Retarget mannequin motion by rotations, hold planted feet, warp it onto the beat

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The dance SDK has motion in one place and characters in another. `srstudio.motion_bridge` ([ADR
0187](0187-srlocations-motion-bridge.md)) reads srlocations' mannequin motion: per frame, the hips' place and each of
the 55 joints' turn on its parent from the T-stance, in srstudio's axes. `srstudio.skeleton` ([ADR
0185](0185-shared-skeleton.md)) poses any character on the same 55 joints, through each joint's own controls, with
each character's proportions, limits and omitted joints. `srstudio.dance` ([ADR 0186](0186-dance-moves-on-the-beat.md))
times moves on a `music.Groove`. Nothing turned a recorded take into a pose of a cartoon or a stick figure, or played
it to a song's tempo.

## Decision

`srstudio.retarget` reads a `MotionClip` into a profile's controls (`to_pose`, `retarget`), holds the feet the clip
plants (`plants`, `foot_slip`, the `lock_feet` flag), and moves the clip's beats onto a song's (`beat_map`, `perform`).

### Rotations into controls

A clip's turn of a joint and the skeleton's turn of the same joint start from two T-stances that differ only at the
thumbs: the joint table keeps the thumb's splay in the first thumb joint's `rest`, the clip keeps it in the rest
offsets of the bones it carries. With `B(j)` the product of the table's rests from the root down to joint `j`
(identity everywhere but the thumbs), the clip's offsets are the table's turned by the parent's `B`, which holds on
the fixtures to 5e-9 m. Then

    controls(j) = B(j)^-1 * clip_rotation(j) * B(j)

and the skeleton's own decomposition reads that turn into the joint's controls, about the table's axes, with their
signs and left-side mirroring, nearest a reference branch: the T-stance for a single pose, the frame before for a
sequence, so a turn past half a turn stays continuous. What the axes cannot hold is a residual in radians, reported per
joint with how often and how large; nothing is dropped unseen.

The hips' turn goes into the hips' own three controls; their translation channels stay at zero and the root frame
carries the clip's hips place, scaled by the ratio of the profile's pelvis height to the clip's. The clip's pelvis
height is the table's share of the reference height times the clip's own size, read from its thighs and shins, so a
clip of a taller figure scales too. Values are absolute turns from the T-stance, the skeleton's zero, so a profile's
`rest` is not added.

A value past the profile's limits is refused with `RetargetLimitError` listing each breach (time, control, value,
limits; the list bounded at 512 with the total counted), unless `clamp=True` holds it at the limit and the report
counts the samples, the worst excess and the first time. Clamping is opt-in because it changes the motion.

A joint the profile omits is dropped, and the report gives the largest turn the clip gave it. Folding its turn into a
kept neighbour is never needed: a profile omits by whole subtrees (an omitted joint takes everything it carries, and a
hand kind keeps the first bones of a digit), so no kept joint has an omitted ancestor and dropping moves no kept joint.
Folding into the parent would turn the parent's other children, so it would be wrong.

World rotations do not depend on bone lengths, so on any profile every kept joint turns in the world as the clip's
does; only positions follow the profile's proportions.

#### Measured

| What | Measured | Held by a test to |
|---|---|---|
| `world()` of the retargeted pose against the clip's `positions()`, every joint and frame of both fixtures, on `realistic` | 3.4e-8 m | 1e-6 m |
| Residual of any joint, any frame of either fixture | 8.4e-9 rad | below `RESIDUAL_FLOOR`, 1e-6 rad |
| A kept joint's world turn against the clip's, on `cartoon` and `stick` | under 1e-8 rad | 1e-7 rad |
| A knee turned 0.2 rad about z, which no knee control holds | 0.2 rad, reported on that joint and frame | 0.2 ± 1e-6 |

### Planted feet

On other proportions the hips travel the clip's path scaled by pelvis height while the legs are another length, so a
foot the clip holds still drifts: on the walk fixture, 4.27 mm on `cartoon` and 8.63 mm on `stick`.

A foot is planted in a frame where the clip's foot joint is within `PLANT_HEIGHT_M` (10 mm) of its standing height and
moves at most `PLANT_SPEED_M_S` (0.1 m/s), the faster of the steps into and out of the frame. On the walk, planted
frames read exactly 0 m/s and 2 mm under the standing height (the take stands on soft knees), and the lowest foot in
flight is 15 mm up and moving at 0.3 m/s or more, so the pair sits between the two: tightening both tenfold (1 mm,
1e-6 m/s) finds the same plants. Loosening them to 100 mm and 1 m/s would plant the rising heel of each push-off, so
they are not looser.

While planted, the character's foot joint is held at one point, the mean of where it would have stood over the plant,
and the leg is solved to reach it: the knee bends to the distance (`acos` of the triangle's sides, inside its stretch
limits), the thigh swings on the shortest arc onto the line, and the foot keeps the turn in the world the clip gives
it. The knee keeps its twist; the toes, carried by the foot, keep theirs. The hip and foot controls are read back by
the same decomposition and the same clamp or refuse rule. A target out of reach straightens the leg toward it, and each
hold reports its worst miss. Within `BLEND_S` (0.1 s) either side of a plant the hold eases in and out on a smoothstep,
so no foot jumps; the largest step a foot takes between frames is the unlocked one's within a millimetre. A side
without a whole leg (hip, knee, foot) is not held.

| On the walk fixture | Unlocked slip | Locked slip | Worst miss |
|---|---|---|---|
| `cartoon` | 4.27 mm | 0.45 mm | 0.45 mm: the cartoon's legs are short for its pelvis height, so a straight leg falls short |
| `stick` | 8.63 mm | 0.05 mm | 0.05 mm |

A test holds the locked slip under 1 mm and the unlocked over it on both presets, so it fails if the lock stops working.
On `realistic`, where the clip already plants its feet, the lock moves no joint more than 0.1 mm.

### Beat warp

`beat_map(clip, beats, song, start=, end=, per=)` pairs the clip's beats (seconds on its clock, or a `Groove` the clip
was made to) with the song's beats from `start` (a beat of the song, by default its first), one per `per` song beats
(0.25 to 4; 2 plays a 60 BPM take at 120). Between pairs the map is straight; before the first and after the last it
keeps the nearest stretch's rate out to the clip's ends, and it stops at the song's zero and at `end`. Both clocks rise
everywhere, so `clip_time` and `song_time` invert each other.

It refuses beats that are not finite and strictly rising, or more than 4,096 of them (`AnchorOrderError`); fewer than
two beats inside the clip, or a song that ends before the second (`EmptyOverlapError`); a stretch outside 0.5 to 2 clip
seconds per song second (`WarpRateError`), past which a recorded take reads as slow motion or fast-forward rather than
as dancing to the song; and a start off the song's grid by more than a millisecond, the tolerance `Groove.opens_bar`
uses, or `per` outside its range (`BeatWarpError`). The map's song length is therefore at most twice the clip's.

`perform(clip, profile, beats)` reads every frame once (refusing there a limit breach without `clamp`) and builds the
foot holds; `pose(song_s)` then maps the song second to the clip's clock, slerps each joint's turn and lerps the hips
between the two frames either side, reads the result with the frame before as the reference branch, and holds the
feet. On each song beat the pose equals the retargeted frame at the clip's beat. `frames(fps)` samples at most 14,400
pictures (eight minutes at 30 fps) up to 120 fps, with one report.

A joint with three controls holds every slerp exactly. A joint with two, such as a knee (stretch, twist), does not: the
slerp of two of its turns leaves its axes slightly. On the walk sampled at 60 fps the worst such residual is 0.0037 rad
at the knees, reported like any other residual, and a test holds it under 0.01 rad; the standing fixture has none.

### Errors

Every refusal is a `RetargetError` (an `SrstudioError`) with a code, the path that failed, what was found and what was
expected: `RetargetInputError` (`retarget.input`), `RetargetLimitError` (`retarget.limit`), and under `BeatWarpError`
(`retarget.warp`) `AnchorOrderError` (`retarget.anchors`), `EmptyOverlapError` (`retarget.overlap`) and
`WarpRateError` (`retarget.rate`). All but the base are also `ValueError`s. Loops run over a clip's frames (at most
7,200), a profile's joints, a plant's frames, a map's anchors (at most 4,096) and a bounded number of pictures; no
bound comes from the data.

## Rejected alternatives

- **Retargeting positions.** Matching each joint's position fixes a bone's direction but not its twist, and on other
  proportions every position is wrong by construction. Rotations keep every bone's direction and twist, and on the
  clip's own proportions reproduce its positions to 3.4e-8 m.
- **Folding an omitted joint's turn into a kept one.** A profile omits whole subtrees, so nothing kept lies below an
  omitted joint, and folding into the parent would move the parent's other children.
- **Scaling the root by stature or leg length.** The skeleton stands a character by its pelvis height
  (`standing_root`), and scaling by that keeps a standing clip's hips at the character's standing height. A scale by leg length alone would
  reach further on short-legged profiles, and the miss it would save on `cartoon` (0.45 mm) is reported instead.
- **Holding feet through `body.Step` plans or `skeleton.from_body_pose`.** `body` plans its own steps on a yaw-only
  root with flat soles, rather than following a recorded one, and `from_body_pose` spreads one torso turn along the
  spine by range, which would undo the spine the clip gives exactly. The hold solves only the leg in the skeleton's own
  controls and limits, and keeps every other value.
- **Interpolating control values between frames.** Mixing Euler-like values is not the shortest arc and wraps badly
  near half a turn; slerping the clip's turns and reading them back keeps three-control joints exact and reports the
  rest.
- **A free time warp, or dynamic time warping against the song.** The clip's beats are known; a piecewise-linear map
  through them is monotonic by construction and its rates are checkable, where an optimised warp could stall or race.

## Consequences

- Any recorded take of the mannequin plays on any profile, with what could not be held listed rather than hidden.
- A foot hold is quasi-static: it keeps a planted foot joint still; it does not plant a rising heel or a toe pivot, and
  a character whose legs are short for its pelvis height straightens and misses by the reported amount.
- `retarget` uses `srstudio.skeleton`'s private decomposition (`skeleton._rotation.decompose` and `angle_of`); the
  skeleton's owner is asked to make it public so the two cannot drift.
- The joint deltas of a `srstudio.dance` move are on canonical controls, so `skeleton.add` layers them on a retargeted
  pose; its root channels are in head radii and need the profile's head radius first.
