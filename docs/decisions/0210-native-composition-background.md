---
generated-by: OpenAI Codex (GPT-6)
---

# 0210: Own the native project background in the scene manifest

The combined candidate must retain native text compositing over its original
clear color. Replacing a native project background with a far picture card
preserved timing but changed 446 antialiased text/pill pixels by one channel
level in the full-size comparison. A visually similar card does not establish
exact preservation of the original compositing path.

Add an optional `ScenePlan.background`, accepting an opaque `#RRGGBB` color or
`None`. Both static and timeline emission write it directly on the native
project. It is scene-owned, constant over the timeline, and separate from world
lighting, geometry, plate preparation and information styling. Vector sources
still cannot declare project backgrounds of their own.

The default remains transparent. Omitted or null background fields do not enter
the canonical scene definition or metadata cost, and unused defaults add no
graph visits. Existing plan, timeline and XML fingerprints remain unchanged.
An explicit color participates in scene identity and crosses the closed worker
protocol through the ordinary typed record parser. Invalid color syntax and
types fail before output/cache mutation. No render, source or memory limit is
raised, and raw plate jobs do not change merely because the clear color changes.

Tests cover the closed parser, all three public emission routes, invalid input,
source override refusal and exact existing fingerprints. The candidate's
full-size native information comparison retains strict RGBA equality; its
tolerance is not widened to accept the card's rounding differences.

Rejected alternatives: retaining the card changes edge pixels and adds camera
geometry; patching emitted XML bypasses the scene contract; loosening the pixel
check conceals a reproducible compositing difference. The new setting preserves
the existing candidate; it does not grant drawing approval.
