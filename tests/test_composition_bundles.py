"""Closed mixed scenes render within shared limits and publish complete bundles."""

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import plates
from support.composition import mixed, plate_source, prepared_plate_plan, renderer


@pytest.fixture
def inputs():
    return mixed()


def test_mixed_bundle_is_complete_private_and_warm_cache_launches_nothing(inputs, tmp_path):
    plan, assets = inputs
    engine = renderer(tmp_path)
    output = tmp_path / 'bundle'
    with plates.render_session(max_invocations=1) as outer:
        first = c.emit_bundle(plan, assets, output, engine=engine, cache=tmp_path / 'cache')
    assert outer.invocations == 1
    assert first.work.new_plates == first.work.engine_invocations == 1
    assert (output / 'scene.xml').read_bytes() == first.xml
    assert len(first.resources) == 1
    for resource in first.resources:
        assert (output / resource.name).read_bytes() == resource.data
    assert output.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in output.iterdir())
    root = ET.fromstring(first.xml)
    groups = list(root.find('composition'))
    assert [node.get('id') for node in groups] == ['l0', 'l1']
    assert groups[0].get('x') == groups[0].get('y') == '0'
    assert groups[0].get('scaleX') is None
    assert groups[1].get('x') == '3' and groups[1].get('y') == '4'
    with plates.render_session(max_invocations=0) as warm:
        second = c.emit_bundle(plan, assets, tmp_path / 'again', engine=engine, cache=tmp_path / 'cache')
    assert warm.invocations == second.work.new_plates == second.work.engine_invocations == 0
    assert second.work.cache_hits == 1
    assert (first.xml, first.resources, first.digest) == (second.xml, second.resources, second.digest)


def test_existing_output_is_preserved_without_starting_renderer(inputs, tmp_path):
    plan, assets = inputs
    output = tmp_path / 'bundle'
    output.mkdir()
    before = output.stat().st_ino
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, assets, output, engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert output.stat().st_ino == before and list(output.iterdir()) == []
    assert not (tmp_path / 'cache').exists()


@pytest.mark.parametrize('bad', ['vector', 'plate', 'missing', 'duplicate'])
def test_all_assets_are_verified_before_cache_or_output_mutation(inputs, tmp_path, bad):
    plan, assets = inputs
    if bad == 'vector':
        assets = (assets[0], replace(assets[1], xml=b'<scene>'))
    elif bad == 'plate':
        assets = (replace(assets[0], xml=b'<scene>'), assets[1])
    elif bad == 'missing':
        assets = assets[:1]
    else:
        assets = assets + (assets[0],)
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, assets, tmp_path / 'bundle', engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert not (tmp_path / 'cache').exists() and not (tmp_path / 'bundle').exists()


@pytest.mark.parametrize('failure', ['exit', 'png', 'timeout', 'file-limit', 'image-limit'])
def test_renderer_failures_never_publish_images_or_bundle(inputs, tmp_path, failure):
    plan, assets = inputs
    body = '''import sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--output') + 1])
out.write_bytes(b'partial')
'''
    body += {
        'exit': 'sys.exit(7)',
        'png': '',
        'timeout': 'import time; time.sleep(60)',
        'file-limit': "with out.open('wb') as stream: stream.truncate(257 * 1024**2)",
        'image-limit': "out.write_bytes(b'x' * (9 * 1024**2))",
    }[failure]
    engine = renderer(tmp_path, body)
    with plates.render_session(max_invocations=1, timeout=0.2 if failure == 'timeout' else 60) as work:
        with pytest.raises(c.CompositionError):
            c.emit_bundle(plan, assets, tmp_path / 'bundle', engine=engine, cache=tmp_path / 'cache')
    assert work.invocations == 1
    assert list((tmp_path / 'cache').rglob('image.png')) == []
    assert not (tmp_path / 'bundle').exists()


def test_corrupt_warm_cache_is_refused_without_repair_or_renderer_launch(inputs, tmp_path):
    plan, assets = inputs
    engine = renderer(tmp_path)
    c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')
    image = next((tmp_path / 'cache').rglob('image.png'))
    image.write_bytes(b'corrupted')
    with plates.render_session(max_invocations=0) as work:
        with pytest.raises(c.CompositionError):
            c.emit_bundle(plan, assets, tmp_path / 'bundle', engine=engine, cache=tmp_path / 'cache')
    assert work.invocations == 0 and image.read_bytes() == b'corrupted'
    assert not (tmp_path / 'bundle').exists()


def test_engine_identity_invalidates_the_render_cache(inputs, tmp_path):
    plan, assets = inputs
    engine = renderer(tmp_path)
    c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')
    engine.write_text(engine.read_text() + '\n# new engine build\n')
    with plates.render_session(max_invocations=1) as work:
        result = c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')
    assert work.invocations == result.work.new_plates == 1
    assert len(list((tmp_path / 'cache').rglob('image.png'))) == 2


def test_failed_bundle_install_removes_only_its_staging_directory(inputs, tmp_path, monkeypatch):
    from srstudio import _bundle_output

    plan, assets = inputs
    engine = renderer(tmp_path)
    c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')

    def fail(*args):
        raise OSError('publication refused')

    monkeypatch.setattr(_bundle_output, 'rename_new', fail)
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, assets, tmp_path / 'bundle', engine=engine, cache=tmp_path / 'cache')
    assert not (tmp_path / 'bundle').exists()
    assert not list(tmp_path.glob('.srstudio-bundle-*'))


def test_real_engine_renders_mixed_bundle_and_preserves_vector_information(
    inputs, tmp_path, scene_render, record_property
):
    plan, assets = inputs
    # Both the plate and final composite need the software-renderer allowance.
    plan = c.preflight(replace(plan.spec, budget=replace(plan.spec.budget, timeout=120)), plan.bindings)
    assets = tuple(c.prepare_plate(plan, a.layer, a.source) if type(a) is c.PreparedPlate else a for a in assets)
    output = tmp_path / 'bundle'
    result = c.emit_bundle(plan, assets, output, engine=scene_render, cache=tmp_path / 'cache')
    rendered = tmp_path / 'frame.png'
    with plates.render_session(max_invocations=1, timeout=120):
        plates._engine_render(scene_render, output / 'scene.xml', rendered)
    pixels = plates.pixels(rendered)
    assert pixels[6, 5].tolist() == [255, 0, 0, 255]
    assert pixels[32, 32, 3] == 255
    # The project schema defaults to opaque black; the portable plate itself
    # retains transparency outside its geometry.
    assert pixels[0, 0].tolist() == [0, 0, 0, 255]
    assert plates.pixels(output / result.resources[0].name)[0, 0, 3] == 0
    record_property('bundle_digest', result.digest)
    record_property('image_sha256', hashlib.sha256(rendered.read_bytes()).hexdigest())


def test_warm_cache_preserves_validation_budget_errors(inputs, tmp_path, monkeypatch):
    from srstudio import _composition_bundle as bundle

    plan, assets = inputs
    engine = renderer(tmp_path)
    c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')

    def exhausted(*args):
        raise c.CompositionError('worker timed out', code='composition.budget')

    monkeypatch.setattr(bundle, '_png_size', exhausted)
    with pytest.raises(c.CompositionError) as caught:
        c.compile_bundle(plan, assets, engine=engine, cache=tmp_path / 'cache')
    assert caught.value.to_dict()['code'] == 'composition.budget'


def test_every_created_cache_directory_is_private(inputs, tmp_path):
    plan, assets = inputs
    cache = tmp_path / 'cache'
    c.compile_bundle(plan, assets, engine=renderer(tmp_path), cache=cache)
    assert all(p.stat().st_mode & 0o777 == 0o700 for p in (cache, *cache.rglob('*')) if p.is_dir())


def test_static_windows_share_one_render_and_preserve_visibility(tmp_path):
    item = plate_source()
    base = prepared_plate_plan(item)
    layer = base.spec.layers[0]
    layers = (
        replace(layer, temporal=c.TemporalPolicy(0, 0.5)),
        replace(layer, id='later', temporal=c.TemporalPolicy(0.5, 1)),
    )
    plan = c.preflight(replace(base.spec, layers=layers), base.bindings)
    assets = tuple(c.prepare_plate(plan, layer.id, item) for layer in layers)
    with plates.render_session(max_invocations=1) as work:
        result = c.compile_bundle(plan, assets, engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert work.invocations == result.work.new_plates == 1
    assert len(result.resources) == 1
    groups = ET.fromstring(result.xml).findall('composition/group')
    assert [(g.get('start'), g.get('end')) for g in groups] == [('0', '0.5'), ('0.5', '1')]
    assert groups[0][0].get('asset') == groups[1][0].get('asset')


def test_vector_only_bundle_needs_no_renderer_or_cache(tmp_path):
    from support.composition import paper

    spec, binding, xml = paper(animated=True)
    plan = c.preflight(spec, (binding,))
    source = c.VectorSource(binding.id, xml)
    result = c.emit_bundle(
        plan, (source,), tmp_path / 'bundle', engine=tmp_path / 'missing-engine', cache=tmp_path / 'cache'
    )
    assert result.xml == c.compile_scene(plan, (source,)).xml
    assert result.resources == () and result.work.engine_invocations == 0
    assert not (tmp_path / 'cache').exists()
