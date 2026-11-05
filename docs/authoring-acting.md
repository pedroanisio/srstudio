---
updated-by: OpenAI Codex (GPT-6)
---

# Coordinate performances and preserve cuts

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Compile one source performance, then place its windows into shots. The executable recipes below include their imports, explicit clocks, capability checks and refusal paths. For the `Canvas`, parent and placement bindings, use the [clip recipe](authoring-clips.md#character-clips-one-placement-and-timing-boundary).

Run commands from the srstudio repository root.

## JSON score schemas for agents

Discover data formats with `srstudio schema --json`. Export an exact version with
`srstudio schema acting --version 1.2.0 --json`, or call
`srstudio.document_schemas.get('acting', version='1.2.0')` in Python. These commands also work
from an installed package outside the repository. Omitting the version selects the latest supported
one; pin the version in reproducible agent workflows.

The self-contained JSON Schema 2020-12 document describes the JSON accepted by `parse_score`,
including closed objects, array limits, nested speech alignment and version-specific fields.
Version 1.0.0 excludes transition policies and blends; 1.1.0 adds policies; 1.2.0 adds blends.
This document schema is separate from `contracts.describe_callable(parse_score)`, which describes
the Python function's arguments and runtime overrides.

Validate structure, then call `parse_score`, then `compile_performance` with a selected rig.
JSON Schema cannot enforce equal-length alignment arrays, cross-field time ordering or rig vocabulary.
The parser also requires finite values and actual Python `int` values for `seed` and `sample_rate`:
JSON Schema's mathematical integer accepts `1.0`, but that Python float is rejected by the parser.
The schema records these remaining obligations in `x-runtime-constraints`; `x-validation` remains
`runtime-required`. Runtime `HeadPlan` and `LimbTrack` overrides are supplied separately, never encoded
as arbitrary objects in a generated score.

## External arms on a candidate Toon figure

Use `ToonClip.external_arms` when a scene draws a spatial arm outside the native
split-head figure. The native drawer and its anatomy ledger both omit that side.
The tuple accepts distinct `left` and `right` entries. Nonempty delegation
requires a candidate rig with `drawn_as=None` and separable shared poses
(`desk`, `lean`, `type`, `crossed`, `sigh`, `face`, `face2`).
An indivisible drawing-specific gesture is refused before mutation.

```python
from dataclasses import replace
from sr_core.scene import Scene
from srstudio import Canvas
from srstudio.character_clips import Interval, ToonClip, place_character
from srstudio.toon import Pose
from srstudio.toon_bento import BENTO_RIG_2

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=2)
canvas = Canvas(scene, font_asset=None)
clip = ToonClip(
    replace(BENTO_RIG_2, drawn_as=None),
    (Pose(0, eyes="neutral", mouth="neutral", arms="desk"),),
    external_arms=("right",),
)
place_character(canvas, canvas.comp, clip, interval=Interval(0, 2), id="carrier")
assert {hand.side.name.lower() for hand in canvas.limbs.values()} == {"left"}
assert scene.check(schema=True) == []
```

This builds the native component. The scene must supply the external arm and
verify its shoulder registration, prop contact, painter order and complete
motion. It does not grant drawing approval or make `LimbTrack` a supported
input to the split-head adapter. Direct `toon_head.figure` accepts the same
keyword; omission defaults to an empty tuple and retains existing output.
See [ADR 0211](decisions/0211-explicit-external-toon-arms.md).

## Coordinated acting and continuity

`srstudio.acting` compiles a bounded score once, then places windows of that same
performance into shots. `BENTO` and `gloss_actor("nadia")` expose explicit artistic
emotion mappings through `describe()`; inspect capabilities before generating intent.
The descriptor's `vocabulary` lists valid `eyes`, expression `mouths`, `gestures`,
named `gaze` and speech `visemes`. Empty lists indicate unsupported controls:
Gloss expressions have no independent mouth field, and Sunny has no arm gestures.
`channels` gives each numeric control's input path, minimum, maximum and unit.
Head rotations use degrees; `nod`, `face_x` and `idle_y` use the rig's reference
pixels; breath is normalized 0–1. Bounds come from the selected rig's style;
combined motion and transitions still undergo runtime validation.
These names describe the author's intent, not a measured emotion or a universal
biomechanical model. Gloss supports its existing face, mouth, gesture and guest limb
controls; directed head motion, gaze and listening require a capable Toon head rig.

`PerformancePlan.sample(t)` and window samples use the same limb interval as
character drawing. A track's `BakeOptions.offset` holds its initial pose before
the offset; `duration` crops its source and holds that terminal pose, contact
state and prop frames through the performance end. Within that interval samples
are continuous source poses; the drawing holds poses at the configured frame rate.

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
limb contact or prop attachment fails until its explicit release. Reset checks,
including transition-policy phases, use the same offset, crop and terminal hold as
sampling: cropping before acquisition removes the conflict, while cropping during
an active contact or attachment holds it through the performance end. A release
exactly at the crop boundary remains released. Spatial limb samples
describe the source motion; baked rendering still uses the selected limb frame rate.

Run the two-family silent study with licensed font assets and a JSON state report:

```sh
python examples/acting_gallery.py ../generated/sdk-acting
scene-render validate ../generated/sdk-acting/acting-gallery.scene.xml --deny-warnings
scene-render encode ../generated/sdk-acting/acting-gallery.scene.xml --strict
```

### Opt-in target gaze

`srstudio.gaze` compiles a target track with separate eye and head latency and
angular limits. Check `rig.describe()["capabilities"]["target_gaze"]` before binding
it. Critter and Inked split-head drawings declare moving pupil layers; unsupported
drawings raise `GazeError` rather than substituting a named direction.

```python
from srstudio import acting, gaze, toon_critters

rig = acting.ActingRig(
    "sloth-tracking", "toon",
    (acting.Emotion("neutral", acting.Expression("wide", "flat"), "desk"),),
    head_rig=toon_critters.SLOTH_RIG,
)
target = gaze.GazePlan(gaze.parse_gaze({
    "duration": 1,
    "target": {"keys": [
        {"time": 0, "point": [0, 0, 2]},
        {"time": 0.5, "point": [0.6, 0.2, 2]},
    ]},
    "limits": {"eye_latency": 0.03, "head_latency": 0.15},
}))
base = acting.compile_performance(
    rig, acting.ActingScore(1, overrides=acting.Overrides(gaze=()), idle=False)
)
plan = base.with_target_gaze(target)
assert plan.window(0.3, 1).sample(0.4) == plan.sample(0.7)
```

Coordinates use one fixed observer frame: X right, Y down, Z forward, with common
caller-selected units. An optional `observer` track supplies translation; resolve
rotating frames before passing coordinates. `parse_gaze` rejects unknown fields and
primitive coercions. Plans reject sampled targets behind the observer and limit
excursions, with at most 1,000 keys per track and 20,000 planned samples. Compilation
samples target easing and emits linear angle interpolation; it does not guarantee
velocity continuity or exact tracking between source samples.

Binding preserves the full performance clock and adds stylized `face_x`/`nod` head
follow inside the rig's envelope. It moves declared pupils while retaining lids and
painter order; closed eyes remain closed. This is an authored 2D mapping, not a
biomechanical model or a world-space line-of-sight constraint. Neutral named holds
may be replaced; authored look-away states conflict. `Overrides(gaze=())` suppresses
procedural named glances. Rebinding replaces the previous target. Direct callers can
pass `target_gaze=target` to `ToonClip` or `toon_head.figure`.

For a rig supporting only named directions, call `gaze.named_gaze(plan,
gaze.NamedGazeMapping(states, max_error))` explicitly. Supply states supported by the
destination rig and an error allowance in eye radii. This returns held **eye** keys
only, each half a frame (of the plan's `fps`) before the frame that first shows it
([ADR 0216](decisions/0216-held-keys-at-frame-centres.md)); it does not transfer head follow. `toon_head.gaze_capabilities(rig)` describes
the drawing mapping and emission budget. Existing drawing paths are unchanged when
no target is supplied.

The [two-style target-gaze study](../examples/target_gaze.py) renders the same target
on Critter Sloth and Inked Fox, with cuts during target motion and a later expression
change. It exports the exact target JSON, sampled states, capabilities and source
hashes. Its cut and uncut builds use identical framing for pixel comparisons.

```sh
python examples/target_gaze.py ../generated/sdk-target-gaze-study
scene-render validate ../generated/sdk-target-gaze-study/target-gaze.scene.xml --deny-warnings
scene-render encode ../generated/sdk-target-gaze-study/target-gaze.scene.xml --strict
```

See the [target-gaze design decision](decisions/0108-source-clock-target-gaze.md) for
the limits of the pupil-layer contract and named-state approximation.

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
`rig.describe()["transitions"]` exposes these limits for both legacy transitions and opt-in policies,
including held drawing switches and source-time-preserving cuts. For spatial tracks and joins, use
[`describe_continuity()`](catalog/limbs.md#inspect-continuity-before-choosing-a-transition); its source
guarantees do not transfer to the native or baked limb compiler's held frames.

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

## Authored emotional blends

Score `srstudio.acting/1.2.0` adds `blend: true` to a beat. Inspect
`rig.describe()["transitions"]["authored_faces"]` before choosing a transition;
unsupported pairs fail during compilation. The default `BENTO` profile retains
discrete expression replacement. `bento_blends()` is an opt-in candidate supporting
all directed pairs between neutral, deadpan and concerned. It uses version-2 hands
and carries no approved drawing identity.

<!-- acting-blends:start -->
```python
from srstudio.acting import bento_blends, compile_performance, parse_score

rig = bento_blends()
score = parse_score({
    "schema": "srstudio.acting/1.2.0", "duration": 3,
    "idle": False, "sample_rate": 24,
    "beats": [
        {"at": 0, "breath": 0, "transition": 0},
        {"at": 1, "emotion": "concerned", "gesture": "tablet",
         "transition": 1, "blend": True,
         "head": {"lean": 0.3, "nod": 4}},
    ],
})
plan = compile_performance(rig, score)
middle = plan.sample(1.5)
assert abs(middle.face_blend.weight - 0.5) < 1e-12
assert plan.window(1.25, 2.5).sample(0.25) == middle
# plan.window(1.25, 2.5).place(ep.cv, ep.comp, at=0)
```
<!-- acting-blends:end -->

The driver deforms lids, brows and mouth controls before clipping and inking.
Only the face geometry is sampled; the existing head/body transform chain remains
shared. Rendered faces hold at `sample_rate`, anchored at performance zero, with
exact launch and arrival boundaries. `sample().face_blend` reports continuous
intent; it is `None` outside an active blend. The expression and emotion labels
still change at arrival. No continuous-raster or perceptual-quality guarantee is
implied by these numeric samples.

Use `idle=False` or an explicit empty gaze override to avoid procedural gaze
ownership. Speech, named/target gaze, expression overrides and pose changes inside
a blend are refused. A beat may coordinate numeric posture, head and breath with
the face; gestures still replace at arrival. Monotone linear, sine-in-out,
cubic-in-out and quint-in-out curves are supported. Existing transition policies
can stagger the expression's launch/arrival relative to numeric channels; their
anticipation and settling do not add facial overshoot.

Custom Toon rigs bind a `face_blends.FaceBlender` to `HeadRig.face_blender`.
Declare directed `FacePose` pairs and return `FaceLayers` with reference-pixel
cubic geometry and `ink`, `white`, `#RRGGBB` or `#RRGGBBAA` colors. Preflight checks
endpoint equivalence against the bound rig and validates emitted geometry. Tracks
allow at most 1,000 held frames and 2,000,000 coordinates (including endpoint
checks), with 1–120 samples/second and a 600-second performance limit. Each held
frame is drawn at its own time and keyed half a frame before it
([ADR 0216](decisions/0216-held-keys-at-frame-centres.md)), so set the track's `fps`
to the project's frame rate. Untrusted
data never supplies Python callbacks; a driver is a trusted runtime binding.

Run the five-second face/body study and its cut variant:

```sh
python -m examples.acting_blends ../generated/acting-blends
scene-render render ../generated/acting-blends/cuts.xml --frames 0..120 --output 'frame-%04d.png' --strict --quality final
scene-render encode ../generated/acting-blends/cuts.xml --strict --quality final
```

The uncut and cut variants share framing and should match at every frame, including
cuts inside both blends. `report.json` preserves the score's sampled state, rig
capabilities and explicit limits; it does not grant drawing approval.
