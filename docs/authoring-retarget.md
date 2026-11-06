---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# Recorded motion on any character, on the beat

Back to the [authoring reference](authoring-reference.md).

`srstudio.retarget` plays a mannequin take from srlocations on any character's skeleton and to any song's tempo. A
`motion_bridge.MotionClip` ([ADR 0187](decisions/0187-srlocations-motion-bridge.md)) gives each canonical joint's turn
per frame. `retarget` reads those turns into a `skeleton.SkeletonProfile`'s controls
([ADR 0185](decisions/0185-shared-skeleton.md)), holds still the feet the clip plants, and `perform` moves the clip's
beats onto a `music.Groove`. The decision, the thresholds and the measured tolerances are in
[ADR 0188](decisions/0188-retarget-mannequin-motion.md).

## Retarget a take and play it to a song

`MOTION_RECORD` is the path of a record written by `tools/motion_export.py`; the recipe below is run by the test suite
on the walk fixture, a 2-second take stepped at 120 BPM.

<!-- retarget-recipe:start -->
```python
from srstudio import motion_bridge, music, retarget, skeleton

clip = motion_bridge.load(MOTION_RECORD)
toon = skeleton.preset("cartoon")

walk = retarget.retarget(clip, toon)  # one SkeletonPose per clip frame, planted feet held
assert len(walk.poses) == clip.frame_count
assert walk.report.clamped == ()  # nothing past the cartoon's limits
assert walk.report.worst_residual_rad < 0.01  # every turn the clip makes, the controls hold
for held in walk.locks:
    assert held.worst_miss_m < 0.001  # each planted foot stays within a millimetre of its spot

song = music.Groove(129)
beats = retarget.beat_map(clip, music.Groove(120), song)  # the take's beats onto the song's
dance = retarget.perform(clip, toon, beats)
song_s, clip_s = beats.anchors[1]  # the song's second beat and the take's, 0.5 s in
assert clip_s == 0.5 and dance.pose(song_s) == walk.poses[15]  # on a beat, exactly the retargeted frame

shots = dance.frames(30)  # a pose every 1/30 s of the song, with one report
assert len(shots.poses) == len(shots.times_s)
```
<!-- retarget-recipe:end -->

## What each step guarantees

- **Rotations, not positions.** Each joint's turn is read into its own controls about the table's axes, with their
  signs and left-side mirroring. On the mannequin's proportions (`realistic`) forward kinematics of the result lands
  every joint where the clip does, within a micrometre. On other proportions every kept joint turns in the world as
  the clip's does; only the positions follow the character.
- **The root.** The hips travel the clip's path scaled by the ratio of the profile's pelvis height to the clip's.
  `report.root_scale` gives the ratio.
- **Limits.** A turn past the profile's limits raises `RetargetLimitError` listing every breach by time, control,
  value and limits. `clamp=True` holds those values at the limits instead, and `report.clamped` lists each control
  with its sample count, worst correction in radians and first time on the clip clock.
  Separately, spline overshoot between two legal source frames is always held inside the limits, even with
  `clamp=False`. `report.interpolation_clamps` records these corrections with the same `Clamp` fields:
  `key`, `samples`, `worst_rad`, and `first_s` (clip seconds). Inspect both collections when accepting a take.
  `performance.sample(song_s)` reports one sample; `performance.frames(fps)` aggregates the samples it evaluates.
  An empty collection certifies only those samples. Limit clipping can introduce velocity or acceleration jumps;
  the unconstrained spline's continuity does not guarantee continuity after clipping or foot locking.
- **Omitted joints.** A joint the profile omits (the stick figure's toes, eyes and jaw) is dropped and listed in
  `report.dropped` with the largest turn the clip gave it. Profiles omit whole subtrees, so no kept joint moves.
- **Residuals.** A turn a joint's controls cannot make is listed in `report.residuals` in radians. Between frames, a
  knee (two controls) leaves a few thousandths of a radian, also listed.
- **Planted feet.** `retarget.plants(clip)` finds the spans in which a foot is down and still, by
  `PLANT_HEIGHT_M` and `PLANT_SPEED_M_S`. With `lock_feet=True` (the default) the leg is solved so the foot stays on
  one spot through each span, easing in and out over `BLEND_S`. `walk.locks` gives each hold's spot and worst miss,
  and `retarget.foot_slip(profile, poses, plants)` measures what a foot still slides. Pass `planted=` to use your own
  spans, or `lock_feet=False` to keep the raw rotations.
- **The beat.** `beat_map(clip, beats, song, start=, end=, per=)` pairs the clip's beats, as seconds or as the
  `Groove` the take was made to, with the song's from `start`, one per `per` song beats. The map eases its rate
  between beats and rises everywhere, so `clip_time` and `song_time` invert each other. It refuses beats out of order
  (`AnchorOrderError`), fewer than two beats in both spans (`EmptyOverlapError`), a stretch outside `MIN_RATE` to
  `MAX_RATE` (`WarpRateError`) and a start off the song's grid (`BeatWarpError`).

### Check playback-rate continuity

The permitted playback-rate range can leave a speed jump at an interior beat. `beats.rate_continuous` is false
when this happens; `beats.rate_jumps` contains immutable `retarget.RateJump` records in song-time order, with
`song_s`, `left_rate` and `right_rate`. Rates use clip seconds per song second. These are analytic one-sided
limits, independent of render fps; differences within four ulps of the larger rate are treated as rounding noise.
Only beats strictly inside `start_s..end_s` count, so this does not guarantee a smooth start or stop against a hold.

`beats.max_rate_change` is a conservative absolute derivative bound in clip seconds per song second squared for
a continuous map, and `math.inf` when a reported jump prevents a finite bound. For example, clip beats
`[0, 0.25, 1.25]` on a 120 BPM song jump from 0.5 to 2.0 at song second 0.5 and have an infinite bound.
An agent requiring continuous playback should reject such a map and revise its beat pairing, tempo or `per`,
then inspect the rebuilt map. Continuity of the time map alone does not certify joints, foot locks or rendered motion.

For strict JSON, preserve the continuity flag and jump evidence and encode the unbounded value as `null`:

```python
import json
from dataclasses import asdict

evidence = {
    "rate_continuous": beats.rate_continuous,
    "max_rate_change": beats.max_rate_change if beats.rate_continuous else None,
    "rate_jumps": [asdict(jump) for jump in beats.rate_jumps],
}
print(json.dumps(evidence, allow_nan=False))
```

## Repairing a refusal

Every refusal is a `retarget.RetargetError`, an `SrstudioError` whose `code` and `path` name what to change, and all
but the base are `ValueError`s. Bound any retry in your own code.

| Code | Means | Repair |
| --- | --- | --- |
| `retarget.input` | An argument of another type or out of its bounds | Fix the argument named by `path` |
| `retarget.limit` | The take turns a control past the profile's limits | `clamp=True`, or widen the profile's limits |
| `retarget.anchors` | Clip beats not finite and strictly rising | Sort and clean the beat list |
| `retarget.overlap` | Fewer than two beats inside both the clip and the song span | Use a longer span or more beats |
| `retarget.rate` | A stretch would play the take too slow or too fast | Pick a nearer tempo or change `per` |
| `retarget.warp` | A start off the song's grid, or `per` out of range | Start on `song.at(n)`; keep `per` in range |
