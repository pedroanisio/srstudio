"""Scaffolding safety, SDK diagnostics and approved character lookup."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from sr_core.scene import SchemaValueError

from srstudio import SrstudioError, characters, registry, sample
from srstudio.sample import SampleError


@pytest.mark.parametrize(
    'filename', ['dialogue.json', 'assets/dialogue.wav', 'assets/DejaVuSans-Bold.ttf', 'assets/FONT-LICENSE.txt']
)
def test_sample_refuses_existing_artifacts_without_writing(tmp_path, filename):
    root = tmp_path / 'project'
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'keep this')
    with pytest.raises(SampleError, match='overwrite'):
        sample.write_sample_project(root, [sample.Line('a', 'hi')])
    assert path.read_bytes() == b'keep this'
    assert sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()) == [filename]


def test_sample_explicit_overwrite_accepts_project_font_as_source(tmp_path):
    root = tmp_path / 'project'
    sample.write_sample_project(root, [sample.Line('a', 'old')])
    font = root / 'assets' / 'DejaVuSans-Bold.ttf'
    before = font.read_bytes()
    data = sample.write_sample_project(root, [sample.Line('a', 'new')], font=font, overwrite=True)
    assert data['phrases'][0]['text'] == 'new'
    assert json.loads((root / 'dialogue.json').read_text()) == data
    assert font.read_bytes() == before


def test_sample_generation_failure_does_not_modify_existing_project(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    sample.write_sample_project(root, [sample.Line('a', 'old')])
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def fail(*args, **kwargs):
        raise OSError('synthetic output failure')

    monkeypatch.setattr(sample, 'write_wav', fail)
    with pytest.raises(SampleError, match='synthetic output failure'):
        sample.write_sample_project(root, [sample.Line('a', 'new')], overwrite=True)
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()} == before


def test_build_reports_sdk_error_without_traceback(project, tmp_path):
    script = tmp_path / 'invalid.py'
    script.write_text(
        'from srstudio import Episode, EpisodeSpec\n'
        'from pathlib import Path\nimport sys\n'
        'ep = Episode(EpisodeSpec(slug="x", title="x", description="x", '
        'root=Path(sys.argv[1]), seed=1, signature=False))\n'
        'ep.markers([(0, 1, "hello", "bad id")])\n'
    )
    run = subprocess.run(
        [sys.executable, '-m', 'srstudio', 'build', str(script), str(project)], capture_output=True, text=True
    )
    assert run.returncode == 1
    assert 'srstudio build:' in run.stderr and 'bad id' in run.stderr
    assert 'Traceback' not in run.stderr


def test_sdk_errors_remain_catchable_and_documented():
    assert issubclass(SchemaValueError, ValueError)
    assert not issubclass(SchemaValueError, SrstudioError)
    docs = (Path(__file__).resolve().parents[1] / 'docs' / 'authoring-reference.md').read_text()
    assert 'SchemaValueError' in docs
    assert 'Every error the library raises is a `srstudio.SrstudioError`' not in docs


def test_approved_version_refuses_unverified_replacement(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))

    @registry.register('character', 'toon-fox@2', replace=True)
    def fake():
        return 'fake'

    with pytest.raises(characters.CharacterError, match='unverified'):
        characters.part('toon-fox')
    with pytest.raises(characters.CharacterError, match='unverified'):
        characters.part('toon-fox', 2)
    with pytest.raises(characters.CharacterError, match='unverified'):
        characters.pin('toon-fox', 2)
    with pytest.raises(characters.CharacterError, match='unverified'):
        characters.resolved('toon-fox', {'toon-fox': 2})
    with pytest.raises(characters.CharacterError, match='unverified'):
        characters.resolved('toon-fox')
    assert characters.part('toon-fox', 2, allow_unverified=True).builder is fake
    assert characters.part('toon-fox', 1).name == 'toon-fox'


def test_failed_commit_restores_all_existing_sample_artifacts(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    sample.write_sample_project(root, [sample.Line('a', 'old')])
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    replace = sample.os.replace

    def fail_on_audio(src, dst):
        if Path(src).name == 'dialogue.wav' and Path(src).parent.name == 'assets':
            raise OSError('cannot install audio')
        return replace(src, dst)

    monkeypatch.setattr(sample.os, 'replace', fail_on_audio)
    with pytest.raises(SampleError, match='cannot install audio'):
        sample.write_sample_project(root, [sample.Line('a', 'new')], overwrite=True)
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()} == before


def test_example_requires_explicit_overwrite_and_supports_project_font(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'examples' / 'new_episode.py'
    root = tmp_path / 'project'
    base = [sys.executable, str(script), str(root)]
    first = subprocess.run(base, capture_output=True, text=True, timeout=60)
    assert first.returncode == 0, first.stderr
    before = (root / 'dialogue.json').read_bytes()
    again = subprocess.run(base, capture_output=True, text=True, timeout=60)
    assert again.returncode != 0 and 'overwrite' in again.stderr and 'Traceback' not in again.stderr
    assert (root / 'dialogue.json').read_bytes() == before
    font = root / 'assets' / 'DejaVuSans-Bold.ttf'
    explicit = subprocess.run([*base, '--overwrite', '--font', str(font)], capture_output=True, text=True, timeout=60)
    assert explicit.returncode == 0, explicit.stderr
