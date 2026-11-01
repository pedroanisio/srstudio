# srstudio

srstudio is a Python toolkit for building animated episodes as [scene-render](https://github.com/pedroanisio/scene-render) scene documents. It combines the [sr-core](https://github.com/pedroanisio/sr-core) scene SDK with reusable characters, locations, props, graphics, audio and timeline helpers.

The library builds and validates scene XML. Rendering that XML into video requires the separate scene-render engine.

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

The default Cutout project uses `dialogue.json`, `assets/dialogue.wav` and a caption font under its root. Other styles use different inputs, such as a take timeline or a timed caption script. `Timeline.load()` chooses the format by content; see [timeline input examples](docs/authoring-reference.md#timeline-input-formats). `shots()` accepts one angle name, a collection of names, or a predicate.

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

SDK errors retain their exception types and expose `error.to_dict()` with the versioned
`srstudio.diagnostic/1.0.0` envelope: `code`, `path`, `message`, `actual`, `expected`, `remedy`, `context`, and
`residual`. Semantic details that a legacy error does not supply are `null`; they are never guessed from its
message. Gaze and missing-part errors provide explicit repair fields. Limb errors retain their existing codes,
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

The [authoring reference](docs/authoring-reference.md#styles) compares their inputs, clocks, palettes and captions. The [limbs guide](docs/catalog/limbs.md) covers reusable arm and hand motion across styles; runnable examples are in [examples/](examples/).

Four shows are channels on Toon's road rather than styles of their own. Each is a `Style` value in its kit, passed as `style=` like any other, but `srstudio styles` and `STYLES` list only the nine above.

| Show | Value | Main use |
| --- | --- | --- |
| Mind | `mind_kit.MIND` | How people think: Toon's cast and sets under its own cards ([ADR 0055](docs/decisions/0055-mind-kit.md)). |
| News | `news_kit.NEWS` | A parody desk with its own set, anchors and graphics ([ADR 0060](docs/decisions/0060-news-kit.md)). |
| Host | `host_kit.HOST` | One talking character on his own set ([ADR 0066](docs/decisions/0066-talking-head-host-kit.md)). |
| Maps | `map_kit.MAPS` | The world on the engine's native maps ([ADR 0057](docs/decisions/0057-map-kit.md)). |

## Finish and plates

`srstudio.look` holds the primitives every style shares, while each style keeps its own numbers: `grade` for bloom, vignette and grain, `depth` for a far plane out of focus, `pool` for a soft light and `fade` for haze or a shade. See [finishing a style](docs/authoring-reference.md#finishing-a-style-srstudiolook) and [ADR 0031](docs/decisions/0031-shared-look-and-caption-primitives.md).

The library draws in 2D, and a clay character is the one thing modelled in 3D. `srstudio.clay` bakes a model to meshes, and `srstudio.plates` path-traces a `Plate`, one camera, one set of lights and some placed meshes, into a still cached by its digest. Rafa, who hosts the Host show, is built this way ([ADR 0068](docs/decisions/0068-rafa-clay-host-on-plates.md)).

[DRAWING.md](DRAWING.md) proposes a layered drawing kit for every style and show. It is a proposal: its `forms` and `paint` modules are not built, and nothing adopts a layer without an approved proof.

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

Call the builder while assembling the episode, before `finish()`. Duplicate kind/name registrations raise `RegistryError`; use `replace=True` for an intentional replacement. Location plugins can declare unannotated callbacks with `slots=("slot_name",)` and provide runnable inspection examples through `examples=`. See [the extension reference](docs/authoring-reference.md#extending).

## Signature

Signed episodes carry a small code and cactus. Built-in locations draw both automatically; a custom location should draw both through `srstudio.signature`. `EpisodeSpec.signature` defaults to `True`. The [signature reference](docs/authoring-reference.md#signature) describes placement, customization and the cactus callback.

## Audio and delivery

`ep.audio()` selects the available source: pinned generated clips, take audio, one mixed file, verified narration, or silence. It uses the style's master levels unless `loudness=` or `true_peak=` is supplied. Explicit `mix()` settings update an existing mix; an implicit `mix()` or `add_track()` preserves the settings already chosen. Take WAVs are checked for readable container structure and supported format tags (PCM, IEEE float, A-law, μ-law, IMA ADPCM, and extensible PCM or float); failures raise `SoundtrackError` with their path. This check does not decode samples, so a renderer may still reject malformed audio. Convert other take WAV encodings to PCM or IEEE float before adding them. The soundtrack used for mouth animation requires 16-bit PCM; extra and narration files are not decoded by this check.

Recording and generated audio use separate workflows and may require provider credentials and permission to send data. See the [audio reference](docs/authoring-reference.md#new-episodes-with-generated-audio-five-years-06), [episode scripts](episodes/) and [recording module](src/srstudio/recording.py). For captions, covers, release checks and outbox packaging, see the [delivery reference](docs/authoring-reference.md#instagram-captions). Pilots for a future channel go to their own Drive folder, never to @okayville.tv's: see [`publish_pilots.py`](episodes/publish_pilots.py).

Auto-enhance is on by default: each video lands one real change to the process on `develop` before its first delivery, and both delivery commands refuse a new video without it. `srstudio enhance` shows the mode and the ledger, `srstudio enhance kinds` the possibilities, and `srstudio enhance off` is the operator's switch back to just delivering. See [ADR 0056](docs/decisions/0056-auto-enhance.md).

New Okayville reels and News and Host pilots have a comedy floor: the lower of the author's and an independent reviewer's score must reach 14/20 at first delivery. Mind and Maps pilots and anything already delivered owe no score. See [ADR 0064](docs/decisions/0064-comedy-floor.md).

Render with `scene-render encode --strict`. A reel's first delivery through `episodes/instagram_posts.py` also passes the frame gates, which refuse measured defects such as captions that run sentences together or signature marks the camera hides, and someone who is not the author reviews frames at full size. `publish_pilots.py` does not run these gates. See [ADR 0073](docs/decisions/0073-frame-gates-and-standing-review.md).

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

## Layout

- [src/srstudio/](src/srstudio/) — library and CLI.
- [examples/](examples/) — runnable authoring and limbs examples.
- [episodes/](episodes/) — episode builders, recording scripts and releases.
- [tests/](tests/) — unit, integration and fidelity tests.
- [docs/decisions/](docs/decisions/) — architecture decisions.
- [DRAWING.md](DRAWING.md) — proposed drawing architecture.
- [Authoring and episode reference](docs/authoring-reference.md) — detailed style, episode, signature and delivery notes.

The project is licensed under MIT.
