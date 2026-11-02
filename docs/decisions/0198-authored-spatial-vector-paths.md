---
generated-by: OpenAI Codex (GPT-6)
---

# 0198: Spatial vector paths retain their authored geometry through shared projection

The hybrid proof needs rig surfaces and outlines to remain registered with rigid geometry while the camera moves.
A frontal vector transform cannot project vertices at different depths, and light normals do not define an outline's
missing spatial coordinates. Replacing the shared camera with a separate screen-space approximation hides that gap.

`FormSurface.path` optionally carries a `FormPath`: explicit asset-space vertices, closure and fixed-topology source
keys. A spatial asset supplies paths for every shape. Its complete parent transform and shared camera project each
vertex once; emitted groups have identity spatial placement. Form normals use the same world transform. Ordinary
vector assets keep their existing frontal-view refusal, and form-only source digests retain their earlier identity.

The spatial points are the geometry authority. Source XML supplies solid styling, opacity and painter order;
nonidentity local transforms, geometry animation and gradient-coordinate projection are refused. Screen-space
stroke width is explicit. World thickness belongs in authored filled ribbon geometry rather than an approximate
single depth-dependent stroke width for a path spanning several depths.

The immutable graph, vertex count, key count, source duration, near-plane envelope and projected XML expansion are
bounded. Geometry changes participate in timeline span identity independently of palette changes. Exact mapped
held boundaries preserve source clocks; linear vertex keys sample the frame grid without claiming anatomical
constraints between solved poses.

Rejected alternatives: extracting 3D shape from a 2D outline is underdetermined; applying a 2D affine transform to
an oblique perspective polygon misregisters its vertices; silently baking a second camera outside the compiler
breaks ownership of projection; accepting arbitrary XML transforms would apply movement twice.

This adapter supplies authored surfaces, not a volume renderer. Hidden-surface removal, cross-layer occlusion,
caster/receiver shadows, world finish and adoption evidence remain explicit requirements of the combined proof.
