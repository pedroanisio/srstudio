---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0099: Limb-motion implementation boundaries

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Keep the public records in `srstudio.limbs.motion`. Separate transform sampling,
gesture requests, contact constraints and skeletal solving into internal modules.
This makes their numerical and anatomical responsibilities explicit before adding
new body or gaze behavior.

| Owner | Responsibility |
| --- | --- |
| `motion` | Public records, validation, scheduling, join orchestration, bounded per-instance caches and contextual failures |
| `_motion_interpolation` | Minimum-jerk interpolation and the endpoint-velocity basis shared by transforms, contacts and joins |
| `_motion_transforms` | Transform velocity estimation and random-access translation/rotation sampling |
| `_motion_gestures` | Gesture phases, proportional targets, expressive offsets and anatomy-aware hand-control blending |
| `_motion_contacts` | Contact acquisition/release, world orientation, residual diagnostics and prop attachment sampling |
| `_motion_kinematics` | Elbow-pole winding, wrist limits and the final arm/hand solve |
| `transitions` | Existing explicit action-join windows, boundary estimates and composed samples |

The five extracted internal modules refer to public records through type-checking imports only.
They receive an existing motion or track; they do not create alternate public
record types or own a second timeline. Public method hooks delegate sampling to
these owners. Contact positions remain available to elbow-pole sampling without
recursively evaluating the final pose.

The same minimum-jerk function and tangent coefficients serve all three
interpolation consumers. Vector multiplication order is preserved so extracting
the coefficients does not introduce floating-point changes. Quaternion track
interpolation, estimated contact boundary velocities and join boundaries retain
their distinct algorithms and the scoped guarantees in
[ADR 0096](0096-scoped-continuity-discovery.md).

## Compatibility

The public dataclasses retain their original definitions, module identities,
constructor signatures and type hints. Existing motion JSON schemas and pickles
continue to resolve them. `smooth` remains available through the public module;
the private `_blend`, `_recipe` and `_GOALS` names retain aliases for existing
internal consumers. These private names are not new supported APIs.

Join plans remain bounded to 64 cached entries and pole paths to two per motion.
Sampling order does not change the result. Validation, capability refusals,
compiler atomicity and error context remain part of the public contract.

The committed `tests/data/limb-motion-compatibility.json` fixture was captured
from `83917174` before extraction. It covers 40 motions: all 13 gestures on both
sides, five hand anatomies, expressive dynamics, continuous roots, joins, moving
wrist and fingertip contacts, attachments, elbow-pole motion and planar targets.
Numeric record hashes round at twelve decimal places. Ten emitted scenes retain
byte-exact XML hashes and numeric reports; six unsupported native requests retain
their capability refusals without scene mutation. Ten original protocol-4 record
serializations also remain readable. Normal tests never regenerate the fixture.

This refactor changes ownership, not motion quality or backend capabilities.
Existing continuity, contact, anatomy and compilation tests remain necessary
alongside the compatibility fixture.

## Alternatives

- Moving record definitions into implementation modules would require rewriting
  runtime module identities to preserve serialization. Keeping definitions at
  their public path avoids that extra compatibility mechanism for records.
- Retaining all sampling inside `Motion` would leave gesture intent, contact
  geometry and elbow constraints coupled during future changes.
- Copying interpolation into each owner would allow their endpoint behavior to
  diverge. A shared scalar basis avoids that duplication without conflating the
  different rotation and boundary-estimation algorithms.
