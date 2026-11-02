"""The facial study makes cuts inside deformation observable and reproducible."""

import importlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from srstudio import gpu
from srstudio._bounded_process import ProcessLimits, run


def test_example_builds_identical_intent_with_cut_and_uncut_clocks(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    example = importlib.import_module('examples.acting_blends')
    out = tmp_path / 'study'
    paths = example.build(out)
    assert {p.name for p in paths} == {'uncut.xml', 'cuts.xml'}
    report = json.loads((out / 'report.json').read_text())
    assert report['schema'] == 'srstudio.acting-blends/1.0.0'
    assert report['cut_times'] == [1.375, 3.375]
    assert all(report['cut_state_equal'])
    assert report['drawing_approval'] is None
    assert report['face_fps'] == 24
    assert len(report['frames']) == 120
    assert (out.stat().st_mode & 0o777) == 0o700
    assert all((p.stat().st_mode & 0o777) == 0o600 for p in paths)


def test_documented_blend_recipe_runs():
    text = (Path(__file__).parents[1] / 'docs/authoring-acting.md').read_text()
    code = text.split('<!-- acting-blends:start -->')[1].split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'acting-blends-recipe', 'exec'), namespace)
    assert namespace['plan'].sample(1.5).head.nod == 2


def test_renderer_cut_frames_equal_uncut_geometry(tmp_path, monkeypatch, scene_render):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    example = importlib.import_module('examples.acting_blends')
    paths = example.build(tmp_path / 'study')
    for start in (32, 80):
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
        for frame in range(start, start + 3):
            with (
                Image.open(tmp_path / f'uncut-{frame:04}.png') as a,
                Image.open(tmp_path / f'cuts-{frame:04}.png') as b,
            ):
                assert a.size == b.size == (1080, 1920)
                assert np.array_equal(np.asarray(a), np.asarray(b)), f'cut changed frame {frame}'
