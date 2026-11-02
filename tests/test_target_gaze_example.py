"""The gaze study exposes its source inputs and verifies pixels across real cuts."""

import importlib.util
import json
import re
import stat
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

from srstudio.digest import sha256
from srstudio.gaze import GazePlan, parse_gaze


def example():
    path = Path(__file__).resolve().parents[1] / 'examples/target_gaze.py'
    spec = importlib.util.spec_from_file_location('target_gaze_example', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_study_exposes_bounded_inputs_source_hashes_and_both_drawing_capabilities(tmp_path, scene_render):
    path = example().build(tmp_path / 'study')
    report = json.loads(path.with_name('gaze-report.json').read_text())
    assert report['schema'] == 'srstudio.target-gaze-study/1.0.0'
    assert report['cuts'] == [1.25, 2.75]
    assert report['human_ratings'] is None
    assert {r['name'] for r in report['performers']} == {'sloth', 'inked-fox'}
    assert all(r['capabilities']['continuous'] for r in report['performers'])
    assert all(all(r['cut_state_equal']) for r in report['performers'])
    root = ET.parse(path).getroot()
    assert len(root.findall('.//sequence/group')) == 3
    for row in report['performers']:
        plan = GazePlan(parse_gaze(json.loads(path.with_name(row['target_file']).read_text())))
        early, late = plan.sample(0.15), plan.sample(1)
        assert early.eye_yaw < 0 and early.head_yaw == 0
        assert late.eye_yaw < 0 and late.head_yaw < 0
        assert plan.window(1.25, 4).sample(0.25) == plan.sample(1.5)
    repo = Path(__file__).resolve().parents[1]
    assert all(sha256(repo / name) == value for name, value in report['sources'].items())
    subprocess.run([str(scene_render), 'validate', str(path), '--deny-warnings'], capture_output=True, check=True)
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in path.parent.rglob('*') if p.is_file())


def test_real_rendered_pixels_preserve_both_performers_after_cuts(tmp_path, scene_render):
    module = example()
    paths = [module.build(tmp_path / name, cuts=cuts) for name, cuts in (('cut', True), ('uncut', False))]
    for time in (1.25, 2.875):
        frames = []
        for i, path in enumerate(paths):
            output = tmp_path / f'{i}-{time}.png'
            subprocess.run(
                [str(scene_render), 'render', str(path), '--time', str(time), '--output', str(output), '--strict'],
                capture_output=True,
                check=True,
                timeout=120,
            )
            frames.append(np.asarray(Image.open(output).convert('RGB')))
        assert frames[0].shape == (1080, 1920, 3)
        assert np.array_equal(frames[0], frames[1])


def test_actor_geometry_stays_between_panel_labels_and_bottom_captions(tmp_path, scene_render):
    path = example().build(tmp_path / 'study')
    shapes = {s.get('id'): s for s in ET.parse(path).iter('shape') if s.get('path')}
    for time in (0.5, 1.25, 2.875, 3.5):
        done = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        visible = [
            n for n in json.loads(done.stdout)['result']['nodes'] if n['id'] in shapes and n['world_opacity'] > 0
        ]
        assert len(visible) > 50
        for node in visible:
            # Brush paths use absolute M/C commands. Their control hull bounds
            # the rendered curves, including motion from every ancestor group.
            path_data = shapes[node['id']].get('path')
            assert set(re.findall('[A-Za-z]', path_data)) <= set('MCZ')
            values = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', path_data)]
            a, b, c, d, e, f = node['world']
            for x, y in zip(values[::2], values[1::2], strict=True):
                assert 80 <= a * x + c * y + e <= 1840
                assert 260 <= b * x + d * y + f <= 945
