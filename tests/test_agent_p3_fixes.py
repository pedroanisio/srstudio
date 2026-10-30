"""Discovering versioned parts and diagnosing plugin imports."""

import json

import pytest

from srstudio import characters, registry
from srstudio.cli import main


def test_character_inspection_distinguishes_registered_and_default_versions():
    default = characters.latest('toon-fox').number
    assert default > 1
    plain = registry.describe('character', 'toon-fox')
    expected = {
        'character': 'toon-fox',
        'version': 1,
        'status': 'approved',
        'record_status': 'approved',
        'default_status': 'approved',
        'default_version': default,
        'default_name': characters.part_name('toon-fox', default),
    }
    assert plain['character_version'] == expected
    newest = registry.describe('character', expected['default_name'])
    assert newest['character_version'] == expected | {'version': default}
    assert registry.get('character', 'toon-fox').name == 'toon-fox'


def test_catalog_and_inspect_expose_version_metadata_in_text_and_json(capsys):
    assert main(['inspect', 'character', 'toon-fox']) == 0
    text = capsys.readouterr().out
    assert 'version 1' in text and 'default' in text and 'toon-fox@2' in text
    assert main(['inspect', 'character', 'toon-fox', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['character_version']['default_name'] == 'toon-fox@2'
    assert main(['catalog', '--kind', 'character', '--style', 'toon', '--json']) == 0
    rows = json.loads(capsys.readouterr().out)
    assert next(x for x in rows if x['name'] == 'toon-fox')['character_version']['default_version'] == 2
    assert main(['catalog', '--kind', 'character', '--style', 'toon']) == 0
    row = next(x for x in capsys.readouterr().out.splitlines() if x.split()[2] == 'toon-fox')
    assert 'version 1' in row and 'toon-fox@2' in row


def test_unversioned_plugin_and_noncharacter_are_inspectable(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))

    @registry.register('character', 'plugin-rabbit')
    def rabbit():
        pass

    assert registry.describe('character', 'plugin-rabbit')['character_version'] is None
    assert registry.describe('location', 'office-wide')['character_version'] is None


@pytest.mark.parametrize('cmd', [['catalog'], ['inspect', 'location', 'office-wide']])
def test_unknown_plugin_has_concise_diagnostic(cmd, capsys):
    assert main([*cmd, '--plugins', 'plugin_not_installed_xyz']) == 2
    result = capsys.readouterr()
    assert result.out == ''
    assert 'plugin_not_installed_xyz' in result.err and 'Traceback' not in result.err


@pytest.mark.parametrize('cmd', [['catalog'], ['inspect', 'location', 'office-wide']])
def test_missing_plugin_dependency_reports_plugin_and_dependency(cmd, tmp_path, monkeypatch, capsys):
    (tmp_path / 'plugin_missing_dep_xyz.py').write_text('import plugin_missing_inner_xyz\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    assert main([*cmd, '--plugins', 'plugin_missing_dep_xyz']) == 2
    result = capsys.readouterr()
    assert result.out == ''
    assert 'plugin_missing_dep_xyz' in result.err and 'plugin_missing_inner_xyz' in result.err
    assert 'Traceback' not in result.err
