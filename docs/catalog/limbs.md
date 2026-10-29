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

## Prop contact and compositing

`Contact` locks a wrist or a named fingertip to a `TransformTrack`, including an optional prop-local anchor.
`props.Prop` supplies named anchors; `props.bind` returns a motion with a corresponding contact interval.
`props.Coordination` samples two arms and their shared moving props without requiring sequential playback.
Contacts enforce reach and wrist limits. `props.clearance` separately reports arm-capsule penetration against
named spheres, or raises when `strict=True`; it does not silently displace a locked hand.

An `Attachment` declares pickup and release times, an initial prop frame and a wrist-local grip offset.
Acquisition rejects position or orientation jumps. The prop follows the hand while attached and retains its
release frame afterward. `interaction.AttachedProp` exposes that lifetime as a reusable frame source.

For drawing, use `interaction.PropMesh` with named polygon `Face` surfaces in canonical spatial units.
`interaction.PropDrawing` pairs a mesh with a transform track or attachment. `interaction.Participant` pairs
a motion with its style, appearance and optional artist contours. `interaction.bake_interaction` projects all
participants and props through one camera, then sorts individual limb surfaces and prop faces together on
every frame. This lets fingers pass behind and in front of different prop surfaces. It returns each arm's
numeric report and the surface-depth order of every frame.

The compositor uses average surface depth. Split intersecting geometry into smaller faces when a single
surface would need two different depth orders. It does not implement a spatial depth buffer or resolve
physical collisions. Projection, reach, style capabilities, duplicate names and resource budgets are checked
before scene mutation. Supply `parent_transform` when the drawing parent has a nonidentity affine transform.

Run the complete contact example from the repository root:

```sh
PYTHONPATH=src python examples/limbs_contact.py ../generated/limbs/contact
../generated/bin/scene-render encode ../generated/limbs/contact/contact.scene.xml
```

The output includes the moving button press, a visibly lifted cup, wrist release, reusable motion JSON,
original prop meshes in the source example, a pinned font and numeric contact/anatomy reports. The default
clip contains 72 frames at 1600×900 and 24 fps. Pass `--font` and `--font-license` when the system DejaVu font
and its distribution license are unavailable.

## Native sleeve deformation

`compile_motion(..., deformation="skin")` requests a connected sleeve surface driven by the native
planar two-bone skeleton. The style draws a tapered, subdivided rest contour; each resulting sleeve shape
binds to that skeleton through the renderer's `skin` modifier. The hand and fingers retain their spatial
controls and deterministic baked contours. The returned backend is `native-skin`.

The explicit skin request requires an orthographic camera, a planar arm, an adapter declaring skin support,
and no separated layers or artist contour corrections. Unsupported combinations raise `LimbError` before
scene mutation. `backend="baked"` cannot satisfy a native skin request. Use the default `deformation="contour"`
for perspectives, separated body/head layers and corrective artwork. Existing actors can opt in with
`LimbTrack(..., deformation="skin")`.

All built-in vector adapters declare skin support. The engine uses automatic weights based on distance to
the rest bone segments. Those weights blend surfaces; the canonical motion report checks bone and contact
constraints rather than measuring the deformed sleeve's silhouette or volume. Native linear blend skinning
can narrow a sleeve at a bent elbow. Artist-corrected baked surfaces remain appropriate when that shape is
unacceptable. Explicit weight files in the engine use nearest-sample lookup rather than smooth interpolation;
the limb compiler does not emit them.

The renderer-enabled skin tests check actual sleeve pixels near the wrist and elbow at multiple poses,
including a mirrored parent. Build and encode the six-action, three-style skin demonstration with:

```sh
PYTHONPATH=src python examples/limbs_gallery.py ../generated/limbs/skin-gallery --deformation skin
../generated/bin/scene-render encode ../generated/limbs/skin-gallery/limbs-gallery.scene.xml
```

## Folded-finger silhouettes

Finger surfaces merge overlapping tapered phalanges into one contour. This avoids self-crossing ribbon
edges when a curled finger projects back across itself. Genuine enclosed holes are preserved and drawn
with even-odd fill. The operation changes the surface rather than the anatomical joints or contact anchors.
Artist corrective artwork replaces the entire affected contour, including any holes.

Shapely supplies polygon union and installs NumPy as a dependency. Install the test extra for its type stubs.
For focused limb coverage, use the source directory as the coverage target:

```sh
PYTHONPATH=src python -m pytest tests/test_limbs* --cov=src/srstudio/limbs --cov-branch
```

## Existing style characters

The following character builders accept `limbs=(track, ...)` directly:

| Builder | Track camera coordinates | Replaced legacy arm |
| --- | --- | --- |
| `stick.rig` | Rig-pose pixel coordinates, before `at`, `scale` and `flip` | Left means far arm; right means near arm |
| `gloss.nadia`, `gloss.gus`, `gloss.tamsin` | Person-local pixels relative to the feet | Named left or right sleeve and hand |
| `toon_cast.figure`, `dog`, `frog`, `bear`, `rabbit` | Toon reference pixels before `fx`/`fy` | Named left or right paw and arm |

Character placement, flipping, Gloss walking/falling/bouncing and Toon lean/sigh placement carry the limb
tracks with the character. For a moving shoulder within a Stick pose sequence, author the corresponding
motion root track; the builder does not infer a spatial torso animation from held pose drawings.

Choose the track's camera origin at the desired shoulder and its scale to fit the character. Retarget arm
width, proportions and hand topology as needed. Pass an `Appearance` matching the coat, sleeve or skin.
`examples/limbs_cast.py` supplies concrete placements for a Stick person, the Toon dog with a mitten hand,
and Gloss Nadia using the same pointing action. It exports each retargeted motion as JSON.

The builders validate duplicate sides, duration, reach, style and compilation before drawing the character.
A track cannot extend beyond the character's end. A single-side replacement preserves the other authored
arm, facial expressions, speech and character details. `limbs=()` retains the existing drawing path. Toon
also exposes `omit_arms=frozenset({"left", "right"})` on `figure_layers` and `figure_shapes` for callers that
compose character artwork as data.

```sh
PYTHONPATH=src python examples/limbs_cast.py ../generated/limbs/cast
../generated/bin/scene-render encode ../generated/limbs/cast/cast.scene.xml
```

## Coordinating two arms

`props.crossed_arms(right_profile, left_profile, front="right")` creates a reusable pair of crossed-arm
motions. It uses the shoulder span to aim the wrists across the torso and assigns different spatial depths
to the two arms. `front="left"` reverses their depth order. `start`, `duration` and `hand` customize the pair;
strict reach and joint limits still apply to the supplied anatomy. The single-arm `crossed` action is also
available through `Action` and `legacy_action`.

`props.grip_prop(right_motion, left_motion, prop, right_anchor=..., left_anchor=..., start=..., end=...)`
binds two hands to distinct named anchors on one moving prop and returns a `Coordination`. The prop's
transform controls both contacts; it does not derive a separate prop animation from each hand. The motions
choose the finger controls, so the same helper supports a grasp or a palm-up tray support.

`Coordination.sample(time)` returns both arm samples, prop frames and collision diagnostics. Sampling after
a seek or in reverse order has the same result as forward playback. Collision checks include conservative
arm capsules against each other and against supplied spheres. They exclude fingers and full prop meshes.
`strict_clearance=True` raises `LimbError` on a reported penetration. The checker reports the requested pose
rather than moving a contact-constrained hand to hide a conflict.

The two-arm example includes a torso, an illustrated head, crossed arms and a tray lifted and tilted by two
hands. Its camera-facing head keeps facial artwork ordered under the tilted camera; the torso, arms and tray
retain spatial perspective. It writes both motions for each interaction and reports anatomy, contact and
collision measurements.

```sh
PYTHONPATH=src python examples/limbs_bimanual.py ../generated/limbs/bimanual
../generated/bin/scene-render encode ../generated/limbs/bimanual/bimanual.scene.xml
```

## Custom hinge mechanics and persisted data

Each `DigitProfile.bend_axis` is a unit vector in that digit's local joint frame. The human, mitten, paw and
three-finger presets retain +X flexion. The gripper uses opposing ±Z axes with its own flexion limits, so its
jaws close toward one another rather than curling together. Custom profiles can change the axis, lengths,
splay and per-joint limits; controls still enforce those limits. FK preserves the supplied shoulder rotation
in the wrist frame, including axial roll.

The current writer emits `srstudio.limbs/1.1.0` motion documents. The reader also accepts `1.0.0` documents
without explicit axes and supplies their original +X default. Explicit axes require `1.1.0`; unknown versions
and fields are rejected. Both versions pass through the current numeric and resource validation. Profile,
digit, action, contact, attachment and take identifiers are bounded to 128 characters. Custom digit labels
can contain spaces or Unicode; they do not become SVG paint IDs.

Resolved bake durations are checked against frame budgets before arithmetic can overflow. The six-decimal
scene clock must be able to represent every emitted interval. Invalid or under-resolved intervals, large
offsets that lose clock precision, nonfinite derived lengths and nonfinite projections raise `LimbError`
before scene emission. A zero outline width disables outlines in every adapter. RGBA material alpha is
preserved by Gloss shading. Collage applies the same affine treatment to a contour and its holes so its
surface treatment retains their topology.

The style gallery accepts every built-in hand profile:

```sh
PYTHONPATH=src python examples/limbs_gallery.py ../generated/limbs/gripper-gallery --hand gripper
../generated/bin/scene-render encode ../generated/limbs/gripper-gallery/limbs-gallery.scene.xml
```

Custom example fonts require both `--font` and `--font-license`. The examples do not attach the system
DejaVu sidecar to a caller-provided font. Supply the matching source license file; the example copies and
pins it alongside the font asset.
