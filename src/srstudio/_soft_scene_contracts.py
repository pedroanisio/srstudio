"""Soft scene discovery: framed slots, local drawing origins and canvas-clock gates."""

from dataclasses import replace

from sr_core.scene import Composition, Group, Symbol

from ._drawing_contracts import _slot
from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

TIME = P(unit='seconds', timebase='canvas')
DURATION = P(unit='seconds', role='duration')
SPAN = P(prefix_items=(TIME, TIME))
SPANS = P(items=SPAN)
RATIO = P(type=float, unit='ratio', minimum=0)
ANGLE = P(unit='degrees')
PARENT = P(type=float, unit='parent pixels', space='parent')
LOCAL = P(unit='drawing pixels', space='returned-group')
ROOT = P(unit='frame pixels', space='set-root')
ID = P(role='scene-id', description='Caller-unique group ID; child IDs are derived from it.')
GROUP = P(type=Group, role='drawing-group', unit='frame pixels', space='parent')
LOCAL_GROUP = P(
    type=Group, role='drawing-group', unit='drawing pixels', space='returned-group', anchors=(('origin', (0, 0)),)
)
COPY = P(role='display-copy', description='Literal displayed text, not an animation instant or service request.')
SHOT = P(
    fields=(
        ('time', TIME),
        ('scale', RATIO),
        ('x', replace(ROOT, role='framing-center')),
        ('y', replace(ROOT, role='framing-center')),
    )
)
SHOTS = P(items=SHOT)
LIGHTS = P(
    items=P(fields=(('time', TIME), ('state', P(enum=('day', 'phone', 'lamp', 'dark'))), ('x', ROOT), ('y', ROOT)))
)
DIM = P(fields=(('start', TIME), ('end', TIME), ('fade', DURATION), ('x', ROOT), ('y', ROOT)))
FONT = 'Text uses the bound Canvas font at fixed sizes; these builders do not take a measurement callback.'
FRAME = (
    'Fixed 1080x1920 layout. shots start at zero and increase strictly. One Shot applies static framing; '
    'multiple Shots hold each transform until the next cut. x/y is the room point centered at frame (540,960). '
    'The foreground stays outside that transform. Invalid framing fails before drawing or slot calls.'
)
CLOCK = (
    'Animation keys and held opacity gates follow Canvas.local_time: composition time by default, '
    'sequence-shot local time when enabled. Gates include the start and exclude the end.'
)


def draw(*parameters: tuple[str, P], returns: P = GROUP, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), ('id', ID), *parameters),
        returns=returns,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', True)),
        constraints=(CLOCK, 'Draws flat geometry; does not solve world-space contacts or biomechanics.', *constraints),
    )


def placed(origin: str, *parameters: tuple[str, P], constraints: tuple[str, ...] = ()) -> PartContract:
    return draw(
        ('x', PARENT),
        ('y', PARENT),
        ('scale', RATIO),
        *parameters,
        returns=LOCAL_GROUP,
        constraints=(f'x/y places {origin}; scale is positive and scales the returned local drawing.', *constraints),
    )


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'soft-park': draw(
        ('shots', SHOTS),
        ('growth', P(items=P(prefix_items=(TIME, P(minimum=0, maximum=4))))),
        ('seated', SPANS),
        ('cast', _slot('Receives the framed room after the tree and bench, before the foreground.')),
        constraints=(
            FRAME,
            'growth is held (time,stage) rows from zero, selecting tree stages 0..4; the town '
            'caps its stage at 3. This swaps drawings rather than growing geometry continuously.',
            'seated gates the bench; empty spans omit it. '
            'The planter and signature marks stay in the fixed foreground. '
            'A default identity Shot retains the original unwrapped room structure.',
        ),
    ),
    'soft-bedroom': draw(
        ('shots', SHOTS),
        ('lights', LIGHTS),
        ('cast', _slot('Receives the framed room behind the duvet, against the pillows.')),
        ('held', _slot('Receives the same room after the duvet. Return values do not select another parent.')),
        constraints=(
            FRAME,
            'lights starts at zero, increases strictly and swaps day/phone/lamp/dark overlays. '
            'Their x/y centers belong to the unframed set root, not the transformed room.',
            'Phone light flickers in held 0.14-second steps for at most 60 seconds per state; the last key holds. '
            'Lamp and dark overlays hold; day adds no veil. These are drawn pools, not shared world lights. '
            'The last light state extends to the fixed 1e6-second sentinel.',
        ),
    ),
    'soft-playroom': draw(
        ('shots', SHOTS),
        ('dim', DIM),
        ('cast', _slot('Receives the framed room on the rug, before the foreground toy crate.')),
        constraints=(
            FRAME,
            'dim fades a root-space radial veil linearly over fade duration, then holds until end. '
            'Require start>=0, fade>0 and end>=start+fade. '
            'The veil covers room and foreground; no physical light is emitted.',
        ),
    ),
    'soft-front-room': draw(
        ('shots', SHOTS),
        ('wedged', SPANS),
        ('hall', _slot('Receives the framed room before the wall with its door opening.')),
        ('behind', _slot('Receives that room after the wall and door trim, before the rug.')),
        ('cast', _slot('Receives that room on the rug, before the fixed foreground shelf.')),
        constraints=(
            FRAME,
            'wedged gates the sofa behind the wall over ordered nonoverlapping spans. '
            'Empty spans omit the sofa. Foreground shelf and signature marks stay fixed.',
        ),
    ),
    'soft-wall-clock': placed(
        'the clock center',
        ('time', COPY),
        constraints=(
            'Static 200-pixel face at scale 1. time is H:MM from 0:00 through 23:59; '
            'the hour hand uses hours modulo 12. '
            'Digits are not drawn and hands do not advance. No font required.',
        ),
    ),
    'soft-picture-book': placed(
        'the middle of the spine',
        ('slide', P(fields=(('time', TIME), ('seconds', DURATION), ('dx', PARENT), ('dy', PARENT), ('turn', ANGLE)))),
        constraints=(
            '300-pixel book at scale 1. Optional slide holds its starting position until time, then '
            'linearly moves by dx/dy in parent pixels over seconds>0 and rotates to turn degrees. '
            'The displacements are not multiplied by the book scale; no physics or font is used.',
        ),
    ),
    'soft-bedside-lamp': placed(
        'the middle of the base',
        ('on', TIME),
        ('off', TIME),
        constraints=(
            '300-pixel lamp at scale 1. The unlit shade always exists; a lit shade and bulb overlay is held over '
            '[on,off), with 0<=on<off. This does not light the room; coordinate soft_sets.Light separately.',
        ),
    ),
    'soft-open-briefcase': placed(
        'the middle of the hinge',
        ('shut', TIME),
        constraints=(
            'Open and closed drawings swap via opacity gates at shut. No interpolated hinge or document parsing. '
            'The final closed drawing holds to 1e6 seconds; the default shut=1e6 leaves it open.',
        ),
    ),
    'soft-handshake': draw(
        ('start', TIME),
        ('end', TIME),
        ('pumps', P(unit='pump count', minimum=1)),
        constraints=(
            'Full-frame quilt and two drawn arms, visible only during [start,end), with end>start>=0. '
            'A positive integer pumps schedules 60-frame-pixel vertical strokes with linear interpolation. '
            'It is a composed insert, not a returned hand anchor or grip solver.',
        ),
    ),
    'soft-quilt-pull': draw(
        ('x', PARENT),
        ('y', PARENT),
        ('to', replace(PARENT, role='absolute-y')),
        ('at', TIME),
        ('seconds', DURATION),
        ('width', LOCAL),
        returns=LOCAL_GROUP,
        constraints=(
            'x/y places the quilt top. to is an absolute parent y strictly above y, not a displacement. '
            'After at>=0, the root moves linearly to to over seconds>0. width is positive drawing pixels. '
            'The shape extends 800 drawing pixels down; no cloth simulation or font is used.',
        ),
    ),
    'soft-door': draw(
        (
            'rows',
            P(
                items=P(
                    fields=(
                        ('a0', P(unit='room units', space='soft-room')),
                        ('a1', P(unit='room units', space='soft-room')),
                        ('up', P(unit='room units', space='soft-room')),
                        ('shut', SPANS),
                        ('hinge', P(enum=('left', 'right'))),
                    )
                )
            ),
        ),
        ('end', TIME),
        (
            'between',
            _slot(
                'Receives a dedicated child group after dark openings, before both door leaves. '
                'Draw in projected frame coordinates, not per-door local coordinates.'
            ),
        ),
        constraints=(
            'a0..a1 runs along the Soft back wall; up is height above its floor. '
            'blob.room_point projects those coordinates into the parent frame. Doors cannot overlap along the wall.',
            'shut intervals form a union; open leaves appear in its gaps up to end. Empty shut intervals mean closed '
            'from zero to end. end is a complement limit, not a gate on the full frame or callback. '
            'Door leaves swap drawings; hinge chooses the authored swung shape, not a continuous rotation.',
        ),
    ),
    'soft-mop': placed(
        'the mop head on the floor',
        ('lean', P(unit='degrees', minimum=-80, maximum=80)),
        ('to', P(unit='degrees', minimum=-180, maximum=180)),
        ('tips', SPAN),
        constraints=(
            '620-pixel pole at scale 1. Optional tips=(start,end) holds lean until start, then uses sine-in '
            'rotation to the absolute angle to about the floor origin. No collision or gravity simulation.',
        ),
    ),
    'soft-closet': draw(
        ('start', TIME),
        ('end', TIME),
        ('slit', P(prefix_items=(PARENT, PARENT))),
        ('veil', P(unit='opacity', minimum=0, maximum=1)),
        ('behind', _slot('Receives the root after the background, before the dark side veils and bright slit.')),
        constraints=(
            'Full-frame drawing gated by 0<=start<end. slit=(left,right) is inside the canvas, not width/height. '
            'veil is positive and at most one. The 200-pixel overscan supports a small parent push; '
            'the slit is drawn light, not a shared lighting source.',
        ),
    ),
    'soft-mug': placed(
        'the mug center',
        constraints=(
            'A static unlettered mug; empty changes the inside fill rather than its pose or shape. '
            'The handle extends beyond the nominal 120x120 cup. No font required.',
        ),
    ),
    'soft-mail-screen': placed(
        'the center of the phone glass',
        ('counts', P(items=P(fields=(('text', COPY), ('at', TIME), ('until', TIME))))),
        constraints=(
            FONT,
            'Glass spans local (-65,-130)..(65,130). Count records contain display copy, not computed totals. '
            'Their ordered nonoverlapping spans gate text only; the badge stays drawn through gaps. '
            'Each nonblank count has at most seven characters.',
        ),
    ),
    'soft-battery-screen': placed(
        'the center of the phone glass',
        (
            'levels',
            P(
                items=P(
                    fields=(
                        ('percent', P(type=int, minimum=0, maximum=100)),
                        ('at', TIME),
                        ('until', TIME),
                        ('number', P(type=bool)),
                    )
                )
            ),
        ),
        constraints=(
            FONT,
            'Glass spans local (-65,-130)..(65,130). Ordered nonoverlapping spans gate the charge and its number; '
            'the empty battery stays drawn through gaps. The charge and number go red at 20 percent and under; a level '
            'with number False shows its charge alone. '
            'No status bar: a plain battery over a percentage, copying no real phone.',
        ),
    ),
    'soft-mail-list': placed(
        'the center of the phone glass',
        ('scroll', P(items=P(prefix_items=(TIME, LOCAL)))),
        ('marked', P(role='row-index', minimum=0, maximum=3)),
        constraints=(
            FONT,
            'One to four nonblank rows, each at most 22 characters and two lines. '
            'marked is an optional zero-based existing row index.',
            'scroll keys linearly move the child page y in unscaled drawing pixels, so the returned group scale '
            'scales the visible travel. The page is not clipped to the glass. No inbox is fetched.',
        ),
    ),
    'soft-call-screen': placed(
        'the center of the phone glass',
        ('pressed', TIME),
        constraints=(
            FONT,
            'Caller copy has at most 16 characters and two lines. The red button center is (-34,62) in local pixels. '
            'At pressed its dark overlay appears until 1e6 seconds; no call is made and the caller text remains.',
        ),
    ),
    'soft-star-card': placed(
        'the card center',
        ('tap', TIME),
        ('stars', P(unit='star count', minimum=1, maximum=5)),
        constraints=(
            'An unlettered 460x150 card. With no tap it stays empty. At tap, stars fill by held gates; '
            'the root y reaches y+34*scale and returns to y over 0.22 seconds, using linear keys from time zero. '
            'This includes approach motion before tap; no external rating is submitted.',
        ),
    ),
}
