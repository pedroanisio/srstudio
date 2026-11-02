---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0108: Target gaze on the source performance clock

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Compile bounded `GazeSpec` records into a deterministic `GazePlan` before drawing.
Target and observer tracks share a fixed coordinate frame and use one performance
clock. Eye and head latency are explicit; the head contributes a declared fraction
of the delayed target angle, and the eyes compensate for that head contribution.
Reject limit excursions instead of silently clamping the intended direction.

Sample target easing onto a bounded grid that retains delayed source breakpoints.
Interpolate the resulting angles linearly. This guarantees the compiled angular
envelope, not exact continuous tracking, derivative continuity, or physiological
plausibility. Rotating coordinate frames remain the caller's responsibility.

Require drawings to declare `EyeLayers` through `TrackingEyes`. The original layer
order remains intact: only declared pupil, iris and glint runs receive transforms.
Lids and other contours stay in their authored positions, and pupil-free expressions
remain pupil-free. Critter and Inked split-head drawings implement this contract.
The optional path leaves legacy output unchanged when no target is supplied.

The Toon adapter maps angles to bounded eye-radius offsets and stylized `face_x`
and `nod` channels. Combined head channels must remain inside the actual rig's
envelope. It does not rotate a 3D eyeball or enforce world-space line of sight.
Preflight checks capability, ownership and emitted-key budgets before scene
mutation; a failed draw rolls back scene nodes and Canvas identifiers.

`PerformancePlan.with_target_gaze` binds the full-duration plan once. Rebinding
replaces its prior target; shot windows retain the original source clock. Named
look-away states conflict with continuous ownership. Neutral holds may be replaced;
`Overrides(gaze=())` suppresses procedural named glances.

## Alternatives

- Keeping a mutable look-at controller per shot would restart latency and make
  random-access sampling depend on playback order.
- Translating the complete eye drawing would move lids and sclera with the pupil.
- Regenerating every eye for every sample would multiply geometry and lose the
  explicit moving-layer contract. Native linear transforms keep that geometry fixed.
- Automatically selecting the closest named state would conceal unsupported
  continuous output. `NamedGazeMapping` instead requires a supported vocabulary and
  an explicit maximum error in eye radii; it returns eye keys only, not head motion.
- A universal anatomical model would claim relationships that these independent
  stylized drawings do not provide. Each rig declares its rendering capabilities.

## Evidence and limits

Planner tests exercise input refusal, budgets, latency, eye compensation, bounds,
random-access samples and source windows. Drawing tests preserve authored geometry
and painter order, test preflight/rollback, and reject unsupported capabilities.
Engine tests compare actual transforms and opacity after cuts. The executable
[two-style study](../../examples/target_gaze.py) also compares cut and uncut rendered
pixels at representative times and checks that animated geometry avoids its labels.

The retained rendered study supports inspection of direction changes, head lag,
expression switches and lid occlusion. Neither those checks nor the demonstration
establish human preference, emotion recognition, or biological accuracy.
