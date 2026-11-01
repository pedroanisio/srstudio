"""Authored placement, clocks and callback spaces for the remaining Cutout families.

Declarations describe existing drawings, not inferred capabilities. No builder is
imported or executed here; registration checks each declaration against its signature.
"""

from sr_core.scene import Group

from ._drawing_contracts import CACTUS, DURATION, END, SPANS, START, TIME, _drawing, _location, _placed, _slot
from .contracts import ParameterContract as P
from .contracts import PartContract

_TEXT_KEYS = P(items=P(prefix_items=(TIME, P())))
_DEPTH = P(unit='pixels', description='Far-plane blur radius.')
_ACTOR = P(type=Group, description='The Cutout actor group; clothing uses its existing actor-local coordinates.')
_CLOTHING = 'Fixed Cutout shoulders and torso geometry; does not retarget clothing or solve anatomy.'
_FONT = 'Lettering requires a bound font asset.'
_READINGS = 'Readings begin at canvas time zero, rise strictly, and hold until the next, with a finite final gate.'


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    # Handed props and clothing.
    'cv-folder': _placed(
        'the folder center',
        ratios=('scale',),
        parameters=(('open_spans', SPANS),),
        constraints=(_FONT, 'The root has a fixed -1.5-degree rotation; open_spans use the canvas clock.'),
    ),
    'phone-post': _placed(
        'the phone center',
        ratios=('scale',),
        dimensions=('message_shift', 'mitts_in'),
        parameters=(
            ('liked_at', TIME),
            ('message_at', TIME),
            ('date', P(description='Displayed date text; not an animation timestamp.')),
        ),
        constraints=(
            _FONT,
            'message and message_at must be supplied together. message is (sender, text).',
            'message_shift and mitts_in move details inside the scaled phone, in drawing units.',
        ),
    ),
    'big-thumb': _placed('the thumb tip', ratios=('scale',), angles=('rotation',)),
    'coat-over': _drawing(
        parent=False,
        parameters=(('parent', _ACTOR), ('left_at', TIME), ('right_at', TIME), ('bottom', P(unit='actor units'))),
        constraints=(_CLOTHING, 'bottom is the actor-local hem y. Each side wraps over 0.25 canvas seconds.'),
    ),
    'cafe-door': _placed('the door top-left', dimensions=('width', 'height'), constraints=(_FONT,)),
    # Hiring office.
    'job-ad': _placed('the middle of the sign foot', ratios=('scale',), constraints=(_FONT,)),
    'crayon-cv': _placed(
        'the sheet top middle', ratios=('scale',), parameters=(('swings', SPANS),), constraints=(_FONT,)
    ),
    'crib': _placed(
        'the middle of the feet',
        ratios=('scale',),
        parameters=(('rattles', SPANS),),
        constraints=(_FONT, 'Mobile keys at canvas times 0, 2 and 4 are independent of rattles.'),
    ),
    'paper-hat': _placed('the brim center', ratios=('scale',), constraints=(_FONT,)),
    'roller-blind': _placed(
        'the blind top-left',
        dimensions=('w', 'h'),
        parameters=(('snap', TIME),),
        constraints=('snap=None leaves the blind closed. Cord anticipation starts 0.2 seconds before snap.',),
    ),
    'hiring-office': _location(
        (
            ('next_room', 'Receives the next-room subgroup in room coordinates, before glass and blind.'),
            ('behind_desk', 'Receives the root before the desk, whose far edge is y=1040.'),
            ('on_desk', 'Receives the root after desk and signatures.'),
        ),
        parameters=(
            ('snap', TIME),
            ('depth', _DEPTH),
            (
                'code',
                P(
                    prefix_items=(P(unit='parent units'), P(unit='parent units'), P(unit='drawing units')),
                    description='Signature text (right-aligned x, y, font size).',
                ),
            ),
        ),
        constraints=('next_room artwork is not clipped; author it inside the visible next-room area.',),
    ),
    # Home and shop.
    'desk-printer': _placed(
        'the middle of the foot',
        ratios=('scale',),
        parameters=(('lcd', _TEXT_KEYS), ('whirs', SPANS), ('sheets', P(items=P(prefix_items=(START, DURATION, P()))))),
        constraints=(
            _FONT,
            _READINGS,
            'sheets are (start, duration, text color). Each sheet slides out over duration, then stays until the next.',
        ),
    ),
    'ransom-note': _placed(
        'the page top-left',
        dimensions=('height', 'size'),
        constraints=(_FONT, 'The page is 840 drawing units wide; its root gets a seeded small rotation.'),
    ),
    'hostage-photo': _placed('the photo top-left', ratios=('scale',), angles=('rotation',)),
    'paper-bag': _placed('the middle of the foot', ratios=('scale',)),
    'home-study': _location(
        (
            ('behind_desk', 'Receives the root before the desk, whose far edge is y=960.'),
            ('on_desk', 'Receives the root after desk and signatures.'),
            ('cactus', CACTUS + ' Receives the root, without an automatic position or scale transform.'),
        ),
        parameters=(('depth', _DEPTH),),
    ),
    'shop-till': _location(
        (('on_counter', 'Receives the root after counter and signatures; counter far edge y=1120.'),),
        parameters=(('depth', _DEPTH),),
    ),
    # Small props, stationery, food and badges.
    'lettered-cup': _placed('the cup drawing center', ratios=('scale',), constraints=(_FONT,)),
    'crayon-page': _placed('the sheet center', ratios=('scale',), angles=('rotation',)),
    'cake-knife': _placed(
        'the handle grip', ratios=('scale',), angles=('rotation',), constraints=('The unrotated blade points down.',)
    ),
    'cake-slice': _placed('the plate center', ratios=('scale',)),
    'wall-plaque': _placed(
        'the plaque center',
        ratios=('scale',),
        parameters=(('read', SPANS),),
        constraints=('read spans replace scrawl with legible text and require a bound font; otherwise no lettering.',),
    ),
    'sheet-cake': _placed('the board middle', ratios=('scale',), constraints=(_FONT,)),
    'id-lanyard': _placed(
        'the loop top',
        ratios=('scale',),
        parameters=(
            (
                'photo',
                _slot(
                    'Receives the photo child at local y=178, after its background and before the card label. '
                    'Draw around (0, 0) in an 88x84 window starting at (-44, -44); artwork is not clipped.'
                ),
            ),
        ),
        constraints=(_FONT,),
    ),
    'paper-streamers': _drawing(
        coordinates=('x0', 'x1', 'y', 'sag'),
        constraints=(
            'Root is untransformed; x0/x1 bound the garland, y is the string height, sag is its downward dip.',
        ),
    ),
    # Phones and map glyphs.
    'table-phone': _placed(
        'the phone center', ratios=('scale',), parameters=(('rings', SPANS), ('speaker', SPANS), ('lit', SPANS))
    ),
    'location-chip': _placed(
        'the map center',
        ratios=('scale',),
        parameters=(('stops', P(items=P(prefix_items=(START, END, P(enum=('table', 'cross', 'moon')))))),),
        constraints=(
            'stops are ordered nonoverlapping (start, end, glyph) spans on the canvas clock.',
            'The root is translated only; scale sets the resting size of each animated stop subgroup.',
            'Invented map artwork, with no geographic lookup or GPS binding.',
        ),
    ),
    'notice-phone': _placed('the phone center', ratios=('scale',), parameters=(('at', TIME),), constraints=(_FONT,)),
    'dinner-plate': _placed('the plate center', ratios=('scale',)),
    'table-fork': _placed(
        'the handle grip', ratios=('scale',), angles=('rotation',), constraints=('The unrotated tines point up.',)
    ),
    'held-phone': _placed('the phone center', ratios=('scale',), constraints=('Shows the back of the phone.',)),
    # Odds and ends.
    'eaten-sandwich': _placed(
        'the sandwich center',
        ratios=('scale',),
        parameters=(('bites', P(items=TIME)),),
        constraints=('Up to three strictly rising bite instants shrink the right edge in held stages.',),
    ),
    'paper-napkin': _placed('the napkin center', ratios=('scale',)),
    'bistro-table': _placed('the tabletop center', dimensions=('width',)),
    'earbud': _placed('the bud center', ratios=('scale',), constraints=('flip reflects the drawing horizontally.',)),
    'tin-of-peas': _placed('the tin center', ratios=('scale',)),
    'store-box': _placed('the box center', ratios=('scale',)),
    'coin-purse': _placed(
        'the purse center', ratios=('scale',), parameters=(('opens', SPANS), ('id', P(type=str, role='node-id')))
    ),
    'small-coin': _placed('the coin center', ratios=('scale',)),
    'lane-sign': _placed(
        'the sign center', ratios=('scale',), parameters=(('numbers', _TEXT_KEYS),), constraints=(_FONT, _READINGS)
    ),
    'glasses-glint': _drawing(
        ratios=('scale',),
        parameters=(
            ('at', TIME),
            ('seconds', DURATION),
            ('lenses', P(items=P(prefix_items=(P(unit='drawing units'), P(unit='drawing units'))))),
        ),
        constraints=(
            'lenses are (x, y) centers inside the scaled root; author their alignment to the glasses.',
            'Star animation starts 0.08 seconds before at; visibility is clamped to start no earlier than zero.',
        ),
    ),
    'chair-lever': _placed(
        'the lever pivot',
        ratios=('scale',),
        parameters=(('pulls', P(items=TIME)),),
        constraints=('Each pull instant starts a 0.42-second tip and return on the canvas clock.',),
    ),
    'ballpoint': _placed('the nib', ratios=('scale',), constraints=('The root has a fixed 35-degree rotation.',)),
    # Office break room and party.
    'drip-machine': _placed('the middle of the foot', ratios=('scale',), parameters=(('pours', SPANS),)),
    'office-mug': _placed(
        'the middle of the foot',
        ratios=('scale',),
        constraints=('label=None omits lettering; otherwise needs a font.',),
    ),
    'days-board': _placed(
        'the board top middle', ratios=('scale',), parameters=(('counts', _TEXT_KEYS),), constraints=(_FONT, _READINGS)
    ),
    'wall-planner': _placed(
        'the page top-left', ratios=('scale',), parameters=(('months', _TEXT_KEYS),), constraints=(_FONT, _READINGS)
    ),
    'gold-watch': _placed(
        'the dial center',
        ratios=('scale',),
        parameters=(('gleam', TIME),),
        constraints=('gleam starts a 0.5-second local highlight crossing; None omits the highlight.',),
    ),
    'stage-mic': _placed('the stand foot', ratios=('scale',), dimensions=('height',)),
    'party-crowd': _drawing(
        coordinates=('y',),
        parameters=(('claps', SPANS),),
        constraints=('Root is untransformed; y sets head tops with seeded jitter, across a fixed horizontal range.',),
    ),
    'break-room': _location(
        (
            ('on_wall', 'Receives the root in focus, before behind_counter and the counter.'),
            ('behind_counter', 'Receives the root before the counter, whose far edge is y=1140.'),
            ('on_counter', 'Receives the root after counter and signatures.'),
        ),
        parameters=(('depth', _DEPTH),),
    ),
    'office-party': _location(
        (('stage', 'Receives the root after banner and signatures.'), ('front', 'Receives the root after stage.')),
        parameters=(('depth', _DEPTH),),
        constraints=(_FONT,),
    ),
    # Reference props and clothing.
    'cue-cards': _placed(
        'the card center',
        ratios=('scale',),
        parameters=(('spans', SPANS),),
        constraints=(_FONT, 'More than one word requires one ordered visibility span per word.'),
    ),
    'banknotes': _placed('the fan center', ratios=('scale',), constraints=(_FONT,)),
    'robe-and-blazer': _drawing(parent=False, parameters=(('parent', _ACTOR),), constraints=(_CLOTHING,)),
    # Barber shop.
    'barber-cape': _placed('the collar center, or top-edge center when spread', dimensions=('width', 'height')),
    'hedge-trimmer': _placed(
        'the motor center', ratios=('scale',), angles=('rotation',), constraints=('The bar extends right.',)
    ),
    'lawnmower': _placed(
        'the wheel baseline center',
        ratios=('scale',),
        parameters=(('facing', P(enum=(1, -1))),),
        constraints=('facing=-1 reflects local x; scale stays positive.',),
    ),
    'hair-fall': _drawing(
        parameters=(('falls', P(items=P(prefix_items=(START, DURATION)))),),
        constraints=(
            'falls are (start, duration), not start/end spans. Each sheet gates and moves on the canvas clock.',
            'Root is untransformed; blurred sheets cross fixed drawing coordinates from y=-760 to y=2000.',
        ),
    ),
    'barbershop': _location(
        (
            ('in_mirror', 'Receives the glass subgroup in room coordinates after the blurred room, before the frame.'),
            ('on_counter', 'Receives the root after counter and signatures.'),
        ),
        parameters=(('depth', _DEPTH),),
        constraints=(
            'Mirror artwork is not clipped and not mirrored automatically; '
            'author within BARBER_MIRROR (100,110,880,1150).',
            'A nonempty price requires a bound font asset.',
        ),
    ),
}
