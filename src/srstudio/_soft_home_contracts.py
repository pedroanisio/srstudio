"""Soft home discovery: a den, two flats, a restaurant door and what people bring into them."""

from ._drawing_contracts import _slot
from ._soft_scene_contracts import COPY, DURATION, FONT, FRAME, PARENT, ROOT, SHOTS, SPANS, TIME, draw, placed
from .contracts import ParameterContract as P
from .contracts import PartContract

COLOR = P(role='paint-color')
ROOM_COLORS = P(
    fields=(
        ('wall', P(prefix_items=(COLOR, COLOR), description='Top then bottom.')),
        ('floor', P(prefix_items=(COLOR, COLOR), description='Top then bottom.')),
    ),
    description="A home's wall, floor and sofa paints.",
)
DAY = P(items=P(prefix_items=(TIME, P(unit='ratio', minimum=0, maximum=1))), description='0 night, 1 morning.')
MARKS = 'The signature marks stand in an unframed front group, outside every shot transform.'
WORN = "scale is the wearer's, so it lands on a blob of that scale."
CAST = _slot('Draws the cast into the framed room.')


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'soft-den': draw(
        ('end', P(unit='seconds', timebase='canvas', role='end', description='Positive.')),
        ('day', DAY),
        (
            'still',
            P(unit='seconds', timebase='canvas', minimum=0, description='Screen flicker starts here; before end.'),
        ),
        ('pool', P(prefix_items=(ROOT, ROOT), description='Where night pools blue.')),
        ('shots', SHOTS),
        ('behind', _slot('Draws behind the sofa, in the framed room.')),
        ('cast', _slot('Draws on the sofa, in the framed room.')),
        ('lit', _slot('Draws over the dark, for a screen that makes its own light.')),
        ('room_colors', ROOM_COLORS),
        constraints=(FRAME, MARKS, 'The blind and daylight move between day rows, which rise in time.'),
    ),
    'soft-flats': draw(
        ('shots', SHOTS),
        ('left', ROOM_COLORS),
        ('right', ROOM_COLORS),
        ('cast', CAST),
        constraints=(FRAME, MARKS, 'One wall at x=540 divides the two homes. Shot(t, 2, 270, 960) is the left alone.'),
    ),
    'soft-restaurant': draw(
        ('tilt', P(unit='seconds', timebase='canvas', minimum=0, description='The tilt down starts here.')),
        (
            'back',
            P(unit='seconds', timebase='canvas', description='The tilt up starts here; needs tilt to have ended.'),
        ),
        ('drop', P(unit='frame pixels', minimum=0, maximum=720, description='Over 0.')),
        ('seconds', DURATION),
        ('cast', _slot('Draws the cast into the world, so a tilt carries them.')),
        constraints=(
            'Fixed layout: a world running to y=2640. seconds is positive. The marks stand in the world on a shelf '
            'above the cast, so a tilt carries them off the top.',
        ),
    ),
    'soft-television': placed(
        "the screen's middle",
        ('still', P(unit='seconds', timebase='canvas', minimum=0, description='Screen light changes from here.')),
        ('talks', SPANS),
        (
            'counts',
            P(items=P(prefix_items=(COPY, TIME, TIME)), description='One digit, then its span; never during talks.'),
        ),
        constraints=(FONT, '360 wide at scale 1. Voice bars pulse in talks. It has no face.'),
    ),
    'soft-chip-bag': placed(
        "the middle of the bag's foot", constraints=('Static and unbranded; 170 wide at scale 1.',)
    ),
    'soft-chip': placed('the chip centre', constraints=('Static; 70 wide at scale 1.',)),
    'soft-blanket': placed(
        'the middle of the head above it', ('color', COLOR), constraints=(WORN, 'Falls 330 below the head at scale 1.')
    ),
    'soft-scarf': placed('the middle of the head above it', ('color', COLOR), constraints=(WORN,)),
    'soft-slippers': placed(
        'the point on the ground between the feet',
        ('apart', P(unit='drawing pixels', minimum=0, description="Over 0, in the wearer's rig units.")),
        ('color', COLOR),
        constraints=(WORN,),
    ),
    'soft-hook-card': draw(
        ('text', P(role='display-copy', description='Nonblank and at most 16 characters.')),
        ('box', P(prefix_items=(PARENT, PARENT, PARENT, PARENT), description='x, y, width, height; positive size.')),
        ('start', TIME),
        ('end', TIME),
        ('size', P(unit='frame pixels')),
        constraints=(FONT, '0<=start<end. Visible from start until end.'),
    ),
}
