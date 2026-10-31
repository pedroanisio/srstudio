"""Recoverable sample writes and verification for all versioned part kinds."""

import os
from pathlib import Path

import pytest

from srstudio import catalog_specimens, parts, registry, sample, specimens


def test_readme_uses_the_current_versioned_parts_api():
    text = (Path(__file__).resolve().parents[1] / 'README.md').read_text()
    assert 'srstudio.characters.part' not in text
    assert 'parts.drawing' in text
    assert 'episodes=' in text


@pytest.mark.parametrize('name', ['barber-cape', 'barbershop', 'answer-bubble'])
def test_noncharacter_replacement_can_be_verified_against_catalog(project, monkeypatch, name):
    part = parts.get(name)
    assert part.kind != 'character' and part.refused is None
    assert catalog_specimens.digest(name, 1, project.parent) == part.version(1).drawing
    assert specimens.digest(name, 1, episodes=project.parent) == part.version(1).drawing
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    original = registry.get(part.kind, name).builder
    registry.register(part.kind, name, replace=True)(original)
    with pytest.raises(parts.UnverifiedBuilderError):
        parts.drawing(name)
    specimens.check(name, 1, episodes=project.parent)
    assert parts.drawing(name).builder is original
    assert parts.pin(name, 1).number == 1


def test_failed_noncharacter_recheck_revokes_previous_verification(project, monkeypatch):
    name = 'answer-bubble'
    part = parts.get(name)
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    original = registry.get(part.kind, name).builder
    registry.register(part.kind, name, replace=True)(original)
    specimens.check(name, 1, episodes=project.parent)
    monkeypatch.setattr(catalog_specimens, 'digest', lambda *args: 'wrong')
    with pytest.raises(specimens.DrawingChangedError):
        specimens.check(name, 1, episodes=project.parent)
    with pytest.raises(parts.UnverifiedBuilderError):
        parts.pin(name, 1)


def test_noncharacter_verification_explains_missing_project_assets(tmp_path, monkeypatch):
    name = 'answer-bubble'
    part = parts.get(name)
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    original = registry.get(part.kind, name).builder
    registry.register(part.kind, name, replace=True)(original)
    with pytest.raises(specimens.SpecimenError, match='episodes=') as caught:
        specimens.check(name, 1, episodes=tmp_path)
    assert 'SRSTUDIO_EPISODES' in str(caught.value)
    with pytest.raises(parts.UnverifiedBuilderError):
        parts.pin(name, 1)


def test_noncharacter_verification_does_not_trust_a_builder_swapped_during_check(project, monkeypatch):
    name = 'answer-bubble'
    part = parts.get(name)
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    original = registry.get(part.kind, name).builder
    registry.register(part.kind, name, replace=True)(original)
    entry = registry.get(part.kind, name)

    def race(*args):
        entry.builder = lambda: None
        return part.version(1).drawing

    monkeypatch.setattr(catalog_specimens, 'digest', race)
    with pytest.raises(specimens.SpecimenError, match='changed during'):
        specimens.check(name, 1, episodes=project.parent)
    with pytest.raises(parts.UnverifiedBuilderError):
        parts.drawing(name)


def test_refused_part_can_restore_original_builder(monkeypatch):
    name = 'office-wide'
    part = parts.get(name)
    assert part.refused is not None
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    original = registry.get(part.kind, name).builder
    original_info = registry.describe(part.kind, name)
    registry.register(part.kind, name, replace=True, summary='replacement')(lambda: None)
    registry.register(part.kind, name, replace=True, summary='another replacement')(lambda: None)
    with pytest.raises(parts.UnverifiedBuilderError, match='restore'):
        parts.drawing(name)
    with pytest.raises(specimens.SpecimenError, match='no standalone specimen'):
        specimens.digest(name)
    parts.restore(name, 1)
    assert parts.drawing(name).builder is original
    assert registry.describe(part.kind, name) == original_info
    assert parts.pin(name, 1).number == 1


def test_refused_part_without_recorded_original_explains_recovery(monkeypatch):
    name = 'office-wide'
    part = parts.get(name)
    monkeypatch.setitem(registry._REGISTRY, part.kind, dict(registry._REGISTRY[part.kind]))
    registry._REGISTRY[part.kind].pop(name)
    registry.register(part.kind, name, replace=True)(lambda: None)
    with pytest.raises(parts.UnverifiedBuilderError, match='no original builder') as caught:
        parts.drawing(name)
    assert 'parts.restore' not in str(caught.value)
    with pytest.raises(parts.PartError, match='no original builder'):
        parts.restore(name)


def test_sample_no_overwrite_preserves_concurrent_edit(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    original = os.link

    def race(source, target, *args, **kwargs):
        if Path(target) == root / 'assets/dialogue.wav':
            (root / 'dialogue.json').write_text('concurrent update')
            Path(target).write_text('concurrent audio')
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, 'link', race)
    with pytest.raises(sample.SampleError, match='preserved'):
        sample.write_sample_project(root, [sample.Line('a', 'hello')])
    assert (root / 'dialogue.json').read_text() == 'concurrent update'
    assert (root / 'assets/dialogue.wav').read_text() == 'concurrent audio'


def test_sample_overwrite_failure_keeps_concurrent_edit_and_backup(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    sample.write_sample_project(root, [sample.Line('a', 'old')])
    old = (root / 'dialogue.json').read_bytes()
    original = os.link
    failed = False

    def race(source, target, *args, **kwargs):
        nonlocal failed
        if Path(target) == root / 'assets/dialogue.wav' and Path(source).name == 'new' and not failed:
            failed = True
            (root / 'dialogue.json').write_text('concurrent update')
            raise OSError('audio install failed')
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, 'link', race)
    with pytest.raises(sample.SampleError, match='backup') as caught:
        sample.write_sample_project(root, [sample.Line('a', 'new')], overwrite=True)
    assert (root / 'dialogue.json').read_text() == 'concurrent update'
    backups = list(root.glob('.srstudio-output-*/old'))
    assert any(path.read_bytes() == old and str(path) in str(caught.value) for path in backups)


def test_sample_retains_backup_if_restore_fails(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    sample.write_sample_project(root, [sample.Line('a', 'old')])
    old = (root / 'assets/dialogue.wav').read_bytes()
    original = os.link

    def fail(source, target, *args, **kwargs):
        if Path(target) == root / 'assets/dialogue.wav':
            raise OSError('audio unavailable')
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, 'link', fail)
    with pytest.raises(sample.SampleError, match='backup') as caught:
        sample.write_sample_project(root, [sample.Line('a', 'new')], overwrite=True)
    backups = list((root / 'assets').glob('.srstudio-output-*/old'))
    assert any(path.read_bytes() == old and str(path) in str(caught.value) for path in backups)
