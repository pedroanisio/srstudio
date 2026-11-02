---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# Make a Stick figure dance

Back to the [authoring reference](authoring-reference.md).

`srstudio.stick_dance` draws a [dance](authoring-dance.md) with the Stick style's rig. A dance is read once for each
picture through the shared skeleton, and the face is held for each phrase. The decision is in
[ADR 0189](decisions/0189-stick-dance-adapter.md).

## Two friends in a car

<!-- stick-dance:start -->
```python
from srstudio import dance
from srstudio import stick_dance as sd
from srstudio import stick_windshield as sw
from srstudio.music import Groove

groove = Groove(129)
moves = dance.moves()
end = 8 * groove.bar
raised = (("left_upper_arm.down_up", 2.0), ("left_lower_arm.stretch", 0.8))
noor = dance.Routine(8, (
    dance.Entry(0, 4, moves["seat-groove"], expression="smile"),
    dance.Entry(4, 8, moves["seat-groove"], transition_beats=1, expression="grin", hold=raised),
))
passenger = sd.perform(noor, groove, 0.0, end)          # seated: seat-groove is a seat move
driver = sd.perform(moves["seat-groove"], groove, 0.0, end, rest_face="cool")

assert dance.SEAT_GROOVE_BOB.misses(dance.measure_dance(passenger.track("head", "up"), 25, groove)) == ()

# on an Episode's canvas cv:
# sw.windshield(cv, cv.comp, end, speed=0)
# sd.draw(cv, cv.comp, passenger, look=sw.NOOR, at=sw.PASSENGER_AT, prefix="noor", blinks=(1.3, 4.4))
# sd.draw(cv, cv.comp, driver, at=sw.DRIVER_AT, prefix="dev")
# sw.dashboard(cv, cv.comp, end)
```
<!-- stick-dance:end -->

`perform` returns a `StickDance`. It holds one `stick.RigPose` for each picture and the face held from each phrase's
first picture. `draw` gives it to `stick.rig` with `held_faces=True`, so the face and its blinks hold for the phrase while
the body changes every picture. Give each figure its own `prefix`, because the pose names have to differ.

## Standing

A move that is not `seat` stands. Planted feet keep their marks on the floor, and the knees bend to reach them:

```python
solo = dance.Routine(16, tuple(
    dance.Entry(8 + 2 * i, 10 + 2 * i, moves[name], transition_beats=1 if i else 0)
    for i, name in enumerate(("bob", "sway", "arm-pump", "step-touch"))
))
standing = sd.perform(solo, groove, 8 * groove.bar, 16 * groove.bar)
# sd.draw(cv, room, standing, end=16 * groove.bar)  # keys land on the time the dance was performed from
print(standing.reach)  # the farthest, in pixels, a planted foot fell short of its mark
```

A routine's bars count from the track's start. When the dance starts later in the reel, put its entries on those bars
and perform from that time.

## What to set

| Argument | Default | Sets |
|---|---|---|
| `profile` | `PROFILE` | The skeleton: the `stick` preset, which has the cast's torso, arm and leg bones. Any `SkeletonProfile` works. |
| `seated` | from the move | `True` uses `SEATED` and `False` uses `STANDING_BASE`, both deltas on the profile's rest. |
| `base` | none | Your own deltas in place of those. |
| `hip` | `SEAT`, or the floor | Where the base pose's hips land in frame pixels. |
| `fps` | 25 | Pictures a second, one rig key each. |
| `rest_face` | `"neutral"` | The face between phrases and for a single move. |
| `clamp` | `True` | A value past a joint's limit is clamped instead of refused. |
| `max_frames` | `MAX_KEYS - 1` | The bound on pictures, checked before any is sampled. |

An arm held past horizontal does not take a dance's shrug: its side's `shoulder.*` channels fade to `SHRUG_RAISED` at
`RAISED_FULL`, so a raised hand rides the body as the head does instead of swinging further.

`EXPRESSIONS` names the faces a phrase can hold: `neutral`, `smile`, `grin`, `eyes-closed`, `smirk`, `cool` and
`surprised`. Any other name raises `ExpressionError`. A held `head` or `neck` `turn_left_right` or `nod_down_up` in an
entry's `hold` turns the face's look for that phrase.

## Check the drawing

`track("head", "up")` and `track("hip", "right")` are the drawn positions in head radii, ready for `measure_dance`. To
read rendered frames, render PNGs with the engine and pass them to `head_centroids`. It returns the centre of the skin
pixels in each frame. Divide by the rig's head radius in pixels (`stick.HEAD_R` times your `scale`) before you measure.
A frame with no head raises `RenderedTrackError`.

`examples/dance_stick/dance_stick_study.py` builds the proof clip. It has two friends in a car and a standing routine,
and it writes the numbers beside the clip.
