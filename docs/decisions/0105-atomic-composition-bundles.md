---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0105: Publish mixed scenes as complete bundles

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

A mixed scene depends on both vector XML and rendered plate images. Publishing
one file at a time exposes incomplete scenes. `emit_bundle` stages a complete
private directory, then installs it with Linux `renameat2(RENAME_NOREPLACE)`.
Existing destinations are refused, including empty directories. An unsupported
filesystem produces a typed failure instead of falling back to partial writes.
Atomic visibility is separate from crash durability.

`compile_bundle` reverifies every supplied source before touching the cache or
starting the renderer. Unique render jobs include the exact prepared XML,
resources and renderer bytes. Warm cache entries require matching metadata,
content hashes and complete bounded PNG validation. Renderer failures count
against every enclosing render session; no retries are implicit. A successfully
verified cache entry may survive a later job or final publication failure.

Image verification and mixed assembly run in the existing limited workers.
Renderer sessions impose per-process address-space, deadline and invocation
limits plus an optional kernel per-file byte cap. Bundles use 256 MiB per file
to allow graphics-backend scratch/mapped files; the initial eight MiB cap
prevented the real renderer from starting its render. The cap does not represent
an aggregate filesystem quota. Scene bundles are limited to eight MiB in total.

The vector compiler and mixed assembler share placement, namespace and clock
handling. A plate already contains the full world/camera transform, so its image
receives only the registered screen offset. Static placements with identical
render inputs share pixels even when their visibility intervals differ.

Rejected alternatives include trusting a prepared record without rechecking its
source, cache keys based only on source IDs, decoding compressed pixels in the
unlimited host, replacing an existing directory, and publishing XML before its
images. These respectively allow forged evidence, stale pixels, unbounded decode
work, destructive output replacement and incomplete scenes.

This adapter supports static plates and existing vector features;
[texture snapshots](0106-verified-plate-textures.md) add UV-bound color/normal maps.
[Printed labels](0144-bounded-composition-prints.md) add verified font and render
dependencies. [Static proxies](0145-bounded-composition-proxies.md) add shared-view
light/ID rendering and worker conversion. [Held timelines](0146-bounded-raster-timelines.md)
add baked geometry/appearance snapshots. Animated scene cameras/lights/parents,
orthographic plate views and animated
drawing approval remain outside its supported contract. See the
[guide](../composition-preflight.md#render-and-publish-a-mixed-bundle) and
[tests](../../tests/test_composition_bundles.py).
