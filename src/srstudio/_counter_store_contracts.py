"""Authored semantics for every counter/store drawing, verified against its coordinates and clock.

Selections are explicit, not derived from parameter names. Return annotations on
ChainRun retain their real type without importing the builder module during registration.
"""

from collections.abc import Callable
from dataclasses import replace

from sr_core.scene import Group

from ._drawing_contracts import SPAN, SPANS, START, TIME, _drawing, _location
from .contracts import ParameterContract as P
from .contracts import PartContract


def _slot(description: str) -> P:
    return P(
        type=Callable[[Group], object] | None,
        role='drawing-slot',
        description='Receives the existing local Group once during building; return is ignored. ' + description,
    )


def _placed(origin: str, **options) -> PartContract:
    constraints = options.pop('constraints', ())
    return _drawing(coordinates=('x', 'y'), constraints=(f'x/y places {origin}.', *constraints), **options)


_DRIFT = P(items=P(prefix_items=(TIME, P(unit='parent units'))))
_DURATION = P(unit='seconds', role='duration')

_CONTRACTS = {
    'hand-basket': _placed('the middle of the foot', ratios=('scale',)),
    'shopping-cart': _placed(
        'the wheel baseline center',
        ratios=('scale',),
        parameters=(('contents', _slot('After the handle and before the front wire; local floor y=-170.')),),
    ),
    'table-lamp': _placed('the middle of the foot', ratios=('scale',)),
    'taper-candles': _placed('the middle of the feet', ratios=('scale',)),
    'step-ladder': _placed('the middle of the feet', dimensions=('height',), ratios=('scale',)),
    'kayak': _placed(
        'the cockpit center',
        dimensions=('length', 'beam'),
        ratios=('scale',),
        angles=('rotation',),
        parameters=(
            ('rider', _slot('Between the cockpit and near hull; shares kayak placement, scale and rotation.')),
        ),
    ),
    'paddle': _placed(
        'the shaft midpoint',
        dimensions=('length',),
        ratios=('scale',),
        angles=('rotation',),
        constraints=('The unrotated shaft runs vertically, with tips at local y=+/-length/2.',),
    ),
    'life-ring': _placed('the ring center', ratios=('scale',)),
    'dark-eyes': _placed(
        'the point between the eyes',
        ratios=('scale',),
        parameters=(('blinks', SPANS), ('glances', P(items=P(prefix_items=(TIME, P(unit='drawing units')))))),
        constraints=('Blink spans close both eyes; glances linearly key the pupil group x on the canvas clock.',),
    ),
    'shelf-goods': _drawing(
        coordinates=('y',),
        dimensions=('width',),
        parameters=(('drift', _DRIFT),),
        constraints=(
            'Four shelves start at y, 260 units apart. drift keys root x in parent units; seed fixes box layout.',
        ),
    ),
    'store-aisle': _location(
        (('in_aisle', 'On the root after floor and signatures.'), ('front', 'After in_aisle, nearest the lens.')),
        parameters=(('drift', _DRIFT), ('depth', P(unit='pixels', description='Far-plane blur radius.'))),
        constraints=('drift moves shelves only; callbacks share the fixed 1080x1920 scene coordinates.',),
    ),
    'light-switch': _placed(
        'the plate center',
        ratios=('scale',),
        parameters=(('flips', P(items=TIME)),),
        constraints=(
            'Each flip starts a 0.04-second linear rocker movement; authored flip times are strictly rising.',
        ),
    ),
    'long-receipt': _placed(
        'the middle of the top edge',
        dimensions=('length',),
        parameters=(('printing', SPAN),),
        constraints=('printing scales local y from zero to one; length remains in unscaled drawing units.',),
    ),
    'checkout-lane': _drawing(
        coordinates=('y',),
        parameters=(('running', SPAN),),
        constraints=(
            'y is the far counter edge in an untransformed root. Belt marks move at -700 parent units/second.',
        ),
    ),
    'pen-on-chain': _drawing(
        coordinates=('x', 'y', 'length'),
        parameters=(
            ('grip', P(items=P(prefix_items=(TIME, P(unit='parent units'), P(unit='parent units'))))),
            ('snap', TIME),
            (
                'scale',
                P(
                    unit='ratio',
                    description='Positive appearance only: pen and link sizes, not grip coordinates or chain length.',
                ),
            ),
        ),
        returns=P(fields=(('taut', TIME), ('snap', TIME), ('home', TIME))),
        constraints=(
            'x/y is the fixed cradle in parent coordinates. grip rows are (canvas time, parent x, parent y).',
            'Returns ChainRun timing data, not the drawn group. Missing events are None.',
            'The flat chain stops the pen at length; it is not a spatial hand/contact solver.',
        ),
    ),
    'paper-poster': _placed(
        'the unrotated top-left',
        dimensions=('width', 'height', 'size'),
        angles=('tilt',),
        constraints=('The returned group origin is the sheet center; tilt rotates around that center.',),
    ),
    'jump-clock': _placed(
        'the clock center',
        dimensions=('radius',),
        parameters=(
            (
                'start',
                P(
                    prefix_items=(
                        P(unit='display hours', minimum=1, maximum=12),
                        P(unit='display minutes', minimum=0, maximum=59),
                    )
                ),
            ),
            ('jumps', P(items=P(prefix_items=(TIME, P(unit='display minutes'))))),
            ('spin', _DURATION),
        ),
        constraints=(
            'start is a displayed (hour, minute), not a scene time. Jumps advance display minutes over spin seconds.',
        ),
    ),
    'sandwich': _placed('the sandwich center', ratios=('scale',)),
    'qr-code': replace(
        _placed(
            'the square center',
            dimensions=('size',),
            constraints=('Seeded decorative pattern, not an encoded QR payload; no scannable content guarantee.',),
        ),
        capabilities=(('spatial_attachment', False), ('qr_payload_encoding', False)),
    ),
    'table-tent': _placed(
        'the center of the standing base',
        constraints=('The label is 1..10 stripped characters; its QR pattern is decorative.',),
    ),
    'cafe-table': _placed(
        'the center of the far edge', dimensions=('width',), constraints=('width is at least 200 drawing units.',)
    ),
    'paper-menu': _placed(
        'the sheet center',
        ratios=('scale',),
        angles=('rotation',),
        constraints=('lying multiplies vertical scale by 0.42. Rotation is -180..180 degrees.',),
    ),
    'soup-bowl': _placed('the bowl base center', ratios=('scale',)),
    'phone-screen': _placed(
        'the phone center', ratios=('scale',), constraints=('At most three nonempty lines, with an optional title.',)
    ),
    'rising-bubbles': _placed(
        'the emission origin',
        dimensions=('width', 'height'),
        parameters=(('start', START), ('seconds', _DURATION)),
        constraints=('seconds spaces bubble births; each bubble has its own seeded 0.45..0.7-second climb.',),
    ),
    'water-splash': _placed(
        'the splash origin',
        dimensions=('reach',),
        parameters=(('start', START),),
        constraints=('Seven seeded beads follow canvas-clock keys, not a physical fluid simulation.',),
    ),
    'back-room': _location(
        (('in_room', 'On the inner 1080x1920 room after wall and chairs, before the foreground hall and door.'),),
        parameters=(('push', SPAN), ('opens', START), ('id', P(type=str, role='node-id'))),
        constraints=(
            'push drives room and hall scales; the callback inherits the room camera transform. opens <= push start.',
        ),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]
