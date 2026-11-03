"""Original biped study: shift support, step right, shift support, step left.

Run ``python -m examples.body_steps OUTPUT``. Both views use the same world-space
plan. The diagnostic view shows the support hull and projected mass proxy; the
solid candidate shows the resulting body. Cut and uncut scenes must match pixels.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, body
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import Camera, Frame, Quaternion, Vec3
from srstudio.sample import SYSTEM_FONTS, copy_dejavu

CUTS = (1.625, 4.125)


def document() -> dict:
    def root(time, x, z, lean=0):
        return {
            'time': time,
            'root': {'origin': [x, -0.88, z]},
            'torso': [math.cos(lean / 2), 0, 0, math.sin(lean / 2)],
        }

    return {
        'schema': 'srstudio.body/1.0.0',
        'duration': 6,
        'roots': [
            root(0, 0, 0),
            root(1, -0.15, 0, -0.05),
            root(2.5, -0.15, 0, -0.05),
            root(3.5, 0.15, 0.2, 0.05),
            root(4.75, 0.15, 0.2, 0.05),
            root(6, 0, 0.2),
        ],
        'stance': [{'side': side, 'frame': {'origin': [x, 0, 0]}} for side, x in [('left', -0.12), ('right', 0.12)]],
        'steps': [
            {'side': 'right', 'start': 1.25, 'end': 2.25, 'target': {'origin': [0.12, 0, 0.2]}},
            {'side': 'left', 'start': 3.75, 'end': 4.75, 'target': {'origin': [-0.12, 0, 0.2]}},
        ],
    }


def build(output: Path) -> tuple[Path, Path]:
    score = document()
    plan = body.compile_body(body.parse_body(score))
    samples = [plan.sample(i / 24) for i in range(145)]
    residuals = []
    for sample in samples:
        for leg in sample.legs:
            if not leg.planted:
                continue
            anchor = next(f.frame for f in plan.score.stance if f.side == leg.side)
            for step in plan.score.steps:
                if step.side == leg.side and sample.time >= step.end:
                    anchor = step.target
            residuals.append(leg.sole.origin.distance(anchor.origin))
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise FileNotFoundError('Install DejaVu Sans Bold with its license to build this study')
    previous = os.umask(0o077)
    try:
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        assets = output / 'assets'
        assets.mkdir(mode=0o700)
        copy_dejavu(font, assets, 'font.ttf')
        facts = inspect_ttf(font.read_bytes())
        for name, boundaries in (('uncut', (0, 6)), ('cuts', (0, *CUTS, 6))):
            scene = Scene(version='auto')
            scene.add_project(width=1920, height=1080, fps='24', duration=6, background='#F3EEE6', fontPolicy='pinned')
            scene.add_metadata(
                title='Shift support, then step',
                language='en',
                generator='srstudio.body; GPT-6 / OpenAI Codex',
                description='Authored flat-foot stepping with a static support proxy and joint envelopes.',
            )
            scene.add_output(
                id='main',
                path=f'{name}.mp4',
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
            cv.text(cv.comp, 'title', 'SHIFT SUPPORT, THEN STEP', 60, 25, 1800, 65, 38, color='#24304A')
            cv.text(cv.comp, 'diagnostic-label', 'SUPPORT + MASS PROXY', 100, 970, 700, 45, 25, color='#24304A')
            cv.text(cv.comp, 'solid-label', 'SAME PLAN / SOLID BODY', 1100, 970, 700, 45, 25, color='#24304A')
            cv.text(
                cv.comp,
                'limits',
                'Authored flat-foot motion; no dynamics or human gait certification.',
                100,
                1020,
                1700,
                35,
                20,
                color='#4C5361',
            )
            view = Frame(
                rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.18) * Quaternion.axis_angle(Vec3(0, 1, 0), -0.5)
            )
            for style, x in (('wire', 450), ('solid', 1400)):
                camera = Camera(origin=(x, 920), scale=475, view=view)
                for index, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
                    plan.window(start, end).place(
                        cv, cv.comp, camera=camera, at=start, fps=24, style=style, id=f'{style}-{index}'
                    )
            findings = scene.check(schema=True)
            if findings:
                raise ValueError(findings)
            (output / f'{name}.xml').write_bytes(scene.to_bytes(layout='pretty'))
        (output / 'score.json').write_text(json.dumps(score, indent=2) + '\n')
        report = {
            'schema': 'srstudio.body-study/1.0.0',
            'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
            'source_sha256': sha256(Path(__file__)),
            'font_sha256': sha256(assets / 'font.ttf'),
            'profile': asdict(plan.profile),
            'cut_times': CUTS,
            'drawing_approval': None,
            'min_support_margin': min(s.support_margin for s in samples),
            'max_planted_residual': max(residuals),
            'validation_samples': len(plan.checked_times),
            'samples': [asdict(s) for s in samples],
            'scope': 'Two original body drawings share an authored spatial plan; arms stay in a torso-local rest pose.',
            'limits': [
                'Static mass proxy and sampled checks, not a continuous-time dynamic stability certificate.',
                'Flat ground, yaw-only soles, no flight, stairs, rolling feet or collision solver.',
                'Rendering holds whole-body poses at 24 Hz on the original clock.',
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
