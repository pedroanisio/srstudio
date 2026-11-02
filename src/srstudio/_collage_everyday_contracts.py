"""Everyday paper drawing coordinates, actual return ownership and sampled reach operations."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P

PARENT = P(unit='parent pixels', space='parent')
LOCAL = P(unit='drawing pixels', space='returned-group')
FIXED = P(unit='drawing pixels', space='fixed-layout')
POINT = P(unit='parent pixels', space='parent', prefix_items=(PARENT, PARENT))
TIME = P(unit='seconds', timebase='composition')
CANVAS_TIME = P(unit='seconds', timebase='canvas')
ANGLE = P(unit='degrees', role='rotation-about-origin')
COPY = P(role='display-copy')
COLOR = P(role='paint-color')
GROUP = P(type=Group, role='drawing-group', unit='drawing pixels', space='fixed-layout')
LOCAL_GROUP = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
SCREEN = replace(LOCAL_GROUP, space='phone-screen')
FONT = 'Text needs a bound Canvas font. Text-box dimensions and lettering size round to whole pixels.'
STATIC = 'Static drawing; the caller can key a containing group to move it.'
SCREEN_SCOPE = (
    'Returns only the inner screen group, with origin at the screen top-left, 26 pixels inside the frame. '
    'The outer frame is not owned by that return. Use a caller-owned parent to move or hide the whole phone. '
    'Screen content is not clipped automatically.'
)
ARM = (
    'who is a Collage cast name or Look. frm/to are points in the supplied parent, baked into the drawing. '
    'The returned group has no translation. hand=False omits the hand. '
    'Explicit side=-1 means screen-left and side=1 screen-right; view selects FRONT or POV hand orientation. '
    'An omitted side keeps the legacy left-hand drawing but records an anatomy fault when hand=True. '
    'Supply side explicitly for new work; the inferred unsaid sentinel is not a string to pass as side.'
)


def drawing(*parameters: tuple[str, P], returns: P = GROUP, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=returns,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', True)),
        constraints=(
            'Draws 2D paper geometry; no physical grip, contact or biomechanics solver is created.',
            *constraints,
        ),
    )


def placed(
    origin: str, *parameters: tuple[str, P], constraints: tuple[str, ...] = (), returns: P = LOCAL_GROUP
) -> PartContract:
    return drawing(
        ('x', PARENT),
        ('y', PARENT),
        *parameters,
        returns=returns,
        constraints=(f'x/y specifies {origin}.', *constraints),
    )


def contract(name: str, **helpers: Callable[..., Any]) -> PartContract:
    return replace(
        _CONTRACTS[name],
        operations=tuple(Operation(helper, builder, _HELPERS[helper]) for helper, builder in helpers.items()),
    )


_HELPERS = {
    'shoulder': PartContract(
        parameters=(('side', P(role='screen-side')),),
        returns=P(unit='drawing pixels', space='fixed-layout', prefix_items=(FIXED, FIXED)),
        capabilities=(('spatial_attachment', False),),
        constraints=(
            'Pure reference in the fixed Collage single-figure layout: side=-1 matches free, side=1 free-right. '
            'who is a cast name or Look. The reference is not transformed into world coordinates.',
        ),
    ),
    'reach': drawing(
        ('frm', POINT),
        ('width', LOCAL),
        ('times', P(items=TIME)),
        ('side', P(role='screen-side')),
        (
            'hand',
            P(
                role='sampled-hand-position',
                description=(
                    'Called exactly once per supplied time, in input order, with a project second; '
                    'returns a parent-space '
                    '(x,y) hand position. It draws nothing. Returned positions are linearly keyed between samples.'
                ),
            ),
        ),
        returns=LOCAL_GROUP,
        constraints=(
            'who is a cast name or Look. Supply side=-1 or 1 explicitly and view=FRONT or POV. '
            'Times must be supplied; each sampled hand must be at least one pixel from frm. '
            'Sample times are project seconds regardless of Canvas.local_time.',
            'A sleeve pivots at frm, turns by the shortest angle between samples and stretches to '
            'max(distance-30,1)/300. This is a single stretching segment, not an articulated elbow or IK solve. '
            'Inter-sample rotation, length and hand translation interpolate independently; exact contact '
            'between sleeve and hand is only authored at sample times.',
            'Returns the hand holder, whose origin is the hand position, without mirroring held objects. '
            'The sleeve pivot is a sibling. Use a caller-owned parent to move or hide the complete arm. '
            'The default omitted side records an anatomy fault; a supplied side selects the hand mirror.',
        ),
    ),
    'eased': PartContract(
        parameters=(
            ('keys', P(items=P(prefix_items=(TIME, P(role='scalar-value'))))),
            ('t', TIME),
            ('kind', P(enum=('sine-in-out', 'cubic-in'))),
        ),
        returns=P(role='sampled-scalar'),
        constraints=(
            'Samples an existing nonempty increasing scalar track without drawing. Holds endpoint values '
            'outside the keys. Caller supplies ordered finite keys; this helper is not a general track validator.',
        ),
    ),
    'frames': PartContract(
        parameters=(('spans', P(prefix_items=(TIME, TIME))), ('step', P(unit='seconds', role='sampling-interval'))),
        returns=P(items=TIME),
        constraints=(
            'Returns sorted unique sample times, rounded to six decimals, including both endpoints of every '
            'forward span. Supply a finite positive step; it is a sampling interval, not output FPS. '
            'No scene is drawn or modified.',
        ),
    ),
    'chew': PartContract(
        parameters=(('track', P(items=P(prefix_items=(TIME, P(role='viseme'))))), ('start', TIME), ('end', TIME)),
        returns=P(items=P(prefix_items=(TIME, P(role='viseme')))),
        constraints=(
            'Requires finite 0<=start<end. Replaces track keys inside the closed span with open/closed '
            'mouth states at 0.12-second intervals; preserves and sorts keys outside. The last closed '
            'key is on the sample grid at or before end, so it holds through end. No scene is drawn.',
        ),
    ),
}

_CONTRACTS = {
    'collage-food': placed(
        'the food center',
        ('kind', P(enum=('taco', 'sushi', 'soup', 'pizza'))),
        ('size', LOCAL),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'Positive size scales the reference drawing by round(size/240,4). It is an approximate width.',
        ),
    ),
    'collage-lasagna': placed(
        'the dish center reference',
        ('w', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, 'Positive w scales the whole layered dish by round(w/520,4).'),
    ),
    'collage-flip-card': placed(
        'the card center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('size', LOCAL),
        ('tilt', ANGLE),
        ('sides', P(items=P(prefix_items=(TIME, COPY)))),
        constraints=(
            FONT,
            'Positive w/h/size. Nonempty sides have finite nonnegative strictly increasing project times '
            'below 86400. All copy and times are checked before drawing. Copy uses an estimated 0.62*size '
            'glyph width, 1.2*size leading and 30-pixel padding; this is not actual font measurement.',
            'Faces swap at their cues on project time. At each change scaleX linearly squeezes from 1 '
            'at cue-0.1 to 0 at the cue and returns to 1 at cue+0.1. Allow room between cues for full turns. '
            'The last face gates off at 86400; a single side has no scale animation.',
        ),
    ),
    'collage-magnifying-glass': placed(
        'the lens center',
        ('size', LOCAL),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'Positive size scales by round(size/420,4); the handle extends down. '
            'The translucent lens shows underlying artwork without magnifying or refracting it.',
        ),
    ),
    'collage-router': placed(
        'the router case center',
        ('w', LOCAL),
        ('light', P(items=P(prefix_items=(CANVAS_TIME, P(enum=('off', 'green', 'amber', 'red')))))),
        ('unplugged', CANVAS_TIME),
        constraints=(
            'Positive w scales router, socket and cable together by round(w/320,4). Nonempty light cues '
            'start at zero and increase strictly. unplugged is nonnegative; it changes the drawn plug '
            'but does not change the light automatically. Held opacity gates follow Canvas.local_time, '
            'composition by default. Continuing states gate off at 86400.',
        ),
    ),
    'collage-phone': placed(
        'the outer frame top-left before rotation about its center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('screen', COLOR),
        ('tilt', ANGLE),
        returns=SCREEN,
        constraints=(STATIC, SCREEN_SCOPE, 'w/h must exceed 52; the screen rectangle is (w-52) by (h-52).'),
    ),
    'collage-battery-insert': placed(
        'the outer phone top-left',
        ('w', LOCAL),
        ('h', LOCAL),
        ('levels', P(items=P(prefix_items=(CANVAS_TIME, P(unit='percent', minimum=0, maximum=100))))),
        ('dead', CANVAS_TIME),
        returns=SCREEN,
        constraints=(
            FONT,
            SCREEN_SCOPE,
            'w/h must exceed 52. Nonempty level cues start at zero and increase strictly; percent is 0..100. '
            'Levels at 20 or below are red; zero still draws a minimum 2-percent fill. dead is a nonnegative '
            'time that overlays black without deleting earlier levels. Opacity gates follow Canvas.local_time; '
            'continuing states gate off at 86400. Percentage lettering is a fixed 200 pixels, not fitted.',
        ),
    ),
    'collage-bubble': placed(
        'the bubble top-left',
        ('text', COPY),
        ('w', LOCAL),
        ('h', LOCAL),
        ('size', LOCAL),
        constraints=(
            STATIC,
            FONT,
            'mine selects a green bubble with right tail; otherwise grey with left tail. '
            'Text is left-aligned inside a 26-pixel horizontal inset; no fit preflight is performed.',
        ),
    ),
    'collage-thumb': placed(
        'the thumb center reference',
        ('size', LOCAL),
        constraints=(STATIC, 'Positive size scales the whole drawing by round(size/170,4).'),
    ),
    'collage-alarm-clock': placed(
        'the clock top-left',
        ('w', LOCAL),
        ('text', COPY),
        constraints=(
            STATIC,
            FONT,
            'w is positive; height is 0.5*w. Red digits show literal text, not a running clock.',
        ),
    ),
    'collage-cereal-box': placed(
        'the box top-left before rotation about its center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, 'w/h are positive. Returns the centered outer group, not a top-left-local group.'),
    ),
    'collage-duvet': drawing(
        ('top', FIXED),
        ('colour', COLOR),
        constraints=(
            STATIC,
            'Fixed foreground across the 1080x1920 layout from a wavy top to y=1990. '
            'Folds retain their fixed coordinates when top changes; canvas resizing does not reflow it.',
        ),
    ),
    'collage-tablecloth': drawing(
        ('top', FIXED),
        ('colour', COLOR),
        constraints=(
            STATIC,
            'Fixed foreground slab from x=-60 to 1140, top to y=1990. '
            'Stripe lines end at y=1920. The returned group has no translation.',
        ),
    ),
    'collage-salt-shaker': placed(
        'the base center',
        ('size', LOCAL),
        constraints=(STATIC, 'Positive size scales the whole 140-pixel reference shaker by round(size/140,4).'),
    ),
    'collage-chip-bag': placed(
        'the bag center',
        ('w', LOCAL),
        ('h', LOCAL),
        ('label', COPY),
        ('colour', COLOR),
        ('size', LOCAL),
        constraints=(
            STATIC,
            FONT,
            'w/h are positive. size is the label lettering size; no label fit preflight. '
            'Scaling the returned group can illustrate deflation; no volume simulation is supplied.',
        ),
    ),
    'collage-chip': placed(
        'the chip center reference',
        ('part', P(enum=('whole', 'half', 'crumb'))),
        ('size', LOCAL),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'Positive size scales all parts by round(size/210,4), the whole-chip width reference. '
            'Half and crumb keep their smaller authored silhouettes; part does not animate a bite.',
        ),
    ),
    'collage-certificate': placed(
        'the certificate top-left before rotation about its center',
        ('text', COPY),
        ('w', LOCAL),
        ('h', LOCAL),
        ('size', LOCAL),
        ('tilt', ANGLE),
        constraints=(STATIC, FONT, 'w/h are positive. Returns the centered group; no text fit preflight is performed.'),
    ),
    'collage-snapshot': placed(
        'the print top-left before rotation about its center',
        ('w', LOCAL),
        ('tilt', ANGLE),
        constraints=(
            STATIC,
            'Positive w gives height 1.16*w. Returns the centered group. '
            'Its picture is a whole chip drawn in paths, not a photo asset or callback slot.',
        ),
    ),
    'collage-gust': drawing(
        ('frm', POINT),
        ('to', POINT),
        ('start', TIME),
        ('end', TIME),
        ('lines', P(role='stroke-count')),
        returns=replace(GROUP, space='parent'),
        constraints=(
            'Requires finite 0<=start<end. Root start/end limits its lifetime on the containing timeline; '
            'x/y/opacity keys explicitly use project time. Author in a project-aligned parent. '
            'No keyframe clock conversion is inferred from Canvas.local_time.',
            '120-pixel strokes travel linearly from frm to to in repeating 0.42-second passes, fading from '
            '0.9 to zero, with 46-pixel transverse offsets and 0.07-second staggering. lines is a loop count; '
            'zero or negative counts draw an empty group. This is an illustration, not airflow simulation.',
        ),
    ),
    'collage-bill': placed(
        'the bill center',
        ('text', COPY),
        ('w', LOCAL),
        ('h', LOCAL),
        ('size', LOCAL),
        constraints=(
            STATIC,
            FONT,
            'w/h are positive. legs toggles two drawn legs and feet; '
            'the caller supplies walking or falling animation. Copy has no fit preflight.',
        ),
    ),
    'collage-confetti': drawing(
        ('start', TIME),
        ('end', TIME),
        ('turn', TIME),
        ('count', P(role='piece-count')),
        ('key', P(role='random-seed')),
        constraints=(
            'Requires finite 0<=start<end and optional turn>=start. Root start/end limits its lifetime on '
            'the containing timeline; y/rotation keys explicitly use project time. Author in a project-aligned '
            'parent. Canvas.local_time does not rewrite those keys.',
            'Deterministic local random generator seeded by key. Pieces span x=30..1050 in the fixed portrait '
            'layout, initially y=-400..1500. y and rotation interpolate linearly. A turn before end reverses '
            'fall at 1.6 times its speed; later turns have no effect. count is a loop count; zero or negative '
            'draws an empty group. This is not a gravity or collision simulation.',
        ),
    ),
    'collage-arm': drawing(
        ('frm', POINT),
        ('to', POINT),
        ('width', LOCAL),
        ('side', P(role='screen-side')),
        returns=replace(GROUP, space='parent'),
        constraints=(STATIC, ARM),
    ),
}
