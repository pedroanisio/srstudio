---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0103: Register plates with the composition camera

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

The composition frame uses +Z toward the reference viewer; plate geometry uses
+Z away. `composition.plate_view` resolves all source parents in canonical space,
then converts physical units and reflects Z. It provides the same conversion for
source points and directions. Mesh consumers must reverse triangle winding.
Metric units have fixed conversions, while a canonical arm has an explicitly
authored physical length. The adapter does not infer a body's physical size.

The perspective focal length derives from the shared camera's pixel scale and
focal distance. Off-center principal points require an oversized centered image
and a screen-space offset. Its dimensions and memory are checked before any
render. Simply shifting a frame of the original size would discard geometry
visible at the opposite edge. The composed image must not receive another
source or camera transform.

Shared lights remain in world space. Reflecting their directions and converting
positions/radii preserves their relationship to transformed geometry. Parenting
the lights to each object would change the scene's lighting when an object moves.

The current plate camera cannot express all composition views. Orthographic,
screen-space and flat views are refused here, as are the engine's up-axis switch,
clamped field of view and clipping crossings. Approximating these views with a
long lens would not establish exact landmark registration. The adapter is a
read-only coordinate bridge; verified mesh inputs, work declarations, runtime
preparation and compiled plate/proxy emission remain required under SDK-P2-07.

The [registration tests](../../tests/test_composition_plate_view.py) cover parent
transforms, physical units, source handedness, off-center framing, lights and
typed refusals. A real-render test measures three colored landmarks under an
off-axis camera and a transformed source parent with a one-pixel tolerance.
