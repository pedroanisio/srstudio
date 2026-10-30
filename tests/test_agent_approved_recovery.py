"""Approval metadata, atomic markers and typed character records."""

import json

import pytest
from sr_core.scene import SchemaValueError

from srstudio import Episode, EpisodeSpec, parts, registry
from srstudio.cli import main
from srstudio.parts import PartError


def test_marker_failure_is_atomic_and_retry_succeeds(project):
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False))
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.markers([(0, 0.5, 'hello', 'good'), (0.5, 1, 'world', 'bad id')])
    assert ep.scene.to_bytes() == before
    ep.markers([(0, 0.5, 'hello', 'good'), (0.5, 1, 'world', 'fixed')])
    assert ep.check() == []


def test_marker_failure_with_existing_markers_preserves_them(project):
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False))
    ep.markers([(0, 1, 'existing', 'existing')])
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.markers([(0, 1, 'other', 'other')])
    assert ep.scene.to_bytes() == before


def test_replaced_character_reports_unverified_builder_and_default(monkeypatch, capsys):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    original = registry.get('character', 'toon-fox@2')

    @registry.register('character', 'toon-fox@2', replace=True)
    def replacement():
        pass

    detail = registry.describe('character', 'toon-fox@2')['character_version']
    assert detail['status'] == 'unverified'
    assert detail['record_status'] == 'approved'
    assert detail['default_status'] == 'unverified'
    assert registry.describe('character', 'toon-fox')['character_version']['default_status'] == 'unverified'
    assert (
        next(row for row in registry.catalog(kind='character') if row['name'] == 'toon-fox@2')['character_version']
        == detail
    )
    assert main(['inspect', 'character', 'toon-fox@2']) == 0
    text = capsys.readouterr().out
    assert 'unverified' in text and 'approved' in text
    assert registry.get('character', 'toon-fox@2').builder is replacement
    assert original.builder is not replacement


def version_doc(field, value):
    v = {
        'number': 1,
        'date': '2026-10-30',
        'note': 'record',
        'status': 'approved',
        'proof': '',
        'drawing': 'a' * 64,
        'approval': None,
        'rig': None,
    }
    v[field] = value
    return {
        'schema': parts.TABLE_SCHEMA,
        'parts': {'toon-fox': {'kind': 'character', 'style': 'toon', 'refused': None, 'versions': [v]}},
    }


@pytest.mark.parametrize(
    'field,value',
    [
        ('drawing', 12),
        ('drawing', None),
        ('drawing', []),
        ('proof', 42),
        ('proof', None),
        ('proof', []),
        ('status', 4),
        ('approval', 1),
    ],
)
def test_bad_character_version_fields_report_context(tmp_path, field, value):
    path = tmp_path / 'table.json'
    path.write_text(json.dumps(version_doc(field, value)))
    with pytest.raises(PartError) as caught:
        parts.read(path)
    error = str(caught.value)
    assert 'toon-fox' in error and '1' in error and field in error


def test_direct_version_refuses_non_approval_object():
    with pytest.raises(PartError, match='approval'):
        parts.Version(2, '2026-10-30', 'record', 'approved', 'proof.mp4', 'a' * 64, approval='yes')


def test_mutated_character_builder_is_unverified(monkeypatch):
    entry = registry.get('character', 'toon-fox@2')
    monkeypatch.setattr(entry, 'builder', lambda: None)
    info = registry.describe('character', 'toon-fox@2')['character_version']
    assert info['status'] == 'unverified' and info['record_status'] == 'approved'
    assert registry.describe('character', 'toon-fox')['character_version']['default_status'] == 'unverified'


def test_marker_extra_failure_rolls_back_and_can_retry(project):
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False))
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.markers([(0, 0.5, 'hello', 'good')], extra=[('bad id', 1, 'extra')])
    assert ep.scene.to_bytes() == before
    ep.markers([(0, 0.5, 'hello', 'good')], extra=[('fixed', 1, 'extra')])
    assert ep.check() == []
