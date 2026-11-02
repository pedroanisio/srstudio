"""Printed plate labels keep font provenance, closed resources and bounded renderer work."""

import hashlib
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import plates
from srstudio.sample import SYSTEM_FONTS
from support.composition import prepared_plate_plan
from test_composition_textures import model


def source(label=None, font=None):
    return c.plate_source(
        'host',
        (model(),),
        (
            plates.Material(
                'skin',
                '#FFFFFF',
                print=label or plates.Print('#FFFFFF', 64, 64, (plates.Line('HI', 32, 32, 32, '#000000'),), '#FF0000'),
            ),
        ),
        basis='clay',
        print_font=font if font is not None else next(p for p in SYSTEM_FONTS if p.exists()).read_bytes(),
        print_license='Bitstream-Vera',
    )


def plan_for(item):
    base = prepared_plate_plan(item)
    binding = replace(
        base.bindings[0],
        nodes=256,
        memory_bytes=16 * 1024**2,
        plates=(replace(base.bindings[0].plates[0], engine_invocations=2, samples=96, memory_bytes=16 * 1024**2),),
    )
    return c.preflight(replace(base.spec, budget=replace(base.spec.budget, timeout=120)), (binding,))


@pytest.fixture(params=['public', 'worker'])
def prepare(request):
    if request.param == 'public':
        return c.prepare_plate
    from srstudio import _composition_plate_wire as payload
    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker

    def dispatch(plan, layer, source):
        result = worker.dispatch(
            wire.dumps(
                {
                    'schema': wire.SCHEMA,
                    'operation': 'prepare-plate',
                    'plan': asdict(plan),
                    'layer': layer,
                    'source': payload.source_encode(source),
                }
            )
        )
        response = wire.loads(wire.dumps(result))
        return payload.prepared_decode(response['prepared'], plan, layer, source)

    return dispatch


def test_label_snapshot_is_immutable_deduplicated_and_roundtrips():
    from srstudio import _composition_plate_wire as wire

    item = source()
    assert len(item.prints) == 1 and item.materials[0].print == item.prints[0].id
    assert wire.source_decode(wire.source_encode(item)) == item
    assert c.plate_source_digest(item) != c.plate_source_digest(
        replace(item, prints=(replace(item.prints[0], font=item.prints[0].font + b'changed'),))
    )
    shared = c.plate_source(
        'host',
        (model(),),
        (
            plates.Material('skin', '#FFFFFF', print=item.prints[0].recipe),
            plates.Material('second', '#FFFFFF', print=item.prints[0].recipe),
        ),
        basis='clay',
        print_font=item.prints[0].font,
        print_license='Bitstream-Vera',
    )
    assert len(shared.prints) == 1
    assert shared.materials[0].print == shared.materials[1].print


def test_preparation_is_closed_and_does_not_render(tmp_path, monkeypatch, prepare):
    item = source()
    monkeypatch.chdir(tmp_path)
    asset = prepare(plan_for(item), 'host', item)
    resources = {r.name: r.data for r in asset.resources}
    print_name = next(n for n in resources if n.endswith('.scene.xml'))
    printed = ET.fromstring(resources[print_name])
    font = printed.find('assets/font')
    assert font.get('family') == 'DejaVu Sans' and font.get('weight') == '700'
    assert font.get('license') == 'Bitstream-Vera'
    font_name = font.get('src').removeprefix('../')
    assert resources[font_name] == item.prints[0].font
    assert font.get('sha256') == hashlib.sha256(resources[font_name]).hexdigest()
    assert ET.fromstring(asset.xml).find('materials/material').get('baseColorMap') == print_name.replace(
        '.scene.xml', '.png'
    )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'bad',
    [
        'attempts',
        'samples',
        'dimensions',
        'memory',
        'font',
        'missing-uv',
        'unused',
        'duplicate',
        'missing',
        'color-map',
    ],
)
def test_bad_label_inputs_fail_before_files(tmp_path, monkeypatch, bad, prepare):
    item = source()
    if bad == 'font':
        item = replace(item, prints=(replace(item.prints[0], font=b'invalid'),))
    elif bad == 'missing-uv':
        item = replace(item, meshes=(replace(item.meshes[0], uvs=None),))
    elif bad == 'unused':
        item = replace(item, materials=(replace(item.materials[0], print=''),))
    elif bad == 'duplicate':
        item = replace(item, prints=item.prints * 2)
    elif bad == 'missing':
        item = replace(item, prints=())
    elif bad == 'color-map':
        item = replace(item, materials=(replace(item.materials[0], color_map='also'),))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(c.CompositionError):
        plan = plan_for(item)
        if bad in ('attempts', 'samples', 'dimensions', 'memory'):
            job = replace(
                plan.bindings[0].plates[0],
                **{
                    'attempts': {'engine_invocations': 1},
                    'samples': {'samples': 48},
                    'dimensions': {'width': 32},
                    'memory': {'memory_bytes': 1024},
                }[bad],
            )
            plan = c.preflight(plan.spec, (replace(plan.bindings[0], plates=(job,)),))
        prepare(plan, 'host', item)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'bad',
    ['font-type', 'recipe-type', 'lines-list', 'nan', 'color', 'size', 'dimensions', 'text', 'too-many', 'license'],
)
def test_snapshot_refuses_unbounded_or_ambiguous_labels(bad):
    label = plates.Print('#FFFFFF', 64, 64, (plates.Line('HI', 32, 32, 32, '#000000'),))
    if bad == 'recipe-type':
        label = 'words'
    elif bad == 'lines-list':
        label = replace(label, lines=list(label.lines))
    elif bad == 'nan':
        label = replace(label, lines=(replace(label.lines[0], x=float('nan')),))
    elif bad == 'color':
        label = replace(label, background='paper')
    elif bad == 'size':
        label = replace(label, lines=(replace(label.lines[0], size=1e20),))
    elif bad == 'dimensions':
        label = replace(label, width=True)
    elif bad == 'text':
        label = replace(label, lines=(replace(label.lines[0], text='a' * 4097),))
    elif bad == 'too-many':
        label = replace(label, lines=label.lines * 129)
    with pytest.raises(c.CompositionError):
        if bad == 'license':
            c.plate_source(
                'host', (model(),), (plates.Material('skin', '#FFFFFF', print=label),), basis='clay', print_font=b'font'
            )
        else:
            source(label, bytearray(b'font') if bad == 'font-type' else None)


def renderer(tmp_path, *, invalid_print=False):
    fixture = plates.write_png(tmp_path / 'fixture.png', np.full((64, 64, 4), 255, np.uint8))
    engine = tmp_path / 'engine'
    engine.write_text(f'''#!{sys.executable}
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[2]).getroot()
font = root.find('assets/font')
if font is not None:
    assert Path(font.get('src')).is_file()
for material in root.findall('materials/material'):
    assert Path(material.get('baseColorMap')).read_bytes().startswith(bytes([137,80,78,71]))
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(
    b'invalid' if font is not None and {invalid_print!r} else Path({str(fixture)!r}).read_bytes())
''')
    engine.chmod(0o700)
    return engine


def test_cold_and_warm_label_bundles_count_all_render_attempts(tmp_path):
    item = source()
    plan = plan_for(item)
    asset = c.prepare_plate(plan, 'host', item)
    engine = renderer(tmp_path)
    with plates.render_session(max_invocations=2) as work:
        first = c.emit_bundle(plan, (asset,), tmp_path / 'bundle', engine=engine, cache=tmp_path / 'cache')
    assert first.work.engine_invocations == work.invocations == 2
    with plates.render_session(max_invocations=0) as work:
        warm = c.compile_bundle(plan, (asset,), engine=engine, cache=tmp_path / 'cache')
    assert warm.digest == first.digest and warm.work.cache_hits == 1 and work.invocations == 0


@pytest.mark.parametrize('failure', ['attempt-limit', 'invalid-print'])
def test_failed_print_or_plate_never_publishes_partial_bundle(tmp_path, failure):
    item = source()
    plan = plan_for(item)
    asset = c.prepare_plate(plan, 'host', item)
    with plates.render_session(max_invocations=1) as work:
        with pytest.raises(c.CompositionError):
            c.emit_bundle(
                plan,
                (asset,),
                tmp_path / 'bundle',
                engine=renderer(tmp_path, invalid_print=failure == 'invalid-print'),
                cache=tmp_path / 'cache',
            )
    assert work.invocations == 1
    assert not (tmp_path / 'bundle').exists() and not list((tmp_path / 'cache').rglob('image.png'))


def test_real_label_survives_uv_mapping_and_is_readable(tmp_path, scene_render):
    item = source()
    plan = plan_for(item)
    asset = c.prepare_plate(plan, 'host', item)
    bundle = c.emit_bundle(plan, (asset,), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    pixels = plates.pixels(tmp_path / 'bundle' / bundle.resources[0].name)
    center = pixels[22:43, 22:43, :3]
    assert (center.max(axis=2) < 100).sum() > 30
    assert (center.min(axis=2) > 150).sum() > 30
    assert bundle.work.engine_invocations == 2


@pytest.mark.parametrize(
    'bad',
    [
        'extra',
        'font-base64',
        'prints-list',
        'lines-list',
        'line-extra',
        'line-text',
        'mutable-font',
        'oversized-font',
        'combined-pixels',
        'text-budget',
    ],
)
def test_print_protocol_rejects_untrusted_payloads(bad):
    from srstudio import _composition_plate_wire as wire

    item = source()
    if bad in ('mutable-font', 'oversized-font', 'combined-pixels', 'text-budget'):
        printed = item.prints[0]
        if bad == 'mutable-font':
            printed = replace(printed, font=bytearray(printed.font))
        elif bad == 'oversized-font':
            printed = replace(printed, font=bytes(8 * 1024**2))
        elif bad == 'text-budget':
            printed = replace(
                printed, recipe=replace(printed.recipe, lines=(plates.Line('A' * 4096, 0, 0, 1, '#000000'),) * 9)
            )
        else:
            printed = replace(printed, recipe=replace(printed.recipe, width=1024, height=2048))
        item = replace(item, prints=(printed,) * (2 if bad == 'combined-pixels' else 1))
        with pytest.raises(c.CompositionError):
            wire.source_encode(item)
        return
    encoded = wire.source_encode(item)
    if bad == 'extra':
        encoded['prints'][0]['unknown'] = 1
    elif bad == 'font-base64':
        encoded['prints'][0]['font'] = '!'
    elif bad == 'prints-list':
        encoded['prints'] = 'not a list'
    elif bad == 'lines-list':
        encoded['prints'][0]['recipe']['lines'] = 'not a list'
    elif bad == 'line-extra':
        encoded['prints'][0]['recipe']['lines'][0]['unknown'] = 1
    else:
        encoded['prints'][0]['recipe']['lines'][0]['text'] = []
    with pytest.raises(c.CompositionError):
        wire.source_decode(encoded)


def test_changed_font_invalidates_cache_and_forged_evidence_is_refused(tmp_path):
    item = source()
    plan = plan_for(item)
    asset = c.prepare_plate(plan, 'host', item)
    engine = renderer(tmp_path)
    first = c.compile_bundle(plan, (asset,), engine=engine, cache=tmp_path / 'cache')
    changed = replace(item, prints=(replace(item.prints[0], font=item.prints[0].font + b'provenance'),))
    new_plan = plan_for(changed)
    new_asset = c.prepare_plate(new_plan, 'host', changed)
    assert new_asset.source_digest != asset.source_digest
    second = c.compile_bundle(new_plan, (new_asset,), engine=engine, cache=tmp_path / 'cache')
    assert first.work.engine_invocations == second.work.engine_invocations == 2
    assert len(list((tmp_path / 'cache').rglob('record.json'))) == 2
    forged = replace(
        asset, resources=tuple(replace(r, data=b'forged') if r.name.endswith('.ttf') else r for r in asset.resources)
    )
    with plates.render_session(max_invocations=0) as work:
        with pytest.raises(c.CompositionError):
            c.compile_bundle(plan, (forged,), engine=engine, cache=tmp_path / 'untouched')
    assert work.invocations == 0 and not (tmp_path / 'untouched').exists()


def test_per_source_attempt_scope_preserves_explicit_plan_process_limits(tmp_path, monkeypatch):
    item = source()
    base = plan_for(item)
    plan = c.preflight(
        replace(base.spec, budget=replace(base.spec.budget, max_memory_bytes=10 * 1024**3)), base.bindings
    )
    asset = c.prepare_plate(plan, 'host', item)
    invoke = plates._invoke_renderer
    observed = []

    def inspect(engine, document, output, limits):
        observed.append((limits.timeout, limits.memory_bytes, limits.file_bytes))
        assert limits.timeout == 120
        assert limits.memory_bytes == 10 * 1024**3
        assert limits.file_bytes == 256 * 1024**2
        invoke(engine, document, output, limits)

    monkeypatch.setattr(plates, '_invoke_renderer', inspect)
    c.compile_bundle(plan, (asset,), engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert len(observed) == 2


def test_print_and_normal_map_keep_their_separate_material_roles(prepare):
    item = source()
    item = replace(
        item,
        textures=(c.PlateTexture('normal', 1, 1, bytes([128, 128, 255, 255])),),
        materials=(replace(item.materials[0], normal_map='normal', normal_scale=0.4),),
    )
    asset = prepare(plan_for(item), 'host', item)
    material = ET.fromstring(asset.xml).find('materials/material')
    assert material.get('baseColorMap').startswith('prints/')
    assert material.get('normalMap').startswith('textures/')
    assert material.get('normalScale') == '0.4'
