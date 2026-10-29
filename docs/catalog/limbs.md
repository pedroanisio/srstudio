---
generated-by: OpenAI Codex
---

# Reusable arm and hand performance

See the [library overview](../../README.md) and [architecture decision](../decisions/0035-reusable-limb-performance.md).

Build a motion once, then choose its camera and style when compiling it:

```python
from srstudio.limbs import HUMAN, ArmProfile, Camera
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.motion import Action, Motion

motion = Motion(ArmProfile(), HUMAN, (Action("point", duration=2),))
compiled = compile_motion(
    cv, cv.comp, motion, id="presenter-right", style="toon",
    camera=Camera(origin=(400, 300), scale=180),
    options=BakeOptions(fps=24),
)
```

`cv` is an existing `srstudio.Canvas`. Positions are canonical spatial units; camera scale converts them to
pixels. Arm lengths, the shoulder anchor and the hand profile are independent of the style. The compiler
returns the selected backend, numeric motion report and any automatic fallback diagnostic. Use `backend="native"`
to require native planar IK, or `backend="baked"` to require frame-held contours.

## Artist contours

A `ContourCorrection` replaces a named projected surface with original artwork. Coordinates are canonical
units relative to the wrist: X is lateral and Y follows the projected hand axis. The drawing is camera-facing,
so an artist can preserve a readable side-view silhouette without changing the spatial skeleton. Keys use
camera-space palm-normal Z: -1 is back, 0 is edge-on, and +1 is palm-facing. The compiler interpolates
corresponding vertices continuously between ordered keys and clamps beyond the supplied endpoints.

```python
from srstudio.limbs import ContourCorrection, ContourKey

palm = ContourCorrection("palm", (
    ContourKey(-1, ((-.12, 0), (.12, 0), (.17, .36), (-.17, .36))),
    ContourKey(0, ((-.05, 0), (.05, 0), (.07, .36), (-.07, .36))),
    ContourKey(1, ((-.12, 0), (.12, 0), (.19, .36), (-.19, .36))),
))
compiled = compile_motion(
    cv, cv.comp, motion, id="authored-right", style="toon",
    camera=Camera(origin=(800, 300), scale=180), correctives=(palm,),
)
```

Keep vertex order, winding and semantic correspondence across keys. Use `mirror=True` for mirrored artwork,
and `strength` in 0..1 to blend toward a correction. Corrective contours affect only surfaces; fingertips,
contact anchors, joint limits and bone lengths retain their canonical positions. Artwork must fit the intended
hand controls and topology. Corrections can name `palm`, `digit:index`, another digit, `upper` or `forearm`;
unknown or duplicate parts fail before scene mutation. Toon respects authored contours instead of replacing
them with its procedural brush outline. Corrected performances use the baked backend.

For existing supported actors, pass the same corrections through `LimbTrack(correctives=(palm,), ...)` in
`Performance(limbs=(track,))` or `Episode.perform(..., limbs=(track,))`. Legacy arm flags cannot be combined
with replacement tracks. A single track replaces only its named side.
