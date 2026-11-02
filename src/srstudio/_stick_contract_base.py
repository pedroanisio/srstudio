"""Shared Stick drawing metadata without builder imports, safe during core module registration."""

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

PIXEL = P(type=float, unit='frame pixels')
SCALE = P(unit='ratio', description='Strictly positive drawing scale.')
TIME = P(unit='seconds', timebase='canvas', minimum=0)
END = P(unit='seconds', timebase='canvas', role='animation-limit')
RATE = P(
    unit='drawings per second', description='Strictly positive; alternates two held drawings, not cycles per second.'
)
FONT = 'Lettering requires a bound Canvas font asset; it is not converted to outlined path geometry.'
FIXED = 'Artwork uses the 1080x1920 Stick layout; canvas-sized backgrounds resize, fixed details do not auto-fit.'
BAKED = 'Placement and scale are baked into the geometry; the returned group has no local placement transform.'
CLOCK = 'Animation keys and opacity gates follow Canvas.local_time: composition by default, local when enabled.'
PAINT = P(description='Paint color passed to the drawing primitives.')
POINT = P(prefix_items=(PIXEL, PIXEL), space='parent')


def draw(
    *parameters: tuple[str, P], local: bool = False, handle: bool = True, constraints: tuple[str, ...] = ()
) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=P(
            type=Group,
            unit='frame pixels',
            space='returned-group' if local else 'parent',
            anchors=(('origin', (0, 0)),) if local else (),
        )
        if handle
        else P(type=type(None)),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', handle)),
        constraints=(
            'Draws flat 2D geometry in the supplied parent; no spatial grip, collision or anatomical solver.',
            CLOCK,
            *constraints,
        ),
    )


def placed(*parameters: tuple[str, P], local: bool = False, constraints: tuple[str, ...] = ()) -> PartContract:
    return draw(('x', PIXEL), ('y', PIXEL), *parameters, local=local, constraints=constraints)
