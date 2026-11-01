"""Render artifacts retain the identity of their engine, recipe and font inputs."""

import hashlib
import os

import numpy as np
import pytest

from srstudio import plates
from support.plates import plate, printed_plate


@pytest.fixture
def rendering(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'build-a')
    engine.chmod(0o755)
    fonts = tmp_path / 'fonts'
    fonts.mkdir()
    (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-a')
    calls = []

    def render(engine, source, out):
        payload = engine.read_bytes() + source.read_bytes()
        calls.append(payload)
        colour = np.array([*hashlib.sha256(payload).digest()[:3], 255], dtype=np.uint8).reshape(1, 1, 4)
        plates.write_png(out, colour)

    monkeypatch.setattr(plates, '_engine_render', render)
    return engine, fonts, tmp_path / 'cache', calls


def test_engine_content_changes_invalidate_without_losing_previous_build(rendering):
    engine, fonts, cache, calls = rendering
    made = plate()
    first = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    original = first.read_bytes()
    assert plates.render(made, engine=engine, cache=cache, fonts=fonts) == first
    assert len(calls) == 1
    stamp = engine.stat()
    engine.write_bytes(b'build-b')
    os.utime(engine, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    second = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert len(calls) == 2
    assert first != second and first.name != second.name
    assert first.read_bytes() == original and second.read_bytes() != original
    engine.write_bytes(b'build-a')
    assert plates.render(made, engine=engine, cache=cache, fonts=fonts) == first
    assert len(calls) == 2


def test_same_engine_bytes_at_another_path_reuse_the_artifact(rendering):
    engine, fonts, cache, calls = rendering
    first = plates.render(plate(), engine=engine, cache=cache, fonts=fonts)
    other = engine.with_name('another-engine')
    other.write_bytes(engine.read_bytes())
    other.chmod(0o755)
    assert plates.render(plate(), engine=other, cache=cache, fonts=fonts) == first
    assert len(calls) == 1


def test_printed_plate_and_texture_follow_engine_and_actual_font_bytes(rendering):
    engine, fonts, cache, calls = rendering
    made = printed_plate()
    first = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert len(calls) == 2
    assert plates.render(made, engine=engine, cache=cache, fonts=fonts) == first
    assert len(calls) == 2
    engine.write_bytes(b'build-b')
    second = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert len(calls) == 4 and second != first
    (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-b')
    third = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert len(calls) == 6 and third not in (first, second)


def test_quality_changes_invalidate_plate_but_reuse_print_texture(rendering, monkeypatch):
    engine, fonts, cache, calls = rendering
    made = printed_plate()
    first = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    monkeypatch.setattr(plates, 'SAMPLES', plates.SAMPLES + 1)
    second = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert second != first and second.name != first.name
    assert len(calls) == 3


def test_standalone_print_uses_renderer_and_font_identity(rendering):
    engine, fonts, cache, calls = rendering
    printed = printed_plate().materials[0].print
    first = plates.print_png(printed, engine=engine, cache=cache, fonts=fonts)
    assert plates.print_png(printed, engine=engine, cache=cache, fonts=fonts) == first
    assert len(calls) == 1
    (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-b')
    second = plates.print_png(printed, engine=engine, cache=cache, fonts=fonts)
    assert second != first and second.name != first.name and len(calls) == 2
    engine.write_bytes(b'build-b')
    third = plates.print_png(printed, engine=engine, cache=cache, fonts=fonts)
    assert third not in (first, second) and len(calls) == 3


def test_legacy_unowned_cache_is_not_accepted_as_current_render(rendering):
    engine, fonts, cache, calls = rendering
    cache.mkdir()
    legacy = cache / f'{plates.digest(plate())}.png'
    legacy.write_bytes(b'unknown renderer')
    current = plates.render(plate(), engine=engine, cache=cache, fonts=fonts)
    assert len(calls) == 1 and current != legacy
    assert legacy.read_bytes() == b'unknown renderer'


@pytest.mark.parametrize('missing', ['engine', 'font'])
def test_missing_identity_inputs_fail_before_creating_cache(rendering, missing):
    engine, fonts, cache, calls = rendering
    (engine if missing == 'engine' else fonts / plates.PRINT_FONT[2]).unlink()
    with pytest.raises(plates.PlateError) as caught:
        plates.render(printed_plate(), engine=engine, cache=cache, fonts=fonts)
    error = caught.value.to_dict()
    assert error['code'] == 'plate.cache.input'
    assert error['path'] == missing
    assert error['remedy']
    assert not cache.exists() and not calls


def test_changed_engine_during_render_is_not_published(rendering, monkeypatch):
    engine, fonts, cache, _ = rendering
    original = plates._engine_render

    def replace_engine(engine, source, out):
        original(engine, source, out)
        engine.write_bytes(b'build-b')

    monkeypatch.setattr(plates, '_engine_render', replace_engine)
    with pytest.raises(plates.PlateError) as caught:
        plates.render(plate(), engine=engine, cache=cache, fonts=fonts)
    assert caught.value.to_dict()['code'] == 'plate.cache.changed'
    assert not list(cache.rglob('*.png'))


def test_catalog_materializes_the_selected_artifact_at_the_drawing_reference(rendering, monkeypatch, tmp_path):
    from sr_core.scene import Scene

    from srstudio import Canvas, catalog_specimens, rafa_host, registry

    engine, fonts, _, calls = rendering
    made = plate()
    scene = Scene(version='auto')
    scene.add_project(width=64, height=64, fps='1', duration=1)
    cv = Canvas(scene, font_asset=None)
    rafa_host.place(cv, cv.comp, made)
    entry = registry.get('prop', 'coffee-cup')
    plan = catalog_specimens.Plan(entry, scene.to_bytes(), 0, 'cache-proof', True)
    folder = tmp_path / 'catalog'
    cache = folder / 'work' / catalog_specimens.style_of(entry).slug / 'plates'
    monkeypatch.setattr(catalog_specimens.rafa_host, 'part_plates', lambda name: (made,))
    monkeypatch.setattr(catalog_specimens.pedro_host, 'part_plates', lambda name: ())
    monkeypatch.setenv('SRSTUDIO_FONTS', str(fonts))

    class Inspected(Exception):
        pass

    selected = None

    def inspect_assets(engine, document, at, out):
        logical = out.parent / 'plates' / f'{plates.digest(made)}.png'
        assert logical.read_bytes() == selected.read_bytes()
        raise Inspected

    monkeypatch.setattr(catalog_specimens, '_render', inspect_assets)
    for contents in (b'build-a', b'build-b'):
        engine.write_bytes(contents)
        selected = plates.render(made, engine=engine, cache=cache, fonts=fonts)
        with pytest.raises(Inspected):
            catalog_specimens.render_one(plan, engine, folder)
    assert len(calls) == 2


def test_real_print_and_plate_resolve_namespaced_dependencies(scene_render, project, tmp_path, monkeypatch):
    monkeypatch.setattr(plates, 'PRINT_FONT', ('DejaVu Sans', '700', 'DejaVuSans-Bold.ttf', 'Bitstream-Vera'))
    fonts, cache = project / 'assets', tmp_path / 'cache'
    made = printed_plate()
    texture = plates.print_png(made.materials[0].print, engine=scene_render, cache=cache, fonts=fonts)
    pixels = plates.pixels(texture)
    assert pixels.shape == (64, 64, 4) and (pixels[..., :3] < 128).any()
    rendered = plates.render(made, engine=scene_render, cache=cache, fonts=fonts)
    assert plates.pixels(rendered).shape == (64, 64, 4)
    monkeypatch.setattr(plates, '_engine_render', lambda *args: pytest.fail('warm build invoked the engine'))
    assert plates.print_png(made.materials[0].print, engine=scene_render, cache=cache, fonts=fonts) == texture
    assert plates.render(made, engine=scene_render, cache=cache, fonts=fonts) == rendered


def test_renderer_identity_reaches_copied_host_assets(rendering, tmp_path):
    from sr_core.scene import Scene

    from srstudio import Canvas, plate_host

    engine, fonts, cache, _ = rendering
    first = plates.render(plate(), engine=engine, cache=cache, fonts=fonts)
    engine.write_bytes(b'build-b')
    second = plates.render(plate(), engine=engine, cache=cache, fonts=fonts)
    cv = Canvas(Scene(version='auto'), font_asset=None)
    shelf = plate_host.Shelf(cv, tmp_path / 'project', 'host')
    assert shelf.name(first, 64, 64) != shelf.name(second, 64, 64)
    copied = tmp_path / 'project' / 'assets' / 'host'
    assert (copied / first.name).read_bytes() == first.read_bytes()
    assert (copied / second.name).read_bytes() == second.read_bytes()


def test_nonexecutable_renderer_has_a_typed_failure_and_no_published_image(tmp_path):
    engine = tmp_path / 'engine'
    engine.write_text('not executable')
    cache = tmp_path / 'cache'
    with pytest.raises(plates.PlateError) as caught:
        plates.render(plate(), engine=engine, cache=cache, fonts=tmp_path)
    error = caught.value.to_dict()
    assert error['code'] == 'plate.render.engine' and error['path'] == 'engine'
    assert error['remedy']
    assert not list(cache.rglob('*.png'))


def test_catalog_refuses_font_changes_between_cache_binding_and_emission(rendering, monkeypatch):
    from srstudio import catalog_specimens as cs
    from srstudio import registry

    engine, fonts, cache, _ = rendering
    made = printed_plate()
    document = b'<scene><project width="64" height="64"/><composition/></scene>'
    plan = cs.Plan(registry.get('prop', 'coffee-cup'), document, 0, 'key', True)
    monkeypatch.setenv('SRSTUDIO_FONTS', str(fonts))
    monkeypatch.setattr(cs, 'plan', lambda *args: ([plan], {}))
    monkeypatch.setattr(cs.rafa_host, 'part_plates', lambda name: (made,))
    monkeypatch.setattr(cs.pedro_host, 'part_plates', lambda name: ())
    original = cs.render_one

    def changed(plan, engine, folder):
        (fonts / plates.PRINT_FONT[2]).write_bytes(b'font-b')
        original(plan, engine, folder)

    def forbidden(*args):
        raise RuntimeError('catalog rendered after its inputs changed')

    monkeypatch.setattr(cs, 'render_one', changed)
    monkeypatch.setattr(cs, '_render', forbidden)
    with pytest.raises(cs.SpecimenRenderError, match='plate inputs changed'):
        cs.render_all(engine, cache, cache)
