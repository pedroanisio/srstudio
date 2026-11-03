"""Sustained listening and a moving hand/cup interaction on one clock across a cut.

Run ``python examples/acting_continuity.py OUTPUT`` then
``scene-render encode OUTPUT/continuity.scene.xml --strict``.
The silent listening fixture has explicitly synthetic alignment and levels. It is not a
recording or measured speech. The carrier is an isolated spatial arm, not a walking body.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, replace
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import BENTO, ActingBeat, ActingScore, SpokenLine, compile_performance
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import AttachedProp, Face, Participant, PropDrawing, PropMesh, bake_interaction
from srstudio.limbs.motion import Action, Attachment, Contact, Motion, TransformKey, TransformTrack
from srstudio.limbs.serialization import save_motion
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT
from srstudio.voice import Alignment


def listening_score() -> ActingScore:
    """Three synthetic short phrases; real recordings should use measured speech_of levels."""
    alignment = Alignment(tuple('Hello.'), (0, 0.1, 0.2, 0.3, 0.4, 0.5), (0.1, 0.2, 0.3, 0.4, 0.5, 0.6))
    return ActingScore(
        6,
        (ActingBeat(0, emotion='neutral', gaze='right', transition=0),),
        heard=tuple(SpokenLine(at, alignment, (-24.0,) * 60) for at in (0.5, 2.2, 4.0)),
        sample_rate=24,
        seed=1,
    )


def carry_motion() -> Motion:
    source = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=6, pole=Vec3(0, 1, 0)),))
    grip = source.sample(2.4).hand.frame
    left = Frame(grip.origin + Vec3(0.04, -0.22, 0.04), grip.rotation)
    right = Frame(grip.origin + Vec3(0.18, -0.18, 0.04), grip.rotation)
    path = TransformTrack(
        (TransformKey(1.2, grip), TransformKey(2.4, left), TransformKey(3.6, right), TransformKey(5, grip)),
        interpolation='continuous',
    )
    source = replace(source, contacts=(Contact('cup-grip', 1.2, 5, path),))
    offset = Frame(Vec3(0, 0.37, 0.19), grip.rotation.inverse())
    return replace(source, attachments=(Attachment('cup', 1.2, 5, grip.compose(offset), offset),))


def cup_mesh() -> PropMesh:
    count, radius, height = 16, 0.19, 0.39
    faces = []
    for i in range(count):
        a, b = math.tau * i / count, math.tau * (i + 1) / count
        shade = round(175 + 45 * math.cos((a + b) / 2))
        faces.append(
            Face(
                f'side-{i}',
                (
                    Vec3(radius * math.cos(a), -height / 2, radius * math.sin(a)),
                    Vec3(radius * math.cos(b), -height / 2, radius * math.sin(b)),
                    Vec3(radius * math.cos(b), height / 2, radius * math.sin(b)),
                    Vec3(radius * math.cos(a), height / 2, radius * math.sin(a)),
                ),
                f'#{shade:02x}{min(255, shade + 14):02x}ef',
                outline='#5c638a',
            )
        )
    faces.append(
        Face(
            'coffee',
            tuple(
                Vec3(
                    radius * 0.92 * math.cos(math.tau * i / count),
                    -height / 2 + 0.025,
                    radius * 0.92 * math.sin(math.tau * i / count),
                )
                for i in range(count)
            ),
            '#54372d',
        )
    )
    return PropMesh('cup', tuple(faces))


def build(out: Path, *, fps: int = 24) -> Path:
    options = BakeOptions(fps=fps, duration=6)
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets = out / 'assets'
    assets.mkdir(exist_ok=True, mode=0o700)
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise FileNotFoundError('Install DejaVu Sans Bold with its license to build this example')
    copy_dejavu(font, assets, 'font.ttf')
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version='auto')
    scene.add_project(width=1920, height=1080, fps=str(fps), duration=6, background='#f5f0e9', fontPolicy='pinned')
    scene.add_metadata(
        title='Listening and carrying across a cut',
        language='en',
        description='Silent synthetic listening fixture and an authored hand/cup interaction.',
        generator='srstudio; GPT-6 / OpenAI Codex',
    )
    scene.add_output(
        id='main',
        path='renders/continuity.mp4',
        codec='h264',
        width=1920,
        height=1080,
        fps=str(fps),
        preset='fast',
        crf='18',
        faststart=True,
    )
    # Both the character adapter and the separate interaction use source-local animation.
    cv = Canvas(scene, width=1920, height=1080, font_asset='font', local_time=True)
    cv.assets.add_font(
        id='font',
        src='assets/font.ttf',
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / 'font.ttf'),
        license='assets/FONT-LICENSE.txt',
    )
    cv.text(cv.comp, 'title', 'LISTENING AND CARRYING ACROSS A CUT', 70, 25, 1780, 80, 42, color='#302739')
    cv.rect(cv.comp, 60, 145, 880, 790, '#f8e1d3', radius=24)
    cv.rect(cv.comp, 980, 145, 880, 790, '#e8dff0', radius=24)
    cv.text(cv.comp, 'listener-label', 'BENTO / LISTENING', 100, 160, 790, 65, 30, color='#302739')
    cv.text(cv.comp, 'carrier-label', 'HAND / CUP', 1020, 160, 790, 65, 30, color='#302739')
    score = listening_score()
    listener = compile_performance(BENTO, score)
    motion = carry_motion()
    prop = AttachedProp(motion, 'cup')
    camera = Camera(
        projection='perspective',
        distance=5,
        focal=5,
        scale=240,
        origin=(1180, 365),
        view=Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.25)),
    )
    support = PropMesh(
        'support',
        (
            Face(
                'top',
                (Vec3(-0.4, 0.195, -0.32), Vec3(0.4, 0.195, -0.32), Vec3(0.4, 0.195, 0.32), Vec3(-0.4, 0.195, 0.32)),
                '#ab8874',
                outline='#795b4b',
            ),
            Face(
                'front',
                (Vec3(-0.4, 0.195, 0.32), Vec3(0.4, 0.195, 0.32), Vec3(0.4, 0.26, 0.32), Vec3(-0.4, 0.26, 0.32)),
                '#795b4b',
                outline='#795b4b',
            ),
        ),
    )
    sequence = cv.comp.add_sequence(id='shots')
    reports = []
    for name, start, end, zoom in (('wide', 0, 3, 1), ('close', 3, 6, 1.04)):
        shot = sequence.add_group(id=name, end=3)
        framing = cv.group(shot, f'{name}-framing', x=960, y=540, anchorX=960, anchorY=540, scaleX=zoom, scaleY=zoom)
        source = listener.window(start, end).place(
            cv,
            framing,
            placement=Placement(500, 650, scale=0.53, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
            id=f'{name}-performance',
        )
        result = bake_interaction(
            cv,
            source,
            (Participant('hand', motion, 'gloss'),),
            (PropDrawing(cup_mesh(), prop), PropDrawing(support, TransformTrack.constant(prop.sample(0)))),
            id=f'{name}-interaction',
            camera=camera,
            options=options,
        )
        reports.append(result.reports[0][1].to_dict())
        cv.text(
            shot,
            f'{name}-caption',
            'WIDE / listen, lift and carry' if start == 0 else 'CLOSER / motion continues, then the cup returns',
            70,
            950,
            1780,
            60,
            30,
            color='#302739',
        )
    cv.text(
        cv.comp,
        'fixture-note',
        'Silent study • synthetic listening timing • isolated arm interaction',
        70,
        1015,
        1780,
        35,
        19,
        color='#64586c',
    )
    save_motion(motion, out / 'carry.motion.json')
    score_data = {
        'schema': 'srstudio.acting/1.0.0',
        'duration': score.duration,
        # This fixture uses the original schema; dataclass fields can grow independently of it.
        'beats': [
            {'at': beat.at, 'emotion': beat.emotion, 'gaze': beat.gaze, 'transition': beat.transition}
            for beat in score.beats
        ],
        'seed': score.seed,
        'sample_rate': score.sample_rate,
        'heard': [
            {'at': line.at, 'alignment': line.alignment.to_json(), 'levels': list(line.levels)} for line in score.heard
        ],
    }
    (out / 'listening.score.json').write_text(json.dumps(score_data, indent=2, allow_nan=False) + '\n')
    samples = [listener.sample(i / fps) for i in range(6 * fps)]
    nods = []
    for sample in samples:
        assert sample.head is not None  # this example uses the Toon head rig
        nods.append(sample.head.nod)
    report = {
        'schema': 'srstudio.acting-continuity/1.0.0',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'source': {
            'audio': 'none; silent synthetic planning fixture',
            'alignment': 'synthetic',
            'levels': 'synthetic constant -24 dB at 100 Hz',
        },
        'listening': {
            'heard_lines': 3,
            'mouth_always_closed': all(s.mouth == 'closed' for s in samples),
            'max_nod': max(nods),
        },
        'continuity': {
            'cut': 3,
            'listener_equal': listener.sample(3) == listener.window(3, 6).sample(0),
            'prop_equal': prop.sample(3) == motion.sample(3).hand.frame.compose(motion.attachments[0].offset),
            'prop_frame': asdict(prop.sample(3)),
        },
        'motion': reports[0],
        'fps': fps,
        'limits': [
            'Interaction uses held frames and average surface-depth sorting.',
            'Spatial attachment continuity does not certify collision-free gripping or whole-body balance.',
        ],
    }
    problems = scene.check(schema=True)
    if problems:
        raise ValueError(problems)
    report['validation'] = {'schema': True, 'findings': []}
    path = out / 'continuity.scene.xml'
    path.write_bytes(scene.to_bytes(layout='pretty'))
    (out / 'continuity-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fps', type=int, default=24)
    args = parser.parse_args()
    print(build(args.output, fps=args.fps))


if __name__ == '__main__':
    main()
