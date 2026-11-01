"""Outer catalog caches cannot bypass renderer or printed-plate input changes."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from srstudio import catalog_specimens as cs
from srstudio import plates, registry
from test_plate_cache_identity import printed_plate


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'build-a')
    fonts = tmp_path / 'fonts'
    fonts.mkdir()
    (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-a')
    monkeypatch.setenv('SRSTUDIO_FONTS', str(fonts))
    entry = registry.get('prop', 'coffee-cup')
    plan = cs.Plan(entry, b'<scene><project duration="1"/><composition/></scene>', 0, 'drawing-key', False)
    monkeypatch.setattr(cs, 'plan', lambda *args: ([plan], {}))
    monkeypatch.setattr(cs.rafa_host, 'part_plates', lambda name: (printed_plate(),))
    monkeypatch.setattr(cs.pedro_host, 'part_plates', lambda name: ())
    calls = []

    def render(plan, engine, folder):
        calls.append(plan.key)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{plan.key}.png').write_bytes(engine.read_bytes())

    monkeypatch.setattr(cs, 'render_one', render)
    return engine, fonts, tmp_path / 'cache', calls


def test_specimen_cache_follows_renderer_and_print_inputs(catalog):
    engine, fonts, cache, calls = catalog
    first = cs.render_all(engine, cache, cache).done['coffee-cup'].png
    assert cs.render_all(engine, cache, cache).made == 0
    assert len(calls) == 1
    engine.write_bytes(b'build-b')
    second = cs.render_all(engine, cache, cache).done['coffee-cup'].png
    assert second != first and len(calls) == 2
    (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-b')
    third = cs.render_all(engine, cache, cache).done['coffee-cup'].png
    assert third not in (first, second) and len(calls) == 3
    assert first.read_bytes() == b'build-a'


def test_poster_cache_follows_renderer_bytes(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'build-a')
    scene = tmp_path / 'project' / 'scene.xml'
    scene.parent.mkdir()
    scene.write_text('<scene><project duration="1"/><composition/></scene>')
    monkeypatch.setattr(cs, 'scene_of', lambda *args: scene)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        Path(command[command.index('-o') + 1]).write_bytes(engine.read_bytes())
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    def resize(source, out, *args):
        out.write_bytes(source.read_bytes())

    monkeypatch.setattr(cs.subprocess, 'run', run)
    monkeypatch.setattr(cs, '_resize', resize)
    cache = tmp_path / 'cache'
    first = cs.poster(tmp_path, 'example', engine, cache)
    assert cs.poster(tmp_path, 'example', engine, cache) == first and len(calls) == 1
    engine.write_bytes(b'build-b')
    second = cs.poster(tmp_path, 'example', engine, cache)
    assert second != first and len(calls) == 2
    assert first.read_bytes() == b'build-a' and second.read_bytes() == b'build-b'


def test_bound_specimen_refuses_an_engine_change_before_drawing(tmp_path):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'build-a')
    digest = plates._engine_digest(engine)
    engine.write_bytes(b'build-b')
    plan = cs.Plan(registry.get('prop', 'coffee-cup'), b'', 0, 'key', False, digest, ())
    folder = tmp_path / 'catalog'
    with pytest.raises(cs.SpecimenRenderError) as caught:
        cs.render_one(plan, engine, folder)
    assert caught.value.to_dict()['code'] == 'catalog.renderer.changed'
    assert not folder.exists()


def test_specimen_does_not_publish_when_the_engine_changes_during_render(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'build-a')
    document = b'<scene><project width="64" height="64"/><composition/></scene>'
    plan = cs.Plan(registry.get('prop', 'coffee-cup'), document, 0, 'key', True, plate_inputs=())

    def changed(engine, document, at, out):
        out.write_bytes(b'frame')
        engine.write_bytes(b'build-b')

    monkeypatch.setattr(cs, '_render', changed)
    folder = tmp_path / 'catalog'
    with pytest.raises(cs.SpecimenRenderError, match='renderer changed'):
        cs.render_one(plan, engine, folder)
    assert not (folder / 'key.png').exists()
