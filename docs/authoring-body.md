---
generated-by: OpenAI Codex (GPT-6)
---

# Whole-body support and stepping

Back to the [authoring reference](authoring-reference.md).

`srstudio.body` coordinates an authored pelvis and torso with two spatial legs.
Planted soles retain their world anchors while the root moves. Use `compile_body`
for typed Python scores or `parse_body` for closed data-only input. Inspect
`plan.describe()` for units, supported anatomy, sampling and work limits.

<!-- body-recipe:start -->
```python
from srstudio import body
from srstudio.limbs import Camera, Frame, Vec3

score = body.BodyScore(
    duration=4,
    roots=(
        body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),
        body.BodyKey(1, Frame(Vec3(-0.15, -0.88, 0))),
        body.BodyKey(2.5, Frame(Vec3(-0.15, -0.88, 0))),
        body.BodyKey(4, Frame(Vec3(0, -0.88, 0.1))),
    ),
    stance=(
        body.FootAnchor("left", Frame(Vec3(-0.12, 0, 0))),
        body.FootAnchor("right", Frame(Vec3(0.12, 0, 0))),
    ),
    steps=(body.Step("right", 1.25, 2.25, Frame(Vec3(0.12, 0, 0.2))),),
)
plan = body.compile_body(score)
pose = plan.sample(1.75)
assert pose.legs[0].planted and not pose.legs[1].planted
assert pose.legs[0].sole == score.stance[0].frame
assert plan.window(1.5, 3).sample(0.25) == pose
# plan.window(1.5, 3).place(ep.cv, ep.comp, at=0,
#     camera=Camera(origin=(540, 1600), scale=700), fps=24, style="solid")
```
<!-- body-recipe:end -->

All spatial values are meters, angles are radians and timestamps are original
performance seconds. The axes are x right, y down and z anatomical forward (toward
the viewer in the shared camera convention). Ground is the horizontal plane y=0.
The root is the pelvis center. A sole frame sits on the ground, below its ankle;
rotations of the root and soles are yaw-only. `BodyKey.torso` is a rotation relative
to the root. Samples expose the root, torso, both shoulder frames, leg joints,
sole frames, active support polygon, mass proxy and signed support margin.

The default profile is authored stylized anatomy, not measured human anatomy.
`BodyProfile` defines bone lengths, foot dimensions, torso height, joint envelopes,
stride and root-speed bounds. The mass proxy allocates 0.60 to torso/head/resting
arms, 0.12 to each thigh, 0.06 to each shin and 0.02 to each foot. Thigh and shin
masses sit at segment midpoints; foot masses sit at sole origins; the torso mass
sits 45% of the torso height above the root. These weights do not adapt to a heavy
prop or independently moving arms.

`shoulder_width` is the full left-to-right distance between shoulder joint centers, independent of `hip_width`.
Supply it when adapting a canonical rig: shoulders are placed at ±`shoulder_width / 2` in the torso frame, then
rotated with the torso. Omitting it (Python `None`) retains the stylized default of `1.5 * hip_width`. In JSON,
omit the field to request that default; explicit widths are finite numbers in 0.01–2 meters.

`foot_width` is the full width of **one sole**, not the distance between the two feet. The stance's `FootAnchor`
origins determine the distance between feet. Each support rectangle spans ±`foot_width / 2`, from `-heel` to `toe`
in its sole frame; both drawing and support calculations use those same dimensions. A joint-center table does
not specify sole width by itself. Carry sole dimensions from the authored foot geometry instead of deriving them
from hip spacing. Changing `shoulder_width` does not change sole width, stance or the mass proxy.

The projected mass must remain inside the convex hull of planted sole rectangles,
with the profile's minimum margin. Moving the root without first shifting support
can raise `body.support`; excessive reach, bend or twist raises `body.joint`.
`error.to_dict()` includes a sample path, measured value, expected envelope and
repair instruction. The planner does not silently move the root or clamp a foot.

A step releases one sole at `start` and plants it exactly at `end`. Its position
uses minimum-jerk interpolation and a clearance arc with zero endpoint velocity
and acceleration. Root keys also stop smoothly at their endpoints; torso rotations
interpolate between keys. The nearest root is held outside its key interval.
There is always at least one supporting foot. Steps may not overlap and must land
before the performance ends. Flat soles and a static support check do not model
flight, toe-off/heel-strike, stairs, collision avoidance or running dynamics.

Adapters can use the public support geometry functions without importing the
body solver's private module:

| Function | Result |
| --- | --- |
| `support_footprint(sole, profile)` | Four world-space `Vec3` corners using the full `foot_width`, heel and toe |
| `support_hull(points)` | Counterclockwise convex hull of `(x, z)` pairs, starting at its lexicographic minimum |
| `support_margin(polygon, point)` | Minimum signed edge clearance of a world `Vec3` projected onto x/z, in meters |
| `support_area(polygon)` | Ground area in square meters |

The hull accepts lists or tuples of 3–4096 finite x/z pairs in the +/-1000 meter
workspace. It removes duplicate and interior points and refuses degenerate
support. Margin and area require unique, counterclockwise convex vertices,
without repeating the closing vertex. Margin is positive inside and negative
outside; outside a corner it is an edge half-plane clearance, not the Euclidean
distance to that corner. The footprint requires a planted yaw-only sole on y=0.
These functions use the same hull, footprint and margin calculations as
`BodyPose.support_polygon` and `BodyPose.support_margin`; they do not infer which
feet are planted or certify dynamic balance. Malformed inputs raise `BodyError`
with repair fields. Existing pose and profile defaults remain unchanged.

Compilation validates a grid at `validation_hz` (default 60), all root keys, contact
boundaries, swing midpoints and immediately preceding contact states. Each direct
sample also validates support and joint limits. `plan.checked_times` records the
checked grid; this is sampled validation, not a continuous-time certificate.
Limits are 600 seconds, 1–120 validation samples/second, 1,000 root keys or steps,
and 20,000 estimated validation samples. Bounds are cumulative, so a long score
may require a lower validation rate.

The `srstudio.body/1.1.0` JSON schema adds explicit `profile.shoulder_width`; the reader also accepts `1.0.0`
documents without that field. Both schemas accept `duration`, `roots`, `stance`, optional
`steps`, `profile` and `validation_hz`. A frame is an object with `origin: [x,y,z]`
and optional `rotation: [w,x,y,z]`; a root key has `time`, `root` and optional
`torso: [w,x,y,z]`. Stance entries have `side` and `frame`; steps have `side`,
`start`, `end`, `target` and optional `clearance`. Profile keys match `BodyProfile`;
`knee_limits` is a two-number array. Unknown fields, string numbers and boolean
numbers are refused. Parse first, then compile for support validation. The
[study's input generator](../examples/body_steps.py) is an executable JSON example.

`plan.window(start, end).place(...)` provides `solid` and `wire` candidate drawings.
The static `Camera` projects world geometry into the parent's pixel coordinates.
The diagnostic view shows soles, joint centers, the support polygon and mass
projection. Both drawings keep arms in a torso-local rest pose. Existing Toon,
Gloss and Stick actors do not automatically accept a body plan; a custom adapter
must explicitly map its anatomy and shoulder frames without retaining duplicate
legacy legs. No drawing approval transfers from another character.

Drawing holds poses at 1–120 fps on the source grid and includes exact contact
boundaries. Cuts reuse those samples instead of restarting a step. The complete
source is revalidated and projected before mutation, with limits of 1,000 frames
and 100,000 nodes. A short window still retains its complete source clock and
counts the full source toward those budgets. Invalid style, camera, projection,
IDs or budgets fail before any scene change; unexpected drawing failures roll back.

Run the six-second weight-shift and two-step study:

```sh
python -m examples.body_steps ../generated/body-study
scene-render render ../generated/body-study/cuts.xml --frames 0..144 --output 'frame-%04d.png' --strict --quality final
scene-render encode ../generated/body-study/cuts.xml --strict --quality final
```

Its cut and uncut variants share framing and should match every frame. The report
records source/font hashes, profile values, all sampled support states and planted
anchor residuals. These measures support a temporal review; they do not establish
audience preference or certify a human gait.
