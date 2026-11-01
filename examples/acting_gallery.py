"""Render shared acting intent on Bento and Gloss Nadia across a camera cut.

Run ``python examples/acting_gallery.py OUTPUT`` then
``scene-render encode OUTPUT/acting-gallery.scene.xml --strict``.
This silent study uses original vector characters and no speech/provider calls.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import BENTO, ActingBeat, ActingScore, compile_performance, gloss_actor
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT


def build(out: Path) -> Path:
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
    scene.add_project(width=1920, height=1080, fps='24', duration=6, background='#f5f0e9', fontPolicy='pinned')
    scene.add_metadata(
        title='A performance survives its cut',
        description='Shared emotion intent in Bento and Gloss Nadia; silent authored study.',
        generator='srstudio.acting; GPT-6 / OpenAI Codex',
        language='en',
    )
    scene.add_output(
        id='main',
        path='renders/acting-gallery.mp4',
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
    cv.text(cv.comp, 'title', 'A PERFORMANCE SURVIVES ITS CUT', 80, 30, 1760, 80, 44, color='#302739')
    cv.rect(cv.comp, 60, 145, 880, 790, '#f8e1d3', radius=24)
    cv.rect(cv.comp, 980, 145, 880, 790, '#e8dff0', radius=24)
    cv.text(cv.comp, 'bento-label', 'BENTO / TOON', 100, 170, 790, 60, 30, color='#302739')
    cv.text(cv.comp, 'nadia-label', 'NADIA / GLOSS', 1020, 170, 790, 60, 30, color='#302739')
    score = ActingScore(
        6,
        (
            ActingBeat(0, emotion='neutral', transition=0),
            ActingBeat(1.2, emotion='happy', transition=0.4),
            ActingBeat(3.8, emotion='concerned', transition=0.4),
        ),
        seed=17,
        sample_rate=24,
    )
    directed = replace(
        score,
        beats=(
            replace(score.beats[0], gaze='left'),
            replace(score.beats[1], gaze='right'),
            replace(score.beats[2], gaze='ahead'),
        ),
    )
    performers = (
        (
            'bento',
            compile_performance(BENTO, directed),
            Placement(500, 650, scale=0.53, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
        ),
        ('nadia', compile_performance(gloss_actor('nadia'), score), Placement(1420, 885, scale=0.9)),
    )
    sequence = cv.comp.add_sequence(id='shots')
    for name, start, end, scale in (('wide', 0, 3, 1), ('close', 3, 6, 1.06)):
        shot = sequence.add_group(id=name, end=3)
        for character, plan, placement in performers:
            # Zoom each panel about its own foot/seat anchor, leaving room for the head.
            framing = cv.group(
                shot,
                f'{name}-{character}-framing',
                x=placement.x,
                y=placement.y,
                anchorX=placement.x,
                anchorY=placement.y,
                scaleX=scale,
                scaleY=scale,
            )
            plan.window(start, end).place(cv, framing, placement=placement, id=f'{name}-{character}')
        cv.text(
            shot,
            f'{name}-caption',
            'WIDE / neutral to happy' if start == 0 else 'CLOSER / happy continues, then concerned',
            80,
            965,
            1760,
            65,
            32,
            color='#302739',
        )
    report = {
        'schema': 'srstudio.acting-gallery/1.0.0',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'duration': 6,
        'fps': 24,
        'cut': 3,
        'limits': [
            'Emotion names describe authored intent, not measured viewer perception.',
            'Faces and gestures switch on arrival; numeric head channels ease.',
            'This study is silent; no speech alignment or audio is fabricated.',
        ],
        'performers': [
            {
                'name': name,
                'rig': plan.rig.describe(),
                'owners': dict(plan.owners),
                'cut_state_equal': plan.window(3, 6).sample(0) == plan.sample(3),
                'cut_state': asdict(plan.sample(3)),
            }
            for name, plan, _ in performers
        ],
    }
    problems = scene.check(schema=True)
    if problems:
        raise ValueError(problems)
    path = out / 'acting-gallery.scene.xml'
    path.write_bytes(scene.to_bytes(layout='pretty'))
    (out / 'acting-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.output))


if __name__ == '__main__':
    main()
