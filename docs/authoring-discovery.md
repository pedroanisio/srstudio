---
updated-by: OpenAI Codex (GPT-6)
---

# Discover parts and bind their contracts

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Inspect capabilities before constructing a drawing. The recipes below import the public SDK, create real canvases and parents, and exercise local versus project clocks. Unknown contract fields remain unknown. For plugin registration and failure atomicity, see [drawing extensions](authoring-extensions.md).

Run commands from the srstudio repository root.

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
| `composition` | Animation keys explicitly use the composition clock, even if `Canvas.local_time=True`. |
| `parent` | Visibility start/end attributes use the containing parent's timeline. These are not durations. |
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

Core Cutout and its extended families publish 113 prop, 16 location and 11 graphic contracts, including
`reaching-hand`'s held-prop callback and the hiring, home, office, shop, handed, leak, lobby, locate, odds and
reference modules. Coverage remains partial across the full catalog. Inspect it separately from ordinary listings:

```bash
srstudio catalog --contract-coverage --json
srstudio catalog --style cutout --kind prop --contract-coverage
srstudio inspect prop coffee-cup --json
```

Forty Toon core, props, sets and world builders also declare their semantics,
including `toon-headset`. Toon positions use `toon-reference` space: `fx(x)` maps
`x * 1080 / 592`, while `fy(y)` maps `(y - 70) * 1080 / 592`, both rounded to two
decimals. Distances use `fh` without the y offset. Font sizes and measurement callback
results use frame pixels. Resizing the canvas does not rescale this reference artwork.
The note insert is an explicitly documented frame-pixel exception.

Most of these Toon builders return `None`; draw inside a group you create if you need
a placement handle. `toon-headset` instead returns ordered geometry/paint layers for
`stickers=`, with no scene mutation. These declarations do not promise spatial grips.

The clock and logo explicitly pin animation keys to composition time. The plant,
coffee machine and other canvas-keyed parts follow `Canvas.local_time`. Toasts mix
parent visibility bounds with composition-keyed movement; inspect constraints before
placing them in a shifted shot. `measure(text)` and `measure(text, size)` are runtime
text-measurement bindings, not drawing callbacks.

<!-- toon-drawing-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

plant = registry.get("prop", "toon-plant")
clock = registry.get("prop", "toon-clock")
plant_info = plant.describe()["contract"]
clock_info = clock.describe()["contract"]
assert plant_info["arguments"]["properties"]["at"]["x-space"] == "toon-reference"
assert plant_info["capabilities"]["spatial_attachment"] is False

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=4)
cv = Canvas(scene, font_asset=None, local_time=True)
parent = cv.group(cv.comp, "drawings")
plant_result = plant(cv, parent, at=(120, 750), scale=1, end=4)
clock_result = clock(cv, parent, times=((0, "08:00"), (2, "09:30")), at=(350, 400))
# Plant keys use local time. Clock hands remain on composition time.
# This unshifted parent aligns both clocks; neither builder returns a handle.
assert plant_result is clock_result is None
```
<!-- toon-drawing-discovery:end -->

The 20 builders in `toon_flat` and `toon_odds` also declare their semantics.
Check individual arguments: `toon-closet.at` is an opening time, while
`toon-pipe.at` is a reference point. Flat animations follow the canvas clock;
pipe drips and mosquito paths explicitly use composition time. The paper insert
uses frame-pixel geometry and the canvas animation clock.

Flat builders return `None`; the odds builders return a `Group` whose coordinates
are already converted to frame pixels. Neither family supplies spatial grips.
An `end` marked `validation-limit` checks timing without hiding the drawing:
laundry piles, tiny drawers and tasting spoons remain visible. Give them a parent
with a visibility end when the shot needs one. A pipe's `end` hides its drops and
jets, while its body remains visible.

<!-- toon-household-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

pile = registry.get("prop", "toon-laundry-pile")
pipe = registry.get("prop", "toon-pipe")
pile_info = pile.describe()["contract"]
assert pile_info["arguments"]["properties"]["end"]["x-role"] == "validation-limit"

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=4)
cv = Canvas(scene, font_asset=None)
holder = cv.group(cv.comp, "household", end=3)
pile_result = pile(cv, holder, start=None, top=750, end=3)
pipe_result = pipe(cv, holder, at=(470, 560), drips=(0.5, 1.5), end=3)
assert pile_result is None
# The holder ends visibility for both the pile and the pipe body at 3 seconds.
# No shifted parent is used: composition animation and parent visibility align.
```
<!-- toon-household-discovery:end -->

The 33 `toon_house` and `toon_homeware` builders declare room, costume, appliance
and screen conventions. Worn props such as `toon-towel` accept a reference point;
they do not track a character automatically. `toon-rack` and `toon-shampoo` return
their root groups. Other builders in these two modules return `None`.

Dishwasher loads, screen changes and soup-tub counts use parent visibility.
Receiver pulses, rack movement, bubbles and garden-tool vibration use canvas
animation time. Finger movement and shower-water phases force composition time.
The horse's `start`/`end` control automatic blinks, not visibility; an explicit
blink sequence also works with `end=0`. Inspect nullable schemas through `anyOf`
to distinguish omitted behavior from an empty sequence.

<!-- toon-domestic-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

shampoo = registry.get("prop", "toon-shampoo")
towel = registry.get("prop", "toon-towel")
point_schema = towel.describe()["contract"]["arguments"]["properties"]["at"]
assert point_schema["type"] == "array"
assert shampoo.describe()["contract"]["capabilities"]["returns_scene_handle"]

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=4)
cv = Canvas(scene, font_asset=None)
holder = cv.group(cv.comp, "bathroom-props")
bottle = shampoo(cv, holder, at=(340, 700), bubble=1)
bottle.end = 3
towel(cv, holder, at=(185, 500), start=0, end=3)
# The bottle handle controls the whole prop; its bubble has its own child keys.
```
<!-- toon-domestic-discovery:end -->

The 15 `toon_bed`, `toon_ward` and `toon_surgery` builders distinguish scene
handles, visibility spans and animation limits. Bed builders return groups;
`toon-bedside-drawer` returns only the moving drawer front inside its cabinet.
Create a containing group to move or hide the whole nightstand. Drawer buzzes,
opening and light use composition animation time; `lit` is the held opacity,
from zero to one. Opening has no automatic visibility end.

Ward and surgery builders generally return `None`. The bandage returns a group;
give it a face drawing parent and a runtime object whose `eyes` contains two
reference points. It inherits that parent's transform without finding or binding
an actor. The swung arm similarly rotates a drawn limb about a fixed reference
shoulder; it supplies no elbow or contact solve.

The dental lamp's `end` limits animation without hiding the lamp. Photo and probe
`end=0` instead means a still: their `start` is ignored. A positive end gives them
parent visibility bounds and a 0.28-second composition-keyed arrival. Keep parent
visibility and animation clocks aligned. Group `timeOffset`/`timeScale` remap the
child timeline, including composition-keyed animations within that group.

<!-- toon-care-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

drawer = registry.get("prop", "toon-bedside-drawer")
lamp = registry.get("prop", "toon-dental-lamp")
drawer_info = drawer.describe()["contract"]
lamp_info = lamp.describe()["contract"]

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="30", duration=4)
cv = Canvas(scene, font_asset=None, local_time=True)
cabinet = cv.group(cv.comp, "cabinet", end=3)
front = drawer(cv, cabinet, buzzes=(1,), slides=2, lit=0.35)
lamp_holder = cv.group(cv.comp, "lamp-holder", end=3)
lamp_result = lamp(cv, lamp_holder, pivot=(712, 30), end=3)
# Both caller-owned parents hide complete drawings at 3 seconds.
# Moving or hiding front alone affects only the drawer front.
assert drawer_info["capabilities"]["returns_scene_handle"]
assert lamp_result is None
```
<!-- toon-care-discovery:end -->

The 22 parts in `toon_everyday`, `toon_inserts`, `toon_study` and `toon_laptop`
also publish contracts. Inspect the return before using it:

| Parts | Return |
| --- | --- |
| Phone, speaker, receipt, take-a-number dispenser, clipboard | `(left, top, right, bottom)` footprint in Toon reference pixels |
| TV menu, remote, open laptop | Created scene `Group` |
| Other registered parts in these four modules | `None` |

Footprint checks use the fixed Toon frame, caption band and signature box; they
do not account for an external parent transform. Text measurement callbacks take
`(text, font_size)` and return frame-pixel widths. Phone `Screen.at` and clipboard
`Field.at` are composition times, while the props' `at` arguments are positions.
Laptop notes use `u`/`v` fractions of a bilinear screen quad.

Books use reference positions, but the highlighter, study page and quiz sheet use
frame pixels. `row_span` and `note_span` convert book geometry into frame positions
for the marker. The following example keeps the marker on the advancing highlight
edge using the same composition clock and linear interpolation:

<!-- toon-study-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry
from srstudio.toon_study import HIGHLIGHT, SWEEP, row_span

book = registry.get("prop", "toon-open-book")
marker = registry.get("prop", "toon-highlighter")
marker_info = marker.describe()["contract"]
assert marker_info["arguments"]["properties"]["at"]["x-space"] == "frame"

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=3)
cv = Canvas(scene, font_asset=None)
left, right, y = row_span(0, at=(300, 801))
tip = left + 0.02 * (right - left)
book_result = book(cv, cv.comp, at=(300, 801), sweep=(0, HIGHLIGHT, 1), id="book")
marker_result = marker(
    cv, cv.comp, at=(tip, y), paw="#c49a6c",
    path=((1, tip), (1 + SWEEP, right)), id="marker",
)
```
<!-- toon-study-discovery:end -->

`srstudio.contract_coverage(style=None, kind=None)` returns the same versioned coverage report. Per-kind counts
separate explicit declarations, complete argument shapes, units, clocks and anchors; `undeclared_parts` names
the gaps. A count of declarations does not certify complete semantics. Discovery never invokes a builder.
The regular `catalog` list retains its existing shape. Coverage and usage-ranking reports are separate modes.
Directly replacing `Entry.builder` invalidates its previous declaration even if the new signature matches.
Inspection marks that contract `declaration_status="builder-changed"`; coverage lists it under
`stale_contract_parts` and `undeclared_parts`. Re-register the replacement with its own checked metadata, or
restore the original version with `parts.restore`. Drawing approval and semantic declarations remain separate.

`register(..., slots=(...))` supports explicit callback slots on every drawing kind, including props.
Each slot must name an actual non-variadic parameter. A slot's contract describes the group it receives and
its depth; the registration itself does not validate callback bodies or sandbox their effects.

The counter/store contracts distinguish parent placement from local dimensions and motion values. For example,
`dark-eyes.glances` shifts pupils in drawing units, while `shelf-goods.drift` moves its root in parent units.
Both use the canvas clock, including `Canvas.local_time`. `jump-clock.start` is a displayed (hour, minute),
while its jump timestamps use canvas seconds and `spin` is a duration. `pen-on-chain` returns `ChainRun`
timing data; its scale changes pen/link appearance without scaling the grip path or chain length.
`paper-poster.x/y` locates the unrotated top-left, but its returned group rotates about the sheet center.
Seeded `qr-code` artwork is decorative and declares `qr_payload_encoding=False`.

This cart callback places a lamp on the cart's local floor, behind its front wire. The returned cart group
owns both objects' placement and scale:

<!-- store-slot-contract:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, get

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=2)
cv = Canvas(scene, font_asset=None)
cart_part = get("prop", "shopping-cart")
assert "contents" in cart_part.describe()["slots"]
lamp = get("prop", "table-lamp")
cart = cart_part(
    cv, cv.comp, 540, 1400, scale=0.5,
    contents=lambda group: lamp(cv, group, 0, -170),
)
```
<!-- store-slot-contract:end -->

Cutout timing contracts distinguish `(start, end)` spans from `(start, duration)` events. `hair-fall.falls` and
`desk-printer.sheets` use durations; `table-phone.rings`, `wall-plaque.read` and location `shots` use end times.
The clock is the canvas clock, including `Canvas.local_time`. A phone post's `date` is display text, while
`glasses-glint.lenses` contains local drawing coordinates. Neither is a sequence of animation times.

This font-free example inspects a fall's clock and makes a half-second fall starting at two seconds:

<!-- cutout-clock-contract:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, get

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=3)
cv = Canvas(scene, font_asset=None)
fall = get("prop", "hair-fall")
event = fall.describe()["contract"]["arguments"]["properties"]["falls"]["items"]["prefixItems"]
assert event[0]["x-timebase"] == "canvas"
assert event[1]["x-role"] == "duration"
hair = fall(cv, cv.comp, falls=((2.0, 0.5),))
```
<!-- cutout-clock-contract:end -->

`id-lanyard.photo` receives a child group at local y=178 inside the scaled lanyard, with an 88×84 window around
(-44, -44); its artwork is not clipped. `barbershop.in_mirror` receives room coordinates inside the glass group,
with neither automatic clipping nor reflection. Author reflected figures within `BARBER_MIRROR` yourself.
`coat-over` and `robe-and-blazer` belong in a Cutout actor's group and use its fixed torso coordinates; they do
not retarget clothing to arbitrary rigs. `location-chip.scale` sets each stop subgroup's resting scale, while
its returned root only carries placement. These constraints are available through `inspect` before drawing.

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
