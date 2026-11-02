"""Blob furniture and room discovery, including the existing projected layout helpers."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from ._drawing_contracts import _slot
from ._soft_scene_contracts import ANGLE, GROUP, SPANS, draw
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P

PIXEL = P(unit='drawing pixels', space='fixed-layout')
POINT = P(unit='drawing pixels', space='fixed-layout', prefix_items=(PIXEL, PIXEL))
REGION = P(unit='drawing pixels', space='fixed-layout', role='drawing-region', items=POINT)
ROOM = P(unit='room units', space='soft-room')
FIXED_GROUP = replace(GROUP, unit='drawing pixels', space='fixed-layout', anchors=(('origin', (0, 0)),))
LAYOUT = (
    'Fixed artwork for the Soft 1080x1920 layout, already positioned in the returned group. '
    'Transform its parent to reposition the whole drawing; canvas resizing does not reflow it. '
    'The perspective is drawn in 2D, not a world mesh or a camera projection at render time.'
)
SHOTS = (
    'shots are visibility spans, not framing records. None leaves the group visible; an empty sequence '
    'hides it. Nonnegative finite start<end spans form a union, including overlapping and touching spans. '
    'Opacity gates follow Canvas.local_time. Use a distinct id for repeated rooms to namespace their furniture.'
)
SOFA_SLOT = replace(
    _slot(
        'Receives the sofa root after its seat, before the near arm. Draw in the fixed projected layout; '
        'this does not position, scale or constrain the actor for you.'
    ),
    space='fixed-layout',
)
SCREEN_SLOT = replace(
    _slot(
        'Receives a separate translated, skewed group masked to the flat picture rectangle. '
        'Draw from (0,0) using meeting_screen width/height; do not project it onto the wall again. '
        'The callback overlays the default slide and is drawn before the webcam.'
    ),
    space='screen-local',
)
REFERENCE = (
    'Returns reference coordinates without drawing or mutating a scene. They describe the authored fixed '
    'layout before caller transforms, not world anchors, collision geometry or solved contacts.'
)


def reference(*parameters: tuple[str, P], returns: P = REGION, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=parameters,
        returns=returns,
        capabilities=(('spatial_attachment', False),),
        constraints=(REFERENCE, *constraints),
    )


_HELPERS = {
    'keyboard': reference(
        constraints=(
            'Four keyboard-deck corners after the built-in LAPTOP translation and '
            '0.75 scale. These are fixed-layout coordinates, not laptop-local points.',
        )
    ),
    'sofa_seat': reference(constraints=('Four cushion-top corners in the sofa projection around SOFA_SEAT.',)),
    'swivel_seat': reference(constraints=('Four seat corners in fixed-layout pixels, matching the office chair.',)),
    'meeting_table_top': reference(constraints=('Four table-top corners projected through room_point.',)),
    'meeting_screen': reference(
        returns=P(
            unit='drawing pixels',
            space='fixed-layout',
            role='screen-frame',
            prefix_items=(replace(POINT, role='top-left'), PIXEL, PIXEL, ANGLE),
        ),
        constraints=(
            'Returns ((x,y),width,height,skewY). x/y is the picture top-left in the fixed layout; '
            'width/height bound the flat masked callback frame; skewY is degrees along the back wall.',
        ),
    ),
    'room_point': reference(
        ('a', ROOM),
        ('c', ROOM),
        ('up', ROOM),
        returns=POINT,
        constraints=(
            'a runs right along the back wall, c toward the viewer and up above the floor. '
            'The projection origin ROOM is (330,1180) in fixed-layout pixels.',
        ),
    ),
    'wall_quad': reference(
        ('wall', P(enum=('back', 'side'))),
        ('a0', ROOM),
        ('a1', ROOM),
        ('u0', ROOM),
        ('u1', ROOM),
        constraints=(
            'a0/a1 run along the chosen wall: a on the back wall, c on the side wall at CORNER. '
            'u0/u1 are heights above the floor. Unknown wall names raise BlobError.',
        ),
    ),
    'floor_quad': reference(
        ('a0', ROOM),
        ('a1', ROOM),
        ('c0', ROOM),
        ('c1', ROOM),
        ('up', ROOM),
        constraints=('Four corners parallel to the room floor, lifted by up before projection.',),
    ),
}


def contract(name: str, **helpers: Callable[..., Any]) -> PartContract:
    return replace(
        _CONTRACTS[name],
        operations=tuple(Operation(helper, builder, _HELPERS[helper]) for helper, builder in helpers.items()),
    )


def fixed(*parameters: tuple[str, P], constraints: tuple[str, ...] = (), returns: P = FIXED_GROUP) -> PartContract:
    return draw(*parameters, returns=returns, constraints=(LAYOUT, *constraints))


_CONTRACTS = {
    'soft-desk': fixed(
        constraints=(
            'Static desk, drawn at the office position with top and square legs. '
            'It does not place or attach a laptop or hands.',
        )
    ),
    'soft-chair': fixed(
        constraints=(
            'Static chair facing left. SEAT=(790,1340) locates the seated hip; '
            'SEATED_FLOOR=1476 locates soles in this layout. No seating solver.',
        )
    ),
    'soft-laptop': fixed(
        returns=replace(FIXED_GROUP, space='laptop-local'),
        constraints=(
            'The root has built-in translation (277.5,416) and scale 0.75; its geometry uses '
            'laptop-local pixels. keyboard() already applies this transform. The lid is static; '
            'the viewer sees its back. No screen slot or grip solver is provided.',
        ),
    ),
    'soft-office': fixed(
        ('shots', SPANS),
        constraints=(
            SHOTS,
            'Draw order is chair, desk, signature cactus, laptop and signature code. '
            'No cast callback; draw actors in the chosen parent at the authored layout positions.',
        ),
    ),
    'soft-sofa': fixed(
        ('on_sofa', SOFA_SLOT),
        constraints=(
            'The sofa projection is centered at SOFA_SEAT=(600,1340). sofa_seat() exposes its '
            'cushion polygon. The callback receives fixed-layout coordinates before the near arm, '
            'not a translated hip frame. Static artwork; the arm supplies drawn occlusion.',
        ),
    ),
    'soft-home': fixed(
        ('shots', SPANS),
        ('on_sofa', SOFA_SLOT),
        ('lamp_talk', SPANS),
        constraints=(
            SHOTS,
            'on_sofa is forwarded to the nested sofa, not called on the room root. '
            'lamp_talk spans are ordered, nonoverlapping and satisfy 0<=start<end; empty means no glow. '
            'The lamp glow is a held overlay, not a shared world light. The room includes a rug, '
            'sofa, floor lamp, side table and signature marks.',
        ),
    ),
    'soft-swivel-chair': fixed(
        constraints=(
            'Static upholstered chair and five-spoke base at the office seat position. '
            'swivel_seat() returns its top polygon; the chair does not animate a swivel.',
        )
    ),
    'soft-meeting-room': fixed(
        ('shots', SPANS),
        ('on_screen', SCREEN_SLOT),
        constraints=(
            SHOTS,
            'chair is strictly boolean; False omits the swivel chair. '
            'The on_screen slot has its own masked and skewed frame; meeting_screen() gives its '
            'geometry. Window patches, wall clock, furniture and laptop are static drawings. '
            'The light patches do not respond to moving objects or a world light.',
        ),
    ),
    'soft-coffee-machine': fixed(
        constraints=(
            'Already positioned on the break-room counter using the room projection. '
            'Includes a mug, static steam paths and a drawn lit button; no brewing or steam animation.',
        )
    ),
    'soft-fridge': fixed(
        constraints=(
            'Static pastel fridge against the break-room wall with drawn doors, handles and notes. '
            'No door or power-state animation; this differs from soft-home-fridge.',
        )
    ),
    'soft-stool': fixed(
        constraints=(
            'Static stool cushion centered at (800,1335), with radii (118,46) and floor at y=1490. '
            'Place a seated pose yourself; the drawing does not constrain the actor.',
        )
    ),
    'soft-break-room': fixed(
        ('shots', SPANS),
        constraints=(
            SHOTS,
            'Includes the counter, coffee machine, fridge, stool and signature marks. '
            'Window light and pendant glaze are authored overlays; the pendant glaze lies over '
            'the furniture. These do not respond to shared world lighting or cast dynamic shadows.',
        ),
    ),
}
