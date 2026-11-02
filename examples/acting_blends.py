"""Authored facial deformation and posture, with cuts inside both transitions.

Run ``python -m examples.acting_blends OUTPUT``. Compare uncut.xml and cuts.xml
at the same frame numbers; their pixels must match. Both encode a five-second
silent study. The candidate drawing requires its own approval before adoption.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import bento_blends, compile_performance, parse_score
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT

CUTS = (1.375, 3.375)


def document() -> dict:
    return {
        'schema': 'srstudio.acting/1.2.0',
        'duration': 5,
        'idle': False,
        'sample_rate': 24,
        'beats': [
            {'at': 0, 'breath': 0, 'head': {'lean': 0, 'nod': 0}, 'transition': 0},
            {
                'at': 1,
                'emotion': 'concerned',
                'gesture': 'tablet',
                'blend': True,
                'transition': 1,
                'head': {'lean': 0.5, 'nod': 5},
                'breath': 0.5,
            },
            {
                'at': 3,
                'emotion': 'deadpan',
                'gesture': 'tablet',
                'blend': True,
                'transition': 1,
                'head': {'lean': -0.5, 'nod': 0},
                'breath': 0,
            },
        ],
    }


def build(output: Path) -> tuple[Path, Path]:
    rig = bento_blends()
    score = document()
    plan = compile_performance(rig, parse_score(score))
    scenes = []
    for name, boundaries in (('uncut', (0, 5)), ('cuts', (0, *CUTS, 5))):
        scene = Scene(version='auto')
        scene.add_project(width=1080, height=1920, fps='24', duration=5, background='#F3EEE6')
        scene.add_metadata(
            title='Concern becoming deadpan',
            language='en',
            generator='srstudio.acting_blends; GPT-6 / OpenAI Codex',
            description='Authored eyes, mouth and posture on a single performance clock.',
        )
        scene.add_output(
            id='main',
            path=f'{name}.mp4',
            codec='h264',
            width=1080,
            height=1920,
            fps='24',
            preset='fast',
            crf='18',
            faststart=True,
        )
        cv = Canvas(scene, font_asset=None)
        for i, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
            plan.window(start, end).place(
                cv,
                cv.comp,
                at=start,
                id=f'performance-{i}',
                placement=Placement(540, 1390, scale=1, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
            )
        findings = scene.check(schema=True)
        if findings:
            raise ValueError(findings)
        scenes.append((name, scene.to_bytes(layout='pretty')))
    previous = os.umask(0o077)
    try:
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        for name, data in scenes:
            (output / f'{name}.xml').write_bytes(data)
        (output / 'score.json').write_text(json.dumps(score, indent=2) + '\n')
        report = {
            'schema': 'srstudio.acting-blends/1.0.0',
            'generated_by': {'tool': 'OpenAI Codex', 'model': 'GPT-6'},
            'source_sha256': sha256(Path(__file__)),
            'rig': rig.describe(),
            'cut_times': CUTS,
            'face_fps': 24,
            'drawing_approval': None,
            'cut_state_equal': [plan.window(t, 5).sample(0) == plan.sample(t) for t in CUTS],
            'frames': [asdict(plan.sample(i / 24)) for i in range(120)],
            'limitations': [
                'Held facial geometry at 24 Hz; continuous intent is separately sampled.',
                'Gestures remain discrete; this study holds the tablet gesture.',
                'No speech, named/target gaze or full-body constraint claim.',
            ],
        }
        (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    finally:
        os.umask(previous)
    return output / 'uncut.xml', output / 'cuts.xml'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    for path in build(args.output):
        print(path)


if __name__ == '__main__':
    main()
