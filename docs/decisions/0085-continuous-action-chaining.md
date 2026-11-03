---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0085: Explicit joins carry motion between gestures

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

`Motion.chain()` produces a new motion with explicit `ActionJoin` records. A default join replaces recovery
through the following stroke, preserving the first hold and the second stroke endpoint. Custom windows select
endpoints within the adjacent actions. Windows cannot overlap or replace active contacts. Unjoined motions and
samples outside join interiors retain their existing behavior.

Planning uses source poses and one-sided second-order boundary derivatives. World wrist position and hand
orientation use continuous transform tracks. A separate rotation track carries the elbow plane; effective
finger angles use quintic Hermite interpolation. The shared pose solver enforces existing reach, wrist and
finger limits at every sample. Interpolating solved bone positions was rejected because it can change lengths.
Ambiguous elbow planes and unreachable paths produce typed diagnostics instead of arbitrary flips or clamps.

Joins are deterministic under random-access sampling. Resolved windows support binary lookup; each motion
caches at most 64 prepared joins. The cache is derived data and is not serialized. At most 9999 joins can connect
the existing 10000-action bound. Motion JSON advances to 1.3.0; readers preserve earlier documents' behavior,
and earlier schema tags reject the new joins field.

## Limits and verification

Boundary velocities are numerical estimates. Root discontinuities are not repaired, acceleration/jerk matching
is not promised, and compiled output still follows its bake rate. A join is a composition primitive, not an
anatomical or emotional quality certificate. Quality profiles and rendered review remain separate checks.

Regression tests cover boundary position/velocity, hand orientation and finger geometry, both anatomical sides,
moving roots and contacts, carried props, every supplied hand topology, cache eviction, serialization migration,
unreachable paths, atomic compiler refusal, and native/baked output. A standalone documentation recipe is executed
as a test. These establish numerical and API behavior; they do not establish perceptual preference.

## Alternatives

Changing every action to retain its pose would alter existing episodes. Hidden playback state would make random
access and parallel frame rendering unreliable. A mandatory global optimizer would complicate a bounded local
composition operation. Explicit windows keep author control, predictable failure paths, and backward behavior.
