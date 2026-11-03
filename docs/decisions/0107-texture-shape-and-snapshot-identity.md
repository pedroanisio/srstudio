---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0107: Texture identity includes shape and uses one render snapshot

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)
- Extends [rendered-artifact identity](0095-rendered-artifact-cache-identity.md)

The former `Texture.sha256` hashed only raw array bytes and cached that hash on
a record whose array remained mutable. A 2×2 RGBA image and a 4×1 image could
therefore share a drawing name, a canvas asset and a rendered cache entry. Two
maps in one plate could also name the same file. Editing pixels after the first
hash reused stale identity, and edits during preparation could stage pixels that
did not match the document used for the cache key.

Texture identity now hashes a versioned domain, fixed-width width and height,
and row-major RGBA8 bytes. It is recomputed on access because callers still own
their mutable arrays. Layout and strides do not affect identity. Hashing and
render preparation refuse non-array, non-RGBA, non-uint8 and empty inputs with
`PlateError` repair fields; implicit quantization would change authored pixels.

Five exact authored maps at `e15fe9cc` retain their previous logical names:
Rafa's knit, clay and skin maps, and Pedro's scalp and goatee maps. A closed
table binds each original pixel hash to its original dimensions. Both must
match to use an alias. Reshaping the same bytes or editing any pixel gets the
new versioned name. No new maps are added to this table. These aliases preserve
approved drawings without extending the raw-byte collision to other shapes.

Before cache lookup, plate preparation copies each distinct texture object into
an immutable byte-backed array. The compiled document and staged resources use
the same snapshot. Equal shape and pixels share one resource across materials
and color/normal maps. Both passes of `verify` use one snapshot. Callers must
keep arrays stable during copying; this is not synchronization for concurrent
writers. Warm hits copy and hash inputs, but do not encode PNGs or render.

Correcting only rendered-cache keys was rejected: `document`, `digest` and
`place` would still collapse different images into one logical drawing or asset,
and maps in one document would still collide. Freezing caller-owned arrays was
also rejected because it changes their mutability and can affect other owners.

New names change custom textured drawings; the five authored maps keep their
approved drawing references. All textured render keys use schema 1.1.0 and
include map names and dimensions, even when the drawing uses a legacy alias.
Previous render artifacts lack that shape evidence and are never promoted to
verified hits. Published project copies and approval records are not rewritten.
Untextured and printed-label drawing and render identities stay unchanged;
unrelated color or normal maps do not invalidate a printed-label render.
No geometry, UVs, shading, pixel values or PNG encoding change for previously
unambiguous inputs. This migration is distinct from the bounded composition
adapter, whose independently versioned identities already included dimensions.

Regression coverage includes shape collisions, mutable arrays, memory layouts,
both material map slots, warm reuse, staging snapshots, malformed inputs, exact
authored aliases and old cache refusal. The real renderer test compares square and strip images, checks
warm reuse, and checks pixel parity against the previous unambiguous square
document with its original texture resource name.
