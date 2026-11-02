"""Versioned, bounded, font-free fixtures for the agent authoring-loop benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from sr_core.scene import Scene

from . import clay, plates
from .acting import BENTO, ActingBeat, ActingScore, PerformancePlan, compile_performance
from .canvas import Canvas
from .character_clips import Placement
from .limbs import HUMAN, ArmProfile, Frame, Vec3
from .limbs.compile import BakeOptions, compile_motion
from .limbs.motion import Action, Contact, Motion, TransformKey, TransformTrack
from .limbs.projection import Camera

FRAMES, FPS, WIDTH, HEIGHT = 8, 8, 360, 640
SEED = 121
PROFILE = {
    'revision': 'authoring-loop/1.0.0',
    'frames': FRAMES,
    'fps': FPS,
    'duration_seconds': 1,
    'width': WIDTH,
    'height': HEIGHT,
    'seed': SEED,
    'font_assets': [],
    'acting_rig': {'name': BENTO.name, 'version': BENTO.version},
    'acting_beats': [[0, 'neutral', 0], [0.25, 'happy', 0.15], [0.65, 'thinking', 0.15]],
    'contact': {'action': 'grasp', 'interval': [0.4, 0.7], 'target_translation': [0.1, 0, 0], 'backend': 'baked'},
    'plates': {
        'size': [64, 64],
        'rotations_y': [0, 25],
        'camera': [[0, -10, -100], [0, 0, 0], 20],
        'body_box': [16, 12, 10],
        'cap_box': [10, 3, 8],
        'path_samples_per_pixel': plates.SAMPLES,
        'bounces': plates.BOUNCES,
        'colors': ['#C88762', '#3B8198'],
    },
}

Plan = PerformancePlan | Motion | tuple[plates.Plate, ...]


def plan(kind: str) -> Plan:
    if kind == 'acting':
        return compile_performance(
            BENTO,
            ActingScore(
                1,
                tuple(
                    ActingBeat(at, emotion=emotion, transition=transition)
                    for at, emotion, transition in ((0, 'neutral', 0), (0.25, 'happy', 0.15), (0.65, 'thinking', 0.15))
                ),
                seed=SEED,
                sample_rate=FPS,
            ),
        )
    if kind == 'contact':
        base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=1),))
        grip = base.sample(0.5).hand.frame
        target = TransformTrack(
            (TransformKey(0, grip), TransformKey(1, Frame(grip.origin + Vec3(0.1, 0, 0), grip.rotation)))
        )
        return replace(base, contacts=(Contact('moving-support', 0.4, 0.7, target),))
    if kind == 'plates':
        model = clay.Model()
        model.box('body', (0, 0, 0), (16, 12, 10))
        model.box('cap', (0, -7, 0), (10, 3, 8))
        return tuple(
            plates.Plate(
                64,
                64,
                plates.Camera((0, -10, -100), (0, 0, 0), 20),
                plates.stage_lights(),
                (plates.Placed(model.meshes(), rotation_y=angle),),
                (plates.Material('body', '#C88762'), plates.Material('cap', '#3B8198')),
            )
            for angle in (0, 25)
        )
    raise ValueError(f'unknown benchmark fixture: {kind}')


def states(value: PerformancePlan | Motion) -> list[dict]:
    return [asdict(value.sample(i / FPS)) for i in range(FRAMES + 1)]


@dataclass(frozen=True)
class CompiledFixture:
    xml: bytes
    audited_samples: int


def compile_drawing(value: PerformancePlan | Motion) -> CompiledFixture:
    scene = Scene(version='auto')
    scene.add_project(width=WIDTH, height=HEIGHT, fps=str(FPS), duration=1, background='#00000000')
    cv = Canvas(scene, font_asset=None)
    samples = 0
    if isinstance(value, PerformancePlan):
        value.window(0, 1).place(cv, cv.comp, placement=Placement(scale=1 / 3), id='performance')
    else:
        result = compile_motion(
            cv,
            cv.comp,
            value,
            id='contact',
            backend='baked',
            camera=Camera(origin=(180, 180), scale=100),
            options=BakeOptions(fps=FPS, duration=1, max_frames=FRAMES, max_nodes=10000),
        )
        samples = result.report.samples
    errors = scene.check(schema=True)
    if errors:
        raise ValueError(f'benchmark fixture failed validation: {errors}')
    return CompiledFixture(scene.to_bytes(), samples)
