"""Saga everyday discovery: the hut and returns rooms, what stands in them, and their canvas clocks."""

from ._saga_set_contracts import AT, MUTATION, PIXELS, RATIO, SPANS, TIME, draw, room
from .contracts import ParameterContract as P
from .contracts import PartContract

COVER = 'Drawn after the cast it covers; returns None after appending under parent.'
SINCE = P(unit='seconds', timebase='canvas', minimum=0, description='Shows from this second; 0 shows it at once.')
PLACED = 'at is the placement point on the parent; returns None after appending under parent.'


def prop(*parameters: tuple[str, P], constraints: tuple[str, ...]) -> PartContract:
    return draw(('at', AT), *parameters, returns=MUTATION, handle=False, constraints=(PLACED, *constraints))


def set_piece(*constraints: str) -> PartContract:
    return draw(returns=MUTATION, handle=False, constraints=constraints)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'saga-hut': room(constraints=('Includes the signature marks on the shelf end.',)),
    'saga-hut-table': set_piece(COVER, 'Fixed table top and plank front; what stands on it is drawn after this.'),
    'saga-returns': room(
        constraints=('Includes both signature marks. The RETURNS sign and the No. 1 board need a font.',)
    ),
    'saga-returns-desk': set_piece(COVER, 'Fixed counter from the desk edge to the right of the frame.'),
    'saga-plate': prop(('width', PIXELS), constraints=('Static.',)),
    'saga-cup': prop(
        (
            'steam',
            P(unit='seconds', timebase='canvas', minimum=0, description='Inside the shot; fades in 0.4 seconds.'),
        ),
        ('pour', P(prefix_items=(TIME, TIME), description='The span tea falls in; clamped to end.')),
        constraints=('steam=None and pour=None draw only the cup.',),
    ),
    'saga-ration-bar': prop(('since', SINCE), constraints=('at translates the group; one end is bitten.',)),
    'saga-wince': prop(
        ('spans', SPANS), constraints=('At least one span, clamped to end; the ticks are gated to the spans.',)
    ),
    'saga-tooth': prop(
        ('start', P(prefix_items=(PIXELS, PIXELS), description='Where it appears; None rests it at at.')),
        ('falls', P(prefix_items=(TIME, TIME), description='0<=appears<lands<=end. Ignored without start.')),
        constraints=('It moves linearly in x and bounces 16 pixels on landing, for 0.14 seconds.',),
    ),
    'saga-benefits': prop(
        ('since', SINCE),
        constraints=(
            'since=None draws only the puck. Otherwise it is inside the shot, and the card fades in over 0.14 seconds.',
            'The card needs a font and matching font bytes.',
        ),
    ),
    'saga-form': prop(
        (
            'slide',
            P(
                items=P(items=P(unit='drawing pixels')),
                description='Rows of (second, x). Seconds rise from 0 or later; empty leaves the form still.',
            ),
        ),
        ('since', SINCE),
        ('pen_until', P(unit='seconds', timebase='canvas', description='Over 0 and at most end; None keeps the pen.')),
        constraints=('slide eases sine-in-out in x. Wrong row width raises SagaError.',),
    ),
    'saga-basket': prop(
        constraints=('at centres the rim. Use saga_everyday.hole_of(at) for where the panel hole lands.',)
    ),
    'saga-coupon': prop(
        (
            'track',
            P(
                items=P(items=P(description='Second, then x, y and scale.')),
                description='Nonempty rows of four finite numbers, whose seconds rise from 0 or later.',
            ),
        ),
        constraints=('Hidden before the first row and from the first row at scale 0 or less; at sets the rest pose.',),
    ),
    'saga-dim': prop(
        ('spans', SPANS),
        ('depth', RATIO),
        ('fade', P(unit='seconds', role='duration')),
        (
            'spared',
            P(
                items=P(items=P(unit='drawing pixels')),
                description='(x, y, w, h) boxes left undimmed, for lit things a dark room leaves readable.',
            ),
        ),
        constraints=(
            'Unused at is required by the shared call shape. At least one span, clamped to end, and 0<depth<=1.',
            'Dims everything drawn before it over the fixed frame, keyed in and out by fade.',
        ),
    ),
}
