# srstudio

srstudio is a Python toolkit for building animated episodes as [scene-render](https://github.com/pedroanisio/scene-render) scene documents. It combines the [sr-core](https://github.com/pedroanisio/sr-core) scene SDK with reusable characters, locations, props, graphics, audio and timeline helpers.

The library builds and validates scene XML. Rendering that XML into video requires the separate scene-render engine.

For AI coding agents, the [task-to-API entry points](docs/authoring-reference.md#agent-authoring-entry-points)
link discovery, typed inputs, clocks, capabilities, executable recipes and repairable failures.
The [authoring benchmark](docs/authoring-benchmark.md) measures discovery, planning, compilation,
rendering and cold/warm cache work with pinned fixtures and output-equivalence checks.
The [composition guide](docs/composition-preflight.md) covers strict scene manifests,
declared contacts, work budgets, verified vector/plate/proxy inputs, bounded rendering
and atomic scene or portable bundle emission. The [timeline workflow](docs/composition-preflight.md#emit-a-scene-timeline)
combines camera, light and parent motion with baked source clips under one render budget.

## Install

From the `srstudio` directory, using Python 3.10 or later:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[validate,test]'
```

The `validate` extra adds XSD and Schematron checks; `test` installs the development tools. The `sr-core` dependency is installed from Git at the revision pinned in `pyproject.toml`, so installation requires Git and access to its repository.

## Quick start

Build the self-contained sample project:

```bash
python examples/new_episode.py examples/out/coffee-review
```

This creates a synthetic dialogue, a tone-burst soundtrack, a caption font, `coffee-review.scene.xml` and `sdk-validation.json`. It makes no speech-provider call. Existing sample inputs and episode outputs are protected; use `--overwrite` to replace them deliberately. The sample needs DejaVu Sans Bold installed locally. If it is elsewhere, supply it explicitly:

```bash
python examples/new_episode.py examples/out/coffee-review --font /path/to/DejaVuSans-Bold.ttf
```

Once scene-render is installed, encode the scene:

```bash
scene-render encode examples/out/coffee-review/coffee-review.scene.xml
```

See [the complete sample](examples/new_episode.py) for a custom registered prop and location.

## How an episode is built

An `EpisodeSpec` describes the project and selects a style. `Episode` loads its timeline and assets, provides a canvas, and checks and writes the result. This complete example builds an office scene from synthetic input:

```python
from pathlib import Path

from srstudio import Episode, EpisodeSpec, cast, locations
from srstudio.sample import Line, write_sample_project

root = Path("examples/out/hello")
write_sample_project(root, [Line("manager", "Hello there.", 1.2)], angles=["wide"])

ep = Episode(EpisodeSpec(
    slug="hello",
    title="Hello",
    description="A first srstudio episode",
    root=root,
    seed=7,
))

ep.setup(
    locations.office_wide,
    ep.t.shots("wide"),
    at_desk=lambda group: ep.perform(
        cast.Manager(ep.cv), group, 560, 724, 1.45
    ),
)
ep.captions()
ep.audio()
ep.markers()
scene_path = ep.finish()
print(scene_path)
```

The default Cutout project uses `dialogue.json`, `assets/dialogue.wav` and a caption font under its root. Other styles use different inputs, such as a take timeline or a timed caption script. `Timeline.load()` chooses the format by content; see [timeline input examples](docs/authoring-timelines.md#timeline-input-formats). `shots()` accepts one angle name, a collection of names, or a predicate.

| API | Purpose |
| --- | --- |
| `ep.t`, `ep.P(i)` | Access the timeline and its phrases. |
| `ep.cv`, `ep.comp` | Draw with a `Canvas` into the scene composition. |
| `ep.setup(...)` | Place a location for selected shot intervals, using its callbacks to position content at the right depth. |
| `ep.perform(...)` | Place an actor with mouth poses, blinks, nods and actor-specific gestures. |
| `ep.captions()`, `ep.native_captions()` | Add drawn captions or engine-native caption tracks. |
| `ep.audio()`, `ep.markers()` | Add the project's audio mix and markers. |
| `ep.finish()` | Check the scene, write XML and a validation report, and return the XML path. |

`finish()` raises `SceneCheckError` on scene-check errors and, by default, on any finding; a missing signature raises `SignatureError`. If the diagnostic report cannot be written, the validation exception still describes the problem and chains the file error as its cause. The underlying SDK may also raise `sr_core.scene.SchemaValueError` during construction. Pass `strict=False` to allow warnings. Existing outputs are replaced by default; pass `overwrite=False` to refuse replacement, including files created during the build. Output and report paths must not alias the timeline, narration manifests, take or timing files, pinned clips, or scene-declared local assets, even when replacing outputs. If publishing one output succeeds and a later write fails, the exception identifies any published output and retained backup; inspect those paths before retrying. Custom `out=` and `report=` paths can use separate directories; their parents are created as needed. Relative input paths in the written scene are adjusted to continue resolving against the project root. See [audio, captions and episode workflows](docs/authoring-reference.md) for more options.

For numbered image, mesh, or volume sequences, the relative path from the output directory back to the project must not contain `%` or `#`: the renderer uses those characters as frame placeholders. Choose a different output directory if `finish()` reports this conflict.

When overwriting, `finish()` follows output symlinks that exist when it starts and checks their targets against project inputs. A symlink created at an output file after that check is replaced rather than followed.
Output directories are held open during installation; if a directory changes, the write fails instead of following the replacement. Pass `private=True` to restrict scene and report files and newly created output directories to the owner without changing the process umask.

## The parts

Explore the registered characters, locations, props and graphics from the command line:

```bash
srstudio styles
srstudio catalog --style cutout --kind location
srstudio inspect location office-wide
srstudio inspect prop coffee-cup --json
srstudio inspect character manager --json
```

srstudio errors retain their exception types and expose `error.to_dict()` with the versioned
`srstudio.diagnostic/1.0.0` envelope: `code`, `path`, `message`, `actual`, `expected`, `remedy`, `context`, and
`residual`. Semantic details that a legacy error does not supply are `null`; they are never guessed from its
message. Common head, spring, speech, gaze, placement, mouth, blink and keyframe failures provide explicit
[repair fields and a retry recipe](docs/authoring-diagnostics.md#repairing-authoring-input). Limb errors retain their existing codes,
geometric residuals and context. Payloads bound strings, collection sizes and nesting; nonfinite numbers become
strings so diagnostics remain valid JSON. Commands accepting `--json` write this envelope to stderr on failure,
including argument and plugin-import errors, and preserve their existing nonzero exit codes.

`inspect` shows the actual signature, parameter defaults, callback slots, documentation and a call template. Catalog and inspection results also show the registered version and latest approved default for each recorded part. In JSON these appear under `part_version`; character results also retain the legacy `character_version` field. A plain registered name identifies version 1; use `srstudio.parts.drawing(name)` for the latest approved drawing or pass a version explicitly. Version metadata reports the approval record separately; a replaced builder is marked unverified and cannot be used as an approved default or pin. Run `specimens.check(name, version)` to compare it with the approved drawing; proposed versions raise `NotApprovedError`. Non-character specimens use projects under `generated/episodes` by default, or the path supplied by `episodes=Path('/path/to/projects')` or `SRSTUDIO_EPISODES`. A successful check verifies that builder for the current process. Parts without a standalone specimen cannot be checked this way: `parts.restore(name, version)` restores their original registered builder, and `parts.drawing(name, version, allow_unverified=True)` permits proof work. Selected parts include runnable examples using an existing `ep`; try `coffee-cup`, `office-mug`, `stick-mug`, `toon-mug`, or `soft-coffee-machine`. Use `--plugins my_package.parts` to import a plugin before listing or inspecting its parts. `srstudio catalog --json` returns the listing as JSON.

The same information is available in Python:

```python
from srstudio import describe, get

info = describe("location", "office-wide")
print(info["signature"], info["slots"])
builder = get("location", "office-wide")
```

Inspection also includes a versioned `contract`: JSON Schema argument/return shapes, declared units and clocks,
capabilities, vocabularies, and helper operations. Actor contracts distinguish construction from `build`; Bento
exposes its `pose_of` vocabulary and identifies `duration` as the project exit time. Unknown metadata stays
explicitly unknown, and runtime objects such as a canvas are marked as runtime bindings. Contracts describe the
API; they do not deserialize records or replace builder validation. See the
[agent contract reference](docs/authoring-discovery.md#agent-contracts).

Core Cutout props, locations and graphics also declare placement units, clocks, return shapes and callback
semantics. Selected props publish local drawing anchors. Run `srstudio catalog --contract-coverage --json` to
see explicit declarations separately from inferred argument shapes and the remaining gaps. The
[location and held-prop recipes](docs/authoring-discovery.md#non-character-discovery-and-drawing-anchors) use
those contracts to place an actor and carry a cup between palm and fingers. Flat drawing anchors do not imply
spatial attachment or collision capabilities.

`srstudio usage` can measure which registered parts episode builds use; its JSON report can be supplied to `srstudio catalog --usage REPORT` and `srstudio page`. See the [catalog guide](docs/catalog/README.md).

## Styles

A `Style` supplies defaults for frame size, timing, input files, palette, captions and audio. Choose one with a value such as `EpisodeSpec(style=TOON)` after `from srstudio import TOON`; explicit spec fields override its defaults. Use `srstudio styles --json` for the current values, and look up a slug in `srstudio.styles.STYLES` when configuring Python code from JSON.

| Style | Main use |
| --- | --- |
| `CUTOUT` | Portrait dialogue scenes with office and café characters. |
| `INK` | Square, hand-drawn shot sequences. |
| `SOFT` | Pose-to-pose blob characters and beat-driven scenes. |
| `CEL` | Silent, traced drawings and lettering. |
| `STICK` | Stick figures, traced poses and painted sets. |
| `TOON` | Cartoon characters, poses, props and rooms. |
| `SAGA` | Space-opera sets and shot sequences. |
| `COLLAGE` | Mixed-media characters and sets. |
| `GLOSS` | Glossy characters and shot sequences. |

The [authoring reference](docs/authoring-styles.md#styles) compares their inputs, clocks, palettes and captions. [Character clips](docs/authoring-clips.md#character-clips-one-placement-and-timing-boundary) give Actor, split-head Toon, Gloss and prepared plates one explicit placement and timing boundary. The [limbs guide](docs/catalog/limbs.md) covers reusable arm and hand motion across styles; runnable examples are in [examples/](examples/).

[Coordinated acting](docs/authoring-acting.md#coordinated-acting-and-continuity) compiles typed emotion, speech,
gaze and head intent with explicit channel ownership. Reuse windows of one performance across cuts; inspect
rig capabilities before generating a score. The [two-family study](examples/acting_gallery.py) builds Bento and
Gloss Nadia with a reproducible scene and JSON continuity report. The
[listening and carrying study](examples/acting_continuity.py) adds sustained reactions and a moving hand/prop
interaction across a cut, with executable [authoring recipes](docs/authoring-acting.md#sustained-listening-and-repairable-capability-failures).

Opt-in [acting transition policies](docs/authoring-acting.md#opt-in-acting-transition-policies) add curves,
springs, anticipation, settling and separate channel arrival times through strict score schema 1.1.0.
Existing scores retain their output. The [transition comparison](examples/acting_transitions.py) demonstrates
faces arriving before heads, with cuts through anticipation and settling; faces remain held drawings, and
velocity/acceleration continuity and perceptual quality are not implied by easing.

[Versioned motion envelopes](docs/catalog/limbs.md#versioned-reference-envelopes) provide measured numeric
limits for explicitly scoped canonical human arms. The [quality study](examples/limbs_quality.py) builds
reference and rejected motions, strict render evidence and a separate blinded review packet. Numeric limits
and human ratings remain separate; these presets do not certify whole-body or perceptual quality.

Four shows are channels on Toon's road rather than styles of their own. Each is a `Style` value in its kit, passed as `style=` like any other, but `srstudio styles` and `STYLES` list only the nine above.

| Show | Value | Main use |
| --- | --- | --- |
| Mind | `mind_kit.MIND` | How people think: Toon's cast and sets under its own cards ([ADR 0055](docs/decisions/0055-mind-kit.md)). |
| News | `news_kit.NEWS` | A parody desk with its own set, anchors and graphics ([ADR 0060](docs/decisions/0060-news-kit.md)). |
| Host | `host_kit.HOST` | One talking character on his own set ([ADR 0066](docs/decisions/0066-talking-head-host-kit.md)). |
| Maps | `map_kit.MAPS` | The world on the engine's native maps ([ADR 0057](docs/decisions/0057-map-kit.md)). |

## Finish and plates

`srstudio.look` holds the primitives every style shares, while each style keeps its own numbers: `grade` for bloom, vignette and grain, `depth` for a far plane out of focus, `pool` for a soft light and `fade` for haze or a shade. See [finishing a style](docs/authoring-styles.md#finishing-a-style-srstudiolook) and [ADR 0031](docs/decisions/0031-shared-look-and-caption-primitives.md).

Caption breaks can keep phrases whole. With `CaptionLook(keep_together=True)`, or `keep_together=True` on `look.wrap`, no cue or line ends after a weak word such as `the` or `to`, inside a number such as `twenty thousand`, or inside a name such as `New York`, while another break fits. It is off by default so that a published reel rebuilds byte for byte, and new reels turn it on. `srstudio.caption_breaks.audit` lists the forbidden breaks in a built scene. See [ADR 0173](docs/decisions/0173-caption-breaks-keep-phrases-whole.md).

The library draws in 2D, and what it models in 3D is a clay character or a rigid proxy. `srstudio.clay` bakes a model to meshes, and `srstudio.plates` path-traces a `Plate`, one camera, one set of lights and some placed meshes, into a still cached by its digest. Rafa, who hosts the Host show, is built this way ([ADR 0068](docs/decisions/0068-rafa-clay-host-on-plates.md)).

3D locations come from srlocations, which runs in its own interpreter. `tools/location_export.py` runs there on an export of the pinned srlocations commit, checked file by file, and writes one JSON record of a location's shots: each camera and where every mark lands at the reel's frame size. `srstudio.location_bridge` reads it strictly, checks every pixel against the recorded camera, and gives a reel a mark's feet, scale and whether it is in frame. A location drawn next to our figures is in our cel/ink or clay look, never path-traced realism, and carries no brand, badge, livery or trade dress; its source photographs are Pedro's and stay out of the repository. See [ADR 0179](docs/decisions/0179-srlocations-location-bridge.md).

Motion comes from the same place. `tools/motion_export.py` runs in srlocations' interpreter on the same pinned export and writes one JSON record of a mannequin's motion, from a location module and a figure in it or from a BVH take: the 55 joints with their rest offsets and, per frame, the root and each joint's rotation as a unit quaternion. `srstudio.motion_bridge` reads it strictly, checks forward kinematics of the rotations against srlocations' own joint positions, and gives `MotionClip` and `MotionFrame` objects in srstudio's axes, by canonical joint name. See [ADR 0187](docs/decisions/0187-srlocations-motion-bridge.md).

Any character dances to any song with `srstudio.dance`: moves are data on the shared skeleton's canonical joints, timed by a `music.Groove`. Besides the bob, sway and nod presets it carries full-arm gestures (`clap`, `point-up`, `raise-the-roof`, `hand-wave-side`, `shoulder-roll`, `hip-sway`) and a `hands-up` pose to hold, each proved on the skeleton's forward kinematics on every preset character. See [ADR 0192](docs/decisions/0192-dance-arm-gestures.md) and the [dance guide](docs/authoring-dance.md).

Drawing digests remain stable; rendered artifacts additionally identify the renderer binary, compiled scenes,
quality settings and actual print font bytes. Use the path returned by `plates.render` or `print_png` rather than
constructing it from a drawing digest. [Plate cache ownership](docs/authoring-clips.md#plate-cache-ownership)
explains warm builds, legacy cache migration and catalog materialization.

[DRAWING.md](DRAWING.md) is the default drawing method for new work ([ADR 0091](docs/decisions/0091-hybrid-drawing-is-the-default.md)); published reels and approved drawings stay as they are. Its rigid-object layer is built: `srstudio.proxy` turns a clay model into cel plates, cut into back, front and under so people draw between them; `srstudio.vehicle` adds tyres and turning rims; `srstudio.on_beat` moves a drawing on a `music.Groove`, and `srstudio beat <audio>` measures that groove from a recorded track. [examples/car_vibe](examples/car_vibe) is the worked example. Its `forms` and `paint` modules are not built, and a type's first use of a layer needs an approved proof.

## Extending

Register a builder to make it available through the catalog and `get()`:

```python
from sr_core.scene import Composition, Group
from srstudio import Canvas, register

@register("prop", "status-light", summary="A small status indicator")
def status_light(cv: Canvas, parent: Composition | Group, x: float, y: float) -> Group:
    group = cv.group(parent, cv.uid("status-light"), x=x, y=y)
    cv.ellipse(group, -8, -8, 16, 16, "#5BB98C")
    return group
```

Call the builder while assembling the episode, before `finish()`. Duplicate kind/name registrations raise `RegistryError`; use `replace=True` for an intentional replacement. Location plugins can declare unannotated callbacks with `slots=("slot_name",)` and provide runnable inspection examples through `examples=`. See [the extension reference](docs/authoring-extensions.md#extending-drawing-calls).

## Signature

Signed episodes carry a small code and cactus. Built-in locations draw both automatically; a custom location should draw both through `srstudio.signature`. `EpisodeSpec.signature` defaults to `True`. The [signature reference](docs/authoring-delivery.md#signature) describes placement, customization and the cactus callback.

## Audio and delivery

`ep.audio()` selects the available source: pinned generated clips, take audio, one mixed file, verified narration, or silence. It uses the style's master levels unless `loudness=` or `true_peak=` is supplied. Explicit `mix()` settings update an existing mix; an implicit `mix()` or `add_track()` preserves the settings already chosen. Take WAVs are checked for readable container structure and supported format tags (PCM, IEEE float, A-law, μ-law, IMA ADPCM, and extensible PCM or float); failures raise `SoundtrackError` with their path. This check does not decode samples, so a renderer may still reject malformed audio. Convert other take WAV encodings to PCM or IEEE float before adding them. The soundtrack used for mouth animation requires 16-bit PCM; extra and narration files are not decoded by this check.

Recording and generated audio use separate workflows and may require provider credentials and permission to send data. See the [audio reference](docs/authoring-audio.md), [episode scripts](episodes/) and [recording module](src/srstudio/recording.py). For captions, covers, release checks and outbox packaging, see the [delivery reference](docs/authoring-delivery.md#instagram-captions). Pilots for a future channel go to their own Drive folder, never to @okayville.tv's: see [`publish_pilots.py`](episodes/publish_pilots.py).

Auto-enhance is on by default: each video lands one real change to the process on `develop` before its first delivery, and both delivery commands refuse a new video without it. `srstudio enhance` shows the mode and the ledger, `srstudio enhance kinds` the possibilities, and `srstudio enhance off` is the operator's switch back to just delivering. See [ADR 0056](docs/decisions/0056-auto-enhance.md).

New Okayville reels and News and Host pilots have a comedy floor: the lower of the author's and an independent reviewer's score must reach 14/20 at first delivery. Mind and Maps pilots and anything already delivered owe no score. See [ADR 0064](docs/decisions/0064-comedy-floor.md).

A hand is drawn through the shared `srstudio.anatomy` contract: the right is the mirror of the left, the arm decides the thumb's side, and a build refuses a hand on the wrong arm, a hand with no side, or a version with one drawing on both arms. `srstudio anatomy` lists the published reels exempted by name. See [ADR 0147](docs/decisions/0147-hand-chirality-is-a-build-error.md).

A body is declared too: `anatomy_parts.BODIES` says whether a character has legs, stops at the waist, or is a thing that is whole as drawn. A hand exists only on an arm, so a prop that draws one runs in `anatomy_ledger.on_arm`. `srstudio build` then reads the frames for a bust ending in the open and two hands on one arm, and first delivery reads them either way. See [ADR 0148](docs/decisions/0148-anatomy-is-a-build-error.md).

A figure draws one pair of hands. Toon and Collage poses record the hands they draw, and a swung Toon arm runs in `anatomy_ledger.on_arm`, so the frame rule `hand-count` counts each figure's hands across its pose groups, limb tracks and swung arms, whatever a sofa or the frame's edge covers. Raised arms over a pose whose own paws still rest are four hands. See [ADR 0174](docs/decisions/0174-a-figure-draws-one-pair-of-hands.md).

A burned caption does not run across a sentence end: a window that drops the stop, or keeps it and breaks off inside the next sentence, is a build error (`srstudio.text_rules`, the check `caption-grammar`). A window of whole sentences with their stops passes, and what is published stays as named rows of `assets/text_published.json` (ADR 0149).

A text is timed as a viewer sees it: `text_rules` reads the frames the engine evaluates and times the words from the first frame they are legible to the last, across layers and cuts, against the 0.8333 s reading minimum, along with each page of a burned caption track. The check is `text-timing`, run by `srstudio build` when it has an engine and at first delivery (ADR 0150).

Render the master with `srstudio master <slug>.scene.xml -- --strict`, which never replaces a master already there: approved files (masters, voice takes, songs, package versions) are write-once through `srstudio.files`, and a re-run writes beside them or stops ([ADR 0170](docs/decisions/0170-approved-files-are-write-once.md)). A reel's first delivery through `episodes/instagram_posts.py` also passes the frame gates, which refuse measured defects such as captions that run sentences together or signature marks the camera hides, and someone who is not the author reviews frames at full size. `publish_pilots.py` does not run these gates. See [ADR 0073](docs/decisions/0073-frame-gates-and-standing-review.md).

## Lanes

Batches and pilot sets run as `govern` lanes, so their state and token cost live in files: processes and exit checks are in [tools/govern/](tools/govern/), the reasons in [ADR 0058](docs/decisions/0058-govern-lanes.md).

## Verification

Run the local checks from the repository root:

```bash
python -m pytest --cov=srstudio --cov-branch
ruff check .
ruff format --check .
mypy src
```

The configured coverage gate is 80%. Some integration tests require additional local inputs and skip when they are unavailable:

| Variable | Input |
| --- | --- |
| `SRSTUDIO_PACKAGES` | Extracted packages for fidelity tests. |
| `SRSTUDIO_ENGINE` | A scene-render binary for engine tests. |
| `SRSTUDIO_EPISODES` | Generated episode projects for Collage build tests. |
| `SRSTUDIO_RENDERS` and `SRSTUDIO_FONTS` | Rendered videos and pinned fonts for the delivery gate. |

Every `render` and `encode` srstudio starts takes one machine-wide GPU lock, `/run/lock/srstudio-gpu.lock`. You can point it elsewhere with `SRSTUDIO_GPU_LOCK`. A job that waits longer than `SRSTUDIO_GPU_WAIT` seconds (900 by default) for another job's render stops with `GpuBusyError`, which names the holder's pid and command. To run a bare engine command by hand under the same lock, use `flock -w 900 /run/lock/srstudio-gpu.lock scene-render ...`. See [ADR 0171](docs/decisions/0171-one-gpu-job-at-a-time.md).

`srstudio scopes <video>...` reads a master's levels with the engine's `scopes` (every fifth frame). It fails on illegal codes, out-of-gamut and oversaturated samples, with a limit of 0 for each, and reports clipping without judging it. It exits 1 on a finding and 2 when a master cannot be measured. `scopes.scope_defects` is the first-delivery check. It is not wired into delivery, because all 240 masters measured on 2026-11-01 carry illegal samples. See [ADR 0172](docs/decisions/0172-master-levels-check.md).

## Layout

- [src/srstudio/](src/srstudio/) — library and CLI.
- [examples/](examples/) — runnable authoring and limbs examples.
- [episodes/](episodes/) — episode builders, recording scripts and releases.
- [tests/](tests/) — unit, integration and fidelity tests.
- [docs/decisions/](docs/decisions/) — architecture decisions.
- [Head motion internals](docs/decisions/0093-head-motion-module-boundaries.md) — module ownership and public API compatibility.
- [DRAWING.md](DRAWING.md) — the default drawing method for new work.
- [Authoring task index](docs/authoring-reference.md) — task guides for discovery, acting, timing, styles and delivery; links to episode history.

The project is licensed under MIT.
