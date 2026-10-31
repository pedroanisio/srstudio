"""Protect project inputs and expose actionable build and verification failures."""

import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from srstudio import Episode, EpisodeSpec, parts, specimens
from srstudio.episode import EpisodeArgumentError


@pytest.mark.parametrize('input_name', ['dialogue.json', 'assets/dialogue.wav', 'assets/DejaVuSans-Bold.ttf'])
@pytest.mark.parametrize('output_name', ['out', 'report'])
@pytest.mark.parametrize('alias', ['identical', 'symlink', 'hardlink'])
def test_finish_refuses_output_alias_of_project_input(project, tmp_path, input_name, output_name, alias):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    target = root / input_name
    before = target.read_bytes()
    path = target
    if alias == 'symlink':
        path = tmp_path / 'link'
        path.symlink_to(target)
    elif alias == 'hardlink':
        path = tmp_path / 'link'
        path.hardlink_to(target)
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    scene_before = ep.scene.to_bytes()
    kwargs = {'out': tmp_path / 'out.xml', 'report': tmp_path / 'report.json'}
    kwargs[output_name] = path
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(**kwargs)
    assert target.read_bytes() == before
    assert ep.scene.to_bytes() == scene_before
    other = kwargs['report' if output_name == 'out' else 'out']
    assert not other.exists()


@pytest.mark.parametrize('reference', ['relative', 'encoded', 'file_uri'])
def test_finish_protects_additional_declared_asset(project, tmp_path, reference):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    image = root / 'assets' / 'extra image.png'
    image.write_bytes(b'important asset')
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    source = {'relative': 'assets/extra image.png', 'encoded': 'assets/extra%20image.png', 'file_uri': image.as_uri()}[
        reference
    ]
    ep.cv.assets.add_image(id='extra-image', src=source)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=image)
    assert image.read_bytes() == b'important asset'


def test_finish_protects_timing_file_and_take_audio_even_before_audio_is_added(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    data = json.loads((root / 'dialogue.json').read_text())
    data['phrases'][0]['timing_file'] = 'assets/timing.json'
    (root / 'dialogue.json').write_text(json.dumps(data))
    timing = root / 'assets' / 'timing.json'
    timing.write_text('timing data')
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(out=timing)
    assert timing.read_text() == 'timing data'

    take_data = {
        'duration': 1,
        'items': [
            {
                'id': '1',
                'actor': 'a',
                'shot': 'wide',
                'text': 'hi',
                'start': 0,
                'duration': 1,
                'audio': 'assets/dialogue.wav',
            }
        ],
    }
    (root / 'dialogue.json').write_text(json.dumps(take_data))
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False, audio=None))
    audio = root / 'assets' / 'dialogue.wav'
    before = audio.read_bytes()
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=audio)
    assert audio.read_bytes() == before


def test_finish_protects_narration_manifest(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    audio = root / 'assets' / 'dialogue.wav'
    item = {
        'id': '01',
        'text': 'Hi.',
        'phase': 'line',
        'caption_start': 0.1,
        'start': 0.1,
        'duration': 0.1,
        'speech_duration': 0.1,
        'speed': 1.0,
        'lead': 0.0,
        'tempo': 1.0,
        'cut': False,
        'audio': 'assets/dialogue.wav',
        'sha256': hashlib.sha256(audio.read_bytes()).hexdigest(),
    }
    manifest = root / 'narration.json'
    manifest.write_text(json.dumps({'items': [item]}))
    before = manifest.read_bytes()
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.audio(narration=manifest)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=manifest)
    assert manifest.read_bytes() == before


def test_failed_narration_does_not_add_a_protected_manifest(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    missing = root / 'missing-narration.json'
    with pytest.raises(ValueError):
        ep.audio(narration=missing)
    assert ep._input_manifests == []


def test_finish_protects_pinned_clip_before_audio_is_added(project, tmp_path):
    from srstudio.generated import Generated, PlacedClip, Placement

    root = tmp_path / 'project'
    shutil.copytree(project, root)
    cache = root / 'assets' / 'generated.wav'
    shutil.copyfile(root / 'assets' / 'dialogue.wav', cache)
    item = Generated(
        id='clip', kind='speech', provider='test', model='test', prompt='hello', cache='assets/generated.wav'
    )
    clip = PlacedClip(item, hashlib.sha256(cache.read_bytes()).hexdigest(), Placement(start=0))
    data = json.loads((root / 'dialogue.json').read_text())
    data['clips'] = [clip.to_dict()]
    (root / 'dialogue.json').write_text(json.dumps(data))
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    before = cache.read_bytes()
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(out=cache)
    assert cache.read_bytes() == before


def test_proposed_specimen_check_is_not_reported_as_success():
    name, number = next(
        (name, version.number)
        for name, part in parts.load().items()
        for version in part.versions
        if version.status == 'proposed' and not part.refused
    )
    with pytest.raises(parts.NotApprovedError, match='proposed'):
        specimens.check(name, number)


def test_build_reports_filesystem_failure_without_traceback(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    (root / 'output-directory').mkdir()
    script = tmp_path / 'build.py'
    script.write_text(
        'from pathlib import Path\nimport sys\nfrom srstudio import Episode, EpisodeSpec\n'
        'root = Path(sys.argv[1])\n'
        'ep = Episode(EpisodeSpec(slug="x", title="x", description="x", root=root, seed=1, signature=False))\n'
        'ep.finish(out=root / "output-directory")\n'
    )
    result = subprocess.run(
        [sys.executable, '-m', 'srstudio', 'build', str(script), str(root)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 1
    assert 'srstudio build:' in result.stderr and 'output-directory' in result.stderr
    assert 'Traceback' not in result.stderr
