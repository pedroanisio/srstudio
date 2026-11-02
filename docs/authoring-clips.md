---
updated-by: OpenAI Codex (GPT-6)
---

# Place character clips and own plate caches

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Use a local source clock and an explicit project interval when placing characters. The recipe below binds `Canvas`, the parent and placement for two real families. Rejected capabilities raise `CharacterClipError`; [input diagnostics](authoring-diagnostics.md) and [acting refusals](authoring-acting.md#sustained-listening-and-repairable-capability-failures) show repair paths. Cache identities and drawing approval are separate contracts.

Run commands from the srstudio repository root.

### Character clips: one placement and timing boundary

`srstudio.character_clips.place_character` accepts typed `ActorClip`, `ToonClip`, `GlossClip` and `PlateClip`
records. Their performance times start at zero. `Interval(start, end)` supplies an inclusive start and exclusive
end on the **parent's timeline**: project seconds below the composition, shot seconds inside a sequence shot.
The adapter shifts the child clock once. Do not add the entrance to mouth, pose, head or limb keys.
Procedural idle and breathing start on that same local clock, independent of `Canvas.local_time`.

`Placement(x, y, scale=1, anchor=(0, 0), rotation=0)` maps a source anchor to parent coordinates. Scale is a positive
ratio; rotation is clockwise degrees. Source units remain explicit:

| Clip | Source origin / supported controls |
| --- | --- |
| `ActorClip(ActorClass, Performance(...))` | Head origin, head radius 100; mouth, blink, nod and supported `LimbTrack`s. Untyped `extras` and overridden build lifecycles are refused. |
| `ToonClip(HeadRig, poses, head=HeadPlan(...))` | Toon frame pixels; poses, visemes, taps and bounded head/gaze/breath channels. Shared Toon vocabulary plus Bento's moods, eye states and gestures. Arm gestures belong to poses; replacement limb tracks are not supported by this split-head drawer. |
| `GlossClip("nadia", ...)` | Feet at zero for Nadia/Gus/Tamsin; center at zero for Sunny. Speech and facial tracks; guests also accept pose and limb tracks. |
| `PlateClip(frames)` | Plate-frame pixels; held, layered image frames referencing already-declared assets. |

This example places two different rig families over the same project interval. The mouth change at local second
0.5 appears at project second 3.5; the listener's pose changes at project second 4:

<!-- character-clips:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, cast
from srstudio.character_clips import ActorClip, GlossClip, Interval, Placement, place_character
from srstudio.rig import Performance

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="30", duration=6)
cv = Canvas(scene, font_asset=None)
interval = Interval(3, 5)
speaker = place_character(
    cv, cv.comp,
    ActorClip(cast.Manager, Performance(mouth=((0, "rest"), (0.5, "open"), (1.2, "rest")))),
    interval=interval, placement=Placement(300, 700, scale=0.9), id="speaker",
)
listener = place_character(
    cv, cv.comp, GlossClip("gus", face=((0, "open"), (1, "wide")), pose=((0, "down"), (1, "shrug"))),
    interval=interval, placement=Placement(760, 1400, scale=0.8), id="listener",
)
assert scene.check(schema=True) == []
```
<!-- character-clips:end -->

For Rafa, prepare the image sheet separately with `rafa_host.sheet`, declare its images on the canvas with their
full-frame or patch dimensions, then call `PlateClip.from_rafa(rows, sheet, path_to_asset_id)`. The mapping uses
each sheet `Path` as a key. Adjacent identical frames coalesce. The returned clip records `len(rows) / 30` as its
duration, and placement refuses a different length. Turn, nod and expression are already baked into those plates;
the adapter does not synthesize new plate poses or start a renderer. Asset paths resolve against the scene file.

Each clip is bounded to 600 seconds and 20,000 entries per track; plate frames allow at most 64 layers. Intervals
must retain microsecond precision. Input data is preflighted, and failed drawing restores scene nodes, built-in
canvas caches and IDs. Custom callback external side effects are outside that transaction. Frozen canvases are
refused. `Actor.build(..., end=...)` now accepts an explicit canvas-clock limb lifetime; omission keeps the project
duration default. Other builders keep their existing clocks and defaults.

These adapters do not equate expression names across rigs or carry emotional/contact state across separate clips.
For a continuous performance through camera cuts, retain its containing group and change cameras around it.
Soft, Ink, Stick, Saga and other specialized builders still use their documented APIs. Python dataclasses and
`contracts.describe_callable(place_character)` expose argument shapes; runtime objects remain runtime bindings,
and this API does not parse untrusted JSON. See [ADR 0087](decisions/0087-character-clip-clocks.md).

### Plate cache ownership

`plates.digest(plate)` identifies a drawing document. `plates.print_name(printed)` identifies a logical printed
texture from its definition and font metadata. Neither is a rendered filename. Use the `Path` returned by
`plates.render`, `plates.print_png`, or the prepared sheet; its filename includes the renderer and input identity
and remains distinct when copied into a project's asset directory.

Rendered plates and prints live under `<cache>/renders/<engine-sha256>/`. Their keys include a versioned cache
schema, the engine file's SHA-256, compiled scene bytes, actual print font bytes when used, and compiled print
dependencies. Samples, bounces, lighting and other emitted settings participate through the scene document.
Changing a printed texture's font or recipe invalidates plates that use it. Changing plate quality can reuse an
unchanged print. Equal renderer bytes at another path reuse artifacts; replacing the bytes at the same path
invalidates them even when its size and modification time are preserved.

Code-generated `Texture` maps use nonempty height-by-width-by-four `uint8` arrays. Their identity binds
width, height and row-major RGBA pixels; reshaping the same bytes creates a different image and drawing.
Pixel edits between calls change identity. `render` and `verify` snapshot all maps before cache lookup and
use those same snapshots for the document and staged PNGs. Keep caller arrays unchanged while the snapshot
is being copied. A warm hit still copies and hashes pixels, but encodes no PNG and starts no renderer.
Invalid arrays raise `plate.texture.pixels` before creating the cache; convert other image formats explicitly.

Five existing authored Rafa/Pedro maps keep their drawing names through a closed set of exact pixel-hash
and dimension aliases. Editing or reshaping one loses that alias. Other textures receive new drawing names.
Textured render keys use schema 1.1.0 and bind map names and dimensions, so old ambiguous render artifacts
are left untouched and are not reused, including for aliased maps. Untextured drawings, printed-label names
and their cache keys retain their identities. Existing published assets and approval records are not rewritten.
See [ADR 0107](decisions/0107-texture-shape-and-snapshot-identity.md).

Catalog specimen and package-poster caches also bind the renderer. Plate-backed specimens include their
rendered-plate input keys, and the catalog atomically materializes the selected plate at the stable logical
reference its scene uses. This keeps renderer installation out of drawing fingerprints while preventing an outer preview cache
from hiding changed renderer or font inputs.

An unchanged rebuild invokes no new plate renderer. It still reads and hashes identity inputs; no zero-cost or
cross-platform pixel-equivalence claim is implied. Renderer dependencies, hardware and environment must remain
pinned for reproducible comparisons. Keep renderer files immutable for a build. A detected change prevents the
current artifact from being published; previous complete artifacts remain available. `plates.verify` compares a
fresh plate render with cached pixels on that selected toolchain.

Legacy `<cache>/<drawing-digest>.png` and `prints/<logical-name>.png` files have no renderer provenance and are
left untouched, but are not imported as trusted cache hits. The first build with the new cache renders new
artifacts. Published projects keep their copied images and approved drawing references. Missing engine/font
inputs raise `plate.cache.input` before cache creation; execution failures retain `PlateError`, and detected
renderer changes expose `plate.cache.changed` or `catalog.renderer.changed` with repair fields.
Specimens also reject a rendered plate whose inputs changed after cache binding with `catalog.inputs.changed`.
