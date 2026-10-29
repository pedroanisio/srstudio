---
generated-by: OpenAI Codex
---

# ADR 0035: Spatial limb performance with explicit rendering capabilities

- Status: accepted for the initial limb implementation
- Back to the [library README](../../README.md)

## Decision

`srstudio.limbs` separates immutable anatomy, spatial motion and style-specific drawing. Canonical coordinates
use normalized lengths, radians and explicit handedness. Human, three-finger, mitten, paw and gripper hands
share controls without requiring equal digit counts. The analytic arm solver preserves segment lengths and
reports unreachable targets; clamping requires an explicit policy and retains its residual.

`Motion.sample(time)` is history independent. Actions carry preparation, stroke, hold and recovery phases.
Relative targets scale with the arm; world targets and named prop anchors retain their coordinates. Contacts
can constrain a wrist or a named fingertip. Attachment acquisition must match the initial prop transform,
and release freezes its transform. `props.bind` coordinates independent arms against anchors on one prop
track. Capsule-versus-sphere clearance reports penetration or raises in strict mode; it does not solve
collisions or alter a locked contact.

A camera projects anatomy once. The compiler can invert a supplied drawing-parent affine transform and
route parts to body, behind-body and foreground layers. Those layer targets must share that transform.
Strictly planar arms can use engine two-bone IK; spatial arms use bounded frame-held vector geometry.
Explicit native requests fail when unsupported, while automatic selection returns its fallback diagnostic.
All nine built-in style adapters receive the same projected pose and own their ink, fill and surface treatment.

Versioned motion JSON is parsed into typed dataclasses with unknown-field rejection, finite-number checks,
semantic validation and deterministic size/depth limits. It is suitable as an untrusted authoring boundary;
this implementation makes no model or provider calls.

Existing Office and Cafe actors accept opt-in `LimbTrack` performances. A replacement suppresses only the
corresponding legacy arm. Other actor implementations must explicitly support replacement tracks. Mixed
legacy arm controls and typed limb tracks are rejected. Default performances retain their existing drawing
paths. Unsupported legacy pose conversions raise instead of silently selecting an idle pose.

## Alternatives

- A separate gesture implementation in every style would duplicate timing, anatomy and contact logic.
- Extending the engine to general spatial IK would couple reusable authoring to a renderer release. The
  vector fallback exercises the existing engine contract while keeping native planar IK available.
- Automatically correcting penetrations would hide failed constraints. Diagnostics let an author choose
  another elbow pole, anchor or intentional stylized overlap.

## Verification and scope

Tests cover anatomical lengths, handedness, joint limits, word alignment, seek order, contact residuals,
attachment continuity, JSON rejection, projection, unique scene IDs, frame intervals, resource preflight,
style adapters and actor integration. Renderer-enabled tests validate gallery XML and compare native
skeleton world transforms with canonical samples. `examples/limbs_gallery.py` builds six shared actions in
Stick, Toon and Gloss with reusable motion JSON and numeric QA reports.

This initial implementation does not establish viewer preference or a measured competitive advantage.
View-keyed artist contours are now available through `ContourCorrection` and `LimbTrack.correctives`;
see the [usage guide](../catalog/limbs.md). The interaction compiler now depth-composites hands and
original prop meshes. `examples/limbs_contact.py` renders a moving fingertip press and a cup that visibly
lifts before release; motion sources and numeric QA accompany the clip. Explicit native sleeve skinning
is available through `deformation="skin"`; renderer tests verify sleeve pixels at the wrist and elbow under
multiple poses and a mirrored parent. The gallery supports a planar skin mode across six actions and three
styles. Stick, Toon and Gloss character integrations are also available. Comparative viewer preference
remains unverified until real review records are collected. The original
six-action style gallery remains separate from the prop-contact clip.

## Folded-finger surfaces

Projecting a curled finger can send its centerline back across itself. Offsetting that whole polyline produced
self-crossing edges and triangular gaps at ordinary grasp controls. Finger surfaces now use the geometric
union of tapered, round-ended phalanges. Shapely replaces bespoke polygon clipping and union code; the
library dependency is `shapely>=2.1,<3`, with `types-shapely` in the test extra. Its NumPy dependency also
makes the existing `fast` extra redundant, but the extra remains accepted for installation compatibility.

The union returns one connected exterior plus any genuine enclosed holes. The renderer receives an even-odd
path when holes exist. Artist contours replace both the exterior and its holes. Toon uses the validated skin
contour for fingers while retaining its brush treatment on sleeves. The operation has explicit point-count
and finite-coordinate validation, and geometry failures raise `LimbError`.

A convex hull was rejected because it would fill the space inside a loop or a curved finger. Repairing a
self-crossing outline after constructing it was rejected because that outline does not define the intended
solid volume. Unioning the solid phalanges constructs the intended visible surface directly.

The [Shapely manual](https://shapely.readthedocs.io/en/stable/manual.html#efficient-unions) describes the polygon
union operation. Tests independently check edge intersections across curl and palm-turn angles, coincident
projection, a genuinely enclosed hole and renderer fill rules.

## Style character integration

Stick's articulated rig, the four brush-drawn Toon cast members and the three Gloss people now accept typed
limb tracks. Named-side suppression happens where each style creates its legacy arm, so replacing one side
retains the other side and the rest of the character. The default empty-track path adds no groups or IDs.

Shared integration helpers preflight complete tracks on an isolated canvas before creating character
geometry. Each builder supplies behind-body, arm and foreground layers in its own coordinate system.
Toon splits its unchanged foundation layers from its arm/face layers and maps replacement tracks through the
same reference-pixel conversion and lean/sigh transform. Renderer tests compare that mapping under desk,
sigh and lean poses. Existing character regression suites and byte comparisons cover the empty-track path.

`examples/limbs_cast.py` renders the same pointing action on complete Stick, Toon and Gloss characters with
character-specific placement, sleeve width, colors and hand topology. It complements the isolated six-action
and prop-contact clips; it does not establish viewer preference or comparative authoring effort.

## Paired-arm recipes and clearance

The `crossed` action and `crossed_arms` recipe add an explicit foreground arm and retarget crossing positions
from the shoulder span. Fixed relative wrist targets were rejected because wider shoulders and shorter arms
could stop before crossing the torso. `grip_prop` binds distinct right and left anchors on a shared moving
prop, preserving independent finger controls and strict contact/joint constraints.

Coordination checks mutual arm capsules as well as external sphere colliders. The segment-distance routine
handles crossing, parallel, point and endpoint cases; the proxy radii include the widest sleeve taper.
Clearance remains a diagnostic by default, with explicit strict failure available. It does not represent a
full hand/prop collision solver.

`examples/limbs_bimanual.py` demonstrates the crossing and a palm-up tray lift with original vector geometry,
serialized motions and numeric QA. Tests verify shared moving anchors, forward/reverse sampling, body-span
retargeting, inter-arm collision failure, panel bounds and rendered facial-detail visibility at a tilted view.

## Authoring-contract audit

Digit profiles now declare a validated local hinge axis. The mechanical gripper uses opposing axes and
explicit flexion limits; its previous generic finger flexion moved both jaws out of the closing plane. The
motion schema advances to `1.1.0`, while `1.0.0` remains readable with the original default axis. FK retains
the full shoulder orientation in the wrist frame instead of reconstructing a frame from position alone.

Frame budgets are checked before duration-to-frame multiplication, and clock precision is validated before
writing visibility keys. Numeric conversion, derived lengths, quaternion normalization, rotation bases and
projection output have explicit failure paths. Identifier bounds prevent a large input label from being
copied into every frame. These checks complement structural decoding; schema conformance alone does not
prove a performance can be compiled.

Paint IDs use invocation-local surface ordinals rather than user-authored digit labels. This avoids invalid
XML IDs and label-normalization collisions. RGBA shading preserves alpha, and zero outline width remains
zero in the Ink treatment. Collage replaces independent vertex jitter with a deterministic affine treatment
shared by outer and inner rings, preserving contour topology. Tests exercise each of these failure cases.

Showcase builders require an explicit license sidecar when a custom font is supplied. Falling back to the
system font's sidecar for a different font would make the generated asset metadata misleading; the failure
now occurs before copying that font into the output package.


## Comparative evaluation

`evaluation.measure` separates observed engineering cost from viewer preference and human authoring effort.
Deterministic repeated builds are schema-validated and hashed. Node counts, XML bytes and entry-function
source lines are reported with their boundaries; build time is not called authoring time. This avoids
claiming an ergonomic benefit from a runtime benchmark.

`examples/limbs_evaluate.py` builds paired Stick, Toon and Gloss tasks and an opaque A/B review packet.
The private implementation mapping stays outside the public review directory. Typed score records reject
unknown fields, invalid ranges, duplicate reviewer/trial records and unknown trials. Empty ratings produce
no preference result. Five reviewers per trial is a collection quota, not statistical evidence of superiority.
Human authoring time and competitive advantage remain unmeasured; neither is inferred from synthetic scores.

Compilation now retains aggregated anatomical diagnostics and maximum wrist reach residuals. Bone-length
and contact checks alone could otherwise hide explicitly permitted target clamping. Native compilation and
automatic fallback preserve this evidence rather than replacing it with backend selection messages.

## Reference boundaries

The [Buss inverse-kinematics survey](https://mathweb.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf)
describes iterative Jacobian methods. This module instead solves its fixed two-segment arm analytically;
it does not expose a general multichain optimizer. That is an implementation choice for deterministic,
bounded authoring, rather than a claim that analytic two-bone IK replaces those methods.

The [Khronos skinning tutorial](https://github.com/KhronosGroup/glTF-Tutorials/blob/main/gltfTutorial/gltfTutorial_020_Skins.md)
explains the distinction between bind geometry and animated joints. Here the engine owns skin evaluation;
the library emits its supported skeleton and modifier contract. This does not imply glTF import/export support.

The [OpenSim model catalog](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53090607)
includes experimentally derived upper-extremity models with muscle compartments. The limb package provides
stylized kinematic authoring with configurable hinge axes and joint limits. Its presets are animation
controls, not experimentally calibrated musculoskeletal models. It does not calculate muscle forces,
clinical range of motion or tissue deformation. Those quantities cannot be inferred from successful
bone-length and contact tests.

## Authoring observations

The evaluation boundary also accepts versioned authoring records, separate from measured scene-build time.
It validates task/implementation references and rejects duplicate author/task/implementation observations.
Failed attempts remain visible in completion counts and are excluded from completed-work timing statistics.
Paired differences require both implementations to be completed by the same author on the same task.
Without actual observations the report remains empty; build timings and entry-function line counts cannot
supply missing human measurements. The example report advances to `1.1.0` for its structured authoring summary.
