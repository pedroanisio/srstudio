---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0179: Read srlocations' 3D locations as a pinned, verified record

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)
- Extended by [ADR 0184](0184-srlocations-mannequin-blocking.md): a body blocked on the marks, schema 1.1.0

## Context

Upcoming scripts stand our figures in 3D locations from srlocations, elaborate places rebuilt from reference
photographs: a starship bridge for Saga and a TV news studio study first, a supermarket once the cast can hold goods
(arc4d3's rulings in Slack, 1793611720.082919 and 1793612340.312069, agreed with Pedro). A reel needs, per
shot, the camera and where each mark lands in the frame: the feet's pixel, the pixels per metre there, and whether the
mark is in frame. srlocations computes this in `framing.blocking` and `compiler.Projection`.

srlocations pins a different sr-core than srstudio does, so the two keep separate interpreters, and its checkout is
edited by other sessions while ours run, so a checkout is no record of what code ran.

## Decision

`tools/location_export.py` runs in srlocations' interpreter and writes one JSON record for a catalog location
(`--location NAME[@VERSION]`) or a location module (`--module FILE`, defining `NAME`, `VERSION` and `location()`), for
the listed shots at the given frame size. `srstudio.location_bridge` reads that record. srstudio never imports
srlocations, and its tests run on a recorded fixture
([airliner at 1080x1920](../../tests/data/location-bridge/airliner-1080x1920.json)).

### The record, schema 1.0.0

| Field | Holds |
|---|---|
| `schema_version` | semver; a reader refuses another major |
| `srlocations_commit` | the 40-hex commit the record was made by; refused unless it is the pin |
| `location` | `source` `catalog` (with `catalog`, the catalog's name) or `module`; `name`, `version` (semver), `digest` (SHA-256: the catalog's digest of the published payload, or of the module file) |
| `frame` | `width_px`, `height_px` |
| `shots[]` | `name`, `camera`, `marks[]` |
| `camera` | `eye_m`, `look_at_m`, `lens_mm`, `gate_mm` (36 x 24), `fit` (the side the gate fits: `height` on a portrait frame), `focal_px`, `near_m`, and the camera's axes in world space, `right`, `up`, `forward` |
| `marks[]` | `mark`, `at_m`, `facing_deg`, `framing`, `height_m`, `feet_px` and `head_px` (null behind the camera), `pixels_per_metre`, `in_frame` |

Units are in the names. World axes are srlocations' (x right, y up, z away); pixels count from the frame's top left.

The reader refuses, with typed errors under `LocationBridgeError`: text that is not one strict JSON object (NaN,
Infinity, a repeated key, over 4 MB), an unknown or missing field, a wrong type (a boolean is not a number), a
non-finite number, and a name, version, digest or commit outside its pattern (`RecordFormatError`); another schema
major (`SchemaVersionError`); another commit (`PinError`). Then it checks the numbers against each other
(`RecordValueError`): the axes are a rotation that looks at the target; the focal length is the lens on the gate fitted
to the frame; every mark's feet, head and scale are where that camera puts them; a point behind the near plane has no
pixel; `in_frame` is srlocations' own rule on those pixels; and a mark stands in the same place in every shot. Shots,
marks and bytes are bounded. `LocationRecord.placement`, `in_frame` and `Camera.project` are what a reel reads.

### The pin

`location_bridge.SRLOCATIONS_COMMIT` is the one pin: srlocations main `2742fd4` when this was decided, `4ae2278` since
2026-11-02. The exporter:

1. refuses a repository that does not hold the pinned commit;
2. writes that commit's `srlocations/` and `catalog/` from git's object store to
   `generated/srlocations/<commit>` (folders 700, files 600), never reading the checkout;
3. before each run, and again after it, checks every file there against the commit's tree by git blob id, and refuses
   an edited, extra or missing file or folder;
4. imports srlocations from that export, without writing bytecode, and refuses if any srlocations module came from
   anywhere else, if `SRLOCATIONS_CATALOGS` is set, or if the interpreter installs srlocations plugins;
5. reads its own record back through `location_bridge` before writing it, so it writes nothing srstudio refuses.
   `location_export.load_srstudio` loads that reader and `srstudio.errors`, which both import only the standard
   library, into an empty `srstudio` package on this repository's `src/srstudio`, so srstudio's `__init__` and the
   sr-core it needs never run in srlocations' interpreter, and the bridge's errors are `SrstudioError`s like every
   other library error.

Moving the pin is a commit that changes the constant, re-exports every recorded fixture, and passes the tests.

### What renders next to our figures

These are arc4d3's conditions, and they bind every reel that uses the bridge:

- A location rendered next to our figures is drawn in our cel/ink or clay look, never path-traced realism.
- No brands, badges, liveries or trade dress. A rebuilt airliner or car is generic.
- Photographs are Pedro's only, and are never committed to this repository.

## Rejected alternatives

- **Importing srlocations into srstudio.** The two pin different sr-core versions, so one interpreter cannot hold both,
  and every srstudio test would need srlocations installed.
- **A hand-copied projection** (as `examples/clay_sofa/clay_room.py` holds): it re-derives the gate, the fit and the
  axes from constants, and drifts without notice when srlocations changes. The record carries the camera srlocations
  computed. The reader still applies the pinhole equation, but only to the recorded axes and focal length, and it checks
  that equation against srlocations' own pixels on every record it reads.
- **Running from the checkout and refusing an edited package** (as `examples/paintover_proof/_lounge_set.py` does): it
  refuses whenever another session has uncommitted work there, and a clean checkout still says nothing about files
  that are not tracked.
- **Copying srlocations into this repository.** A second copy to keep in step with the first, cut off from its history.

## Consequences

- A location reaches a reel only as a record checked against srlocations' projection. A shot's camera moves are
  recorded as one named shot per frame, up to 512 shots.
- The paint-over studies keep their own pin (`_lounge_set.SRLOCATIONS_COMMIT`, `8dfe7a19`) and their hand-copied
  camera until they move to this bridge.
