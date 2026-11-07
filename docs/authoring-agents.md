# JSON authoring for agents

[Task index](authoring-reference.md) · [Discovery](authoring-discovery.md) · [Motion](catalog/limbs.md)

Use `srstudio.authoring/1.0.0` to author a character performance, isolated gesture,
or attached-prop study. The parser constructs typed SDK records. Supply the canvas
and parent separately at compilation; JSON never contains runtime objects, import
paths, callbacks or arbitrary constructors.

```bash
srstudio recipes --json
srstudio recipes pip --json
srstudio schema authoring --version 1.0.0 --json
srstudio inspect character pip --fields name,contract.authoring --json
```

`recipes` returns nine executable studies, their request documents, style, scope,
test location, preview commands and evidence limitations. Its `curves`
describe the scalar curve choices below. Character inspection links supported
builders to the exact arguments schema, parser, compiler and runtime bindings.
Other builders remain available through their typed Python APIs.

## Parse, then bind

<!-- agent-request:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, authoring

document = {
    "schema": "srstudio.authoring/1.0.0",
    "task": "character",
    "character": "pip",
    "interval": {"start_s": 3, "end_s": 5},
    "placement": {"x": 540, "y": 1400, "scale": 1.5},
    "arguments": {"cues": [
        {"time": 0, "pose": "stand"},
        {"time": 1, "pose": "wave-a", "ease": 0.3},
    ]},
}
request = authoring.parse_request(document)
scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=6)
cv = Canvas(scene, font_asset=None)
compiled = authoring.compile_request(cv, cv.comp, request, id="speaker")
group = compiled.group
evidence = compiled.to_dict()
assert not scene.check()
```
<!-- agent-request:end -->

The interval is inclusive at `start_s` and exclusive at `end_s`, on the parent's
clock. Every performance key uses seconds from zero within that interval. Placement
uses parent-space pixels, degrees and dimensionless scale. Changing the interval
does not require retiming the source, regardless of `Canvas.local_time`. Under an
already offset parent, `start_s` is relative to that parent, not the project.

Supported families are Actor, Soft, Stick, Ink, Saga, Gloss and selected Toon rigs.
Use the names and closed argument shapes from discovery. Family records share a
clock, but pose vocabularies remain rig-specific: for example, Gloss Sunny's face
states differ from Nadia's. The adapters own legacy `enter`, `end`, `duration` and
position arguments; those fields are rejected in `arguments`.
Each character's schema carries its declared vocabulary, and parsing checks it,
including defaulted record fields. Invalid values identify an exact repair path
such as `arguments.cues[0].pose` and list the accepted choices.

`gesture` takes a versioned `motion` document, optional `style` and `fps`.
`carry` additionally takes a typed prop `mesh` and a matching named `attachment`.
Both use the same interval and placement. Procedural limbs versions 1.0–1.4 and
keyed limbs 1.0 are accepted. Source motion extending beyond the interval is
refused instead of silently cropped. Carry follows the attachment frame during
the grip and holds the final world frame after release; it does not simulate a fall.
`limbs.serialization.motion_dict(motion)` returns JSON-shaped dictionaries and
lists that can be assigned directly to a request's `motion`; no JSON round trip is needed.

`compile_request` returns `CompiledRequest`: use `.group` as a scene parent,
`.diagnostics` for sampling warnings, and `.motion_reports` for named numeric
measurements. `.frames` and `.backend` identify the emitted motion; characters
without a limb audit have no motion reports and a null frame count. `to_dict()`
exports the evidence without runtime objects. Migrate earlier group-returning
calls by selecting `.group`. No quality profile or perceptual approval is implied
by a successful compilation or a numeric measurement.

The JSON boundary permits at most 100,000 values, 32 nested levels, 16,384
characters per string and finite numbers. Intervals are at most 600 seconds;
emission rates are integers from 1 to 120 Hz. Geometry and compiler budgets still
apply. Structural schema validation does not replace parsing or rig validation.
Failures expose `code`, `path`, `actual`, `expected` and `remedy`. A failed compile
restores scene mutations and held-frame bookkeeping so a corrected request can retry.
On `Canvas(held_frames=True)`, call `cv.place_held()` after placing all clips;
`Episode.finish()` does this automatically. Clip-local conversion preserves its
bookkeeping, including when intervals or ancestor clocks start between project frames.

## Choose the motion intent

`curves.track(((0, 0), (1, 100), (2, 180)), intent=...)` authors a scalar source:

| Intent | Source behavior |
| --- | --- |
| `stop-smoothly` | Zero velocity and acceleration at every key and endpoint hold. |
| `pass-through` | Shared velocity and zero acceleration at interior keys; smooth endpoint holds. |
| `intentional-impact` | Cubic arrival with a deliberate velocity jump into the hold or next segment. |

Call `sample(time)` for the source value and `describe()` for its continuity scope.
`emit(cv, group, "x", fps=24)` emits bounded linear samples on the Canvas clock and
reports the key count. Source C2 continuity does not transfer to piecewise-linear
emission, a constrained skeleton, projected geometry or raster output.

New procedural limb styles use a C2 accent envelope: the arc, overshoot and
asymmetry contributions have zero velocity and acceleration at their endpoints.
This removes the old sin² envelope's acceleration jump. It is a source-envelope
property, not a biomechanical guarantee. Legacy documents retain their original
envelopes; see [motion versioning](catalog/limbs.md).

Compilers refuse non-rest actions with no interior output sample and contacts
with no sample in their active interval (`motion.sampling`). Entirely cropped-away
events are excluded. Missed action phases are disclosed as `motion.phase-sampling`
diagnostics by motion compilation. Increase the rate within its bound or lengthen
the event; a zero-valued sampled quality metric cannot certify an invisible action.

## Preview and inspect evidence

```bash
python examples/agent_authoring.py /tmp/agent-previews
scene-render render /tmp/agent-previews/pip.xml --frames 0..48 \
  --output /tmp/agent-previews/pip-%04d.png --strict
```

Use a fresh output directory. The example writes nine two-second, 24 fps scenes
and adjacent JSON reports with source requests, scene hashes, compilation evidence and scope. It validates
the SDK scene but does not render; `rendered_review="not-run"` is intentional.
The optional `--recipe ID` builds one study. Recipe render commands cover 48 frames.

These studies include a bust, an upper-body rig, whole characters and isolated
arms. Named poses can switch discretely. Inspect temporal playback as well as
stills. Tests exercise all supported character names, schema parity, clocks and
rollback; pixel tests check Pip's framing and the carry prop's visibility at three
times. Neither those tests nor numeric calibration proves full-body balance,
heel-strike/toe-off realism, emotional readability or human preference. Retain
actual renderer responses and independent perceptual ratings when those are required.

The carry study reaches, translates the rooted arm while gripping the prop, then
releases it. Spatial tests verify travel, hand-relative attachment and the held
world frame after release; the study remains an isolated arm, without a body or a physical fall.

## Read contract coverage accurately

`contract.binding` separates `runtime_bindings` from `unresolved_fields`, with
JSON-pointer paths, required/optional status and conditional branches. A canvas
does not count as missing authoring data. `data_shape_complete` means no unresolved
data fields; it does not promise semantic validity or automatic binding.

`catalog --contract-coverage --json` reports complete data shapes, entries with
runtime bindings, entries with examples and named unresolved parts. “With examples”
counts declared snippets, not executions or successful renders. The generated
[coverage table](authoring-discovery.md#non-character-discovery-and-drawing-anchors)
tracks those measures independently from units, clocks and anchors.
