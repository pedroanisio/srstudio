---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0096: Scoped continuity discovery

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Expose `describe_continuity()` on spatial transform tracks and motions. Version
the returned JSON-compatible contract separately from motion serialization.
Describe interior source keys, outer held endpoints, join estimates and rendered
sampling as separate scopes. A false guarantee means no general guarantee;
it does not assert that every motion is discontinuous.

Minimum-jerk smooth transforms stop with zero velocity and acceleration at
interior keys. Continuous translation shares velocity and has zero acceleration
at keys. Continuous rotation targets shared angular velocity through spherical
controls, but normalized linear blending for small arcs is approximate. Do not
claim exact angular C1 or angular acceleration continuity. Explicit nonzero
endpoint velocities meet a stationary hold outside the authored interval.

Action joins match poses under their geometry conditions and estimate boundary
velocities using preserved source samples. They do not promise acceleration
continuity. Motion-wide guarantees cannot be inferred from a root or a join:
contacts, attachments, constraints, IK branches and projection need their own
checks. Both limb compiler backends use held sampled frames.

Acting rig discovery also describes legacy and policy baking, discrete drawing
switches and source-time-preserving cuts. Linear baked keys do not retain the
source easing curve's derivative guarantees. Existing numeric interpolation,
serialized motion and emitted drawing behavior remain unchanged.

## Verification

Boundary tests distinguish position, velocity and acceleration on nonuniform
spatial keys, including explicit velocities and held endpoints. Counterexamples
exercise small-arc angular approximation, an action join's acceleration mismatch
and a baked acting curve's velocity jump. Renderer evaluation demonstrates a
held native target between frames despite a continuous source track. Existing
contact, random-access, serialization and drawing parity tests remain required.

## Alternatives

One global smoothness flag would conflate different derivatives and stages.
Treating finite-difference estimates as exact derivatives would overstate the
join contract. Changing interpolation to match a stronger metadata claim would
change existing authored motion. This decision publishes the behavior actually
supported; stronger interpolators require their own explicit authoring contract.
