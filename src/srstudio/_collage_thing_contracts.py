"""Collage table and corner prop contracts grounded in their drawing coordinates and clocks."""

from dataclasses import replace

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

PARENT = P(unit='parent pixels', space='parent')
LOCAL = P(unit='drawing pixels', space='returned-group')
FIXED = P(unit='drawing pixels', space='fixed-layout')
ANGLE = P(unit='degrees', role='rotation-about-origin')
TIME = P(unit='seconds', timebase='composition', minimum=0)
COPY = P(role='display-copy')
COLOR = P(role='paint-color')
GROUP = P(type=Group, role='drawing-group', unit='drawing pixels', space='fixed-layout')
LOCAL_GROUP = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
FONT = (
    'Nonempty text needs a bound Canvas font. Lettering size and text-box dimensions are rounded to '
    'whole pixels; no font measurement callback or automatic text fitting is performed.'
)
STATIC = 'Static drawing. The caller can key the returned group to move it.'


def drawing(*parameters: tuple[str, P], returns: P = GROUP, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=returns,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', True)),
        constraints=(
            'Draws 2D paper geometry under one returned group; no physical grip, contact or body solver is created.',
            *constraints,
        ),
    )


def placed(origin: str, *parameters: tuple[str, P], constraints: tuple[str, ...] = ()) -> PartContract:
    return drawing(
        ('x', PARENT),
        ('y', PARENT),
        *parameters,
        returns=LOCAL_GROUP,
        constraints=(f'x/y places {origin} in the parent; it is the returned group origin.', *constraints),
    )


def contract(name: str, *, cast: tuple[str, ...] = ()) -> PartContract:
    result = _CONTRACTS[name]
    if cast:
        result = replace(result, parameters=(*result.parameters, ('who', P(enum=cast, role='collage-character-name'))))
    return result


_CONTRACTS = {
    'collage-handset': placed(
        'the handset center',
        ('length', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, 'length is positive. The handset lies horizontally before tilt; its end cups protrude.'),
    ),
    'collage-desk-phone': placed(
        'the foot center',
        ('w', LOCAL),
        ('display', COPY),
        ('size', LOCAL),
        constraints=(
            STATIC,
            FONT,
            'w is positive. Body height is 0.8*0.62*w above the foot. An empty display is dark; '
            'nonempty display requires positive size. off_hook omits the handset, without moving or returning '
            'a detached one. Use collage-handset separately for the receiver in a hand.',
        ),
    ),
    'collage-resume': placed(
        'the sheet center',
        ('w', LOCAL),
        ('tilt', ANGLE),
        ('turn', TIME),
        constraints=(
            'w is positive; height is 1.3*w. The CV heading and lines are paths, so no font is needed. '
            'turn=None keeps the front static. Otherwise turn is a nonnegative project second: scaleX '
            'shrinks linearly from 1 to 0.03 in 0.15 seconds and returns to 1 after another 0.15. '
            'Front/back opacity swaps at that midpoint on the same project clock regardless of Canvas.local_time. '
            'The back is blank. This is a flat squeeze, not a spatial sheet rotation.',
        ),
    ),
    'collage-fork': placed(
        'the handle end',
        ('length', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, 'length is positive. Tines point upward before tilt; no hand attachment is supplied.'),
    ),
    'collage-gravy-boat': placed(
        'the foot center',
        ('size', LOCAL),
        ('forks', P(minimum=0, maximum=5, role='fork-count')),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'size is a positive reference length. forks is an exact integer from 0 through 5, excluding booleans. '
            'Forks fan in 14-degree increments with length 0.95*size; zero forks also omits their tape.',
        ),
    ),
    'collage-tiny-cup': placed(
        'the saucer center reference',
        ('size', LOCAL),
        constraints=(STATIC, 'size is a positive bowl width; the saucer is 1.36*size wide and extends below y=0.'),
    ),
    'collage-wine-glass': placed(
        'the foot center',
        ('height', LOCAL),
        constraints=(STATIC, 'height is positive; the bowl top is at -height. The wine amount is fixed.'),
    ),
    'collage-bank-card': placed(
        'the card center',
        ('w', LOCAL),
        ('name', COPY),
        ('colour', COLOR),
        ('tilt', ANGLE),
        constraints=(STATIC, FONT, 'w is positive; height is 0.63*w. Nonempty name is drawn literally at size 0.16*w.'),
    ),
    'collage-receipt': placed(
        'the slip center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'w/h are positive. torn selects a jagged foot in the static silhouette; it does not animate a tear. '
            'Printed bars are paths, not receipt text or a transaction record.',
        ),
    ),
    'collage-wallet': placed(
        'the wallet center',
        ('w', LOCAL),
        ('cards', P(items=COLOR)),
        constraints=(
            STATIC,
            'w is positive; height is 0.62*w. At most two card colors fill the upper slots. '
            'There are always three slots, with the last empty; cards does not accept drawing callbacks.',
        ),
    ),
    'collage-counter': drawing(
        ('top', FIXED),
        ('colour', COLOR),
        ('slab', COLOR),
        ('seam', COLOR),
        constraints=(
            STATIC,
            'Fixed 1080x1920 foreground layout. top is positive and baked into the paths; '
            'the returned group has no translation. Slab runs from x=-60 to 1140 and y=top to top+44; '
            'the body extends to y=2024 and seams to y=1920. Canvas resizing does not reflow it.',
        ),
    ),
    'collage-till': placed(
        'the foot center',
        ('w', LOCAL),
        ('text', COPY),
        ('size', LOCAL),
        constraints=(
            STATIC,
            FONT,
            'w is positive; body height is 0.8*w. Nonempty text requires positive size. '
            'The readout is a literal illustration; it does not process payments.',
        ),
    ),
    'collage-stool': placed(
        'the seat top reference',
        ('w', LOCAL),
        constraints=(
            STATIC,
            'w is positive. The seat outline is centered at y=0.06*w and has half-height 0.1*w; '
            'legs extend to y=1.1*w. This origin is an authored reference, not a fitted contact anchor.',
        ),
    ),
    'collage-towel': placed(
        'the top center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, 'w/h are positive. The towel hangs downward, with a 22-pixel fringe below h.'),
    ),
    'collage-ring-corner': drawing(
        ('x', FIXED),
        ('y', FIXED),
        ('h', FIXED),
        ('reach', FIXED),
        constraints=(
            STATIC,
            'x/y is the post top center, baked into the paths; the returned group has no translation. '
            'h/reach are positive. Three ropes run reach pixels left and 60 pixels down from the post, '
            'at 0.1, 0.4 and 0.7 of its height. Draw behind the cast.',
        ),
    ),
    'collage-eye-twitch': drawing(
        ('times', P(items=TIME)),
        ('side', P(enum=(-1, 1), role='screen-side')),
        constraints=(
            'Draws the selected cast eyelid in its fixed figure coordinates, over a held face. '
            'It does not follow head motion or solve eyelid anatomy. -1 selects screen-left, 1 screen-right. '
            'Parent it with the figure to share placement.',
            'times is nonempty, finite, nonnegative, strictly increasing and below 1000000. '
            'Each closure lasts 0.09 seconds on the project clock regardless of Canvas.local_time. '
            'Keys round to six decimals; overlapping and touching closures merge. Opacity is held.',
        ),
    ),
}
