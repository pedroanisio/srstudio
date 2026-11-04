"""Agent verification, plugin streams and repair fields survive boundary cases."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import acting, cli, onboarding
from srstudio.voice import Alignment, VoiceOutputError


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', list(sys.argv))
    monkeypatch.setattr(sys, 'path', list(sys.path))
    root = tmp_path / 'hello'
    onboarding.init_project(root)
    return root


@pytest.mark.parametrize('json_output', [False, True])
@pytest.mark.parametrize('outside', [False, True])
def test_frame_checks_follow_all_published_scenes(project, monkeypatch, capsys, outside, json_output):
    root = project
    destination = root.parent / 'exports' if outside else root
    outputs = [destination / 'new.scene.xml', destination / 'second.scene.xml']
    (root / 'hello.scene.xml').write_text('<old/>')
    script = root / 'build.py'
    script.write_text(
        script.read_text().replace(
            'ep.finish(overwrite=args.overwrite)', '\n'.join(f'ep.finish(out=Path({str(p)!r}))' for p in outputs)
        )
    )
    measured = []
    monkeypatch.setattr(cli, 'find_engine', lambda: Path('/fake/engine'))
    monkeypatch.setattr(cli.anatomy_gate, 'after_build', lambda p, slug, scene, e: measured.append((p, scene)) or [])
    monkeypatch.setattr(
        cli.text_rules, 'after_build', lambda slug, scene, e: ['new scene fault'] if scene == outputs[1] else []
    )
    flags = ['--json'] if json_output else []
    status = cli.main(
        ['build', *flags, '--require-check', 'anatomy', '--require-check', 'text', str(script), str(root)]
    )
    assert status == 1
    assert measured == [(root, p) for p in outputs]
    if json_output:
        evidence = json.loads(capsys.readouterr().err)['context']['build']
        assert {a['path'] for a in evidence['artifacts'] if a['kind'] == 'scene'} == {str(p) for p in outputs}
        assert evidence['checks']['text']['status'] == 'failed'


def test_noop_with_old_scene_cannot_satisfy_required_frame_check(project, monkeypatch, capsys):
    (project / 'hello.scene.xml').write_text('<old/>')
    script = project / 'build.py'
    script.write_text('pass')
    monkeypatch.setattr(cli, 'find_engine', lambda: Path('/fake/engine'))
    monkeypatch.setattr(cli.anatomy_gate, 'after_build', lambda *args: [])
    monkeypatch.setattr(cli.text_rules, 'after_build', lambda *args: [])
    assert cli.main(['build', '--json', '--require-check', 'anatomy', str(script), str(project)]) == 1
    result = json.loads(capsys.readouterr().err)
    assert result['context']['build']['checks']['anatomy']['status'] == 'skipped'


@pytest.mark.parametrize('exit_code', ['0', 'None'])
def test_successful_script_exit_still_enforces_requirements(project, capsys, exit_code):
    script = project / 'build.py'
    script.write_text(f'raise SystemExit({exit_code})')
    assert cli.main(['build', '--require-check', 'sdk', str(script), str(project)]) == 1
    assert 'Required build checks' in capsys.readouterr().err


@pytest.mark.parametrize('json_output', [False, True])
def test_successful_script_exit_still_runs_frame_checks(project, monkeypatch, capsys, json_output):
    script = project / 'build.py'
    script.write_text(script.read_text() + '\nraise SystemExit(0)\n')
    monkeypatch.setattr(cli, 'find_engine', lambda: Path('/fake/engine'))
    monkeypatch.setattr(cli.anatomy_gate, 'after_build', lambda *args: ['frame fault'])
    monkeypatch.setattr(cli.text_rules, 'after_build', lambda *args: [])
    assert cli.main(['build', *(['--json'] if json_output else []), str(script), str(project)]) == 1
    if json_output:
        evidence = json.loads(capsys.readouterr().err)['context']['build']
        assert evidence['checks']['anatomy']['status'] == 'failed'
        assert evidence['checks']['usage']['status'] == 'passed'


@pytest.mark.parametrize('exit_code, status', [(0.0, 1), ('', 1), (3, 3)])
@pytest.mark.parametrize('json_output', [False, True])
def test_unsuccessful_script_exit_preserves_status(project, capsys, exit_code, status, json_output):
    script = project / 'build.py'
    script.write_text(f'raise SystemExit({exit_code!r})')
    if json_output:
        assert cli.main(['build', '--json', str(script)]) == status
        assert json.loads(capsys.readouterr().err)['code'] == 'build.exit'
    else:
        with pytest.raises(SystemExit) as stopped:
            cli.main(['build', str(script)])
        assert stopped.value.code == exit_code


@pytest.mark.parametrize('command', [['catalog', '--summary'], ['inspect', 'prop', 'coffee-cup']])
@pytest.mark.parametrize('failure', ['', "raise ValueError('configuration missing')", 'raise SystemExit(0)'])
def test_plugin_logs_and_failures_keep_json_streams_parseable(tmp_path, command, failure):
    (tmp_path / 'review_plugin.py').write_text(
        "import os, subprocess, sys\n"
        "print('plugin python log')\n"
        "os.write(1, b'plugin native log\\n')\n"
        "subprocess.run([sys.executable, '-c', \"print('plugin child log')\"], check=True)\n"
        "print('plugin warning', file=sys.stderr)\n" + failure
    )
    env = {**os.environ, 'PYTHONPATH': str(tmp_path) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    process = subprocess.run(
        [sys.executable, '-m', 'srstudio', *command, '--json', '--plugins', 'review_plugin'],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if failure:
        assert process.returncode == 2
        assert process.stdout == ''
        error = json.loads(process.stderr)
        assert error['code'] == 'plugin.import' and error['path'] == 'plugins'
        assert error['actual'] == 'review_plugin'
        for source in ('python', 'native', 'child'):
            assert f'plugin {source} log' in error['context']['stdout']
        assert 'plugin warning' in error['context']['stderr']
    else:
        assert process.returncode == 0 and process.stderr == ''
        assert isinstance(json.loads(process.stdout), dict)


@pytest.mark.parametrize('channel', ['speech', 'heard'])
@pytest.mark.parametrize(
    'field, values, suffix, actual',
    [
        ('character_end_times_seconds', [-1, 1], '[0]', -1),
        ('character_start_times_seconds', [0, True], '[1]', True),
        ('character_start_times_seconds', [0.5, 0.2], '[1]', 0.2),
        ('character_end_times_seconds', [0.1, 0.1], '[1]', 0.1),
        ('characters', ['a', 'word'], '[1]', 'word'),
        ('character_end_times_seconds', [0.5], '', 1),
    ],
)
def test_alignment_diagnostics_retain_nested_repair_fields(channel, field, values, suffix, actual):
    alignment = {
        'characters': ['a', 'b'],
        'character_start_times_seconds': [0, 0.5],
        'character_end_times_seconds': [0.5, 1],
        field: values,
    }
    where = f'{channel}[0].alignment'
    with pytest.raises(VoiceOutputError) as direct:
        Alignment.parse(alignment, where)
    score = {
        'schema': 'srstudio.acting/1.2.0',
        'duration': 2,
        channel: [{'at': 0, 'alignment': alignment, 'levels': [0.2]}],
    }
    with pytest.raises(acting.ActingError) as nested:
        acting.parse_score(score)
    for error in (direct.value, nested.value):
        detail = error.to_dict()
        assert detail['path'] == f'{where}.{field}{suffix}'
        assert detail['actual'] == actual
        assert detail['expected'] is not None
        assert detail['remedy'] and 'rig profile' not in detail['remedy']
    assert nested.value.to_dict()['code'] == 'acting.input'
