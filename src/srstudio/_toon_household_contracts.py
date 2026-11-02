"""Authored flat and household prop semantics; no builder execution or name-based inference."""

from dataclasses import replace
from typing import Literal

from sr_core.scene import Group

from ._toon_contracts import COMP_TIME, DURATION, END, FONT, PARENT_END, PARENT_START, REF, START, draw, point
from .contracts import ParameterContract as P
from .contracts import PartContract

OPENING = P(unit='seconds', timebase='canvas', minimum=0, description='Opening cue, not a coordinate point.')
LIMIT = P(unit='seconds', role='validation-limit', description='Timing validation limit; does not set visibility end.')
TOP = P(unit='reference pixels', space='toon-reference', minimum=200, maximum=900)
COMP_START = P(unit='seconds', timebase='composition', role='start')
DEGREES = P(unit='degrees')


def group(
    *parameters: tuple[str, P], constraints: tuple[str, ...] = (), clock: Literal['canvas', 'composition'] = 'canvas'
) -> PartContract:
    return replace(
        draw(*parameters, constraints=constraints, clock=clock),
        returns=P(
            type=Group,
            unit='frame pixels',
            space='parent',
            description='Root Group. Reference coordinates are already converted to frame pixels; no grip frame.',
        ),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', True)),
    )


_CONTRACTS = {
    'toon-flat': draw(constraints=('Wall fills the canvas; skirting uses fixed reference geometry.',)),
    'toon-closet': draw(('at', OPENING), constraints=('Door opens over 0.18 seconds; artwork has no visibility end.',)),
    'toon-oven': draw(('at', OPENING), constraints=('Door drops over 0.18 seconds; artwork has no visibility end.',)),
    'toon-shower': draw(('at', OPENING), constraints=('Curtain retracts over 0.25 seconds; no visibility end.',)),
    'toon-front-door': draw(('at', OPENING), constraints=('Door opens over 0.18 seconds; no visibility end.',)),
    'toon-plates': draw(
        ('start', START),
        ('count', P(minimum=1)),
        ('step', DURATION),
        ('end', LIMIT),
        constraints=(
            'Positive count and step; start+(count-1)*step+0.42 must not exceed end.',
            'Each cue is rounded to three decimals and supplies parent visibility for its 0.42-second flight.',
        ),
    ),
    'toon-laundry-pile': draw(
        ('top', TOP),
        ('start', START),
        ('end', LIMIT),
        constraints=(
            'start=None draws the heap already raised; otherwise 0<=start and start+0.55<=end.',
            'start also sets parent visibility; the heap is not hidden at end.',
        ),
    ),
    'toon-tiny-drawer': draw(
        ('at', OPENING),
        ('end', LIMIT),
        ('x', REF),
        ('y', REF),
        constraints=(
            'x,y is the chest bottom middle. at+0.3<=end; the sock becomes visible at at on the parent clock.',
        ),
    ),
    'toon-whirl': draw(
        ('start', START),
        ('end', END),
        ('at', point('Final blur center.')),
        ('travel', P(unit='reference pixels', minimum=0)),
        constraints=('0<=start and start+0.2<=end; travel arrives from the right by 70% of the span.',),
    ),
    'toon-sparkles': draw(
        ('start', START),
        ('end', END),
        ('at', P(items=point('Glint center.'))),
        constraints=(
            '0<=start<end; empty at draws nothing. Each glint peaks 0.22 seconds after its cue.',
            'Glint visibility ends at min(cue+0.5,end); very short spans can clip the peak.',
        ),
    ),
    'toon-pipe': group(
        ('at', point('Bad pipe joint.')),
        ('drips', P(items=COMP_TIME)),
        ('burst', PARENT_START),
        ('end', PARENT_END),
        clock='composition',
        constraints=(
            'Sorted drip cues satisfy 0<=cue<end; duplicates are accepted. Each cue also sets parent visibility.',
            'Drips animate for 0.32 seconds but hide at min(end,cue+0.32). burst=None omits jets.',
            '0<=burst<end when supplied; only drops and jets hide at end, not the pipe body.',
        ),
    ),
    'toon-faucet': group(
        ('x', REF),
        ('counter', REF),
        ('drips', P(items=COMP_TIME)),
        ('burst', PARENT_START),
        ('end', PARENT_END),
        clock='composition',
        constraints=(
            'x is the riser; counter is the counter top. The spout extends left by 62 reference pixels.',
            'Sorted drip cues satisfy 0<=cue<end; duplicates are accepted. Each cue also sets parent visibility.',
            'Drips animate for 0.32 seconds but hide at min(end,cue+0.32). burst=None omits jets.',
            '0<=burst<end when supplied; only drops and jets hide at end, not the faucet body.',
        ),
    ),
    'toon-paper-insert': group(
        ('start', START),
        ('end', END),
        constraints=(
            FONT,
            'Exception to reference geometry: the insert uses frame pixels.',
            'Sheet at (100,500), height 860 and width canvas.width-200.',
            '0<=start<end also sets parent visibility; nonblank title to 40 characters, up to 4 lines of 26 chars.',
            'Scale pushes from 1 to 1.05 across the span; paper is a paint color.',
        ),
    ),
    'toon-mosquito': group(
        ('path', P(items=P(prefix_items=(COMP_TIME, REF, REF)))),
        ('end', PARENT_END),
        clock='composition',
        constraints=(
            'Two or more sorted (second,x,y) keys; 0<=first_time<end. Duplicate times and keys beyond end are allowed.',
            'First key time also starts parent visibility. id is a UID prefix.',
            'Artwork has fixed wings; path keys drive translation.',
        ),
    ),
    'toon-rolled-towel': group(
        ('root', point('Arm base and rotation pivot.')),
        ('swings', P(items=P(prefix_items=(COMP_TIME, DEGREES)))),
        ('start', PARENT_START),
        ('end', PARENT_END),
        clock='composition',
        constraints=('Nonempty swings; 0<=start<end. Rotation keys use composition time independently of visibility.',),
    ),
    'toon-wrestled-sheet': group(
        ('start', COMP_START),
        ('end', PARENT_END),
        ('y', REF),
        ('beat', P(unit='seconds', role='duration', minimum=0.1, maximum=1)),
        clock='composition',
        constraints=(
            '0<=start<end; start also sets parent visibility.',
            'Keys alternate every beat through floor((end-start)/beat).',
        ),
    ),
    'toon-balled-sheets': group(
        ('top', TOP),
        ('start', COMP_START),
        ('end', PARENT_END),
        clock='composition',
        constraints=(
            'start=None draws a static heap. Otherwise 0<=start and start+0.7<=end; start also sets parent visibility.',
            'Unlike the laundry pile, this root is hidden at end.',
        ),
    ),
    'toon-folded-sheet': group(
        ('at', point('Center of the folded sheet bottom edge.')),
        ('start', PARENT_START),
        ('end', PARENT_END),
        constraints=(
            '0<=start<end sets visibility only; no animation keys. coat is the drawn paw color, not an actor binding.',
        ),
    ),
    'toon-padlock': group(
        ('at', point('Reference point shared by the shackle and lock body.')),
        ('start', PARENT_START),
        ('opened', COMP_TIME),
        ('end', PARENT_END),
        clock='composition',
        constraints=(
            '0<=start<=opened<=end; the lock falls 700 reference pixels over 0.6 seconds from opened.',
            'Parent visibility ends at min(end,opened+0.6); opened=end hides the fall.',
        ),
    ),
    'toon-tasting-spoons': group(
        ('cues', P(items=PARENT_START)),
        ('at', point('Pile reference origin; spoon positions are offset by row and column.')),
        ('end', LIMIT),
        constraints=(
            'Sorted cues satisfy 0<=cue<end; duplicates are accepted.',
            'Each cue starts parent visibility without animation keys.',
            'Spoons remain visible after end; the builder does not set a visibility end.',
        ),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]
