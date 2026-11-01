---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0089: Freeze measured motion envelopes within an explicit scope

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Named quality presets reuse the existing motion sampler and audit. Each version fixes
anatomy, style adapter, motion clock, sampling rate, reference sources and numeric limits.
The compiler checks the scope again when options are reused. Shoulder translation and
left/right mirroring are permitted; implicit anatomical rescaling is not.

The initial Toon and Gloss envelopes use canonical human arms and hands, with two- and
three-second gestures respectively. Point, present and joined point/present motions on
both sides provide six derivative measurements per profile. Frozen thresholds use their
measured maxima plus 25% authored headroom, rounded upward to two decimals. Reach uses
a separate geometric tolerance. The headroom expresses a regression policy; it is not a
physiological estimate or a perceptual score.

The package asset records the measurement corpus, source hashes and exact limits.
Recomputation is read-only. Tests compare source hashes, sample counts and measurements
within numerical tolerance, and compare frozen rounded limits exactly. Updating the
corpus or limits requires a new version and reviewed evidence.

## Verification and use

Reference motions must pass. Sixfold time compression must trip every configured
derivative gate; an explicitly clamped unreachable target must trip the reach gate.
Out-of-scope anatomy, styles and rates fail before scene emission, including native,
baked and interaction boundaries. Tests also cover reused options and structured repairs.

The executable quality study builds all twelve reference scenes and two rejected scenes,
preserving the production error before using warn policy for deliberate failure rendering.
Strict engine results and video hashes are recorded only when rendering actually runs.
The separate blinded comparison uses existing review parsing and aggregation. Missing
human observations remain missing; a numeric pass never becomes a naturalness rating.

## Alternatives and limits

Universal thresholds would hide differences in anatomy, scale and sampling. Automatically
recomputed limits could absorb the regression they should detect. A separate sampler
would risk disagreement with emitted motion. Frozen, scoped presets avoid these problems
while keeping custom QualityProfile values available for other measured performances.

These studies cover isolated arms, not complete character performances. Low-level audit
does not own style or full-hand scope; callers use compiler options for scoped presets.
Obstacle definitions are environment-specific and are not invented by these profiles.
Continuous collision safety, whole-body balance, expressive success and human preference
remain distinct evidence requirements.
