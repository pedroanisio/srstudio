"""Authored contracts for Toon core, props, sets, world drawings and headset data.

Reference geometry, frame typography, parent visibility and animation clocks are
separate declarations. No builder is imported, executed or inferred by name here.
"""

from collections.abc import Callable
from typing import Literal

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

REF = P(unit='reference pixels', space='toon-reference')
FONT_SIZE = P(unit='frame pixels', description='Font size passed to Canvas.text without reference scaling.')
RATIO = P(unit='ratio')
DURATION = P(unit='seconds', role='duration')
TIME = P(unit='seconds', timebase='canvas')
START = P(unit='seconds', timebase='canvas', role='start')
END = P(unit='seconds', timebase='canvas', role='end')
PARENT_START = P(unit='seconds', timebase='parent', role='start')
PARENT_END = P(unit='seconds', timebase='parent', role='end')
COMP_TIME = P(unit='seconds', timebase='composition')
SPANS = P(items=P(prefix_items=(START, END)))
STILL_END = P(
    unit='seconds', timebase='canvas', role='end', description='Animate from zero; zero omits looping motion.'
)
MEASURE = P(
    type=Callable[[str], float],
    role='text-measure',
    description='Called with text; return advance width in frame pixels at the requested font size. Does not draw.',
)
FONT = 'Lettering requires a bound font asset; text lengths and measurements remain the builder\'s constraints.'
REFERENCE = (
    'Reference x maps through fx(x)=round(x*1080/592,2); reference y through fy(y)=round((y-70)*1080/592,2). '
    'Distances use fh without the y offset. These conversions do not adapt to canvas dimensions.'
)
CANVAS_CLOCK = (
    'Animation keys follow Canvas.local_time: composition by default, local when enabled. '
    'Visibility start/end attributes use their parent timeline; keep those clocks consistent when nesting.'
)
COMPOSITION_CLOCK = (
    'Animation keys explicitly use the composition clock even when Canvas.local_time is True. '
    'Visibility start/end attributes still use their parent timeline.'
)


def point(description: str) -> P:
    return P(space='toon-reference', prefix_items=(REF, REF), description=description)


def draw(
    *parameters: tuple[str, P], constraints: tuple[str, ...] = (), clock: Literal['canvas', 'composition'] = 'canvas'
) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=P(type=type(None), description='Draws into the supplied parent; returns no scene handle.'),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', False)),
        constraints=(
            REFERENCE,
            'Draws 2D artwork; no world-space attachment, collision geometry or anatomical solver is supplied.',
            COMPOSITION_CLOCK if clock == 'composition' else CANVAS_CLOCK,
            *constraints,
        ),
    )


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'toon-room': draw(
        constraints=('Wall background follows canvas dimensions; window and chair use fixed reference geometry.',)
    ),
    'toon-desk': draw(
        constraints=(FONT, 'Fixed laptop and desk geometry in front of the figure; includes signature marks.')
    ),
    'toon-captions': draw(
        ('lines', P(items=P(fields=(('start', PARENT_START), ('end', PARENT_END))))),
        ('measure', MEASURE),
        ('band', REF),
        constraints=(
            FONT,
            'measure(text) must use the caption font at 60 frame pixels; band is the pill top, not a time.',
        ),
    ),
    'toon-meeting': draw(constraints=('Fixed whiteboard and chair geometry; backdrop fills the canvas.',)),
    'toon-mug': draw(('x', REF), ('steam', SPANS), constraints=('x is the mug left edge; base is reference y=838.',)),
    'toon-clock': draw(
        ('at', point('Clock center.')),
        ('r', REF),
        ('times', P(items=P(prefix_items=(COMP_TIME, P(description='Displayed HH:MM; not an animation time.'))))),
        clock='composition',
        constraints=(
            'Nonempty rising time list; the first clock reading is held from zero. Hands jump between readings.',
        ),
    ),
    'toon-notes': draw(
        ('size', FONT_SIZE),
        constraints=(FONT, 'One to four nonblank notes, at most ten characters each, on the fixed laptop lid.'),
    ),
    'toon-toast': draw(
        ('items', P(items=P(fields=(('start', PARENT_START), ('end', PARENT_END))))),
        ('size', FONT_SIZE),
        clock='composition',
        constraints=(
            FONT,
            'Card visibility uses parent times; slide and buzz keys use those numbers on the composition clock.',
            'gated=True delays lettering by 0.25 seconds and requires at least 1.125 seconds per item.',
        ),
    ),
    'toon-board-text': draw(
        ('size', FONT_SIZE),
        ('start', PARENT_START),
        ('end', PARENT_END),
        constraints=(FONT, 'One to forty nonblank characters; None omits that visibility bound.'),
    ),
    'toon-logo': draw(
        ('sizes', P(items=P(prefix_items=(COMP_TIME, RATIO)))),
        (
            'shadow',
            P(
                prefix_items=(
                    P(unit='seconds', timebase='composition', role='start'),
                    P(unit='seconds', timebase='composition', role='end'),
                )
            ),
        ),
        clock='composition',
        constraints=(
            'Positive scales, changes at least 0.3 seconds apart. First scale holds from zero.',
            'Shadow is an optional absolute start/end span, not a duration.',
        ),
    ),
    'toon-badge': draw(
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('measure', MEASURE),
        ('size', FONT_SIZE),
        constraints=(FONT, 'measure receives uppercase text at size; visibility requires 0 <= start < end.'),
    ),
    'toon-kitchen': draw(
        constraints=(
            FONT,
            'Empty note omits lettering; a supplied fridge note has at most 14 characters.',
            'Counter top is reference y=500; chair=False leaves the chair out.',
        )
    ),
    'toon-note-insert': draw(
        ('start', START),
        ('end', END),
        constraints=(
            FONT,
            'This insert uses frame pixels directly: a fixed 760-pixel note centered in the canvas.',
            '0 <= start < end; at most 14 characters. Visibility uses parent times; '
            'push keys follow Canvas.local_time.',
        ),
    ),
    'toon-home': draw(('end', STILL_END)),
    'toon-coffee-machine': draw(
        ('at', point('Center and base of the machine.')),
        ('brewing', SPANS),
        constraints=(
            'Brewing spans are ordered, nonoverlapping absolute start/end pairs. Empty spans leave the machine still.',
        ),
    ),
    'toon-desk-lamp': draw(
        ('at', point('Center and base of the lamp.')),
        (
            'lit',
            P(
                items=P(prefix_items=(START, END)),
                description='None keeps the light on; an empty sequence keeps it off.',
            ),
        ),
        constraints=('Supplied lit spans are ordered and nonoverlapping.',),
    ),
    'toon-plant': draw(
        ('at', point('Center and base of the pot.')),
        ('scale', P(unit='ratio', minimum=0.3, maximum=3)),
        ('end', STILL_END),
        constraints=('scale changes the authored geometry around at; it is not a transform on a returned group.',),
    ),
    'toon-calendar': draw(
        ('at', point('Center of the calendar pad.')),
        (
            'pages',
            P(items=P(prefix_items=(TIME, P(description="Displayed date like OCT 14; not an animation timestamp.")))),
        ),
        constraints=(FONT, 'Nonempty rising pages must start at zero; each later date tears away the preceding page.'),
    ),
    'toon-call-centre': draw(
        ('end', STILL_END),
        ('waiting', P(items=P(prefix_items=(TIME, P(minimum=0, maximum=9999))))),
        constraints=(
            FONT,
            'Nonempty rising counts start at zero; counts are integers excluding booleans.',
            'legible=True and bright_count=True choose contrast-safe lettering; '
            'legacy defaults preserve published output.',
        ),
    ),
    'toon-far-wall': draw(),
    'toon-sofa-back': draw(constraints=('Draw behind the character; the separate sofa seat goes in front.',)),
    'toon-sofa': draw(
        ('ground', P(enum=('rug', 'bare', 'lawn', 'flatbed', 'heap'))),
        constraints=(
            FONT,
            'Seat, side table and ground are fixed reference geometry; signed=False omits signature marks.',
        ),
    ),
    'toon-worktop': draw(
        constraints=(FONT, 'top, front and code are paint colors, not geometric coordinates or source text.')
    ),
    'toon-yard': draw(
        constraints=('sign=None omits sign lettering; table=False omits the TV and table. Lettering needs a font.',)
    ),
    'toon-road': draw(
        ('start', START),
        ('end', END),
        constraints=(
            '0 <= start < end. Hand-drawn planes drift at authored speeds; duration increases generated geometry.',
        ),
    ),
    'toon-dump': draw(),
    'toon-gull': draw(
        ('at', point('Landing point under the feet.')),
        ('land', TIME),
        ('end', END),
        constraints=('A 0.5-second flight begins before land; require 0.5 <= land < end. The bird stays until end.',),
    ),
    'toon-paw': draw(
        ('spans', SPANS),
        ('y', REF),
        ('reach', REF),
        ('slide', DURATION),
        ('presses', P(items=TIME)),
        ('side', P(enum=(1, -1))),
        ('holding', P(enum=('remote', 'note', 'keys', 'torch', 'pencil', ''))),
        constraints=(
            'Each span must allow twice slide for entry and exit. Side 1 enters from the right, -1 from the left.',
            'holding selects a built-in drawing, not a callback or solved spatial grip. '
            'Presses outside each span are ignored.',
        ),
    ),
    'toon-snores': draw(
        ('at', point('Starting position of each Z.')),
        ('spans', SPANS),
        constraints=('A new Z appears every 0.7 seconds and rises 90 reference pixels.',),
    ),
    'toon-night-street': draw(
        ('leave', P(items=TIME)),
        ('end', END),
        constraints=(
            FONT,
            'At most seven leave times, assigned left to right; each needs 1.15 seconds before end.',
            'end bounds departures; it does not hide the entire scene. said is displayed phone text.',
        ),
    ),
    'toon-press-room': draw(
        ('flashes', P(items=P(unit='seconds', timebase='parent'))),
        constraints=('Each flash is visible for 0.09 parent seconds. live=True adds lettering and requires a font.',),
    ),
    'toon-mics': draw(
        ('x', REF),
        ('top', REF),
        constraints=('x centers the microphone cluster; top sets microphone tops. Stems reach reference y=812.',),
    ),
    'toon-lower-third': draw(
        ('spans', P(items=P(prefix_items=(PARENT_START, PARENT_END, P())))),
        ('size', FONT_SIZE),
        (
            'measure',
            P(
                type=Callable[[str, int], float],
                role='text-measure',
                description='Called as measure(text, size); return advance width in frame pixels. Does not draw.',
            ),
        ),
        constraints=(FONT, 'Each nonblank line must measure at most 86% of canvas width.'),
    ),
    'toon-chopper': draw(
        ('start', START),
        ('end', END),
        ('sky', point('Helicopter hover center.')),
        (
            'over',
            P(
                type=Composition | Group | Symbol | None,
                role='drawing-parent',
                description='Optional foreground parent for the searchlight; must use the same coordinate frame '
                'and clock as parent. Not a callback.',
            ),
        ),
        constraints=('Requires at least one second from start to end; None puts the beam under parent.',),
    ),
    'toon-hall-chair': draw(),
    'toon-porch': draw(),
    'toon-van': draw(
        ('start', START),
        ('end', END),
        ('at', point('Van drawing center.')),
        constraints=('Requires at least 0.3 seconds; scales down and moves right until end.',),
    ),
    'toon-missed-slip': draw(
        ('start', START),
        ('end', END),
        constraints=(
            FONT,
            'A full-frame insert, not a local slip prop. Requires more than 0.7 seconds to arrive; '
            'text is 1..40 characters.',
        ),
    ),
    'toon-stuck-note': draw(
        ('start', START),
        ('stuck', TIME),
        ('at', point('Note center.')),
        ('reach', REF),
        constraints=(
            FONT,
            'No end bound: the note remains. stuck=None starts at rest; otherwise it must follow start '
            'and lettering waits until arrival.',
        ),
    ),
    'toon-headset': PartContract(
        parameters=(
            (
                'look',
                P(
                    unit='reference pixels',
                    space='toon-reference',
                    role='drawing-look',
                    description='Authored Look with silhouette and face landmarks in reference coordinates.',
                ),
            ),
        ),
        returns=P(
            unit='reference pixels',
            space='toon-reference',
            description='Ordered (cubic shape, paint) layers; no scene mutation. Pass as figure stickers.',
        ),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', False), ('geometry_data', True)),
        constraints=(
            REFERENCE,
            'Fits the supplied Look silhouette and face landmarks; mic=False omits the boom.',
            'No universal retargeting or anatomical fit is solved. Figure sticker placement owns lean/sigh transforms.',
        ),
    ),
}
