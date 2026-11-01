"""The two-family acting example ships inspectable intent and preserves the cut clock."""

import importlib.util
import json
import stat
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio.sample import SYSTEM_FONTS


def gallery():
    path = Path(__file__).resolve().parents[1] / 'examples/acting_gallery.py'
    spec = importlib.util.spec_from_file_location('acting_gallery', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not any(p.is_file() for p in SYSTEM_FONTS), reason='DejaVu Sans is required')
def test_gallery_has_two_families_and_reuses_the_full_clock_after_a_cut(tmp_path, scene_render):
    path = gallery().build(tmp_path / 'acting')
    root = ET.parse(path).getroot()
    report = json.loads(path.with_name('acting-report.json').read_text())
    assert report['schema'] == 'srstudio.acting-gallery/1.0.0'
    assert {item['rig']['family'] for item in report['performers']} == {'toon', 'gloss'}
    assert all(item['cut_state_equal'] for item in report['performers'])
    assert all(item['cut_state']['emotion'] == 'happy' for item in report['performers'])
    assert len(root.findall('.//sequence/group')) == 2
    for name in ('bento', 'nadia'):
        group = root.find(f".//group[@id='close-{name}']")
        assert float(group.get('timeOffset')) == -3
    subprocess.run([str(scene_render), 'validate', str(path), '--deny-warnings'], check=True, capture_output=True)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_documented_score_recipe_is_executable_and_preserves_state():
    path = Path(__file__).resolve().parents[1] / 'docs/authoring-reference.md'
    section = path.read_text().split('<!-- acting:start -->')[1].split('<!-- acting:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'acting-recipe', 'exec'), namespace)
    assert namespace['after_cut'].sample(0) == namespace['plan'].sample(3)
    assert namespace['after_cut'].sample(0).emotion == 'happy'
