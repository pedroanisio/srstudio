"""Authored semantics for house and homeware drawings, independent of builder execution."""

from collections.abc import Callable

from ._toon_contracts import COMP_TIME, END, FONT, PARENT_END, PARENT_START, REF, SPANS, START, TIME, draw, point
from ._toon_household_contracts import LIMIT, group
from .contracts import ParameterContract as P
from .contracts import PartContract

SCALE = P(unit='ratio', description='Finite positive geometry scale about the placement point.')
BOUNDED_SCALE = P(unit='ratio', minimum=0.5, maximum=1.5)
PARENT_SPANS = P(items=P(prefix_items=(PARENT_START, PARENT_END)))
COMP_SPANS = P(items=P(prefix_items=(COMP_TIME, COMP_TIME)))
SPAN = P(prefix_items=(START, END))
INSET = P(unit='reference pixels', minimum=0, description='Horizontal inset of signature marks.')
ID = P(role='scene-id', description='Exact scene group ID; the caller must keep IDs unique.')
WORN_AT = P(type=tuple[float, float], space='toon-reference', prefix_items=(REF, REF))
WORN_TIMING = 'start=None omits both visibility bounds; otherwise start/end use the parent clock. No actor binding.'
READINGS = 'Nonempty strictly increasing cues from zero. end=0 permits one cue at zero without timed visibility.'
RUNNING = 'Ordered nonoverlapping spans from zero; y alternates +/-3 reference pixels at 12 keys/s, returning to zero.'

_CONTRACTS = {
    'toon-ledge': draw(
        ('finish', P(enum=('oak', 'white', 'steel', 'dash', 'parlour'))),
        ('inset', INSET),
        constraints=('Fixed foreground surface at reference y=801; inset moves signature marks only.',),
    ),
    'toon-key-line': draw(
        ('start', PARENT_START),
        ('end', PARENT_END),
        (
            'measure',
            P(
                type=Callable[[str, float], float],
                role='text-measure',
                description='measure(text,56) returns advance width in frame pixels; does not draw.',
            ),
        ),
        constraints=(
            FONT,
            'Nonblank text to 34 characters; 0<=start<end.',
            'Measured width plus 64 frame pixels must fit canvas.width-80. Band y=884 is reference geometry.',
        ),
    ),
    'toon-hallway': draw(
        ('door', P(enum=('shut', 'open', 'none'))),
        constraints=('Background fills the canvas; doorway and pictures use fixed reference geometry.',),
    ),
    'toon-horse': draw(
        ('at', point('Head center.')),
        ('scale', BOUNDED_SCALE),
        ('start', P(unit='seconds', timebase='composition', role='animation-start', minimum=0)),
        ('end', P(unit='seconds', timebase='composition', role='animation-limit', minimum=0)),
        ('blinks', P(items=COMP_TIME)),
        ('neck', REF),
        ('id', ID),
        clock='composition',
        constraints=(
            'start/end only generate and filter blinks; they do not set group visibility.',
            'blinks=None generates cues from start+0.9 every 2.6 seconds; end=0 omits automatic blinks.',
            'An empty sequence disables blinks; explicit blinks still work with end=0. Cues rise strictly from zero.',
            'Blink closures last 0.12 seconds and must finish strictly before the blink limit.',
            'neck is the local reference distance below the head center; scale transforms the entire group.',
        ),
    ),
    'toon-thermostat': draw(
        ('readings', P(items=P(prefix_items=(PARENT_START, P(description='Two displayed digits, not a time.'))))),
        ('end', PARENT_END),
        ('at', point('Dial center.')),
        ('scale', BOUNDED_SCALE),
        ('id', ID),
        constraints=(FONT, READINGS, 'Timed readings end at the next cue or end; the thermostat body stays visible.'),
    ),
    'toon-finger': draw(
        ('tip', point('Finger tip before movement.')),
        ('angle', P(unit='degrees')),
        ('moves', P(items=P(prefix_items=(COMP_TIME, REF, REF)))),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', ID),
        clock='composition',
        constraints=(
            'angle rotates clockwise from pointing up; colour and sleeve are paints.',
            'start/end are nonnegative; end=0 omits visibility bounds and requires no moves.',
            'Rising move cues begin 0.1-second glides to absolute reference x,y; moves are not clipped to end.',
        ),
    ),
    'toon-vent': draw(
        ('at', point('Vent center.')),
        ('width', P(unit='reference pixels', minimum=120, maximum=240)),
        constraints=('Height is round(width*0.58,2) in reference pixels.',),
    ),
    'toon-bedroom': draw(
        constraints=('Canvas-filling wall; window, pillow and headboard use fixed reference geometry.',)
    ),
    'toon-quilt': draw(
        ('pattern', P(enum=('plum', 'teal'))),
        constraints=('Fixed foreground quilt and signed nightstand; no character or contact binding.',),
    ),
    'toon-sink': draw(
        ('stages', P(items=P(prefix_items=(PARENT_START, P(enum=('skin', 'plant', 'mail', 'frog')))))),
        ('end', PARENT_END),
        ('id', ID),
        ('inset', INSET),
        clock='composition',
        constraints=(
            'Stage names occur once in skin,plant,mail,frog order; cues rise strictly from zero.',
            'end=0 shows all named stages without timing. Otherwise stage cues precede end and set parent visibility.',
            'The frog waves on composition time between its stage cue and end; the counter stays visible.',
        ),
    ),
    'toon-day-card': draw(
        ('days', P(items=P(prefix_items=(PARENT_START, P(minimum=1, maximum=999))))),
        ('end', PARENT_END),
        ('at', point('Card center.')),
        ('id', ID),
        constraints=(
            FONT,
            READINGS,
            'Days are integers 1..999; numbers hide at end while the card and DAY header remain.',
        ),
    ),
    'toon-watering-can': draw(
        ('at', point('Near the spout rose.')),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('pour', COMP_TIME),
        ('id', ID),
        clock='composition',
        constraints=(
            'All times are nonnegative. end=0 omits visibility bounds and falling drops.',
            'For timed output start<=pour<end; pour also starts drop parent visibility.',
            'Three drop phases cycle every 0.36 seconds, falling 118 reference pixels.',
        ),
    ),
    'toon-tee': draw(
        ('at', WORN_AT),
        ('scale', SCALE),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', ID),
        constraints=(
            WORN_TIMING,
            'at is the collar center. colour must be #rrggbb; the printed face is fixed artwork.',
        ),
    ),
    'toon-bow-tie': draw(
        ('at', WORN_AT),
        ('scale', SCALE),
        ('id', ID),
        constraints=('at is the knot center in the supplied parent reference frame; no automatic figure tracking.',),
    ),
    'toon-bathroom': draw(
        constraints=('Wall fills the canvas; shower head at reference (256,190). Water is separate.',)
    ),
    'toon-shower-water': draw(
        ('spans', COMP_SPANS),
        ('clear', P(space='toon-reference', prefix_items=(REF, REF))),
        ('stop', REF),
        ('id', P(role='scene-id-prefix')),
        clock='composition',
        constraints=(
            'Nonempty ordered nonoverlapping spans from zero also set parent visibility.',
            'Three held phases repeat every 0.24 seconds on composition time.',
            'clear=(left,right), left<right, selects columns by their landing x; it is not a time span.',
            'Without stop the selected columns are omitted; with stop they end at that reference y.',
            'stop has no effect without clear. No collision or anatomical head tracking is performed.',
        ),
    ),
    'toon-suds': draw(
        ('at', WORN_AT),
        ('scale', SCALE),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', ID),
        constraints=(WORN_TIMING, 'at is the foam heap center in the supplied parent reference frame.'),
    ),
    'toon-towel': draw(
        ('at', WORN_AT),
        ('scale', SCALE),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', ID),
        constraints=(WORN_TIMING, 'at is the middle of the towel lower edge in the supplied parent reference frame.'),
    ),
    'toon-dishwasher': draw(
        ('at', point('Base center.')),
        ('scale', SCALE),
        ('loads', P(items=PARENT_START)),
        ('end', PARENT_END),
        constraints=(
            'At most 12 strictly increasing load cues from zero; end must follow the last cue.',
            'Each dish becomes visible at its cue and hides at end. The dishwasher itself remains visible.',
            'Empty loads draws an empty dishwasher; scale changes geometry around at, not a root transform.',
        ),
    ),
    'toon-rack': group(
        ('roll', SPAN),
        ('tilt', SPAN),
        ('rows', P(minimum=1, maximum=4)),
        ('start', PARENT_START),
        ('end', PARENT_END),
        constraints=(
            'start<=roll[0]<roll[1]<=end. tilt=None omits mug rotation; otherwise roll[1]<=tilt[0]<tilt[1]<=end.',
            'roll raises the rack 420 reference pixels; tilt turns the front middle mug -14,8,-14 degrees.',
            'Rows are integers 1..4; five mugs per row. Keys follow the canvas clock, not group visibility start.',
        ),
    ),
    'toon-baby-monitor': draw(
        ('at', point('Base center.')),
        ('scale', SCALE),
        constraints=('Static nursery unit; scale changes geometry about at. The LED is always lit.',),
    ),
    'toon-monitor-receiver': draw(
        ('at', point('Base center.')),
        ('scale', SCALE),
        ('pulses', P(items=TIME)),
        ('end', LIMIT),
        constraints=(
            'Strictly increasing pulses from zero; end must follow the last pulse but does not hide or clip the bars.',
            'Each pulse holds five bars on for 0.14 seconds; empty pulses leaves only the static baseline bars.',
        ),
    ),
    'toon-swing-door': draw(
        ('opens', SPANS),
        ('at', point('Frame top left.')),
        ('size', P(prefix_items=(P(unit='reference pixels'), P(unit='reference pixels')))),
        ('end', LIMIT),
        constraints=(
            'Ordered nonoverlapping opens from zero, all ending by end; empty opens keeps the door shut.',
            'Canvas opacity keys switch door and guest artwork. legs adds fixed guest legs, not an actor slot.',
        ),
    ),
    'toon-cupcakes': draw(
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('rows', P(minimum=1, maximum=6)),
        ('cols', P(minimum=1, maximum=6)),
        constraints=('Integer rows and columns 1..6; end>start. Static tray visibility only, no animation keys.',),
    ),
    'toon-shampoo': group(
        ('at', point('Bottle base center.')),
        ('scale', SCALE),
        ('bubble', P(unit='seconds', timebase='canvas', minimum=0)),
        constraints=(
            'bubble=None omits the bubble; otherwise it rises 80*scale reference pixels over 0.9 seconds.',
            'bubble also starts parent visibility for the bubble only; the bottle remains visible.',
            'Returned group contains the entire bottle; keys are emitted on the bubble child.',
        ),
    ),
    'toon-soup-tubs': draw(
        ('counts', P(items=P(prefix_items=(PARENT_START, P(minimum=1, maximum=6))))),
        ('at', point('Stack base center.')),
        ('end', PARENT_END),
        constraints=(
            'Nonempty strictly increasing cues from zero; end follows the last cue. Counts are integers 1..6.',
            'Each cue selects the visible count until the next cue or end, including decreases and later increases.',
            'Visibility changes only; no interpolation or physical stacking simulation.',
        ),
    ),
    'toon-profile-list': draw(
        ('start', PARENT_START),
        ('end', PARENT_END),
        constraints=(FONT, '1..6 names, each 1..12 characters; end>start. Font sizes are frame pixels.'),
    ),
    'toon-device-list': draw(
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('paints', P(description='Five paint colors: page, row, ink, soft ink, doing.')),
        constraints=(
            FONT,
            '1..4 (name,device,doing) rows; name 1..12 characters. end>start. Font sizes are frame pixels.',
        ),
    ),
    'toon-scribble': draw(
        ('spans', PARENT_SPANS),
        ('at', point('Caption pill center.')),
        ('width', P(unit='reference pixels', minimum=120, maximum=540)),
        constraints=('Ordered nonoverlapping spans from zero; empty spans draws nothing. No font or animation keys.',),
    ),
    'toon-mower': draw(
        ('at', point('Mower base reference point.')),
        ('scale', SCALE),
        ('running', SPANS),
        constraints=(RUNNING, 'Running spans do not hide the tool; displacement amplitude is independent of scale.'),
    ),
    'toon-blower': draw(
        ('at', point('Drawn handle reference point; not a spatial grip frame.')),
        ('scale', SCALE),
        ('running', SPANS),
        constraints=(RUNNING, 'Running spans do not hide the tool; displacement amplitude is independent of scale.'),
    ),
    'toon-lasagna': draw(
        ('at', point('Dish base center.')),
        ('scale', SCALE),
        constraints=('Static dish with drawn oven gloves; no character hand binding.',),
    ),
    'toon-plate-of-toast': draw(
        ('at', point('Plate reference point; ellipse spans y-18*scale to y+12*scale.')),
        ('scale', SCALE),
        constraints=('Static plate and two toast slices; scale changes geometry about at.',),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]
