"""Rafa's static mesh builders: model mutation, authored units and material preparation."""

from collections.abc import Callable

from .clay import Mesh, Model
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P

MODEL = P(type=Model, unit='Rafa model units', space='model-frame', role='mutable-model')
MESH = P(type=Mesh, unit='Rafa model units', space='model-frame', role='material-mesh')
ROOM = (
    'Build the room in an identity Model frame, then place the completed meshes with the plate object transform. '
    'Internal plant helpers enter absolute Model.at frames; an outer Model.at does not transform every room component. '
    'The actor, recurring props, counter and near-worktop dressing are separate builders, not callback slots.'
)
DETAILS = {
    'rafa-mug': (
        'Mug geometry is built near the origin, with its body centered at (0,-23,0), radius 22 and height 42. '
        'Its recessed coffee, rim and arched handle are held geometry. mug-label is a curved UV surface. '
        'No grip frame, liquid simulation or drinking animation is supplied.'
    ),
    'rafa-phone': (
        'Phone body is centered at (0,-48,0), dimensions (48,96,8); its screen faces negative z. '
        'phone-screen is a printed UV faceplate with fixed 09:41 and 99+ copy, not a clock or message service.'
    ),
    'rafa-bills': (
        'Folder body is centered at (0,-38,0), dimensions (96,73,17), with separate papers, tabs and a cord. '
        'bill-label supplies fixed ADULT LIFE / PENDING copy. Pages do not turn.'
    ),
    'rafa-lunchbox': (
        'Lunchbox body is centered at (0,-20,0), dimensions (86,35,57); lid, clips and handle extend beyond it. '
        'lunch-label supplies fixed RAFA / NOT COMMUNAL copy. The lid does not open.'
    ),
    'rafa-tote': (
        'Tote body is centered at (0,-44,0), dimensions (90,86,40); handles, bread, greens and receipt are included. '
        'tote-label and receipt are distinct printed UV surfaces. The bag does not deform or react to a hand.'
    ),
    'rafa-kitchen': (
        'Kitchen includes floor, walls, cabinets, window, sink, stove, shelves, plants and home-print. '
        'Window buildings and appliance details are static geometry; no lighting or camera is installed.'
    ),
    'rafa-breakroom': (
        'Break room includes tiled floor, walls, closed fridge, cabinets, coffee machine, sink, clock, lamp and '
        'office-poster. Clock hands are static geometry. The lamp uses an emissive material; '
        'the builder does not install scene lights or a camera.'
    ),
}


def contract(name: str, finished: Callable[[Mesh], Mesh]) -> PartContract:
    return PartContract(
        parameters=(('m', MODEL),),
        returns=P(type=type(None), role='model-mutation'),
        capabilities=(('returns_scene_handle', False), ('spatial_attachment', False), ('animation', False)),
        operations=(
            Operation(
                'finished',
                finished,
                PartContract(
                    parameters=(('mesh', MESH),),
                    returns=MESH,
                    constraints=(
                        'Returns the input mesh unchanged when UVs already exist, the material is unknown or '
                        'the material has no normal map. Otherwise returns a planar-UV mesh for the authored '
                        'knit or clay surface. Geometry and material identity are preserved; no rendering occurs.',
                    ),
                ),
            ),
        ),
        constraints=(
            'Appends static triangles into the caller-owned clay.Model and returns None. It does not create a '
            'Canvas group, render a plate or schedule animation. Model.meshes() merges geometry by material.',
            'Coordinates are centimetre-like Rafa model units: x right, y down, z away from the lens. '
            'They are not canvas pixels or guaranteed physical centimetres. No contact anchor is declared.',
            'Resolve every mesh material through rafa.MATERIALS or rafa.materials(). Named labels use rafa.PRINTS '
            'and existing UVs; the plate renderer supplies font resources and renders these recipes. '
            'Use finished(mesh) to add surface UVs where required by a normal map.',
            ROOM
            if name in ('rafa-kitchen', 'rafa-breakroom')
            else 'The prop bakes the active Model.at frame into its vertices. Place it with that frame or with a '
            'plate object transform; it has no returned scene node to move.',
            DETAILS[name],
        ),
    )
