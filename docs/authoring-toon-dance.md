---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# Toon characters dance

Back to the [authoring reference](authoring-reference.md).

`srstudio.toon_dance` puts a [dance](authoring-dance.md) on a Toon character's approved head rig, through the
[shared skeleton](authoring-skeleton.md). The decision is [ADR 0190](decisions/0190-toon-dance-adapter.md).

## Dance a Toon character

```python
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, dance, toon_dance
from srstudio.music import Groove

groove = Groove(129)
fit = toon_dance.DOG_FIT  # toon-dog@2's skeleton, measured on its drawing
raised = fit.hold(
    {
        "left_upper_arm.down_up": 1.2,
        "left_upper_arm.front_back": 0.0,
        "left_upper_arm.twist_in_out": 0.0,
        "left_lower_arm.stretch": -0.3,
    }
)
moves = dance.moves()
routine = dance.Routine(
    8,
    (
        dance.Entry(0, 4, moves["seat-groove"], expression="grin"),
        dance.Entry(4, 8, moves["seat-groove"], transition_beats=1, expression="grin", hold=raised),
    ),
)
end = groove.at(8)
performance = toon_dance.perform(fit, routine, groove, 0.0, end)
assert dance.SEAT_GROOVE_BOB.misses(performance.measure("bob")) == ()
assert dance.SEAT_GROOVE_SWAY.misses(performance.measure("sway")) == ()

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="25", duration=end, background=PEACH.background)
cv = Canvas(scene, PEACH, width=1080, height=1920, font_asset=None)
toon_dance.draw(cv, cv.comp, performance)  # body, held faces and the drawing's own arms on its head rig
```

`perform` reads every picture three ways. The hips and spine become one transform of the whole figure about its seat.
What the neck and head do beyond that becomes the rig's `turn`, `nod` and `face_x`, inside its envelope or refused with
`HeadReachError`; pass `clamp=True` to clamp and count in `performance.clamped`. The arms are the approved drawing's
own arms posed on the skeleton's bones: the torso's tapered coat stroke over one ink line, rooted inside the body, the
taper laid bone by bone, and the character's own paw. Each picture draws its arm where the skeleton has it, nothing
smoothed or held, so a raised arm rides the body on the same picture and each gesture keeps its timing.

An entry's `expression` names a face in the fit's table (`fit.faces`) and is held for the entry; an unknown name raises
`ExpressionError` before anything is sampled. A dance that needs feet raises `SupportError` on a seated character.
`fit.hold` turns absolute control values into the deltas an entry's `hold` adds: the presets assume arms that hang at
rest, so on a desk rest an arm that should rise needs one.

## Check the groove on rendered pictures

`performance.measure(axis)` reads `bob` or `sway` from the projected head. `silhouette_series(pictures, background,
radius)` reads the same two series from rendered pictures (RGB arrays), as the coverage-weighted centroid of everything
that is not the background, in head radii. Hand either series to `dance.measure_dance` with a `DanceTarget`, and the
groove is checked on what the engine drew. `examples/toon_dance.py` builds the proof clip and does both.
