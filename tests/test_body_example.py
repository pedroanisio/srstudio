"""Two flat-foot steps remain supported through original-clock cuts."""

import importlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from srstudio import body, gpu
from srstudio._bounded_process import ProcessLimits, run


def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.body_steps')


def test_example_coordinates_both_legs_root_and_torso(monkeypatch):
    module = example(monkeypatch)
    plan = body.compile_body(body.parse_body(module.document()))
    assert len(plan.score.steps) == 2
    assert not plan.sample(1.75).legs[1].planted
    assert not plan.sample(4.25).legs[0].planted
    assert all(leg.planted for leg in plan.sample(6).legs)
    assert all(abs(leg.sole.origin.z - 0.2) < 1e-12 for leg in plan.sample(6).legs)
    assert plan.sample(1).torso.rotation != plan.sample(0).torso.rotation


def test_build_exports_measured_support_and_closed_input(tmp_path, monkeypatch):
    paths = example(monkeypatch).build(tmp_path / 'study')
    report = json.loads(paths[0].with_name('report.json').read_text())
    assert report['schema'] == 'srstudio.body-study/1.0.0'
    assert report['min_support_margin'] >= 0.005
    assert report['max_planted_residual'] < 1e-12
    assert report['cut_times'] == [1.625, 4.125]
    assert len(report['samples']) == 145
    assert report['drawing_approval'] is None
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in paths)


def test_cut_does_not_restart_step_pixels(tmp_path, monkeypatch, scene_render):
    paths = example(monkeypatch).build(tmp_path / 'study')
    for start in (38, 98):
        for path in paths:
            with gpu.held():
                run(
                    (
                        str(scene_render),
                        'render',
                        str(path),
                        '--frames',
                        f'{start}..{start + 3}',
                        '--output',
                        str(tmp_path / f'{path.stem}-%04d.png'),
                        '--strict',
                        '--quality',
                        'final',
                        '--json',
                    ),
                    input=b'',
                    limits=ProcessLimits(timeout=120, stdout_bytes=2 * 1024**2),
                )
        for i in range(start, start + 3):
            with Image.open(tmp_path / f'uncut-{i:04d}.png') as a, Image.open(tmp_path / f'cuts-{i:04d}.png') as b:
                assert a.size == b.size == (1920, 1080)
                assert np.array_equal(np.asarray(a), np.asarray(b)), f'cut changed frame {i}'


def test_documented_body_recipe_executes():
    text = (Path(__file__).parents[1] / 'docs/authoring-body.md').read_text()
    code = text.split('<!-- body-recipe:start -->')[1].split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'body-recipe', 'exec'), namespace)
    assert namespace['pose'].support_margin >= namespace['plan'].profile.support_margin
