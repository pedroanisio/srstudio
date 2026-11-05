"""An agent can distinguish artifacts, executed checks and missing verification."""

import json
import sys
from pathlib import Path

import pytest

from srstudio import cli
from srstudio.build_report import CHECKS, BuildReport
from srstudio.errors import SrstudioError
from srstudio.layout import LayoutError


@pytest.mark.parametrize('names', [['motion_quality'], ['sdk', 'typo'], [None], [[]], 'sdk', None, 3])
def test_sdk_required_checks_reject_invalid_names_with_repair_details(names):
    with pytest.raises(SrstudioError) as caught:
        BuildReport().require(names)
    error = caught.value.to_dict()
    assert error['code'] == 'build.check'
    assert error['path'] == 'require_check'
    assert error['actual'] == names
    assert error['expected'] == list(CHECKS)
    assert 'motion-quality' in error['remedy']
    json.dumps(error, allow_nan=False)


def test_sdk_required_checks_accept_empty_and_passed_check_names():
    report = BuildReport()
    report.require([])
    report.results['sdk'].append({'status': 'passed'})
    report.require(['sdk', 'sdk'])


@pytest.fixture
def starter(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', list(sys.argv))
    monkeypatch.setattr(sys, 'path', list(sys.path))
    root = tmp_path / 'hello'
    assert cli.main(['init', str(root), '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    return root, result


def no_engine():
    raise LayoutError('engine unavailable')


def test_init_command_records_usage_and_reports_skipped_frames(starter, monkeypatch, capsys):
    root, initialized = starter
    assert initialized['build'][-1] == str(root)
    monkeypatch.setattr(cli, 'find_engine', no_engine)
    args = initialized['build'][1:]
    assert cli.main([args[0], '--json', *args[1:]]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['checks']['sdk']['status'] == 'passed'
    assert result['checks']['usage']['status'] == 'passed'
    for name in ('anatomy', 'text'):
        assert result['checks'][name]['status'] == 'skipped'
        assert result['checks'][name]['results'][0]['reason']
    paths = {a['path'] for a in result['artifacts']}
    assert str(root / 'hello.scene.xml') in paths and str(root / 'parts.json') in paths
    assert all(Path(p).is_file() for p in paths)


def test_required_checks_refuse_skipped_verification(starter, monkeypatch, capsys):
    root, _ = starter
    monkeypatch.setattr(cli, 'find_engine', no_engine)
    assert cli.main(['build', '--json', '--require-check', 'anatomy', str(root / 'build.py'), str(root)]) == 1
    failure = json.loads(capsys.readouterr().err)
    assert failure['code'] == 'build.required_checks'
    assert failure['context']['build']['checks']['anatomy']['status'] == 'skipped'
    assert any(a['kind'] == 'scene' for a in failure['context']['build']['artifacts'])


@pytest.mark.parametrize('outcome', ['passed', 'failed', 'skipped'])
def test_frame_check_reports_actual_outcome(starter, monkeypatch, capsys, outcome):
    root, _ = starter
    monkeypatch.setattr(cli, 'find_engine', lambda: Path('/fake/engine'))

    def anatomy(*args):
        if outcome == 'skipped':
            raise cli.FrameGraphError('cannot measure')
        return ['anatomy fault'] if outcome == 'failed' else []

    monkeypatch.setattr(cli.anatomy_gate, 'after_build', anatomy)
    monkeypatch.setattr(cli.text_rules, 'after_build', lambda *args: [])
    status = cli.main(['build', '--json', str(root / 'build.py'), str(root)])
    output = capsys.readouterr()
    result = json.loads(output.out) if status == 0 else json.loads(output.err)['context']['build']
    assert result['checks']['anatomy']['status'] == outcome
    assert result['checks']['text']['status'] == 'passed'
    assert status == (1 if outcome == 'failed' else 0)


def test_noop_build_does_not_claim_stale_artifacts_or_validation(tmp_path, capsys):
    (tmp_path / 'old.scene.xml').write_text('old scene')
    script = tmp_path / 'noop.py'
    script.write_text('pass')
    assert cli.main(['build', '--json', str(script)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['artifacts'] == []
    assert result['checks']['sdk']['status'] == 'skipped'


def test_overridden_check_does_not_claim_sdk_or_schema_execution(starter, capsys):
    root, _ = starter
    script = root / 'build.py'
    script.write_text(script.read_text().replace('ep.setup(', 'ep.check = lambda: []\nep.setup('))
    assert cli.main(['build', '--json', str(script)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['checks']['sdk']['status'] == result['checks']['schema']['status'] == 'skipped'


def test_require_check_is_enforced_in_text_mode(tmp_path, capsys):
    script = tmp_path / 'noop.py'
    script.write_text('pass')
    assert cli.main(['build', '--require-check', 'sdk', str(script)]) == 1
    assert 'Required build checks' in capsys.readouterr().err
