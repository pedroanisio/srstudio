"""Authored traffic, dining, parlour and lit-room contracts; no builder imports or inferred semantics."""

from collections.abc import Sequence
from dataclasses import replace
from typing import Annotated, Any, Literal, TypedDict

from sr_core.scene import Composition, Group, Symbol

from ._toon_contracts import COMP_TIME, DURATION, FONT, PARENT_START, REF, TIME, draw, point
from ._toon_domestic_contracts import ID, SCALE
from ._toon_household_contracts import group
from .contracts import ParameterContract as P
from .contracts import PartContract

State = Literal['on', 'off', 'flicker', 'dim']
Colour = Literal['blue', 'white', 'red', 'green', 'amber', 'purple']
CueTime = Annotated[float, TIME]
MainCue = tuple[CueTime, State] | tuple[CueTime, State, None]
ScreenCue = tuple[CueTime, State] | tuple[CueTime, State, Colour | None]
DishKind = Literal['salad', 'water', 'lobster', 'shells', 'wine', 'glass', 'empty', 'check']
DishX = Annotated[float, P(unit='reference pixels', space='toon-reference', minimum=0, maximum=592)]
Dish = tuple[DishKind, DishX] | tuple[DishKind, DishX, CueTime]
Ticket = Annotated[str, P(description='One capital letter followed by one to three digits, such as A17.')]


class LoungeLights(TypedDict, total=False):
    lamp: Sequence[MainCue]
    tv: Sequence[ScreenCue]


class CounterLights(TypedDict, total=False):
    tubes: Sequence[MainCue]
    board: Sequence[ScreenCue]


CUE_FIELDS = P(
    fields=(
        ('at', TIME),
        ('state', P(enum=('on', 'off', 'flicker', 'dim'))),
        ('colour', P(enum=('blue', 'white', 'red', 'green', 'amber', 'purple', None))),
    )
)
PAINT = P(description='A #rrggbb paint color.')
AUTO_ID = P(role='scene-id', description='Caller-unique scene group ID; None or an empty string generates an ID.')
LIMIT = P(unit='seconds', timebase='canvas', role='animation-limit', minimum=0)
PASSING = P(
    items=P(
        fields=(
            ('at', P(unit='seconds', timebase='composition', role='crossing-time', minimum=0)),
            ('kind', P(enum=('car', 'bus'))),
            ('colour', PAINT),
        )
    )
)
TRAFFIC = (
    'Passing.at is when the vehicle center crosses the frame center; the records need not be ordered.',
    'Vehicles move right to left at 900 reference pixels per second; bus color is fixed, car color is configurable.',
    'Each vehicle gets parent visibility around its crossing time and linear composition-clock translation.',
)
SCALED_AT = 'Geometry scales about at using a group whose position and anchor are both the converted point.'
CONE_RULES = (
    'at is the cone tip, not its center. Python requires a tuple of two finite reference coordinates.',
    'Scale is baked into geometry about at; the returned root has no placement transform or local grip frame.',
)
ROOM_RULES = (
    'lights=None or omitted keys use room defaults. Cues are nonempty, strictly rising from zero.',
    'A screen first cue must name a color; later omitted/None colors preserve it. Main-light color must be None.',
    'end=0 requires one cue at zero per light and draws a still; positive cues must be strictly before end.',
    'on/off hold 1/0. dim fades to 0.35 over 1.5 seconds; the next cue cannot interrupt it, but end can clip it.',
    'An initial dim holds 0.35. flicker uses a held 1.3-second cycle. Final levels remain after end.',
    'light=None creates an overlay after the background. Supply a separate light group between actors and desk.',
    'end bounds keys, not visibility; use caller-owned parents for complete scene visibility.',
)
LIGHT_LAYER = P(
    type=Composition | Group | Symbol | None,
    role='light-layer',
    description='Existing drawing parent for shade and glows, not a callback. None creates a sibling overlay group.',
)

_CONTRACTS = {
    'toon-side-car': draw(
        ('at', point('Vehicle ground point.')),
        ('colour', PAINT),
        ('scale', SCALE),
        ('id', AUTO_ID),
        ('wheels', P(items=P(enum=('front', 'rear')))),
        constraints=(SCALED_AT, 'Wheel names must be distinct; an empty tuple omits both wheels. Static side view.'),
    ),
    'toon-loose-wheel': draw(
        ('at', point('Ground point of the matching parked side car, not the wheel center.')),
        ('start', COMP_TIME),
        ('to', REF),
        ('seconds', DURATION),
        ('scale', SCALE),
        ('id', AUTO_ID),
        clock='composition',
        constraints=(
            'start>=0, seconds>0, finite at/to and positive scale; converted radius must remain positive.',
            'Computed geometry, rotation and end time must be finite; invalid plans fail before drawing.',
            'Wheel center begins at at-(96*scale,28*scale); radius is 30*scale reference pixels.',
            'x and rotation interpolate linearly from start to start+seconds, then hold; no visibility end.',
            'Rotation in radians times the converted radius equals travel in frame pixels, up to key rounding.',
        ),
    ),
    'toon-school-bus': draw(
        ('at', point('Vehicle ground point.')), ('scale', SCALE), ('id', AUTO_ID), constraints=(SCALED_AT,)
    ),
    'toon-banana': draw(
        ('at', point('Banana ground point.')), ('scale', SCALE), ('id', AUTO_ID), constraints=(SCALED_AT,)
    ),
    'toon-car-inside': draw(
        ('start', P(unit='seconds', timebase='canvas', role='animation-start')),
        ('end', LIMIT),
        ('passing', PASSING),
        ('body', PAINT),
        clock='mixed',
        constraints=(
            *TRAFFIC,
            '0<=start<end bounds scrolling road animation, not the car body visibility.',
            'Passing spans are independent of start/end; traffic uses scale 1.5 at reference ground y=770.',
            'Window border covers the road edges; no clipping or collision region is returned.',
        ),
    ),
    'toon-car-seat': draw(('x', REF), ('colour', PAINT), constraints=('x is the seat center; draw behind the cast.',)),
    'toon-dash-vents': draw(
        constraints=('Static front-panel detail; draw over a dash ledge, which carries signatures.',)
    ),
    'toon-steering-wheel': draw(
        ('at', point('Wheel center.')),
        ('radius', P(unit='reference pixels', description='Finite and strictly positive.')),
        constraints=('Static front view; draw the dashboard afterward to hide its lower edge.',),
    ),
    'toon-tally-pad': draw(
        ('at', point('Pad top-left corner.')),
        ('count', P(minimum=0, maximum=30)),
        ('strokes', P(items=PARENT_START)),
        ('scale', SCALE),
        ('id', ID),
        constraints=(
            SCALED_AT,
            'count+len(strokes)<=30; nonnegative nondecreasing times permit simultaneous strokes.',
            'Initial count is always present. Each new stroke uses parent visibility from its cue onward.',
        ),
    ),
    'toon-restaurant': draw(
        (
            'special',
            P(
                prefix_items=(
                    P(description='Nonblank dish name, at most 12 characters.'),
                    P(description='Nonblank price, at most two lines of eight characters.'),
                )
            ),
        ),
        constraints=(FONT, 'lettering=False omits board text but still validates special. Draw table separately.'),
    ),
    'toon-table': draw(constraints=('Foreground table replaces the desk, with a dish surface at reference y=826.',)),
    'toon-dishes': draw(
        ('items', P(type=Sequence[Dish])),
        ('id', P(role='scene-id-prefix')),
        constraints=(
            'Rows draw in order; omitted at means zero. Nonnegative at reveals by held canvas opacity without an end.',
            'Dish bases stand at reference y=826, scaled by 1.5. Names are id-kind, id-kind-2, and so on.',
        ),
    ),
    'toon-mint': draw(
        ('at', point('Saucer base.')),
        ('scale', SCALE),
        ('start', P(unit='seconds', timebase='canvas', minimum=0)),
        ('id', ID),
        constraints=('Held opacity reveals at start; no visibility end. eaten draws only the empty wrapper.',),
    ),
    'toon-card-reader': draw(
        (
            'states',
            P(
                items=P(
                    prefix_items=(
                        TIME,
                        P(description='Nonblank text, at most ten characters.'),
                        P(enum=('idle', 'bad', 'good')),
                    )
                )
            ),
        ),
        ('at', point('Reader base.')),
        ('id', ID),
        constraints=(
            FONT,
            'Nonempty states rise strictly from zero. Held canvas opacity shows one screen at a time.',
            'The final screen remains indefinitely. Reader geometry scales by 0.75.',
        ),
    ),
    'toon-cone': group(
        ('at', point('Cone tip.')), ('flavour', P(enum=('vanilla', 'mint'))), ('scale', SCALE), constraints=CONE_RULES
    ),
    'toon-toothpaste-cone': group(('at', point('Cone tip.')), ('scale', SCALE), constraints=CONE_RULES),
    'toon-parlour-case': group(('top', REF), constraints=('top is the glass-case upper edge; draw after the ledge.',)),
    'toon-parlour-front': draw(
        ('start', P(unit='seconds', role='validation-limit')),
        ('end', P(unit='seconds', role='validation-limit')),
        ('passing', PASSING),
        ('scale', SCALE),
        clock='composition',
        constraints=(
            *TRAFFIC,
            '0<=start<end is validated but sets no animation or visibility bounds. The street itself is static.',
            'scale applies only to passing vehicles at reference ground y=670; no vehicles means scale is unused.',
        ),
    ),
    'toon-parlour-back': draw(constraints=('Static shelves and picture board with no lettering or signatures.',)),
    'toon-lounge': draw(
        ('lights', P(type=LoungeLights | None)),
        ('end', LIMIT),
        ('light', LIGHT_LAYER),
        ('speaker', P(items=P(prefix_items=(COMP_TIME, P(enum=('off', 'listen', 'think', 'speak', 'error')))))),
        ('blink_from', TIME),
        (
            'bare',
            P(
                type=Sequence[str],
                items=P(enum=('tv', 'lamp', 'shelf', 'console')),
                description='Omission names; the Python builder also accepts other collections.',
            ),
        ),
        clock='mixed',
        constraints=(
            *ROOM_RULES,
            'Default lights: lamp on, TV on blue. Speaker ring keys explicitly use composition time.',
            'Speaker cues rise from zero; end=0 requires one state at zero. blink=False only stops router LEDs.',
            'blink_from=0 starts immediately; otherwise 0<blink_from<end. It does not delay other light/speaker cues.',
            'bare removes fixtures; removing lamp keeps its lighting contribution. Removing TV removes its glow.',
        ),
    ),
    'toon-counter': draw(
        ('lights', P(type=CounterLights | None)),
        ('end', LIMIT),
        ('light', LIGHT_LAYER),
        ('serving', P(type=Sequence[tuple[CueTime, Ticket]])),
        constraints=(
            *ROOM_RULES,
            FONT,
            'Default lights: tubes on, board on red. Serving tickets rise strictly from zero, with positive cues<end.',
            'lettering=False omits all sign/board text but still validates serving. Last ticket remains after end.',
        ),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


def room_contract(name: str, returns: Any) -> PartContract:
    """Bind the public Cue return type where it is defined, keeping drawing imports out of metadata."""
    return replace(
        _CONTRACTS[name],
        returns=P(
            type=returns,
            role='parsed-light-cues',
            description='Dictionary of light names to lists of toon_rooms.Cue records, not a scene handle.',
        ),
    )
