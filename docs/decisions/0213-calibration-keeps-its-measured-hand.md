---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0213: A calibrated preset keeps the hand it was measured with

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

[ADR 0089](0089-calibrated-motion-envelopes.md) says each preset version fixes its anatomy, reference sources and
limits, and that updating the corpus or limits needs a new version and reviewed evidence. The code did not hold
the anatomy fixed: the reference corpus and the preset scope both read the library's `HUMAN` constant. When
`HUMAN`'s thumb gained a third segment (lengths `(0.17, 0.13)` became `(0.12, 0.10, 0.08)`), the
`toon-human-conversation/1.0.0` and `gloss-human-deliberate/1.0.0` presets silently changed anatomy under the same
version. Their frozen source hashes stopped matching the corpus, and motions authored with the hand those presets
measured fell outside their own scope.

## Decision

`srstudio.limbs.calibration.CALIBRATED_HAND` states, as literal values, the hand every 1.0.0 envelope was measured
with: `HUMAN` with its two-segment thumb. The reference corpus and the preset scope use it. The frozen calibration
asset is unchanged, and the source-hash test proves the corpus is the one measured.

A motion authored with the current `HUMAN` is outside the 1.0.0 scope and is refused with `quality.scope` on the
`hand` path. Covering it needs a new preset version measured on that hand and reviewed, as ADR 0089 requires.

## Rejected alternatives

- Re-measure the 1.0.0 asset in place. The limits would come out identical, because the audit measures the arm,
  wrist and hand frame and never the digits, but ADR 0089 forbids changing a version's corpus in place.
- Revert the three-segment thumb. It is a deliberate change, documented in the limbs catalog and covered by its
  own tests; only its effect on the presets was unintended.
- Let the scope accept both hands. The 1.0.0 envelopes never measured the new hand, so that would claim a
  calibration nobody performed.

## Consequences

Callers that used `HUMAN` with a 1.0.0 preset must pass `CALIBRATED_HAND` until a reviewed new version covers
the current `HUMAN`. The catalog recipe and the reach-gate test now do. No episode uses these presets. The
quality study (`examples/limbs_quality.py`) builds its references from the corpus, so it is unaffected.
