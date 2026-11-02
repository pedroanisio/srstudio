---
generated-by: OpenAI Codex (GPT-6)
---

# 0206: Reuse native vector geometry across timeline spans

The actual hybrid figure is a 2.4 MB native drawing. Copying its full source for
each of the candidate camera schedule's fourteen spans requires a conservative
40,858,140-byte expansion allowance. The existing eight-MiB output cap therefore
rejects a drawing whose geometry need not change at a camera cut.

Keep the existing representation when its expansion and working-memory bounds
fit. Otherwise, consider per-layer reuse for native vectors with no form fields
or only ink fields without spatial paths. Reuse a layer only when its retained
geometry and placement keys cost less than its interval copies. The host and
worker independently choose this representation after complete source validation.
The source, output, memory, node and transport limits remain unchanged.
Planning retains its conservative node and metadata estimates; this emission
optimization does not relax plan-level frame or node limits.

A reused layer has one scoped source beneath its original affine source clock.
An outer transform carries held placement keys on the composition clock. Parent
and camera transforms are resolved once at each planned interval; native spring
history and facial state continue through cuts. Separate placements of the same
asset retain separate IDs, windows and clocks.

The compact representation groups intervals by the base painter order. Scene
motion cannot reorder layers, so each original span is a subsequence of that
same order. Raster images, diffuse lighting fields, projected paths and native
layers for which reuse would increase the bound retain their per-span values.
Font resources and paints remain scoped, and full source verification still
includes hidden content before any cache access.

Rejected alternatives: raising the output cap merely postpones multiplicative
growth; baking the native source changes its curve and continuity contract;
reusing lit or projected geometry without retaining its changing values freezes
the scene; restarting a source at each cut loses its animation history; rewriting
already-fitting scenes changes established output identities without a need.

Evidence includes the complete figure/camera schedule, full-size pixel equality
at six times with nested parent motion and a fractional source rate, independent
clocks for repeated placements, fonts and raster cache reuse, changing lighting
and spatial-path spans, refusal of invalid hidden content and exhausted output
budgets, and unchanged fingerprints for existing small scenes. This removes the
native expansion obstacle. Full body/form/receiver integration and the complete
DRAWING acceptance matrix remain separate requirements.
