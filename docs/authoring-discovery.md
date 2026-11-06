---
updated-by: OpenAI Codex (GPT-6)
---

# Discover parts and bind their contracts

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Inspect capabilities before constructing a drawing. The recipes below import the public SDK, create real canvases and parents, and exercise local versus project clocks. Unknown contract fields remain unknown. For plugin registration and failure atomicity, see [drawing extensions](authoring-extensions.md).

Run commands from the srstudio repository root.

For closed JSON tasks that construct typed records, start with `srstudio recipes --json`
and the [agent authoring guide](authoring-agents.md). Supported character contracts link
their `authoring` adapter and its local performance clock.

For an installed SDK, discovery commands also work outside a repository. Start with a bounded summary:

```bash
srstudio catalog --summary --json
srstudio catalog --search coffee --kind prop --limit 10 --json
srstudio catalog --kind character --capability limbs --limit 10 --json
srstudio catalog --operations --kind character --capability head_motion --limit 10 --json
srstudio inspect character manager --fields name,contract.capabilities --json
```

Paged results use `srstudio.catalog-page/1.0.0`: `items`, `total`, `offset`, `limit`, and `next_offset`
(null at the end). Repeat the same query with that offset. Pages sort by kind and name; keep the SDK,
plugins and registry state fixed while paging. The default page is 20 entries, with a maximum of 100.
Search matches all case-insensitive words in names, summaries or tags. Repeated `--capability` filters
are ANDed and match only explicit true declarations, never unknown values or inferred parameter names.

`catalog --fields kind,name,summary --json` selects top-level listing fields and enables paging.
`inspect --fields` also accepts dotted dictionary paths such as `contract.arguments`; invalid paths
raise a structured field error. These selectors require JSON output. Paged discovery cannot be combined
with usage reports or contract-coverage reports. Plain `catalog --json` retains its full legacy listing.
Python agents can call `registry.search(query, kind=..., capabilities=(...), limit=..., offset=...)`
and `registry.select_fields(registry.describe(kind, name), ('name', 'contract.capabilities'))`.

Use `--operations` (Python: `operations=True`) to search explicitly declared immediate helpers. Each row adds
`operation`, the page adds `scope="operations"`, and ordering is by kind, name, then operation. Words also match
the operation name. Capability filters apply to each helper independently. A character's static builder may
declare `head_motion=false` while its `head_performance` helper declares it true. These helpers bind the correct
rig for Bento v1/v2, Lyra, Fox v2, Sloth, Goat and Hamster. Inspect the helper's own contract and resolve it with
`registry.get(kind, name).operation(operation)`; a missing helper raises a structured error listing valid names.

<!-- helper-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry
from srstudio.head_motion import Channel, HeadPlan

page = registry.search("bento", kind="character", capabilities=("head_motion",), operations=True, limit=1)
row = page["items"][0]
entry = registry.get(row["kind"], row["name"])
contract = entry.describe()["contract"]["operations"][row["operation"]]
assert contract["arguments"]["properties"]["duration"]["x-role"] == "end"

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=2)
cv = Canvas(scene, font_asset=None)
pose = entry.operation("pose_of")(0, "neutral")
group = entry.operation(row["operation"])(
    cv, cv.comp, [pose], duration=2,
    plan=HeadPlan(nod=Channel(((0, 0), (1, 1)), curve="sine-in-out")),
)
assert not scene.check()
```
<!-- helper-discovery:end -->

Here `duration` is the project exit time; pose starts are relative to `enter`, and head-plan keys use project
seconds. Construct the typed `Pose` and `HeadPlan` records before calling the helper.

Unknown kinds and style filters raise `RegistryError` with `path=kind` or `path=style`, the rejected
value, valid choices and a repair instruction. Plugin-declared styles are valid after their modules are imported.
In JSON mode, plugin logs cannot mix with the catalog or inspection payload. Failed imports return a
structured diagnostic on stderr, including bounded captured logs; see [plugin diagnostics](authoring-diagnostics.md).

For targeted retrieval, use the recipe section matching the selected family:

| Family or task | Recipe sections |
| --- | --- |
| Contracts and registration | [Agent contracts](#agent-contracts) |
| Cutout and Toon placement | [Drawing anchors, rooms and held props](#non-character-discovery-and-drawing-anchors) |
| Stick | [Household](#stick-household-and-everyday-drawings), [transport](#stick-road-and-airport-composition), [scene placement](#stick-scene-placement-and-partial-handles) |
| Captions, maps and news | [Core and Orbit](#core-captions-and-orbit-print-artwork), [presentation kits](#presentation-kits-and-map-assets), [news](#news-graphics-and-insert-timelines) |
| Soft and Blob | [Rooms](#soft-rooms-bedtime-props-and-phone-inserts), [props](#soft-props-appliances-and-effects), [layouts](#blob-furniture-room-layouts-and-placement-helpers) |
| Ink | [Shots and interfaces](#ink-shots-and-illustrated-interfaces) |
| Collage | [Table props](#collage-table-and-corner-props), [reaches](#everyday-collage-props-and-sampled-reaches), [rooms and photos](#collage-rooms-photographs-and-illustrated-interfaces) |
| Rafa, Gloss and Saga | [Rafa models](#rafa-models-and-surface-preparation), [Gloss rooms](#gloss-rooms-cards-and-graphics), [Saga contact](#saga-scenery-and-sampled-console-contact) |
| Cel and wire vehicles | [Measured rooms and vehicles](#measured-rooms-call-props-signatures-and-wire-vehicles) |

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
gaps by guessing from parameter names. Start with `srstudio catalog --summary --json`, inspect the selected part, supply its
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

The default catalog's declaration coverage is generated from `registry.contract_coverage()` below.
Explicit contracts can still have unknown units, clocks or capabilities. “With units/clocks/anchors” means at least
one such annotation exists, not that every parameter is covered. Complete data shapes exclude known runtime
bindings such as canvases. `contract.binding` lists runtime and unresolved data paths separately, including
required and conditional status. “With examples” counts declared snippets, not executions or renders.
Neither a declaration nor a complete shape certifies semantic validity.

<!-- contract-coverage:start -->
| Kind | Registered | Explicit contracts | Complete data shapes | Runtime bindings | With examples | With units | With clocks | With anchors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| character | 81 | 81 | 8 | 81 | 5 | 81 | 78 | 0 |
| location | 128 | 128 | 110 | 128 | 2 | 96 | 72 | 26 |
| prop | 569 | 569 | 560 | 569 | 5 | 545 | 250 | 262 |
| graphic | 88 | 88 | 74 | 88 | 1 | 88 | 82 | 15 |
<!-- contract-coverage:end -->

Contributors regenerate this table with `python tools/update_contract_coverage.py`; its `--check` mode and the
documentation test detect drift. Plugin imports change the live registry, so inspect your installed environment:

```bash
srstudio catalog --contract-coverage --json
srstudio catalog --style cutout --kind prop --contract-coverage
srstudio inspect prop coffee-cup --json
```

Toon core, props, sets and world builders also declare their semantics,
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

The 21 builders in `toon_cars`, `toon_dinner`, `toon_parlour` and `toon_rooms`
declare the traffic, dining and room contracts. Newer Toon orbit props and sets
still require their own semantic declarations. Passing vehicles use
`Passing(at, kind, colour)`: `at` is the composition time when the vehicle crosses
the frame center. Road scrolling follows the canvas clock; tally marks use parent
visibility. Loose wheels keep translation and rotation proportional to their
converted radius. Their scale, position and destination must produce finite
geometry and a positive frame-pixel radius.

Dining dishes accept `(kind, x)` or `(kind, x, at)` rows. They use a fixed table
height and canvas-keyed opacity reveals. Cones and the parlour case return groups
with geometry already placed in frame pixels; changing their group `x` adds a
translation to that placement. The parlour front's `start` and `end` are only
validation limits: they do not trim traffic or hide the room.

Lit rooms return a dictionary of `toon_rooms.Cue` records. Their closed light maps
list the room's supported sources; omitted sources receive defaults. A screen's
first cue names its color, and later cues can retain or change it. Light levels,
screen colors, tickets and router LEDs follow the canvas clock. The lounge speaker
ring uses composition keys. `end=0` draws a still; positive `end` bounds generated
keys without hiding the room.

Create the light layer after the actor and before the foreground desk. This lets
room lighting reach the character while keeping the signature clear. `dim` fades
linearly over 1.5 seconds; it can support a quiet mood change, but it does not
select or animate the actor's expression.

<!-- toon-lit-room-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, toon

room = registry.get("location", "toon-lounge")
room_info = room.describe()["contract"]
dog = registry.get("character", "toon-dog")
names = dog.describe()["contract"]["vocabularies"]
pose = toon.Pose(0, names["eyes"][0], names["mouths"][0], names["arms"][0])

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="30", duration=4)
cv = Canvas(scene, font_asset=None)
back = cv.group(cv.comp, "back")
actor = cv.group(cv.comp, "actor")
light = cv.group(cv.comp, "light")
front = cv.group(cv.comp, "front")
cues = room(cv, back, {"lamp": ((0, "on"), (1, "dim")),
                       "tv": ((0, "on", "blue"),)}, end=4, light=light)
dog(cv, actor, [pose], enter=0, duration=4)
toon.desk(cv, front)
assert room_info["returns"]["x-role"] == "parsed-light-cues"
```
<!-- toon-lit-room-discovery:end -->

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
separate explicit declarations, complete argument/data shapes, runtime bindings, examples, units, clocks and
anchors. `undeclared_parts` names declaration gaps; `unresolved_parts` names incomplete data shapes.
A count of declarations does not certify complete semantics. Discovery never invokes a builder.
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

## Stick household and everyday drawings

The 49 builders in `stick_home`, `stick_office` and `stick_odds` declare their
coordinate units, return values, choices and animation clocks. They draw in
frame pixels for the 1080×1920 Stick layout; changing canvas dimensions does not
scale fixed furniture or typography. These drawings provide no spatial grip,
collision geometry or anatomical solver.

Check the returned coordinate frame before attaching or moving a prop.
`stick-handset` bakes its center and scale into the geometry, so assigning its
group `x` adds a translation. `stick-box`, `stick-receipt`, `stick-drill` and the
other explicitly local props return a group whose transform owns placement.
Their origin is an authored drawing reference, not a verified physical contact.
For example, the truck's tires extend below its authored y reference.

Opacity gates and motion keys use the canvas clock: composition time by default,
local time with `Canvas.local_time=True`. The caller-phone shake lasts 0.25 seconds
per ring and moves in parent pixels, independently of the phone's scale. A flame
or spark `rate` counts alternating drawings per second; a complete two-drawing
cycle takes `2/rate` seconds.

An animation limit does not necessarily hide the drawing. The overhead figure's
feet stop at `end`, but its body remains. A scanner's `end` finishes its scan line.
A robe or passenger drawing covering a whole interval omits its opacity gate.
Use a caller-owned parent to control complete shot visibility, and give a robe
the same validated keys, poses and transforms as its figure.

<!-- stick-drawing-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

entry = registry.get("prop", "stick-receipt")
contract = entry.describe()["contract"]
assert contract["returns"]["x-space"] == "returned-group"
assert contract["capabilities"]["spatial_attachment"] is False

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=6)
cv = Canvas(scene, font_asset=None, local_time=True)
shot = cv.group(cv.comp, "receipt-shot", start=2, end=5)
receipt = entry(cv, shot, 540, 900, 300, unroll=(0.5, 1.5))
# Local unroll keys run within the shot; the outer parent hides all receipt geometry.
# The receipt starts at 2% height and holds its full height after unrolling.
```
<!-- stick-drawing-discovery:end -->

## Stick road and airport composition

The 28 builders in `stick_car`, `stick_windshield`, `stick_street`,
`stick_roadtrip` and `stick_airport` declare their drawing frames, clocks and
return ownership. Inspect nested records before interpreting a value as speed,
a duration or physical geometry.

`stick-car` takes `Scroll.speed` in frame pixels per second; its six scenery
layers use different fractions of that speed. `Scroll.offset` changes scenery
placement and is not a source-time offset for cuts. `stick-windshield.speed`
counts receding road dashes per second. Both are authored 2D effects.
`stick-ride` takes an existing `node`, modifies its y keys and returns `None`.
Its waves depend on sample index, so changing `step` changes temporal frequency;
the last sample can follow `end`. These adapters do not promise phase-preserving
cuts or physical suspension dynamics.

`ride` and `windshield` accept `max_keys` (an integer from 2 to 20,000,
default 20,000), limiting generated keys per animation track. Reduce duration
or sampling rate when a plan exceeds the budget. Nonfinite values and times
that collapse at serialization precision raise `StickDataError` before the
call changes the scene. A parked windshield or zero-amplitude ride emits no
motion keys. Windshield reset gaps are the smaller of 0.001 seconds and half
a cycle, keeping fast representable cycles ordered.

The mirror and mounted-phone returns have `x-role="partial-drawing"`. The mirror
returns only its masked glass; the phone returns only its case. Use an outer
parent when moving or hiding the complete drawing. A mirror callback receives
parent coordinates, not coordinates translated to the glass's top-left.

<!-- stick-transport-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry

entry = registry.get("prop", "stick-rear-view")
contract = entry.describe()["contract"]
assert contract["returns"]["x-role"] == "partial-drawing"
assert contract["arguments"]["properties"]["figure"]["x-role"] == "drawing-slot"

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=6)
cv = Canvas(scene, font_asset=None, local_time=True)
shot = cv.group(cv.comp, "mirror-shot", start=2, end=5)
seen = []

def reflection(glass):
    seen.append(glass)
    cv.ellipse(glass, 450, 700, 180, 180, "#F0E9DF")

# The callback runs once; the glass mask clips its drawing.
# The outer parent owns visibility of glass, housing, background and glare.
glass = entry(cv, shot, reflection)
```
<!-- stick-transport-discovery:end -->

Airport readouts accept timed display strings, with `None` for a dark interval;
they do not infer a physical weight unit. Readings begin at zero, rise strictly
and finish before `end`. Their opacity keys follow the canvas clock, while the
scale housing stays visible. `stick-carry-on(tag=None)` and
`stick-gate-podium(plate=False)` need no font. `stick-gate` still requires its font
and valid sign strings when `sign=False`.

## Stick scene placement and partial handles

The 24 builders in `stick_door`, `stick_flat`, `stick_gym`, `stick_school`,
`stick_shop`, `stick_bed` and `stick_table` declare their return ownership,
placement and timing. `stick-snow-cap` returns a path shape, while `stick-duvet`
returns only the moving mound. The duvet cover and folds remain in sibling
nodes; move or hide an outer parent to control the entire drawing.

`duvet.lift` values are vertical displacements from the drawn mound.
`folded_bedding.slide` values are absolute parent x positions and replace its
`x` argument. Its interpolation is `cubic-out` per segment. An essay's `at`
places its sheet center, with scaling about that center, rather than placing
the sheet's top left. Inspect these semantics before attaching another prop.

<!-- stick-scene-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, stick_bed

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=3)
cv = Canvas(scene, font_asset=None)
bed_layer = cv.group(cv.comp, 'bed-layer')
entry = registry.get('prop', 'stick-duvet')
contract = entry.describe()['contract']
assert contract['returns']['x-role'] == 'partial-drawing'

# The phone uses the mound's authored drawing coordinates, not a new (0, 0) origin.
mound = entry(cv, bed_layer, 3, x=540, y=1300, near=1800,
              lift=((0, 0), (1, -20), (3, 0)))
phone = stick_bed.recorder(cv, mound, 540, 1100, 3, lines=2, live=True)
assert phone in list(mound.elements())

# Darkening is a multiply overlay with a radial pool, not a scene light.
stick_bed.lights_low(cv, cv.comp, pool=(540, 1100, 250), strength=0.6)
```
<!-- stick-scene-discovery:end -->

Door closure and Murphy-bed folding switch held drawings; they do not solve
hinge motion or collisions. Gym dawn, kiosk messages, alarms and scene motion
keys follow `Canvas.local_time`. A kiosk's nested `Screen.start` uses that same
clock, and its `tone` enumerates `idle`, `error`, `help` and `award`.
The turned clipboard requires a font; its edge and quarter views use paths
alone. These declarations describe supported drawing semantics, without
claiming spatial contacts, physical lighting or biomechanical motion.

## Core captions and Orbit print artwork

The core Stick and Toon orbit builders declare their arguments and return
ownership. Stick `hook`, `headline` and `captions` use parent-timeline visibility
attributes. A sequence shot provides a shot timeline; an ordinary group's
`start` only limits visibility and does not shift its children's timeline.
`Canvas.local_time` does not change these visibility attributes. Stick `words`
instead gates its text and animates its pop and scrim on the canvas clock.

<!-- core-orbit-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, stick, toon_orbit

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=4)
cv = Canvas(scene, font_asset=None)
sequence = cv.comp.add_sequence(id='shots')
sequence.add_group(id='lead', end=1)
shot = sequence.add_group(id='shot', end=3)

hook = registry.get('graphic', 'stick-hook')
args = hook.describe()['contract']['arguments']['properties']
assert args['start']['x-timebase'] == 'parent'
lettering = stick.Plate('#182030', 'M 100 350 L 250 350 L 250 380 L 100 380 Z')
card = hook(cv, shot, lettering, start=1, end=2)  # project seconds 2..3

# Orbit props return None. Own their placement/visibility with an outer group.
props = cv.group(shot, 'props')
result = toon_orbit.field_notebook(cv, props, at=(300, 900), scale=0.6)
assert result is None  # lettering=None leaves the label blank and needs no font
```
<!-- core-orbit-discovery:end -->

Orbit `at` places an authored foot in Toon reference coordinates. Scale and
placement are baked into the paths before reference-to-frame conversion; the
created group stays untransformed. Optional `Lettering(display, body)` names
font asset IDs independently of `Canvas.font_asset`. The salon uses both;
the terrace and notebook use only `display`. Builders do not load those fonts.
Orbit sets and props add neither signature marks nor the shared print finish.
Discovery metadata does not change their catalog approval status.

## Presentation kits and map assets

The 31 non-character builders in `host_kit`, `mind_kit` and `map_kit` declare
their clocks and return types. Their coordinates are frame pixels, except
map longitude/latitude in degrees and projection zoom in levels. Their
`measure(text, size)` callbacks return text advance in frame pixels at the
requested font size; use the actual bound font rather than character counts.

Host `punch` mutates an existing group, and its optional `push` is
`(duration, target_scale)`. Host `captions` takes an episode context and returns
`(background_bands_group, native_caption_track)`. Its words are timed tuples,
and its layout uses the episode safe area. Unpack the pair when controlling
caption visibility. This differs from the Mind and Map caption builders,
which return one group of text boxes.

Map views return a `MapAsset`, separate from the layer displaying it.
`parallel` adds routes to that asset; `population` adds geographic layers.
Neither returns a scene group. A pin or daylight marker uses the engine's
projection to follow that asset. A ring is fixed in frame coordinates and
does not follow the map. These are geographic bindings, not world-space
contacts or collision geometry.

<!-- presentation-discovery:start -->
```python
from sr_core.scene import MapAsset, Scene
from srstudio import Canvas, map_kit, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=4)
cv = Canvas(scene, font_asset=None)
view_builder = registry.get('graphic', 'map-flat')
assert view_builder.describe()['contract']['returns']['x-role'] == 'map-asset'
view = view_builder(cv, cv.comp, lon=0, lat=0, zoom=0, start=0, end=4)
assert isinstance(view, MapAsset)

# Place uses name, latitude, longitude. The unlabelled route needs no font.
place = map_kit.Place('Rome', 41.89193, 12.51133)
result = map_kit.parallel(cv, cv.comp, view, place, 0, 4, drawn=0.5)
assert result is None and len(list(view.iter('route'))) == 2

# runs means total elapsed hours across the interval, not hours per second.
clock = map_kit.clock(cv, cv.comp, 200, 400, 80, hour=9, start=0, end=4, runs=2)
assert clock.x == 200 and clock.y == 400
```
<!-- presentation-discovery:end -->

Before rendering a map project, use `map_kit.install(project_root)` to publish
the referenced GeoJSON files. Builders declare hashes and credits but do not
copy files into the project. Population dots come from the shipped dataset;
the builder does not fetch current figures.

Most kit animations explicitly use the composition clock even when the
canvas uses local time. Host `punch`, Mind `stamp` and Mind `zipper` follow
`Canvas.local_time` instead. Visibility attributes remain on the parent
timeline in both cases. Keep those clocks aligned when nesting shots;
inspect nested move, dive, sweep and reveal metadata before reusing a plan.
Mind spotlight and lens are drawn overlays, with absolute x tracks; they
do not calculate lighting or magnification.

## News graphics and insert timelines

The 27 non-character builders in `news_kit` and `news_inked` expose explicit
contracts. Select the version deliberately: names such as `news-phone` and
`news-phone@2` retain distinct drawings. Most builders return `None`; place
related graphics under a caller-owned group to move or hide them together.
Both caption builders return their complete text-panel group. Their cue
visibility is held, with no native word-level karaoke.

These layouts use frame pixels for a 1080×1920 composition. The route insert
uses phone-screen pixels below the header, with `(0, 0)` at frame `(190, 616)`.
Its `draw` argument is a duration. The marker moves linearly with segment
times proportional to distance; each full route leg appears at its segment
start. The route is a schematic drawing, not a geographic map asset.

<!-- news-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, news_inked, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=8)
cv = Canvas(scene, font_asset=None)

# Version 2's desk has no lettering and needs no font asset.
desk = registry.get('prop', 'news-desk@2')
parent = cv.group(cv.comp, 'news-shot', start=1, end=7)
assert desk(cv, parent) is None

route = registry.get('graphic', 'news-route').describe()['contract']
arguments = route['arguments']['properties']
assert arguments['draw']['x-role'] == 'duration'
assert arguments['track']['items']['x-space'] == 'phone-map'

# A later corridor stop starts a short step; it is not the arrival time.
keys = news_inked.corridor_keys(((1, 250, 250), (3, 400, 250)))
assert keys == [(1, 250, 250), (3, 250, 250), (3.22, 400, 250)]
```
<!-- news-discovery:end -->

Bind the show font and supply `measure(text, size)` using that font for text
builders. Version 1's desk includes lettering; version 2's does not. A
`Source` supplies the outlet, date and headline to display; constructing it
does not verify the source. Bubble `clock` and oven `time` are display copy,
not animation timestamps. The oven's digits remain fixed when its label
changes. Money-app inserts draw a UI without making service calls.

Animation keys use the composition clock even with `Canvas.local_time=True`.
Visibility intervals use parent time, including phone-message arrivals,
button refusals, door cuts and count changes. Align those clocks when placing
these graphics in sequence shots. The studio's `end` parameter is accepted
for compatibility but changes neither its sweep times nor its visibility;
use the caller-owned parent to limit the shot. Corridor targets are panel
pixels, and the dots have no skeletal, balance or collision constraints.

## Soft rooms, bedtime props and phone inserts

The 18 non-character builders in `soft_sets`, `soft_front`, `soft_bedtime`,
`soft_closet` and `soft_inbox` declare their coordinates, callbacks, clocks
and return ownership. Each returns a drawing group. Placed props expose an
origin in that group's unscaled drawing pixels; `x` and `y` place the origin
in the supplied parent's pixels. Room builders return the complete set,
including foreground elements that remain outside the room's framing.

Discovery represents typed `NamedTuple` records such as `Shot`, `Light`,
`Dim`, `BookSlide`, `Door` and `Count` as named properties with their actual
scalar defaults. Untyped fields remain unknown, and recursive records stay
bounded. These schemas describe inputs; construct the public Python records
when calling the SDK. Inspection does not construct them or draw a scene.

<!-- soft-scene-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, WARM, registry, soft_bedtime, soft_sets

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=6)
cv = Canvas(scene, WARM, font_asset=None)

book_contract = registry.get('prop', 'soft-picture-book').describe()['contract']
slide = book_contract['arguments']['properties']['slide']['anyOf'][0]['properties']
assert slide['time']['x-timebase'] == 'canvas'
assert slide['seconds']['x-role'] == 'duration'
assert slide['dx']['x-space'] == 'parent'

# held receives the framed room after the duvet; its return value is ignored.
def held(parent):
    return soft_bedtime.picture_book(
        cv, parent, x=540, y=1400, scale=0.8,
        slide=soft_bedtime.BookSlide(time=1, seconds=0.5, dx=120, dy=50, turn=30),
    )

room = soft_sets.bedroom(
    cv, cv.comp,
    shots=(soft_sets.Shot(0), soft_sets.Shot(2, 1.4, 300, 900)),
    lights=(soft_sets.Light(0, 'day'), soft_sets.Light(3, 'lamp', 100, 1200)),
    held=held,
)
assert room.id == 'soft-bedroom'
```
<!-- soft-scene-discovery:end -->

The book's slide adds parent-pixel displacements regardless of its own
scale. A mail list's scroll moves its child page in unscaled drawing pixels,
so the insert's scale multiplies the visible travel. The quilt's `to` is an
absolute parent y coordinate. The wall clock's `time` and inbox counts are
display content, not an advancing clock or fetched data. Inbox text requires
a bound font; the unlettered bedtime props do not.

Animation keys and opacity gates follow `Canvas.local_time`. Room `Shot`
records hold framings; light and dimming pools belong to the set root outside
the framed room. A bedside lamp only changes its own drawing—coordinate a
room's `Light` records separately to darken the surroundings. These pools
and the closet slit are authored overlays, not shared world lights.

Door records use the Soft room projection: `a0` and `a1` run along its back
wall, and `up` is height above its floor. The `between` callback receives a
group in projected frame coordinates, after the dark openings and before
the door leaves. Nonempty shut intervals form a union; open drawings appear
in the gaps up to `end`. Empty shut intervals keep the default door closed.
The handshake insert and tipping mop draw their own motion; neither creates
biomechanical constraints or a world-space contact anchor.

## Soft props, appliances and effects

The 32 registered builders in `soft_props` and `soft_odds` declare their
drawing origins, units, timed records and callback ownership. Each returns
a group. Most place a local drawing at parent-pixel `x`/`y` and scale its
geometry and child motion together. The bench, parcel stack and time card
instead bake parent coordinates into their geometry. The glare lamp scales
its body while keeping `reach` as an independent parent-pixel radius.

Inspect schedule vocabularies before constructing them. Washer `loads` take
`brick`, `ball`, `coins` or `shovel`; smoke and grill flame rows start at zero
and use levels 0..3. `BadgeState` and `TimeState` separate literal display
copy from their visibility spans. Their text needs a bound font. The phone's
`screen` and beach call's `guest` receive an existing group once; their return
values are ignored and their drawings are not clipped to the suggested box.

<!-- soft-prop-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, soft_odds

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=6)
cv = Canvas(scene, font_asset=None)
cv.local_time = True

washer = registry.get('prop', 'soft-washer').describe()['contract']
load = washer['arguments']['properties']['loads']['items']['prefixItems']
assert load[0]['x-timebase'] == 'canvas'
assert 'brick' in load[1]['enum']

machine = soft_odds.washer(
    cv, cv.comp, x=540, y=1600, scale=1.2, end=6, stop=4,
    open_at=((1, 5), (2, 3)), loads=((1, 'brick'),),
)
# Hide the complete machine at the end; its own end limits selected effects.
cv.gate(machine, ((0, 6),))
assert machine.id == 'soft-washer'
```
<!-- soft-prop-discovery:end -->

Overlapping washer door intervals form a union: the nested interval above
does not close the door early. The drum rotates linearly until `stop`, then
holds; loads ride in its group. `end` limits door and load visibility, while
the machine body remains. TV and fridge `off` times extinguish their picture
or indicator, and the grill's `end` limits flame and char overlays. Use a
caller-owned gate when the entire object must disappear.

Motion styles are explicit. Tongs snap between held angles, rumble lines
shake in held steps, smoke loops interpolate linearly, and dust specks fall
once and hold their final positions. A cake turn squeezes its flat drawing
and swaps the lettering at the narrowest point. Its candle and the beach's
sea and palm use renderer expressions; `Canvas.local_time` selects keyframe
clocks without rewriting those expressions. These illustrations provide no
grip, collision, fluid, lighting or biomechanical solver. The hush finger
draws an extra forearm and finger, so authors must coordinate it with the rig.

## Blob furniture, room layouts and placement helpers

Blob's 12 registered furniture and room builders use the Soft fixed
1080x1920 layout. Their returned groups contain already-positioned artwork.
Transform a shared parent to move the room and its occupants together.
The laptop is an exception within that layout: its root already translates
and scales laptop-local geometry. `blob.keyboard()` returns the deck corners
after that built-in transform; applying it again misplaces the hands.

Discovery now includes the existing placement helpers as operations:
`keyboard`, `sofa_seat`, `swivel_seat`, `meeting_table_top`, `meeting_screen`,
`room_point`, `wall_quad` and `floor_quad`, on the parts that use them. These
return reference geometry without drawing. They can guide placement and
framing, but they do not create world anchors, collisions or solved contacts.

`shots` on these four room builders means visibility intervals, unlike the
`Shot` framing records used by `soft_sets`. `None` leaves a room visible;
an empty sequence hides it. The opacity gates follow `Canvas.local_time`.
The home forwards `on_sofa` to the sofa group, between its seat and near arm,
so the near arm supplies the foreground occlusion. The callback still owns
the actor's placement and scale.

<!-- blob-drawing-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, blob, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='30', duration=6)
cv = Canvas(scene, font_asset=None)
contract = registry.get('location', 'soft-meeting-room').describe()['contract']
assert contract['arguments']['properties']['on_screen']['x-space'] == 'screen-local'
assert contract['operations']['meeting_screen']['returns']['x-role'] == 'screen-frame'

_, width, height, _ = blob.meeting_screen()

def screen(parent):
    # The room supplies translation, wall skew and a rectangular mask.
    cv.rect(parent, 0, 0, width, height, '#336699')
    cv.ellipse(parent, width / 2 - 30, height / 2 - 30, 60, 60, '#FFFFFF')

room = blob.meeting_room(
    cv, cv.comp, shots=((1, 3), (4, 6)), on_screen=screen, chair=False,
)
assert room.id == 'soft-meeting-room'
```
<!-- blob-drawing-discovery:end -->

The meeting screen slot overlays its default slide in a separate masked
group. Draw its contents in the flat local rectangle; the room applies the
wall skew once. The other furniture, window light patches, clock, coffee
steam and pendant glaze are static drawings. The home's `lamp_talk` toggles
a drawn shade and halo in ordered spans, without changing shared lighting.

## Ink shots and illustrated interfaces

The 19 non-character builders in the Ink family declare their coordinates,
clocks, returns and interface records. Ink uses a fixed square 1080x1080
layout. Event times are authored from the beginning of a take, but builders
emit them on the clock selected by `Canvas.local_time`. Set it to `True`
for sequence shots. Changing `Take.start` alone does not offset animations,
and a timed group is not a substitute for a sequence shot's clock.

Return ownership varies. `ink-desk` draws into its parent and returns
`None`; the desk, wide and router-wide shot builders return that parent.
The router, phone, kerb, doorstep and vacuum shot builders return only the
featured object, leaving surrounding scenery outside it. The doorbell view
returns its lens overlay while the human remains a sibling. Use a dedicated
parent when moving or hiding an entire shot.

<!-- ink-drawing-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, ink, registry
from srstudio.timeline import Take

scene = Scene(version='auto')
scene.add_project(width=1080, height=1080, fps='24', duration=6)
cv = Canvas(scene, font_asset=None, local_time=True)
sequence = cv.comp.add_sequence(id='shots')
sequence.add_group(id='lead', end=2)
shot = sequence.add_group(id='router-shot', end=4)
whole = cv.group(shot, 'whole-shot')
take = Take('02', 'router', 'router', '', start=2, duration=4)

contract = registry.get('location', 'ink-router-shot').describe()['contract']
assert contract['arguments']['properties']['hand_at']['x-timebase'] == 'canvas'
assert contract['returns']['x-role'] == 'drawing-group'

router = ink.router_shot(
    cv, whole, take, power='down', hand_action='press', hand_at=1,
)
cv.gate(whole, ((0, 4),))
assert router is not whole
```
<!-- ink-drawing-discovery:end -->

The phone, kerb, doorstep and vacuum wrappers forward keyword options.
Their discovery operations expose the actual `phone`, `meter`, `doorbell`
or `vacuum` function and its typed inputs. The wrapper's variadic envelope
remains explicitly open; use its documented subset of those inputs. In
particular, the wide kerb supplies meter `zoom` and `framed` itself.

`Bubble`, `AppRow` and map `Room` records distinguish display copy, event
times and drawing coordinates. Chat status waits for the last outgoing
bubble to appear; typing dots occupy an incoming reply's slot when possible.
App forms reject overflow before drawing: five rows fit alone, four with a
progress bar or stars, and three with both. Progress fills linearly; stars,
ticks, tags and captcha picks use held states. These are illustrated
interfaces, with no messaging, payment, navigation or verification service.
Text-bearing builders require a bound font asset.

Motion conventions matter across cuts. The kerb's negative `tow` time
continues the lift or departure from before the take; `view` maps the
pavement anchor to its new position and scale. The hand uses cubic easing
and parent-pixel displacements independent of its drawing scale. The vacuum
instead multiplies its travel by scale. None creates a physical grip or
contact constraint, and the floor map's fixed route does not adapt to custom
room geometry.

## Collage table and corner props

The 16 builders in `collage_things` declare their return ownership, drawing
origins, sizes, copy and animation clocks. Most return a group translated
to `x/y` in the parent. That origin may be a center, foot, handle end or
top: inspect the constraints before aligning a prop with a hand or surface.
The stool's origin is a seat reference, not a fitted contact point.
`collage-counter`, `collage-ring-corner` and `collage-eye-twitch` instead bake
coordinates into their drawings and return an untranslated group. The
counter uses the fixed 1080x1920 layout.

<!-- collage-thing-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, collage_things, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=6)
cv = Canvas(scene, font_asset=None, local_time=True)
sequence = cv.comp.add_sequence(id='shots')
sequence.add_group(id='lead', end=2)
shot = sequence.add_group(id='paper-shot', end=4)

contract = registry.get('prop', 'collage-resume').describe()['contract']
assert contract['arguments']['properties']['turn']['x-timebase'] == 'composition'
assert contract['returns']['x-anchors']['origin'] == [0, 0]
paper = collage_things.resume(cv, shot, 540, 900, w=500, turn=3)
# The sheet turns one second into this shot: turn uses project seconds.
# Its heading is drawn in paths, so this example needs no font asset.
cv.gate(paper, ((0, 4),), local=True)
assert cv.local_time is True
```
<!-- collage-thing-discovery:end -->

The resume's scale and face change share project time. Its 0.3-second turn
is a linear squeeze to a thin sliver and back, with the blank back revealed
at the midpoint. Eye-twitch cues also use project time: each closes the eye
for 0.09 seconds, and overlapping or touching cues keep it closed until the
last cue ends. The eyelid overlays a held face in that figure's coordinates;
it does not track a moving head. Parent it with the figure to share placement.

Other props are static. Use caller-owned animation to move them; `torn`
selects a receipt silhouette and `off_hook` omits a handset. Draw a separate
`collage-handset` for a receiver held elsewhere. The gravy boat accepts zero
through five forks; the wallet accepts at most two card colors and retains
an empty third slot. None supplies a physical grip or contact solver.

Readout copy is literal. A nonempty desk-phone display or till readout needs
an explicit positive lettering `size` and a bound font; discovery separates
that size from prop dimensions. Text is not automatically fitted. Bank-card
names likewise need a font, while the resume and receipt use drawn paths.

## Everyday Collage props and sampled reaches

The 22 `collage_everyday` builders declare their placement, sizes, copy,
clocks and return ownership. Food, chips, thumbs, the shaker, magnifying
glass and lasagna scale reference drawings; their size arguments are not
exact silhouette bounds. Other props use literal dimensions. A cereal box,
certificate or snapshot takes its top-left as placement input but returns
a group centered on the drawing for rotation.

The phone and battery insert return only the inner screen group, with its
origin 26 pixels inside the frame. Adding screen content does not clip it,
and moving that return leaves the frame behind. Keep a caller-owned parent
when moving the whole phone. The bubble, clock, bag and bill display literal
copy; most do not fit-check it. The flip card checks all side copy and times
before drawing, using estimated glyph widths rather than font measurement.

Clocks differ by builder. Flip-card turns and sampled reaches use project
seconds regardless of `Canvas.local_time`. Router light/unplug cues and
battery level/death cues use the Canvas clock. Gust and confetti have project
keyframes plus lifetime groups on the containing timeline: place them in a
project-aligned parent. They do not convert cue times for a later sequence
shot. Confetti is seeded and deterministic; its reversal is a linear change
of direction, not a gravity simulation.

`collage-arm` also exposes the actual `shoulder`, `reach`, `eased`, `frames`
and `chew` helpers as discovery operations. These are available directly
from `collage_everyday`; discovery does not create a second calling API.

<!-- collage-everyday-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, collage_everyday as paper, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=3)
cv = Canvas(scene, font_asset=None)
whole_arm = cv.group(cv.comp, 'whole-arm')
operations = registry.get('prop', 'collage-arm').describe()['contract']['operations']
assert operations['reach']['arguments']['properties']['hand']['x-role'] == 'sampled-hand-position'

shoulder = paper.shoulder('deb', side=1)
times = paper.frames((0, 2), step=1 / 24)
def hand_at(t):
    return paper.eased(((0, 400), (2, 700)), t, 'sine-in-out'), 900

holder = paper.reach(cv, whole_arm, 'deb', shoulder, hand_at, times, side=1)
paper.chip(cv, holder, 0, 0, size=80)
assert holder is not whole_arm
```
<!-- collage-everyday-discovery:end -->

`shoulder()` is a reference in the fixed single-figure layout. Transform it
with the figure when using another placement. `reach()` calls the position
callback once per supplied time and returns an unmirrored hand holder, so a
child prop shares hand translation without inheriting the hand artwork's
mirror. Its sleeve pivot is a sibling; move or gate the common parent to
affect the whole arm. Supply `side=-1` or `side=1` explicitly. Omitting it
retains legacy artwork but records an anatomy fault for a drawn hand.

This reach has one rotating, stretching sleeve segment. It does not solve
an elbow, grip or body constraint. Sleeve angle, length and hand translation
interpolate independently, so their meeting is authored at sample times;
choose sufficiently dense samples and inspect the result. `frames()` takes
a finite positive time step, while `eased()` samples ordered scalar keys
with its two supported easings. `chew()` replaces viseme keys inside a span
on a 0.12-second grid and preserves keys outside it.


## Collage rooms, photographs and illustrated interfaces

The 33 builders in `collage_sets`, `collage_odds`, `collage_photo`,
`collage_article` and `collage_forecast` declare placement, clocks and return
ownership. The 13 rooms use fixed 1080×1920 furniture layouts. Each returns
one whole group with a softened, slightly overscanned backdrop and a sharp
signature shelf. Their lights, clocks and newsroom globe are static drawings.
Add actors separately. Room contracts expose the actual `signature_box`,
`marks_box` and `zoom_pivot` helpers; the last computes a pivot that preserves
12-pixel signature margins under a uniform zoom, without emitting a camera.

<!-- collage-context-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, collage_photo, registry
from srstudio.collage_group import Place

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=4)
cv = Canvas(scene, font_asset=None)
room = registry.get('location', 'collage-living-room')
operations = {op.name: op.builder for op in room.contract.operations}
pivot = operations['zoom_pivot']('living-room', (540, 1100), 1.4)
assert len(pivot) == 2

photo = collage_photo.print_photo(
    cv, cv.comp,
    places={'gary': Place(540, 1800, 0.6)},
    poses={'gary': ('wide', 'grin', 'shrug')},
    x=90, y=600, width=900, blur=('gary',),
)
record = registry.get('prop', 'collage-photo-print').describe()['contract']
assert record['arguments']['properties']['places']['additionalProperties'][
    'x-python-type'
] == 'srstudio.collage_group.Place'
assert photo is not cv.comp
```
<!-- collage-context-discovery:end -->

A photo print composes a static room, posed figures and a foreground sofa
inside a crop mask, then adds its border and gloss. `Place` supplies each
figure's fixed-layout position and positive scale. Pose keys must match place
keys. Blur names select actors; their blur radius compensates for figure
scale before the entire photo is scaled. The returned group is the whole
print, positioned and rotated at its top-left. Its `width` describes the
image, excluding the border. This is a drawing assembled from poses, not a
capture of another scene's current animation.

Cake cuts, doctor-scale drops, weather-map slides and message-thread cues
use composition seconds even when `Canvas.local_time` is enabled. Sensor-tap
water, timer digits, viewfinder countdowns and flash fades use the Canvas
clock. A timer's first digit is visible before its start cue; viewfinder
brackets remain after its countdown. Eye-chart lifetime groups and gates
require a project-aligned parent with `local_time=False`. These are authored
visibility and transform changes, without a physical simulation.

Article and thread builders return a wrapper containing the whole phone.
Their contents are illustrations: body-copy bars, a landscape placeholder,
and message bubbles. They do not fetch articles or send messages. Article
headlines and thread messages preflight estimated text fit; this is not a
promise to fit every field, including sender and contact copy. Read their
constraints before choosing dimensions. Chart bars, the TV and call buttons
are likewise static drawings. Glass and jug geometry keeps parent-space
coordinates even though their root transform scales around an authored base;
do not treat that base as a new local origin.


## Rafa models and surface preparation

Rafa's five props and two rooms take a mutable `clay.Model`, append static
triangles and return `None`. Their coordinates use Rafa's centimetre-like
model units, with y down and z away from the lens. They do not return a
Canvas group, render a plate or author motion. Material meshes are obtained
from `model.meshes()`; place those meshes through the plate API when composing
a scene. Body geometry, faces, recurring props and room foreground dressing
are separate calls.

Each contract exposes the existing `rafa.finished(mesh)` helper. It preserves
geometry and adds planar UVs for the authored surface normal map when needed.
Printed surfaces retain their UVs. Material names resolve through
`rafa.MATERIALS` or `rafa.materials()`; the latter also prepares painted head
skin. In-world lettering is a `rafa.PRINTS` recipe referenced by its material,
so rendering still requires the plate pipeline's font resources.

<!-- rafa-model-discovery:start -->
```python
from srstudio import clay, rafa, registry

part = registry.get('prop', 'rafa-mug')
contract = part.describe()['contract']
assert contract['returns']['type'] == 'null'
assert contract['capabilities']['animation'] is False
model = clay.Model()
with model.at(20, -240, -180):
    assert part.builder(model) is None
finish = next(op.builder for op in part.contract.operations if op.name == 'finished')
meshes = tuple(finish(mesh) for mesh in model.meshes())
materials = {mesh.material: rafa.MATERIALS[mesh.material] for mesh in meshes}
assert materials['mug-label'].print is rafa.PRINTS['mug-label']
assert all(mesh.uvs is not None for mesh in meshes if materials[mesh.material].normal_map)
```
<!-- rafa-model-discovery:end -->

A prop's geometry follows its active `Model.at` frame. Build rooms in the
identity frame and transform their completed meshes for whole-room placement:
room plant helpers enter absolute frames, so an outer `Model.at` does not move
all room geometry together. The fridge, clock hands, mug coffee and phone
readout are held shapes or printed copy. No grip, support, liquid or appliance
behavior is supplied by these builders.


## Gloss rooms, cards and graphics

Gloss's eight scenery builders declare Canvas clocks and their actual return
ownership. The three rooms append scenery and return `None`; wrap a room in a
caller-owned group when moving or gating it. A board returns one group per
card. Door, ticket, hook and notice return their whole drawing group. Room,
board and graphic coordinates use the fixed 1080×1920 layout; door and ticket
geometry has a local origin at the requested placement.

<!-- gloss-set-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, gloss_sets, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=4)
cv = Canvas(scene, font_asset=None, local_time=True)
room_parent = cv.group(cv.comp, 'waiting-room')
room = registry.get('location', 'gloss-waiting')
assert room.describe()['contract']['returns']['type'] == 'null'
assert room.builder(cv, room_parent, end=4, serving=((0, '3'), (2, '4'))) is None
cv.gate(room_parent, ((0, 4),))
door = gloss_sets.door(cv, room_parent, at=(540, 1200), end=4, opens=(1, 2))
assert door is not room_parent
card = registry.get('prop', 'gloss-board').describe()['contract']
assert card['arguments']['properties']['cards']['items']['properties']['start'][
    'x-timebase'
] == 'canvas'
```
<!-- gloss-set-discovery:end -->

Keys and visibility gates follow `Canvas.local_time`. Use local time for cues
relative to a later sequence shot. `end` bounds cues but does not universally
clip the returned drawing: gate the containing group when it should vanish.
Door leaves use cubic-out horizontal foreshortening over 0.35 seconds. Card
and badge pops use linear overshoot keys. A first card with `carried=True`
starts at zero, skips the pops and retains its words at a cut.

Board, hook and notice contracts expose the actual `gloss_sets.wrap` helper.
Supply font bytes matching the bound Canvas font. Every board title/body and
its height are preflighted before emission, including later cards. Headings
and numeric badges have no separate width-fit check. Room displays and tickets
use seven-segment paths without fonts; ticket numerals are not fitted for
arbitrarily long strings.

The notice grades its backdrop separately, leaving its card crisp. Its body
uses the native `typewriter` text preset, whose start and duration are stated
in the contract; this is distinct from the Canvas key tracks controlling its
word gate and Sunny's motion. The notice adds a signature code but no cactus.
The graphic returns the whole composition, without a separate host handle.

## Saga scenery and sampled console contact

Saga's sixteen scenery, prop and graphic contracts distinguish room mutation
from returned groups. The eight location layers and the cube return `None`;
use a caller-owned group to move or gate them together. Holograms return one
group per panel. Ships, the pebble, the Handbook and the two graphics return
their whole drawing group. Room and graphic geometry uses the fixed
1080×1920 layout. Ships, the pebble and the Handbook have local geometry at
their placement; cube coordinates are baked into its paths.

<!-- saga-set-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, registry, saga_sets

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=6)
cv = Canvas(scene, font_asset=None, local_time=True)
sequence = cv.comp.add_sequence(id='shots')
sequence.add_group(id='lead', end=2)
shot = sequence.add_group(id='cockpit-shot', end=4)
room = cv.group(shot, 'room')
saga_sets.cockpit(cv, room, end=4, jump=((0.5, 1.5),))
# Draw pilots here, before the foreground console.
console = registry.get('location', 'saga-cockpit-console')
jab = saga_sets.Jab(1, '#efe2c4', '#925934', (404, 1040), 1.55)
assert console.builder(cv, room, end=4, jab=jab) is None
cv.gate(room, ((0, 4),))
operations = {op.name: op.builder for op in console.contract.operations}
hand_at = operations['hand_at']
stick_grip = operations['stick_grip']
jab_frames = operations['jab_frames']
assert hand_at(jab, 0) == stick_grip(0)
assert len(jab_frames(jab, 4)) == 97
assert console.describe()['contract']['capabilities']['spatial_attachment'] is False
```
<!-- saga-set-discovery:end -->

Keys and visibility gates follow `Canvas.local_time`; enabling it makes cues
relative to the later sequence shot. `end` does not universally clip emitted
animation. Compactor walls retain their supplied stop time, even beyond
`end`; `start_px` can carry their displacement across a cut. Door motion can
also finish after `end`. Static ships, the desert and the bar validate `end`
without adding motion. Call `saga_sets.finish` explicitly for shot grading.

Console inspection exposes the actual `stick_ball`, `stick_grip`, `hand_at`
and `jab_frames` helpers. Positions use fixed-layout coordinates before caller
transforms. The console shares bounded 24 Hz samples between stick rotation
and the hand/forearm drawing, with at most 20,000 samples including the terminal
sample. The arm is one stretching forearm from a fixed elbow. Its independent
interpolation tracks do not guarantee exact contact between sample times or
provide whole-body support, articulation or collision handling.

Hologram, hook and entry contracts expose the actual `wrap` helper. Supply
font bytes matching the bound Canvas font. All hologram title/body layouts
are measured before drawing, including later panels. A panel's `fade=True`
uses opacity instead of the first panel's vertical pop and the nonfade
flicker. Hologram `face` draws a small complete cast member, without a head
crop or speech track. The entry's body uses the engine's native typewriter
preset; the contract states its start and duration separately from Canvas
keys. Its screen ignores a speech state at zero and responds to later states;
the small Handbook follows its initial speech state as well.

## Measured rooms, call props, signatures and wire vehicles

Every default catalog entry now has an authored contract. The contract still
distinguishes a projected anchor from a scene attachment, and measured
keyframes from a continuous physical constraint.

<!-- remaining-parts-discovery:start -->
```python
from sr_core.scene import Scene
from srstudio import Canvas, cel, registry

scene = Scene(version='auto')
scene.add_project(width=1080, height=1920, fps='24', duration=4)
cv = Canvas(scene, font_asset=None)
camera = cel.parse_camera([
    dict(time=0, scale=1, tx=0, ty=0),
    dict(time=1, scale=1.2, tx=-20, ty=-30),
])
world = cel.world(cv, cv.comp, camera, 4)
room = registry.get('location', 'cel-room')
assert room.builder(cv, world, camera, camera, 4) is not None
vehicle = registry.get('prop', 'wire-car')
helpers = {op.name: op.builder for op in vehicle.contract.operations}
anchor = helpers['anchor']
head = anchor('driver-head', at=(540, 960), width=200, seed='contract')
assert head.scale > 0
assert vehicle.describe()['contract']['capabilities']['spatial_attachment'] is False
```
<!-- remaining-parts-discovery:end -->

Cel camera keys always use local time, regardless of `Canvas.local_time`.
Draw a room under `cel.world` with the same world samples, and supply its own
measured room samples. Compensation agrees at those sample times; interpolating
the world and compensated tracks independently can differ between samples.
Use the parsers for external camera and caption data. Cel captions draw their
supplied glyph paths and boxes; transcript strings are not font-layout input.
Caption lifetimes use offsets from their parent.

The call tile gives its `inside` callback the returned local group before
drawing the foreground frame. That frame covers surrounding rectangles; it
is not a clipping mask. Lettered tiles require a font before the callback runs.
Phone line reveals use parent-local group starts. Phone shake and turnover
keys follow `Canvas.local_time`, so their clocks differ when local time is
disabled beneath a later shot. The apron and trial tag are static drawings;
their names do not imply cloth simulation or solved attachment.

Phone buzzes are preflighted before drawing, with a 20,000-key budget shared
across all spans, including the initial key and each return to rest. Buzz
sample times must advance, and turnover phase times must remain distinct;
extreme timestamps that lose those distinctions raise `CutoutCallError`.

Signature code and cactus return `None` on unsigned canvases. An acting cactus
requires a signature and uses Canvas-clock flower turns, bloom gates and scale
pops. The show bug returns its complete fixed-layout group; a direct call
inherits its parent transform, so place it on the composition for a stationary
overlay. These marks use built-in paths without fonts.

Wire cars and jets return static projected stroke groups. Their contracts
expose the existing `anchor`, `plate` and `edge` helpers. Match projection
arguments between calls: anchor results give parent-space pixels and pixels
per metre, plates give PNG bytes plus their top-left placement, and edges give
a row and slope for foreground/background band cuts. Plates require light and
currently support the `night` palette. Installing the image asset remains the
caller's responsibility. Unfilled stroke groups do not hide content behind
the vehicle. Car `spin` and jet `sweep` select a held geometry state; animation
requires authored motion or sampled drawings.
