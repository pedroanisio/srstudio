"""The calibration study ships measured cases, strict scenes and an unrated blinded comparison."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

from srstudio.limbs.errors import LimbError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def example():
    spec = importlib.util.spec_from_file_location('limbs_quality', ROOT / 'examples/limbs_quality.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def study(example, tmp_path_factory):
    report = example.build(tmp_path_factory.mktemp('quality') / 'study', seed='private-test-key')
    return report.parent, json.loads(report.read_text())


def test_study_contains_all_calibrated_references_and_explicitly_rejected_cases(study):
    out, report = study
    assert report['schema'] == 'srstudio.quality-study/1.0.0'
    assert len(report['cases']) == 14
    assert report['render']['status'] == 'not_requested'
    for case in report['cases']:
        assert (out / case['scene']).is_file()
        assert (out / case['motion']).is_file()
        assert case['sdk_findings'] == []
        assert case['expected_frames'] == case['duration'] * 24
        assert len(case['scene_sha256']) == 64
        if case['rejected']:
            assert case['production_failure']['code'] == 'quality.limit'
            assert len(case['report']['quality_findings']) >= 6
        else:
            assert case['production_failure'] is None
            assert not case['report']['quality_findings']


def test_public_packet_does_not_label_numeric_pass_or_fail_as_human_preference(study):
    out, report = study
    assert report['review']['status'] == 'awaiting_ratings'
    assert report['review']['results'] is None
    public = out / 'review'
    manifest = json.loads((public / 'trials.json').read_text())
    assert len(manifest['trials']) == 2
    assert json.loads((public / 'ratings-template.json').read_text())['ratings'] == []
    for path in public.iterdir():
        text = path.read_text()
        assert 'private-test-key' not in text
        assert re.search(r'\b(reference|compressed)\b', text) is None
    assert len(json.loads((out / 'private-key.json').read_text())['trials']) == 2
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in out.rglob('*') if p.is_file())


def test_study_refuses_existing_output_and_invalid_seed_before_writing(example, tmp_path):
    occupied = tmp_path / 'occupied'
    occupied.mkdir()
    sentinel = occupied / 'ratings.json'
    sentinel.write_text('keep')
    with pytest.raises(FileExistsError):
        example.build(occupied, seed='private-test-key')
    assert sentinel.read_text() == 'keep'
    missing = tmp_path / 'new'
    with pytest.raises(LimbError):
        example.build(missing, seed='')
    assert not missing.exists()


def test_quality_recipe_uses_public_presets_and_checks_the_result():
    document = (ROOT / 'docs/catalog/limbs.md').read_text()
    match = re.search(r'<!-- calibrated-quality:start -->\s*```python\n(.*?)```', document, re.S)
    assert match, 'missing executable calibrated-quality recipe'
    namespace = {}
    exec(compile(match[1], 'calibrated-quality recipe', 'exec'), namespace)
    assert namespace['compiled'].report.quality_findings == ()
    assert namespace['scene'].check(schema=True) == []
