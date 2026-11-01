"""Compare legacy, anticipated and spring acting with cuts through both policy phases.

Run ``python examples/acting_transitions.py OUTPUT`` with a new output directory,
then ``scene-render encode OUTPUT/acting-transitions.scene.xml --strict``.
This silent authored study measures state continuity, not audience preference.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import BENTO, compile_performance, parse_score
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT


def document(curve: str | None) -> dict:
    beats = [
        {
            'at': 0,
            'emotion': 'neutral',
            'gaze': 'left',
            'transition': 0,
            'head': {'turn': -1.6, 'roll': -1, 'face_x': -0.6, 'nod': 0},
        },
        {
            'at': 1.2,
            'emotion': 'happy',
            'gaze': 'right',
            'transition': 0.7,
            'head': {'turn': 1.6, 'roll': 1, 'face_x': 0.6, 'nod': 5},
        },
        {
            'at': 3,
            'emotion': 'concerned',
            'gaze': 'ahead',
            'transition': 0.4,
            'head': {'turn': 0, 'roll': 0, 'face_x': 0, 'nod': 0},
        },
    ]
    if curve is not None:
        beats[1]['policy'] = {
            'version': '1.0.0',
            'curve': curve,
            'anticipation': 0.25,
            'anticipation_amount': 0.1,
            'settle': 0.35,
            'overshoot': 0.1,
            'timing': [
                {'channel': 'expression', 'duration': 0.1},
                {'channel': 'gaze', 'duration': 0},
                {'channel': 'turn', 'delay': 0.08},
            ],
        }
        if curve == 'spring':
            beats[1]['policy']['spring'] = {'frequency': 3, 'damping': 0.85}
    return {
        'schema': 'srstudio.acting/1.1.0' if curve else 'srstudio.acting/1.0.0',
        'duration': 4,
        'beats': beats,
        'seed': 17,
        'sample_rate': 24,
        'idle': False,
    }


def build(out: Path) -> Path:
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise FileNotFoundError('Install DejaVu Sans Bold with its license to build this example')
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    assets = out / 'assets'
    assets.mkdir(mode=0o700)
    copy_dejavu(font, assets, 'font.ttf')
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version='auto')
    scene.add_project(width=1920, height=1080, fps='24', duration=4, background='#f5f0e9', fontPolicy='pinned')
    scene.add_metadata(
        title='When the face arrives before the head',
        description='Three authored timing variants; cuts during anticipation and settling.',
        generator='srstudio.acting; GPT-6 / OpenAI Codex',
        language='en',
    )
    scene.add_output(
        id='main',
        path='renders/acting-transitions.mp4',
        codec='h264',
        width=1920,
        height=1080,
        fps='24',
        preset='fast',
        crf='18',
        faststart=True,
    )
    cv = Canvas(scene, width=1920, height=1080, font_asset='font')
    cv.assets.add_font(
        id='font',
        src='assets/font.ttf',
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / 'font.ttf'),
        license='assets/FONT-LICENSE.txt',
    )
    cv.text(cv.comp, 'title', 'WHEN THE FACE ARRIVES BEFORE THE HEAD', 50, 28, 1820, 75, 42, color='#302739')
    variants = [
        ('legacy', None, 'TOGETHER / legacy'),
        ('anticipation', 'cubic-in-out', 'FACE FIRST / anticipation'),
        ('spring', 'spring', 'FACE FIRST / spring'),
    ]
    plans, records = [], []
    for i, (name, curve, label) in enumerate(variants):
        left = 40 + i * 620
        cv.rect(cv.comp, left, 125, 600, 810, ('#f8e1d3', '#e8dff0', '#dce9dd')[i], radius=22)
        cv.text(cv.comp, f'label-{name}', label, left + 20, 150, 560, 60, 27, color='#302739')
        score = document(curve)
        plan = compile_performance(BENTO, parse_score(score))
        plans.append(plan)
        filename = f'{name}.score.json'
        (out / filename).write_text(json.dumps(score, indent=2, allow_nan=False) + '\n')
        records.append(
            {
                'name': name,
                'score_file': filename,
                'cut_state_equal': [plan.window(t, 4).sample(0) == plan.sample(t) for t in (1.1, 2.1)],
                'samples': [asdict(plan.sample(t)) for t in (0.95, 1.1, 1.2, 1.3, 1.9, 2.1, 2.4)],
            }
        )
    sequence = cv.comp.add_sequence(id='shots')
    for index, (start, end) in enumerate(((0, 1.1), (1.1, 2.1), (2.1, 4))):
        shot = sequence.add_group(id=f'shot-{index}', end=end - start)
        for i, plan in enumerate(plans):
            x, y = 340 + 620 * i, 690
            framing = cv.group(
                shot,
                f'frame-{index}-{i}',
                x=x,
                y=y,
                anchorX=x,
                anchorY=y,
                scaleX=1 + 0.04 * index,
                scaleY=1 + 0.04 * index,
            )
            plan.window(start, end).place(
                cv,
                framing,
                id=f'actor-{index}-{i}',
                placement=Placement(x, y, scale=0.49, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
            )
        cv.text(
            shot,
            f'caption-{index}',
            ('Prepare to react', 'CUT / anticipation continues', 'CUT / settling continues, then concern')[index],
            60,
            966,
            1800,
            65,
            32,
            color='#302739',
        )
    report = {
        'schema': 'srstudio.acting-transitions/1.0.0',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'duration': 4,
        'fps': 24,
        'cuts': [1.1, 2.1],
        'variants': records,
        'continuity': BENTO.describe()['transitions']['policy']['continuity'],
        'human_ratings': None,
        'limits': [
            'Faces are held drawings, not facial morphs.',
            'Numeric checks do not establish emotional readability or audience preference.',
            'The film changes framing at each cut; performance time stays continuous.',
            'This study has no speech, audio synthesis or provider calls.',
        ],
        'versions': {'srstudio': version('srstudio'), 'sr-core': version('sr-core')},
        'sources': {
            name: sha256(Path(__file__).resolve().parents[1] / name)
            for name in (
                'examples/acting_transitions.py',
                'src/srstudio/acting.py',
                'src/srstudio/_acting_compile.py',
                'src/srstudio/_acting_parse.py',
                'src/srstudio/_acting_transitions.py',
                'src/srstudio/head_motion.py',
                'src/srstudio/_curves.py',
                'src/srstudio/character_clips.py',
            )
        },
    }
    problems = scene.check(schema=True)
    if problems:
        raise ValueError(problems)
    path = out / 'acting-transitions.scene.xml'
    path.write_bytes(scene.to_bytes(layout='pretty'))
    (out / 'transition-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    for item in out.rglob('*'):
        item.chmod(0o700 if item.is_dir() else 0o600)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    print(build(parser.parse_args().output))


if __name__ == '__main__':
    main()
