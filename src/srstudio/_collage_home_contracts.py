"""Collage home and table props: placement origins, sizes refused at zero, and static paper drawings."""

from ._collage_everyday_contracts import ANGLE, COLOR, COPY, LOCAL, LOCAL_GROUP, PARENT, drawing, placed
from .contracts import ParameterContract as P
from .contracts import PartContract

SIZED = 'Positive size or HomeError; the root scales to it about the origin. Static paper drawing.'
BOXED = 'Static paper drawing; the size is applied to the geometry, not a root scale.'
BAKED_GROUP = P(
    role='drawing-group', unit='parent pixels', space='parent', description='Geometry is baked in parent pixels.'
)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'collage-wall-tv': placed(
        'the TV top-left',
        ('w', PARENT),
        returns=P(description='Screen record: the group, a clipped image group to draw into, and its size in pixels.'),
        constraints=('Positive w or HomeError; the height is 0.62 of w. Draw the reel into Screen.image.',),
    ),
    'collage-hard-hat': placed("the brim's centre", ('w', PARENT), ('tilt', ANGLE), constraints=(SIZED,)),
    'collage-kayak': placed('the kayak centre', ('w', PARENT), ('tilt', ANGLE), constraints=(SIZED,)),
    'collage-school-desk': placed('the middle of the feet', ('w', PARENT), constraints=(SIZED,)),
    'collage-staircase': placed(
        "the foot's left corner",
        ('w', LOCAL),
        ('h', LOCAL),
        ('steps', P(minimum=2)),
        constraints=(BOXED, 'Rises to the right. At least two steps or HomeError.'),
    ),
    'collage-pay-envelope': placed(
        'the envelope centre',
        ('w', LOCAL),
        ('stamp', COPY),
        ('size', P(unit='drawing pixels', description='Lettering size of the stamp.')),
        constraints=(
            BOXED,
            'Positive w or HomeError; a stamp holding a digit is refused, since a sealed envelope shows no figure. '
            'An empty stamp draws none. A stamp needs a bound Canvas font.',
        ),
    ),
    'collage-headset': drawing(
        ('cx', PARENT),
        ('cy', PARENT),
        ('rx', LOCAL),
        ('ry', LOCAL),
        returns=LOCAL_GROUP,
        constraints=('cx/cy and rx/ry describe the head it sits on: its centre and radii. Static.',),
    ),
    'collage-desk-lamp': placed('the middle of the base', ('h', PARENT), constraints=(SIZED,)),
    'collage-dead-plant': placed("the middle of the pot's foot", ('h', PARENT), constraints=(SIZED,)),
    'collage-cereal-bowl': placed("the middle of the bowl's foot", ('w', PARENT), constraints=(SIZED,)),
    'collage-spoon': placed(
        'the end of the handle', ('length', PARENT), ('tilt', ANGLE), constraints=(SIZED, 'Tilted about that end.')
    ),
    'collage-pen': placed(
        'the tip', ('length', PARENT), ('tilt', ANGLE), ('colour', COLOR), constraints=(SIZED, 'Tilted about the tip.')
    ),
    'collage-menu-card': placed(
        'the menu centre',
        ('w', LOCAL),
        ('h', LOCAL),
        ('tilt', ANGLE),
        constraints=(BOXED, 'Lettered MENU; needs a bound Canvas font.'),
    ),
    'collage-order-pad': placed(
        'the pad centre',
        ('w', LOCAL),
        ('tilt', ANGLE),
        ('lines', P(minimum=0)),
        constraints=(BOXED, 'Positive w or HomeError; the height is 1.32 of w. The scrawl is unreadable by design.'),
    ),
    'collage-plate': placed(
        'the plate centre',
        ('w', PARENT),
        ('dish', P(enum=('steak', 'salad', 'sauce', 'empty'))),
        constraints=(SIZED, 'An unknown dish raises HomeError.'),
    ),
    'collage-chair-back': placed('the middle of the chair top', ('w', LOCAL), ('h', LOCAL), constraints=(BOXED,)),
    'collage-wall-hole': placed('the hole centre', ('w', LOCAL), ('h', LOCAL), constraints=(BOXED,)),
    'collage-snowy-window': placed(
        'the pane top-left',
        ('w', PARENT),
        ('h', PARENT),
        (
            'flakes',
            P(
                items=P(prefix_items=(P(unit='ratio'), P(unit='ratio'))),
                description='Fractions of the pane; empty uses a fixed scatter.',
            ),
        ),
        returns=BAKED_GROUP,
        constraints=('Static; laid over a set window, in parent pixels.',),
    ),
    'collage-tissue-box': placed('the middle of the foot', ('w', PARENT), constraints=(SIZED,)),
    'collage-wall-clock': placed(
        'the clock centre',
        ('r', LOCAL),
        ('time', P(role='display-copy', description='A time like "9:50"; anything else raises HomeError.')),
        returns=P(description='WallClock record: the group and the hour and minute hand angles.'),
        constraints=('The hands do not move.',),
    ),
    'collage-toothbrush-mug': placed('the middle of the foot', ('h', PARENT), ('colour', COLOR), constraints=(SIZED,)),
    'collage-napkin': placed('the middle of the tucked edge', ('w', PARENT), constraints=(SIZED,)),
}
