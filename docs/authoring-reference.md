# Authoring and episode reference

Detailed style, episode, delivery and verification notes for srstudio. Start with the
[library README](../README.md) for installation and a first working episode.
Run the commands below from the srstudio repository root.

## Agent authoring entry points

Start from the task, inspect the selected rig's capabilities, then use its typed API. JSON contracts describe
arguments; objects such as `Canvas` and scene parents remain runtime bindings. Do not infer a capability from
a similar character or pass contract JSON directly to a builder.

| Task | Entry point | Clock and capability checks |
| --- | --- | --- |
| Discover a character, prop or location | `srstudio inspect KIND NAME --json`; [agent contracts](#agent-contracts) | Read declared units, vocabularies, versions and runtime bindings; unknown fields remain unknown. |
| Place different character families | [Character clips](#character-clips-one-placement-and-timing-boundary) | One local performance clock and an explicit project interval; adapters enforce family capabilities. |
| Coordinate emotion, speech and listening | `parse_score`, `compile_performance`; [acting](#coordinated-acting-and-continuity) | Strict score schema, supported emotion maps and explicit channel ownership. |
| Add anticipation and staggered arrivals | [Transition policies](#opt-in-acting-transition-policies) | Opt-in score 1.1.0; declared phases must fit and respect contacts. Faces remain held drawings. |
| Carry state through a cut | [Listening](#sustained-listening-and-repairable-capability-failures) and [carrying](#carrying-a-prop-across-a-cut) recipes | Window one source performance; preserve contact, expression and texture clocks. |
| Author constrained arm motion | [Limbs guide](catalog/limbs.md) | Declare anatomy, reference units, projection and contacts; canonical-arm limits do not certify whole-body motion. |
| Repair invalid authoring input | [Diagnostic recipe](#repairing-authoring-input) | Match `code` and `path`, validate corrected input, and bound retries in ordinary code. |
| Evaluate motion quality | [Quality study](../examples/limbs_quality.py) | Keep numeric limits, strict rendering and human temporal ratings separate. |

## Repairing authoring input

SDK failures expose `to_dict()` using `srstudio.diagnostic/1.0.0`. CLI commands with `--json` emit the same
fields on stderr and add `context.command`, including SDK failures while importing plugins. Catch the
documented exception type; use `code`, `path`, `actual`, `expected` and `remedy` to identify the repair rather
than parsing the human message. Older validation sites that have not declared these facts retain null fields.

Common explicit paths include `style.breath_period`, `spring.damping`, `channel.keys[1][0]`,
`speech[0].words`, `heard[0].words`, `facing[0]`, `gaze[0][1]`, `performance.mouth[0][1]`,
`blink.period`, `visibility[0]` and `keys.rotation[1][1]`. Their code families are `head.style.*`,
`head.spring.*`, `head.channel.*`, `head.speech.*`, `head.facing.*`, `gaze.*`, `rig.*` and `canvas.*`.
The path identifies the supplied input, not a general-purpose object mutation expression.

This example repairs one known invalid setting and compiles a new plan. An agent should validate its proposed
correction through the same typed constructor. Unsupported capabilities require changing the request or rig;
retrying unchanged input cannot add a capability.

<!-- diagnostic-repair:start -->
```python
from dataclasses import replace

from srstudio.acting import BENTO
from srstudio.head_motion import HeadMotionError, plan

style = BENTO.head_rig.style
try:
    replace(style, breath_period=0)
except HeadMotionError as error:
    failure = error.to_dict()
    assert failure["code"] == "head.style.range"
    assert failure["path"] == "style.breath_period"
    assert failure["expected"] and failure["remedy"]
    repaired = replace(style, breath_period=3)

motion = plan(repaired, [], 4)
motion.check_bounds(repaired)
```
<!-- diagnostic-repair:end -->

Diagnostics are bounded previews, not a lossless copy of invalid input. Each payload field has a shared
1,000-node traversal budget and 16,384-character content budget, with at most 100 items per collection,
eight nesting levels and 4,096 characters per string. Metadata strings are capped at 4,096 characters.
Markers report exhausted traversal or depth; nonfinite numbers become strings, and opaque objects become
type labels. JSON escaping and punctuation add encoded bytes beyond these content budgets.

Generated blink schedules refuse more than 10,000 blinks before drawing. Carried springs also enforce their
sampled-key budget and scene clock precision. Reduce the requested work or use a suitable local clock when
those diagnostics fire. The tested mouth, visibility and keyframe preflights leave their scene unchanged;
this is not a blanket transaction guarantee for every legacy builder.

## Timeline input formats

`Timeline.load(path)` reads JSON and selects a format by its top-level shape. The same data can be passed to
`Timeline.from_dict(data)`. Times are seconds on the project clock unless described otherwise. Invalid records raise
`TimelineError` with the field or file to correct. These examples describe timing only; an `Episode` also needs the
assets and font selected by its `EpisodeSpec` and style.

Choose one object format: `phrases` for dialogue or `items` for takes. An object containing both is rejected so
take audio cannot be silently ignored.

A dialogue object has a positive `duration` and a `phrases` list. Each phrase needs a nonempty `role` and `text`
and an ordered `start`/`end` inside the duration. Optional `camera_cuts` must have strictly increasing times inside
the duration; `angle` selects intervals through `timeline.shots("wide")`. Optional named beats such as
`reaction_start` and `end_card_start` must be within the duration. `sound_effects` may be omitted.

```json
{
  "duration": 3.0,
  "phrases": [
    {"role": "manager", "text": "Hello there.", "start": 0.3, "end": 1.5}
  ],
  "camera_cuts": [{"time": 0.0, "angle": "wide"}],
  "reaction_start": 1.8,
  "end_card_start": 2.4
}
```

A take timeline has `duration` and `items`. Each take needs `id`, `actor`, `shot`, `text`, `start`, and positive
`duration`. Takes must be contiguous from zero; include pauses in a take's duration. `words` and `phones`, when
present, use times relative to that take. `audio` is optional when parsing, but `ep.audio()` needs an existing file
for every take; paths are relative to the project root. An effect uses `actor: "sfx"`.

```json
{
  "duration": 2.0,
  "items": [
    {"id": "01", "actor": "speaker", "shot": "wide", "text": "Hello.",
     "start": 0.0, "duration": 1.0, "audio": "audio/take-01.wav"},
    {"id": "02", "actor": "speaker", "shot": "close", "text": "Goodbye.",
     "start": 1.0, "duration": 1.0, "audio": "audio/take-02.wav"}
  ]
}
```

A silent caption script is a nonempty list. Each caption needs `start`, `end`, and nonempty `text`; captions must
not overlap. Its duration is the final caption's end. An optional `caption` overrides displayed text.

```json
[
  {"start": 0.0, "end": 1.2, "text": "Hello there."},
  {"start": 1.2, "end": 2.4, "text": "Goodbye.", "caption": "Goodbye!"}
]
```

See [`Timeline.from_dict`, `from_takes`, and `from_captions`](../src/srstudio/timeline.py) for the supported fields
and [`srstudio.takes`](../src/srstudio/takes.py) for producing recorded take timelines.

## Coordinated acting and continuity

`srstudio.acting` compiles a bounded score once, then places windows of that same
performance into shots. `BENTO` and `gloss_actor("nadia")` expose explicit artistic
emotion mappings through `describe()`; inspect capabilities before generating intent.
These names describe the author's intent, not a measured emotion or a universal
biomechanical model. Gloss supports its existing face, mouth, gesture and guest limb
controls; directed head motion, gaze and listening require a capable Toon head rig.

<!-- acting:start -->
```python
from srstudio.acting import BENTO, compile_performance, parse_score

score = parse_score({
    "schema": "srstudio.acting/1.0.0",
    "duration": 6,
    "seed": 17,
    "beats": [
        {"at": 0, "emotion": "neutral", "gaze": "left", "transition": 0},
        {"at": 1.2, "emotion": "happy", "gaze": "right", "transition": 0.4},
        {"at": 3.8, "emotion": "concerned", "transition": 0.4}
    ]
})
plan = compile_performance(BENTO, score)
after_cut = plan.window(3, 6)
assert after_cut.sample(0) == plan.sample(3)
assert after_cut.sample(0).gaze == "right"
# In a shot whose parent clock begins at zero:
# after_cut.place(cv, shot, at=0, placement=Placement(...), id="speaker")
```
<!-- acting:end -->

The decoded JSON parser rejects unknown fields and type coercions. Compilation then
checks vocabulary, timing, bounds, capabilities and conflicting ownership, raising
`ActingError` with `to_dict()` repair fields. Python authors can construct `ActingScore`
and `ActingBeat` directly. Scores are limited to 600 seconds, 1,000 beats and 20,000
sampled keys per numeric channel; the default sampling rate is 30 Hz.

Discrete expression, gaze and gesture changes occur at `at + transition`. Numeric
`HeadTarget` fields and `breath` ease during that interval using sampled sine easing.
`breath` is a held expansion in 0..1, not an oscillation gain. A reset returns authored
channels to the rig's neutral/procedural state. Emotion defaults persist until replaced;
an explicit beat field wins over its emotion default. Directed eyes lead inferred head
turn by 80 ms; explicit head targets win over that inferred turn. Omitted fields preserve
their prior owner. These transitions do not morph between drawings or promise continuous
velocity at arbitrary changes in authored intent.

`SpokenLine(at, alignment, levels)` uses line-relative character alignment and measured
dB samples at 100 Hz; `at` is on the performance clock. `speech` drives the mouth and
head; `heard` supplies another speaker's prosody for listening without opening this
character's mouth. Audio assets are placed separately. Full `Overrides` tracks take
precedence over beat channels; `None` inherits, while an empty track requests defaults.
A `HeadPlan` override owns numeric head channels and gaze together. Typed limb tracks
own gestures; conflicting explicit gestures are rejected. Runtime overrides are Python
bindings passed to `parse_score(..., overrides=...)`, never opaque generated JSON.

`window(start, end)` uses absolute performance endpoints; `place(..., at=...)` uses the
parent clock. The returned group runs on the original performance clock, so attached
drawings must use that clock too. Random-access sampling preserves expression, gaze,
breathing phase, contacts and attachment state across cuts. A reset during an active
limb contact or prop attachment fails until its explicit release. Spatial limb samples
describe the source motion; baked rendering still uses the selected limb frame rate.

Run the two-family silent study with licensed font assets and a JSON state report:

```sh
python examples/acting_gallery.py ../generated/sdk-acting
scene-render validate ../generated/sdk-acting/acting-gallery.scene.xml --deny-warnings
scene-render encode ../generated/sdk-acting/acting-gallery.scene.xml --strict
```

### Opt-in acting transition policies

Score schema `srstudio.acting/1.1.0` adds a versioned `policy` to each beat. Existing
1.0.0 scores retain their output and reject this new field. Python uses
`TransitionPolicy` and `ChannelTiming` from `srstudio.acting`; inspect
`BENTO.describe()["transitions"]["policy"]` for supported channels, curves and bounds.

<!-- acting-policy:start -->
```python
from srstudio.acting import BENTO, compile_performance, parse_score

score = parse_score({
    "schema": "srstudio.acting/1.1.0", "duration": 4, "idle": False,
    "beats": [
        {"at": 0, "head": {"turn": 0}, "transition": 0},
        {"at": 1, "emotion": "happy", "head": {"turn": 2}, "transition": 0.7,
         "policy": {
             "version": "1.0.0", "curve": "spring",
             "spring": {"frequency": 3, "damping": 0.85},
             "anticipation": 0.2, "anticipation_amount": 0.1,
             "settle": 0.3, "overshoot": 0.1,
             "timing": [{"channel": "expression", "duration": 0.1},
                        {"channel": "turn", "delay": 0.08}]
         }}
    ]
})
plan = compile_performance(BENTO, score)
assert plan.sample(1.1).emotion == "happy"
assert plan.window(0.9, 3).sample(0.2) == plan.sample(1.1)
```
<!-- acting-policy:end -->

Each channel launches at `beat.at + delay` and arrives after its timing `duration`
(default: `beat.transition`). Numeric anticipation starts **before** launch, moving
opposite the target delta by `anticipation_amount`. Arrival can exceed the target by
`overshoot`; positive `settle` then returns to it. These amounts are fractions of the
delta, not absolute angles or pixels. Springs default to 3 Hz and damping 0.75; an
explicit spring uses 0.1–20 Hz and damping 0.1–2. Its own `anticipation` must be zero:
the policy owns that phase. Other curves use the shared `Channel` sampler.

Expression, gesture and gaze remain held drawings that switch at their individual
arrival times. The emotion label follows expression timing. Speech owns mouth timing.
Gloss can stagger supported drawing channels; numeric easing/anticipation on a beat
without numeric targets is rejected. A timing entry must name a unique, supported
channel assigned by that beat. Reset also assigns procedural numeric channels on Toon;
ordinary `HeadTarget` assignments retain their existing five fields.

All phases must fit inside the performance and cannot overlap another transition on
the same channel. Reset phases cannot cross active contacts or prop attachments.
Whole-channel overrides keep precedence, but cannot hide an invalid policy excursion.
Rendered head channels stay inside rig limits, and policy-driven breath stays in 0..1.
Numeric anticipation/settling requires a positive transition at six-decimal scene
precision. A zero-duration numeric arrival changes within one scene quantum
(one microsecond), preserving the preceding hold; discrete drawings switch directly.

Policies bake linear keys at at least 240 Hz inside their intervals (at least 32 samples
per spring cycle), retaining phase boundaries and the score's ordinary sample grid.
The compiler limits candidate keys to 20,000 per channel before adding a dense interval.
These are bounded sampled motions, not a continuous physical simulation. Position,
velocity and acceleration are separate properties: policy baking does **not** guarantee
velocity or acceleration continuity, and it never implies facial morph support.

The executable [transition study](../examples/acting_transitions.py) compares legacy,
anticipated and spring timing, with cuts during anticipation and settling. It exports
the exact score JSON, source hashes and state report; human ratings remain explicitly
absent. Build into a new directory, then render:

```sh
python examples/acting_transitions.py ../generated/sdk-acting-transitions
scene-render encode ../generated/sdk-acting-transitions/acting-transitions.scene.xml --strict
```

### Sustained listening and repairable capability failures

Use `heard` for the other speaker's lines. Keep one plan across their phrases and cuts;
recompiling at each phrase restarts the procedural performance. This executable fixture
is deliberately synthetic and silent. Its constant levels are not measurements.

<!-- listening:start -->
```python
from srstudio.acting import (
    BENTO, ActingBeat, ActingError, ActingScore, SpokenLine,
    compile_performance, gloss_actor,
)
from srstudio.voice import Alignment

synthetic_alignment = Alignment(
    tuple("Hello."), (0, .1, .2, .3, .4, .5), (.1, .2, .3, .4, .5, .6)
)
heard = tuple(
    SpokenLine(at, synthetic_alignment, (-24.0,) * 60)
    for at in (.5, 2.2, 4.0)
)
score = ActingScore(
    6, (ActingBeat(0, gaze="right", transition=0),), heard=heard, seed=1
)
listener = compile_performance(BENTO, score)
assert listener.sample(3) == listener.window(3, 6).sample(0)
assert listener.sample(1.1).mouth == "closed"

try:
    compile_performance(gloss_actor("nadia"), score)
except ActingError as error:
    diagnostic = error.to_dict()
assert diagnostic["code"] == "acting.unsupported"
assert diagnostic["path"] and diagnostic["expected"] and diagnostic["remedy"]
```
<!-- listening:end -->

For a real recording, parse its alignment with `Alignment.parse`, then obtain measured
levels with `head_motion.speech_of(alignment, at, audio_path).levels` and pass those to
`SpokenLine`. Place the recording as a separate scene audio asset at the same performance
offset. Do not substitute the synthetic levels above for measured prosody. The planner
selects reactions deterministically from the rig style and seed; it need not nod at every
phrase. This fixture's seed produces three reactions, with the middle reaction continuing
through the cut.

### Carrying a prop across a cut

An attachment belongs to the source motion. Bind it once, then observe the same plan
through both shot windows. This compact recipe demonstrates state ownership; the complete
rendered interaction below adds moving contact, prop geometry and depth compositing.

<!-- carrying:start -->
```python
from dataclasses import replace
from srstudio.acting import ActingScore, Overrides, compile_performance, gloss_actor
from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, Vec3
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.integration import LimbTrack
from srstudio.limbs.motion import Action, Attachment, Motion

motion = Motion(ArmProfile(), HUMAN, (Action("grasp", duration=6),))
offset = Frame(Vec3(0, .37, .19))
initial = motion.sample(1.2).hand.frame.compose(offset)
motion = replace(motion, attachments=(Attachment("cup", 1.2, 5, initial, offset),))
track = LimbTrack(
    motion, style="gloss", camera=Camera(origin=(-92, -345), scale=200),
    options=BakeOptions(fps=24), backend="baked",
)
source = compile_performance(
    gloss_actor("nadia"), ActingScore(6, overrides=Overrides(limbs=(track,)))
)
after_cut = source.window(3, 6)
assert after_cut.sample(0) == source.sample(3)
cup_at_cut = dict(after_cut.sample(0).limbs[0].props)["cup"]
assert cup_at_cut == motion.sample(3).hand.frame.compose(offset)
```
<!-- carrying:end -->

`Attachment` verifies that acquisition does not jump and holds the release frame after
release. It does not draw the prop. `bake_interaction` combines a `Participant` hand and
`PropDrawing(mesh, AttachedProp(motion, "cup"))` in the same canonical coordinates,
sorting their surfaces together. Do not draw a second copy of that hand with `LimbTrack`
in the same view. For an isolated interaction, place the compositor under the performance
window's returned group with `Canvas(local_time=True)` and an explicit full-source
`BakeOptions(duration=6)`. The group supplies the source clock; baking just the shot length
would discard later motion. The limb and prop must use the same projection, placement,
facing and parent transform. Adding a prop beside a bobbing character's root does not
automatically inherit its body bob or anatomical reflection.

The complete study combines a sustained Bento listener and an isolated hand that lifts,
carries and replaces a cup. A camera cut occurs while both are moving. It includes a
serialized motion, exact listening-score JSON, licensed font, explicit synthetic-input provenance,
SDK schema validation and numeric report:

```sh
python examples/acting_continuity.py ../generated/sdk-continuity
scene-render validate ../generated/sdk-continuity/continuity.scene.xml --deny-warnings
scene-render encode ../generated/sdk-continuity/continuity.scene.xml --strict
```

For changing emotion and the same intent on two rig families, run
[`acting_gallery.py`](../examples/acting_gallery.py) from the preceding section. These
studies demonstrate supported clocks and composition; they do not certify emotional
readability, collision-free gripping or whole-body balance.

## Styles

A **style** is what an episode looks like before a single part is placed, and it is a value:
`srstudio.styles.Style` holds the frame and rate, the clock, the input file, the caption font, the palettes the style
is drawn in (with a mouth model per palette), the id scheme, accessibility defaults and the modules that hold its
parts. `EpisodeSpec(style=…)` resolves every field the episode does not set; an explicit field still wins; a palette
the style is not drawn in is a `StyleError`. The names and the reasoning are in
[docs/decisions/0002-style-names.md](../docs/decisions/0002-style-names.md),
[docs/decisions/0003-soft-style.md](../docs/decisions/0003-soft-style.md),
[docs/decisions/0004-cel-style.md](../docs/decisions/0004-cel-style.md),
[docs/decisions/0006-stick-style.md](../docs/decisions/0006-stick-style.md) and
[docs/decisions/0010-toon-style.md](../docs/decisions/0010-toon-style.md),
[docs/decisions/0025-saga-style.md](../docs/decisions/0025-saga-style.md),
[docs/decisions/0030-gloss-style.md](../docs/decisions/0030-gloss-style.md) and
[docs/decisions/0026-collage-style.md](../docs/decisions/0026-collage-style.md); `srstudio styles` lists
all nine. The table compares the first seven; Collage and Gloss are described in their own sections below.

| | **Cutout** — `CUTOUT` (default) | **Ink** — `INK` | **Soft** — `SOFT` | **Cel** — `CEL` | **Stick** — `STICK` | **Toon** — `TOON` | **Saga** — `SAGA` |
|---|---|---|---|---|---|---|---|
| Look | Flat vector shapes, soft gradients, bold outlines, like paper cut-outs | Pen stroke, one ink and one grey on white paper | Round white blob characters, one dark outline, flat warm stage, pose-to-pose | Traced, filled drawings with no outline, held per run under a measured camera push; silent | Stick figures in heavy ink traced at 12 fps, on painted, flat-shaded sets; dancers with badge heads | Flat cartoon in heavy ink on a gradient room: a cat whose expression swaps per cue and a brush-drawn, lip-synced cast, each phrase in a white pill; narrated portrait recreations and sketches | Space-opera parody in heavy ink: a lit, shaded cast on sets whose far plane is out of focus, glowing holograms sized to their words, one grade (bloom, vignette, grain) over every shot |
| Palettes | `OFFICE` (cool, stage `#D5DFDF`), `CAFE` (warm, stage `#F0DDC0`) | `MONO` (stage `#FFFFFF`) | `WARM` (stage `#F3DFCF`) | `LINEN` (stage `#c5bbb0`, shade = the lettering box teal) | `DAYLIGHT` (stage `#bda77a`, shade = the sets' brown line `#665541`) | `PEACH` (stage `#f8ead9`, shade = the cat's blue `#5bb7db`) | `VOID` (stage deep space, paper warm, shade gold) |
| Frame | 1080×1920 portrait, 30 fps | 1080×1080 square, 24 fps | 1080×1920 portrait, 30 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps | 1080×1920 portrait, 24 fps |
| Clock | one composition on the project clock; camera setups gated by hold keys | a `<sequence>` of shots, each as long as its take; animations on the shot clock | one composition; each look of a character gated by hold keys on a beat grid (`music.Groove`) | one composition; the world group carries the measured camera (`cel.world`), the room its own inside it (`cel.compensate`); linear keys on the local clock, held to the end | one composition; each traced pose a group alive from its start to its end, each set a group per shot | one composition; each pose a group alive from its start to its end, the typing forearm keyed on the composition clock so it dips on the foley's keystrokes | a `<sequence>` of shots, each as long as its take; animations on the shot clock |
| Input | `dialogue.json` + one mixed `assets/dialogue.wav` | `timeline.json` with takes (words, character timestamps, one audio file per take) | `dialogue.json` with pinned generated clips + `assets/groove.wav` from `music.render` | `script.json`, a list of timed captions; the measured camera, pose runs and drawings are read from `assets/` (`cel.load_*`) | `script.json`, timed captions with a size; poses, icons, lettering and foliage are read from `assets/` (`stick.load_*`) | `script.json`, timed captions, and `assets/poses.json` (eyes, mouth, arms per run), both derived from the episode's data module (`toon.load_*`) | `timeline.json` with takes from `srstudio.takes` (words, character timestamps, one audio file per take) and the music bed |
| Mouths | five shapes from RMS amplitude windows (`OFFICE_MOUTH`, `CAFE_MOUTH`, chosen by palette) | five poses from character timestamps (`INK_MOUTH`, `phoneme_states`) | `SOFT_MOUTH` amplitude states drive the `sing` mouth of a cue | none: the style is silent and `mouth_style` resolves to `None` | none: `mouth_style` resolves to `None`; voice is narration over the captions | none: `mouth_style` resolves to `None`; the mouth is one of six drawn shapes per pose | visemes from character timestamps (`lipsync.SPEECH_MOUTH`); masked characters talk with a light |
| Captions | DejaVu Sans Bold, bottom captions with highlighted spans | Patrick Hand, top captions paged from word timings (`subtitles.chunk_words`), plus an SRT | Poppins Bold from Google Fonts (`srstudio fonts add`), dark text with a white outline at the top (`captions(color=, shadow=None)`) | traced lettering (`cel.lettering`: boxes in the shade, glyphs as white paths), no font asset, plus an SRT | Inter Bold, white with an ink outline outside, one line per cue (`stick.captions`); hook and headline are traced lettering; plus an SRT | Comic Neue Bold Italic from Google Fonts (pinned), ink text centred in a white pill whose width is measured from the font file (`fonts.text_width`), plus an SRT | Space Grotesk 700 from Google Fonts (pinned); the engine's native karaoke captions, a long line split at words (`native.cues_from_takes`) |
| Audio | `ep.audio()` (one mixed file) | `ep.audio(take=…)` (one file per take; master −14 LUFS) | `ep.audio(extra=[("groove", …, {"role": "music"})])` (pinned clips) | none (no `<assets>`, no `<audioMix>`); `ep.audio(narration=…)` for a narrated master | none in the picture; `srstudio.dub` adds a voice-over and a music bed to the built scene | none in the silent master; `ep.audio(narration=…)` plus one effects track per bed (typing, camera click) in the narrated one | `ep.audio(take=…, duck=…)`: one file per take panned by speaker, effects, the music bed ducked under lines |
| Ids | `path-0001` | `shared_counter()` → `g1, p2, e3` | `path-0001`; looks are `<character>-<pose>-<digest>` | `flat_counter("v")` → `v1, v2, v3` for every node | `flat_counter("n")` → `n1, n2, n3` for every node | `flat_counter("k")` → `k1, k2, k3` for every node | `flat_counter("s")` → `s1, s2, s3` for every node |
| Parts | `cast`, `locations`, `props`, `graphics`, `camera` | `ink`, `ink_captcha`, `ink_doorbell`, `ink_meter`, `ink_phone`, `ink_vacuum`, `subtitles` | `blob`, `soft_props`, `soft_sets` | `cel` | `stick`, `stick_airport`, `stick_car`, `stick_door`, `stick_flat`, `stick_gym`, `stick_home`, `stick_office`, `stick_school`, `stick_shop`, `stick_street`, `stick_windshield` (the reel builder is `stick_reel`) | `toon`, `toon_cast`, `toon_dinner`, `toon_everyday`, `toon_bento`, `toon_critters`, `toon_inked`, `toon_props`, `toon_rooms`, `toon_sets`, `toon_wear` | `saga`, `saga_sets` (the reel builder is `saga_reel`) |

The parts of one style are usable in the other (they draw with the canvas's ink, paper and shade), and the signature
marks adapt to the palette, so `srstudio catalog --style ink` lists Ink's own parts plus the shared ones.
`Timeline.load` picks the input format by content (`phrases`, `items`, or a list of captions). It raises
`TimelineError` for invalid ranges or unordered cuts. Shot-sequence takes must be contiguous from zero
(within one microsecond of recording roundoff); include pauses in a take's duration. Word and character
times must stay within their take. Frame-rounded trailing silence is allowed, and validation never retimes inputs.
A new style is a `Style` value, usually
`dataclasses.replace` of an existing one, plus a module of parts named in its `parts` (see `ink.py`: ~40 lines of
drawing conventions before the first character, or `blob.py`: a pose sheet); nothing in `Episode` is specific to a
style.

### Lip sync

`Performance.mouth` and `Episode.perform(mouth=...)` use `(project second, pose)` sequences. The base actor's
vocabulary is `srstudio.rig.MOUTHS`: `rest`, `round`, `open`, `small`, `smile`. In particular, use `rest`, not
the `closed` state from other styles. Actors reject unknown names, malformed pairs and nonfinite, negative or
decreasing times with `RigError` before drawing. Custom actors can extend `Actor.mouth_poses` alongside their
`draw_mouths()` implementation; retain `rest` for the default performance.

`srstudio.lipsync` turns what is said into mouth poses ([ADR 0019](../docs/decisions/0019-lip-sync.md)). The shipped
mouths stay the default, so delivered episodes rebuild unchanged. New episodes opt in:

```python
from dataclasses import replace
from srstudio import OFFICE_MOUTH, SPEECH_MOUTH, ink, sketch

ink.mouth(cv, g, take, style=SPEECH_MOUTH)                    # timestamped takes (Ink, Toon sketches)
sketch.record(sk, root, client, key=key, mouth=SPEECH_MOUTH)
ep.mouth("candidate", style=replace(OFFICE_MOUTH, letters=True))  # amplitude mouths that know the line's text
```

- `SPEECH_MOUTH` reads English spelling (*ph* is an f, the *h* of *th*/*sh*/*ch*/*wh* holds the consonant, *w* and
  *qu* round, a silent final *e* or *gh* holds the pose before it), closes the mouth on every *b*, *m* and *p* even
  when the sound falls between two samples, shows each sound 0.04 s early, and keeps the mouth open over a pause
  between words shorter than 0.12 s.
- `PhonemeStyle(first_sound=True)`, off by default, opens a take the trim cut on the sound due at its first second.
  Samples run on the clock of the file, so a trim drops the sample at its second 0 and the mouth would otherwise stay
  shut until the next one, about 0.08 s into the first sound.
- `MouthStyle(letters=True)` spreads the line's letters in order over the frames where it is voiced (a vowel weighs
  twice a consonant). The letters choose round, closed or open; the amplitude still chooses how open. Without it,
  the round mouth comes from a clock pattern, unrelated to the words.
- `srstudio lipsync TIMELINE...` scores the shipped and the speech mouth over the takes of timelines with character
  timestamps: bilabials closed, word joins snapped shut, and pose changes a second.
- `srstudio lip-proof PROJECT --master MP4 --out DIR` picks mid-word instants across a recorded reel, prints the pose
  the mouth track holds at each one, names any vowel on a shut mouth, and pulls those frames from the master to compare
  by eye.

### Engine-native captions, transitions, effects and text animators

`srstudio.native` writes the scene-render elements the library used to draw by hand
([ADR 0021](../docs/decisions/0021-engine-native-features.md); the map of adopted features is
[docs/engine-features.json](../docs/engine-features.json)). All of it is opt-in:

```python
from srstudio import native
from srstudio.native import CaptionLook

ep.native_captions()                                     # the takes' words, sung word by word, burned in
ep.native_captions(look=CaptionLook(preset="pop", upper=True, max_chars=18), mode="both")  # + a WebVTT sidecar
native.transition(shots, "shot-01", "shot-02", "whip-pan", duration=0.4)
cv.apply(layer, cv.effect("lift", "drop-shadow", offsetY=8))
cv.animate_text(layer, "pop")
```

- A caption track is centred on the safe area with its last line on the region's bottom edge. With the episode
  font, every wrapped line is measured against the safe width, so a line too wide is refused before the render.
  Capitals are wider: an uppercase look needs `max_chars` of about 18 at 53 px.
- `mode="sidecar"` or `"both"` makes `scene-render encode` write `<video stem>.<track>.<language>.vtt` beside the video.
- `CaptionLook(min_last=2, min_seconds=0.84)` makes captions readable
  ([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)). A cue whose last line would hold a lone
  word is split after a clause end, else where its halves balance. Each cue is held into the silence after it
  for `min_seconds` (the engine's minimum is 0.8333 s), and a split that would show a half more briefly is not
  made. A long take's last cue that is too small to read is re-cut with the one before it. The house look
  leaves both off, so delivered videos rebuild unchanged.
- Cues out of order or overlapping, words outside their cue, and a transition between shots that are not
  neighbours (or longer than either shot) raise `NativeError`. An unknown preset or type raises the SDK's
  `SchemaValueError`.

## The parts

Give repeated graphics distinct `id=` values. Each custom instance namespaces its text assets and layers as
`<instance id>-<text id>`; the default instance retains the original IDs. A part named with an explicit `prefix=`
or `text_id=` keeps that name on any instance, so give each such instance its own prefix.

`Canvas.gate` merges overlapping and touching visibility spans, independent of their input order; empty spans
draw nothing, and reversed, negative or nonfinite spans are refused before adding animation. Named linear and
radial gradients reuse identical declarations and raise `NativeError` for conflicting types, stops, coordinates,
units or interpolation spaces. Stick's user-space gradients use the same checks.

`srstudio catalog` lists them; `srstudio catalog --json` is machine-readable, and `--usage REPORT` adds the episodes
that use each part, from the report below.

Which episodes use a part is measured, not declared: `srstudio usage`
rebuilds every episode project on a copy and records each registered part its build calls
([ADR 0017](../docs/decisions/0017-measured-part-usage.md)). It prints the used and unused parts per kind and writes the
report that `srstudio page --usage` reads:

Rig drawing and Canvas ID allocation emit explicit `drawing_events` notifications. Custom performers can use
`with drawing_events.drawing(registered_part_name):` around their drawing calls; `usage.trace()` then records
the part and the IDs allocated by `cv.uid()`, including IDs from custom namers. Nested scopes count every used
part and associate IDs with the outermost character. An unknown explicit name raises `UsageError` while tracing.
`drawing_events.observe(callback)` receives paired begin/end events and ID events in the current execution
context; end events include `successful`. Observation and profiler state are restored on exceptional exit.
Existing registered functions and class methods retain automatic tracing, including the legacy delegate fallback.
The head emitter's private name, signature and code object no longer identify the character.

```bash
srstudio usage --episodes ../generated/episodes --packages ../generated/packages --scripts episodes \
    --work _tmp/usage-work --out ../generated/catalog/usage.json
```

A project with a `voiced/` recording whose script takes `--voice` is built from it, as its delivered master was;
`--arg SLUG=OPTION` passes any other option to one episode's script. A project with no script in `--scripts` is listed
as not measured. So is an episode whose build fails: the others still run, the report is written, the failure is
printed and the exit code is 1; when every build fails nothing is written. `--skip SLUG` leaves out a project that cannot
build yet (one still in progress, with no `timeline.json`): it is reported as not measured, and a skip that names no
project is refused.

- **Characters** (`srstudio.cast`): `Manager`, `Candidate` (office rig: five mouth shapes, blink overlay, head nods,
  static or articulated arms, raised brows, pupils, facepalm, pointing forearm), `Barista`, `Customer` (café rig;
  standing or `seated=True`, phone, held cup) and `pigeon`. Subclass `Actor` (or `OfficeActor`/`CafeActor`) and override
  `draw_body`, `draw_head`, `draw_eyes`, `draw_face_front`, `draw_blink`, `after_head` to add one.
  (`srstudio.ink`): `human` (the round-headed doodle, drawn per take with its mood: waiting, pointing, screaming),
  `printer` (a talking prop: LED and voice marks when it speaks, shaking shell and bobbing paper when it whirrs) and
  `router` (`talking-router`: four LEDs chase and the antennas bob when it speaks; `power="down"`/`"up"` steps the
  LEDs off or sweeps them on for a reboot, `drop_at=` blacks them out mid-take; the model plate carries the signature).
  (`srstudio.blob`): `pip`, the sprout-headed blob of the Soft style, one rig of five tapered brush `Stroke`s
  (legs, torso, arms) and a head. Every pose in `POSES` (stand, step, walk-a/b, stride, sit, type-a/b, nod, clasp, lean,
  groove-a/b/c, cheer-a/b, wave-a/b) has the same limbs, so any two interpolate: a `Cue(ease=)` arrives through smoothstep in-between
  drawings (`blob.drawings`, 15 a second) and lands on its beat. Poses blend in pose space while position and turn blend
  apart, so a turn rotates instead of shrinking limbs; `lift=` arcs a move, `overshoot=` lands past the pose and
  settles a drawing later, and `pin="leg_l"` keeps that foot planted and solves the position from it (a side-step
  walks with `walk-a`, `stride`, `walk-b`, `stand`). The expression changes when the pose lands. `blob.cue(when,
  pose, spot, scale=, ease=)` places a cue at a spot in output pixels, and `blob.settle(cues, fps)` caps each ease so
  no move starts before the previous pose has landed
  ([docs/decisions/0016-episode-helpers-in-the-library.md](../docs/decisions/0016-episode-helpers-in-the-library.md)). Limb paths are
  hold-keyed per drawing in two passes (outline, then fill) so the body merges under one outline; arms switch to a
  front pass whenever they cross the body (standing, walking, clasped hands; seated, only the near arm and leg, the
  far arm stays behind in 3/4 view). A front limb is filled, then traced along its sides and tip only
  (`Stroke.contour`), so it grows out of the body instead of sitting on it; a limb moving to or from the front
  travels behind the body. Every arm and leg keeps its length in every pose (tested
  within -20 %..+25 %), so limbs bend at elbows and knees instead of stretching.
  `shadow=True` keys a contact shadow under the feet. Eyes `EYES` (ring eyes with pupils, look, wide, happy, squint, closed) and mouths `MOUTHS` follow the head;
  `sing` follows the soundtrack (`blob.mouth_track`). The rig is `blob.blob(..., look=)`: a `Look` names the body
  fill, blush, topper, hair and features, so `pip` is the rig in `PIP` (white, blush, sprout) and `bo`, the boss,
  the same rig and pose sheet in `BO` (pale blue, side-parted hair, square glasses, no blush). Two more looks
  are polished: `juno` in `JUNO` (apricot, auburn bun and scrunchie, scalloped bangs, freckles, lashes) and `remy`
  in `REMY` (lavender, curling tuft, headset with mic boom, gloss). A look may turn on `shade` (a crescent away
  from an upper-left light), `gloss`, `catchlights` and `lashes`; all are off by default, so Pip and Bo draw as
  before ([ADR 0007](../docs/decisions/0007-polished-looks.md)). A seated `lounge`
  pose rests both hands on the near thigh, for the sofa.
  (`srstudio.cel`): `traced` (`cel-traced`): a traced character as a sheet of filled drawings, one held per run of
  the pose timeline; drawings and runs are data (`cel.load_drawings`, `cel.load_runs`), parsed and refused when
  malformed (`cel.CelDataError`).
- **Locations** (`srstudio.locations`): `office_wide(at_desk=)`, `office_reverse(in_chair=)`,
  `cafe(behind_counter=, at_counter=, on_counter=)`, `park(on_bench=, beside_bench=)`. Each takes `shots=` and gates its
  root group before drawing, so new locations should do the same (see `examples/new_episode.py`). `park(sign_lettering=False)`
  keeps the sign's board and code but drops its lettering, for a framing that crops the sign: SA01 measures text off frame too. Two polished rooms
  add window and lamp light as a `-light` glaze group: `conference_room(behind_table=, on_table=, rising=,
  speaker_talk=)` (blinds, whiteboard, speakerphone, walnut table; `speaker_talk` spans light the speakerphone's ring
  while a caller speaks, as `props.speakerphone(talk=)` does) and `reception(behind_desk=, on_desk=, at_desk=)` (lit slat wall, backlit
  logo, globe pendants, fluted counter, reflective floor); `CONFERENCE_SEAT`, `RECEPTION_CLERK` and `RECEPTION_VISITOR`
  are the tested placements ([ADR 0011](../docs/decisions/0011-polished-cutout-rooms.md)).
  (`srstudio.ink`): the shots `desk_shot`, `closeup`, `printer_shot`, `wide_shot`, `router_shot` (the router on its
  wall shelf, `close=True` fills the frame, `hand_action="reach"|"press"|"leave"` brings in the `ink-hand` prop) and
  `router_wide`, each drawn into a take's group; `router_scene(cv, g, take, **beats)` picks the shot a take names.
  (`srstudio.blob`): `office` (`soft-office`: desk, laptop and slatted chair in a 3/4 view from above, wood outlined
  in `WOOD_LINE`; drawn in output pixels for Pip at `SCALE` and sized to him: a seated pose's hands land on
  `blob.keyboard()` and its soles on `SEATED_FLOOR`, which a test asserts; `SEAT` and `FLOOR` place a sitting or
  standing pose). `home` (`soft-home`): the living room in the same 3/4 view, a fabric `sofa` (`soft-sofa`) facing
  left on a rug, a floor lamp and a side table with the cactus; the sofa shares the chair's axes and seat height, so
  a seated pose at `SOFA_SEAT` has its hip on `blob.sofa_seat()` and its soles on `SOFA_FLOOR` (tested), and
  `on_sofa=` seats a character between the seat and the near arm; `lamp_talk=` lights the floor lamp while it speaks, and
  `LAMP_SHADE` is its shade's point. `meeting_room` (`soft-meeting-room`) and
  `break_room` (`soft-break-room`) are polished rooms on a shared shell (`room_point`, walls, plank or tile floor,
  baseboards, a `-light` glaze group): a walnut table with a swivel chair (`soft-swivel-chair`), a wall screen and a
  clock; mint cabinets, a coffee machine (`soft-coffee-machine`), a fridge (`soft-fridge`), a pendant lamp and a stool
  (`soft-stool`). Both seats hold `SEAT`, and wall decor stays below `CAPTION_FLOOR` (tested;
  [ADR 0008](../docs/decisions/0008-polished-rooms.md)).
  (`srstudio.cel`): `room` (`cel-room`: wall, plank floor fanning from a vanishing point and a wooden desk under the
  room's own measured camera re-expressed inside the world's, `cel.compensate`); `cel.world` places the measured
  camera on the group everything else is drawn in.
- **Props** (`srstudio.props`): desk papers, plant, chairs, laptop, water glass, silent phone, coffee cup, menu board,
  café window, pendant lights, espresso machine with steam expressions, pastry stand, buildings, tree, shrubs, park sign,
  bench, and the gradient sets `office_paints`/`cafe_paints`.
- **Graphics** (`srstudio.graphics`): `episode_slate`, `quiz_card`, `answer_bubble`, `scorecard`, `dashboard`,
  `notification`, `password_card`, `location_slate`, `connected_card`, `captions`; `ink.caption` for the top captions
  and `subtitles.write_srt` for the external file; `cel.lettering` (`cel-lettering`) for a caption traced as boxes and
  glyph paths.
- **Music** (`srstudio.music`): `Groove(bpm)` turns bars and beats into seconds; `render(groove, sections)`
  synthesises a deterministic groove on that grid (rests are cut, not faded), `write_wav` stores it.
- **Camera** (`srstudio.camera`): `anchor`, `push_in`, `zoom_holds`, `reframe` (hard cuts by hold keys on one group),
  `crash_zoom` (a snap onto the subject within `SNAP` seconds, optional snap back; returns the cue for
  `foley.write_whoosh`, a seeded noise sweep that swells into the landing).
- **Craft report** (`srstudio.craft`, [ADR 0023](../docs/decisions/0023-comic-craft-measured.md)): `srstudio craft
  PROJECT... --renders ../generated/renders` lists each episode's punch-ins, crash zooms and pushes (camera or gag)
  and the pauses between its lines, with the rendered level inside each one (quiet or filled); `--json` for the data.
- **Mouth styles** (`srstudio.soundtrack`): `OFFICE_MOUTH`, `CAFE_MOUTH`; `dataclasses.replace(CAFE_MOUTH, idle="smile")`
  keeps a character smiling between lines.

## Extending

Register a part so the catalog and other episodes find it:

After finding a part in `srstudio catalog`, inspect it without opening its source:

```bash
srstudio inspect location office-wide
srstudio inspect character manager --json
srstudio inspect location my-room --plugins my_package.parts
```

Inspection shows the real callable signature, parameter defaults, callback slots, full docstring and a call
template. The template names the arguments you supply (`cv` is usually `ep.cv`, `parent` is `ep.comp` or a
shot group). The office, café, Manager, Toon sloth/goat/hamster and episode slate include runnable examples
using an existing `ep` Episode. Python tools can use `srstudio.describe(kind, name)` or
`registry.get(kind, name).describe()`;
both return the same JSON-compatible details as `--json`. Inspection does not call the builder.

### Agent contracts

`describe(kind, name)["contract"]` uses `schema="srstudio.part-contract/1.0.0"`. Its `arguments` and `returns`
describe JSON representations using JSON Schema 2020-12; records expose named properties, sequences expose item
schemas, and fixed tuples expose `prefixItems` with their exact length. See the standard's
[array](https://json-schema.org/understanding-json-schema/reference/array) and
[object](https://json-schema.org/understanding-json-schema/reference/object) references. The existing signature,
parameter list, call template, examples, and version fields remain available.

| Field | How an agent uses it |
| --- | --- |
| `invocation` | `construct` creates an instance; `call` invokes a function. An Actor then exposes `operations.build`. |
| `arguments` | Check required names and structural types. `x-python-kind` identifies positional-only and variadic binding rules. `additionalProperties` is closed unless the callable accepts `**kwargs`. |
| `returns` | Inspect the result representation or its runtime Python type. |
| `shape_complete` | True only when argument shapes contain no unknown or runtime-only nodes; it does not certify semantic validity or the return type. |
| `validation` | Always `runtime-required`: use the actual typed constructors and builder checks before accepting a generated plan. |
| `capabilities` | `true` is supported, `false` is unsupported, and `null` is unknown. A parameter's presence does not imply support. |
| `vocabularies` | Explicit supported names, such as an Actor's mouths and extras. Unknown option shapes still require runtime validation. |
| `operations` | Independently described helpers/methods; Bento includes `pose_of` with its mood, gesture, and eye-state enums. |
| `constraints` | Additional authored relationships, such as an exit occurring after an entrance; these are explanatory, not an executable constraint language. |

Shape annotations `x-unit`, `x-timebase`, and `x-role` come from explicit metadata. Their absence means unknown,
not dimensionless or project time. `canvas` time follows `Canvas.local_time`; `relative:enter` is an offset from
the builder's entrance. Bento's pose starts use that relative clock, while `duration` is an absolute project
exit. The Actor build operation describes coordinates in drawing-parent units and scale as a ratio.

`ParameterContract.space` and `anchors` publish `x-space` and `x-anchors`; `PartContract.returns` can attach them
to a returned drawing group. Anchors are named finite 2D points, with explicit units and coordinate space.
They describe local geometry before the returned group's transform. They do not imply a mesh, collision
surface, finger contact solver, or supported camera view. These are optional additions to the existing
`srstudio.part-contract/1.0.0` envelope; argument-shape completeness still says nothing about return semantics.

`x-status="runtime"` marks Python objects such as a Canvas or callback. `x-status="unknown"` marks missing or
unresolved annotations and bounded recursive expansion. Neither is permission to accept arbitrary generated
JSON as valid input. Dataclass-shaped JSON still needs construction of the actual Python record; inspection
does not provide a decoder. Inspection never calls builders or dataclass default factories. Annotation
resolution evaluates imported Python annotations, so plugin modules remain trusted executable code.

Plugins declare semantics with frozen `ParameterContract` and `PartContract` records. Metadata is checked against
the signature before registration, and restoring a replaced part also restores its original metadata. Use
`fields` for record fields, `items` for homogeneous sequences, and `prefix_items` for fixed tuples. An
`Annotated[T, ParameterContract(...)]` annotation can carry the same metadata. Missing annotations can be supplied
with `ParameterContract(type=T)` on a callable parameter; default values never imply parameter types.

This complete plugin declares a bound and implements its runtime failure path:

<!-- contract-plugin:start -->
```python
from sr_core.scene import Composition, Group
from srstudio import Canvas, checks, register
from srstudio.canvas import CanvasError
from srstudio.contracts import ParameterContract, PartContract

@register("prop", "agent-marker", contract=PartContract(parameters=(
    ("opacity", ParameterContract(minimum=0, maximum=1, unit="ratio")),
)))
def marker(cv: Canvas, parent: Composition | Group, opacity: float = 1) -> Group:
    if not checks.number(opacity) or not 0 <= opacity <= 1:
        raise CanvasError("opacity must be finite and within 0..1", code="marker.opacity")
    group = cv.group(parent, cv.uid("marker"), opacity=opacity)
    cv.rect(group, 0, 0, 12, 12, "#5BB98C")
    return group
```
<!-- contract-plugin:end -->

Every built-in registered character declares its core capabilities, with shared metadata for verified family
contracts. Other parts and plugins may still have unknown units, clocks, or capabilities. Do not fill those
gaps by guessing from parameter names. Start with `srstudio catalog --json`, inspect the selected part, supply its
runtime bindings, construct its typed records, and handle the builder's structured diagnostics on failure.

Capabilities describe the **registered callable**. `limbs` means typed `LimbTrack` replacement; `head_motion`
means accepting an authored `HeadPlan`; `expressions` means named facial controls. A held tilt or built-in idle
movement does not imply `head_motion`. Rafa's registered `body(Model)` builds static geometry below the head,
so its facial capabilities are false; its separate `operations.face` describes the validated `rafa.Face` record.
Rafa's animated plate composition is supplied by `rafa_host`. Toon head-rig performance is supplied separately
by `toon_head.figure`; the ordinary registered pose drawers do not accept a `HeadPlan`.

Clocks are explicit:

| `x-timebase` | Meaning |
| --- | --- |
| `project` | Absolute project seconds. In Toon and Collage, `duration` is the exit time, not an interval length. |
| `relative:enter` | Pose start relative to the character's `enter`; the drawer adds the entrance once. |
| `canvas` | The canvas animation clock. With `Canvas(local_time=True)` under a shot sequence, zero is the shot start. |
| `relative:take` | Time since the supplied take starts. Ink builders expect a corresponding local canvas; they do not add `Take.start`. |

`x-role="duration"` identifies a length such as Soft's arrival easing interval. Units distinguish parent placement,
rig coordinates, degrees, ratios and sampling rates. Family constraints describe reference geometry and placement
anchors. Nested records, nullable tracks and pose unions retain their field and element metadata.

This complete example discovers a supported expression, constructs its public record, and draws it from project
second 3 to 4. The pose begins at zero relative to the entrance:

<!-- character-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, toon

entry = registry.get("character", "toon-dog")
contract = entry.describe()["contract"]
names = contract["vocabularies"]
pose = toon.Pose(0, names["eyes"][0], names["mouths"][0], names["arms"][0])
scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=4)
cv = Canvas(scene, font_asset=None)
groups = entry.builder(cv, cv.comp, [pose], enter=3, duration=4)
assert groups[0].attributes()["start"] == "3"
```
<!-- character-discovery:end -->

Inspect `pip` for Soft's existing `pose_tweening` and `foot_pinning` controls and its cue helper. Its expression
changes on arrival; its `pin` cannot be combined with cue translation or lift. For Stick, `default_poses` lists
the built-in seated sheet, while callers can supply a custom `poses` mapping; it is intentionally not a closed
enum. The traced cat's vocabulary excludes brush-only expressions. Collage declares its ignored compatibility
arguments and its `still` behavior. These distinctions let agents reject unsupported plans before drawing.

Discovery remains a description, not a JSON executor or a new validation layer. Opaque runtime bindings,
legacy extras and some nested plugin data still require the actual Python API and its checks. Units and
capabilities do not establish emotional readability, biomechanics, or rendered quality.

### Non-character discovery and drawing anchors

The core Cutout families publish 33 prop, 8 location and 11 graphic contracts; `reaching-hand` adds a held-prop
callback contract. Coverage remains partial across the full catalog. Inspect it separately from ordinary listings:

```bash
srstudio catalog --contract-coverage --json
srstudio catalog --style cutout --kind prop --contract-coverage
srstudio inspect prop coffee-cup --json
```

`srstudio.contract_coverage(style=None, kind=None)` returns the same versioned coverage report. Per-kind counts
separate explicit declarations, complete argument shapes, units, clocks and anchors; `undeclared_parts` names
the gaps. A count of declarations does not certify complete semantics. Discovery never invokes a builder.
The regular `catalog` list retains its existing shape. Coverage and usage-ranking reports are separate modes.
Directly replacing `Entry.builder` invalidates its previous declaration even if the new signature matches.
Inspection marks that contract `declaration_status="builder-changed"`; coverage lists it under
`stale_contract_parts` and `undeclared_parts`. Re-register the replacement with its own checked metadata, or
restore the original version with `parts.restore`. Drawing approval and semantic declarations remain separate.

Location slots are runtime callbacks receiving an existing group. The slot description identifies its drawing
depth, and the callback's return value is ignored. This complete recipe validates a malformed callback before
drawing, then places an actual actor behind the office desk. `shots` gates visibility on the canvas clock;
it does not call the callback again for each frame or shift the actor's performance clock.

<!-- location-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, cast, describe, get
from srstudio.locations import LocationError

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="30", duration=3)
cv = Canvas(scene, font_asset=None)
info = describe("location", "office-desk")["contract"]
assert info["arguments"]["properties"]["behind_desk"]["x-role"] == "drawing-slot"
location = get("location", "office-desk")
before = scene.to_bytes()
try:
    location(cv, cv.comp, behind_desk=False)
except LocationError as error:
    repair = error.to_dict()
    assert scene.to_bytes() == before

seated = []
def seat(parent):
    seated.append(cast.Manager(cv).build(parent, 560, 724, 1.45))

room = location(cv, cv.comp, shots=[(0, 3)], behind_desk=seat)
assert scene.check(schema=True) == []
```
<!-- location-discovery:end -->

For a held cup, align its published `body-center` anchor with the hand's `grip`. The existing hand builder draws
the carried object between palm and fingers. Animate the shared parent so the contact survives translation,
rotation and scaling without independently sampled prop keys. A floating cup uses `shadow=False`; its contact
shadow belongs on a support surface. `base` is a separate local anchor for placing the cup on a table.

<!-- held-prop-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, describe, get

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="30", duration=3, background="#ECE2D2")
cv = Canvas(scene, font_asset=None)
cup_info = describe("prop", "coffee-cup")["contract"]
hand_info = describe("prop", "reaching-hand")["contract"]
assert cup_info["returns"]["x-space"] == "returned-group"
assert hand_info["returns"]["x-anchors"]["grip"] == [0, 0]
assert cup_info["capabilities"]["spatial_attachment"] is False
cups = []
def carry(parent):
    cup = get("prop", "coffee-cup")(cv, parent, 0, 0, scale=2, shadow=False)
    cup.anchorX, cup.anchorY = cup_info["returns"]["x-anchors"]["body-center"]
    cups.append(cup)

hand = get("prop", "reaching-hand")(
    cv, cv.comp, 540, 1050, scale=1.3, grip=52, holds=carry,
)
cv.keys(hand, "y", [(0, 1050), (1, 900), (2, 900), (3, 1050)], kind="sine-in-out")
cv.keys(hand, "rotation", [(0, 0), (1, -8), (2, -8), (3, 0)], kind="sine-in-out")
assert scene.check(schema=True) == []
```
<!-- held-prop-discovery:end -->

This is an authored flat grip and a sleeve entering from outside the frame, with no articulated shoulder,
physical collision, or automatic view conversion. Use the [spatial contact compositor](catalog/limbs.md#prop-contact-and-compositing)
when the prop needs a mesh and depth ordering across articulated limbs. Some builders return only part of their
drawing: `cafe-window` returns its clipped view, and `tree` its animated canopy. Their contracts identify that
limitation. `captions` returns layers placed directly in the composition; its start/end values use the composition
clock, independently of `Canvas.local_time`. Other core graphic animation keys use the canvas clock.

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

### Extending drawing calls

`Canvas.keys()` builds and validates the complete animation before attaching it to the scene. A failed key
conversion or SDK validation leaves existing nodes and scene bytes unchanged, so a corrected call can be retried
on the same canvas. Frozen drawings also validate the supplied keys before retaining only the initial value.
This atomicity covers one `keys()` call; it does not roll back separate drawing calls made earlier.

Plugin decorators can add `slots=("at_table",)` for unannotated callback parameters and
`examples=("...Python code using ep...",)` for their own usage examples. The library's `Slot` annotations
are discovered automatically. A declared slot must name an explicit location builder parameter.

```python
from srstudio import register

@register("prop", "tip_jar", summary="A glass tip jar")
def tip_jar(cv, parent, x, y, scale=1.0):
    g = cv.group(parent, cv.uid("tip-jar"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -40, -90, 80, 100, radius=10, fill="#DDEAF2", stroke=cv.ink, sw=3)
    return g
```

Kinds are `character`, `location`, `prop`, `graphic`. A new location is complete only when it places both marks
of the [Signature](#signature) convention. Registering the same kind and name twice raises `RegistryError`;
use `@register("prop", "tip_jar", replace=True)` when intentionally replacing a builder.
Parts from another package are listed with
`srstudio catalog --plugins my_package.parts`. A new episode is a script like the ones in [episodes/](../episodes):
it takes the project folder as its first argument and is run with `python3 episode.py PROJECT`,
`srstudio build episode.py PROJECT` or, once it has a release, `srstudio build <slug> PROJECT`. Its recorder
(`<script>_audio.py`, front end `srstudio.recording.main`) runs with `srstudio record <slug> PROJECT`
([ADR 0032](../docs/decisions/0032-releases-recorders-and-discovery.md)). `srstudio.sample.write_sample_project` writes a synthetic project (dialogue,
tone-burst soundtrack, font) to try a build without a TTS pass.

srstudio-defined errors derive from `srstudio.SrstudioError` and retain their built-in base (`ValueError` for bad
data, `RuntimeError` for a provider failure). The underlying SDK can also raise `sr_core.scene.SchemaValueError`
for invalid scene values, and filesystem operations can raise `OSError`. Catch those separately when needed.
A missing API key
is `MissingKeyError`, a provider HTTP failure `ProviderHTTPError`, and a builder given a flag it does not know raises
`FlagError` before building anything (`srstudio.errors.flags`;
[ADR 0034](../docs/decisions/0034-one-error-base.md)).

Built-in `shared_counter()` and `flat_counter()` ID namers rewind when a transactional authoring call fails, so a retry uses the same IDs as a fresh call. A custom `namer` owns its own state and is not automatically rewound.

Malformed timeline records and JSON raise `TimelineError` with field or file context. Catalog lookups with an
unknown kind raise `RegistryError`. The installed package includes `py.typed` so type checkers can use its
annotations.

`register` preserves decorated functions' type signatures. The core episode authoring helpers also expose
typed parameters and SDK return nodes. Office and café actors reject unknown performance extras and invalid
gesture values with `CastError` before drawing; subclasses can extend `extra_options` and override
`validate_performance` for custom behavior. `srstudio build` prints expected library errors as concise
diagnostics with a nonzero exit status.

### Finishing a style: `srstudio.look`

A style's finish is a handful of calls with its own numbers and id prefix, never a copy of another style's helpers
([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)):

```python
from srstudio import look

lines = look.wrap(font, text, 50, 640, max_lines=3)    # measured; look.FitError when it does not fit
far = look.depth(cv, g, "mystyle-depth", 3.0)          # the far plane, out of focus
look.pool(cv, g, "mystyle-pool", "#ffc870", 40, 1160, 1000, 260, opacity=0.3)
look.fade(cv, g, "mystyle-shade", "#3a1f5cb3", 1900, 1500, width=1080)
look.grade(cv, shot, "mystyle", {"bloom": dict(threshold=0.9, radius=28, intensity=0.5)})
```

Every file hash in the library is `srstudio.digest.sha256`.

### Staging and series: `srstudio.staging`, `srstudio.series`

A sequence style stages a recorded take timeline with `staging` (the checks, the camera `rig` of a `Move` and a
shake, `blackout`, `crossfades` into a closing card, and `close` for the transitions, captions and ducked mix),
and declares its episodes once as a `series.Series` (voices, settings, music bed, font, output, reel builder,
caption look). Each episode is a `Reel` subclass's instance; `series.record` records it and `series.build`
builds it ([ADR 0031](../docs/decisions/0031-shared-look-and-caption-primitives.md)). `episodes/_saga.py` is the
worked example.

`staging.freeze(shot)` preserves the shot's starting pose and leaves the scene unchanged on failure. Properties with
additive animation retain static one-key animations so the renderer can compose them with their base values.
Timed descendants retain their opening visibility throughout the frozen shot; the shot's own schedule is
preserved. Animation sampling respects `timeBase`: composition time zero, local time minus the node's start,
or that local time divided by the node's duration for normalized keys. An omitted normalized end uses project
duration; if neither is available, freezing is refused. A curve spanning the resulting freeze point without a
key there is refused unless that segment uses hold interpolation. Provide an explicit key at that point with
the intended opening value before freezing. Expressions and text animators are also refused; these failures
leave the scene unchanged.

### Google Fonts

A style's caption face can name a Google Font (`Font(google=GoogleFont("Poppins", 700))`). Fetch and pin it once:

```bash
srstudio fonts add Poppins --weight 700 --into PROJECT/assets/fonts
```

`srstudio.fonts.install` asks the Google Fonts CSS API for the TrueType file, accepts only a single `@font-face`
served from `fonts.gstatic.com`, reads the file's own `name` and `OS/2` tables to check that family, weight and
italic match the request, and fetches the family's licence (OFL, Apache or UFL) from the google/fonts repository.
Only then does it write `<family>-<weight>.ttf`, the licence and `fonts.lock.json` (URL, SHA-256, licence). Later
runs verify the pinned SHA-256 and do not touch the network; a file that changed is refused. An episode whose
style font is missing stops with the `srstudio fonts add` command that fetches it.

### Cast cards: `srstudio.cast_card`

`srstudio cards FOLDER` writes one 1080×1920 PNG per character in `cast_card.CAST`: the approved drawing rendered
through the engine, a name, one line and the wordmark, in Fredoka 600 and DM Sans 700. `--only rex` narrows it. A
`Card` is typed data (name, line, drawing, `Pose`, `Frame`, backdrop). Before anything is written the card is
refused if the drawing is unknown or unapproved, the line reads as engagement bait, the letters leave the story safe
zone (no text in the top 250 px or the bottom 340 px, measured from the rendered letters), the figure is too small
to read, or the panel cuts a shape down to its tip: an island of ink resting on the panel's edge and under 24 px tall.
That last refusal is fixed by moving the `Frame`, never by painting over the tip or changing the drawing. Folders are
mode 700, files mode 600.

Who gets a card: a character is cast when the same name sits on the same drawing in five or more reels, in an everyday
world. Count from the releases and `srstudio usage`. A one-reel character is not cast, and sealed worlds such as Saga
and Gloss are not everyday life. Ava is the one exception, at four reels, because the Okayville request named her.

## New episodes with generated audio: *Five Years* (06)

[episodes/five_years.py](../episodes/five_years.py) is the first episode made on the library rather than ported to it.

```bash
python3 episodes/five_years_audio.py PROJECT --key-stdin < key   # resolve, speech check, trims, dialogue.json
SRSTUDIO_ENGINE=scene-render srstudio build episodes/five_years.py PROJECT   # scene + overlay check
scene-render encode PROJECT/five-years.scene.xml --strict         # renders/five-years.mp4
```

**Generated audio, resolved by the engine.** Every line and effect is a `<generated>` asset
(`srstudio.generated.Generated`) for the `srstudio-elevenlabs` provider ([src/srstudio/provider.py](../src/srstudio/provider.py),
console script `scene-render-provider-srstudio-elevenlabs`, or `SR_PROVIDER_SRSTUDIO_ELEVENLABS="python -m srstudio.provider"`).
`scene-render resolve` runs the provider for each stale item and pins the file's SHA-256 in the document; the
episode plays each pinned clip on its own `<audioTrack>` (`Episode.generated_audio()`, placements from the
`clips` of `dialogue.json`) and refuses a clip whose file no longer matches its pin. The provider parses the
resolve request strictly, needs `SRSTUDIO_ALLOW_CLOUD=1`, and writes nothing until ElevenLabs speech-to-text hears
the scripted line; a mismatch fails the item and asks for another `@seed`.

The interview episodes (06 and 09) share one audio pipeline, `srstudio.interview`
([src/srstudio/interview.py](../src/srstudio/interview.py)). An `Interview` lists its voices (`srstudio.song.Singer`),
its `Spoken` lines and its `Sound` effects, and is checked when made. The episode supplies a `schedule` (the start of
every line and effect from the trimmed clip lengths), refused when two lines overlap, an effect is missing or
unknown, or anything plays past the end card, and an `extra` that adds its beats and camera cuts from the `Timing`.

`srstudio.voice` treats the provider's output as untrusted. It parses dialogue, sound effects and speech-to-text
into typed values that reject unknown fields. It checks that the aligned characters spell the requested line,
that timings are finite and ordered, and that each clip is audible and as long as its alignment or its requested
length. Any violation raises `VoiceOutputError` and nothing is cached. Every uncached call is one request, never
retried; cached clips and transcripts are re-verified when read. `tests/test_voice.py`, `tests/test_provider.py`
and `tests/test_generated.py` feed malformed, truncated and adversarial responses and requests through each path.

**Safe area.** `EpisodeSpec(safe_area=srstudio.VERTICAL)` declares a `<safeArea>` with `enforce="error"` and makes it
the project's: the engine then fails validation and rendering when text or a caption leaves x 80–920, y 220–1420
(the engine's documented production box for 1080 × 1920; its platform presets are approximations). The engine does
not measure vector graphics, so `srstudio.layout.check_overlays(scene, ["squeak-loud", ...], engine=...)`
evaluates every frame, maps each drawn shape under the named groups through its world transform (exact bounds for
lines, quadratic and cubic curves and arcs, plus the stroke's reach) and reports every crossing; episode 06 runs it
with `strict=True` after `finish()`, as `ep.check_overlays(out, roots)` does with the engine that
`layout.find_engine()` finds (`--engine`, then `$SRSTUDIO_ENGINE`, then the `PATH`). Episodes 01–05 declare no safe
area and are unchanged. `ep.audio(extra=[music], duck=-8)` ducks every music track under the spoken lines.

**Symbols.** `Canvas.symbol(id, draw)` defines a symbol once and `Canvas.instance(parent, id, symbol)` places it
(ids inside are scoped `instance/inner`); `office_wide`/`office_desk(instanced=True)` share the room and the desk
that way. The engine draws an instance into an offscreen at its frame size and scales that texture, so an instance
under a camera push-in renders soft; episode 06 pushes in on its wide angle and therefore keeps the inline drawing.

Parts added for it: the `office-desk` location (the wide office without the foreground candidate; `chair=False`
leaves the chair to the slot), the `chair-back` prop, the `squeak-mark` graphic, and `camera.spin` with
`camera.show_facing` (a turn about the vertical axis, one `|cos|` key per frame, the far side swapped in at each
edge-on moment).

## Cutout episode with generated audio: *Tip Screen* (12)

[episodes/tip_screen.py](../episodes/tip_screen.py) brings Ava and Milo from episode 05 back to the café. Milo asks for
a black coffee, Ava swivels the tip tablet, and Milo sets down a tablet of his own: "how would you like to tip me for
ordering?" They tap "thirty" at each other until closing, and the scorecard nets it out at nothing.

```bash
python3 episodes/tip_screen_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/tip_screen.py PROJECT                     # PROJECT/tip-screen.scene.xml
```

The dialogue (Liam and Jessica, ElevenLabs premade voices), the swivel, the second tablet and five taps are an
`Interview`; `schedule` lands each tap 0.05 s after the number it answers, and `TAPS` names whose tablet it lights
and which option. Parts added for it: the `tip-tablet` prop (`props.tip_tablet(cv, parent, x, y, heading=,
options=, picks=((time, index), ...), scale=)`: a stand, a heading, one button per option, the tiny "no tip", and
a lit overlay per pick that holds until the next one), and `Barista(..., name=None)`, which leaves the name tag
blank so a close-up carries no lettering out of frame (the default stays "AVA").

The episode declares no engine safe area: its close-ups reframe the menu board and the tablets out of frame on
purpose, which the SA01 text check refuses. Captions and cards are placed inside `layout.VERTICAL` by hand, the
contact sheet is checked by eye, and the cover variant hides the burned captions (`ep.hide_on_cover`).

## Cutout crossover in the park: *Culture Fit* (14)

[episodes/culture_fit.py](../episodes/culture_fit.py) seats Milo (episodes 05 and 09) next to the boss from the
interview series on a park bench. Milo has sent two hundred applications; the boss interviews a pigeon on his lunch
break, hires it, and explains why: "He works for crumbs." Milo makes a counter-offer.

```bash
python3 episodes/culture_fit_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/culture_fit.py PROJECT                     # PROJECT/culture-fit.scene.xml
```

The dialogue (Liam and Eric, ElevenLabs premade voices) and six effects (a flutter, three coos, two notification
pings) are an `Interview`; `schedule` holds 1.3 s before the punchline and 1.2 s before Milo's answer. Parts added
for it: the `legs="seated"` performance extra on the office actors (trousers and shoes below the torso, drawn behind
it; without it nothing changes), `locations.PARK_SEAT_Y` with `locations.park_seat_y(bottom, scale)`, which seats
any actor on the bench, and the `crumbs` prop (`props.crumbs(cv, parent, x, y, ground, toss=, count=, seed=)`: a
handful that leaves the hand at `toss` and lands scattered on `ground`). The push notifications are the
`notification` graphic at 2.25×. Like *Tip Screen*, the episode declares no engine safe area (the park sign's
lettering sits right of x 920); captions and cards are placed inside `layout.VERTICAL` by hand.

## Cutout episode in the conference room: *Market Rate* (16)

[episodes/market_rate.py](../episodes/market_rate.py) brings back the candidate from the interview series, a year into
the job. Alone in the conference room, he asks the boss on the speakerphone for a raise and gets a title instead
("Does Senior pay more?" "It's longer."). Then his own job turns up online, paying more, for external talent only.

```bash
python3 episodes/market_rate_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/market_rate.py PROJECT                     # PROJECT/market-rate.scene.xml
```

The dialogue (Will and Eric, ElevenLabs premade voices, as in the series) and four effects (a call chime, two pings
and hold music) are an `Interview`; `schedule` holds 1.25 s before "It's longer." and puts the hold music before the
last line. It is the first episode in `locations.conference_room`. The speakerphone's ring lights while the boss
talks and while his hold music plays (`conference_room(speaker_talk=)`, new and off by default). The job posting is
the `password-card` graphic, the endorsement the `notification` graphic at 2.25×. The episode declares
`layout.VERTICAL`, so the engine holds every caption and card inside the safe area.

## Cutout episode in the elevator: *Elevator Pitch* (18)

[episodes/elevator_pitch.py](../episodes/elevator_pitch.py) puts the employee from *Market Rate* in the elevator with the
boss: "Working from home? Elevator pitch. You've got till my floor." At floor 4 the doors open on Kevin, the pigeon
from *Culture Fit*, who is fully remote ("He negotiated. You took a title."). At floor 9: "Kevin, your call." Coo.

```bash
python3 episodes/elevator_pitch_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/elevator_pitch.py PROJECT                     # PROJECT/elevator-pitch.scene.xml
```

The dialogue (Will and Eric, as in the series) and four effects (two arrival dings, two coos) are an `Interview`;
`schedule` opens the doors between the pitch and "Morning, Kevin." and holds 1.3 s before the coo that decides.
Parts added for it:

- `locations.elevator` (`elevator`): the cab seen from inside with the doors on the back wall. `riders` stand in front
  of them facing the camera and `on_floor` draws in front of the riders. `floors=((second, floor), ...)` drives a
  seven-segment display (`SEGMENTS`, no font needed), `doors=((open, shut), ...)` slides each door `DOOR_W` behind
  the wall over `DOOR_SLIDE` seconds onto a hallway, and `lit=` lights a button. Out-of-order floors or overlapping
  door spans raise `ValueError`.
- `legs="standing"` on the office actors (`OfficeActor.STANDING_LEGS`): trousers and shoes straight down, drawn
  behind the torso; `locations.elevator_stand_y(bottom, scale)` stands them on the cab floor. Without the extra
  nothing changes.

The pigeon is `cast.pigeon` in a walking group that comes forward through the doorway. The episode declares
`layout.VERTICAL`.

## Cutout crossover finale: *Going Down* (20)

[episodes/going_down.py](../episodes/going_down.py) closes the office series. Floor 9, going down. "Am I being fired?"
"No. Your role is being sunset." "So I'm fired." "You're going fully remote. From your couch. Forever." At floor 4
Kevin, the pigeon from *Culture Fit*, walks in with a pink slip in his beak: "He flew in for this. He's Head of People
now." The slip lands at the boss's feet, lettered ERIC. "Kevin... is my role being sunset?" A 1.3 s hold, then a
coo. The lobby, then the bench from *Culture Fit*: the two of them tossing crumbs to the pigeons. "What are we
doing?" "Networking."

```bash
python3 episodes/going_down_audio.py PROJECT --key-stdin < key   # srstudio.interview: resolve, speech check, timing
srstudio build episodes/going_down.py PROJECT                     # PROJECT/going-down.scene.xml, 29.8 s
```

The dialogue (Will and Eric, as in the series) and seven effects (two dings, three coos, the slip's slap, a flutter)
are an `Interview`; `extra` returns `park_start`, where the elevator's shots end and the park's begin, and each room
is reframed with only its own camera angles. Parts added or extended for it:

- `props.pink_slip` (`pink-slip`): a sealed pink envelope lettered `name=` (up to `SLIP_CHARS`; `None` shows its
  blank back), shown only in `show=(start, end)` (held in a hand or a beak) or falling `fall=(at, height)` onto its
  mark in `SLIP_FALL` seconds, tipping as it lands.
- `locations.elevator(going="down")` points the display's arrow down; the default stays `"up"`, byte for byte.

The episode declares no engine safe area, as *Culture Fit* does, because the park sign's lettering sits right of
x 920; captions and cards are placed inside x 80–920 by hand.

## Cutout episode at the café counter: *Cup Fee* (22)

[episodes/cup_fee.py](../episodes/cup_fee.py) brings Ava and Milo back to the café. "One black coffee. Three bucks."
Then a fee for the cup, the lid fee, a service fee ("for serving you") and, when Milo offers cash, a cash fee, each
a beep and a higher total on the card reader. "How much is the actual coffee?" "Oh, the coffee's free." "Then what
are the three bucks for?" "The coffee fee." The tip tablet from *Tip Screen* swivels round to him.

```bash
srstudio record cup-fee PROJECT   # srstudio.interview: resolve, speech check, timing
srstudio build cup-fee PROJECT    # PROJECT/cup-fee.scene.xml
```

The dialogue (Jessica and Liam, as in *Tip Screen*), four beeps and the swivel are an `Interview`; `schedule` lands
each beep 0.05 s after the line naming its fee and holds 1.3 s before "Oh, the coffee's free." Its first second is
still (arm A of the `sp-hook_motion` test): the two-shot keeps the espresso machine's steam out of frame and nothing
moves before the first line. Parts added or extended for it:

- `props.card_reader` (`card-reader`): a counter-top card terminal whose screen shows `readings=((time, amount,
  label), ...)`, a big amount (up to `READER_AMOUNT` characters) over a small label (up to `READER_LABEL`), each held
  until the next. The first reading is at 0 and still; each later one pops in about the screen's middle.
- `locations.cafe(menu=(coffee, pastry, footer))` letters the menu board's three lines under its title (up to
  `MENU_CHARS` each); without it the board is the shipped one, byte for byte.
- `locations.finish(cv, parent)`: an opt-in Cutout grade (`locations.FINISH`: a warm vignette and a soft bloom, no
  grain and no blur) on a group the episode draws its sets into, so camera moves stay inside it. A set drawn without
  it is unchanged.

Like *Tip Screen*, the episode declares no engine safe area (its close-ups reframe the menu board out of frame);
captions are placed inside x 80–920 by hand.

## Cutout episode on the park bench: *Storage Full* (23)

[episodes/storage_full.py](../episodes/storage_full.py) puts Milo on the park bench from *Culture Fit*. A pigeon walks
up the path and does a backflip. "No way. Do that again!" The phone: "Storage full." It offers fourteen photos of the
same sunset ("Still full."), then the wedding video. Milo and the pigeon look at each other. "...Yes." "Recording."
The pigeon flies off, and a message from his wife asks for the wedding video.

```bash
srstudio record storage-full PROJECT
srstudio build storage-full PROJECT    # PROJECT/storage-full.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test): the pigeon is walking in and the camera pushes in
from the first key. It reuses `cast.pigeon` (nested in walk, flip and turn groups, the flip turning about the
mirrored rig's body centre), `graphics.notification` holders at 2.25 times for the phone, and `locations.finish` over
the park.



## Cutout episode across the interview desk: *Name a Number* (24)

[episodes/name_a_number.py](../episodes/name_a_number.py) brings the interviewer and the applicant from *Five Years*
back for the salary talk, where whoever names a number first loses. "So. What number did you have in mind?" "What's
the range?" "What would make you happy?" "What would make you happy?" "I asked first." "The ad said competitive."
"Extremely competitive." "Competitive with what?" "Other ads." They both write it down: the offer says LESS THAN
YOURS, the ask says MORE THAN YOURS. "Great. We're aligned." "Are we?" "Competitively."

```bash
srstudio record name-a-number PROJECT
srstudio build name-a-number PROJECT    # PROJECT/name-a-number.scene.xml
```

Its first second is still (arm A of the `sp-hook_motion` test): the job ad lies on the desk and the interviewer's
question is heard over it, its caption from 1.15 s. The desk inserts take one light from the top left, each sheet's
shadow falling down and to the right, and every angle is drawn into `locations.finish`. Extended for it:

- `locations.office_wide(depth=)` and `locations.office_reverse(depth=)` blur the room behind the desk (wall, art,
  plant) or the wall behind the chair by that many px in a group of its own; the desk, the cast and the signature
  marks stay sharp. `locations.elevator(depth=)` does the same for the hallway through the doorway, its cactus kept
  sharp. Without `depth` each set is the shipped one, byte for byte; an instanced office refuses it.

## Interview episodes with a Google caption face

An `Interview` takes an opt-in `font=GoogleFont(...)` (for example `interview.NOTO_SANS_BOLD`, Noto Sans 700, close
to DejaVu Sans Bold's width). The record step then installs that face with `srstudio.fonts.install` into
`PROJECT/assets/fonts` (pinned in `fonts.lock.json`, its licence beside it) before any clip is requested, and copies
no DejaVu file; a face that will not install stops the record with an `InterviewError` instead of falling back to
DejaVu. The picture script gives its `EpisodeSpec` the matching fields with `**interview.spec_font(face, root)`,
which reads the pin and never downloads. Without `font=`, the caption face is DejaVu Sans Bold as before, and every
published interview project rebuilds byte for byte.

## Cutout episode in the elevator: *Neighbor Names* (25)

[episodes/neighbor_names.py](../episodes/neighbor_names.py) puts the applicant from *Five Years* in the elevator with
Rosa, his neighbor of seven years, whose name he never learned. "Morning!" "Morning... you!" "Seven years in this
building, huh?" "Seven years!" "Can I ask you something I should know by now?" "Anything, dear." "Where did you get
that cardigan?" "I made it." Her name is stitched on it; his parcel's label says DEV 7C. The doors open on a third
neighbor: "Morning, Linda! Morning, Steve!" The doors shut. "Steve." "Linda."

```bash
srstudio record neighbor-names PROJECT
srstudio build neighbor-names PROJECT    # PROJECT/neighbor-names.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test): the greeting is under way, his hand up and her
lean toward him, with no camera move. The voices are Lily (Rosa), Will and Eric; the captions are Noto Sans 700 (`interview.NOTO_SANS_BOLD`). Parts added or extended for it:

- `cast.Rosa` (`rosa`): an office-family actor with a grey bob, round glasses and a terracotta cardigan whose pocket
  has her name stitched over it (`stitch=`, 1 to `Rosa.STITCH` characters, default ROSA; `None` draws no text).
- `props.parcel` (`parcel`): a taped cardboard box with an address label, lettered by `label=` (1 to `PARCEL_LABEL`
  characters) or left blank.
- `locations.elevator(hallway=)`: a slot drawn in the hallway behind the doors and in focus, for someone waiting
  there while they are open; `depth=` blurs the hallway itself. Without either, the elevator is the shipped one.

The episode declares no engine safe area, as *Cup Fee* does: each close-up reframes the other rider's lettering out of
frame, which the SA01 text check refuses; captions are placed inside x 80–920 by hand.

## Cutout episode at the home printer: *Out of Cyan* (26)

[episodes/out_of_cyan.py](../episodes/out_of_cyan.py) sits Rosa at her desk with one black page to print and a printer
that reads LOW ON CYAN. "It's black and white." It answers in pages: a ransom note in cut-out letters, WE HAVE YOUR
DOCUMENT, then BRING CYAN. COME ALONE. She pays $64 at a shop till, and it wants OFFICIAL CYAN. She pays $89, and it
wants the magenta too, with an instant photo of her page tied to a chair. "Don't hurt it." She pays $98. The display
says THANK YOU, and her black page comes out blue.

```bash
srstudio record out-of-cyan PROJECT
srstudio build out-of-cyan PROJECT    # PROJECT/out-of-cyan.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). The voice is Lily (Rosa); the printer never
speaks, and the long gaps between her lines are its whirs and pages, not silence. The captions are Noto Sans 700.

Rosa's card, for this and every later appearance:

- **wants**: to be treated with basic courtesy, by neighbours and by machines;
- **flaw**: she is too polite to refuse anything that asks nicely or threatens nicely;
- **habit**: she answers a demand with "dear" and then meets it.

Parts added for it, in `srstudio.cutout_home`:

- `desk_printer` (`desk-printer`): a home printer from the front; `lcd=` is timed readings of 1 to `LCD_CHARS`
  characters, `whirs=` are spans it rattles, `sheets=` slide out into its tray.
- `ransom_note` (`ransom-note`): a sheet whose `lines=` (1 to `NOTE_LINE` characters) are cut from magazines, each
  letter on a seeded scrap.
- `hostage_photo` (`hostage-photo`): an instant photo of a sheet of paper tied to a chair under one bulb.
- `paper_bag` (`paper-bag`): a very small carrier bag.
- `home_study` (`home-study`): a sage study with a window and an out-of-focus bookshelf; `behind_desk=` draws whoever
  sits there and `on_desk=` what stands in front of them. `desk_top` is the same desk from above, for inserts.
- `shop_till` (`shop-till`): out-of-focus shelves over a pale counter; `on_counter=` draws on it.

These six parts are recorded `proposed`: nothing draws them by default and no release can pin them until the operator
has approved them. `srstudio parts` shows such a part with `-` as its default.

## Cutout episode in the break room: *I'm Quitting* (27)

[episodes/im_quitting.py](../episodes/im_quitting.py) stands the applicant at the coffee machine, already mid-rant. "That's
it. I'm quitting. Today." His friend, eyes on his own mug: "Mm." The same shot, a new mug, a bigger plant, and the wall
board reads 2,190 days since "today". "This time I mean it." "Mm." Twelve years in, a planner lands on the counter. "You
said Friday." "Which Friday?" Every Friday in it is circled. "Twelve years of them." A banner, a gold watch. "Forty
years. Thank you." He taps the mic. "That's it. I'm quitting." The same mug: "Mm."

```bash
srstudio record im-quitting PROJECT
srstudio build im-quitting PROJECT    # PROJECT/im-quitting.scene.xml
```

Its first frame already moves (arm B of the `sp-hook_motion` test). Time passes on the props and not on the people: the
mug, the plant and the board. The voices are Will and Eric; the captions are Noto Sans 700. Parts added for it, in
`srstudio.cutout_office`, all recorded `proposed` until the operator has approved them:

- `drip_machine` (`drip-machine`): an office coffee machine; `pours=` are spans its stream runs.
- `office_mug` (`office-mug`): a mug in any colour, lettered by `label=` (1 to `MUG_LABEL` characters) or plain.
- `days_board` (`days-board`): a workplace-safety style wall board; `heading=` and timed `counts=` (1 to `BOARD_CHARS`
  characters).
- `wall_planner` (`wall-planner`): a planner page with every Friday circled around `note=`; `months=` flips its pages.
- `gold_watch` (`gold-watch`), `stage_mic` (`stage-mic`): a presentation watch with a `gleam=` time, a mic on a stand.
- `party_crowd` (`party-crowd`): the backs of an audience's heads out of focus; hands clap in `claps=`.
- `break_room` (`break-room`): a mustard wall, cupboards and a fridge out of focus, and a counter; `on_wall=`,
  `behind_counter=` and `on_counter=` draw at those depths.
- `office_party` (`office-party`): a dark teal function room with streamers; `banner=` hangs in focus, `stage=` draws
  under it and `front=` nearest the lens.

## Cutout episode in the hiring office: *Entry Level* (28)

[episodes/entry_level.py](../episodes/entry_level.py) opens on an interviewer and the ad on his desk: ENTRY LEVEL, 10 YEARS'
EXPERIENCE. "It's entry level, so just ten years." "I'm 22." "Have you tried starting earlier?" The desk bell brings a
crayon CV with small shoes swinging under it: "Been in the role since nursery." "Promising." Milo: "This software came
out in 2024." "We need twenty years in it." A crib, a CV over its rail: "I've been networking since the womb."
"Overqualified. We'd lose you." "Who actually got it?" The blind snaps up on Rosa at a desk in a paper hat that says
TRAINEE. "She's still on probation."

```bash
srstudio record entry-level PROJECT
srstudio build entry-level PROJECT    # PROJECT/entry-level.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). The toddler and the baby are heard, in grown men's
voices (Brian and George), and never drawn. The other voices are Eric, Will and Liam; the captions are Noto Sans 700.
Parts added for it, in `srstudio.cutout_hiring`, all recorded `proposed` until the operator has approved them:

- `job_ad` (`job-ad`): a printed advert standing on a desk; `heading=` and two `lines=` of 1 to `AD_LINE` characters.
- `crayon_cv` (`crayon-cv`): a CV in crayon with a clip-on tie, two small hands on it and shoes under it; `swings=`.
- `crib` (`crib`): a slatted crib and mobile with a CV over the rail; `rattles=` shakes the rattle.
- `paper_hat` (`paper-hat`): a folded paper hat lettered by `label=` (1 to `HAT_LABEL` characters).
- `roller_blind` (`roller-blind`): a blind that snaps up at `snap=`, its cord dipping first.
- `hiring_office` (`hiring-office`): a slate wall and a poster out of focus, a glass wall onto `next_room=` behind the
  blind, a desk; `behind_desk=` and `on_desk=` draw at those depths.

## Cutout episode at the barber's: *Just a Trim* (29)

[episodes/just_a_trim.py](../episodes/just_a_trim.py) opens on Rosa in a barber's mirror, a lawnmower parked behind her and
a hedge trimmer on the shelf. "Just a trim, please." "Sure." A cape covers the mirror; a hedge trimmer is heard, then a
lawnmower. The barber steps in front of the glass: "Bit off the sides?" Hair falls past the lens in sheets. "...Sure."
The engine stops, the cloth drops, and the head in the mirror is not hers. Two seconds of nothing. "How's that?" The
face wobbles. "Love it." The card reader shows the cut, $22, then the tip, $30, and it stops there.

```bash
srstudio record just-a-trim PROJECT
srstudio build just-a-trim PROJECT    # PROJECT/just-a-trim.scene.xml
```

Its first second is a held frame (arm A of the `sp-hook_motion` test). Nobody's hair is redrawn: the cut is another
approved character in the mirror, with Rosa's voice and mouth. New parts live in
[src/srstudio/cutout_shop.py](../src/srstudio/cutout_shop.py): `barbershop` draws the people inside the glass with
`in_mirror=` and the shelf with `on_counter=`, and `barber_cape(spread=True)` is the cloth over the mirror.

## Cutout episode at the store: *Just One Thing* (30)

[episodes/just_one_thing.py](../episodes/just_one_thing.py) is already walking when it starts, with a very small basket: "I
only need light bulbs." The basket is a cart: a lamp, three candles, a plant. "We do need a plant." A bigger cart: a
ladder, a kayak. "It was on sale." Bigger again: a paddle, a life ring. "That's just safety." At the till the screen
says $412, then rolls on while the receipt runs down the frame, and Milo is proud of it. At home, in the dark, sitting
in the kayak, a dead switch goes click, click, click, nothing for longer than is comfortable, click, and it stops on
his eyes.

```bash
srstudio record just-one-thing PROJECT
srstudio build just-one-thing PROJECT    # PROJECT/just-one-thing.scene.xml
```

It moves from the first frame (arm B of the `sp-hook_motion` test). New parts live in
[src/srstudio/cutout_store.py](../src/srstudio/cutout_store.py): `store_aisle` slides its shelves with `drift=`,
`shopping_cart(contents=)` holds the goods behind its front wire, and `kayak(rider=)` seats someone in the cockpit.

## Ink episode: *The Router* (Ink 02)

[episodes/the_router.py](../episodes/the_router.py) is the first original Ink episode: the internet is down and the router
would rather be rebooted by hand. Twenty takes as a shot sequence (desk, human close, router on its shelf, wide).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_router_audio.py PROJECT --font DIR   # voices, effects, timeline.json
python3 episodes/the_router.py PROJECT                                            # scene, SRT, ig.txt
scene-render encode PROJECT/the-router.scene.xml --out-dir OUT                    # OUT/renders/the-router.mp4
```

[episodes/the_router_audio.py](../episodes/the_router_audio.py) makes one request per take through `srstudio.voice`
(typed parse, alignment spells the line, audible, right length), confirms each voice id is the premade voice it names,
and requires ElevenLabs speech-to-text to hear every line as scripted; three interjections were respelled until it did.
Each verified clip is trimmed, levelled and conformed to one 48 kHz mono WAV per take under `audio/`, checked to the
sample, and `timeline.json` lists the takes with words and character timings relative to the take. The key is read
from `ELEVENLABS_API_KEY` and never written. Parts added: `talking-router`, `ink-hand`, `ink-router-shot`,
`ink-router-wide`.

## Ink episode: *Not a Robot* (Ink 03)

[episodes/not_a_robot.py](../episodes/not_a_robot.py): one form before lunch, and the captcha escalates from traffic
lights to sad traffic lights to "every moment you felt truly alive", fails the human for hesitating like one, and the
router welcomes him home. Fourteen takes through `srstudio.takes` (human, captcha and router voices), with the
screens as data in `SCREENS` ([episodes/not_a_robot_audio.py](../episodes/not_a_robot_audio.py)).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/not_a_robot_audio.py PROJECT   # takes, checked by speech-to-text
python3 episodes/not_a_robot.py PROJECT                                # scene, SRT, ig.txt
```

`takes.Script(font=)` names the caption font (file, licence) a script ships with; it defaults to the takes font.
Parts added (`srstudio.ink_captcha`): `ink-captcha`, a verification card with a prompt band, a grid of drawn tiles
(`TILES`: lights, happy and sad lights, car, tree, laptop), timed picks with a tick and a verdict banner, and
`ink-checkbox`, the "I'm not a robot" box whose tick lands at `tick_at`. Bad tiles, picks or timings raise
`CaptchaError`. Burned captions are hidden on the cover (`hide_on_cover`).

## Ink episode: *Message Failed* (Ink 04)

[episodes/message_failed.py](../episodes/message_failed.py): a text about the boss goes to the boss. The router from
*The Router* drops the Wi-Fi so it fails, then retries it because it hates failing; the boss types, agrees, and the
router offers a reply. Fourteen takes through `srstudio.takes` (human and router voices, two effects), with the chats
as data in `SCREENS` and the router's power beats in `ROUTER_BEATS`
([episodes/message_failed_audio.py](../episodes/message_failed_audio.py)).

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/message_failed_audio.py PROJECT   # takes, checked by speech-to-text
python3 episodes/message_failed.py PROJECT                                # scene, SRT, ig.txt
```

Parts added (`srstudio.ink_phone`): `ink-phone`, a held phone with the contact in its header, `Bubble`s (mine in
ink on the right, theirs outlined on the left) that arrive at their second, a delivery status (`STATUS_TEXT`:
sending, not delivered, delivered, read) under the last of mine that changes on the shot's clock, and typing dots
that pulse in the slot their reply lands in; and `ink-phone-shot`, the phone over the desk line with the signature
cactus. A contact, bubble, status or typing span the screen cannot show, or a chat that does not fit, raises
`PhoneError`.

## Ink episode: *U Up?* (Ink 05)

[episodes/u_up.py](../episodes/u_up.py): two in the morning, the human from *The Router* has texted his ex. The router
will not unsend it: it does not fail any more, it has grown (a callback to *Message Failed*). She asks who this is,
then remembers the forty dollars, and the router has already paid them from his account, with a memo. Twelve takes
through `srstudio.takes` (human and router voices, two effects), the chats as data in `SCREENS`, under the contact
"Do Not Text" ([episodes/u_up_audio.py](../episodes/u_up_audio.py)). It reuses `ink-phone`, `ink-closeup` and the
router shots; no new parts.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/u_up_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/u_up.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Premium Suction* (Ink 06)

[episodes/premium_suction.py](../episodes/premium_suction.py): the robot vacuum has stopped in the middle of the floor,
because its free trial ended. Suction is monthly, the kitchen premium, the corners platinum; what is free is the map
of the home, which it sells. The landlord texts: he saw the map, and rent goes up in May. He liked the second
bedroom, which is the closet. Deleting it is premium. Fourteen takes go through `srstudio.takes`: the human (Chris,
as in the earlier Ink episodes), the vacuum (Lily) and one effect
([episodes/premium_suction_audio.py](../episodes/premium_suction_audio.py)). The vacuum's moves and displays are data
in `VACUUM`, the map's in `MAPS`, the chat in `SCREENS`.

The new parts are in [src/srstudio/ink_vacuum.py](../src/srstudio/ink_vacuum.py):

- `vacuum` (`talking-vacuum`): a disc seen from above at three quarters. Its ring of lights chases and voice marks
  flicker while it speaks. `state` is `still`, `roll` (it rolls off through the take) or `stop` (it rolls in and
  brakes), and `display` puts a word of up to five characters on top. The side band carries the signature code.
- `vacuum_shot` (`ink-vacuum-shot`): the floor, the baseboard, the outlet and the dock, with the vacuum normal or
  close.
- `floor_map` (`ink-floor-map`): the app's map, with `Room`s outlined and named (`PLAN` by default). `trace=(start,
  end)` draws the route dot by dot, and `relabel=(room, label, at)` renames and shades one room at its moment.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/premium_suction_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/premium_suction.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Home Sick* (Ink 07)

[episodes/home_sick.py](../episodes/home_sick.py): it is Monday, 2:14 PM, and the human is home early with sunglasses on
his forehead. His video doorbell will not let him in, because the resident is home sick today. He got better? Then
he is late for work. The doorbell asks the street's group chat who he is, from his own account: never seen him,
nope, and, after a hold, his boss: that's my employee. Face recognized, welcome home; the boss texts him, feeling
better? Nice tan. Thirteen takes go through `srstudio.takes`: the human (Chris), the doorbell (George) and three
message dings ([episodes/home_sick_audio.py](../episodes/home_sick_audio.py)). The face box's tags are data in `LENS`,
the doorbell's verdicts in `DOORBELL`, the chats in `SCREENS`.

The new parts are in [src/srstudio/ink_doorbell.py](../src/srstudio/ink_doorbell.py):

- `doorbell` (`talking-doorbell`): a tall rounded box with the lens, the speaker and the button. Its ring of lights
  chases and voice marks flicker while it speaks, and `mark=(verdict, at)` shows a cross (`deny`) or a tick
  (`allow`) on the button from `at`. It carries the signature code.
- `doorstep` (`ink-doorstep`): the siding, the front door with its panels, knob and deadbolt, the house number
  (`number=`, up to four characters), the mat and the signature cactus, with the doorbell beside the door, normal or
  close.
- `doorbell_view` (`ink-doorbell-view`): the doorbell's camera. The human is seen through a round lens with REC
  blinking, a FRONT DOOR strip with `clock=`, and a face box whose tag changes at each `(at, text)` of `tags=`.

`ink.human(shades=True)` pushes a pair of sunglasses up on the doodle's forehead; the default draws him as before.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/home_sick_audio.py PROJECT --font DIR   # takes, checked by speech-to-text
python3 episodes/home_sick.py PROJECT                                           # scene, SRT, ig.txt
```

## Ink episode: *Pay to Park* (Ink 08)

[episodes/pay_to_park.py](../episodes/pay_to_park.py): the human holds a coin up to a parking meter whose slot is taped
over. Coins? How retro. The meter sends him through its app: download it, create an account (full name, email, shoe
size), choose a password with a capital, a symbol and a childhood memory. Biscuit. That memory is already in use.
Enable location; he is right in front of it. Minimum session two hours, rate your parking experience, and "Session
started!" as the tow truck lifts his car. The hold music stops dead as it drives off, and he says thank you. Fourteen
takes go through `srstudio.takes`: the human (Chris), the meter (Laura), two effects and a hold-music bed
([episodes/pay_to_park_audio.py](../episodes/pay_to_park_audio.py)). The app's screens are data in `SCREENS` and the
meter's readings in `DISPLAYS`; a cue there is a word of the take's line, resolved on the recorded words, or seconds
into the take. Take 06's `heard=("Biskit",)` is an operator-approved speech-to-text spelling (2026-10-29).

The new parts are in [src/srstudio/ink_meter.py](../src/srstudio/ink_meter.py):

- `meter` (`talking-meter`): a box on a post with a display whose reading changes at each `(at, text)` of
  `display=`, lights that chase and voice marks while it speaks, a QR code, and a coin slot taped over with
  `TAPE_TEXT`. Lettering that would draw under `LEGIBLE_PX` at the scale it is seen is a pen scrawl instead. It carries
  the signature code.
- `kerb` (`ink-kerb`): the pavement and the road from the side, with the doodle, the meter, the signature cactus and
  his parked car, or the meter alone (`close=True`). `tow=` brings a tow truck, already hooked on, that lifts the
  car's front by `LIFT_DEGREES` and drives off with it; a negative `tow` began before the take, so a cut carries the
  tow on. `view=` frames it: `KERB_VIEW`, `TOW_WIDE` (the default with a tow) or `TOW_TIGHT` on the car and the truck.
- `app_screen` (`ink-app-screen`): the held phone of `ink_phone` with a form on it. A title bar, `AppRow`s that
  arrive, tick or are refused (`taken=`: the row flips to ink with a cross and `TAKEN_TEXT`), a progress bar and five
  stars that light one after another.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/pay_to_park_audio.py PROJECT --font DIR   # takes, bed, checked by speech-to-text
python3 episodes/pay_to_park.py PROJECT                                           # scene, SRT, ig.txt
```

## Soft style episode: *Focus Mode* (07)

[episodes/focus_mode_audio.py](../episodes/focus_mode_audio.py) declares seven sung lines and a record scratch as
`<generated>` ElevenLabs items. The engine resolves and pins them, speech-to-text must hear each line as written,
and each line is placed on its beat of `Groove(bpm=120)`. A line that would run into the next stops the build. The
script then synthesises the groove on the same grid: bars 0–5 play, bars 6–7 rest for the deadline, and the groove
creeps back in bars 8–9. [episodes/focus_mode.py](../episodes/focus_mode.py) places Pip's cues on that grid (typing on
eighths, sway, wiggle, hands-behind-head groove, freeze, a planted-foot side-step out of frame) with eased
in-betweens (four drawings before a beat, two before an eighth; the scratch cuts without any), arcs on sitting and
standing, overshoot on dance landings and a contact shadow, and burns the lyrics at the top in Poppins inside
the `VERTICAL` safe area. The audio script also pins the caption face with `fonts.install`.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/focus_mode_audio.py PROJECT --key-stdin
python3 episodes/focus_mode.py PROJECT && scene-render encode PROJECT/focus-mode.scene.xml --output main -o "$PWD/focus-mode.mp4"
```

## Soft style episode: *Camera Off* (08)

Both sung Soft episodes share one audio pipeline, `srstudio.song` ([src/srstudio/song.py](../src/srstudio/song.py)). A `Song` lists its voices
by role, its `Line`s on (bar, beat), its `Effect`s, the groove `Section`s and where the last line must end. `main`
resolves and pins the items, checks each line with speech-to-text, places the lines and effects on the grid, renders
the groove, pins the caption font and writes `dialogue.json`. The refactor leaves episode 07's `dialogue.json`
byte-identical.

[episodes/camera_off_audio.py](../episodes/camera_off_audio.py) is the second song. It has ten lines in two voices:
Pip (Will) sings, and the boss (Eric) talks from the call. It also has a mouse click, a call chime and a groove. Polite
hat and keys play in bars 0–2, the whole groove in bars 4–7, and the meeting music returns in bars 10–11. The music
rests while the camera goes off and while the boss asks.

In [episodes/camera_off.py](../episodes/camera_off.py), Pip nods along on the beat (`nod`), clicks the camera off,
grooves, cheers (`cheer-a/b`) and waves at nobody (`wave-a/b`). He freezes on the chime, then scrambles back to type
on the eighths. A call badge over the laptop shows what the meeting sees: CAM ON, CAM OFF, SHARE?, SHARING. Boss lines
are captioned in blue. The video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/camera_off_audio.py PROJECT --key-stdin
python3 episodes/camera_off.py PROJECT && scene-render encode PROJECT/camera-off.scene.xml --output main -o "$PWD/camera-off.mp4"
```

## Soft style episode: *Day Off* (11)

[episodes/day_off_audio.py](../episodes/day_off_audio.py) is an instrumental `Song`: six 4-second chunks composed at
120 bpm with no vocals, and Pip's six lines spoken by Will on the bar grid. Two effects sit on the grid with them: a
calendar ping and a meeting-ended chime. An earlier sung version failed its speech-to-text checks repeatedly.
Spoken lines over a composed bed passed on the first composition seed.

In [episodes/day_off.py](../episodes/day_off.py), Pip spends Saturday in `blob.home`. His hands keep typing on nothing
(seeded keyboard foley on the eighths), he nods along to the lamp, and he books a meeting with the sofa. The meeting
runs over and he extends it. The calendar is a `soft_props.status_badge`
([src/srstudio/soft_props.py](../src/srstudio/soft_props.py), graphic `soft-status-badge`): pill states that pop in
by span, one of them struck through (SOFA SYNC, ACCEPTED, ENDED, EXTEND?, EXTENDED). Two crash zooms
(`camera.push_in`, 0.2 s) land on Pip's face, on the invite and on the snap back to work. Each one cuts back to the
wide shot on a beat, and the frame drops 150 px while zoomed so the sprout clears the badge. The video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/day_off_audio.py PROJECT --key-stdin --engine scene-render
python3 episodes/day_off.py PROJECT && scene-render encode PROJECT/day-off.scene.xml -o "$PWD/day-off.mp4"
```

## Soft style episode: *Unlimited PTO* (13)

[episodes/unlimited_pto_audio.py](../episodes/unlimited_pto_audio.py) is an instrumental `Song` with two speakers on
the bar grid: Bo (Eric, the boss of episode 08) and Pip (Will). It has three decline blips and an approval chime,
and a composed bed of six 4-second chunks: office-pop while Bo sells unlimited vacation, one held pad for the hold
before the punchline, and a steel-drum groove for the button.

In [episodes/unlimited_pto.py](../episodes/unlimited_pto.py), Bo is on screen for the first time, in the polished
`blob.meeting_room`. Every one of his cues is mirrored (`Cue(flip=True)`), so he faces Pip across the room. Pip
stands up from the swivel chair to ask (Friday, Friday afternoon, lunch) and drops back at each decline. The
request badge (`soft_props.status_badge`) shows each ask in amber, then DECLINED struck through in red, and finally
Bo's own "BO: BALI 3 WK" in green. Bo waves and walks out, and Pip types on. Bo's lines are captioned in blue. The
video is 24.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/unlimited_pto_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/unlimited_pto.py PROJECT && scene-render encode PROJECT/unlimited-pto.scene.xml -o "$PWD/unlimited-pto.mp4"
```

## Soft style episode: *Return to Office* (15)

[episodes/return_to_office_audio.py](../episodes/return_to_office_audio.py) is an instrumental `Song`: Pip (Will) and
Bo (Eric) on the bar grid, six effects (a call chime, a seagull, the call ending and three motion-sensor light
switches) and a composed bed in six chunks: office-pop for the welcome, steel drums for Bali, a held pad before the
punchline, almost nothing for the lights.

In [episodes/return_to_office.py](../episodes/return_to_office.py), Pip stands alone in `blob.meeting_room` on day one
back, and Bo calls in from a beach on the wall screen. The room takes the call through an opt-in slot,
`blob.meeting_room(on_screen=)`: `blob.meeting_screen()` gives the screen picture as a flat frame (its top-left, size
and the `skewY` that lays it along the back wall), and the slot draws into it, masked to the picture; without it the
slide is drawn as before. The call is the new `soft_props.beach_call` graphic (`soft-beach-call`: sky, sun, sea,
sand, a swaying palm, a `guest` slot and a name tag placed by `tag=`), with Bo's rig grooving inside it. Two crash
zooms land on the screen; the status badge tells the story (RTO: DAY 1, ON CALL, 312 WATCHING, CALL ENDED, NO
MOTION), and a dark overlay plays the motion-sensor lights that switch off on Pip, back on for a wave, and off
again. The video is 28.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/return_to_office_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/return_to_office.py PROJECT && scene-render encode PROJECT/return-to-office.scene.xml -o "$PWD/return-to-office.mp4"
```

## Soft style episode: *Smart Lamp* (17)

[episodes/smart_lamp_audio.py](../episodes/smart_lamp_audio.py) is an instrumental `Song` with three voices: Juno
(Laura), Pip (Will) and the smart lamp (Matilda), four effects (a wake-up blip, two order chimes and an error bloop)
and a composed bed in five chunks: a domestic sitcom groove for the argument, a shopping-channel bounce for the
orders, a held pad before the proposal and a short outro.

In [episodes/smart_lamp.py](../episodes/smart_lamp.py), Pip sits on the sofa in `blob.home` and Juno stands at the left.
The floor lamp is the third character through an opt-in slot, `blob.home(lamp_talk=)`: a list of `(start, end)`
spans, in order and apart (a `BlobError` otherwise), during which a halo, a lit shade and an orange rim glow; without
it the room is drawn as before. `blob.LAMP_SHADE` is the shade's point in the room, so the camera anchors on it and
pushes in at "She said yes." and at the last line. The status badge tells the story (LISTENING, + FLOWERS, + RING,
ENGAGED, PARDON?). The video is 30.4 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/smart_lamp_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/smart_lamp.py PROJECT && scene-render encode PROJECT/smart-lamp.scene.xml -o "$PWD/smart-lamp.mp4"
```

## Soft style episode: *The Cake* (19)

[episodes/the_cake_audio.py](../episodes/the_cake_audio.py) is an instrumental `Song` with three voices: Juno (Laura),
Pip (Will) and Bo (Eric), three effects (a party blower, a plate turned on the counter and a sad trombone) and a
composed bed in five chunks: an office sitcom groove for the collection, an office-party groove for Bo's entrance, a
held pad for the pause before the cake turns, the party groove deflated, and an outro.

In [episodes/the_cake.py](../episodes/the_cake.py), Juno and Pip are in the polished break room (`blob.break_room`) and
Bo glides in from the left carrying the cake. The cake is a new prop, `soft_props.cake`: a frosted round cake on a
plate with one candle and iced lettering (up to two lines of twelve characters) on the front. With `back=` and
`turn_at=` it turns half round on its plate (`CAKE_TURN`) and shows the back lettering. `lettering=` limits the
lettering to spans: the lettering is text, which the engine holds inside the safe area, so it shows only while the
cake is in frame. The camera cuts to the cake as Pip reads WE'LL MISS YOU, holds through the turn (BYE PIP) and the
trombone, cuts to Pip for his line and goes back wide. The video is 32.5 s.

```bash
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_cake_audio.py PROJECT --key-stdin --engine scene-render
SRSTUDIO_ENGINE=scene-render python3 episodes/the_cake.py PROJECT && scene-render encode PROJECT/the-cake.scene.xml -o "$PWD/the-cake.mp4"
```

## Soft style episode: *Hang Out*

The first Soft reel with no music: [episodes/hang_out_audio.py](../episodes/hang_out_audio.py) records through
`srstudio.interview` (Juno is Laura, Pip is Will, the old lines the same voices taken slower), and the build writes its
foley with `srstudio.foley`. [episodes/hang_out.py](../episodes/hang_out.py) is staged for a close shot in `soft_sets`,
frontal sets for a cast at about twice `blob.SCALE`: `soft_sets.park` takes `growth=`, so the tree between them goes from
a staked sapling to a crown wider than the frame while the town rises and the two-shot never changes. Its props are
`soft_props.phone` (held with `blob.held`, which rides a group between the hands), `soft_props.bench`, `soft_props.cane`
and `soft_props.time_card`, whose year flips on each cut. The video is 20.7 s.

```bash
srstudio record hang-out PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build hang-out PROJECT && scene-render encode PROJECT/hang-out.scene.xml --out-dir generated --strict
```

## Soft style episode: *Early Night*

A narrator goes on announcing an early night while the hour card runs away from him. [episodes/early_night.py](../episodes/early_night.py)
is a bed seen from its foot, `soft_sets.bedroom`: rows of `Light` take the room from one flickering pool around a phone to
black and then to day, and rows of `Shot` cut in on everything but the nightstand, which keeps the signature marks in the
last frame, a single open eye. What is on her phone is drawn at full frame with `soft_props.shovel` and `soft_props.hive`.
The video is 17.1 s.

```bash
srstudio record early-night PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build early-night PROJECT && scene-render encode PROJECT/early-night.scene.xml --out-dir generated --strict
```

## Soft style episode: *Why*

Five whys to the edge of what anyone knows, in [episodes/why.py](../episodes/why.py). `soft_sets.playroom` is a room straight
on, with a window of sky and a door; its `Shot` rows cut between one fixed close-up of Pip and a close-up of Bo that comes
in a little more each time, and `Dim` takes the light out of the room when he sits down. The first and last shots are the
same room with the sizes swapped, with `soft_props.necktie` and
`soft_props.briefcase`. The video is 20.0 s.

```bash
srstudio record why PROJECT   # the key from ELEVENLABS_API_KEY
srstudio build why PROJECT && scene-render encode PROJECT/why.scene.xml --out-dir generated --strict
```

## Cel style package: *Work Training Be Like*

The fourth style comes from the silent package `mushroom-training-2.0.0` (a recreation of an Under Studio
workplace-training cartoon: a mushroom at a desk, teal caption boxes with hand lettering, a slow camera push).
[episodes/mushroom_training.py](../episodes/mushroom_training.py) rebuilds its `scene.xml` element for element and its
SRT byte for byte from the package's own data: `script.json` (timed captions with their lettering boxes and glyph
paths), `assets/camera.json` and `assets/room-camera.json` (measured camera samples every 0.25 s), `assets/poses.json`
(which drawing is held when) and `assets/pose-NN.json` (the traced contours of each drawing). Nothing in the library
is specific to the mushroom: `cel.traced` holds any sheet of drawings, `cel.room` draws the set in any palette, and
`cel.lettering` draws any boxed glyph paths. The package's character art, dialogue and lettering are adapted from the
reference and remain their author's; the style, the loaders and the conventions are what the library keeps.

```bash
python3 episodes/mushroom_training.py /path/to/mushroom-training-2.0.0/project   # scene.xml, SRT, ig.txt, qa/
scene-render encode scene.xml -o /abs/path/mushroom-training.mp4                 # 1053 frames, 43.875 s, silent
```

### Narrated master

The silent build is the fidelity reference; a narrated master is the same scene with an ElevenLabs voice-over
(premade voice *Alice*) and keyboard foley on the mix. [episodes/mushroom_training_audio.py](../episodes/mushroom_training_audio.py)
reads the caption script and speaks each caption through `srstudio.voice` (typed parse, alignment check,
speech-to-text that must hear the scripted words, voice id confirmed by name) at the narrator's own pace: nothing
is asked again faster and nothing is time-stretched. `srstudio.narration.plan_relaxed` places the clips: a line
that outlasts its caption spills into the next, which waits for it (a 40 ms guard, at most 0.9 s after its own
caption, then the spilling line is cut instead); a montage fragment ("He...", "Lunch...") starts on its caption
and is cut where the caption ends, which is the joke; and the project is extended past the last caption so the
last line is heard whole. Three one-word fragments and the spelt-out score are spoken in a form the recogniser
can confirm (`SPOKEN`). Under the voice, `srstudio.foley` synthesises two to four keystrokes wherever the
package's tracked hand (`assets/poses.json`, sampled every 0.25 s) moves more than 8 px while on the keyboard
(poses flagged `raised` are skipped), seeded so the bed is reproducible; the keystroke onsets are written to the
manifest (`effects[].taps`) and the drawn keyboard sinks 4 px on the same beats.
The clips are conformed to 48 kHz mono under `audio/` and listed in `narration.json` with their placement, the
typing bed (`effects`), the extended `duration` and SHA-256s; `mushroom_training.py --voice` checks the manifest
and the hashes, holds the last drawing and caption to the extended end, and presses the keyboard: a traced
drawing's ink is one compound path whose holes are the coloured areas, so no limb can move on its own, but
`cel.Pressed` splits every fill's subpaths inside the keyboard box into what sinks (filled regions with the
holes they carry) and what stays (the ink frame), so the keyboard face and its key rows dip inside the frame on
each keystroke. It adds one dialogue track per clip and one effects track at −8 dB, and encodes with AAC
mastered by the Cel style's mix. The cloud step needs `SRSTUDIO_ALLOW_CLOUD=1` and `ELEVENLABS_API_KEY`; cached takes cost nothing.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/mushroom_training_audio.py PROJECT   # audio/vo-NN.wav, narration.json
python3 episodes/mushroom_training.py PROJECT --voice                       # scene.xml with the 41 tracks
scene-render encode PROJECT/scene.xml -o /abs/path/mushroom-training.mp4    # h264 + aac, 43.875 s
```

## Stick style package: *Check With My Team*

The fifth style comes from the silent package `check-with-my-team-1.0.0` (a recreation of a `@theaifilmmaker`
cartoon: a stick figure at a laptop says they will check with their team, and the team turns out to be a person and
three AI assistants, stick figures with logo badges for heads, dancing in a garden).
[episodes/check_with_my_team.py](../episodes/check_with_my_team.py) rebuilds its `scene.xml` element for element and its
SRT byte for byte from the package's own data: `script.json` (timed captions with their sizes), `assets/poses.json`
(141 traced poses at 12 fps: the seated figure's legs, head and ink plates, or the dancers' measured head centres,
head angle, body and head plates), `assets/icons.json` (the badge drawings around their traced centres),
`assets/lettering.json` (the hook and headline as glyph plates) and `assets/foliage.json`. `stick.room` and
`stick.yard` draw the two sets, `stick.figures` holds one group per pose and puts a `stick.Badge` (a coloured face
with an icon drawing turned by the measured head angle) on every dancer but the leader, and `stick.hook`,
`stick.headline` and `stick.captions` letter it. The badge faces, their colours and the logos are the episode's data,
not the library's; the character art, dialogue and lettering are adapted from the reference and remain their
author's.

`--voice` builds the same picture as `scene.silent.xml` and dubs into `scene.xml` what
[episodes/check_with_my_team_audio.py](../episodes/check_with_my_team_audio.py) wrote: one ElevenLabs take cut at its
word boundaries and placed phrase by phrase on the captions (`srstudio.phrasing`), and an ElevenLabs Music song at
the dance's measured 152 bpm whose drop lands on the cut to the garden (`dub.beat_offset`, `dub.music_bed`). The
voiced scene ends at frame 230, where the package's recording starts over, so it loops without a repeat.

```bash
python3 episodes/check_with_my_team.py PROJECT --package /path/to/check-with-my-team-1.0.0   # verify and copy inputs
python3 episodes/check_with_my_team.py PROJECT                     # silent scene.xml + SRT, the fidelity reference
grep '^ELEVENLABS_API_KEY=' .env | cut -d= -f2- | SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/check_with_my_team_audio.py PROJECT --key-stdin
python3 episodes/check_with_my_team.py PROJECT --voice             # scene.xml with the voice and the music, 9.583 s
```

### An original Stick episode: *Screen Share* (R2)

[episodes/screen_share.py](../episodes/screen_share.py) is the first Stick episode drawn rather than traced
([ADR 0009](../docs/decisions/0009-stick-rig.md), [ADR 0012](../docs/decisions/0012-stick-looks-and-call.md)). Dev, a
`stick-rig` figure, sits in the `stick-room` through a video call that shares too much, a disconnect that comes just
in time, and a "got a sec?" on a Friday. `stick.rig` poses a figure from `RigKey`s, seated (`SEATED`) or standing
(`STANDING`), dressed by a `stick.Look` (hair, glasses, tie), placed, scaled or mirrored anywhere, and lip-syncs the
mouth to the take's phones: Dev keeps the default look, the boss stands in the room on Friday, bald, in glasses and a
tie. `stick.call` is the call: the boss's shared inbox above the captions, one row marked, and the participants'
tiles below. `stick.camera` cuts to a close shot or pushes in; `stick-card` letters each beat's hook in Inter; the
captions page the words (`subtitles.chunk_words`) with a width check, their outline drawn as a layer of its own
(`captions(outline="layer")`, or `"none"` over the call's dark screen) so the contrast check measures the white
against the ink: the encode reports no contrast warning. [episodes/screen_share_audio.py](../episodes/screen_share_audio.py) voices the nine lines with ElevenLabs and
keeps a take only when its transcript matches the script.

```bash
SRSTUDIO_ALLOW_CLOUD=1 ELEVENLABS_API_KEY=... python3 episodes/screen_share_audio.py PROJECT --font FONT_DIR   # takes + timeline.json
python3 episodes/screen_share.py PROJECT        # screen-share.scene.xml + SRT, 17.542 s
```

### An original Stick episode in a car: *Repeat After Me* (R3)

[episodes/repeat_after_me.py](../episodes/repeat_after_me.py) puts Dev behind the wheel on the drive home. He makes
the viewer repeat his vows to stop working after hours, until the passenger seat gives him away
([ADR 0018](../docs/decisions/0018-stick-car-and-voiced-takes.md)).

The car is `srstudio.stick_car`:

- `stick-car` is the cabin seen from the passenger door. The country passes the window in six parallax layers: the
  far ones out of focus under a haze, the near trees, poles, wires and guardrail motion-blurred by the engine. An
  oncoming car can pass on a cue (`passing=`).
- `DRIVING` poses put the hands on the wheel's rim.
- `stick-cockpit` draws over the figure: the knee panel, the wheel, a seatbelt per pose, the trees' soft shadows
  sweeping across the cabin, the sun and a vignette.
- `stick-ride` bobs the driver and the scenery on the suspension.
- `stick-car-seat`, `stick-laptop` and `stick-phone` stage the reveal.

Depth comes from the engine's effects, through `Canvas.effect`: blur, drop and inner shadows, screen and multiply
blending, and per-node motion blur.

The words come one at a time, as spoken (`stick.word_cues` + `stick-words`). The mouth uses
`lipsync.SPEECH_MOUTH` through `stick.rig(mouth=)`.

[episodes/repeat_after_me_audio.py](../episodes/repeat_after_me_audio.py) is a `srstudio.takes.Script`: seven lines in
the premade voice Will, a phone-buzz effect and an instrumental bed from the ElevenLabs Music API. Each take must be
heard as scripted, and the bed must hold no words and cover the episode. `screen_share_audio.py` uses the same
pipeline.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/repeat_after_me_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/repeat_after_me.py PROJECT     # repeat-after-me.scene.xml + SRT, 14.708 s
```

### An original Stick episode at the store: *Unexpected Item* (R4)

[episodes/unexpected_item.py](../episodes/unexpected_item.py): Dev buys one avocado at the self-checkout. The kiosk
wants it in the bagging area, calls it unexpected, wants it out, wants it back, and calls for help; the supervisor
reads his month off the screen and makes him employee of the month. He asks whether he gets paid, which is an
unexpected item too. On Saturday he wears the apron and says the kiosk's line to the next shopper.

The store is `srstudio.stick_shop`:

- `stick-checkout`: stocked shelves under strip lights, the hanging sign, a tiled floor and the bagging shelf
  (`BAG_SPOT`).
- `stick-kiosk`: the pedestal, the scanner bed and the screen. `Screen(start, text, tone, face=)` holds each message
  until the next, in a tone from `TONES` (idle, error, help, award; white lettering passes the 4.5:1 contrast
  check on every header), and an award shows a `Look`'s face. The lamp flashes red at each `alarm`. A schedule the
  screen cannot show raises `StickDataError`.
- `stick-avocado` and `stick-name-badge`. `hand(pose, at=, flip=)` finds where a placed figure's near hand carries
  an item; `SHOPPER_AT` and `CLERK_AT` (mirrored) stand `STANDING` poses either side of the counter.

`stick.Look(apron=)` dresses the torso in a shop apron under the tie; it is off by default, so earlier episodes
rebuild byte for byte. [episodes/unexpected_item_audio.py](../episodes/unexpected_item_audio.py) is a `takes.Script`
in three premade voices (Laura for the kiosk, Will, Alice), a scanner beep and a supermarket music bed, with the
screens per take in `SCREENS`.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/unexpected_item_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/unexpected_item.py PROJECT     # unexpected-item.scene.xml + SRT, 34.333 s
```

### An original Stick episode in a flat for rent: *The Viewing* (R5)

[episodes/the_viewing.py](../episodes/the_viewing.py): flat hunting, day 41. The kitchen has a toilet in it, the window
is painted on, and the bed folds down out of the wall with Gary asleep in it: he comes with the lease. Two grand a
month, each. Dev takes it and is applicant forty-seven; Gary, asleep, is forty-six.

The flat is `srstudio.stick_flat`:

- `stick-studio-flat`: the wall and floorboards, the counter with its stove, pot and tap, a toilet beside the stove,
  a window whose sunny view is painted on (the blue runs over the frame and drips), and the bed's cabinet. The set
  is `SET_W` wide, so a camera turns from the kitchen (`WINDOW_FOCUS`) to the bed (`BED_FOCUS`). Figures stand at
  `VIEWER_AT` and, mirrored, `AGENT_AT`.
- `stick-murphy-bed`: closed in the wall, folding down at `drop_at` through one mid frame (`FOLD`), and open on the
  floor with a `sleeper` under the blanket who snores and opens his mouth in each `talk` span. A timing the bed
  cannot show raises `StickDataError`.

The word captions take three options, off by default so earlier episodes rebuild byte for byte:
`stick.word_cues(size=)` letters the cues smaller so more quick words join a readable cue, `borrow=True` lets a cue
shorter than `min_seconds` take time from the next cue of its take, and `stick.words(scrim=)` darkens the band behind
the words over a bright set. With them the encode reports no legibility or contrast warning.
[episodes/the_viewing_audio.py](../episodes/the_viewing_audio.py) is a `takes.Script` in three premade voices (Will,
Lily for the agent, Callum for Gary), a bed-drop effect and a lounge-house bed.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_viewing_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/the_viewing.py PROJECT     # the-viewing.scene.xml + SRT, 25.125 s
```

### An original Stick episode at the gym: *Cancel Anytime* (R6)

[episodes/cancel_anytime.py](../episodes/cancel_anytime.py): Theo wants to cancel his gym membership. The sign says
anytime, with an asterisk: in person (he is here), on a Tuesday (it is Tuesday), before sunrise (it is still dark),
with a note from his trainer, whom he has never met. Any other way? A death certificate. Whose? They are flexible.
Then the sun comes up in the window, and Brooke at the desk sees him next week.

The gym is `srstudio.stick_gym`:

- `stick-gym`: the wall with the brand (`BRAND`), a poster, a dumbbell rack, a treadmill and mats, and a window on a
  night city. `gym(..., sunrise=)` keys the dawn layer and the sun over `DAWN` seconds from that moment in the shot;
  `sunrise=0` draws the day already up, and a time outside the shot raises `StickDataError`.
- `stick-gym-counter`: the front desk with a card reader, a cactus and a tent sign: the headline in `LETTER` red
  (contrast-checked) and a fine-print line that only reads in a close-up. A sign longer than `SIGN_CHARS` or fine
  print longer than `FINE_CHARS` raises `StickDataError`. Figures stand at `MEMBER_AT` and, mirrored, `STAFF_AT`.

`stick.word_cues(tail=True)` (off by default, so earlier episodes rebuild byte for byte) mends a take's last cue
when it is shorter than `min_seconds`: it joins the cue before it when the joined words fit the width, and otherwise
takes that cue's last words. It needs `min_seconds`. With it the encode reports no legibility or contrast warning.
[episodes/cancel_anytime_audio.py](../episodes/cancel_anytime_audio.py) is a `takes.Script` in two premade voices
(Callum for Theo, Jessica for Brooke) and a 120 BPM gym-pop bed.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/cancel_anytime_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/cancel_anytime.py PROJECT     # cancel-anytime.scene.xml + SRT, 27.208 s
```

### An original Stick episode at school: *What My Dad Does* (R7)

[episodes/what_my_dad_does.py](../episodes/what_my_dad_does.py): parent-teacher night. Dev perches on a child's chair,
knees above his hip, while the teacher reads his son's essay: Dad works from home, a tie on top and no pants; his job
is saying "I think you're on mute"; at three he has Focus Time, and Focus Time snores. Dev has an answer for each.
Last line: Dad says he works from home. Mom says he's just home. What did he get? An A. His mom helped.

The classroom is `srstudio.stick_school`:

- `stick-classroom`: the wall with an alphabet strip, a chalkboard lettered `board=` (up to `BOARD_CHARS`), the
  class's drawings pinned up, a clock and the linoleum floor.
- `stick-tiny-chair` and the `PERCHED` poses (`perch`, `perch-lean`, `perch-shrug`, `perch-point`, `perch-face`):
  a grown-up on a child's chair, the hip on the seat at `SEAT_Y` and the knees above it.
- `stick-teacher-desk`: the front layer at `DESK_X`, with marked papers, an apple and the cactus. The teacher
  stands mirrored at `TEACHER_AT` in `TEACHER_POSES` (`STANDING` plus `READING`: `read`, `lower`), and
  `held(pose)` is where the page in her hands goes.
- `stick-essay`: the child's page, its title and author, the first `shown` lines (up to `ESSAY_LINES`, each up to
  `LINE_CHARS`), a highlighter sweeping line `mark` over `SWEEP` seconds from `mark_at`, a circled `grade`, a margin
  `note` that appears at `note_at`, and the crayon drawing of Dad. A page that would run ahead of the reading, or
  letter more than it can hold, raises `StickDataError`.

[episodes/what_my_dad_does_audio.py](../episodes/what_my_dad_does_audio.py) is a `takes.Script` in two premade voices
(Will for Dev, Sarah for the teacher), one chalk effect and a 120 BPM pizzicato bed; `PAGES` says, per essay take,
how many lines are up, which is marked and the spoken word the highlighter starts on.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/what_my_dad_does_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/what_my_dad_does.py PROJECT     # what-my-dad-does.scene.xml + SRT, 32.417 s
```

### An original Stick episode at the airport: *Group 9* (R8)

[episodes/group_nine.py](../episodes/group_nine.py): gate B9. Sam asks if Group 9 is boarding. After the luggage; his
bag is Group 4, and it's doing great. An upgrade? Same seat, you just pay. The plane can't leave without him?
Everyone says that. He puts on the cap: he's the pilot, and pilots are Group 9. Button: row 38, between two
neighbours who own both armrests, this is your captain speaking from the middle seat.

The airport is `srstudio.stick_airport`:

- `stick-gate`: the window with the parked plane, a `NOW BOARDING` sign calling `now=` (up to `NOW_CHARS`) under
  the gate number `gate=` (up to `GATE_CHARS`), the waiting-room seats and the carpet.
- `stick-gate-podium`: the agent's podium at `PODIUM_X`, drawn in front of the agent standing mirrored at
  `AGENT_AT`; `plate=False` leaves its gate plate unlettered for a close-up whose caption band would cross it.
- `stick-carry-on`: a wheeled bag whose tag (`TAG_SPAN` from its middle) is lettered `tag=` (up to `TAG_CHARS`;
  `None` leaves it blank). Place it so the tag ends left of `PODIUM_X`, or the podium hides it.
- `stick-cabin` and `stick-armrests`: a row seen from the aisle, the row number `row=` and seat letters `seats=` on
  the overhead bins, seat backs at `SEATS` (`SEAT_STEP` apart); the armrests at `ARMRESTS` are drawn after the
  passengers so an elbow rests on them. `SQUEEZED` holds the seated poses: `tucked` and `tucked-up` keep both
  elbows between the armrests, `spread` takes the neighbouring one.

`stick.Look(cap=)` (a `#rrggbb` colour; `None`, the default, draws no cap) puts a peaked cap with a badge on the
head. `stick.word_cues(balance=True)` (off by default) splits each take where its shortest cue lasts longest within
the width limit, the fewest cues on a tie, instead of filling cues greedily from the left; it needs `width` and
refuses `tail`. [episodes/group_nine_audio.py](../episodes/group_nine_audio.py) is a `takes.Script` in two premade
voices (Liam for Sam, Matilda for the agent) and a 120 BPM airport-lounge bed; `NOW` says which group the sign calls
on each gate take, and `CAPPED` the take from which Sam wears the cap.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/group_nine_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/group_nine.py PROJECT     # group-nine.scene.xml + SRT, 25.625 s
```

### An original Stick episode in the car: *The Exit* (R9)

[episodes/the_exit.py](../episodes/the_exit.py): Dev has missed the exit, and he and Noor run their oldest argument in
shorthand. "Your sister's wedding." "Your mum's birthday." "The tent." "The tent." Dead air. "Sorry." "Sorry." Then
it dawns on them: they are not going to her sister's. Her sister texts; Noor puts the phone face down.

The car from the front is `srstudio.stick_windshield`:

- `stick-windshield`: the back layer seen from the hood, with the sky, the headliner, the rear window with the road
  receding behind the car (`speed=` dashes a second), the rear seat and the two front seats at `SEATS`.
- `FRONT` holds the seated poses, centred on x 540: `sit`, `drive`, `cite`, `crossed`, `reach` and `slump`. Place
  them with `stick.rig(at=PASSENGER_AT)` or `at=DRIVER_AT`.
- `stick-windshield-dash`: what lies between the camera and the couple. That is the wheel, the dashboard (its top at
  `DASH_TOP`) with the cactus, the phone in its mount buzzing at `buzz=`, put face down at `down=`, the glare, the
  wipers, the pillars and the hood with the code. The phone cannot buzz in its mount once it is down.
- `COUPLE` holds the couple's looks under their short names (`dev`, and `noor`: a bun and glasses).

[episodes/the_exit_audio.py](../episodes/the_exit_audio.py) is a `takes.Script` in two premade voices: Will for Dev,
as in R3, and Jessica for Noor. It has two effects and a 120 BPM car-radio bed, hushed (`gloss_reel.hush`) through
the dead air. It also holds the staging: `PARTS`, both figures' poses per take; `SETTLE`, the beat after a line
lands; and `CAMERAS`, framed as follows:
- the two-shot at 1.25× on the windshield;
- the singles at 1.7×;
- the face-down punch-in at 1.5×, with the phone down at `DOWN` and the cut back to the two-shot at `CUT`.

The word captions sit at `WORDS_Y`, over the hood.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_exit_audio.py PROJECT --font FONT_DIR   # takes, bed, timeline.json
python3 episodes/the_exit.py PROJECT     # the-exit.scene.xml + SRT, 17.792 s
```

### An original Stick episode at a door: *Hold the Door* (R10)

[episodes/hold_the_door.py](../episodes/hold_the_door.py): Dev holds the door for a stranger far too far away, so the
stranger has to jog for it. Others overtake him, day turns to night, snow settles, a marathon passes. Years later the
stranger is three steps away when Dev's arm gives out.

The set is `srstudio.stick_door`:

- `stick-entrance`: the lobby and the street through its doorway, with a wall clock that runs and a street that
  darkens over the shot; `stick-street-lens` is the same street on a long lens, for close work on a runner.
- `stick-glass-door`: the pane on its hinge, held, swinging shut, or `closed`.
- `stick-snow-cap` and `stick-marathon`: snow in three sizes, and the silhouettes past the end of the street.
- `HOLD` and `JOG`: the poses of the arm that tires and of a run, with `shaking()` and `jogger()`; `on_path()`,
  `approach()` and `through()` put a figure on the path and behind the doorway.

`srstudio.stick_reel` holds what a recorded Stick reel repeats: `spec()`, the spoken `words()` and `close()`.

### An original Stick episode in a kitchen: *Take My Phone* (R11)

[episodes/take_my_phone.py](../episodes/take_my_phone.py): she hands her friend her phone and tells her not to let her
text him. Twenty seconds later she wants it back. The friend runs, sits on it, freezes it, locks it up and swallows
the key. She has already lifted the friend's own phone.

The set is `srstudio.stick_home`: `stick-kitchen` with its fridge and wall safe, `stick-table` drawn apart so figures
pass behind and in front of it, `stick-fridge-open` and `stick-safe-open` over the shut ones, `stick-handset` and
`stick-key` for the hands, `stick-reply-screen` for a message that takes the whole frame, and `POSES` for the argument.
The chase is `stick-kitchen-plan` and `stick-from-above`, straight down: two full figures crossing the frame again and
again fail the flash check, because each head's outline sweeps the same pixels more than three times a second.

### An original Stick episode at the coffee machine: *Good, You* (R12)

[episodes/good_you.py](../episodes/good_you.py): "How was your weekend?" "Good, you?" "Good." Every Monday, through a
cast, a neck brace, a parrot, a small fire and a headstone, and through the Friday a meteor lands outside the window.
Repeated lines are one recording, so the deadpan cannot drift.

The set is `srstudio.stick_office`: `stick-coffee-corner` with its window on the city, `stick-coffee-counter` in front
of the figures, and what the weeks leave: `stick-arm-cast`, `stick-neck-brace`, `stick-parrot`, `stick-flames` and
`stick-tombstone`, placed by `on_figure()`, with `stick-mug` and `stick-meteor` in the window's `view()`.

### An original Stick episode on the road: *The Stove* (R13)

[episodes/the_stove.py](../episodes/the_stove.py): Dev and Noor leave for the airport and turn back for the stove, for
the door, and for an iron they do not own. The sign says Airport 2. The neighbour ages, the tree grows, the children
grow up in the window, and in the last car she asks about the stove.

The car is `stick_windshield`, moving from the first frame. The rest is `srstudio.stick_street`: `stick-home-street`
with a tree that grows and a window (`in_window()`, `window_frame()`), `stick-side-car`, `stick-road-plan` and
`stick-top-car` for a U-turn from above with a skid mark for each one before it, `stick-stove-knob` and
`stick-door-lock` for what they came back to check, `stick-road-ahead` and `stick-road-sign`, and `stick-suitcases`.

## Toon style package: *Anonymous Employee Survey*

The sixth style recreates a the.nope.cat reel from a screen recording: a blue cartoon cat at a laptop answers an
"anonymous" employee survey out loud while each phrase appears in a white pill at the top of the frame.
[episodes/employee_survey_data.py](../episodes/employee_survey_data.py) is the reel as data: `SENTENCES` (what the
narrator records, one request each), `SEGMENTS` (every change of caption or expression at its reference time, each
spoken one naming the sentence and the word it starts on), `cues()` and `poses()` (which derive `script.json` and
`assets/poses.json` from the segments) and `place_segments()` (which moves the segments onto a narration).
[episodes/employee_survey.py](../episodes/employee_survey.py) draws it with the Toon parts: `toon.room` (a gradient
wall, the window, the chair back), `toon.cat` (one group per pose run holding a body traced from the recording for
the pose's arms, the eyes in one of nine kinds and the mouth in one of nine), `toon.desk` (the laptop lid and the
desk) and `toon.captions` (each cue in the style's font inside a pill measured with `fonts.text_width`). The cat's
drawings are packaged data (`assets/toon/cat.json`, schema `toon-cat/1.0.0`): a body per arm pose (`desk`, two
typing frames, `crossed`, `sigh`, `lean`, `face`, `face2`), eyes and mouths as closed cubic paths in the
reference's screen pixels, parsed by `toon.parse_art` (exact tables, finite coordinates, every expression present)
and mapped to the frame by `toon.fx`/`toon.fy`. While keys are heard the two typing bodies alternate
(`toon.typing_frames`, every `TYPE_SWAP` within a burst, back to the first frame between bursts), with opacity keys
on the composition clock (`toon.swap_frames`). The character, dialogue and captions are adapted from the reference
and remain their author's; the style, the loaders, the drawing conventions and the vocabulary (`EYES`, `MOUTHS`,
`ARMS`) are what the library keeps.

```bash
python3 episodes/employee_survey.py PROJECT --init    # script.json, assets/poses.json, Comic Neue Bold Italic pinned
python3 episodes/employee_survey.py PROJECT           # the silent master on the reference timing, 63.125 s
```

### Narrated master

[episodes/employee_survey_audio.py](../episodes/employee_survey_audio.py) records the 21 sentences through
`srstudio.voice` (premade voice *Brian*, typed parse, alignment check, speech-to-text that must hear the scripted
words, voice id confirmed by name) at the narrator's own pace, nothing quickened. Two sentences are interrupted by
the survey in the reference ("Do you have any feed—", "mark an X where you s—"): the whole sentence is recorded
and confirmed, then cut after the letter the reference cuts at, read from the character alignment. The lines are
placed by `srstudio.narration.plan_relaxed` on the reference's sentence starts, then the picture is moved to the
voice: a spoken segment starts where its word is heard, a silent beat (the sigh, the stare, the camera) a moment
after the line before it ends and no later than the next spoken segment, and a change that would cut a caption
short of 0.85 s waits for it, at most 0.45 s after its own word. `srstudio.foley` types only in the quiet windows of
the typing segments (`typing_bursts(speech=…)`, seeded bursts every 0.3 s, `SPEECH_MARGIN` clear of every placed
line, so no clack lands under a word) and the laptop's camera clicks on the flash; the keystroke onsets go into the
manifest and `toon.cat` swaps its typing frames on the same beats. The clips are
conformed to 48 kHz mono under `audio/`; `narration.json` lists them with their placement, the two effect beds, the
extended `duration` and SHA-256s; `voiced/script.json` and `voiced/poses.json` are the moved picture, and
`employee_survey.py --voice` builds from them after checking the hashes, with one dialogue track per clip, the
typing at −2 dB (peak-normalised to 0.70 before the gain) and the click at −3 dB, mastered by the style's mix. The cloud step needs `SRSTUDIO_ALLOW_CLOUD=1`
and `ELEVENLABS_API_KEY`; cached takes cost nothing.

```bash
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/employee_survey_audio.py PROJECT   # audio/, narration.json, voiced/
python3 episodes/employee_survey.py PROJECT --voice                        # the narrated master
scene-render encode PROJECT/employee-survey.scene.xml -o /abs/path/employee-survey.mp4   # h264 + aac, 63.6 s
```

### Toon coworkers: brush-drawn characters

[src/srstudio/brush.py](../src/srstudio/brush.py) is a hand-inked brush for characters drawn in code: `spline`
(Catmull-Rom through the points, open or closed), `stroke` (a band whose width follows a `Pressure` profile with a
swell and a slow wobble, round caps), `outline` (a closed fill) and `rim` (the fill pushed outward by the ink
weight, whichever way the points wind), `inked` (a rim pressed by a `Hand`: heavier where the outline turns from
the light, thin at sharp tips, uneven along the way in the shape of a `Wave`, with a dry brush's fine grit when the
hand is `ragged`),
`broken` (that band in seeded pieces with tapered gaps and nicks), `wobble` (a contour's small, repeatable hand
drift, with per-sample `weights`), `facing` (a contour's samples with their outward normals), `crescent` (a shade
swelling inside an edge), `lump` (a seeded one-off blob where an ellipse would look digital), `ellipse`, and
`shift`/`rotate`/`flip`/`bounds`. Every result is a closed cubic `Shape` the Toon parts fill flat
with `toon.flat`, so a figure is a stack of filled layers (ink rim, coat, markings, limbs, face) and never a stroked
path. [src/srstudio/toon_cast.py](../src/srstudio/toon_cast.py) draws two
coworkers for the cat's desk with the cat's vocabulary and contract: `toon-dog` (orange coat, drop ears, a light
muzzle and a black nose) and `toon-frog` (green, a pale belly, three spots, eyes on the bumps of its head, a wide
mouth). A `Look` holds the coat colours, the silhouette, the eye and mouth placement and the markings;
`figure_shapes(look, eyes, mouth, arms, frame)` returns the layers for one expression (every `EYES` × `MOUTHS` ×
`ARMS` is tested to stay inside the character's corner), and `dog`/`frog` take the same poses, duration and
keystrokes as `toon.cat`, plus `enter=` for a character that comes on later. Rex (the dog) and Fern (the frog) are
the cast of the first two sketches below.

Two more characters carry opt-in polish fields on their `Look` ([docs/decisions/0020-toon-lip-synced-cast.md](decisions/0020-toon-lip-synced-cast.md)):
`toon-bear` (brown coat, round ears lined in cream, a pale muzzle and belly) and `toon-rabbit` (pale coat, tall
ears lined in pink, front teeth and whiskers). Both have eyebrows that follow the eye kind (raised for a shock,
tilted down in a frown), a highlight on each pupil, blushing cheeks, and blinks at their own pace (`blink`
seconds, `blink_times`, a lid over each eye for `BLINK_HOLD`). The four brush-drawn characters take `mouths=`, a
viseme track of `(second, viseme)` with `VISEMES` closed, open, round and teeth. Within each pose run the mouth is
one layer per viseme heard, keyed on opacity on the composition clock (`viseme_keys`); "closed" shows the pose's
own mouth, so a character that is not speaking keeps its expression. `figure_layers` splits a figure into the
layers under the mouth, the mouth and the layers over it, so typing frames and stickers are drawn once per run.

Three more take the same contract ([docs/decisions/0041-toon-cast-expressions-and-wear.md](decisions/0041-toon-cast-expressions-and-wear.md)):
`toon-fox` (slender, tall splayed ears, white cheek tufts, dark paws), `toon-raccoon` (stout, a bandit mask,
rounded ears, cheek ruffs, dark gloves) and `toon-hedgehog` (small, a crest of spines drawn as the look's `mantle`).
The vocabulary also has eyes and mouths past the traced set: `roll`, `teary`, `wince` and `hearts` eyes, and
`grimace`, `frown`, `tongue` and `kiss` mouths. Every brush character draws them; the traced cat refuses them by
name (`toon.TRACED_EYES`, `TRACED_MOUTHS`). Any character, the cat included, can wear `toon.WEAR` per pose
(`"wear": ["glasses", "sweat", "flush"]` in a poses file, `wear=` on a sketch `Beat`), drawn by
[src/srstudio/toon_wear.py](../src/srstudio/toon_wear.py) about the character's face; on a head its drawing turns
(`toon_cast.Drawing.tilt`), the items turn with it.

Fox version 2, `toon-fox@2` ([src/srstudio/toon_inked.py](../src/srstudio/toon_inked.py),
[docs/decisions/0044-inked-toon-characters.md](decisions/0044-inked-toon-characters.md)), is the fox drawn
again the way the traced cat is drawn. Its outlines are placed by hand, unmirrored, and drift like a
hand following them (`brush.wobble`). Every ink band is pressed: heavier where the form turns from the light, thin
at the tips, with a dry brush's grit, and broken in three to five seeded places with a nick between
(`brush.broken`, a ragged `brush.Hand`). A few lumpy open strokes stay inside: the cheeks, the tail tip, a fluff in
each ear, the philtrum and the paw creases. Like the cat's, its body is one contour from the ruff into the
shoulders and flanks, and its arms leave the body inside the shoulder, slim there and widest at the forearm and
paw, inked only where they overlap the body or leave it. A darker coat tone shades the flank and the tail, and turns the head
with a crescent that starts and ends on the outline and swells into the cheek. The head tilts about the neck, the
face sits off its midline with the far eye smaller, and what it wears turns with the head. Its almond eyes with an
iris, its muzzle mouths and its visemes are drawn for its face: every `EYES` and `MOUTHS` kind is its own drawing,
and every eye a one-off of seeded lumps (`brush.lump`), never a perfect ellipse. A `Look` takes these through its `drawing` (a `toon_cast.Drawing`), so
the inked fox keeps the whole contract, and a sketch casts it as `"fox"`, at the version its release pins. Looks
without a drawing are drawn exactly as before.

### Part versions

Every registered part has numbered versions: characters, locations, props and graphics
([docs/decisions/0047-character-versions.md](decisions/0047-character-versions.md)), so a drawing can improve
without touching a published reel. `srstudio parts` lists them, a part's page in the catalog shows them, and
[src/srstudio/assets/parts.json](../src/srstudio/assets/parts.json) records each one: number, date, a note, a proof clip,
status, approval and the digest of its drawing
([src/srstudio/catalog_specimens.py](../src/srstudio/catalog_specimens.py)). A part that cannot stand alone, such as a
caption layer or a shot with a character in it, records a typed refusal instead of a digest, and
`srstudio parts --refused` lists those. A new reel gets the latest approved version, and a release pins what it draws:

```python
RELEASE = Release("a-new-reel", post, parts={"toon-fox": 2, "toon-bear": 1, "toon-desk": 1})
```

`srstudio build` leaves what it drew in the project's `parts.json`. `instagram_posts.py deliver` refuses a release with
no pins, a video with no such record and a build that drew anything its pins do not say, and `check` reports the
first and the last. A proposed version is never
the default and cannot be pinned. An approved drawing is never revised in place: a test redraws every one and fails
if its digest moves, so changing a look means adding a version. Only the operator approves a version. Only Toon's
characters read pins so far, through `toon_sketch.Staging.versions`, and the table refuses a second version of
anything else by name until its kind and style are in `parts.ROUTED`. A head rig is a second drawing, recorded on its
version with the same fields and rules, so changing an approved rig means adding a version of the character.

Version 2 of the dog, the frog, the bear, the rabbit, the raccoon and the hedgehog is the default for new reels
([docs/decisions/0052-older-cast-version-2.md](decisions/0052-older-cast-version-2.md),
[src/srstudio/toon_redrawn.py](../src/srstudio/toon_redrawn.py)): each keeps its colours and what it is known by, and
is drawn again with one smooth torso, pressed ink, a shade tone, a tilted head and its own pupils and paws. Published
reels pin version 1 and keep it.

A sloth, a goat and a hamster draw like the traced cat, in code
([docs/decisions/0045-toon-sloth-goat-hamster.md](decisions/0045-toon-sloth-goat-hamster.md),
[src/srstudio/toon_critters.py](../src/srstudio/toon_critters.py)): `toon-sloth` (olive, droopy, a pale face with dark
stripes down from the eyes, long ivory claws, a slow blink), `toon-goat` (lilac, wiry, swept horns, sideways ears, a
long muzzle and beard, bar pupils) and `toon-hamster` (pink, round, cheek pouches, a creamy belly, tiny paws held up).
Run `srstudio inspect character toon-sloth --json` (or either other name) for an executable pose recipe.
These builders accept `srstudio.toon.Pose` states using `EYES`, `MOUTHS` and `ARMS` names from that module.
The first pose starts at zero; pose starts are seconds relative to `enter`. `enter`, `duration` (the exit time),
`taps`, `mouths` and optional `LimbTrack` motion use project seconds. Builders return the pose groups.
Each is a `Critter`, a `toon_cast.Drawing` the look routes its foundation, face and limbs to: a dense hand-placed
outline with a pressed line (`pressed`, heavier at the bottom and back, thinning at sharp turns), open tapered fur
strokes, one shade tone along the edges away from the light (`shade`) and a head tilted about the neck. Each has
its own signature: the sloth's yawn, the goat's scream, the hamster's puffed pouches. Every brush character also
draws the new `sleepy` eyes (heavy lids, blinked slower: `SLEEPY_PACE`, `SLEEPY_HOLD`) and `yawn`, `scream` and
`puff` mouths (`shared_eye`, `shared_mouth`); the traced cat refuses them by name.

A critter's body and arms come from a `Torso`
([docs/decisions/0049-toon-torso-one-smooth-body.md](decisions/0049-toon-torso-one-smooth-body.md),
[src/srstudio/toon_torso.py](../src/srstudio/toon_torso.py)). `Torso(head, shoulder, slope, flank, arm)` builds one
smooth outline under a head contour: fixed-radius arcs from the neck over the shoulder and down the flank, so it
cannot make a corner. `Torso.weights` calms `brush.wobble` on that line. `Torso.limb(points, paw, coat, shade)` redraws
a pose's arm inside the body, a wedge from a thin crease at the top to full width at the forearm, its ink set low so
it reads heavier underneath, and leaves the paw to the character. `toon_torso.arm_lines` is the other way to ink an
arm, the inked fox's: only where it leaves the body or lies well over it.
Any `toon_cast.Drawing` can use it. The older brush cast still draws the shared `_limb` arms.

The sloth's, the goat's, the hamster's and the inked fox's heads can move on their own
([docs/decisions/0050-organic-head-motion.md](decisions/0050-organic-head-motion.md)). The redrawn six can too, from their
version 2 drawings ([docs/decisions/0059-older-cast-head-rigs.md](decisions/0059-older-cast-head-rigs.md)).
[src/srstudio/head_motion.py](../src/srstudio/head_motion.py) turns a `HeadStyle` and the `Speech` of a shot
(`speech_of(alignment, at, path)`) into a `HeadPlan` with `plan(style, speeches, duration)`: spring-keyed nods on the
accents of the line, a dip before a phrase, a two-octave idle, a breath tied to the pauses and glances, all
deterministic and bounded by `limit(style, name)`. Head plans keep the spring history and Catmull-Rom neighbors needed
to preserve motion across shot cuts. Long carried-spring channels are sampled into linear keys at at least 240 Hz
to preserve momentum while bounding renderer work; the sampler rejects channels exceeding its 100,000-key budget.
`limit()` describes the rig's allowed excursion, not a universal overshoot factor for every spring. `plan()`
checks every channel's response; `HeadPlan.check_bounds(style)` exposes the same check. Public Toon, Host, News,
and Rafa head entry points validate supplied plans before drawing or generating plates' face states. Gaze names
must exist in `head_motion.GAZES`, and gaze times must be finite and strictly increasing, including states outside
the current shot. Invalid gaze input raises `HeadMotionError` before scene mutation.

`channel.sample(project_second)` evaluates the emitted motion without drawing: hold, easing, spline and spring
semantics match the renderer, including emitted key precision. Empty channels sample as zero; times outside the
keys hold the nearest value. Sampling order does not matter. `channel.during(start, end)` retains the curve history
and spline neighbors needed for continuity across cuts. Rafa samples this same motion before selecting the nearest
plate and holding it on twos. Its valid `up` gaze maps explicitly to `ahead` because no upward plate exists; unknown
states are refused. See [ADR 0081](decisions/0081-shared-channel-sampling.md).
Linear, hold, and endpoint-bounded easing check their key values; Catmull-Rom, default TCB, back, and elastic
curves also check analytic extrema between keys. Unknown curve names raise `HeadMotionError`.
Short spring curves use sampled extrema plus a conservative
curvature allowance between samples; long channels use the extrema of their emitted linear keys. Validation
shares the sampler's work budget. A response outside the envelope raises `HeadMotionError` naming the channel
and bound. Reduce the excursion or adjust curve/timing; for springs, increasing damping can help. Tuning a curve
does not enlarge the approved rig. A bare `Channel(curve="spring")` uses the engine's default spring without
carried momentum; it is checked separately from explicit `Spring` channels.
For example, Goat's `Spring(2, 0.2)` settling response exceeds its face/turn envelope, while `Spring(0.8, 0.5)`
fits the same directed-turn example. `check_bounds(style, frozen=True)` checks only the initial pose emitted by
a frozen drawing, without sampling unused future spring history. Times must remain distinct on the six-decimal
scene clock. Immutable rig specimens use a separate, fixed probe generated from the rig's combined geometry
envelope; that probe folds several channels into turn/nod and is not a caller-supplied performance plan.
Generate plans with the destination rig's `style`: a plan prepared for a larger movement envelope can be
refused when applied to another character. Regenerate it with the destination style before drawing.
Explicit `facing=[(on, off, side)]` intervals take precedence over incidental glances: an idle glance is omitted
when its eye hold or head return overlaps a directed turn, including that turn's return to rest. This prevents
their head turns and face slides from adding beyond the style's intended bounds. Nonoverlapping glances retain
their original timing and seeded choices.
`toon_head.rest_springs()` is a lossy compatibility helper: it removes carried momentum and can visibly change
trajectories and velocity. New callers should use the automatic spring sampling in `toon_head.figure()` and
`Channel.during()`; preview scenes that intentionally retain spring resets.
[src/srstudio/toon_head.py](../src/srstudio/toon_head.py) draws a
`HeadRig` in nested groups with `toon_head.figure(cv, parent, rig, poses, duration, plan)`: the head turns about the
neck, and either the body's ruff or the chin hides the seam. [src/srstudio/toon_rigs.py](../src/srstudio/toon_rigs.py)
holds the rigs, and `rig_of` refuses a character with none by name. In a sketch, one line turns it on:
`Staging(..., heads=("sloth", "goat"))`. The build plans each named character from the takes in `voiced/speech.json`,
its own lines to speak and the others' to hear, and plays that plan a shot at a time. It is opt-in:
`toon_cast.figure` and the flat drawings draw as before. A `toon_torso` character gets a rig with
`toon_critters.Split` and `torso_rig`; `Split.open_chin` draws a head over the body with no line under its chin, for
a body that has no ruff or collar to hide the seam. Word stress comes from a table built by
[tools/build_stress.py](../tools/build_stress.py) from the CMU Pronouncing Dictionary
([licence](../src/srstudio/assets/stress/CMUDICT-LICENSE)).

`toon-bento` is the operator's capybara in a blazer, approved and not yet in any reel
([src/srstudio/toon_bento.py](../src/srstudio/toon_bento.py),
[docs/decisions/0062-bento.md](decisions/0062-bento.md)). He has 36 moods, 12 eye states and 9 gestures as typed data.
`toon_bento.pose_of(start, "skeptical", "folded", "left")` is one pose: a mood, with any gesture or shared arm and an eye
state over it. Pass such poses to `toon_head.figure` with `BENTO_RIG`. Each mood's tilt is held by the rig through
`HeadRig.pose_tilt`. A sketch's shared kinds draw on him as his nearest mood, and `parse_poses` admits only those. His
lip sync takes the same viseme track as the bear and the rabbit.
`srstudio inspect character toon-bento --json` includes an executable mood-change recipe and the timing
contract. Import `MOODS`, `EYE_STATES` and `GESTURES` from `srstudio.toon_bento` to discover names. The registered
builder holds mood tilts; use `toon_head.figure` for a moving head plan. Bento's named gestures supply his arms;
nonempty `limbs` replacement tracks are unsupported.

### Toon sketches: *The Report* (T3), *Logo Bigger* (T4) and *Quick Question* (T5)

The coworkers' episodes are short comedies written as data and cut between the two characters
([docs/decisions/0015-toon-sketches.md](../docs/decisions/0015-toon-sketches.md)).
[src/srstudio/sketch.py](../src/srstudio/sketch.py) defines a `Sketch`: its `Speaker`s (an ElevenLabs premade voice
each and the Toon character one plays, or none for a voice heard on a speaker), its `Line`s (one request each) and
its `Beat`s (every change of caption, on-screen character, expression or prop event at its scripted time, a spoken
beat naming the line and the word it starts on). `check` refuses an inconsistent sketch; `cues` (the caption script,
each cue carrying its line's speaker so `toon.captions(tints=)` colours the pill by who speaks), `appearances` (one
stretch of one character on screen, its poses counted from its entrance) and `events` (`"toast:0"`,
`"clock:09:05"`, `"logo:2.3"`, `"pop"`, `"hangup"`) are what the build draws. `record` says every line in its
speaker's voice through `srstudio.voice`, confirms each voice by name, hears each take back with speech-to-text
(the run stops on any misheard line), places the lines at the speakers' own pace and moves the beats onto the heard
words (`place`); the placed beats are written to `voiced/beats.json` and read back typed by `load_beats`. The
same run turns each take's character timestamps into its character's viseme track (`visemes`, sampled at
`VISEME_RATE` over the part of the take that was kept, joined in order by `extend_track`) and writes
`voiced/mouths.json`, read back typed by `load_mouths` (known characters, known visemes, rising seconds within the
project).

[src/srstudio/toon_props.py](../src/srstudio/toon_props.py) holds the sets and props the sketches play with, all in
the style's reference pixels: `toon-meeting` (a mint room with a whiteboard where the window was), `toon-mug`
(steam in the spans asked), `toon-clock` (hour and minute hands that jump to each `(second, "HH:MM")`),
`toon-notes` (up to four sticky notes lettered on the laptop lid), `toon-toast` (a phone notification that slides
in and shakes with the buzz; `gated=True` letters the card only once it has landed, so a camera push never leaves
its lettering wholly off frame, where the strict encode's contrast check fails it), `toon-board-text`, `toon-logo` (a sun that scales about its centre to each asked
size over 0.3 s, `scale_keys`, with a drop shadow through a span) and `toon-badge` (the call status under the
pill). `toon_cast.sticky_note` and the `stickers=` parameter of `dog`/`frog` stick a note on a character's forehead
that follows its sigh and lean. `foley.buzz` and `foley.tones` (`STING`, `CHIME`) are the phone and the sting, as
deterministic as the keyboard.

[srstudio.toon_sketch](../src/srstudio/toon_sketch.py) is the build the Toon sketches share: `build` draws one gated
group per appearance (set and props behind the character, the character on its poses, the desk, the props in
front), tints the pills, refuses a caption too wide for one pill (`fit_captions`), checks that `voiced/beats.json`
and `narration.json` agree, draws the mouths from `voiced/mouths.json` (refusing one whose end differs from the
beats'), and adds the voices and effects; `record_episode` is the ElevenLabs run plus the
keyboard between the lines, a buzz under every toast and the sting on the hangup. Each sketch is a data module
with its `SKETCH`, a `validate` for what its events ask of the props, and a `dress` for its shots:
[episodes/the_report_data.py](../episodes/the_report_data.py) (Fern asks where the report is; Rex has never heard of
it; his own reminders buzz in; the notes and the one on his forehead have been there from the first frame;
"...What report?") and [episodes/logo_bigger_data.py](../episodes/logo_bigger_data.py) (a client on speaker wants the
logo bigger until it is the size of the building, then popping, then smaller; the original pops; "Invoice sent.")
and [episodes/quick_question_data.py](../episodes/quick_question_data.py) (T5 *Quick Question*: Pip the rabbit has a
quick question for Bruno the bear; first some context, March, then Dave; his clock jumps from 9:02 to 9:48 and his
coffee goes cold; the question is when the stand-up is, and it is on the board behind her; "Oh. Quick
follow-up."). *Quick Question* records with `record_episode(mouth=)` set to the Toon reading plus the English
spelling, closed bilabials, lead and bridged joins of `srstudio.lipsync`.

```bash
python3 episodes/the_report.py PROJECT --init                                # script.json, assets/poses.json, Comic Neue pinned
python3 episodes/the_report.py PROJECT                                       # the silent master on the scripted timing
SRSTUDIO_ALLOW_CLOUD=1 python3 episodes/the_report_audio.py PROJECT          # the recording: audio/, voiced/, narration.json
python3 episodes/the_report.py PROJECT --voice                               # the narrated master
scene-render encode PROJECT/the-report.scene.xml -o /abs/path/the-report.mp4
```

`logo_bigger.py`, `logo_bigger_audio.py`, `quick_question.py`, `quick_question_audio.py`, `whose_milk.py`,
`whose_milk_audio.py`, `out_of_office.py`, `out_of_office_audio.py`, `date_night.py`, `date_night_audio.py`,
`in_network.py`, `in_network_audio.py`, `split_it.py` and `split_it_audio.py` take the same arguments.

*Whose Milk?* (T6, [episodes/whose_milk_data.py](../episodes/whose_milk_data.py)) is the first sketch in the office
kitchen. Fern (Matilda) and Rex (Charlie) argue over the milk in the fridge, labelled Rex, 2019. The note on the
fridge escalates through `note:` events (WHOSE MILK?, IT MOVED., WHOSE YOGURT?). Each new note is cut in full frame
with `toon_sets.note_insert` for its beat, and the last one holds to the end as the button. Rex's coffee brews
behind him in every one of his shots.

*Out of Office* (T7, [episodes/out_of_office_data.py](../episodes/out_of_office_data.py)) brings Pip (Alice) and Bruno
(Bill) back, and it is the first sketch in the home office at night. Bruno is on vacation, out-of-office on. He has
answered every email to say so, personally. The tear-off calendar behind him loses its pages on `page:` events, only
in his shots. His boss's reply and, as the button, his own auto-reply arrive as `toast:` events, drawn larger with
`toon_props.toasts(size=)`. The desk lamp lights his laptop, and the plant stands in front of its glow, right of his
paws.

*Date Night* (T8, [episodes/date_night_data.py](../episodes/date_night_data.py)) takes the Toon home: Mae (a
rabbit, Sarah) is in the kitchen and Otto (a bear, Daniel) in the home office next door, on a video call. He has
sent her a calendar invite for dinner. Its agenda, her status as optional and, as the button, a shared spreadsheet
of apartments arrive on her phone as `toast:` events, and the fridge carries the date. The tear-off calendar
behind him jumps from OCT 29 to JUN 30 on the `page:` event of the punchline, the month their lease ends.

*In Network* (T9, [episodes/in_network_data.py](../episodes/in_network_data.py)) is a phone call to an insurer. Gil (a
frog, Chris) is in the home office at night; Dana (a dog, Jessica) is in claims, in the new call-centre cubicle
(`toon_sets.call_centre`), and wears the new headset sticker (`toon_cast.headset`). Is a broken arm covered? Which
arm? They cover the right. The claims arrive on his phone as `toast:` events. Her CALLS WAITING board climbs on
`tick:` events, only in her shots, and jumps to 999 in the hold before her punchline: try again in January, fresh
deductible. After the sting, his calendar jumps to JAN 1 and the button is the callback toast, a new claim.

*Split It* (T10, [episodes/split_it_data.py](../episodes/split_it_data.py)) is the end of a dinner. Brock (a bear,
Roger) wants to split the bill evenly; Mia (a rabbit, River) had a side salad and water, he had three lobsters and
the wine. It is the first sketch in the new restaurant (`toon_dinner.restaurant`), and its staging swaps the office
desk for the dinner table with the new `Staging(desk=toon_dinner.table)` option (the default stays `toon.desk`).
Each side of the table is laid with `toon_dinner.dishes`, and the card reader (`toon_dinner.card_reader`) changes
screen on `reader:` events: DECLINED for him, APPROVED for her. Her payment, his transfer of $6.50 and, as the
punchline, what it is for (half her salad) arrive on her phone as `toast:` events; the button is his last toast,
"Same place Friday?".

Two more staging options serve the opening A/B test (a still first second against a moving one). A sketch may open
on a silent, uncaptioned beat and caption its first line later: the build checks the caption script against the
sketch's first cue, not against second 0, so a still opening holds the frame unchanged until the first word. And
`Staging(camera=)` moves each shot: it is called with the dressed `Shot` (its beats are the ones drawn, scripted or
voiced) and the shot's group (set, character, desk and props; the captions stay still), and the group is named
`shot-NNN` so `srstudio craft` counts its moves as camera. Without it, shots keep their anonymous ids and every earlier sketch
rebuilds byte-identical.

### Toon dinner: the restaurant, the table, the dishes and the card reader

`srstudio.toon_dinner` draws the restaurant set in the Toon line. `restaurant(cv, parent, special=(dish, price))`
is the wall with a seascape, a lit sconce, wainscot, a leather banquette and a chalk SPECIALS board.
`table(cv, parent)` is a tablecloth that takes the desk's place in a sketch and carries the signature marks.
`dishes(cv, parent, items, id=)` lays `(kind, x[, at])` items (salad, water, lobster, shells, wine, glass, empty,
check), each appearing at `at` when given. `card_reader(cv, parent, states, at=, id=)` shows one screen per
`(start, text, tone)` state, with tones `idle`, `bad` and `good`. Bad data raises `ToonDataError`.

### Toon sets: the office kitchen and the home office at night

[src/srstudio/toon_sets.py](../src/srstudio/toon_sets.py) adds two backdrops and four props, drawn more finely than
the first sets ([ADR 0022](../docs/decisions/0022-toon-kitchen-and-home-sets.md)). Objects are inked with the brush,
so their outlines swell and taper like the characters'. Surfaces carry light: a highlight on glass, steel and
glaze, a soft shadow under each object, and glows drawn as radial gradients. Everything is placed in reference
pixels and keyed on the composition clock. Looping motion runs from 0 to `end` (`cycle_keys`) and is left out when
`end` is 0, so a still frame is the same either way.

| Part | What it is | Motion |
|---|---|---|
| `toon-kitchen` | butter wall, mint cabinets, subway tiles with a glint each, a counter at `COUNTER_Y`, a tall fridge with magnets | a `note=` (1 to `NOTE_MAX` = 14 characters) on the fridge door |
| `toon-home` | dusk-violet wall, a night window with a cratered moon, the city skyline, a gathered curtain, string lights, a bookshelf | stars twinkle, bulbs pulse, lit windows go out and come back, until `end` |
| `toon-coffee-machine` | a drip machine on the counter: carafe, coffee, steel glint | in each `brewing` span: the light blinks, drops fall, steam sways |
| `toon-desk-lamp` | an angled teal lamp at the desk's right, its head over the laptop | its cone and pool of light show in the `lit` spans (`None`: always on) |
| `toon-plant` | a terracotta pot with five glossy leaves; `at` and `scale` | the leaves sway until `end` |
| `toon-calendar` | a tear-off wall calendar in the clock's place | at each `(second, "OCT 28")` in `pages` the page above tears, tips and falls |
| `toon-note-insert` | a full-frame close-up of the fridge note, lettered at 128 px so it reads on a phone | shown from `start` to `end` under a slow push |
| `toon-call-centre` | a cubicle: a pale office wall, a flecked fabric partition, a YOUR CALL MATTERS poster, a CALLS WAITING LED board in the window's place | one count at a time from `waiting` (`(second, count)`, from 0, up to `WAITING_MAX`); the board's lamp blinks until `end`; `legible=True` letters the label lighter (`LED_LABEL`) so it passes a strict encode's contrast check |

The signature marks stay on `toon.desk`, which is in front of every Toon shot. The new sets draw neither mark, and
the defaults of the lamp and the plant stand clear of the desk's cactus. *Whose Milk?* uses the kitchen, the coffee
machine and the note insert.

`toon_cast.headset(look, mic=True)` (`toon-headset`) fits a headset to any brush-drawn look from its silhouette: a
band just over the crown, ear cups at eye height and a boom to a mic beside the mouth. It is a list of layers, like
`toon_cast.sticky_note`, passed to the figure with `stickers=` so it leans and sighs with the character.

### Toon rooms: a living room at night and a service counter, lit over time

[src/srstudio/toon_rooms.py](../src/srstudio/toon_rooms.py) adds two backdrops whose light a sketch drives
([ADR 0043](../docs/decisions/0043-lit-toon-rooms.md)). Each room has a main light and a screen. A light runs through
cues `(second, state)` from 0. The states are:

- `on` and `off`;
- `flicker`, a stutter that repeats until the next cue;
- `dim`, a fade to `DIM` over `FADE` seconds.

A screen's cue may also name a colour from `SCREEN_COLOURS` (blue, white, red, green, amber, purple). The colour holds
until a cue changes it. Cues are plain data:

```python
toon_rooms.dress(shot, "lounge", {"lamp": [[0, "on"], [4.5, "flicker"]], "tv": [[0, "on", "blue"], [3, "on", "red"]]})
```

The light shows on the sources themselves, in the set behind the character. It also reaches the character: a sketch
built with `Staging(lit=True)` gets a light layer in every shot, between the character and the desk. In that layer, a
shade multiplies the frame darker as the main light goes down, and glows add each light's colour over the
character's side of the frame. The desk, with the signature on it, is drawn after the light layer, so no light state
changes it. Tests render each state and compare the signature's pixels.

| Part | What it is | Lights and motion |
|---|---|---|
| `toon-lounge` | deep teal striped wall, a shelf above the pill with a router and the library's smart speaker (`toon-speaker` at scale 0.5), a floor lamp at the left, a wall TV over a media console, a plum sofa behind the character | `lamp` (main) and `tv` (screen, default blue); the router's lights blink until `end`; the speaker's ring follows `speaker=` (`(second, state)`, default off) |
| `toon-counter` | mint wall and wainscot, ceiling tiles with two fluorescent fixtures, a TAKE A NUMBER sign with its dispenser, a NOW SERVING board, an orange plastic chair | `tubes` (main) and `board` (screen, default red); the board shows one ticket at a time from `serving=` (`(second, "A17")`, from 0) |

`toon_rooms.ROOMS` names each room's lights, its defaults and the boxes its objects keep clear of the figure, the pill
and the desk. `toon_rooms.stage(cv, back, light, name, lights, end)` draws a room outside a sketch.

### Toon everyday props: the phone, the speaker, the receipt, the queue and the form

[src/srstudio/toon_everyday.py](../src/srstudio/toon_everyday.py) adds five props for everyday tech, money and
services, job search and dating ([ADR 0042](../docs/decisions/0042-toon-everyday-props.md)). Each stands at `at`
(reference pixels) and `scale` (0.9 to 2.0; the speaker, which carries no lettering, from 0.5), takes states keyed from 0 in rising seconds, and returns its
footprint. A footprint that leaves the frame, enters the caption band or touches `SIGNATURE_BOX`, the desk's
signature marks, raises `ToonDataError`, as does text that does not fit its box in the style's font (`measure=`,
the sketch's `Shot.measure`).

| Part | What it is | Motion |
|---|---|---|
| `toon-phone` | a phone, held (`hand=`) or set down, with typed `Screen`s: `notify`, `code`, `profile`, `declined`, `loading`, `off` | one screen at a time; a notification buzzes the phone; the loading bar fills to `fill` |
| `toon-speaker` | a smart speaker with a light ring and a halo | `off`, `listen`, `think` (a light chasing round), `speak` (pulsing), `error` (red), until `end` |
| `toon-receipt` | a receipt strip under a printer slot: a header, `(name, price)` rows, a total | unrolls from `start` at `pace` seconds a row; each row shows as the paper passes it |
| `toon-take-a-number` | a ticket dispenser on a pole under a NOW SERVING display, the customer's `ticket` in it | the display changes at each `(second, number)` |
| `toon-clipboard` | a form on a clipboard: a title and up to five `Field(label, value, at)` rows | each value is written in at its second; a `(second, text, tone)` stamp lands with a pop |

No episode draws them yet, so the catalog's notes need no gallery item for them.

## Saga style: a space-opera parody in seven episodes (S1–S7)

The galaxy's grandeur is the setup; the turn is that it runs on the systems the viewer suffers at work, and a
deadpan field guide, the *Handbook*, gets the last word ([docs/decisions/0025-saga-style.md](../docs/decisions/0025-saga-style.md)).
Everything is original: no franchise names, characters, crawl or theme.

- **Cast**, [src/srstudio/saga.py](../src/srstudio/saga.py): Lord Gloom (a visor whose red glow is the mouth),
  Enforcer Seven and Gary (helmets with a mic light), Juno, Rook and Elder Mabel (visemes and blinks; Mabel has
  glasses and a cane), and a bar droid whose smile bar glows. Each figure is lit from the upper left: an inner
  shadow and a soft drop shadow (`saga.FORM`, `saga.LIFT`), drawn shadow sides, a gold rim and a contact shadow.
- **Sets and props**, [src/srstudio/saga_sets.py](../src/srstudio/saga_sets.py): space, bridge, cantina (with its bar
  as a front layer), desert, cockpit (with its console) and trash compactor; the hologram `holo`, the battle cube,
  a freighter, a fighter, a pebble; the hook card and the Handbook `entry`. Each location blurs its far plane by
  `DEPTH_BLUR` and keeps the floor, the cast and both signature marks sharp; `finish` grades a shot with `GRADE`.
- **Staging as data**, [src/srstudio/saga_reel.py](../src/srstudio/saga_reel.py): one `Stage` per recorded take
  (set, `Place`s, panels, props, a `Move`, blackouts, shakes, or an `Entry`). `check` refuses a staging that does
  not fit the recording before anything is drawn; `build` draws it, hooks the first take, crossfades into the
  entry, captions and mixes.

An episode is two files: `episodes/saga_<name>_audio.py` (its takes and stages; run it to record through
`srstudio.takes`, every line heard back by speech-to-text, no retries) and a three-line `episodes/saga_<name>.py`
that builds it. `tests/test_saga_episodes.py` holds all seven to the format: the narrator's hook question first, a
hold of at least 1.2 s before the button, the Handbook entry last, and a staging that fits at other speaking rates.

| # | Episode | The turn |
|---|---|---|
| S1 | *Known Issue* | the battle cube's fatal hole sat in the backlog for nine years |
| S2 | *Annual Review* | an enforcer who never hit anything is enforcer of the year |
| S3 | *Group Chat* | the big reveal was already in the family group chat |
| S4 | *Card Reader* | a smuggler meets the tip screen |
| S5 | *Update* | mid-chase, the jump drive installs an update |
| S6 | *Free Tier* | the energy that binds the galaxy, on the free plan |
| S7 | *Open Plan* | the compactor walls closing in are a workspace upgrade |

S13 *The Code* (the weapon's two-factor code went to the phone on the target planet) and S14 *Take-Home* (an
unpaid interview task is launched as the station that rejected her) use the opt-in switches of the ADR's
2026-10-30 amendment: a `still` opening shot that holds every frame of the first second, and `fade` panels and
entries whose text passes the strict encode. S15 *Call Juno* (the smart speaker calls the dark lord instead of
the granddaughter, and he gets mothered), S16 *Travel Notice* (the most feared man in the galaxy has his card frozen
over a coffee and washes dishes), S17 *Typing* (from the next seat, "we need to talk", then a typing indicator; it
is about snacks) and S18 *Friday Deploy* (one tiny fix at five on a Friday, and the only one who can roll it back
is on leave) use them too; S15's desert darkens under the captions with the second amendment's `shade` switch.

## Gloss style: a cheerful forever-plaza in nine episodes (G1–G9)

The relentless cheer is the setup; the turn is that it is a system you cannot leave, only rate, score and wait in,
narrated by a calm orb host in the deadpan of a facility announcement while a Joy Points board scores every small act
([docs/decisions/0030-gloss-style.md](../docs/decisions/0030-gloss-style.md)). Everything is original: the Plaza,
Sunny, the guests and the Joy Points are the library's own.

- **Cast**, [src/srstudio/gloss.py](../src/srstudio/gloss.py): glossy vinyl peg dolls Nadia (a NEW sticker that
  peels), Gus (a wind-up key that unwinds) and Tamsin (a spring base that bounces), and Sunny, a floating orb with
  a screen face that scans and wears a tie as the manager. Faces and poses are tracks on the shot's clock; the vinyl
  is rounded from each silhouette (`gloss.FORM`, `gloss.RIM`) with gradient highlights (`gloss.haze`) and seated by
  contact shadows. `gloss.LIFT`, a soft drop shadow, is applied only by `gloss.finish(..., lift=True)`, which no
  shipped part calls.
- **Sets and props**, [src/srstudio/gloss_sets.py](../src/srstudio/gloss_sets.py): the Plaza, the Activity Room and
  the Waiting Room (far planes softened by `DEPTH_BLUR`, lettering in strokes, a caption shade at the foot of the
  frame); the Joy Points `board` of `Card`s, the painted-on `door`, the queue `ticket`; the `hook` card and the
  Plaza `notice` that buttons each reel. `finish` grades a shot's world with `GRADE`; the board and the notice card
  stay ungraded and crisp. A `Card(carried=True)` stays on across a cut without popping again.
- **Staging as data**, [src/srstudio/gloss_reel.py](../src/srstudio/gloss_reel.py): one `Stage` per recorded take
  (set, `Place`s, cards, props, one camera `Move`, shake, blackout, or a `Notice`), checked against the takes before
  anything is drawn. The music ducks `DUCK` dB under every line and a further `HUSH` dB through every pause between
  lines (`hush`), so the hold before a punchline is quiet; the camera is the `gloss-<take>-angle` group, which
  `srstudio craft` reports.

An episode is two files: `episodes/gloss_<name>_audio.py` (its takes and stages; run it to record through
`srstudio.takes` via `episodes/_gloss.py`, every line heard back by speech-to-text, no retries) and a short
`episodes/gloss_<name>.py` that builds it. `tests/test_gloss_episodes.py` holds every reel to the format: Sunny's
hook question first, a hold of at least 1.2 s before the button, the Plaza notice last.

**A still opening.** A reel may open on a still first second (arm A of the `sp-hook_motion` test) with
`Reel(still=1.0)`. The recording (`takes.Script.still`) puts that much silence at the head of the first take, so the
first word comes after it and the timeline still runs contiguous from zero. The build then holds the first shot and
the hook on their first frame until then: it draws a copy of each inside `Canvas.frozen()`, where every key keeps
only its value at 0 s, and shows the running shot from the first word on. `gloss_reel.still_opening` refuses a
staging that would change the shot inside the still second (a card, move, blackout, shake, walk, face or pose
before the first word) and a notice as the first shot; a frozen drawing refuses expressions and text animators, which
it cannot hold still. Without `still`, recordings and builds are as before. Two other designs were rejected. A
timeline that starts its first take late breaks the contiguous-from-zero rule every take timeline keeps. An output
segment that freezes the first frame would make the encoded file a second longer than the scene whose clock the
captions, markers and craft checks read.

**Captions from G8 on.** G8 and later caption in `gloss_reel.LOOK_INK`: the lines wrap and hold as in
`gloss_reel.LOOK`, in solid dark letters (the sung word too) outlined thinly in their own color. The engine's contrast
check compares the pixels a caption changes most with the set behind them. A white letter in a dark outline lightens
some of those pixels and darkens the others, and on the light Gloss sets that averages to 1.00:1, so the strict encode
refused the house look (the published *Terms* fails it the same way under the current engine). A centered outline
passed but filled the white letters in, and a plum sung word measured under 3:1 on the notice's darker floor. G1–G7
keep the looks they shipped with. A reel that runs long can ask for its own encoder quality, `Reel(crf="20")`, over
the series output, to keep its master under the size cap; *Fewer Meetings* does.

| # | Episode | The turn |
|---|---|---|
| G1 | *Orientation* | the exit is painted on, and it arrives "in a future update" |
| G2 | *Joy Points* | points can be redeemed for more points, and the balance does not roll over |
| G3 | *Trust Exercise* | nobody catches anyone; catching was not in the budget |
| G4 | *Feedback* | the guests' complaint about the plaza is answered with more plaza |
| G5 | *Exit* | behind the exit door is a waiting room, and waiting is the attraction |
| G6 | *Wellness* | the manager is the same orb in a tie; wellbeing is the top priority, ranked fourth |
| G7 | *Terms* | declining the terms is added to the terms; real is also premium |
| G8 | *Fewer Meetings* | the meeting about fewer meetings schedules more; meetings are reduced to one, this one, and it does not end (opens still) |
| G9 | *Notifications* | saying no to notifications is a notification; turning them off is coming soon, and you will be notified |

## Collage style: grown-ups losing to brainrot

Paper cut-out people on painted sets give up their dignity to *BOWLHEADS*, an invented kids' show starring Flush,
a singing porcelain toilet. The style is decided in
[docs/decisions/0026-collage-style.md](../docs/decisions/0026-collage-style.md). The series bible (the world, the family at its centre and a card per character) is
[docs/decisions/0036-collage-series-bible.md](../docs/decisions/0036-collage-series-bible.md).

- **Cast and sets**, [src/srstudio/collage.py](../src/srstudio/collage.py) and
  [src/srstudio/collage_sets.py](../src/srstudio/collage_sets.py): ten characters as data (`collage.LOOKS`, drawn by
  `collage.DRAWERS`), twelve painted rooms (`collage_sets.SETS`), and the paper sign, chart and TV props.
- **The build**, [src/srstudio/collage_sketch.py](../src/srstudio/collage_sketch.py): a `Staging` per episode turns a
  sketch's beats into one shot per appearance, with crash zooms, the sting, Kai's beep, lip sync and tinted
  caption pills. `Staging.cast` decides who is drawn in a shot. `Staging.still` holds the first shot still for
  that many seconds (the `sp-hook_motion` test's still arm): no grain, and `Staging.opening` draws its cast keying
  nothing (`collage.figure(still=True)`). `Staging.bitrate` sets the master's average video bitrate, encoded in
  two passes (the rate factor alone, as published, by default).
- **Camera-safe zooms and call buttons**: `collage_sets.zoom_pivot` moves a zoom's pivot off a face only as far as
  keeps the set's whole signature in frame; `collage_sets.call_buttons` turns a shot into the far side of a video
  call.
- **Group shots**, [src/srstudio/collage_group.py](../src/srstudio/collage_group.py): `Lineup` puts several of the
  cast on one set, each in a fixed `Place`, the listeners holding their reactions while the speaker plays its
  beats; outside its spans it draws the speaker alone.
- **The family photo's props**, [src/srstudio/collage_photo.py](../src/srstudio/collage_photo.py): the self-timer
  on a stack of books, the viewfinder's countdown, the sofa front, the flash and the printed photo.
- **Everyday props**, [src/srstudio/collage_everyday.py](../src/srstudio/collage_everyday.py): food, a phone with a
  screen the scene writes on, message bubbles, a bedside clock, a cereal box, a duvet and a tablecloth, a salt
  shaker, chip bags and chips, a certificate, a snapshot, a gust of air, walking bills, confetti that can turn and
  fall back up, an arm on its own, a thumbs-up, and `chew`, which keeps a mouth working while a character eats.
- **A change of room and the extra sounds**: `Staging.setting` picks a shot's set from the beats (a reel that moves
  from the sofa to the bed), and rows can start on a later word of a line, `(line, word, caption)`. Beats also take
  `swat`, `ding`, `crunch` and `hiss:<seconds>`, written by `sound_effects` from `srstudio.foley`.

An episode is `episodes/<name>_data.py` (the lines, the timed beats and the `Staging`), `episodes/<name>.py`
(the build) and `episodes/<name>_audio.py` (the ElevenLabs recording, every line heard back by speech-to-text, no
retries). Its release is `episodes/posts/<name>.py`.

## Signature

Every episode built with this library carries two recurring marks that sign the work. They are a convention
decided on 2026-10-28 ([docs/decisions/0001-signature.md](../docs/decisions/0001-signature.md)) and implemented in
[src/srstudio/signature.py](../src/srstudio/signature.py). Episode 06 (`five-years`) is the first signed episode; the
seven shipped packages predate the convention and build with `signature=False`.

| Mark | What it is | Where it appears |
|---|---|---|
| **Code** `SR-1028` | A short diegetic code, in the style of Pixar's A113, drawn as stroked glyph paths (no font asset, so it never trips the legibility check) in the location's own colour | Office: on the top sheet of the desk papers. Café: the last line of the menu board. Park: the corner of the park sign. Doodle: the model plate under the printer's output tray |
| **Prop** `signature-cactus` | A small potted cactus, redrawn in the language of each palette (gradients in `OFFICE`/`CAFE`, pen stroke in `MONO`), about 6 % of the frame height | Office: the far corner of the desk. Café: the shelf. Park: beside the bench. Doodle: on the desk, between the laptop and the edge of the frame |

Rules:

- Both marks are drawn by the location builders through `srstudio.signature.code(cv, parent, x, y, height, color=…)`
  and `srstudio.signature.cactus(cv, parent, x, y, scale)`, never by episode scripts, so a new location adds one call
  per mark and an episode cannot forget them. Both return `None` and draw nothing on an unsigned canvas.
- `EpisodeSpec.signature` controls both and defaults to `True`. The seven shipped episode scripts pass
  `signature=False`, because their packages predate the convention and the fidelity tests reproduce them element for
  element; re-signing them is a new package version, not a rebuild.
- The code is `EpisodeSpec.signature_code` (default `SR-1028`); changing it is a project-wide decision, not a
  per-episode one. A character without a glyph (`A–Z`, `0–9`, `-`, `.`, space) raises `ValueError` at build time.
  The groups are ided `sig-code`, `sig-cactus` (then `-2`, `-3`… per location) so `tests/test_signature.py` asserts
  both are present in every location of a signed scene, absent when `signature=False`, and that the `MONO` variant
  adds no gradient paints.
- The marks never carry story information unless an episode opts in (next rule), never sit inside a caption's box or
  on a face, and stay inside the engine's safe area. They must not trigger the legibility check: the code is at
  least the `minTextSize` of the episode's `<accessibility>` or is drawn as paths.
- The cactus may perform ([ADR 0039](../docs/decisions/0039-the-signature-cactus-may-perform.md)). A
  `signature.Act(end, turn=, bloom=, code=)` turns its flower, pops it into bloom on a beat and writes the code
  inline on its pot (`signature.cactus(..., act=)`). `office_wide`, `office_desk`, `office_reverse`, `cafe` and
  `park` take a `cactus=` slot that replaces their own cactus at the same depth, through
  `signature.home_cactus`: on a signed canvas the slot must draw exactly one cactus, so a shot never loses or
  doubles the mark. Without `act=` or `cactus=` every drawing keeps its bytes, which `tests/test_signature.py` pins.

## Instagram captions

Every episode ships with an `ig.txt`: title, description, credit and hashtags, in that order, separated by blank
lines. The caption is data before it is text: `srstudio.social.InstagramPost` holds the four parts and refuses to
write when a limit is broken (title longer than the 125 characters the feed shows before folding, a malformed or
duplicate hashtag, a caption over 2200 characters, an empty title or description). The error is `InstagramPostError`,
with every problem listed.

The account is Okayville, handle @okayville.tv, and the brand is everyday life, animated, not office cartoons. A new
caption carries at most 5 hashtags (`social.HASHTAG_LIMIT`), Instagram's cap since 18 December 2025. The whole caption
counts, so a tag in the description is one of the five. The first delivery holds this
([ADR 0065](../docs/decisions/0065-okayville-and-five-hashtags.md)): `deliver` and `publish_pilots.py` refuse by slug
with `HashtagError` before anything is written. A published post keeps the 6 to 8 it went out with, so writing one
still passes up to `social.PUBLISHED_HASHTAG_LIMIT`, and `check` does not ask.

- Each shipped episode has a release, `episodes/posts/<slug with underscores>.py`, defining
  `RELEASE = srstudio.releases.Release(slug, post, video=, scene=, cover=, builder=)`
  ([ADR 0032](../docs/decisions/0032-releases-recorders-and-discovery.md)). `cover=True` says the cover is drawn from
  the scene's `cover` variant, and the gate refuses a release that disagrees with the built scene. A new release
  also sets `tags=srstudio.releases.Tags(territory, cause, emotion, recurring=, test=, arm=)`, from closed sets the
  account's analytics count ([ADR 0033](../docs/decisions/0033-episode-tags-for-analytics.md)); releases published
  before tags existed leave it `None`. A reel in a second A/B test adds `also=(("sp-speakers", "a"),)`, and a reel on
  the send test adds `send_to=` and `send_line=`
  ([ADR 0080](../docs/decisions/0080-a-brief-in-episode-json-and-giving-a-claim-back.md)).
  [episodes/instagram_posts.py](../episodes/instagram_posts.py) derives its `POSTS` map from the releases; each episode
  script calls `ep.instagram(POSTS[slug])` before `ep.finish()`, so a build leaves `ig.txt` next to the scene.
  Recreations credit the original author in the caption itself.
- Every post designs its **cover**: `InstagramPost(thumbnail=Thumbnail(headline, at, kicker, focus, zoom, place))`
  from [srstudio.thumbnail](../src/srstudio/thumbnail.py) (ADR 0013). The backdrop is the frame of the rendered video on
  screen at `at` (frame floor(t × fps), selected by index, not by seeking), magnified `zoom` times on `focus`; over it
  the engine draws a kicker pill and a one-to-three-line headline in Anton, white with an ink outline, its last line
  in the accent, on an ink band that is opaque outside the grid area. Everything that carries meaning stays inside
  the profile grid's centred 3:4 window (`grid_box`): the headline takes the largest size from 200 px down to
  110 px whose widest line fits and whose block takes at most 38 % of that window, and is refused
  (`ThumbnailError`) when none does. `srstudio.social.take_frame` refuses (`CoverError`) a time after the last
  frame and a blank frame (a fade or a black cut). `post.deliver(folder, video, font=, engine=)` writes `cover.jpg`
  and then `ig.txt`; a post without a thumbnail is an `InstagramPostError`, and on any failure nothing is written.
- **Publish gate.** `python3 episodes/instagram_posts.py deliver <out> <renders> --fonts <dir>` delivers every video
  that drifted (one `<out>/<video name>/` folder with `ig.txt` and `cover.jpg` per `<renders>/<video name>.mp4`) and
  records `<out>/delivery.json` (version 1.1.0): per video, the SHA-256 of its render, of its post fingerprint and
  of the two files written. The post fingerprint is the cover's drawing, not the source of the code that draws it
  ([ADR 0037](../docs/decisions/0037-the-cover-fingerprint-is-the-drawing.md)): the caption, the thumbnail spec, the
  headline font, the document `compose` lays out at the video's own size (read from the MP4 index) and the named
  render steps (`thumbnail.ENGINE_ARGS`, `thumbnail.ENCODER_ARGS`, `social.BACKDROP_ARGS`, `social.FRAME_SLACK`,
  `social.COVER_VARIANT`), so a refactor of `thumbnail.py` that draws the same covers drifts nothing. `check` writes
  nothing, runs no engine, ffmpeg or ffprobe, lists every drift and exits 1: a video re-rendered after its cover was
  made, a changed post, thumbnail or drawing, a cover that can no longer be laid out, an `ig.txt` or `cover.jpg`
  edited or missing, a post without a render, a video delivered but no longer published. A 1.0.0 manifest is
  refused by name; `instagram_posts.py migrate <out> <renders> --fonts <dir> [--dry-run]` moves it to 1.1.0 once,
  rewriting only the entries that provably hold the 1.0.0 fingerprint of the post they have now, under the
  delivery lock; it draws and delivers nothing.
  Every render must exist before `deliver` writes anything; current videos are left untouched. `--only <video name>`
  (repeatable) delivers the named videos alone, needing only their renders, while another post waits for its render;
  the other manifest entries are kept as they were, so `check` still reports their drift. A release declared
  `frozen=<fingerprint>` ([ADR 0040](../docs/decisions/0040-frozen-releases-at-an-accepted-drawing.md)) is a published
  video whose post now draws another cover: the gate takes it as current at that one drawing (every other check
  still holds), `deliver` leaves it as published, and `check` lists it. Only the operator freezes a release.
  The font is installed
  into `--fonts` and pinned there (`generated/fonts`); the deliveries live in `generated/renders/ig/`. With
  `SRSTUDIO_RENDERS` and `SRSTUDIO_FONTS` set, the test suite runs `check` against the real delivery, so a
  re-render without a new delivery fails the quality gate.
- **Doubled captions.** `deliver` refuses a video being delivered when two caption layers at one height overlap, so
  no frame shows two lines stacked on one band (`craft.doubled_captions`, `releases.doubled_captions`). Videos already
  published are not read: they are frozen. `Episode.spoken_captions(tail=, lead=)` times each caption to its phrase
  and cuts it where the next phrase starts, so lines spoken close together never share the band.
- **Outbox and packages** ([ADR 0024](../docs/decisions/0024-every-video-ships-its-package.md)).
  `python3 episodes/publish_drive.py` stages every video that passes the gate in `generated/outbox/<video name>/`
  (video, `ig.txt`, `cover.jpg` and its `.vpkg.zip`) and copies it to Drive (`--stage-only`, `--dry-run`). A video
  without a package is held back like a drifted one. A video whose release is in an A/B test
  (`releases.Tags(test=, arm=)`) is staged with an `ab.json` (`{"test": ..., "arm": ...}`) that the posting job
  reads, hashed in `outbox.json` like every staged file. A second test goes beside them as `"also": [{"test": ...,
  "arm": ...}]`, from `Tags(also=)`. The recipient test rides in the same file: `recipient=` is
  its arm, and arm `b` adds `to=`, who the viewer sends it to, from `releases.RECIPIENTS`. A recreation ships the package it was received with
  (`videos-styles/`); an original episode is packed by `srstudio.package` from `generated/episodes/<slug>/` into
  `generated/vpkg/` with `scenerender-vpkg`, unpacked and checked against its SHA-256s, and its scene validated by
  the engine. Each call builds and verifies a candidate, comparing its resolved files and metadata with the latest
  release. Changed assets, supporting files or metadata produce the next patch version; unchanged content keeps
  the existing archive. The tests cover each limit's failure path, the episode hook, every shipped post (each
  with a thumbnail and one video), the frame selection on a synthetic video whose frames differ (first, middle and
  last frame), frames outside the video, blank frames, unreadable probes, deliveries that leave no files when the
  backdrop or the engine fails, and the gate: a fresh delivery, never delivered, a re-render (and that only it is
  redelivered), a changed post, edited and missing files, a dropped video, every untrustworthy manifest and a
  missing render. `tests/test_thumbnail.py` covers every refused spec, the grid window, the layout inside it at
  both places and both frame shapes, the size and height refusals, the composed scene, and the engine render with
  its failure path.
- **Pilots** ([ADR 0054](../docs/decisions/0054-pilots-have-their-own-road-to-drive.md)). A pilot for a future channel is
  not published and must never reach Okayville, so it has its own road: `python3 episodes/publish_pilots.py FOLDER`
  (`--series`, `--stage-only`, `--dry-run`). `FOLDER` holds one folder per slug with `<slug>.mp4`, `cover.jpg`, `ig.txt`,
  `sources.md`, `notes.md` and a package, `vpkg.zip` or `<slug>-<version>.vpkg.zip`, delivered as `vpkg.zip`. It stages
  `generated/pilots/<series>/` (folders 700, files 600; `mind` by default, or `maps` or `news`) with `manifest.json`
  beside the folders, shaped like `outbox.json`, and uploads to `gdrive:srstudio/pilots/<series>` with `outbox.push`:
  `rclone copy`, then `rclone check`, never a delete.
  It refuses a missing or empty file, blank `sources.md` or `notes.md`, a slug that is not one plain name, a slug
  Okayville has used (release slugs, video names, folders in `generated/renders/ig`), any staging folder but
  `generated/pilots/<series>`, any remote outside `gdrive:srstudio/pilots/<series>`, and a new News pilot short of the
  comedy floor ([ADR 0064](../docs/decisions/0064-comedy-floor.md)): `comedy-author` and `comedy-reviewer` in the frontmatter of
  its `notes.md`, the lower at 14 or above. The remote is judged after normalising, and rclone is given the normal form,
  so `pilots/../ready-to-publish` is refused. No systemd unit watches the staging folder and none runs this tool.
  `FOLDER` is the whole set: staging replaces the last stage.

### The Okayville show signature

A reel in the show's look carries one cover and one corner bug ([ADR 0074](decisions/0074-okayville-show-signature.md)).
The cover is a `srstudio.thumbnail.ShowCover`: a solid band with OKAYVILLE, `#N` and the premise in at most 5 words,
over the reel's own art. The bug is the part `show-bug`, which `srstudio build` draws above the camera for a release on
that cover and for no other. Numbers come from `srstudio number`: `base` sets the publishing side's count once, `claim`
takes the next one before the final build, `list` prints the ledger at `generated/okayville/numbers.json`. A series has
its own count with `--series`, and `outbox` writes `episode.json` beside the video, exactly `{"number": N, "series":
"saga" or "", "series_number": n}`, with 0 outside a series (`show_numbers.EpisodeDocument`). `srstudio.show_gate`
refuses a first delivery out of the look. `srstudio number claim <slug> --brief send-v1` records the brief a reel was
made to, and `episode.json` then carries `"brief"` too; a reel without one keeps the three fields. `srstudio number
release <slug>` gives back a claim on a reel never delivered ([ADR 0080](decisions/0080-a-brief-in-episode-json-and-giving-a-claim-back.md)).

### Strict findings at first delivery

`srstudio.strict_gate` reads a new reel's `qa/render-report.json` at first delivery
([ADR 0078](decisions/0078-strict-findings-at-first-delivery.md)). A `--strict` finding refuses the reel unless
`episodes/strict/<slug>.json` proves it false on the master's own frames, signed off by a reviewer who is not the
author. `srstudio strict` lists the reels shipped that way, with their numbers and frames, and how many of the delivered
reels that is.

## Verification

- `tests/test_build.py` builds an office and a café episode from a synthetic project and asserts the SDK, the XSD and
  the Schematron report nothing; it also asserts `finish()` refuses a document with findings.
- `tests/test_ink_layout.py` does the same for the square Ink style from a synthetic `timeline.json`, and for *The
  Router*: the LED chase and voice marks, the power states, the blackout, the hand's three actions, the shelf shots
  with their signature marks, and a ten-take build through `router_scene`; `tests/test_the_router.py` covers the
  audio step's checks (script shape, word and phone timings against the trim, the schedule, the conform to the
  sample, the voice-name check) with mismatched, cut and malformed inputs.
- `tests/test_styles.py` asserts what each style decides, that an explicit field wins, that a foreign palette is
  refused, that a silent style needs no mouth model, and that the registry and the CLI know the style of every part.
- `tests/test_cel.py` covers the Cel style (silent, font-less, one id counter), the caption-script timeline, every
  loader with malformed camera, run, drawing and caption files, the room camera compensation, the drawing
  conventions (even-odd paths, radius-less rects, five-decimal keys held to the end) and a silent build with no
  `<assets>` that the SDK and the engine validate, the tracked-point loader with bad samples and the pressed
  keyboard (subpath split by nesting depth so holes travel with their shape, press keys on the composition clock, a
  plain drawing when nothing is struck, errors for relative paths, bad boxes and an empty box).
  `tests/test_narration.py` covers the narration step's slots, bounded speed-up, placement rules (lead, tempo,
  cut), look-ahead plan, the relaxed plan (natural pace, spill, bounded lag, montage cut, extended duration),
  tempo conform and the manifest check (items, optional `lag`, `effects`, `duration`) with malformed, tampered
  and missing inputs; `tests/test_mushroom_training_audio.py` pins the script to the library steps, the natural
  speed and the respellings; `tests/test_foley.py` covers the keystroke bed (bursts from motion, determinism,
  peak, bounds, the written file).
- `tests/test_stick.py` covers the Stick style value, every loader with malformed poses (wrong shot, unknown and
  missing fields, gaps, bad points, colours and paths, a changing number of dancers), icons, lettering and scripts,
  the drawing conventions (even-odd paths stroked only with a width, rects that always carry a radius, user-space
  gradients defined once), the seeded fence, one group per pose with a badge per dancer, and the outlined captions;
  the rig's pose and head keys, its mouth and closed faces, refused performances, every pose and face, looks
  (every hair, glasses, ties, refused looks), standing, placed and mirrored figures, the camera, the hook card and
  the box its three lines fit, the call screen (inbox, tiles, speaker ring, marked row, refused calls) and the
  caption outline modes; `tests/test_screen_share.py` checks the *Screen Share* script and refuses malformed lines;
  `tests/test_fidelity.py` rebuilds the package's 3 470 elements and its SRT.
- `tests/test_toon.py` covers the Toon style value, the pose and script parsers with every malformed input (unknown
  expressions, out-of-order times, overlapping cues, empty captions, unreadable files), the traced art's parser
  (wrong schema, missing tables, bad shapes, a missing or broken package file), the reference-pixel mapping, the
  room and desk colours and gradient, one group per pose run with every eye, mouth and arm kind drawn, the typing
  frames and their swap keys on the composition clock, the measured caption pills and a canvas without a font;
  `tests/test_brush.py` covers the brush (splines through their points, stroke bands and caps, outline and rim,
  the transforms, refused measures); `tests/test_toon_cast.py` draws every expression of the dog and the frog
  inside their corner, the two typing frames, refused expressions, the groups and swaps, a later entrance and the
  registry entries;
  `tests/test_toon_cast_more.py`, `tests/test_toon_expressions.py` and `tests/test_toon_wear.py` cover the fox,
  the raccoon and the hedgehog (thumbnail heads, coats, builds), the new expressions with the cat's refusal, and the
  wear on every character and through a sketch;
  `tests/test_sketch.py` covers the sketch (checks and every refused inconsistency, cues with speakers,
  appearances, events, line spans, typing bursts, the placement onto a recording, the drawn cast with stickers, the
  written and reloaded files, a recording through a fake client with its manifest, and a misheard line);
  `tests/test_toon_props.py` draws every prop with its keys and refuses bad data; `tests/test_toon_sketches.py`
  covers the two sketches (a question hook, both coworkers, the hold before the punchline, the sting, refused
  events, the dressing of each shot, the badge spans, the recording run's effects and manifest, a voiced project
  whose files disagree, captions too wide for a pill);
  `tests/test_employee_survey.py` covers the reel's data (consistency, every refused inconsistency, cue and pose
  derivation, sentence spans, typing bursts), the placement onto a narration (words, silent beats, the crowded
  beat, the minimum caption hold and its cap, refused takes), the written files and the narration script's
  constants and alignment cut; `tests/test_fonts.py` covers `fonts.text_width` on a real TrueType file.
- `tests/test_signature.py` asserts the two [Signature](#signature) marks are in every location of a signed office
  episode, absent from an unsigned one, typed on a code without glyphs, and gradient-free in the `MONO` palette.
- `tests/test_layout.py` covers safe-area validation, exact path bounds for every SVG command, the overlay check
  against the engine (inside, crossing, hidden, rotated, instanced) and every malformed-input path; `tests/test_symbols.py`
  asserts instanced office angles draw each shape with the same world transform as the inline drawing.
- `tests/test_soft.py` covers the Soft style and palette, top captions, stroke outlines, interpolation and placement,
  the pose sheet, the two-pass silhouette, in-between drawings, rotation-preserving turns, arcs, planted feet,
  overshoot and settle, the cheer, wave and seated-nod poses, that no front arm covers the face in any pose or in-between, every refused cue, the sung
  mouth track, the keyed rig and contact shadow and, on the engine, that exactly one eyes and one mouth of Pip are
  visible at each frame, the seated legs reading as two, the looks (Bo's ids, fills and hairline, Juno's and
  Remy's shade, the shade crescent's geometry, lashes on every eye and catch-lights only on pupils, Pip and Bo
  drawing no polish, the whole cast in one scene without an id clash) and the soft home (the hip on the cushion, the soles and the sofa's front on one floor,
  the lounging hands on the lap, a seated character between the seat and the near arm);
  `tests/test_audio.py` asserts `ep.audio()` builds each source's mix exactly as the explicit calls do, the style's
  master levels, verified narration cues (a tampered clip is refused) and the refused options;
  `tests/test_music.py` covers the beat grid, deterministic and peak-levelled rendering, silent rests, beat-exact
  kicks and every refused setting; `tests/test_fonts.py` covers the request, every refused stylesheet, the font-file
  reader on damaged files, install with offline reuse, a tampered pin, wrong family or weight (nothing written),
  licence fallback, the size limit and the CLI, against a fake fetcher with a real TrueType file.
- Quality gates (`pyproject.toml`): `ruff format --check`, `ruff check`, `mypy src`, and branch coverage of at least 80 %.
  The publish gate runs inside the suite when `SRSTUDIO_RENDERS=/path/to/generated/renders` and
  `SRSTUDIO_FONTS=/path/to/generated/fonts` are set (see Instagram captions).
- `tests/test_fidelity.py` rebuilds the seven shipped episodes from their extracted packages
  (`SRSTUDIO_PACKAGES=/path/to/extracted` with `<name>-<version>/project` inside) and compares them with the shipped
  `.scene.xml` using [tools/compare_scene.py](../tools/compare_scene.py): every element, attribute and text in document
  order, numbers rounded to five decimals, `metadata` ignored, `animate`/`expression` children compared after their
  sibling shapes (the engine evaluates them by property, so their position among shapes does not change the picture).

Rendering needs the scene-render engine (`scene-render encode <slug>.scene.xml`); it is not part of this package.
