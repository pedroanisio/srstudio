"""Authored Cutout hat and one-way interview contracts: placement origins, canvas clocks and refusals."""

from ._drawing_contracts import SPANS, TIME, _drawing, _placed
from .contracts import ParameterContract as P
from .contracts import PartContract

_ID = P(role='scene-id', description='Scene id of the root group; ids must stay unique on a canvas.')
_FONT = 'Lettering requires a bound font asset.'
_HATS = ('trilby', 'boater', 'visor', 'beanie', 'headset', 'hard-hat', 'chef')
_KEYS = 'Times use the canvas clock.'


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'hat-stack': _placed(
        "the first hat's brim",
        ratios=('scale',),
        parameters=(
            (
                'hats',
                P(
                    items=P(prefix_items=(P(enum=_HATS), TIME)),
                    description='Kind and landing time, from the bottom; nonempty, with times that never fall.',
                ),
            ),
            (
                'sway',
                P(
                    items=P(prefix_items=(TIME, P(unit='degrees'))),
                    description='Rotation keys taken by every seat, so they add up toward the top.',
                ),
            ),
            (
                'topple',
                P(
                    prefix_items=(TIME, P(enum=(1, -1))),
                    description='Time, at or after the last landing, and side. The stack is gone 0.55 seconds later.',
                ),
            ),
            ('id', _ID),
        ),
        constraints=(_KEYS, 'A hat landing at 0.14 seconds or later drops in and squashes; earlier ones just sit.'),
    ),
    'tiny-hat': _placed(
        "the brim's middle",
        ratios=('scale',),
        parameters=(('id', _ID),),
        constraints=('Static; 58 wide and 30 tall at scale 1.',),
    ),
    'recording-window': _drawing(
        parameters=(
            ('seconds', P(unit='seconds', role='displayed-reading', minimum=1, maximum=600)),
            ('end', P(unit='seconds', timebase='canvas', role='end', description='Positive; the end of the reel.')),
            ('stop', P(unit='seconds', timebase='canvas', minimum=0, description='Freezes the clock; before end.')),
            ('id', _ID),
        ),
        constraints=(
            _FONT,
            _KEYS,
            'Fixed 1080x1920 chrome drawn over the shot. The clock drops one label a second and the red dot blinks; '
            'stop freezes the clock and puts the dot out. An invented interface.',
        ),
    ),
    'meter-panel': _placed(
        'the panel top-left',
        parameters=(
            (
                'meters',
                P(
                    items=P(
                        prefix_items=(
                            P(role='display-copy', description='Nonblank and at most 10 characters.'),
                            P(items=P(prefix_items=(TIME, P(unit='ratio', minimum=0, maximum=1)))),
                        )
                    ),
                    description='One to four meters. Keys are nonempty, their times never fall and are at least 0.',
                ),
            ),
            ('id', _ID),
        ),
        constraints=(_FONT, _KEYS, 'Bars interpolate between keys. A fraction of 0 draws at 0.001.'),
    ),
    'face-box': _placed(
        'the middle of the corner marks',
        dimensions=('size',),
        parameters=(('spans', SPANS), ('color', P(role='paint-color')), ('id', _ID)),
        constraints=(_KEYS, 'size is positive, from the middle to a side. No spans means always shown.'),
    ),
    'green-tick': _placed(
        'the disc center',
        ratios=('scale',),
        parameters=(('at', TIME), ('id', _ID)),
        constraints=(_KEYS, 'Off until at, then popped in and kept; 160 across at scale 1.'),
    ),
    'cereal-bowl': _placed(
        "the middle of the bowl's foot",
        ratios=('scale',),
        parameters=(('id', _ID),),
        constraints=('Static; 190 wide at scale 1.',),
    ),
    'spoon': _placed(
        'the grip',
        ratios=('scale',),
        angles=('rotation',),
        parameters=(('id', _ID),),
        constraints=('Static, pointing up before rotation; 170 long at scale 1.',),
    ),
    'room-door': _placed(
        "the middle of the door's foot",
        ratios=('scale',),
        parameters=(('opens', TIME), ('id', _ID)),
        constraints=(
            _KEYS,
            'Hinged on the left; 190 by 560 at scale 1. opens swings the panel back over 0.35 seconds; None stays '
            'shut.',
        ),
    ),
}
