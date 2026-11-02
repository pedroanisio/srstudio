---
generated-by: OpenAI Codex (GPT-6)
---

# 0207: Declare native ink ownership by group

The hybrid figure contains 977 shapes with nested native clocks, opacity and
gradients. A lit world composition requires explicit shading ownership, while
one binding accepts at most 256 surface records. Describing every preserved
shape separately would multiply metadata; splitting the drawing would duplicate
ancestors and require proving that group compositing remains unchanged.

Allow a native `FormSurface(mode="ink")` to name a nonempty source group. That
declaration owns all descendant shapes, preserving their complete native XML.
Every shape still has exactly one explicit owner, either a shape field or an
ancestor ink group. Nested fields, shape overrides inside an ink group, missing
owners, unknown targets and empty group declarations fail. Diffuse fields and
spatial paths still name individual shapes. Native text remains a separate
information layer.

Coverage validation walks the already verified, bounded source tree once. It
does not infer materials, normals or unseen geometry. The source digest includes
the declaration and complete XML. Existing shape declarations, their digests and
their emitted drawing remain unchanged. Group ink does not bypass world/view,
candidate approval, source, node, memory or output limits.

Rejected alternatives: raising the surface-record cap retains redundant
per-shape metadata; declaring the picture as information misstates its role;
silently treating unmatched shapes as ink hides missing lighting intent; splitting
native groups risks changing compositing and duplicates source structure.

Tests exercise public and worker preparation, mixed ink/diffuse ownership,
failure before publication, and the actual 977-shape figure without rewriting
its source. This preserves the candidate's authored colors. Lighting the rig's
actual forms remains an explicit, separately authored task.
