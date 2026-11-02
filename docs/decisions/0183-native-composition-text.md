---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0183: Composition owns font resources and preserves native text

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

The hybrid composition proof needs its protected information layer to pass
through the shared compiler. Rasterizing captions into proxy or plate outputs
would change their representation and make native information equivalence
harder to establish. Reading paths from agent-supplied XML would also move
resource ownership outside the host contract.

Vector sources therefore carry immutable `VectorFont` records: source ID,
actual font bytes and the full redistribution notice. Bounded preparation
validates declarations against those bytes. Source identity includes fonts and
licenses while retaining the old SHA-256 identity for fontless XML. Static and
timeline bundles preserve native text, scope references per placement and
publish deduplicated content-addressed resources with the scene in one atomic
directory operation. Single-file emission refuses resource-bearing inputs.

Text's declared box does not inherently contain its glyphs. Guessing an envelope
from character counts or advance widths was rejected. This adapter requires
authored `overflow="clip"`, which the renderer implements as a vector mask, and
uses that rectangle through the existing complete animation envelope checks.
It never inserts clipping. Bitmap, color and SVG fonts are refused because their
rendering paths need separate bounds evidence; upright TrueType outlines retain
the proven mask path. This is a bounded composition contract, not a new text
layout implementation or a guarantee that every glyph is available.

The [guide](../composition-preflight.md#native-text-and-pinned-fonts) and
[tests](../../tests/test_composition_text.py) cover resource ownership, hostile
inputs, rollback, content pins, typed worker errors, reference scoping and
pixel equivalence across nonzero source clocks. This capability enables the
hybrid migration; it does not complete or approve the full DRAWING proof.
