"""Authored Toon contracts for story props: alarm, cables, chat, drafts, interview, night car, screens, signal, tie.

Each declaration describes what the builder draws and refuses. No builder is imported or executed here.
"""

from dataclasses import replace

from ._toon_contracts import COMP_TIME, FONT, PARENT_END, PARENT_START, REF, draw, point
from ._toon_household_contracts import group
from .contracts import ParameterContract as P
from .contracts import PartContract

CUE = P(unit='seconds', timebase='parent', minimum=0, description='Visibility cue on the parent timeline.')
COMP_CUE = replace(COMP_TIME, minimum=0, description='Animation cue on the composition clock.')
INK = P(role='paint-color')
OBJECT_ID = P(role='scene-id', description='Scene id of the root group; ids must stay unique on a canvas.')
PARENT_SPAN = P(prefix_items=(PARENT_START, PARENT_END))
COMP_SPAN = P(prefix_items=(COMP_CUE, COMP_CUE))
MEASURE = P(
    role='text-measure',
    description='Called with text and font size; returns advance width in frame pixels. Does not draw.',
)
MOVES = P(
    items=P(prefix_items=(COMP_TIME, REF, REF), description='Composition second, then reference x and y.'),
    description='The first stop also sets the resting position.',
)
SCALE = P(unit='ratio', description='Multiplies the reference geometry; must be over 0.')
SIZE = P(unit='frame pixels', description='Font size passed to Canvas.text without reference scaling.')
COPY = P(role='display-copy')
KEEP_CLEAR = 'ToonDataError off the Toon frame, in the caption band or over the signature marks, before drawing.'
OFF_MARKS = 'ToonDataError off the Toon frame or over the signature marks, before drawing.'
CHIP_CLEAR = 'ToonDataError past the left or right frame edge, in the caption band or over the marks, before drawing.'
BAKED = 'The returned group has no translation: its geometry is baked at frame coordinates computed from at.'


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS: dict[str, PartContract] = {
    # Alarm.
    'toon-smoke-detector': group(
        ('at', point('The top middle of the ceiling plate.')),
        ('red', CUE),
        ('scale', SCALE),
        constraints=(
            BAKED,
            'red=None keeps the green light for the whole parent. Otherwise green ends and red with its halo starts '
            'at red, a cut with no fade.',
        ),
    ),
    'toon-folder': group(
        ('at', point('The folder center.')),
        ('opened', CUE),
        ('scale', SCALE),
        constraints=(
            BAKED,
            'opened=None stays shut with no photograph drawn. Otherwise the cover ends and the photograph starts at '
            'opened, a cut with no opening motion.',
        ),
    ),
    # Cables.
    'toon-cable-drawer': group(
        ('opens', COMP_CUE),
        ('closes', COMP_TIME),
        ('at', point('The drawer front center; the root group is translated here.')),
        ('end', P(unit='seconds', role='unused', description='Accepted and ignored: nothing is gated on it.')),
        ('id', OBJECT_ID),
        clock='composition',
        constraints=(
            'opens is finite and >= 0; closes is None or >= opens+0.14. The front scales to its open size over 0.14 '
            'seconds and back over 0.45 from closes. The knot shows from opens until closes+0.45.',
            'The start and end of the knot use the same seconds on the parent timeline as opens and closes use on the '
            'composition clock, so parent the drawer on a timeline starting at zero.',
        ),
    ),
    'toon-gray-cable': group(
        ('moves', MOVES),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', OBJECT_ID),
        clock='composition',
        constraints=(
            'moves is nonempty and strictly rising in time; 0<=start<end. Motion is linear between stops. A single '
            'stop draws no keys.',
        ),
    ),
    'toon-kitchen-bin': group(
        ('at', point('The middle of the bin foot.')),
        constraints=(BAKED, 'Static; returns the front so that what lands in it can be drawn behind.'),
    ),
    'toon-fridge-light': group(
        ('off', COMP_CUE),
        ('on', COMP_CUE),
        ('at', point('The display center.')),
        clock='composition',
        constraints=(
            BAKED,
            'off is None or >= 0. on needs off and comes after it. The case stays drawn while the display is out, and '
            'opacity holds between keys.',
        ),
    ),
    'toon-hill-window': group(
        ('out', P(items=COMP_CUE, description='One rising second per street light, or empty for lights left on.')),
        ('on', COMP_CUE),
        clock='composition',
        constraints=(
            'Backdrop fills the canvas. Fixed window and hill geometry; the street has a fixed number of lights.',
            'on is >= 0 and after the last of out. House windows go dark with the last street light.',
        ),
    ),
    # Chat.
    'toon-chat-phone': group(
        (
            'bubbles',
            P(
                items=P(fields=(('at', COMP_CUE), ('text', COPY))),
                description='Nonempty and strictly rising in time; all must fit the screen or nothing is drawn.',
            ),
        ),
        ('measure', MEASURE),
        ('at', point('The middle of the phone base; the root group is translated here.')),
        ('scale', P(unit='ratio', minimum=0.9, maximum=2.0)),
        ('face_from', COMP_CUE),
        ('buzz', P(items=COMP_CUE, description='Each second shakes the root x.')),
        ('id', OBJECT_ID),
        clock='composition',
        constraints=(
            FONT,
            KEEP_CLEAR,
            'face_from=0 draws no back of the phone. The app name in the title bar is fixed and invented.',
        ),
    ),
    'toon-chat-chip': group(
        ('text', COPY),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('measure', MEASURE),
        ('at', point('The chip center; the root group is translated here.')),
        ('size', SIZE),
        ('id', OBJECT_ID),
        clock='composition',
        constraints=(
            FONT,
            CHIP_CLEAR,
            'text is nonblank and 0<=start<end. The chip pops in by scale over 0.18 seconds from start.',
        ),
    ),
    # Drafts.
    'toon-laptop-screen': group(
        (
            'drafts',
            P(
                items=P(
                    fields=(('start', PARENT_START), ('end', PARENT_END), ('head', COPY), ('body', COPY)),
                    description='head is at most 16 characters; body is nonblank and at most 30.',
                )
            ),
        ),
        constraints=(
            FONT,
            'Nonempty, spans do not overlap and rise from 0<=start<end. The screen shows from the first start to the '
            'last end at fixed reference geometry; it is blank in any gap between drafts.',
        ),
    ),
    'toon-stuck-notes': group(
        (
            'notes',
            P(
                items=P(
                    fields=(('at', CUE), ('text', COPY)),
                    description='text is nonblank and at most 10 characters; each note appears at its second.',
                )
            ),
        ),
        constraints=(FONT, 'Notes take the fixed spots in order; more notes than spots are refused.'),
    ),
    'toon-magnifier': group(
        ('at', point('The lens center.')),
        ('scale', SCALE),
        constraints=(BAKED, 'Static; the handle runs down and to the left of the lens.'),
    ),
    'toon-exclaim': group(
        ('at', point('The middle of the mark.')),
        ('height', P(unit='reference pixels', minimum=0, description='Over 0.')),
        ('colour', INK),
        constraints=(BAKED, 'Drawn as a shape: it needs no font.'),
    ),
    'toon-corkboard': group(
        ('texts', P(items=COPY, description='Each is nonblank and at most 10 characters.')),
        ('slide', COMP_SPAN),
        clock='composition',
        constraints=(
            FONT,
            'Texts take the fixed spots in order; more texts than spots are refused. slide also sets the group start, '
            'and 0<=start<end. Without it the board stands from the parent start.',
        ),
    ),
    # Interview.
    'toon-wall-sign': group(
        ('text', P(role='display-copy', description='Nonblank and at most 26 characters, on one line.')),
        constraints=(FONT, 'Fixed plaque across the top of the wall.'),
    ),
    'toon-blind': group(
        ('drop', COMP_SPAN),
        ('down', P(description='Draws the blind down from the first frame.')),
        clock='composition',
        constraints=('Fixed geometry over the room window. drop and down are exclusive; 0<=start<end.',),
    ),
    'toon-tissue-box': group(
        ('at', point('The middle of the box foot.')), ('scale', SCALE), constraints=(BAKED, 'Static.')
    ),
    'toon-sample-tray': group(
        ('at', point('The middle of the tray foot.')),
        ('colours', P(items=INK, description='One to six bars.')),
        (
            'missing',
            P(
                prefix_items=(P(minimum=0), PARENT_END),
                description='Bar index and the second it is gone from, a cut on the parent timeline.',
            ),
        ),
        ('scale', SCALE),
        constraints=(BAKED,),
    ),
    'toon-paper': group(
        ('at', point('The middle of the sheet.')),
        ('scale', SCALE),
        constraints=(BAKED, 'Static and unlettered: its lines are a scrawl, so it needs no font.'),
    ),
    # Night car.
    'toon-night-cabin': draw(constraints=('Backdrop fills the canvas; the two seats stand at fixed reference x.',)),
    'toon-night-dash': draw(
        ('close', P(description='Fills the frame above the lip too, for a shot that has come down to the dash.')),
        constraints=('Includes both signature marks, drawn on the dash where a desk carries them.',),
    ),
    'toon-call-chip': group(
        ('name', COPY),
        ('reads', P(prefix_items=(P(unit='seconds', timebase='parent'), P(unit='seconds', role='displayed-reading')))),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('measure', MEASURE),
        ('at', point('The chip center; the root group is translated here.')),
        ('scale', P(unit='ratio', minimum=0.8, maximum=2.5)),
        ('lit_from', CUE),
        ('id', OBJECT_ID),
        constraints=(
            FONT,
            KEEP_CLEAR,
            'name is nonblank and upper-cased behind "CALL: ". reads is the reading shown at one second; the timer '
            'counts one per second from it and may not read under zero at start.',
            '0<=start<end, long enough to be read. A reading a cut would clip too short is merged with the next.',
            'The chip lights on the first reading edge at or after lit_from, so no text changes colour mid-reading. '
            'If no edge comes, it stays dim.',
        ),
    ),
    # Screens.
    'toon-laptop-lid': group(
        ('shut', COMP_CUE),
        clock='composition',
        constraints=(
            'Fixed geometry: the lid and foot the desk draws, without the desk. It folds onto its hinge in 0.22 '
            'seconds from shut, and stays folded.',
        ),
    ),
    'toon-notice': group(
        ('head', P(role='display-copy', description='Nonblank and at most 24 characters.')),
        ('verdict', P(role='display-copy', description='Nonblank and at most 24 characters.')),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('colour', INK),
        clock='composition',
        constraints=(
            FONT,
            'The span must last over 0.14 seconds: the card rises into place over that time from start. Fixed '
            'position under the desk edge.',
        ),
    ),
    # Signal.
    'toon-climb-chair': draw(
        ('at', point('The middle of the chair feet.')),
        constraints=(OFF_MARKS, 'The top of the back may not rise above reference y=200.'),
    ),
    'toon-table-legs': draw(constraints=('Fixed apron, floor and two legs, to be drawn over a ledge front.',)),
    'toon-raised-phone': draw(
        ('hand', point('The paw holding the phone.')),
        ('colour', INK),
        ('dark', INK),
        (
            'bars',
            P(
                items=P(prefix_items=(PARENT_START, P(minimum=0, maximum=4))),
                description='Readings: the first at start, rising, the last before end. Zero bars adds a cross.',
            ),
        ),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('down', P(unit='reference pixels', minimum=0, description='Forearm length; over 0.')),
        ('id', OBJECT_ID),
        constraints=(OFF_MARKS, 'The arm and phone never move; only the bar readings change, as cuts.'),
    ),
    'toon-upload-chip': draw(
        ('readings', P(items=P(fields=(('start', PARENT_START), ('end', PARENT_END), ('text', COPY))))),
        ('shares', P(items=P(unit='ratio', minimum=0, maximum=1), description='One per reading.')),
        ('measure', MEASURE),
        ('at', point('The chip center; the chip group is translated here.')),
        ('id', OBJECT_ID),
        constraints=(
            FONT,
            KEEP_CLEAR,
            'Each reading must fit the chip by measure at 50 frame pixels. The bar turns green at a share of 1. The '
            'chip shows from the first reading start to the last reading end.',
        ),
    ),
    'toon-sandwich-broom': draw(
        ('moves', replace(MOVES, description='At least two stops, strictly rising; the sandwich middle travels them.')),
        ('start', PARENT_START),
        ('end', PARENT_END),
        (
            'bite',
            P(unit='seconds', timebase='parent', description='start<bite<end; the whole sandwich cuts to bitten.'),
        ),
        ('tilt', P(unit='degrees')),
        ('id', OBJECT_ID),
        clock='composition',
        constraints=('moves ease sine-in-out; start, end and bite gate groups on the parent timeline.',),
    ),
    # Tie.
    'toon-necktie': group(
        ('at', point('The knot; the root group is anchored here.')),
        ('scale', SCALE),
        ('length', P(unit='reference pixels', minimum=60, description='At scale 1.')),
        ('swinging', COMP_SPAN),
        ('start', PARENT_START),
        ('end', PARENT_END),
        clock='composition',
        constraints=('swinging sways the rotation about the knot over 0<=start<end. No font.',),
    ),
    'toon-lanyard': group(
        ('at', point('The top middle of the card.')),
        ('scale', SCALE),
        ('neck', P(items=point('One strap end beside the throat.'), description='Exactly two points.')),
        ('start', PARENT_START),
        ('end', PARENT_END),
        constraints=(BAKED, 'The card is unlettered, so it needs no font. Static inside its span.'),
    ),
}
