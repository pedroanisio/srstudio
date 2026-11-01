---
generated-by: OpenAI Codex
---

# Reusable arm and hand performance

See the [library overview](../../README.md), [architecture decision](../decisions/0038-reusable-limb-performance.md),
and [requirements-to-verification map](limbs-verification.json).

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
When `fps` is omitted, baking follows the scene project's integer frame rate; without a project it uses 24 fps.
For a fractional project rate, choose an integer bake rate explicitly. Set `fps=` explicitly when a lower,
held-frame look is intentional. This also applies to interaction bakes and character limb tracks.
In the native backend, the arm's IK target, elbow pole and shoulder use the same held frames as the baked hand;
use the scene frame rate for the smoothest available motion.
Standalone compilation infers its duration from the latest action, root key or attachment release (`Motion.end`).
Entirely static motion defaults to one second. `BakeOptions(duration=...)` deliberately crops those tracks.
Character tracks clip root motion to the character's lifetime; actions and attachment releases must fit inside it.
Prepared character tracks reuse their numeric samples, projections and reports during drawing. Changed motion,
camera, timing or corrective inputs invalidate that preparation; IDs, budgets and adapter capabilities are still checked.

## Continue through a moving pose

Use `TransformTrack(interpolation="continuous")` for a root or contact target that should pass through its
interior keys. The default `"smooth"` mode still stops at each key. This standalone recipe moves through the
middle position without pausing:

<!-- continuous-track:start -->
```python
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.math3d import Frame, Vec3
from srstudio.limbs.motion import Motion, TransformKey, TransformTrack

track = TransformTrack(
    tuple(TransformKey(t, Frame(Vec3(0.2 * t, 0, 0))) for t in (0, 1, 2)),
    interpolation="continuous",
)
motion = Motion(ArmProfile(), HUMAN, root=track)
assert track.sample(1).origin == Vec3(0.2, 0, 0)
```
<!-- continuous-track:end -->

Each key can supply `velocity=Vec3(...)` in parent units/second and `angular_velocity=Vec3(...)` in local
radians/second. Missing interior velocities come from neighboring poses; endpoints default to zero. Translation
uses quintic segments with matching velocity and zero acceleration at keys. Rotation uses spherical cubic
segments with matching angular velocity; angular acceleration is not constrained. Excessive angular control
arcs are rejected before sampling: insert keys or reduce angular velocity. Velocities require continuous mode.

Sampling is independent of playback order. Outside the key interval, the nearest frame is held, even when an
explicit endpoint velocity is nonzero. Compiler output still follows its bake frame rate; continuous authoring
does not override an intentionally held-frame look. Motion JSON `1.2.0` and later preserve the mode and velocities.

## Chain gestures without returning to rest

`Motion.chain()` joins every adjacent action. It returns a new motion, replacing the first action's recovery
and the next action's preparation/stroke with a transition. The default window starts at the end of the first
action's hold and ends at the next action's stroke time. Outside that window, the original motion is unchanged.

<!-- action-chain:start -->
```python
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion

source = Motion(
    ArmProfile(), HUMAN,
    (Action("point", duration=2), Action("present", start=2, duration=2)),
)
motion = source.chain()
assert motion.sample(2).phase == "transition"
assert source.joins == ()
```
<!-- action-chain:end -->

For selected pairs, use `motion.chain(0, 2)`: each index identifies the action before a join. Existing explicit
windows are preserved. For custom timing, use `dataclasses.replace(motion, joins=(ActionJoin(0, start=1.4,
end=2.65),))`, importing `ActionJoin` from `srstudio.limbs.motion`. Times are motion seconds. Each endpoint
must lie inside its respective action; windows must be ordered, unique and nonoverlapping. A join can bridge
a gap between actions, and neighboring windows may touch.

The transition matches source wrist position, hand orientation, elbow plane and effective finger angles,
with boundary velocities estimated from the preserved source motion. Sampling order does not affect the
result. IK and the existing reach, wrist and finger limits still apply; a join can fail if its intermediate
poses are unreachable or its elbow plane becomes ambiguous. Such failures include `join_after` and
`phase="transition"` in their diagnostic context. Compilation checks sampled poses before scene emission.

Joins cannot replace an active contact. An explicit window can start at a contact's release and end at the
next contact's acquisition; held props continue following the sampled hand frame. Use an intermediate action
or different endpoints when a direct transition violates limits. Joins do not repair discontinuities in the
root track, guarantee matching acceleration/jerk, or certify anatomical or emotional plausibility. Keep root
motion continuous and inspect the compiled quality report and rendered movement. Output remains sampled at
the compiler's bake rate. Without explicit joins, actions retain their original return-to-rest behavior.

Build the same six chained gestures in Stick, Toon and Gloss, including strict motion JSON and numeric reports:

```sh
python examples/limbs_gallery.py ../generated/limbs/chained --chain
scene-render encode ../generated/limbs/chained/limbs-gallery.scene.xml
```

Add `--deformation skin` for planar native arm skinning or `--hand gripper` for the mechanical hand. Omitting
`--chain` keeps the gallery's original independent gestures. The chained skin example uses an explicit elbow
guide to keep one planar bend direction. Joining opposite elbow branches may require a spatial transition;
that motion needs the baked backend rather than native planar skinning.

## Time an expressive gesture to speech

The stroke can land on a specific word without manually calculating its project time. This example is standalone;
replace the sample `Take` with a recorded take from `ep.takes` and compile `motion` as above.

<!-- expressive-motion:start -->
```python
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion, MotionStyle, WordRef
from srstudio.timeline import Take

take = Take(
    "01", "actor", "wide", "No, no.", 3, 2,
    words=({"text": "No,", "start": 0.1, "end": 0.4},
           {"text": "no.", "start": 0.8, "end": 1.0}),
)
gesture = Action.on_word(
    "point", WordRef("01", 1), [take], duration=1,
    preparation=0.15, stroke=0.25, hold=0.35,
    style=MotionStyle(speed=1.2, overshoot=0.08, settling=0.15, arc=0.08),
)
motion = Motion(ArmProfile(), HUMAN, (gesture,))
assert gesture.stroke_at == 3.8  # take start plus the second word's relative start
```
<!-- expressive-motion:end -->

`start` and `duration` are seconds. `preparation`, `stroke` and `hold` are fractions of duration; their sum must
be below 1, leaving time for recovery, and stroke must be positive. `on_word` puts the end of the stroke at the
word's start and raises `LimbError` if the reference is ambiguous or the required preparation starts before zero.
Do not pass `start=` to `Action.on_word`; it derives the start from the word and rejects the conflicting option.
`MotionStyle` accepts amplitude 0–2, speed 0.25–4, and tension, overshoot, asymmetry, settling and arc 0–1. Tune
these to the character and preview the result: an exaggerated reaction and a quiet listening gesture need different
amounts of movement. The numeric report checks geometry and timing; it does not score emotional readability.
Set `preparation=0` to start a stroke at the resting pose without an anticipation. The `rest` action holds the
resting pose throughout its interval; a moving root or an explicitly declared contact can still move the hand.
Hand controls use a minimum-jerk envelope at the neutral and fully posed limits. Anticipation and reach
overshoot therefore do not start or stop finger curls with an abrupt velocity change; the wrist's authored
reach path remains independent of this hand-control envelope.
An explicit `Action.pole` is a world-space elbow guide. Its direction eases in during preparation (or the stroke
when preparation is zero), remains authored through the hold, and returns to the default during recovery.
The transition rotates the elbow around the reach axis, so an opposing pole can require spatial motion and the
baked backend. Settling eases in at the stroke-to-hold boundary and fades out before recovery, preserving velocity
continuity. Contact transitions with an authored pole blend wrist offsets relative to the moving arm.

Pole transitions track rotation winding across root and contact keys, including turns beyond 180° and repeated
turns. Preparation and recovery track their own winding, so recovery does not replay rotations accumulated
during the hold. Sampling order does not affect the result. Each transition prepares 32 samples between keys,
with a 100,000-sample limit; exceeding it raises `LimbError` with `code="budget"`.

`compiled.report.max_speed` and `max_acceleration` measure **wrist translation** in world canonical units per
second and per second squared. `max_elbow_speed` measures elbow translation; `max_hand_angular_speed` measures
the hand frame's rotation in radians per second. These are finite differences between sampled frames, not bounds
on unsampled motion. `bounds` describes projected geometry in the drawing parent's coordinate system.
`report.to_dict()` includes `metric_definitions` with each described metric's subject, space and units. These
numbers do not certify whole-body biomechanics or emotional readability.
Velocity samples belong to interval midpoints when computing acceleration, so a partial final frame does not
artificially inflate the acceleration report. Native IK, baked hand contours and interaction visibility share
the same six-decimal scene-time quantization, including frame-aligned offsets such as `1 / 24` seconds.

## Apply a character's motion quality limits

`BakeOptions(quality=QualityProfile(...))` checks authored limits before scene emission in native and baked
compilation, prepared character tracks, and interaction bakes. Profiles are opt-in and named for the character
or style. This example uses an existing `cv` Canvas; the limits are illustrative authoring choices, to be
calibrated against the intended performance:

<!-- quality-profile:start -->
```python
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.validation import QualityProfile

arm = ArmProfile()
profile = QualityProfile("presenter", max_speed=2 * arm.length, max_jerk=60 * arm.length, policy="warn")
compiled = compile_motion(
    cv, cv.comp, Motion(arm, HUMAN, (Action("point", duration=2),)),
    id="quality-point", backend="baked", options=BakeOptions(fps=24, quality=profile),
)
findings = compiled.report.quality_findings
```
<!-- quality-profile:end -->

Available limits cover wrist speed, acceleration and jerk; elbow speed; hand angular speed and acceleration;
reach residual; and obstacle penetration. `max_jerk` uses world units/second³ and angular acceleration uses
world radians/second². Differences carry interval-midpoint times, including nonuniform sampling. Each finding
contains its metric, measured value, limit, sample time, repair guidance and, for collisions, obstacle and arm
segment. `policy="warn"` preserves these findings in the report and compiler diagnostics; `"error"` raises a
`LimbError` with `code="quality.limit"` before drawing. Changed profiles invalidate prepared reports.

Derivatives require evidence: speed needs two samples, acceleration three, jerk four. An enabled limit with
too few samples produces `quality.evidence`, rather than passing on a default zero. Reports without a quality
profile retain zero defaults for unavailable measurements; those zeros are not proof of stillness.

For obstacles, pass `CollisionSphere(name, center, radius, parts=("upper", "forearm"))` in `profile.obstacles`
and set `max_penetration`. Centers and radii use world canonical units. The check measures sphere penetration
against arm-segment capsules of radius `arm.width / 2`; it does not check the hand mesh, infer the torso, detect
collisions between samples, or move the actor automatically. Choose obstacles and exclusions to represent the
intended contacts. At most 128 uniquely named obstacles and `max_collision_checks` segment/obstacle/sample
checks (default and maximum 1,000,000) are allowed. Budget exhaustion is an error even under warning policy.

These measurements support visual review. They do not certify anatomical plausibility, emotion or whole-body
balance, and thresholds are not universal across rigs or stylized animation.

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
and `strength` in 0..1 to blend toward a correction. A partial blend first resamples the original surface to match the artwork's
winding, starting point and arc-length spacing, so mirrored or opposite-winding artwork blends without folding.
Every corrected contour must be a simple polygon; self-intersecting artwork or a folded blend raises `LimbError`. Corrective contours affect only surfaces; fingertips,
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
A contact must start after its action starts, end before that action ends and leave a gap before the next
contact; the action eases the hand from rest into the lock and back out during those intervals. Contacts touching
an action edge or another contact raise `LimbError`. Contacts enforce reach and wrist limits. `props.clearance` separately reports arm-capsule penetration against
named spheres, or raises when `strict=True`; it does not silently displace a locked hand.
Transitions match the moving contact's linear and angular velocity at acquisition and release, and the resting
root's velocity at action boundaries. Tangents are estimated locally and blended with quintic corrections;
reach and wrist limits remain enforced throughout the transition.

An `Attachment` declares pickup and release times, an initial prop frame and a wrist-local grip offset.
Acquisition rejects position or orientation jumps. The prop follows the hand while attached and retains its
release frame afterward. `interaction.AttachedProp` exposes that lifetime as a reusable frame source.

For drawing, use `interaction.PropMesh` with named polygon `Face` surfaces in canonical spatial units.
`interaction.PropDrawing` pairs a mesh with a transform track or attachment. `interaction.Participant` pairs
a motion with its style, appearance and optional artist contours. `interaction.bake_interaction` projects all
participants and props through one camera, then sorts individual limb surfaces and prop faces together on
every frame. This lets fingers pass behind and in front of different prop surfaces. It returns each arm's
numeric report and the surface-depth order of every frame.

Without an explicit `BakeOptions(duration=...)`, the interaction lasts through the latest participant action,
root key, attachment release or built-in prop transform. A fully static interaction defaults to one second.
Custom frame sources must supply an explicit duration; the compositor cannot infer when arbitrary `sample()`
implementations finish. An explicit duration also lets an author deliberately crop a longer track.
When an attached prop is present and the scene continues after all known tracks, the final composited pose holds
through the scene's end. This adds one frame to the bake budget. If the scene has no duration, provide an explicit
`BakeOptions(duration=...)`; an explicit duration controls the interval without an automatic hold.

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
clip contains 72 frames at 1600×900 and 24 fps. Pass `--font` and `--font-license` when DejaVu Sans Bold is
not installed at any `srstudio.sample.SYSTEM_FONTS` path.

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

The following character builders accept `limbs=(track, ...)` directly. A track's `ArmProfile.side` names the
character's own arm in every style, so one right-hand track drives each character's anatomical right arm:

| Builder | Track camera coordinates | Facing | A right track replaces |
| --- | --- | --- | --- |
| `stick.rig` | Rig-pose pixel coordinates, before `at`, `scale` and `flip` | Profile, facing screen-right; `flip` turns it to face left | The near arm; with `flip`, the far arm |
| `gloss.nadia`, `gloss.gus`, `gloss.tamsin` | Person-local pixels relative to the feet, before `flip` | The viewer | The sleeve and hand on screen-left, flipped or not |
| `toon_cast.figure`, `dog`, `frog`, `bear`, `rabbit` | Toon reference pixels before `fx`/`fy` | The viewer | The paw and arm on screen-left |
| `cast.Manager`, `Candidate`, `Barista`, `Customer` via `Performance(limbs=...)` | Actor-local pixels before the actor's position and scale | The viewer | The arm, hand and held prop on screen-left |

Motions reach outward toward +x with the right arm and mirror a left arm's goals to -x. A profile Stick figure
faces +x, which is forward rather than sideways, so it reflects a left track about its shoulder and both arms
reach forward. A flipped figure mirrors its tracks with the rest of the figure, so they point the way it faces. A front-facing
character reflects each track about its camera origin, so the right arm reaches out to screen-left. A flipped
Gloss person mirrors its tracks back about its centre line, keeping each on its anatomical side. A Stick
far-arm track draws behind the torso, like the legacy far arm; an `Occlusion(..., layer="front")` still brings a
part forward. `integration.Facing` records each builder's facing and maps a side to the builder's legacy arm.

Character placement, flipping, Gloss walking/falling/bouncing and Toon lean/sigh placement carry the limb
tracks with the character. For a moving shoulder within a Stick pose sequence, author the corresponding
motion root track; the builder does not infer a spatial torso animation from held pose drawings.

Choose the track's camera origin at the shoulder of the named side, in the coordinates above before any flip:
for a front-facing character, the right shoulder is the screen-left one. Choose its scale to fit the
character. Retarget arm
width, proportions and hand topology as needed. Pass an `Appearance` matching the coat, sleeve or skin.
`examples/limbs_cast.py` supplies concrete placements for a Stick person, the Toon dog with a mitten hand,
and Gloss Nadia using the same pointing action. It exports each retargeted motion as JSON.

The builders validate duplicate sides, duration, reach, style and compilation before drawing the character.
A track cannot extend beyond the character's end. A single-side replacement preserves the other authored
arm, facial expressions, speech and character details. `limbs=()` retains the existing drawing path. Toon
also exposes `omit_arms=frozenset({"left", "right"})` on `figure_layers` and `figure_shapes` for callers that
compose character artwork as data.

The replacement arm holds its first pose before a track's offset and its final pose after the track ends,
through the character's lifetime. With an implicit duration, a root track continues moving the arm through its
last key or the character's end. An explicit duration crops the entire motion, including the root track.
Standalone `compile_motion` retains its explicitly requested interval.

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
in the wrist frame, including axial roll. FK and IK share one hand-frame convention: +Y follows the forearm and
+X is the elbow's hinge axis crossed with it, mirrored for the left arm. FK flexes each elbow toward its side's
lateral direction, as `reach` does with its default pole, so an FK pose solved back through `reach` with its
elbow as the pole returns the same hand frame on both sides.

The current writer emits `srstudio.limbs/1.3.0` motion documents. The reader also accepts `1.0.0`, `1.1.0` and `1.2.0`
documents and supplies the original smooth interpolation for tracks without the new fields. Documents without
explicit axes retain their original +X default. Explicit axes require at least `1.1.0`; transform interpolation
and velocity fields require `1.2.0`; action joins require `1.3.0`. Older documents without joins preserve their
return-to-rest behavior. Unknown versions and fields are rejected. All accepted versions pass through
the current numeric and resource validation.
Decoding errors retain the nested field path, including optional objects: an invalid target coordinate reports
`motion.actions[0].target.position.x` and the expected finite number, so an authoring agent can repair that field.
`load_motion` reads at most 5 MiB of UTF-8 and bounds array/object nesting to 64 levels before parsing, so
an oversized, deeply nested or non-UTF-8 file raises `LimbError` instead of exhausting the parser. Profile,
digit, action, contact, attachment and take identifiers are bounded to 128 characters. Custom digit labels
can contain spaces or Unicode; they do not become SVG paint IDs. Wrongly typed constructor input, such as a
number where a name, color, tuple or (digit, value) override belongs, raises `LimbError` (still a `ValueError`)
rather than a bare `TypeError` or `KeyError`.

Sampling failures retain `LimbError.code` and `residual` and add a JSON-compatible `context` dictionary.
It includes `time` in motion seconds, anatomical `side`, and, during an action, `action` and zero-based
`action_index`. Compilation adds `track` (the compiled limb ID or interaction participant name); numeric
limit failures identify `field`. The same context appears in the error text. Add `BakeOptions.offset` to
`context["time"]` when locating the failure on the project clock. Context that is not available is omitted.
Use these fields to repair the specific action and resample it before retrying compilation.

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

The examples resolve their font like the library: the first DejaVu Sans Bold in
`srstudio.sample.SYSTEM_FONTS`, shipped with the same DejaVu license note `srstudio.sample` writes. Custom
example fonts require both `--font` and `--font-license`. The examples do not attach the system
DejaVu sidecar to a caller-provided font. Supply the matching source license file; the example copies and
pins it alongside the font asset.

## Engineering comparison and blinded review

The evaluation example compares three complete characters performing matched tasks: Stick pointing, Toon
hands over the face, and Gloss shrugging. Each pair uses the same framing, duration, background and character.
Legacy versions hold named poses; spatial versions use continuous gesture phases. The tasks match intent,
not exact geometry or hand silhouettes.

```sh
export SRSTUDIO_LIMBS_REVIEW_SEED=...   # a private key chosen for this study; never commit or publish it
PYTHONPATH=src python examples/limbs_evaluate.py ../generated/limbs/evaluation \
  --engine ../generated/bin/scene-render
```

The example refuses to run without a review key from `--seed` or `SRSTUDIO_LIMBS_REVIEW_SEED`. Rebuild with
the same key to keep the trial mapping; a different key produces a different, unrelated packet.

`evaluation.json` records actual repeated build times, serialized scene bytes, node and shape counts, and
scene hashes. Builds must be byte-identical across repetitions and pass schema validation. Timings exclude
schema validation, serialization and rendering. Each measurement's `source_functions` lists the entry
function and every example function it reaches, with their line counts. The per-pair `source_comparison` counts
only lines one side reaches and the other does not, so helpers shared by both sides cancel. Library dependencies
are excluded. In this example the spatial builders reach the `_track` helper, so they count more lines than
the legacy builders. Line counts do not measure human authoring effort. Without separate human observations,
authoring time is explicitly unmeasured.

The `review/` directory contains opaque A/B clips, task descriptions, rating instructions and an empty
ratings template. Keep `private-key.json`, `scenes/` and the engineering report outside the review material.
There are no implementation names in the public trial manifest. The private key shuffles task order and,
separately, which half of the trials show the candidate as A, so neither side nor order follows from the trial
number. One shared packet does not counterbalance order across viewers.

Reviewers score task clarity, motion naturalness and fit with the drawing style from 1 to 5, then choose
A, B or a tie. Each reviewer uses one stable anonymous ID. The instructions show the record format; the
empty template contains no invented observations. Collect actual responses and run:

```sh
PYTHONPATH=src python examples/limbs_evaluate.py ../generated/limbs/evaluation \
  --ratings path/to/collected-ratings.json
```

This rebuilds the scene measurements and review metadata. Include `--engine` to regenerate the video clips.
`evaluation.parse_ratings` rejects unsupported schemas, unknown fields and invalid scores.
`evaluation.summarize` rejects unknown trials and duplicate reviewer/trial records. It reports counts and
means, with `awaiting_ratings` when empty and `partial` until every trial has at least five reviewers.
`complete` means that the collection quota is met; it does not establish statistical significance, reviewer
identity or a competitive advantage. Review identities are caller-supplied and are not independently verified.

Compiled `MotionReport.max_reach_error` records allowed reach clamping separately from bone-length and
contact errors. Compilation preserves aggregated anatomical diagnostics for baked, automatic and native
backends, so a clamped request cannot appear as a perfect target match merely because bone lengths are valid.

## Adding a drawing style

A style implements `adapters.Adapter`: a name, explicit `Capabilities`, and
`draw(cv, parent, pose, appearance, *, id)`. Register it once with
`register_adapter(name, adapter)` and pass that name to compilation or `LimbTrack`. Duplicate names are
rejected. The immutable `ProjectedPose` contains depth-ordered surfaces, centerlines, contour holes and
an authored-contour flag. A custom adapter can draw these directly or delegate to an existing treatment:

```python
from srstudio.limbs.adapters import Capabilities, adapter_for, register_adapter

class StudioInk:
    name = "studio-ink"
    capabilities = Capabilities()  # contour support; no native skin claim

    def draw(self, cv, parent, pose, appearance, *, id):
        return adapter_for("ink").draw(cv, parent, pose, appearance, id=id)

register_adapter(StudioInk.name, StudioInk())
```

Declare only capabilities the adapter implements. Perspective and native compilation enforce those
capabilities before emission. Keep anatomical solving and projection outside `draw`; a style receives the
same motion geometry as other adapters. Preserve holes and respect authored contours when applying surface
treatments, so a paint effect cannot reintroduce folded-finger outline crossings.

## Observed authoring effort

Build timing does not measure the time a person spends authoring a performance. The evaluation example
accepts separate human observations through `--authoring FILE`. Its report schema is now
`srstudio.limbs.evaluation/1.2.0`, which adds `source_functions` and `source_comparison` to the 1.1.0
report; the `authoring` summary replaces the former always-null
`human_authoring_seconds` field. With no observations, the summary says `awaiting_records` and has no results.
An empty `authoring-template.json` is written outside the blinded viewer packet. Existing authoring and
rating templates are preserved when rebuilding, including observations entered into those files.

Authoring input uses `srstudio.limbs.authoring/1.0.0`. Each record has `case`, `author`, `implementation`,
`seconds`, `completed`, and optional `notes`. Case and implementation must match the example's pairs:
`point` with `legacy-stick` or `spatial-stick`, `face` with `legacy-toon` or `spatial-toon`, and `shrug` with
`legacy-gloss` or `spatial-gloss`. Seconds must be finite, positive and at most 86400. Completion must be a
boolean. The parser rejects unknown fields and missing required data. The summary rejects duplicate
observations for the same author, task and implementation.

```sh
PYTHONPATH=src python examples/limbs_evaluate.py ../generated/limbs/evaluation \
  --authoring path/to/observed-authoring.json --ratings path/to/collected-ratings.json
```

Use the same task description, project assets and acceptance criteria for both implementations. Time one
attempt per author, task and implementation. Start when the author begins the task; count editing,
documentation lookup, debugging and active preview inspection. Pause for breaks and unattended rendering.
Stop when the rendered result meets the task or the author ends an unsuccessful attempt. Record unsuccessful
attempts with `completed: false`. Keep prior experience and deviations in the notes. Alternate which
implementation is attempted first across authors to reduce order effects; do not treat repeat exposure as
an independent first attempt.

Summaries report attempts, completions and failures separately. Means and medians use completed attempts
only. Paired differences use the same author's completed attempts on the same task and report candidate
seconds minus baseline seconds; a negative difference means the candidate took less time in that pair.
An unpaired attempt or failed attempt cannot become a successful paired comparison. These descriptive
observations do not authenticate authors, judge the completed videos or establish statistical significance.
