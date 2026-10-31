"""Version metadata is discoverable consistently across all part kinds."""

import json

import pytest

from srstudio import parts, registry, specimens
from srstudio.cli import main


@pytest.mark.parametrize(
    ('kind', 'name'), [('prop', 'barber-cape'), ('location', 'barbershop'), ('graphic', 'answer-bubble')]
)
def test_noncharacter_version_metadata_is_available_in_catalog_and_inspect(kind, name, capsys):
    info = registry.describe(kind, name)
    record = parts.get(name)
    version = info['part_version']
    assert version == {
        'part': name,
        'version': 1,
        'status': 'approved',
        'record_status': 'approved',
        'default_status': 'approved',
        'default_version': record.latest().number,
        'default_name': parts.part_name(name, record.latest().number),
    }
    assert info['character_version'] is None
    assert next(row for row in registry.catalog(kind=kind) if row['name'] == name)['part_version'] == version
    assert main(['inspect', kind, name, '--json']) == 0
    assert json.loads(capsys.readouterr().out)['part_version'] == version
    assert main(['inspect', kind, name]) == 0
    assert 'version 1 (approved)' in capsys.readouterr().out
    assert main(['catalog', '--kind', kind, '--json']) == 0
    rows = json.loads(capsys.readouterr().out)
    assert next(row for row in rows if row['name'] == name)['part_version'] == version


def test_replaced_noncharacter_status_shows_unverified(monkeypatch, capsys):
    kind, name = 'graphic', 'answer-bubble'
    monkeypatch.setitem(registry._REGISTRY, kind, dict(registry._REGISTRY[kind]))
    original = registry.get(kind, name).builder
    registry.register(kind, name, replace=True)(original)
    info = registry.describe(kind, name)['part_version']
    assert info['status'] == 'unverified'
    assert info['record_status'] == 'approved'
    assert info['default_status'] == 'unverified'
    assert main(['inspect', kind, name]) == 0
    assert 'unverified' in capsys.readouterr().out


def test_verified_noncharacter_status_becomes_approved(project, monkeypatch):
    kind, name = 'graphic', 'answer-bubble'
    monkeypatch.setitem(registry._REGISTRY, kind, dict(registry._REGISTRY[kind]))
    original = registry.get(kind, name).builder
    registry.register(kind, name, replace=True)(original)
    specimens.check(name, 1, episodes=project.parent)
    info = registry.describe(kind, name)['part_version']
    assert info['status'] == 'approved'
    assert info['default_status'] == 'approved'


def test_character_metadata_retains_legacy_field():
    info = registry.describe('character', 'toon-fox@2')
    new = info['part_version']
    old = info['character_version']
    assert old == {'character': new['part'], **{k: v for k, v in new.items() if k != 'part'}}


def test_plugin_with_same_name_but_wrong_kind_has_no_version(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', dict(registry._REGISTRY['prop']))
    registry.register('prop', 'answer-bubble')(lambda: None)
    assert registry.describe('prop', 'answer-bubble')['part_version'] is None
