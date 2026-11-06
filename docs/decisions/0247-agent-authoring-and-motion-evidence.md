# 0247: Agent authoring and motion evidence

Date: 2026-11-06

Status: accepted

## Decision

Expose a bounded `srstudio.authoring/1.0.0` document for character, gesture and carry
tasks. Closed adapters construct typed records for explicitly listed rigs; canvas,
parent and identifier remain caller-owned runtime bindings. Placement uses a
parent-clock `start_s`/`end_s` interval and local performance seconds from zero.
Legacy builder signatures remain available. Compilation rolls back scene and
held-frame state on failure.

Contract discovery reports unresolved data independently from runtime bindings,
and counts declared examples independently from executed evidence. Nine executable
recipes expose schemas, compiler paths, preview commands, scope and limitations.
They do not label a render or perceptual review as complete during discovery.

Procedural limb compilation refuses authored actions/contacts that vanish between
samples, even when sampled derivative metrics would pass. Entirely cropped-away
events retain explicit crop semantics. Missing phases produce diagnostics.

New motion styles use a unit-peak C2 accent envelope with zero endpoint velocity
and acceleration. Motion schema 1.4 records the choice. Earlier JSON schemas and
pickles keep their legacy envelope; the existing calibration asset and compatibility
fixture remain unchanged. Calibration version 1.1 records separately measured C2
references under the same scoped anatomy and regression policy.

Scalar curves offer stop-smoothly, pass-through and intentional-impact intents.
Source continuity is reported separately from piecewise-linear emitted samples.
Neither smoother source curves nor calibrated isolated-arm metrics establish
whole-body biomechanics, perceptual quality or continuous collision safety.

## Validation

Regression tests were written and observed failing before fixes for invisible
events, acceleration jumps, binding coverage, JSON authoring, clocks, failure
rollback, curve intents and preview defects. Schema parity covers each recipe and
keyed motion; all supported character names execute. Existing serialized behavior
and both calibration versions have independent tests. Strict renderer pixel tests
check framing and visible attached-prop geometry; these checks remain narrower than
a human temporal quality review.
