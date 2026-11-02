---
generated-by: OpenAI Codex (GPT-6)
---

# 0208: Coalesce unchanged vector intervals after native reuse

The world figure samples 72 held placements, folding its held opening into
66 intervals, while the camera has only 14 views. Native reuse from ADR 0206
keeps two source instances for its back/front
windows. Copying the unchanged floor at every figure placement still makes the
conservative output bound exceed eight MiB.

Retain the existing output whenever the ordinary layout or native reuse already
fits. Otherwise, consider coalescing adjacent intervals for non-reused vector
layers. The layer's source clock, coordinate space, resolved parent pose, complete
camera and resolved form fields must match. A visibility gap prevents merging.
Changing lighting fields, projected geometry, placement or camera keeps the
boundary. Comparing complete fields is deliberately conservative even when two
different irradiance values select the same palette color.

One retained interval keeps the original affine source clock and complete XML.
Native animation continues inside the enlarged window; it is not sampled or
frozen. The base painter order and source windows stay intact. Raster references
and preparation are unchanged. Both host and worker independently derive the
layout after source validation, and both enforce the existing source, output,
memory and transport limits. Planning retains its conservative node and metadata
bounds.

Rejected alternatives: raising the output cap postpones multiplicative growth;
lowering the figure's cadence changes its authored movement; freezing all vector
layers across a camera hold loses native animation and form changes; changing
already-fitting layouts needlessly changes existing identities.

Tests cover the actual full-cadence world vectors and the existing compact
compiler, plus camera, parent, lighting, path, visibility-window and gap cases.
Rendered comparison checks source-clock continuity against the unchanged native
drawing around the camera cut. The optimization does not imply approval of the
combined drawing or completion of its body, hand and information integration.
