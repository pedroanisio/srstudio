"""Core Stick discovery without importing builders during their registration."""

from ._stick_contract_base import FIXED, FONT, PIXEL, TIME, draw
from .contracts import ParameterContract as P
from .contracts import PartContract

PARENT_TIME = P(unit='seconds', timebase='parent')
PLATE = P(
    fields=(
        ('fill', P(description='Paint color or url(#paint); referenced paint must exist in the canvas.')),
        ('path', P(unit='frame pixels', space='parent', role='path-data')),
    )
)
PARENT_LINE = P(fields=(('start', PARENT_TIME), ('end', PARENT_TIME), ('size', PIXEL)))
CANVAS_LINE = P(fields=(('start', TIME), ('end', TIME), ('size', PIXEL)))
LOOK = P(unit='ratio', minimum=-1, maximum=1)
FACE = P(
    fields=(
        ('eyes', P(enum=('open', 'wide', 'half', 'closed', 'happy', 'peek', 'peek-back'))),
        ('brows', P(enum=('flat', 'raised', 'angry', 'worried'))),
        ('mouth', P(enum=('flat', 'smile', 'frown', 'smirk'))),
        ('look', P(prefix_items=(LOOK, LOOK))),
    )
)
PARENT_VISIBILITY = (
    'Visibility uses start/end attributes on the parent timeline, independent of Canvas.local_time. '
    'A sequence shot supplies its shot timeline; an ordinary group start does not create a new clock.'
)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'stick-room': draw(
        handle=False,
        constraints=(
            FIXED,
            'Static study, desk and laptop. marks controls both signature marks; no room group is returned.',
        ),
    ),
    'stick-yard': draw(
        ('foliage', P(items=PLATE)),
        ('seed', P(role='random-seed')),
        handle=False,
        constraints=(
            FIXED,
            'foliage paths are traced frame coordinates, drawn back to front without automatic placement.',
            'seed controls fence-board jitter through a local deterministic generator. No animated foliage.',
            'Includes both signature marks; no yard group is returned.',
        ),
    ),
    'stick-hook': draw(
        ('lettering', PLATE),
        ('start', PARENT_TIME),
        ('end', PARENT_TIME),
        constraints=(
            FIXED,
            PARENT_VISIBILITY,
            'Traced lettering on a fixed white card. No font or text layout is requested; returns both together.',
        ),
    ),
    'stick-headline': draw(
        ('outline', PLATE),
        ('fill', PLATE),
        ('start', PARENT_TIME),
        ('end', PARENT_TIME),
        constraints=(
            FIXED,
            PARENT_VISIBILITY,
            'Draws the outline contour then the fill contour, stroked 1.2 frame pixels in its own fill color. '
            'No font or text layout; returns the group containing both contours.',
        ),
    ),
    'stick-captions': draw(
        ('lines', P(items=PARENT_LINE)),
        ('outline', P(enum=('stroke', 'layer', 'none'))),
        handle=False,
        constraints=(
            FIXED,
            FONT,
            PARENT_VISIBILITY,
            'Each cue is centered font text at the fixed caption band. stroke uses one outlined text layer; '
            'layer draws a separate ink text layer beneath white; none draws only white. No wrapping.',
        ),
    ),
    'stick-words': draw(
        ('cues', P(items=CANVAS_LINE)),
        ('y', PIXEL),
        ('scrim', P(unit='ratio', minimum=0, maximum=1)),
        handle=False,
        constraints=(
            FONT,
            'Each cue holds one nonblank line and ends after its start. y is the text box top; '
            'the word scales about its center. scrim is strictly positive through one.',
            'Words pop from scale 0.86 to 1.06 over 0.07 seconds, then settle to 1 by 0.14 seconds. '
            'Cue opacity and pop keys follow the canvas clock, not parent visibility attributes.',
            'Nearby cues share a feathered scrim, with 0.12-second fades; the final scrim fade can follow cue end.',
        ),
    ),
    'stick-card': draw(
        ('size', PIXEL),
        ('width', P(unit='frame pixels', maximum=900)),
        constraints=(
            FONT,
            'Nonblank text, balanced over at most three lines inside a white card.',
            'width=None uses the fixed card at x=90,y=300 with width=900. An explicit width must be '
            'greater than 70 and at most 900 and centers the card on the canvas. No visibility schedule.',
        ),
    ),
    'stick-call': draw(
        ('tiles', P(items=P(fields=(('face', FACE),)))),
        ('speaking', P(role='tile-name')),
        ('highlight', P(unit='row index', minimum=0)),
        constraints=(
            FIXED,
            FONT,
            'One to four uniquely named tiles and one to seven nonblank inbox rows. speaking is empty or '
            'matches a tile name; highlight is None or a zero-based inbox row index.',
            'Returns the complete static call screen. Faces are held drawings; the speaker ring does not '
            'animate speech, and the inbox is supplied data rather than a live service.',
        ),
    ),
}
