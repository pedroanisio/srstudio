"""Regression tests for automated callers consuming the public API."""

import os
import subprocess
import sys

import pytest

from srstudio import Timeline
from srstudio.generated import GeneratedError, load_clips
from srstudio.timeline import TimelineError


def take_data(**changes):
    return {
        'duration': 1,
        'items': [{'id': 'a', 'actor': 'a', 'shot': 'wide', 'text': 'Hi', 'start': 0, 'duration': 1} | changes],
    }


@pytest.mark.parametrize(
    'field,value',
    [
        ('id', None),
        ('id', []),
        ('id', ''),
        ('actor', None),
        ('actor', []),
        ('actor', ''),
        ('shot', []),
        ('shot', None),
        ('text', None),
        ('text', {}),
        ('text', ''),
    ],
)
def test_invalid_take_fields_report_field(field, value):
    with pytest.raises(TimelineError, match=rf'take 0\.{field}'):
        Timeline.from_dict(take_data(**{field: value}))


def test_empty_shot_is_supported_for_unstaged_sequences():
    assert Timeline.from_dict(take_data(shot='')).takes[0].shot == ''


@pytest.mark.parametrize('field,value', [('text', None), ('text', {}), ('text', ''), ('caption', []), ('caption', 123)])
def test_invalid_caption_fields_report_field(field, value):
    item = {'start': 0, 'end': 1, 'text': 'Hi', field: value}
    with pytest.raises(TimelineError, match=rf'caption 0\.{field}'):
        Timeline.from_dict([item])


def clip():
    return {
        'generated': {'id': 'a', 'kind': 'speech', 'provider': 'p', 'model': 'm', 'prompt': 'hi', 'cache': 'a.wav'},
        'sha256': '0' * 64,
        'placement': {'start': 0},
    }


@pytest.mark.parametrize(
    'field,value',
    [
        ('id', None),
        ('cache', None),
        ('provider', []),
        ('provider', ''),
        ('model', None),
        ('prompt', 17),
        ('voice', []),
        ('language', 1),
        ('license', {}),
        ('seed', 'bad'),
        ('seed', True),
    ],
)
def test_invalid_generated_fields_name_clip_and_field(field, value):
    entry = clip()
    entry['generated'][field] = value
    with pytest.raises(GeneratedError, match=rf'clip 1.*{field}'):
        load_clips([clip(), entry])


def test_invalid_clip_digest_is_typed_and_indexed():
    entry = clip()
    entry['sha256'] = None
    with pytest.raises(GeneratedError, match=r'clip 0.*sha256'):
        load_clips([entry])


def test_timeline_file_error_carries_path_and_cause(tmp_path):
    path = tmp_path / 'missing.json'
    with pytest.raises(TimelineError, match='missing.json') as info:
        Timeline.load(path)
    assert isinstance(info.value.__cause__, FileNotFoundError)


def test_missing_timeline_build_is_actionable_without_traceback(tmp_path):
    script = tmp_path / 'build.py'
    script.write_text(
        'from srstudio import Episode, EpisodeSpec\n'
        'Episode(EpisodeSpec(slug="x",title="x",description="x",root="missing",seed=1))\n'
    )
    result = subprocess.run(
        [sys.executable, '-m', 'srstudio', 'build', str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert 'srstudio build:' in result.stderr and 'dialogue.json' in result.stderr
    assert 'Traceback' not in result.stderr


def test_audio_signature_is_visible_to_consumer_type_checker(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in {'MYPYPATH', 'PYTHONPATH'}}
    source = (
        'from srstudio import Episode\n'
        'def build(ep: Episode) -> None:\n'
        '    ep.audio(does_not_exist=True)\n'
        '    ep.audio(loudness=12)\n'
    )
    result = subprocess.run(
        [sys.executable, '-m', 'mypy', '--follow-imports=silent', '--no-incremental', '-c', source],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert '[call-arg]' in result.stdout and '[arg-type]' in result.stdout


@pytest.mark.parametrize('field,value', [('kind', None), ('duration', '1'), ('seed', 1.5)])
def test_invalid_generated_additional_fields_name_clip_and_field(field, value):
    entry = clip()
    entry['generated'][field] = value
    with pytest.raises(GeneratedError, match=rf'clip 0.*{field}'):
        load_clips([entry])


def test_invalid_placement_language_names_clip_and_field():
    entry = clip()
    entry['placement']['language'] = []
    with pytest.raises(GeneratedError, match=r'clip 0.*language'):
        load_clips([entry])


def test_numeric_take_id_is_still_supported():
    assert Timeline.from_dict(take_data(id=42)).takes[0].id == '42'
