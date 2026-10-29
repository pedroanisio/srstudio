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
lifts before release; motion sources and numeric QA accompany the clip. A skinning/deformation capability
demonstration, broader actor migrations and a comparative viewer evaluation remain unverified. The original six-action style gallery remains separate from the prop-contact clip.
