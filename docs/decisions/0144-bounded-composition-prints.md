---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0144: Retain printed labels as bounded render dependencies

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

A printed material needs both a label render and a plate render. Flattening the
label before composition preflight would hide renderer work and font provenance.
`PlatePrint` therefore retains the exact immutable `plates.Print` recipe, font
bytes and a host-declared license. `plate_source` snapshots existing materials
with explicit `print_font` and `print_license` inputs, deduplicating identical
labels. A material can combine its label with a normal map, but cannot also
specify a competing color map.

The preparation worker checks recipe bounds and references, inspects the font's
actual TrueType family, weight and upright style, and schema-validates the label
document. Closed resources include content-addressed font bytes and label XML.
No font path, callback, renderer or cache enters preparation. Source identity
version 1.2.0 binds these additional inputs; unprinted sources retain their
existing identities.

Each source's existing `PlateWork` includes all its label attempts, dimensions,
conservative sample work, nodes and memory. Cold bundle jobs render the labels
inside their private work directory, verify their PNGs under process limits,
then render the plate. Each attempt consumes the source, plan and enclosing
render-session budgets. Adding the source attempt scope must preserve explicit
plan memory, deadline and file limits; scope defaults must not silently narrow
them. A failed label or plate leaves no partial cached plate or published bundle.
A warm plate needs no label render. Final bundles contain portable images and
do not need the fonts at playback.

Rejected alternatives:

- Keeping font paths in source records permits the font to change after preflight.
- Rendering labels during snapshotting or preparation hides renderer attempts
  from bundle accounting and makes preparation depend on a renderer/cache.
- Reusing ordinary print-cache entries without revalidating them bypasses the
  composition pipeline's image and dependency checks.
- Dropping the label or accepting both color maps leaves material meaning
  ambiguous and can change an approved drawing.

The [guide](../composition-preflight.md#preserve-printed-labels) defines supported
bounds. [Tests](../../tests/test_composition_prints.py) cover immutable snapshots,
wire validation, font-sensitive identity, normal-map coexistence, closed worker
preparation, cache reuse and failure preservation, inherited process limits,
and a rendered UV label probe. Animated geometry/textures, proxy adapters and
the complete animated drawing proof remain outside this decision.
