---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0175: Sample scene motion before backend preparation

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

Camera, light and parent motion belong to the scene clock. A separate, versioned
`SceneMotion` record samples them into the existing immutable `ScenePlan` before
backend preparation. This keeps source playback clocks intact and gives every
backend the same resolved view. Static plan schemas and existing worker payloads
retain their current meaning.

The initial contract supports explicit linear, cubic and quintic easing plus
held cuts. Angles interpolate as authored XYZ Euler channels, preserving full
turns. Quaternion shortest-arc interpolation was rejected as an implicit default:
it would erase an authored 360-degree turn. Color/projection changes require a
held segment, while light identity and kind remain fixed.

Sampling is random-access and side-effect-free. The strict bounded parser and
normal preflight validate inputs and the requested scene. Each result is a
static view; its work estimate cannot be reused as the total cost of rendering
an animated sequence. Whole-timeline planning and emission must budget the
combined work explicitly rather than looping over individually valid plans.

Contact guarantees must survive motion, not merely pass at selected frames.
The static affine-source-anchor proof remains valid for a shared rigid animated
ancestor because rigid transformations preserve the residual norm. Independent
branch motion and varying common scale are refused pending an appropriate
continuous proof. Dropping contacts, clearing animated binding metadata and
claiming continuity from output-frame samples were rejected.

Quintic easing is evaluated from its nearest endpoint. Evaluating the expanded
polynomial near one can exceed one through floating-point cancellation and
make a nonnegative light fade negative. The symmetric evaluation preserves the
intended range without changing its analytic easing function.

The [guide](../composition-preflight.md#sample-shared-scene-motion) and
[tests](../../tests/test_scene_motion.py) define this sampling API. Aggregate
timeline budgets, animated emission and rendered style adoption remain open.
