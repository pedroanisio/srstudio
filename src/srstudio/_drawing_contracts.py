"""Authored discovery semantics for the core Cutout drawing families.

Every selection below is explicit and checked against its registered signature.
No parameter-name inference, builder execution or registration side effects occur here.
Other families remain undeclared until their own coordinate and clock rules are verified.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sr_core.scene import Composition, Group, Layer, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

TIME = P(unit='seconds', timebase='canvas')
START = P(unit='seconds', timebase='canvas', role='start')
END = P(unit='seconds', timebase='canvas', role='end')
DURATION = P(unit='seconds', role='duration')
SPAN = P(type=tuple[float, float], prefix_items=(START, END))
SPANS = P(type=Sequence[tuple[float, float]], items=SPAN)
SHOTS = P(type=Sequence[tuple[float, float]] | None, items=SPAN)
GROUP = P(type=Group, unit='drawing units', space='returned-group', anchors=(('origin', (0, 0)),))
NONE = P(type=type(None))
CACTUS = 'Replaces the signature cactus at its existing depth; on a signed canvas draw exactly one cactus.'


def _drawing(
    *,
    coordinates: tuple[str, ...] = (),
    dimensions: tuple[str, ...] = (),
    ratios: tuple[str, ...] = (),
    angles: tuple[str, ...] = (),
    parameters: tuple[tuple[str, P], ...] = (),
    returns: P = GROUP,
    constraints: tuple[str, ...] = (),
    parent: bool = True,
) -> PartContract:
    return PartContract(
        parameters=(
            ('cv', P(type=Canvas)),
            *(
                (('parent', P(type=Composition | Group | Symbol, description='A drawing parent in this canvas.')),)
                if parent
                else ()
            ),
            *((name, P(type=float, unit='parent units')) for name in coordinates),
            *((name, P(type=float, unit='drawing units')) for name in dimensions),
            *((name, P(type=float, unit='ratio')) for name in ratios),
            *((name, P(type=float, unit='degrees')) for name in angles),
            *parameters,
        ),
        returns=returns,
        capabilities=(('spatial_attachment', False),),
        constraints=(
            'Draws 2D geometry; does not create a spatial mesh, solve a grip or infer collision geometry.',
            'Coordinates pass to the drawing parent; resizing the canvas does not automatically fit this artwork.',
            *constraints,
        ),
    )


def prop(name: str) -> PartContract:
    return _PROPS[name]


def _slot(description: str) -> P:
    return P(
        type=Callable[[Group], object] | None,
        role='drawing-slot',
        description='Receives the existing local Group once during building; return is ignored. ' + description,
    )


def _placed(origin: str, **options) -> PartContract:
    constraints = options.pop('constraints', ())
    return _drawing(coordinates=('x', 'y'), constraints=(f'x/y places {origin}.', *constraints), **options)


def location(name: str) -> PartContract:
    return _LOCATIONS[name]


def graphic(name: str) -> PartContract:
    return _GRAPHICS[name]


_FIXED = 'The artwork uses fixed coordinates in the original 1080x1920 drawing; transform its parent to reposition it.'
_ORIGIN = 'x/y place the local drawing origin, not necessarily its bottom or center.'

_PROPS = {
    'papers': _drawing(
        coordinates=('x', 'y'),
        ratios=('scale',),
        angles=('angle',),
        parameters=(('seed', P(type=int)),),
        constraints=(_ORIGIN,),
    ),
    'woodgrain': _drawing(
        coordinates=('y', 'height'),
        parameters=(('seed', P(type=int)),),
        returns=NONE,
        constraints=('Grain spans a fixed horizontal range; y and height bound its vertical sampling.',),
    ),
    'office-art': _drawing(returns=NONE, constraints=(_FIXED,)),
    'plant': _drawing(constraints=(_FIXED,)),
    'chair': _drawing(
        parameters=(('style', P(type=str, enum=('black', 'gray'))),), returns=NONE, constraints=(_FIXED,)
    ),
    'chair-back': _drawing(
        parameters=(
            ('head', P(prefix_items=(P(unit='parent units'), P(unit='parent units'), P(unit='parent units')))),
        ),
        returns=NONE,
        constraints=(_FIXED, 'head is (x, y, radius), or None for an empty chair.'),
    ),
    'laptop': _drawing(returns=NONE, constraints=(_FIXED,)),
    'water-glass': _drawing(returns=NONE, constraints=(_FIXED,)),
    'candidate-back': _drawing(returns=NONE, constraints=(_FIXED,)),
    'silent-phone': _drawing(
        coordinates=('x', 'y'),
        angles=('rotation',),
        parameters=(('label', P(type=str)),),
        constraints=('The origin is the top-left of the 280x160 phone body.',),
    ),
    'coffee-cup': _drawing(
        parameters=(
            (
                'x',
                P(type=float | str | None, unit='parent units', description='Number or sr-core relative coordinate.'),
            ),
            (
                'y',
                P(type=float | str | None, unit='parent units', description='Number or sr-core relative coordinate.'),
            ),
            ('scale', P(type=float | str | None, unit='ratio', description='Finite number or numeric lexical form.')),
            (
                'rotation',
                P(type=float | str | None, unit='degrees', description='Finite number or numeric lexical form.'),
            ),
            ('shadow', P(type=bool)),
        ),
        returns=P(
            type=Group,
            unit='drawing units',
            space='returned-group',
            anchors=(('origin', (0, 0)), ('base', (0, 61.5)), ('body-center', (0, 24))),
        ),
        constraints=(
            _ORIGIN,
            'Use shadow=False while held in the air. Anchors align a drawing; they are not a solved grip.',
        ),
    ),
    'reaching-hand': _drawing(
        coordinates=('x', 'y'),
        dimensions=('grip',),
        ratios=('scale',),
        angles=('rotation',),
        parameters=(
            (
                'holds',
                P(
                    type=Callable[[Group], object] | None,
                    role='drawing-slot',
                    description='Draws in the hand group, after the palm and before the fingers. Return is ignored.',
                ),
            ),
        ),
        returns=P(type=Group, unit='drawing units', space='returned-group', anchors=(('grip', (0, 0)),)),
        constraints=(
            'x/y places the grip. grip is the carried drawing half-width in local drawing units.',
            'The arm extends down out of frame; this is a flat hand and sleeve, not an articulated spatial arm.',
            'Parent the carried prop in holds to share all hand transforms and its canvas-clock animation.',
        ),
    ),
    'menu-board': _drawing(
        parameters=(
            (
                'items',
                P(
                    type=Sequence[tuple[str, str, float, float, float, str]],
                    items=P(
                        prefix_items=(
                            P(),
                            P(),
                            P(unit='parent units'),
                            P(unit='parent units'),
                            P(unit='parent units'),
                            P(),
                        )
                    ),
                ),
            ),
        ),
        returns=NONE,
        constraints=(_FIXED, 'Each item is (id, text, y, height, font_size, color).'),
    ),
    'cafe-window': _drawing(
        constraints=(_FIXED, 'Returns only the clipped view group; the frame is drawn directly in parent.')
    ),
    'pendant-light': _drawing(
        coordinates=('x',), returns=NONE, constraints=('x is the cord center; vertical coordinates are fixed.',)
    ),
    'bean-jar': _drawing(
        coordinates=('x',), returns=NONE, constraints=('x is the jar body left edge; its bottom is y=1012.',)
    ),
    'espresso-machine': _drawing(
        returns=NONE,
        constraints=(_FIXED, 'Steam uses the engine expression variable time; no independent steam timeline.'),
    ),
    'pastry-stand': _drawing(returns=NONE, constraints=(_FIXED,)),
    'building': _drawing(
        coordinates=('x', 'y', 'w', 'h'),
        returns=NONE,
        constraints=('x/y are the building top-left. Windows retain the original scene clipping limits.',),
    ),
    'tree': _drawing(
        constraints=(_FIXED, 'Returns only the animated canopy group; the trunk is drawn directly in parent.')
    ),
    'shrub': _drawing(coordinates=('x',), returns=NONE, constraints=('The stem meets the ground at (x, 1410).',)),
    'park-sign': _drawing(returns=NONE, constraints=(_FIXED, 'text=None omits lettering.')),
    'bench': _drawing(returns=NONE, constraints=(_FIXED,)),
    'crumbs': _drawing(
        coordinates=('x', 'y', 'ground'),
        parameters=(('toss', START),),
        constraints=(
            'x/y is the hand origin; ground is an absolute parent y below it. Crumbs fall in canvas seconds.',
        ),
    ),
    'whiteboard': _drawing(
        coordinates=('x', 'y', 'w', 'h'),
        parameters=(('rising', P(type=bool)),),
        constraints=('The returned group is untransformed; x/y locate geometry inside it. w and h are at least 160.',),
    ),
    'blinds-window': _drawing(
        coordinates=('x', 'y', 'w', 'h'),
        constraints=('The returned group is untransformed; x/y locate the window frame inside it.',),
    ),
    'speakerphone': _drawing(
        coordinates=('x', 'y'),
        parameters=(('talk', SPANS),),
        constraints=('x/y place the local origin. talk spans are ordered, disjoint and use the canvas clock.',),
    ),
    'globe-pendant': _drawing(
        coordinates=('x', 'y', 'r'),
        parameters=(('light', P(type=Group | None)),),
        constraints=(
            'x/y is the globe center inside an untransformed group. light receives the halo in the same coordinates.',
        ),
    ),
    'slat-wall': _drawing(
        coordinates=('x', 'y', 'w', 'h'),
        parameters=(('light', P(type=Group | None)),),
        constraints=(
            'x/y locate the wall inside an untransformed group. light receives its wash in the same coordinates.',
        ),
    ),
    'reception-counter': _drawing(
        coordinates=('x0', 'x1', 'top', 'bottom'),
        constraints=('Coordinates bound the counter in an untransformed returned group.',),
    ),
    'tip-tablet': _drawing(
        coordinates=('x', 'y'),
        ratios=('scale',),
        parameters=(('picks', P(items=P(prefix_items=(TIME, P(role='option-index'))))),),
        constraints=('x/y is the tablet foot. Each pick holds its option index until the next canvas time.',),
    ),
    'card-reader': _drawing(
        coordinates=('x', 'y'),
        ratios=('scale',),
        parameters=(('readings', P(items=P(prefix_items=(TIME, P(), P())))),),
        constraints=('x/y is the terminal foot. Readings are (canvas time, amount, label), beginning at time zero.',),
    ),
    'pink-slip': _drawing(
        coordinates=('x', 'y'),
        ratios=('scale',),
        angles=('rotation',),
        parameters=(('show', P(prefix_items=(START, END))), ('fall', P(prefix_items=(START, P(unit='parent units'))))),
        constraints=('x/y is the envelope center. show and fall are mutually exclusive; fall=(canvas time, height).',),
    ),
    'parcel': _drawing(
        coordinates=('x', 'y'),
        ratios=('scale',),
        returns=P(
            type=Group, unit='drawing units', space='returned-group', anchors=(('center', (0, 0)), ('base', (0, 80)))
        ),
        constraints=('x/y is the box center. label=None leaves its label blank.',),
    ),
}


def _location(
    slots: tuple[tuple[str, str], ...], *, parameters: tuple[tuple[str, P], ...] = (), constraints: tuple[str, ...] = ()
) -> PartContract:
    return _drawing(
        parameters=(
            ('shots', SHOTS),
            *(
                (
                    name,
                    P(
                        type=Callable[[Group], object] | None,
                        role='drawing-slot',
                        description='Receives one existing drawing Group; its return value is ignored. ' + description,
                    ),
                )
                for name, description in slots
            ),
            *parameters,
        ),
        constraints=(
            _FIXED,
            'shots are canvas-clock visibility spans; callbacks are invoked once while building.',
            *constraints,
        ),
    )


_DEPTH = P(unit='pixels', description='Positive far-plane blur radius, or None for no blur.')
_LOCATIONS = {
    'office-wide': _location(
        (('at_desk', 'After the chair and before the desk front and foreground candidate.'), ('cactus', CACTUS)),
        parameters=(('depth', _DEPTH), ('instanced', P(type=bool))),
        constraints=('instanced=True cannot combine with depth or a cactus callback.',),
    ),
    'office-desk': _location(
        (('behind_desk', 'After the optional chair and before the desk front.'), ('cactus', CACTUS)),
        parameters=(('instanced', P(type=bool)),),
        constraints=('instanced=True cannot combine with a cactus callback.',),
    ),
    'office-reverse': _location(
        (('in_chair', 'After the optional chair and before the foreground desk.'), ('cactus', CACTUS)),
        parameters=(('depth', _DEPTH),),
    ),
    'cafe': _location(
        (
            ('behind_counter', 'Before the espresso machine and counter.'),
            ('on_counter', 'After the counter and pastry stand, before at_counter.'),
            ('at_counter', 'In front of the completed counter and its props.'),
            ('cactus', CACTUS),
        ),
        constraints=('menu is None or exactly three nonempty lines of at most 14 characters each.',),
    ),
    'park': _location(
        (('on_bench', 'After the bench and cactus.'), ('beside_bench', 'After on_bench.'), ('cactus', CACTUS))
    ),
    'conference-room': _location(
        (
            ('behind_table', 'After the chair, before the table.'),
            ('on_table', 'Receives the table group after its props.'),
            ('on_wall', 'After the optional whiteboard, before the light and chair.'),
        ),
        parameters=(('speaker_talk', SPANS),),
    ),
    'reception': _location(
        (
            ('behind_desk', 'Behind the counter.'),
            ('on_desk', 'Receives the separate desk-props group, after its monitor, vase and cactus.'),
            ('at_desk', 'In front of the counter.'),
            ('cactus', CACTUS),
        ),
        parameters=(('code_at', P(unit='parent units')),),
    ),
    'elevator': _location(
        (
            ('riders', 'In front of the elevator doors.'),
            ('on_floor', 'In front of riders.'),
            ('hallway', 'Receives the main location group, outside the blur, before the doors and surrounding wall.'),
        ),
        parameters=(
            ('floors', P(items=P(prefix_items=(TIME, P(role='floor-number'))))),
            ('doors', SPANS),
            ('depth', _DEPTH),
        ),
        constraints=('floors are canvas-time/floor-number keys; doors are canvas-time opening/closing triggers.',),
    ),
}


def _graphic(
    *,
    coordinates: tuple[str, ...] = ('x', 'y'),
    dimensions: tuple[str, ...] = (),
    angles: tuple[str, ...] = (),
    parameters: tuple[tuple[str, P], ...] = (),
    constraints: tuple[str, ...] = (),
    show: bool = True,
) -> PartContract:
    return _drawing(
        coordinates=coordinates,
        dimensions=dimensions,
        angles=angles,
        parameters=(*((('show', SPAN),) if show else ()), *parameters),
        constraints=('Text needs a bound font asset. Animation keys use the canvas clock.', *constraints),
    )


_GRAPHICS = {
    'episode-slate': _graphic(
        dimensions=('w', 'h', 'badge_h', 'title_x', 'title_w', 'title_size', 'radius', 'badge_radius'),
        show=False,
        parameters=(('fade', P(type=tuple[float, float, float], prefix_items=(TIME, TIME, TIME))),),
        constraints=(
            'x/y is the top-left. fade contains the three arrival times for opacity 1, 1, 0 after time-zero opacity 0.',
        ),
    ),
    'quiz-card': _graphic(
        parameters=(('verdict_span', P(prefix_items=(START, END))),),
        constraints=('x/y places the card center at local (300, 100). Verdict defaults to the show span.',),
    ),
    'answer-bubble': _graphic(angles=('rotation',), constraints=('x/y places the bubble center at local (100, 80).',)),
    'scorecard': _graphic(
        dimensions=('w', 'row_h', 'heading_size', 'row_size', 'value_size', 'value_w', 'label_w'),
        constraints=('x/y is the settled top-left; the introduction animates y from y+50.',),
    ),
    'dashboard': _graphic(
        dimensions=('w', 'h'), constraints=('x/y is the settled top-left; the introduction animates y from y+50.',)
    ),
    'notification': _graphic(constraints=('x/y is the settled top-left; the introduction animates y and scale.',)),
    'password-card': _graphic(constraints=('x/y is the top-left; the introduction animates scale around the origin.',)),
    'location-slate': _graphic(constraints=('x/y is the banner top-left.',)),
    'connected-card': _graphic(constraints=('x/y is the card top-left.',)),
    'squeak-mark': _graphic(
        dimensions=('w', 'h', 'size'),
        angles=('rotation', 'wobble'),
        parameters=(('rate', P(type=float, unit='seconds', role='interval')),),
        constraints=(
            'x/y is the center, with local anchor (w/2, h/2). rate is time between alternating rotation keys.',
        ),
    ),
    'captions': _drawing(
        parent=False,
        coordinates=('x', 'y'),
        dimensions=('width', 'height', 'size', 'stroke_width'),
        parameters=(
            (
                'specs',
                P(
                    items=P(
                        prefix_items=(
                            P(unit='seconds', timebase='composition', role='start'),
                            P(unit='seconds', timebase='composition', role='end'),
                            P(),
                            P(),
                        )
                    )
                ),
            ),
        ),
        returns=P(type=list[Layer]),
        constraints=(
            'Adds layers directly to cv.comp. specs are (start, end, text, asset_id); x/y is each layer top-left.',
        ),
    ),
}
