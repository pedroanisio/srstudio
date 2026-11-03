---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0187: Read srlocations' mannequin motion as a pinned, verified record

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The dance SDK retargets motion onto any character through a shared skeleton. The motion it needs is already authored on
srlocations' mannequin: walks with planted feet, named poses, reaches, and BVH takes read onto its 55 joints. srstudio
cannot run any of it. srlocations pins a different sr-core, so the two keep separate interpreters ([ADR
0179](0179-srlocations-location-bridge.md)), and its checkout is edited by other sessions while ours run.

Motion therefore crosses the way a location does: one record, made by a tool in srlocations' interpreter on the pinned
commit, read here with typed errors and checked number against number.

## Decision

`tools/motion_export.py` runs in srlocations' interpreter and writes one JSON record, from a location module and a figure
in it (`--module FILE --figure NAME`, the module defining `NAME`, `VERSION` and `location()`) or from a BVH take read
onto the stock mannequin (`--bvh FILE`), at `--fps`, from `--start` to `--end`. `srstudio.motion_bridge` reads that
record into typed `MotionClip` and `MotionFrame` objects. srstudio never imports srlocations, and its tests run on two
recorded fixtures made from location modules kept beside them:
[a two-metre walk](../../tests/data/motion-bridge/walk-2m-30fps.json) and
[stand, wave, arms crossed](../../tests/data/motion-bridge/stand-wave-crossed-30fps.json).

### The record, schema `srstudio.motion/1.0.0`

| Field | Holds |
|---|---|
| `schema` | `srstudio.motion/MAJOR.MINOR.PATCH`; a reader refuses another major |
| `srlocations_commit` | the 40-hex commit the record was made by; refused unless it is the pin |
| `source` | `kind` `module`: `name`, `version`, `digest` (SHA-256 of the module file), `figure`. `kind` `bvh`: `file`, `digest` (SHA-256 of the take), `unknown_bones` and `clamped_controls`, srlocations' report on the take |
| `axes` | always `{"x": "right", "y": "up", "z": "away"}`, srlocations' world |
| `fps`, `start_s`, `frame_count` | frame `n` is at `start_s + n / fps` |
| `joints[]` | the 55 in mannequin order: `name`, `parent` (null for the hips), `rest_offset_m` from the parent at the T-stance |
| `frames[]` | `root_translation_m`; `local_rotations_wxyz`, a unit quaternion per joint in `joints` order; `world_positions_m`, optional, a point per joint in that order |

Units are in the names. Quaternions are Hamilton's, `(w, x, y, z)`, and turn vectors actively. At the rest, every
rotation identity, the figure stands in srlocations' T-stance. A joint's rotation is its turn on its parent from there:

    world_rotation(joint) = world_rotation(parent) * rotation(joint)
    position(joint) = position(parent) + world_rotation(parent) applied to rest_offset(joint)
    position(hips) = root_translation, world_rotation(hips) = rotation(hips)

### Axes

The record keeps srlocations' axes, x right, y up, z away from the viewer, and the reader converts. The mannequin faces
+z. `MotionClip` is in the axes of `srstudio.body` and `srstudio.skeleton`: x right, y down, z the figure's anatomical
forward. The change is `(x, y, z)` to `(x, -y, z)`, the one the skeleton's joint table ([ADR
0185](0185-shared-skeleton.md)) was made with, so a clip's bones are that table's at the mannequin's height and a test
holds them to it. A rotation R becomes M R M with M = diag(1, -1, 1); an axis turns as a pseudovector, so a quaternion
`(w, x, y, z)` becomes `(w, -x, y, -z)`. M is orthogonal, so forward kinematics holds in either frame. A half turn
about x, `(x, -y, -z)`, would also keep y down, but it turns the figure to face -z, its back to the viewer of every
srstudio style, and its bones would no longer be the skeleton's. A BVH file's own frame is a third one (z toward the
viewer), and it stops at the exporter.

### What the exporter reads

Only srlocations' public interface. `interchange.save_bvh` gives the rest offsets and, per frame, the hips' place and
each joint's turns from the T-stance; the exporter parses that BVH, refusing any layout other than the one `save_bvh`
writes at the pin. `Location.at(time).nodes[i]`, then `Mannequin.frames()` and `Node.transform`, give each joint's world
position. A take goes through `interchange.load_bvh` onto the stock mannequin, and each pose back through `save_bvh`, so
a take and a location have one shape. A take keeps its own rate: `--fps` must equal it, and nothing is resampled.

### The checks

The reader refuses, with typed errors under `MotionBridgeError`, itself an `SrstudioError`: text that is not one strict
JSON object (NaN, Infinity, a repeated key, over 32 MB), an unknown or missing field, a wrong type (a boolean is not a
number), a non-finite number, a list past its bound and a name, version, digest or commit outside its pattern
(`RecordFormatError`); another schema major (`SchemaVersionError`); another commit (`PinError`). Then it checks the
numbers against each other (`RecordValueError`):

- the frame count is the frames held, from 1 to 7,200, at a rate above 0 and up to 240 fps;
- the parents form a tree, each before its children, and the skeleton is the canonical 55 in order with the mannequin's
  parents, held in `motion_bridge.CANONICAL_JOINTS` because srstudio cannot read `srlocations.stock.mannequin.JOINTS`;
- the hips have no rest offset, and every other bone is longer than 0 and at most 3 m;
- every rotation is a unit quaternion, within 1e-6;
- world positions are in every frame or none, and, where they are, the hips stand on the root, every bone keeps its rest
  length, and every joint is where forward kinematics of the rotations puts it, within a tenth of a millimetre, the
  tolerance srlocations' own BVH tests use.

Two public paths through srlocations meet in that last check: `save_bvh`'s turns and `frames()`' positions. It catches
any error in reading, converting or rounding either one, and it caught one while this exporter was written, a world
position flipped into the file's frame. It cannot catch a pose srlocations itself solves wrong, because both paths share
that solver. Without recorded positions a unit rotation is checked against nothing, so the exporter always writes them
and a record without them says less.

### One pin, one export

There is one srlocations pin: `location_bridge.SRLOCATIONS_COMMIT`, which `motion_bridge` imports. There is one export
folder, `generated/srlocations/<commit>`. `tools/motion_export.py` calls `tools/location_export.py`'s `require_commit`,
`export`, `verify`, `tree`, `check_loaded` and `load_srstudio`, so the steps of ADR 0179 hold unchanged: the commit's files come from git's
object store, are checked by blob id before and after the run, and no srlocations module loads from anywhere else. Its
environment refusals (`SRLOCATIONS_CATALOGS`, plugins, an srlocations imported too soon) match that tool's.

Moving the pin is the commit that changes the constant and re-exports every fixture of both bridges: the reader refuses
the old records with `PinError`, and the exporter's end-to-end test compares fresh exports with the committed fixtures
byte for byte. That test skips, and says why, when srlocations' interpreter or the pinned commit is missing.

The reader imports only the standard library and `srstudio.errors` and `srstudio.location_bridge`, both standard library
alone. In srlocations' interpreter the exporter loads the reader through `location_export.load_srstudio`, the one
loader both bridges share: an empty `srstudio` package on this repository's source holding those three modules, so `MotionBridgeError` is an `SrstudioError` while `srstudio/__init__.py` and everything it
needs never run there. It refuses a module loaded from anywhere else. The record is read back through the reader before
it is written, so the reader and the writer cannot drift.

## What srlocations would need to add

- **A public joint-transform call.** Local rotations and rest offsets are private (`Mannequin._local`, `_offset`,
  `_solved`). A call giving each joint's parent-relative rotation and rest offset would end the Euler round trip through
  a text BVH, whose six decimals are the record's precision floor.
- **A joint-table version.** `JOINTS_VERSION` is not committed at the pin. Once it is, the record can carry it and the
  reader can refuse a table it does not know, in place of comparing 55 names against a copy.
- **A public frame sampler.** The exporter repeats `interchange._moments`' rule for a frame's time, and refuses a count
  that differs from the BVH's.

## Rejected alternatives

- **Importing srlocations into srstudio.** The two pin different sr-core versions, so one interpreter cannot hold both,
  and every srstudio test would need srlocations installed.
- **GLB as the interchange.** A binary container we would have to parse for rotations the BVH already gives as text, with
  meshes and materials a dance has no use for. srlocations also has uncommitted work on `save_glb`, so its layout is the
  less settled of the two formats.
- **Positions only.** World positions cannot be retargeted: they fix a bone's direction but not its twist, so a forearm or
  a hand has no roll, and on a character of other proportions every position is wrong. They stay in the record as a check
  on the rotations.
- **BVH as the record.** Euler turns depend on their order and lose a turn at the poles, the format has no field for a
  pin, a digest or a take's report, and srstudio would need a second tolerant parser. The strict parser stops at the
  exporter.
- **A second pin for motion.** It would let the bridges disagree on what srlocations is, and it would need a second export
  folder that checks nothing the first does not.

## Consequences

- Motion reaches srstudio only as a record checked against srlocations' own joint positions, in srstudio's axes, by
  canonical joint name. `srstudio.skeleton` and `srstudio.dance` consume `MotionClip`.
- A record is bound to one pin, so moving the pin re-exports every recorded motion, not only the fixtures.
- The mannequin's proportions travel with the record. Retargeting onto a character is the skeleton's job.
- A take that srlocations clamped or only partly knew carries that in `source`, and a consumer decides what to do with it.
