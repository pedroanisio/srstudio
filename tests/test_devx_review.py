"""Developer-facing output contracts and reusable style configuration."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from srstudio import CEL, INK, EpisodeSpec, Timeline, parts, releases, usage
from srstudio.cli import main
from srstudio.episode import SceneCheckError
from srstudio.timeline import TimelineError


def test_build_json_captures_native_and_subprocess_output(tmp_path):
    script = tmp_path / 'builder.py'
    script.write_text(
        "import os, subprocess, sys\n"
        "os.write(1, b'native log\\n')\n"
        "subprocess.run([sys.executable, '-c', \"print('child log')\"], check=True)\n"
        "os.write(2, b'bad byte: \\xff\\n')\n"
    )
    process = subprocess.run(
        [sys.executable, '-m', 'srstudio', 'build', '--json', str(script)], capture_output=True, text=True, timeout=30
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert 'native log' in result['context']['stdout'] and 'child log' in result['context']['stdout']
    assert 'bad byte' in result['context']['stderr'] and process.stderr == ''


def test_refused_json_filters_the_same_parts_as_text(capsys):
    assert main(['parts', '--refused', '--json']) == 0
    assert set(json.loads(capsys.readouterr().out)) == {name for name, part in parts.load().items() if part.refused}


def test_build_json_missing_slug_keeps_lookup_exit_code(capsys):
    assert main(['build', '--json', 'no-such-devx-episode']) == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'build.not_found'


def test_build_json_keeps_execution_errors_distinct_from_lookup_errors(tmp_path, monkeypatch, capsys):
    from srstudio import cli

    script = tmp_path / 'builder.py'
    script.write_text("from srstudio.releases import ReleaseError\nraise ReleaseError('bad release')\n")
    assert main(['build', '--json', str(script)]) == 1
    execution = json.loads(capsys.readouterr().err)

    def missing(*args):
        raise releases.ReleaseError('bad lookup')

    monkeypatch.setattr(cli, '_episode_script', missing)
    assert main(['build', '--json', str(script)]) == 2
    lookup = json.loads(capsys.readouterr().err)
    assert execution['code'] == lookup['code'] == 'srstudio.releases.ReleaseError'


def test_digest_json_contains_identity_and_digest(capsys):
    assert main(['parts', '--digest', 'toon-fox@2', '--json']) == 0
    assert json.loads(capsys.readouterr().out) == {
        'name': 'toon-fox',
        'version': 2,
        'digest': parts.get('toon-fox').version(2).drawing,
    }


@pytest.mark.parametrize('pinned', [False, True])
def test_usage_json_preserves_pin_verdict(tmp_path, monkeypatch, capsys, pinned):
    report = usage.Report({'demo': ('toon-bear',)})
    path = report.write(tmp_path / 'usage.json')
    from srstudio.social import InstagramPost

    release = releases.Release(
        'demo', InstagramPost(title='Demo', description='Demo.'), parts={'toon-bear': 1} if pinned else {}
    )
    monkeypatch.setattr(releases, 'load', lambda folder: {'demo': release})
    assert main(['parts', '--usage', str(path), '--json']) == (0 if pinned else 1)
    result = json.loads(capsys.readouterr().out)
    assert result['episodes_measured'] == 1
    assert result['ok'] is pinned
    assert bool(result['drift']) is not pinned


@pytest.mark.parametrize('failure', ['scene', 'timeline', 'exit', 'unexpected', 'success'])
def test_build_json_handles_logs_errors_and_script_arguments(tmp_path, monkeypatch, capsys, failure):
    monkeypatch.setattr(sys, 'argv', list(sys.argv))
    monkeypatch.setattr(sys, 'path', list(sys.path))
    script = tmp_path / 'build.py'
    action = {
        'scene': "from srstudio.episode import SceneCheckError\n"
        "from types import SimpleNamespace\n"
        "raise SceneCheckError([SimpleNamespace(severity='error', code='duplicate', message='duplicate id')])",
        'timeline': "from srstudio import Timeline\nTimeline.from_dict({'duration': 'bad', 'phrases': []})",
        'exit': 'raise SystemExit(3)',
        'unexpected': "raise RuntimeError('broken builder')",
        'success': '',
    }[failure]
    script.write_text(
        "import sys\nprint('builder log')\nprint('builder warning', file=sys.stderr)\n"
        "assert sys.argv[2:] == ['--custom']\n" + action
    )
    status = main(['build', '--json', str(script), str(tmp_path), '--custom'])
    output = capsys.readouterr()
    if failure == 'success':
        assert status == 0
        result = json.loads(output.out)
        assert result['status'] == 'ok'
        assert output.err == ''
    else:
        assert status != 0
        assert output.out == ''
        result = json.loads(output.err)
        assert result['schema'] == 'srstudio.diagnostic/1.0.0'
        assert result['context']['command'] == 'build'
        if failure == 'scene':
            assert result['context']['findings'][0]['code'] == 'duplicate'
        if failure == 'timeline':
            assert result['path'] == 'duration'
    assert 'builder log' in result['context']['stdout']
    assert 'builder warning' in result['context']['stderr']


def test_scene_check_sdk_diagnostic_keeps_individual_findings():
    error = SceneCheckError([SimpleNamespace(severity='error', code='duplicate', message='duplicate id')])
    assert error.to_dict()['context']['findings'] == [
        {'severity': 'error', 'code': 'duplicate', 'message': 'duplicate id'}
    ]


def test_with_style_resolves_all_defaults_without_changing_original(tmp_path):
    original = EpisodeSpec(slug='demo', title='Demo', description='Demo', root=tmp_path, seed=7, fps=60)
    changed = original.with_style(INK)
    fresh = EpisodeSpec(slug='demo', title='Demo', description='Demo', root=tmp_path, seed=7, style=INK)
    for name in (
        'palette',
        'background',
        'width',
        'height',
        'fps',
        'dialogue',
        'audio',
        'font',
        'font_id',
        'font_policy',
        'mouth_style',
        'local_time',
        'safe_area',
        'accessibility',
    ):
        assert getattr(changed, name) == getattr(fresh, name), name
    assert changed.namer('g') == fresh.namer('g') == 'g1'
    assert original.fps == 60 and original.local_time is False
    assert changed.root == tmp_path and changed.seed == 7


def test_with_style_accepts_new_overrides_and_clears_accessibility():
    original = EpisodeSpec(slug='demo', title='Demo', description='Demo', root=Path('.'), seed=7, style=INK)
    changed = original.with_style(CEL, fps=48, audio='music.wav', title='Silent drawing')
    assert changed.fps == 48 and changed.audio == 'music.wav' and changed.title == 'Silent drawing'
    assert changed.font is None and changed.mouth_style is None and changed.accessibility == dict(CEL.accessibility)


@pytest.mark.parametrize('value', ['bad', True, float('inf'), None])
def test_timeline_number_diagnostic_identifies_repair(value):
    data = {'duration': 1, 'phrases': [{'role': 'a', 'text': 'Hi', 'start': value, 'end': 1}]}
    with pytest.raises(TimelineError) as caught:
        Timeline.from_dict(data)
    diagnostic = caught.value.to_dict()
    assert diagnostic['code'] == 'timeline.number'
    assert diagnostic['path'] == 'phrases[0].start'
    assert diagnostic['expected'] == 'finite number'
    assert diagnostic['actual'] == (str(value) if value == float('inf') else value)
    assert diagnostic['remedy']


@pytest.mark.parametrize(
    'data, path, code',
    [
        ({'duration': 1}, 'phrases', 'timeline.required'),
        ({'duration': 1, 'phrases': None}, 'phrases', 'timeline.sequence'),
        ({'duration': 1, 'phrases': [None]}, 'phrases[0]', 'timeline.object'),
        (
            {'duration': 1, 'phrases': [{'role': '', 'text': 'Hi', 'start': 0, 'end': 1}]},
            'phrases[0].role',
            'timeline.text',
        ),
    ],
)
def test_timeline_shape_diagnostic_identifies_repair(data, path, code):
    with pytest.raises(TimelineError) as caught:
        Timeline.from_dict(data)
    diagnostic = caught.value.to_dict()
    assert (diagnostic['path'], diagnostic['code']) == (path, code)
    assert diagnostic['expected'] and diagnostic['remedy']


@pytest.mark.parametrize(
    'data, path, code',
    [
        ({'duration': 0, 'phrases': []}, 'duration', 'timeline.positive'),
        (
            {'duration': 1, 'phrases': [{'role': 'a', 'text': 'Hi', 'start': 0, 'end': 2}]},
            'phrases[0]',
            'timeline.range',
        ),
        (
            {'duration': 1, 'phrases': [], 'camera_cuts': [{'time': 2, 'angle': 'wide'}]},
            'camera_cuts[0].time',
            'timeline.order',
        ),
        ([{'start': 1, 'end': 0, 'text': 'Hi'}], '[0]', 'timeline.range'),
        (
            {
                'duration': 1,
                'items': [
                    {
                        'id': 'a',
                        'actor': 'a',
                        'text': 'Hi',
                        'shot': 'wide',
                        'start': 0,
                        'duration': 1,
                        'words': [{'start': 'bad', 'end': 1}],
                    }
                ],
            },
            'items[0].words[0].start',
            'timeline.number',
        ),
    ],
)
def test_timeline_semantic_errors_keep_input_paths(data, path, code):
    with pytest.raises(TimelineError) as caught:
        Timeline.from_dict(data)
    diagnostic = caught.value.to_dict()
    assert (diagnostic['path'], diagnostic['code']) == (path, code)
    assert diagnostic['expected'] and diagnostic['remedy']
