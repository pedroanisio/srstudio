---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0095: Rendered-artifact cache identity

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Separate stable drawing identity from rendered-artifact identity. Keep
`plates.document`, `plates.digest` and logical print references independent of
renderer installation. Use a versioned artifact key incorporating renderer file
bytes, compiled scene bytes, actual font bytes when used and compiled printed
texture dependencies. Quality settings enter through the emitted scenes.

Store artifacts under `<cache>/renders/<engine-sha256>/` with renderer-aware
filenames. Distinct filenames propagate identity through host image shelves,
patches and other caches that use source stems. Preserve all previous artifacts;
returning to earlier inputs reuses their existing outputs. Hash actual engine
bytes on each request, without treating paths, version strings, sizes or mtimes
as content identity. The extra read cost remains explicit for phase benchmarks.

Preflight engine/font inputs and compile scenes before creating the plate cache.
Render in private, unique temporary directories and atomically install complete
PNGs. Recheck engine bytes after rendering and refuse publication if they changed.
Font bytes used for compilation are the same bytes staged for rendering.
These controls assume an immutable toolchain during the call; they are not a
sandbox for a malicious executable or proof across changed dynamic dependencies,
hardware and environment. Failed work may leave complete reusable dependencies,
but never publishes the failed plate as a successful artifact.

Catalog specimen caches bind the engine and each plate dependency's full input
key before checking for a hit. Package poster caches also bind the renderer.
Specimen plans retain their stable drawing key until bound for rendering. A
plate-backed specimen atomically copies its selected artifact to the logical
plate reference its document declares. Rendering checks the bound engine before
and after drawing and before final installation.
Each rendered plate must also match the dependency key bound to its specimen;
a font or plate-input change between planning and rendering refuses publication
with `catalog.inputs.changed`.

## Migration

Callers use returned render paths. A drawing digest is not a rendered filename.
Unowned legacy cache files remain on disk and are never silently promoted to a
renderer-owned hit. New artifacts are rendered once. Existing published projects
and their copied assets are not rewritten by this cache migration; approval
fingerprints still describe drawings, not a renderer installation.

## Alternatives

A renderer version string can be shared by distinct builds. Path/stat-only keys
can miss replacement bytes. Sidecars on mutable drawing filenames would allow
different renderer outputs to collide when copied into a host project's assets.
Changing drawing digests to include a local engine would prevent inspection and
approval checks without that engine. Separate artifact identities preserve those
contracts and prevent stale renderer/font outputs from being reused.
