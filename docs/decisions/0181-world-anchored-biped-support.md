---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0181: World-anchored biped support and authored steps

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

Whole-body authoring needs feet that stay fixed while the pelvis moves, plus an
explicit test for supported posture. Reusing arm motion names or parenting a foot
to the moving pelvis would hide the coordinate ownership and cause foot sliding.
The body score instead owns world-space sole anchors, a root/torso track, and
non-overlapping lift/plant intervals. Both legs use the existing analytic
two-segment solver with explicitly declared hip, knee, ankle and foot-yaw limits.
World shoulder frames are outputs for adapters; arm contacts are not inferred.

Support uses the ground-plane projection of an authored mass proxy against the
convex hull of planted foot rectangles. This is a quasi-static authoring constraint,
not a dynamics or physiological model. A silent balance correction was rejected:
it could move a deliberately placed root or break a prop interaction. Invalid
support raises `body.support` with the sample time, measured margin and repair
fields. A requested sample must satisfy the contract. Compilation additionally
checks a bounded grid, root keys and contact boundaries; that grid is not a
continuous-time stability certificate.

Root translation and torso rotation use zero-end-velocity/acceleration easing.
The swing has an authored clearance with zero lift derivatives at both endpoints;
before release and after landing, the exact sole frame is retained. Flat ground,
yaw-only soles, sequential supported steps and bounded anatomy are explicit scope.
Flight, rolling feet, stairs, collision response and calibrated human gait require
separate contracts. Treating a passing static support test as proof of those
capabilities was rejected.

The data schema is closed, bounded and separate from runtime canvas/camera bindings.
Drawing revalidates the complete source score and projects every emitted pose before
allocating IDs. A transaction rolls back unexpected emission failures. Frames stay
on the original performance clock, including contact events, through cropped
windows. The solid and diagnostic drawings are original candidates with no inherited
part approval; existing registered actors are not silently replaced.

The [guide](../authoring-body.md), [two-step study](../../examples/body_steps.py),
and [support tests](../../tests/test_body.py) cover the intended path.
