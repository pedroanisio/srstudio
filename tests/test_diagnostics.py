"""An agent can inspect and repair failures without parsing human error prose."""

import json

import pytest

from srstudio import cli
from srstudio.errors import SrstudioError
from srstudio.head_motion import HeadMotionError, HeadPlan
from srstudio.limbs.errors import LimbError


def test_sdk_diagnostic_keeps_legacy_exception_behavior():
    error = HeadMotionError(
        'unknown state',
        code='gaze.unknown',
        path='gaze[0][1]',
        actual='typo',
        expected=['ahead', 'left'],
        remedy='Choose a supported gaze.',
    )
    assert isinstance(error, ValueError)
    assert str(error) == 'unknown state'
    data = error.to_dict()
    assert data['schema'] == 'srstudio.diagnostic/1.0.0'
    assert data['code'] == 'gaze.unknown'
    assert data['path'] == 'gaze[0][1]'
    assert data['actual'] == 'typo'
    assert data['expected'] == ['ahead', 'left']
    assert data['remedy'] == 'Choose a supported gaze.'
    assert json.loads(json.dumps(data, allow_nan=False)) == data


def test_limb_error_keeps_context_and_residual_in_shared_diagnostic():
    error = LimbError('too far', code='reach', residual=0.5, context={'time': 1.2}).with_context(track='left')
    data = error.to_dict()
    assert data['code'] == 'reach'
    assert data['context'] == {'time': 1.2, 'track': 'left'}
    assert data['residual'] == 0.5
    assert error.message == 'too far'
    assert str(error) == "too far (time=1.2, track='left')"


def test_gaze_failure_supplies_machine_repair_context():
    with pytest.raises(HeadMotionError) as caught:
        HeadPlan(gaze=((0, 'typo'),)).check_gaze()
    data = caught.value.to_dict()
    assert data['code'] == 'gaze.unknown'
    assert data['path'] == 'gaze[0][1]'
    assert data['actual'] == 'typo'
    assert 'ahead' in data['expected']
    assert data['remedy']


def test_nonfinite_failure_values_stay_strict_json():
    error = SrstudioError('bad input', actual={'value': float('nan')})
    assert json.loads(json.dumps(error.to_dict(), allow_nan=False))['actual'] == {'value': 'nan'}


def test_extreme_integers_do_not_break_json_encoding_or_payload_bounds():
    error = SrstudioError('bad integer', actual={'value': 10**10000})
    encoded = json.dumps(error.to_dict(), allow_nan=False)
    assert len(encoded) < 1000
    assert json.loads(encoded)['actual']['value'] == '<integer exceeds 4096 bits>'


def test_extreme_dictionary_keys_do_not_replace_the_original_diagnostic_with_an_error():
    error = SrstudioError('invalid mapping', actual={10**5000: 'value'})
    data = error.to_dict()
    assert data['message'] == 'invalid mapping'
    assert data['actual'] == {'<integer exceeds 4096 bits>': 'value'}
    assert len(json.dumps(data, allow_nan=False)) < 1000


def test_diagnostic_keys_do_not_invoke_opaque_object_stringification():
    class Unprintable:
        def __str__(self):
            raise RuntimeError('diagnostics must not execute this')

    data = SrstudioError('invalid mapping', expected={Unprintable(): 'value'}).to_dict()
    assert json.loads(json.dumps(data, allow_nan=False))['expected'] == {'<Unprintable>': 'value'}


def test_json_cli_preserves_failure_status_and_original_error_with_extreme_keys(monkeypatch, capsys):
    error = cli.registry.RegistryError('invalid mapping', actual={10**5000: 'value'})

    def refuse(*args):
        raise error

    monkeypatch.setattr(cli.registry, 'describe', refuse)
    assert cli.main(['inspect', 'character', 'rafa', '--json']) == 2
    out, err = capsys.readouterr()
    assert out == ''
    data = json.loads(err)
    assert data == {**error.to_dict(), 'context': {'command': 'inspect'}}


def test_inspect_json_failure_is_structured_on_stderr(capsys):
    assert cli.main(['inspect', 'character', 'missing-part', '--json']) == 2
    out, err = capsys.readouterr()
    assert out == ''
    data = json.loads(err)
    assert data['schema'] == 'srstudio.diagnostic/1.0.0'
    assert data['code'] == 'registry.not_found'
    assert data['path'] == 'name'
    assert data['actual'] == 'missing-part'
    assert data['context']['command'] == 'inspect'


def test_plugin_import_json_failure_is_structured(capsys):
    assert cli.main(['inspect', 'character', 'rafa', '--plugins', 'missing_srstudio_plugin', '--json']) == 2
    out, err = capsys.readouterr()
    assert out == ''
    assert json.loads(err)['code'] == 'plugin.import'


def test_plain_cli_failure_keeps_human_message(capsys):
    assert cli.main(['inspect', 'character', 'missing-part']) == 2
    assert 'srstudio inspect:' in capsys.readouterr().err


def test_json_argument_errors_use_the_same_envelope(capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(['inspect', 'not-a-kind', 'rafa', '--json'])
    assert caught.value.code == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'cli.arguments'


@pytest.mark.parametrize('command', ['catalog', 'proof', 'parts'])
def test_json_file_errors_use_the_same_envelope(command, tmp_path, capsys):
    options = ['--usage'] if command != 'proof' else []
    argv = [command, *options, str(tmp_path / 'missing.json'), '--json']
    assert cli.main(argv) == (1 if command == 'proof' else 2)
    data = json.loads(capsys.readouterr().err)
    assert data['context']['command'] == command
    assert data['message']


def test_cyclic_error_payload_is_bounded_and_serializable():
    actual = []
    actual.append(actual)
    data = SrstudioError('invalid', actual=actual).to_dict()
    assert len(json.dumps(data, allow_nan=False)) < 1000
