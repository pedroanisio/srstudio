"""Executable small studies, with production limitations kept next to the inputs."""

from dataclasses import asdict, replace

from . import registry
from .limbs import HUMAN, ArmProfile
from .limbs.interaction import Face, PropMesh
from .limbs.math3d import Frame, Vec3
from .limbs.motion import Action, Attachment, Motion, TransformKey, TransformTrack
from .limbs.serialization import motion_dict


def catalog():
    items = []
    examples = [
        ('manager', {'mouth': [[0, 'rest'], [0.5, 'open'], [1, 'rest']]}, {'x': 540, 'y': 700}),
        (
            'pip',
            {'cues': [{'time': 0, 'pose': 'stand'}, {'time': 1, 'pose': 'wave-a', 'ease': 0.3}]},
            {'x': 540, 'y': 1400, 'scale': 1.5},
        ),
        ('stick-rig', {'keys': [{'start': 0, 'pose': 'type-a'}, {'start': 1, 'pose': 'lean'}]}, {}),
        ('doodle', {'text': 'Hello', 'gesture': True}, {'x': 540, 'y': 700}),
        ('saga-droid', {'talk': [[0, 'closed'], [0.5, 'open'], [1, 'closed']]}, {'x': 540, 'y': 1200}),
        ('gloss-nadia', {'face': [[0, 'open'], [1, 'wide']]}, {'x': 540, 'y': 1400}),
        (
            'toon-sloth',
            {
                'poses': [
                    {'start': 0, 'eyes': 'sleepy', 'mouth': 'flat', 'arms': 'desk'},
                    {'start': 1, 'eyes': 'wide', 'mouth': 'yawn', 'arms': 'sigh'},
                ]
            },
            {},
        ),
    ]
    base = {'schema': 'srstudio.authoring/1.0.0', 'interval': {'start_s': 0, 'end_s': 2}}
    for name, arguments, placement in examples:
        items.append(
            {
                'id': name,
                'request': {
                    **base,
                    'task': 'character',
                    'character': name,
                    'arguments': arguments,
                    'placement': placement,
                },
                'style': registry.describe('character', name)['style'],
                'scope': (
                    'character bust; local speech cues'
                    if name == 'manager'
                    else 'character upper body; local pose cues'
                    if name == 'toon-sloth'
                    else 'whole character; local pose or speech cues'
                ),
            }
        )
    motion = Motion(ArmProfile(), HUMAN, (Action('present', duration=2),))
    items.append(
        {
            'id': 'gesture',
            'request': {
                **base,
                'task': 'gesture',
                'motion': motion_dict(motion),
                'placement': {'x': 340, 'y': 600, 'scale': 2},
            },
            'style': 'toon',
            'scope': 'isolated arm; acceleration-safe gesture envelope',
        }
    )
    # Reach first, then translate the rooted arm while the fingers maintain their grip.
    # Zero-velocity root keys stop the prop at acquisition and release.
    grip = Motion(
        ArmProfile(),
        HUMAN,
        (Action('grasp', duration=2),),
        root=TransformTrack(
            (TransformKey(0, Frame()), TransformKey(0.8, Frame()), TransformKey(1.3, Frame(Vec3(0.6, -0.25, 0))))
        ),
    )
    offset = Frame(Vec3(0, 0.3, 0))
    grip = replace(
        grip, attachments=(Attachment('box', 0.8, 1.3, grip.sample(0.8).hand.frame.compose(offset), offset),)
    )
    mesh = PropMesh(
        'box',
        (Face('front', (Vec3(-0.25, 0, 0), Vec3(0.25, 0, 0), Vec3(0.25, 0.55, 0), Vec3(-0.25, 0.55, 0)), '#6C9ABC'),),
    )
    items.append(
        {
            'id': 'carry',
            'request': {
                **base,
                'task': 'carry',
                'motion': motion_dict(grip),
                'mesh': asdict(mesh),
                'attachment': 'box',
                'placement': {'x': 340, 'y': 600, 'scale': 2},
            },
            'style': 'toon',
            'scope': 'isolated rooted arm moves an attached flat prop; release holds its last world frame',
        }
    )
    # Fresh JSON-shaped values, including tuple fields from dataclass serialization.
    import json

    items = json.loads(json.dumps(items, allow_nan=False))
    for item in items:
        item['evidence'] = {
            'test': 'tests/test_agent_authoring_requests.py',
            'preview_command': ['python', 'examples/agent_authoring.py', 'OUTPUT', '--recipe', item['id']],
            'render_command': [
                'scene-render',
                'render',
                'OUTPUT/' + item['id'] + '.xml',
                '--frames',
                '0..48',
                '--output',
                'OUTPUT/' + item['id'] + '-%04d.png',
                '--strict',
            ],
            'frame_count': 48,
            'fps': 24,
            'rendered_review': 'not-run',
            'limitations': [
                'Recipe discovery does not run rendering or certify perceptual quality.',
                'No dynamic balance, heel-strike, toe-off, physical release or automatic full-body retargeting.',
                'Named poses can be held or switch discretely; inspect source and rendered sampling separately.',
            ],
        }
    return {'schema': 'srstudio.authoring-recipes/1.0.0', 'items': items, 'total': len(items)}
