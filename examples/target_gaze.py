"""Two original drawing styles track one authored target across cuts.

Run ``python examples/target_gaze.py OUTPUT`` with a new directory, then
``scene-render encode OUTPUT/target-gaze.scene.xml --strict``. The target uses
local observer coordinates; this is a stylized 2D study, not a biomechanical model.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, acting, gaze, toon_critters, toon_head, toon_inked
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT

DURATION = 4
CUTS = (1.25, 2.75)


def document() -> dict:
    return {
        'duration': DURATION,
        'fps': 60,
        'target': {
            'curve': 'sine-in-out',
            'keys': [
                {'time': 0, 'point': [0, 0, 2]},
                {'time': 0.8, 'point': [-0.9, 0.1, 2]},
                {'time': 1.2, 'point': [-0.9, 0.1, 2]},
                {'time': 2, 'point': [0.9, -0.35, 2]},
                {'time': 2.4, 'point': [0.9, -0.35, 2]},
                {'time': 3.2, 'point': [0, 0.4, 2]},
                {'time': 4, 'point': [0, 0, 2]},
            ],
        },
        'limits': {'eye_yaw': 22, 'eye_latency': 0.03, 'head_latency': 0.25, 'head_yaw': 20},
    }


def build(out: Path, *, cuts: bool = True) -> Path:
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise FileNotFoundError('Install DejaVu Sans Bold with its license to build this example')
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    assets = out / 'assets'
    assets.mkdir(mode=0o700)
    copy_dejavu(font, assets, 'font.ttf')
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version='auto')
    scene.add_project(width=1920, height=1080, fps='24', duration=DURATION, background='#f5f0e9', fontPolicy='pinned')
    scene.add_metadata(
        title='Eyes lead, the head follows',
        description='A shared target on Critter Sloth and Inked Fox, with continuous performance clocks.',
        generator='srstudio.gaze; GPT-6 / OpenAI Codex',
        language='en',
    )
    scene.add_output(
        id='main',
        path='renders/target-gaze.mp4',
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
    cv.text(cv.comp, 'title', 'EYES LEAD, THE HEAD FOLLOWS', 60, 25, 1800, 70, 44, color='#302739')
    cv.text(
        cv.comp,
        'subtitle',
        'Same target / two drawing styles / one continuous performance',
        60,
        100,
        1800,
        50,
        28,
        color='#302739',
    )
    records, plans = [], []
    spec = document()
    target = gaze.GazePlan(gaze.parse_gaze(spec))
    (out / 'target.json').write_text(json.dumps(spec, indent=2, allow_nan=False) + '\n')
    for i, (name, head, label) in enumerate(
        (('sloth', toon_critters.SLOTH_RIG, 'CRITTER / SLOTH'), ('inked-fox', toon_inked.FOX_RIG, 'INKED / FOX'))
    ):
        left = 60 + 920 * i
        cv.rect(cv.comp, left, 175, 880, 770, ('#f8e1d3', '#e8dff0')[i], radius=24)
        cv.text(cv.comp, f'label-{name}', label, left + 30, 195, 820, 55, 30, color='#302739')
        rig = acting.ActingRig(
            name, 'toon', (acting.Emotion('neutral', acting.Expression('wide', 'flat'), 'desk'),), head_rig=head
        )
        score = acting.ActingScore(
            DURATION,
            (
                acting.ActingBeat(2.2, expression=acting.Expression('half'), transition=0),
                acting.ActingBeat(3.3, expression=acting.Expression('wide'), transition=0),
            ),
            idle=False,
            overrides=acting.Overrides(gaze=()),
        )
        plan = acting.compile_performance(rig, score).with_target_gaze(target)
        plans.append(plan)
        records.append(
            {
                'name': name,
                'target_file': 'target.json',
                'capabilities': toon_head.gaze_capabilities(head),
                'cut_state_equal': [plan.window(t, DURATION).sample(0) == plan.sample(t) for t in CUTS],
                'samples': [asdict(plan.sample(t)) for t in (0, 0.15, 0.5, 1, 1.25, 2, 2.75, 3, 3.5)],
            }
        )
    # Identical framing in both builds isolates cut-clock continuity from camera
    # placement; the integration test compares actual rendered pixels.
    sequence = cv.comp.add_sequence(id='shots')
    boundaries = (0, *CUTS, DURATION) if cuts else (0, DURATION)
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        shot = sequence.add_group(id=f'shot-{index}', end=end - start)
        for i, plan in enumerate(plans):
            plan.window(start, end).place(
                cv,
                shot,
                id=f'actor-{index}-{i}',
                placement=Placement(500 + 920 * i, 875, scale=0.76, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
            )
    # Direction labels describe the source target, not a screen-space fixation.
    for i, (start, end, text) in enumerate(
        ((0, 1.2, 'LOOK LEFT'), (1.2, 2.4, 'LOOK RIGHT AND UP'), (2.4, 3.2, 'LOOK DOWN'), (3.2, 4, 'RETURN TO CENTER'))
    ):
        group = cv.group(cv.comp, f'direction-{i}', start=start, end=end)
        cv.text(group, f'cue-{i}', text, 60, 970, 900, 60, 32, color='#302739')
    cv.text(cv.comp, 'timing', 'Eyes: 30 ms / head: 250 ms', 1000, 970, 850, 60, 28, color='#302739')
    problems = scene.check(schema=True)
    if problems:
        raise ValueError(problems)
    path = out / 'target-gaze.scene.xml'
    path.write_bytes(scene.to_bytes(layout='pretty'))
    sources = (
        'examples/target_gaze.py',
        'src/srstudio/gaze.py',
        'src/srstudio/_gaze_drawing.py',
        'src/srstudio/acting.py',
        'src/srstudio/_acting_compile.py',
        'src/srstudio/character_clips.py',
        'src/srstudio/toon_head.py',
        'src/srstudio/toon_critters.py',
        'src/srstudio/toon_inked.py',
        'src/srstudio/_curves.py',
    )
    report = {
        'schema': 'srstudio.target-gaze-study/1.0.0',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'duration': DURATION,
        'fps': 24,
        'cuts': list(CUTS) if cuts else [],
        'plan': target.describe(),
        'performers': records,
        'human_ratings': None,
        'limits': [
            'Stylized 2D pupil translation and head follow, not world-space fixation or anatomy.',
            'Linear sampled angles do not guarantee velocity or acceleration continuity.',
            'Expression drawings switch; lids keep their authored painter order.',
            'No human perceptual-quality rating or approval is claimed.',
        ],
        'versions': {'srstudio': version('srstudio'), 'sr-core': version('sr-core')},
        'sources': {name: sha256(Path(__file__).resolve().parents[1] / name) for name in sources},
    }
    (out / 'gaze-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    for item in out.rglob('*'):
        item.chmod(0o700 if item.is_dir() else 0o600)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    print(build(parser.parse_args().output))


if __name__ == '__main__':
    main()
