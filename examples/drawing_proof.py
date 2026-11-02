"""Render a six-second hybrid drawing candidate, without changing part approvals.

Run from the repository: python -m examples.drawing_proof OUTPUT --engine ENGINE.
The output is a review candidate, not an adopted style. See its report for gates
that still need evidence. The car is original geometry, unrelated to Car Vibe's
reference study. All source clocks continue across the camera cut at four seconds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
from dataclasses import asdict, dataclass
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import numpy as np
from examples.acting_continuity import carry_motion, cup_mesh
from sr_core.scene import Scene

from srstudio import Canvas, clay, plates, proxy
from srstudio.acting import ActingBeat, ActingScore, HeadTarget, PerformancePlan, bento_blends, compile_performance
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import Camera, CameraSample, CameraTrack, Frame, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import AttachedProp, Participant, PropDrawing, bake_interaction
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT

DURATION = 6
SIZE = (1080, 1920)
HAND_ORIGIN = Vec3(40, -325, 0)
HAND_SCALE = 45.0  # centimeters per authored arm unit
TONES = {
    'body': ('#486f6d', '#629b90', '#91c9af', '#c3ead0'),
    'glass': ('#263b61', '#416089', '#6b99b8', '#a7ccdf'),
    'tire': ('#181c29', '#293040', '#414a59', '#626c79'),
    'lamp': ('#c18b43', '#e1b85c', '#f8dc89', '#fff2cb'),
    'trim': ('#644356', '#8b6174', '#ba8a97', '#e6b6ba'),
}


@dataclass(frozen=True)
class Sample:
    time: float
    view: proxy.View
    yaw: float
    lights: tuple[plates.Light, ...]


def sample(time: float, *, size: tuple[int, int] = SIZE) -> Sample:
    if type(time) not in (int, float) or not 0 <= time <= DURATION:
        raise ValueError('proof time must lie in 0..6 seconds')
    u = max(0.0, min(1.0, time - 0.5))
    eased = u * u * u * (10 + u * (-15 + 6 * u))
    position = (370 - 100 * eased, -270, -780)
    if time >= 4:
        position = (-290, -250, -810)
    lights = (
        plates.Light('key', 'directional', '#ffffff', 1.15 if time < 4 else 0.9, yaw=-35, pitch=-52),
        plates.Light('fill', 'ambient', '#ffffff', 0.32 if time < 4 else 0.43),
        plates.Light('rim', 'directional', '#ffffff', 0.45 if time < 4 else 0.8, yaw=145, pitch=-28),
    )
    return Sample(time, proxy.View(position, (0, -95, 0), 31, size=size), -15 + 30 * eased, lights)


def schedule(*, fps: int = 12, size: tuple[int, int] = SIZE, events: tuple[float, ...] = ()) -> tuple[Sample, ...]:
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError('proof fps must be an integer in 1..120')
    if type(size) is not tuple or len(size) != 2 or any(type(n) is not int or n < 2 or n > 1920 or n % 2 for n in size):
        raise ValueError('proof dimensions must be even integers in 2..1920')
    if (
        type(events) is not tuple
        or len(events) > 32
        or any(type(time) not in (int, float) or not 0 <= time < DURATION for time in events)
    ):
        raise ValueError('proof events must be a tuple of at most 32 finite times in [0, 6)')
    return tuple(sample(time, size=size) for time in sorted({i / fps for i in range(DURATION * fps)} | set(events)))


def hand_world(point: Vec3) -> tuple[float, float, float]:
    """Canonical arm coordinates into the model's centimeter, +Z-away basis."""
    value = HAND_ORIGIN + point * HAND_SCALE
    return value.x, value.y, -value.z


def hand_camera(frame: Sample) -> Camera:
    """Explicit registration for this candidate's centered proxy camera.

    This fixture still uses the legacy proxy View; migrating its car to the
    compiler's candidate-review path is separate from this explicit adapter.
    It does not label the candidate as an approved part to obtain a plan.
    """
    view = frame.view
    position = Vec3(view.position[0], view.position[1], -view.position[2])
    target = Vec3(view.target[0], view.target[1], -view.target[2])
    forward = (target - position).unit()
    right = forward.cross(Vec3(0, 1, 0)).unit()
    down = right.cross(forward)
    return Camera(
        projection='perspective',
        distance=(target - position).length / HAND_SCALE,
        focal=1,
        scale=view.size[0] / (2 * math.tan(math.radians(view.fov) / 2)),
        origin=(view.size[0] / 2, view.size[1] / 2),
        view=Frame((target - HAND_ORIGIN) / HAND_SCALE, Quaternion.axes(right, down, -forward)),
    )


def car(yaw: float) -> tuple[clay.Mesh, ...]:
    model = clay.Model()
    with model.at(yaw=yaw):
        model.box('body', (0, -48, 0), (250, 57, 112), radius=16)
        model.box('glass', (-17, -95, 0), (133, 63, 96), radius=14)
        model.box('body', (-17, -126, 0), (139, 9, 105), radius=4)
        for z in (-50, 50):
            model.box('body', (-24, -97, z), (10, 63, 5), radius=2)
            model.box('trim', (-47, -56, z * 1.14), (24, 5, 3), radius=1)
        for x in (-80, 80):
            for z in (-57, 57):
                model.ell('tire', (x, -25, z), (28, 28, 14))
                model.ell('trim', (x, -25, z * 1.18), (15, 15, 3))
        for z in (-36, 36):
            model.box('lamp', (126, -53, z), (4, 18, 24), radius=3)
        model.box('trim', (126, -30, 0), (7, 11, 94), radius=4)
    return model.meshes()


def _path(points) -> str:
    return 'M ' + ' L '.join(f'{x:.6f} {y:.6f}' for x, y in points) + ' Z'


def _environment(cv: Canvas, parent, frames: tuple[Sample, ...], fps: int) -> None:
    # A fixed, authored floor texture in world coordinates. Camera motion
    # reprojects its marks; no random draw or time-dependent noise is involved.
    for i, frame in enumerate(frames):
        group = cv.group(parent, f'ground-{i}')
        cv.gate(group, [(frame.time, (i + 1) / fps)])
        floor = frame.view.project(((-600, 0, -260), (600, 0, -260), (600, 0, 600), (-600, 0, 600)))
        cv.path(group, _path(floor), fill='#d9c8b7', stroke=cv.clear, sw=0)
        for row in range(6):
            for column in range(11):
                x, z = -450 + column * 90 + (row % 2) * 30, -170 + row * 115
                points = frame.view.project(((x, -0.1, z), (x + 16, -0.1, z + 4), (x + 21, -0.1, z + 12)))
                cv.path(group, _path(points), fill='#c4b19e', stroke=cv.clear, sw=0)
        # An authored planar contact-shadow mask, not a simulated cast shadow.
        shadow = frame.view.project(
            tuple((145 * math.cos(a), -0.2, 66 * math.sin(a)) for a in np.linspace(0, math.tau, 48, endpoint=False))
        )
        cv.path(group, _path(shadow), fill='#7b6976', stroke=cv.clear, sw=0, opacity=0.3)


def figure_performance() -> PerformancePlan:
    """Authored face/head transitions retain their source clock through the camera cut."""
    return compile_performance(
        bento_blends(),
        ActingScore(
            DURATION,
            (
                ActingBeat(0, emotion='neutral', breath=0, transition=0),
                ActingBeat(
                    2, emotion='concerned', head=HeadTarget(nod=2, lean=0.3), breath=0.3, transition=0.7, blend=True
                ),
                ActingBeat(
                    3.6, emotion='deadpan', head=HeadTarget(nod=0, lean=-0.3), breath=0, transition=1, blend=True
                ),
            ),
            seed=17,
            idle=False,
            sample_rate=24,
        ),
    )


def figure_location(time: float) -> tuple[float, float, float]:
    """Authored world roots on either side of the declared depth replacement."""
    if time < 3:
        return -40 - 190 * math.sin(math.pi * time / 6), 0, 115
    return -110 + 150 * (time - 3) / 3, 0, -115


def _figure(cv: Canvas, parent, frames: tuple[Sample, ...], fps: int, *, front: bool) -> None:
    performance = figure_performance()
    group = cv.group(parent, 'figure-front' if front else 'figure-back')
    cv.gate(group, [(3, 6)] if front else [(0, 3)])
    # This rig is an explicitly frontal billboard. Its location is projected,
    # but changing the camera does not synthesize a profile drawing.
    moving = cv.group(group, group.id + '-position')
    xs, ys = [], []
    for frame in frames:
        # Move round the car's left end before changing the declared depth pass.
        t = frame.time
        point = frame.view.project((figure_location(t),))[0]
        xs.append((t, float(point[0])))
        ys.append((t, float(point[1])))
    cv.keys(moving, 'x', xs, hold=True, local=True)
    cv.keys(moving, 'y', ys, hold=True, local=True)
    performance.window(0, DURATION).place(
        cv,
        moving,
        placement=Placement(scale=0.42 * cv.width / SIZE[0], anchor=(fx(PIVOT[0]), fy(PIVOT[1]) + 300)),
        id=group.id + '-performance',
    )


def build(
    output: Path,
    *,
    engine: Path,
    fps: int = 12,
    size: tuple[int, int] = SIZE,
    cache: Path | None = None,
    warm_only: bool = False,
) -> Path:
    example_digest = sha256(Path(__file__))
    frames = schedule(fps=fps, size=size)
    if not engine.is_file():
        raise FileNotFoundError(engine)
    if output.exists():
        raise FileExistsError(output)
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise FileNotFoundError('DejaVu Sans Bold is required')
    previous = os.umask(0o077)
    try:
        output.mkdir(parents=True, mode=0o700)
        assets = output / 'assets'
        assets.mkdir(mode=0o700)
        copy_dejavu(font, assets, 'font.ttf')
        facts = inspect_ttf(font.read_bytes())
        scene = Scene(version='auto')
        scene.add_project(
            width=size[0],
            height=size[1],
            fps='24',
            duration=DURATION,
            seed=17,
            background='#efe8df',
            fontPolicy='pinned',
        )
        scene.add_metadata(
            title='A shared view', language='en', generator='srstudio; OpenAI Codex (GPT-6)'
        ).add_accessibility(
            description='A mint car turns while Bento passes behind and in front; a hand carries a cup above it.',
            contrastCheck='error',
            flashCheck='error',
            legibilityCheck='error',
        )
        scene.add_output(
            id='main',
            path='renders/drawing-proof.mp4',
            codec='h264',
            width=size[0],
            height=size[1],
            fps='24',
            preset='fast',
            crf='18',
            faststart=True,
        )
        cv = Canvas(scene, width=size[0], height=size[1], font_asset='font', local_time=True)
        cv.assets.add_font(
            id='font',
            src='assets/font.ttf',
            family=facts.family,
            weight=str(facts.weight),
            sha256=sha256(assets / 'font.ttf'),
            license='assets/FONT-LICENSE.txt',
        )
        world = cv.group(cv.comp, 'world')
        _environment(cv, world, frames, fps)
        _figure(cv, world, frames, fps, front=False)
        rendered: dict[tuple[proxy.View, float, tuple[plates.Light, ...]], str] = {}
        work_limit = 2 * (fps + 2)
        for i, frame in enumerate(frames):
            key = (frame.view, frame.yaw, frame.lights)
            if key not in rendered:
                asset = f'car-{len(rendered)}'
                cv.assets.add_image(id=asset, src=f'assets/{asset}.png', width=size[0], height=size[1])
                rendered[key] = asset
            group = cv.group(world, f'car-frame-{i}')
            cv.gate(group, [(frame.time, (i + 1) / fps)])
            group.add_layer(id=f'car-image-{i}', asset=rendered[key])
        _figure(cv, world, frames, fps, front=True)
        cameras = CameraTrack(DURATION, tuple(CameraSample(frame.time, hand_camera(frame)) for frame in frames))
        motion = carry_motion()
        interaction = bake_interaction(
            cv,
            world,
            (Participant('hand', motion, 'toon'),),
            (PropDrawing(cup_mesh(), AttachedProp(motion, 'cup')),),
            id='carry',
            camera=cameras,
            options=BakeOptions(fps=fps, duration=DURATION),
        )
        information = cv.group(cv.comp, 'information', scaleX=size[0] / SIZE[0], scaleY=size[1] / SIZE[1])
        cv.text(information, 'title', 'A SHARED VIEW', 80, 100, 920, 100, 62, color='#26303a')
        cv.text(
            information, 'subtitle', 'One car. One hand. One continuing moment.', 80, 220, 920, 100, 30, color='#4a5666'
        )
        cv.rect(information, 80, 1680, 920, 130, '#26303a', radius=32)
        cv.text(information, 'caption', 'Keep hold. The camera can move.', 110, 1712, 860, 80, 36, color='#ffffff')
        errors = scene.check(schema=True)
        if errors:
            raise ValueError(errors)
        # Validate the complete vector/contact scene before any raw plate work.
        with plates.render_session(max_invocations=0 if warm_only else work_limit, timeout=120) as work:
            for i, ((view, yaw, lights), asset) in enumerate(rendered.items()):
                recipe = proxy.Recipe(
                    TONES, behind=frozenset(TONES), lights=lights, oversample=1, soft_edge=0, grain_seed=17
                )
                image = proxy.layers(car(yaw), view, recipe, engine=engine, cache=cache or output.parent / 'cache').back
                plates.write_png(assets / f'{asset}.png', image)
                print(f'Prepared car view {i + 1}; renderer invocations {work.invocations}', flush=True)
        path = output / 'scene.xml'
        path.write_bytes(scene.to_bytes())
        report = {
            'schema': 'srstudio.drawing-candidate/1.1.0',
            'generated_by': {'tool': 'OpenAI Codex', 'model': 'GPT-6'},
            'status': 'candidate; no adoption approval',
            'source': {
                'example_sha256': example_digest,
                'srstudio': version('srstudio'),
                'sr_core': version('sr-core'),
                'engine_sha256': sha256(engine),
                'scene_version_policy': scene.version,
                'schema_sha256': hashlib.sha256(
                    files('sr_core').joinpath('scene/schema/scene-render.xsd').read_bytes()
                ).hexdigest(),
                'font_sha256': sha256(assets / 'font.ttf'),
                'continuity_example_sha256': sha256(Path(__file__).with_name('acting_continuity.py')),
                'candidate_figure_rig': figure_performance().rig.describe(),
                'candidate_car_recipe': 'drawing-proof-car/1.0.0; unapproved',
                'machine': platform.machine(),
                'platform': platform.platform(),
            },
            'schedule': {
                'duration': DURATION,
                'output_fps': 24,
                'sample_fps': fps,
                'size': size,
                'held_camera': [[0, 0.5], [1.5, 4], [4, 6]],
                'camera_cut': 4,
                'car_turn': [0.5, 1.5],
                'expression_blends': [[2, 2.7], [3.6, 4.6]],
                'face_fps': 24,
                'figure_depth_replacement': 3,
                'sampling': 'held; 12 fps is animation on twos',
            },
            'render': {
                'unique_views': len(rendered),
                'work_limit': work_limit,
                'actual': asdict(work),
                'samples': plates.SAMPLES,
                'bounces': plates.BOUNCES,
                'oversample': 1,
                'per_process_memory_limit': 8 * 1024**3,
                'per_invocation_timeout': 120,
                'host_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'child_peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                'memory_qualification': 'Linux process high-water marks; not combined RSS or GPU memory',
            },
            'interaction': interaction.reports[0][1].to_dict(),
            'images': {p.name: sha256(p) for p in sorted(assets.glob('*.png'))},
            'validation': {'schema': True, 'findings': errors},
            'remaining_gates': [
                'Full-size and temporal rendered review, strict encode, measured pixel gates and peak memory',
                'Rendered expression/pose continuity measurements and whole-body locomotion; '
                'the depth-pass change remains a cut',
                'Approved information-layer equivalence and compatibility fingerprints',
                'Shared drawn shading and validated caster/receiver shadows; current shadow is an authored ground mask',
                'Shared scene-compiler candidate-asset contract; this study uses explicit legacy proxy views',
                'Operator review of the complete proof before style adoption',
            ],
        }
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        return path
    finally:
        os.umask(previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--engine', required=True, type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--warm-only', action='store_true')
    args = parser.parse_args()
    print(build(args.output, engine=args.engine, fps=args.fps, cache=args.cache, warm_only=args.warm_only))
