---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0182: Candidate composition uses explicit review provenance

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

New drawings need the same bounded composition pipeline used by approved parts
to produce adoption evidence. Assigning an unrelated approved part name to new
geometry conflates drawing identity with approval. Bypassing the shared compiler
also bypasses its relationship and resource checks.

Host-owned asset bindings may therefore carry `CandidateSource`: intended style
and exact source digest. Candidate part names occupy a separate `candidate.`
namespace, with explicit versions. Preflight requires the host to select
`candidate-review`; production remains the default. Scene JSON cannot supply
this policy or asset bindings. Registered references continue to resolve through
the verified part table in either mode. Candidate declarations never write that
table or claim its approval.

Source identity covers complete vector XML, plate content, proxy conversion
controls, or complete raster sequence content and timing. Geometry preparation
checks that identity before cache access or rendering. Raw render job identity
remains separate so recipe changes can reuse valid raw light/ID renders. Within
one plan, a candidate name/version cannot refer to conflicting content. Global
revision history belongs to the host; adding a mutable candidate registry was
rejected because this workflow prepares evidence rather than adopting drawings.

Review purpose persists in validated plans and timeline worker protocols.
Compiled XML carries a bounded non-rendering provenance comment, including null
candidate approvals. A separate sidecar alone was rejected because copying the
scene could lose its review designation. Existing production vector output and
manifest digests retain captured pre-change fingerprints. Candidate metadata
does not alter pixels, approve a style, or certify the full DRAWING matrix.

The [executable guide](../composition-preflight.md#review-a-new-candidate-drawing)
and [contract tests](../../tests/test_composition_candidates.py) exercise the
review path, strict refusals, worker propagation, rendering and cache reuse.
