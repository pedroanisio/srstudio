"""Authored Stick interview, porch and satnav contracts: fixed layouts, shot clocks and what each builder refuses."""

from ._stick_contract_base import END, FIXED, FONT, PIXEL, TIME, draw
from .contracts import ParameterContract as P
from .contracts import PartContract

SHOT = 'end is the positive shot length; StickDataError before drawing otherwise.'
BUZZ = P(items=TIME, description='Each second, inside the shot, shakes the phone sideways for 0.16 seconds.')
PATH = P(
    items=P(
        prefix_items=(TIME, P(unit='ratio', minimum=0, maximum=1.4, description='Depth along the path, over 0.')),
        description='Second, then depth; seconds rise and stay inside 0..end.',
    )
)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'stick-interview-room': draw(
        ('end', END),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            'Wall, door, window, plant, two chairs and the desk top; sit the figures, then draw the desk over them.',
        ),
    ),
    'stick-interview-desk': draw(
        ('end', END),
        ('opens', TIME),
        ('is_open', P(description='Draws the drawer already open.')),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            FONT,
            'Includes the signature marks. opens and is_open are exclusive; the font is required only when the drawer '
            'contents can show.',
            'The drawer slides out through five held drawings of 1/16 second, which must finish before end.',
        ),
    ),
    'stick-desk-page': draw(
        ('x', PIXEL),
        ('y', PIXEL),
        ('face_down', P(description='Shows the blank back.')),
        ('ringed', P(description='Rings one line in red; refused with face_down.')),
        local=True,
        constraints=('x/y is the middle of the sheet, translated on the returned group. Static and unlettered.',),
    ),
    'stick-resume-insert': draw(
        ('end', END),
        ('line', P(role='display-copy', description='Nonblank and at most 14 letters.')),
        handle=False,
        constraints=(FIXED, SHOT, FONT, 'Fills the frame. Static; includes the signature marks. It names nobody.'),
    ),
    'stick-hall': draw(
        ('end', END),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            'Includes the signature marks on the shelf and a yard through the doorway. end only validates the shot; '
            'the drawing is static.',
        ),
    ),
    'stick-front-door': draw(
        ('end', END),
        ('opens', TIME),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            'opens=None draws the door standing open. Otherwise it holds shut until opens and swings in through four '
            'drawn frames of 1/24 second, which must finish before end.',
        ),
    ),
    'stick-tow-truck': draw(
        ('end', END),
        ('path', PATH),
        ('drop', TIME),
        constraints=(
            SHOT,
            'path=None parks the truck, hook down. Otherwise position and size ease sine-in-out through path. drop '
            'lowers the hook over 0.8 seconds, inside the shot.',
            'The beacon runs to end. Unbranded. Placement and size animate on the returned group.',
        ),
    ),
    'stick-rough-road': draw(
        ('end', END),
        ('surface', P(enum=('street', 'gravel', 'grass'))),
        ('fence', P(unit='seconds', timebase='canvas', minimum=0, description='Over 0 and at most end.')),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            'Ground marks run to fence or end, and the frame shakes on gravel and grass. fence brings a fence up to '
            'its full size with cubic-out, and the car stops there.',
        ),
    ),
    'stick-nav-insert': draw(
        ('end', END),
        ('screen', P(enum=('straight', 'recalculating', 'apologize', 'fence', 'couch'))),
        ('buzz', BUZZ),
        handle=False,
        constraints=(
            FIXED,
            SHOT,
            FONT,
            'Fills the frame. The map and instruction are invented, and masked to the fixed phone screen.',
        ),
    ),
}
