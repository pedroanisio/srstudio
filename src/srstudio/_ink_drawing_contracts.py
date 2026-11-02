"""Ink drawing discovery: take-relative authoring, Canvas clocks and returned drawing scope."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P
from .timeline import Take

TIME = P(unit='seconds', timebase='canvas')
SPAN = P(prefix_items=(TIME, TIME))
COPY = P(role='display-copy')
PIXEL = P(type=float, unit='drawing pixels', space='fixed-layout')
PARENT_PIXEL = P(type=float, unit='parent pixels', space='parent')
SCALE = P(type=float, unit='ratio')
BOOL = P(type=bool)
TAKE = P(
    type=Take,
    fields=(
        ('start', P(unit='seconds', timebase='composition')),
        ('duration', P(unit='seconds', role='duration')),
        ('speech_duration', P(unit='seconds', role='duration')),
    ),
)
GROUP = P(type=Group, role='drawing-group', unit='drawing pixels', space='fixed-layout')
LOCAL = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
PARENT = P(type=Composition | Group | Symbol, role='drawing-parent', unit='parent pixels', space='parent')
NONE = P(type=type(None))
CLOCK = (
    'Animation keys follow Canvas.local_time: composition by default, local when enabled. '
    'Author take events as seconds from the take start and enable local time in sequence shots. '
    'These builders do not subtract take.start or set the clock for you; duration bounds selected events '
    'but does not gate the whole drawing. Fixed gestures can extend beyond a short take.'
)
LAYOUT = 'Ink uses a fixed 1080x1080 layout; canvas resizing does not reflow the artwork.'
FONT = 'Text uses the bound Canvas font at fixed sizes; no font measurement callback is accepted.'
SIBLINGS = (
    'Only the featured group is returned; surrounding scenery is drawn in siblings, sometimes under a '
    'shared layout group. '
    'Transform or gate a caller-owned parent to move or hide the complete shot.'
)
HUMAN = (
    'The built-in human uses take.actor and phoneme timestamps for speech, take.mood for held arms/brows '
    'and short head motion, plus a blink. This is not an authored HeadPlan or an emotional blend.'
)
POSITION = (('x', PARENT_PIXEL), ('y', PARENT_PIXEL), ('scale', SCALE))


def drawing(*parameters: tuple[str, P], returns: P = GROUP, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=returns,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', returns is not NONE)),
        constraints=(LAYOUT, CLOCK, 'Draws 2D geometry; does not solve grips, contacts or biomechanics.', *constraints),
    )


def forwarded(target: str, names: str) -> P:
    return P(
        role='forwarded-keywords',
        description=f'Passed to {target}: {names}. See the named operation for '
        'its typed inputs; this variadic envelope remains open, not a closed keyword validator.',
    )


def contract(name: str, **delegates: Callable[..., Any]) -> PartContract:
    return replace(
        _CONTRACTS[name],
        operations=tuple(Operation(target, builder, _TARGETS[target]) for target, builder in delegates.items()),
    )


PHONE = drawing(
    ('contact', COPY),
    ('bubbles', P(items=P(fields=(('text', COPY), ('at', TIME))))),
    ('status', P(items=P(prefix_items=(TIME, P(enum=('sending', 'failed', 'sent', 'read')))))),
    ('typing', SPAN),
    constraints=(
        FONT,
        'Phone body is (270,250,540,800). Contact is nonblank and at most 16 characters; '
        'nonempty ordered bubbles have nonblank text of at most 60 characters and nonnegative arrival '
        'times. The complete chat must fit the glass before drawing.',
        'Status times increase strictly and apply beneath the last mine bubble. A status replaced '
        'before that bubble arrives is omitted. Typing dots pulse linearly within their start/end gate '
        'and occupy the first incoming reply slot at or after typing ends, otherwise the final slot. '
        'Nothing sends messages or retrieves delivery state.',
    ),
)

_TARGETS = {
    'phone': PHONE,
    'meter': drawing(
        ('take', TAKE),
        *POSITION,
        ('display', P(items=P(prefix_items=(TIME, COPY)))),
        ('zoom', SCALE),
        ('framed', P(prefix_items=(PARENT_PIXEL, PARENT_PIXEL))),
        returns=LOCAL,
        constraints=(
            FONT,
            'Origin is the meter head center x and top y; its post extends 500 drawing pixels. '
            'Nonempty display readings start at zero, increase strictly within duration, and contain '
            '1..12 characters. speaker selects which take.actor animates the lights and voice marks. '
            'zoom is the parent scale and framed is its visible x interval; too-small or clipped '
            'lettering becomes a pen scrawl.',
        ),
    ),
    'doorbell': drawing(
        ('take', TAKE),
        *POSITION,
        ('mark', P(prefix_items=(P(enum=('deny', 'allow')), TIME))),
        returns=LOCAL,
        constraints=(
            'Origin is the doorbell center. mark is (deny/allow,time) within duration. '
            'speaker matching take.actor enables held ring-light chases and linearly fading voice marks.',
        ),
    ),
    'vacuum': drawing(
        ('take', TAKE),
        *POSITION,
        ('state', P(enum=('still', 'roll', 'stop'))),
        ('display', COPY),
        returns=LOCAL,
        constraints=(
            FONT,
            'Origin is the top center. Display is absent or 1..5 nonblank characters. '
            'roll travels right by 700*scale parent pixels over duration using cubic-in. '
            'stop starts 500*scale pixels left, overshoots by 14*scale, then brakes to x over '
            'min(0.7,duration), using cubic-out. speaker matching take.actor activates ring lights.',
        ),
    ),
}

_CONTRACTS = {
    'ink-laptop': drawing(
        *POSITION,
        returns=LOCAL,
        constraints=(
            'Static laptop with origin at the local lid '
            'top-left reference. It does not attach to a desk or accept screen content.',
        ),
    ),
    'ink-desk': drawing(
        returns=NONE,
        constraints=(
            'Draws the desk slab directly into parent, at y=787..1040. '
            'Returns None; retain the parent to transform it.',
        ),
    ),
    'ink-hand': drawing(
        *POSITION,
        ('action', P(enum=('reach', 'press', 'leave'))),
        ('at', TIME),
        returns=replace(LOCAL, anchors=(('fingertip', (0, 0)),)),
        constraints=(
            'at must be positive. The fingertip reference is at the local origin; x/y is its '
            'target in the parent. Reach uses cubic-out from (x+300,y+180) to (x,y). Press moves '
            'by (-12,-6) at the cue and returns 0.14 seconds later, using cubic-out; leave moves '
            'by (320,200) with cubic-in. These displacements are parent pixels independent of '
            'hand scale. No button binding or force constraint is created.',
        ),
    ),
    'ink-desk-shot': drawing(
        ('take', TAKE),
        ('scale', SCALE),
        returns=PARENT,
        constraints=(
            HUMAN,
            'Returns the supplied parent. scale affects only the human at (67,390); '
            'the laptop, desk line and cactus keep their fixed layout positions.',
        ),
    ),
    'ink-closeup': drawing(
        ('take', TAKE),
        ('zoom', SCALE),
        ('gesture', BOOL),
        returns=LOCAL,
        constraints=(
            HUMAN,
            'Returns the human at (185,360); zoom scales that group and gesture selects '
            'the pointing arm unless scream mood overrides it.',
        ),
    ),
    'ink-printer-shot': drawing(
        ('take', TAKE),
        ('close', BOOL),
        ('fps', P(unit='samples/second')),
        returns=LOCAL,
        constraints=(
            'Returns the printer with its signed model plate. close changes its fixed placement '
            'and scale. take.actor=sfx enables sampled rotation and paper bobbing; fps controls '
            'that rotation sampling, not output frame rate. actor=printer enables voice marks.',
        ),
    ),
    'ink-wide': drawing(
        ('take', TAKE),
        ('fps', P(unit='samples/second')),
        returns=PARENT,
        constraints=(
            HUMAN,
            'Returns parent after drawing human, laptop, printer/model plate, desk and cactus. '
            'fps controls the printer rotation samples for sfx takes.',
        ),
    ),
    'ink-router-shot': drawing(
        ('take', TAKE),
        ('close', BOOL),
        ('power', P(enum=('on', 'off', 'down', 'up'))),
        ('drop_at', TIME),
        ('hand_action', P(enum=(None, 'reach', 'press', 'leave'))),
        ('hand_at', TIME),
        returns=LOCAL,
        constraints=(
            SIBLINGS,
            'Returns the router; shelf, cable and optional hand are siblings. '
            'close selects a fixed scale/position. Power changes held LED states and sine-in-out '
            'antenna motion; drop_at, when set, must be within duration. hand_at is positive; '
            'the optional hand is placed near the drawn power button, without a contact solver.',
        ),
    ),
    'ink-router-wide': drawing(
        ('take', TAKE),
        returns=PARENT,
        constraints=(
            HUMAN,
            'Returns parent after drawing human, laptop, desk, cactus and a router on its shelf. '
            'actor=router activates its speech lights and antenna motion.',
        ),
    ),
    'ink-phone': PHONE,
    'ink-phone-shot': drawing(
        ('contact', COPY),
        ('bubbles', P(items=P(fields=(('text', COPY), ('at', TIME))))),
        ('chat', forwarded('phone', 'status, typing')),
        constraints=(
            FONT,
            SIBLINGS,
            'Returns the phone; the desk line and cactus are siblings. '
            'phone has the complete chat layout and validation contract.',
        ),
    ),
    'ink-kerb': drawing(
        ('take', TAKE),
        ('tow', replace(TIME, role='tow-start')),
        ('view', P(prefix_items=(SCALE, PARENT_PIXEL, PARENT_PIXEL))),
        ('meter_kw', forwarded('meter', 'display, speaker; zoom/framed are supplied internally in the wide view')),
        returns=LOCAL,
        constraints=(
            FONT,
            HUMAN,
            SIBLINGS,
            'Returns only the meter. close draws the meter alone and forbids tow. '
            'Wide view is (positive scale,x,y), mapping the pavement anchor (0,880) to x/y. '
            'tow may be negative to continue across a cut, but must be before duration. The car '
            'lifts linearly by -15 degrees over 0.5 seconds, then truck/car travel right at 700 '
            'drawing pixels/second. Negative keys fold into their interpolated value at zero.',
        ),
    ),
    'ink-doorstep': drawing(
        ('take', TAKE),
        ('number', COPY),
        ('bell_kw', forwarded('doorbell', 'speaker, mark')),
        returns=LOCAL,
        constraints=(
            FONT,
            SIBLINGS,
            'Returns only the doorbell; siding, door, plaque, mat and cactus are siblings. '
            'number is nonblank and at most four characters. close changes fixed scenery and bell placement.',
        ),
    ),
    'ink-vacuum-shot': drawing(
        ('take', TAKE),
        ('vacuum_kw', forwarded('vacuum', 'speaker, state, display')),
        returns=LOCAL,
        constraints=(
            SIBLINGS,
            'Returns only the vacuum; floor, baseboard, outlet and dock are siblings. '
            'Normal placement is (540,830), scale 1.55; close uses (540,790), scale 2.3.',
        ),
    ),
    'ink-app-screen': drawing(
        ('take', TAKE),
        ('title', COPY),
        ('rows', P(items=P(fields=(('text', COPY), ('at', TIME), ('tick', TIME), ('taken', TIME))))),
        ('progress', SPAN),
        ('stars', replace(TIME, role='rating-reveal-start')),
        constraints=(
            FONT,
            'Fixed phone body (270,250,540,800). Nonblank title has at most 16 characters and '
            'row copy at most 24. Rows fit the glass: at most five alone, four with progress or stars, '
            'three with both. Overflow fails before drawing.',
            'Row arrival/tick/taken times are within duration; tick or taken must follow arrival '
            'and cannot both be supplied. Progress grows linearly over 0<=start<end<=duration. '
            'stars reveals five held fills at 0.12-second intervals; the last must fit duration. '
            'These display a form without submitting data or checking actual account state.',
        ),
    ),
    'ink-doorbell-view': drawing(
        ('take', TAKE),
        ('tags', P(items=P(prefix_items=(TIME, COPY)))),
        ('clock', COPY),
        constraints=(
            FONT,
            HUMAN,
            SIBLINGS,
            'Returns the lens/face-box overlay; the human is a sibling. '
            'Tags are nonempty, at most 10 characters, starting at zero and strictly increasing '
            'within duration. clock is literal copy of at most 12 characters, not an advancing clock. '
            'REC blinks in held half-second steps. The lens is a drawn surround, not a camera feed.',
        ),
    ),
    'ink-floor-map': drawing(
        ('take', TAKE),
        ('rooms', P(items=P(fields=(('label', COPY), ('x', PIXEL), ('y', PIXEL), ('w', PIXEL), ('h', PIXEL))))),
        ('trace', SPAN),
        ('relabel', P(prefix_items=(P(role='room-label-reference'), COPY, TIME))),
        constraints=(
            FONT,
            'Rooms are nonempty and have unique nonblank labels of at most 12 characters. '
            'Coordinates are literal frame positions; no automatic layout is solved. relabel names '
            'an existing room and swaps its label/fill at a time within duration.',
            'trace reveals 24 dots along a fixed route over 0<=start<end<=duration. Custom room '
            'geometry does not recompute that route. This is an illustration, not robot navigation.',
        ),
    ),
    'ink-captcha': drawing(
        ('prompt', COPY),
        ('tiles', P(items=P(enum=('light', 'happy-light', 'sad-light', 'car', 'tree', 'laptop')))),
        ('picks', P(items=P(prefix_items=(TIME, P(minimum=0, maximum=8))))),
        ('verdict', P(prefix_items=(TIME, COPY))),
        constraints=(
            FONT,
            'Exactly nine tile kinds in row-major order. Prompt is nonblank and at most 60 '
            'characters. Each pick has a unique index 0..8 and nonnegative time; picks need not '
            'be time-sorted. Optional nonblank verdict overlays the grid from its nonnegative time. '
            'This draws an interface and never solves or submits a real challenge.',
        ),
    ),
    'ink-checkbox': drawing(
        ('label', COPY),
        ('tick_at', TIME),
        constraints=(
            FONT,
            'Static card at (140,430,800,230), label 1..24 nonblank characters. Optional '
            'nonnegative tick_at reveals a held tick; None omits it. No verification is performed.',
        ),
    ),
}
