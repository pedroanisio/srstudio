"""Authored bed, ward and surgery semantics; geometry and clocks are not inferred from parameter names."""

from dataclasses import replace
from typing import Protocol

from sr_core.scene import Group

from ._toon_contracts import COMP_TIME, PARENT_END, PARENT_START, REF, draw, point
from ._toon_domestic_contracts import ID
from ._toon_household_contracts import group
from .contracts import ParameterContract as P
from .contracts import PartContract


class BandageLook(Protocol):
    """Only eye geometry is consumed; a full character look is not required."""

    eyes: tuple[tuple[float, float], tuple[float, float]]


DEGREES = P(unit='degrees')
PATTERN = P(enum=('plum', 'teal'))
POSITIVE_REF = P(unit='reference pixels', space='toon-reference', description='Finite and strictly greater than zero.')
STILL_END = P(
    unit='seconds',
    timebase='parent',
    role='end',
    description='Visibility end; zero draws a still with no visibility limits and ignores start.',
)
SLIDE_RULES = (
    'end=0 draws in place without animation; otherwise 0<=start<end.',
    'start sets parent visibility and the composition slide cue; a linear slide lasts 0.28 seconds.',
    'A shorter visibility span clips the slide before arrival. Use an unshifted parent to align the clocks.',
)

_CONTRACTS = {
    'toon-double-bed': group(
        constraints=(
            'day switches between a raised blind with sun and a closed night blind. No animation keys.',
            'Wall fills the canvas; headboard and pillows use fixed reference geometry. Draw the cast next.',
        )
    ),
    'toon-double-quilt': group(
        ('pattern', PATTERN),
        constraints=(
            'Draw in front of the cast and double bed. day adds static sun bands; no animated lighting.',
            'signed enables signature marks when the canvas has a signature; it does not supply a new signature.',
        ),
    ),
    'toon-bedroom-corner': group(
        constraints=('Wall and floor follow canvas dimensions; skirting and floorboards use fixed reference y.',)
    ),
    'toon-quilt-heap': group(
        ('pattern', PATTERN),
        ('x', REF),
        ('width', POSITIVE_REF),
        constraints=(
            'x is the left edge; heap top is reference y=836 and its foot reaches 20 frame pixels below the canvas.',
            'width changes the heap silhouette; patch sizes and column spacing remain fixed reference geometry.',
        ),
    ),
    'toon-bedside-drawer': replace(
        group(
            ('buzzes', P(items=P(unit='seconds', timebase='composition', minimum=0))),
            ('slides', P(unit='seconds', timebase='composition', minimum=0)),
            ('lit', P(unit='ratio', minimum=0, maximum=1)),
            clock='composition',
            constraints=(
                'Empty buzzes leave the front still; each cue emits a 0.3-second shake with frame-pixel offsets.',
                'slides=None omits opening and light. Opening scales the front over 0.45 seconds with sine-in-out.',
                'lit=0 omits light; otherwise its held opacity begins at slides and remains afterward.',
                'Create an outer parent to move or hide the whole cabinet; the returned front excludes the cabinet.',
            ),
        ),
        returns=P(
            type=Group,
            unit='frame pixels',
            space='parent',
            description='The moving drawer front, nested inside the cabinet group; not the whole nightstand.',
        ),
    ),
    'toon-swung-arm': group(
        ('shoulder', point('Shoulder pivot; place in the same drawing parent as the body.')),
        ('coat', P(description='A #rrggbb coat color.')),
        ('swing', P(items=P(prefix_items=(COMP_TIME, DEGREES)))),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('length', POSITIVE_REF),
        ('width', POSITIVE_REF),
        clock='composition',
        constraints=(
            '0<=start<end. Nonempty finite swing rows use cubic-out rotation; zero points right, clockwise positive.',
            'The shoulder stays fixed; the single drawn limb does not solve elbows, contacts or a full-body pose.',
            'Swing times are not clipped or restricted to the visibility span; visibility can hide part of the motion.',
        ),
    ),
    'toon-ward': draw(
        constraints=('Wall fills the canvas; curtain, rail and drip stand use fixed reference geometry.',)
    ),
    'toon-ward-bed': draw(
        ('marks_in', P(unit='reference pixels', description='Inward shift of both signature marks from the right.')),
        constraints=(
            'Draw the bed in front of the cast. Its blanket extends below the canvas; sheet top is reference y=742.',
            'marks_in moves only the signature marks; it is not an entrance time.',
        ),
    ),
    'toon-bandage': group(
        ('start', PARENT_START),
        ('end', PARENT_END),
        (
            'look',
            P(
                type=BandageLook,
                role='face-geometry',
                description='Runtime object with eyes=((left_x,left_y),(right_x,right_y)) in reference pixels.',
            ),
        ),
        constraints=(
            '0<=start<end. Pass the face drawing group as parent to inherit its motion.',
            'Only look.eyes is read: the left eye y sets brow height. No automatic lookup or actor binding occurs.',
        ),
    ),
    'toon-surgery': draw(
        ('view', P(enum=('chair', 'cupboards'))),
        constraints=('Wall follows canvas dimensions; other geometry is fixed. No animation keys.',),
    ),
    'toon-dental-lamp': draw(
        ('pivot', point('Rotation pivot above the hanging arm.')),
        ('angle', DEGREES),
        ('swing', P(unit='degrees', minimum=0, maximum=30)),
        ('end', P(unit='seconds', timebase='composition', role='animation-limit', minimum=0)),
        ('hand', P(description='Optional arm/paw paint color; drawn artwork, not a rig or callback.')),
        ('id', ID),
        clock='composition',
        constraints=(
            'end=0 or swing=0 keeps angle fixed. Otherwise rotation starts at angle-swing and uses sine-in-out.',
            'The cycle repeats every 1.6 seconds; end bounds generated keys without hiding the lamp.',
            'Final emitted rotation stays held. The hand is part of the rotating lamp drawing.',
        ),
    ),
    'toon-dental-tray': draw(
        ('x', REF), ('y', REF), constraints=('x is the tray left edge; y is the supporting surface height.',)
    ),
    'toon-tooth-photo': draw(
        ('at', point('Print center.')),
        ('start', COMP_TIME),
        ('end', STILL_END),
        ('id', ID),
        clock='composition',
        constraints=(*SLIDE_RULES, 'Print slides from reference x=760 and retains a six-degree tilt.'),
    ),
    'toon-probe': draw(
        ('tip', point('Hooked tip target.')),
        ('start', COMP_TIME),
        ('end', STILL_END),
        ('id', ID),
        clock='composition',
        constraints=(
            *SLIDE_RULES,
            'Probe slides from 150 reference pixels to the right and retains a -14-degree tilt.',
        ),
    ),
    'toon-bib-insert': draw(
        ('start', COMP_TIME),
        ('end', PARENT_END),
        ('skin', P(description='Wearer skin paint color.')),
        ('id', ID),
        clock='composition',
        constraints=(
            '0<=start<end with end-start>0.32 seconds. start also sets parent visibility.',
            'Bib fills the canvas; the drop falls linearly for 0.32 seconds and is replaced by a static mark.',
            'Drop and mark meet at the frame center. Reference distances size the details, not the whole insert.',
        ),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]
