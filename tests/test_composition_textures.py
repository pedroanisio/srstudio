"""Textured plate preparation preserves authored pixels, UVs and closed resource identities."""

import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import clay, plates
from srstudio import composition as c
from srstudio._composition_plate_wire import identity
from support.composition import mesh as model
from support.composition import plate_source as plain_source
from support.composition import prepared_plate_plan


def picture():
    return plates.Texture(
        np.array([[[255, 0, 0, 255], [0, 255, 0, 255]], [[0, 0, 255, 255], [255, 255, 0, 255]]], np.uint8)
    )


def textured():
    material = plates.Material(
        'skin',
        '#FFFFFF',
        color_map=picture(),
        normal_map=plates.Texture(np.full((2, 2, 4), (128, 128, 255, 255), np.uint8)),
        normal_scale=0.55,
        sheen='#FFE9D2',
        subsurface=0.08,
    )
    return c.plate_source('host', (model(),), (material,), basis='clay')


def test_existing_untextured_identities_and_resources_do_not_change():
    golden = json.loads((Path(__file__).parent / 'data/composition-untextured-baseline.json').read_text())
    item = plain_source()
    asset = c.prepare_plate(prepared_plate_plan(item), 'host', item)
    assert c.plate_source_digest(item) == golden['source_digest']
    assert asset.digest == identity(asset)
    # The plan digest folds in the live Toon style revision, which moves with every new Toon part; the plate's own
    # identity is pinned against the plan digest the baseline was taken with.
    assert identity(replace(asset, plan_digest=golden['plan_digest'])) == golden['prepared_digest']
    assert hashlib.sha256(asset.xml).hexdigest() == golden['xml_sha256']
    assert [[r.name, hashlib.sha256(r.data).hexdigest()] for r in asset.resources] == golden['resources']


def test_snapshots_own_uvs_and_rgba_without_mutating_host_arrays():
    mesh, texture = model(), picture()
    frozen_mesh = c.plate_mesh(mesh, basis='clay')
    frozen_texture = c.plate_texture('paint', texture)
    uv, pixels = mesh.uvs.copy(), texture.pixels.copy()
    mesh.uvs[:] = 99
    texture.pixels[:] = 0
    assert np.array_equal(np.frombuffer(frozen_mesh.uvs, '<f8').reshape(-1, 2), uv)
    assert frozen_texture.pixels == pixels.tobytes()
    assert (frozen_texture.width, frozen_texture.height) == (2, 2)


def test_source_adapter_preserves_materials_and_deduplicates_shared_pixels():
    item = textured()
    assert len(item.textures) == 2
    material = item.materials[0]
    assert material.color_map and material.normal_map and material.normal_scale == 0.55
    assert material.sheen == '#FFE9D2' and material.subsurface == 0.08
    tint = picture()
    shared = c.plate_source(
        'host',
        (model(),),
        (
            plates.Material('skin', '#FFFFFF', color_map=tint),
            plates.Material('other', '#FFFFFF', color_map=plates.Texture(tint.pixels.copy())),
        ),
        basis='clay',
    )
    assert len(shared.textures) == 1
    assert shared.materials[0].color_map == shared.materials[1].color_map


def test_preparation_emits_uvs_and_complete_content_addressed_texture_resources(tmp_path, monkeypatch):
    item = textured()
    plan = prepared_plate_plan(item)
    monkeypatch.chdir(tmp_path)
    asset = c.prepare_plate(plan, 'host', item)
    root = ET.fromstring(asset.xml)
    material = root.find('materials/material')
    assert material.get('normalScale') == '0.55'
    assert material.get('sheenColor') == '#FFE9D2'
    assert material.get('subsurface') == '0.08'
    resources = {r.name: r.data for r in asset.resources}
    assert {material.get('baseColorMap'), material.get('normalMap')} == {n for n in resources if n.endswith('.png')}
    for name, content in resources.items():
        prefix, suffix = ('textures/', '.png') if name.endswith('.png') else ('meshes/', '.obj')
        assert name == prefix + hashlib.sha256(content).hexdigest() + suffix
    obj = next(data.decode() for name, data in resources.items() if name.endswith('.obj'))
    assert sum(line.startswith('vt ') for line in obj.splitlines()) == 4
    assert 'f 1/1/1' in obj
    assert list(tmp_path.iterdir()) == []


def test_equal_pixel_bytes_in_different_shapes_do_not_alias():
    pixels = picture().pixels
    a = c.plate_texture('a', plates.Texture(pixels))
    b = c.plate_texture('b', plates.Texture(pixels.reshape(1, 4, 4)))
    mesh = c.plate_mesh(model(), basis='clay')
    item = c.PlateSource(
        'host',
        (mesh,),
        (c.PlateMaterial('skin', '#FFFFFF', color_map='a'), c.PlateMaterial('second', '#FFFFFF', color_map='b')),
        textures=(a, b),
    )
    asset = c.prepare_plate(prepared_plate_plan(item), 'host', item)
    images = [r for r in asset.resources if r.name.endswith('.png')]
    assert len(images) == 2 and images[0].name != images[1].name
    assert {struct.unpack('>II', r.data[16:24]) for r in images} == {(2, 2), (4, 1)}
    assert c.plate_source_digest(item) != c.plate_source_digest(
        replace(item, textures=(a, replace(b, width=2, height=2)))
    )


@pytest.mark.parametrize(
    'bad',
    [
        'uv-short',
        'uv-nan',
        'uv-large',
        'missing-uv',
        'missing-map',
        'duplicate',
        'unused',
        'color',
        'normal-scale',
        'subsurface',
    ],
)
def test_invalid_texture_semantics_fail_without_files(tmp_path, monkeypatch, bad):
    item = textured()
    mesh, material = item.meshes[0], item.materials[0]
    with pytest.raises(c.CompositionError):
        if bad == 'uv-short':
            item = replace(item, meshes=(replace(mesh, uvs=mesh.uvs[:-1]),))
        elif bad == 'uv-nan':
            item = replace(item, meshes=(replace(mesh, uvs=struct.pack('<d', float('nan')) + mesh.uvs[8:]),))
        elif bad == 'uv-large':
            item = replace(item, meshes=(replace(mesh, uvs=struct.pack('<d', 2**54) + mesh.uvs[8:]),))
        elif bad == 'missing-uv':
            item = replace(item, meshes=(replace(mesh, uvs=None),))
        elif bad == 'missing-map':
            item = replace(item, materials=(replace(material, color_map='absent'),))
        elif bad == 'duplicate':
            item = replace(item, textures=item.textures * 2)
        elif bad == 'unused':
            item = replace(item, textures=item.textures + (replace(item.textures[0], id='unused'),))
        elif bad == 'color':
            item = replace(item, materials=(replace(material, sheen='warm'),))
        elif bad == 'normal-scale':
            item = replace(item, materials=(replace(material, normal_scale=float('nan')),))
        else:
            item = replace(item, materials=(replace(material, subsurface=2),))
        plan = prepared_plate_plan(item)
        monkeypatch.chdir(tmp_path)
        c.prepare_plate(plan, 'host', item)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('bad', ['type', 'dtype', 'shape', 'channels', 'empty', 'oversized', 'id'])
def test_texture_snapshot_refuses_lossy_or_unbounded_inputs(bad):
    texture = picture()
    if bad == 'type':
        texture = None
    elif bad == 'dtype':
        texture = plates.Texture(texture.pixels.astype(float))
    elif bad == 'shape':
        texture = plates.Texture(np.zeros((4,), np.uint8))
    elif bad == 'channels':
        texture = plates.Texture(np.zeros((2, 2, 3), np.uint8))
    elif bad == 'empty':
        texture = plates.Texture(np.zeros((0, 2, 4), np.uint8))
    elif bad == 'oversized':
        texture = plates.Texture(np.broadcast_to(np.zeros((1, 1, 4), np.uint8), (4096, 4096, 4)))
    with pytest.raises(c.CompositionError):
        c.plate_texture('../escape' if bad == 'id' else 'paint', texture)


@pytest.mark.parametrize('bad', ['type', 'mutable', 'dimensions', 'count', 'extra', 'base64'])
def test_texture_wire_rejects_untyped_mutable_or_unknown_data(bad):
    from srstudio import _composition_plate_wire as wire

    item = textured()
    if bad in ('extra', 'base64'):
        encoded = wire.source_encode(item)
        if bad == 'extra':
            encoded['textures'][0]['unknown'] = 1
        else:
            encoded['textures'][0]['pixels'] = 'not-base64'
        with pytest.raises(c.CompositionError):
            wire.source_decode(encoded)
    else:
        texture = item.textures[0]
        if bad == 'type':
            item = replace(item, textures=['pixels'])
        elif bad == 'mutable':
            item = replace(item, textures=(replace(texture, pixels=bytearray(texture.pixels)),))
        elif bad == 'dimensions':
            item = replace(item, textures=(replace(texture, width=True),))
        else:
            item = replace(item, textures=(texture,) * 129)
        with pytest.raises(c.CompositionError):
            wire.source_encode(item)


def test_print_material_is_refused_instead_of_silently_dropping_the_label():
    label = plates.Print('#FFFFFF', 16, 16, ())
    with pytest.raises(c.CompositionError):
        c.plate_source('host', (model(),), (plates.Material('skin', '#FFFFFF', print=label),), basis='clay')


def test_real_renderer_preserves_texture_orientation_and_reuses_the_complete_bundle(tmp_path, scene_render):
    item = textured()
    # A neutral unlit-looking material makes each quadrant's channel dominance
    # legible without treating a path tracer's exact shade as a color guarantee.
    item = replace(item, materials=(replace(item.materials[0], sheen='', subsurface=0),))
    plan = prepared_plate_plan(item)
    plan = c.preflight(replace(plan.spec, budget=replace(plan.spec.budget, timeout=120)), plan.bindings)
    asset = c.prepare_plate(plan, 'host', item)
    first = c.emit_bundle(plan, (asset,), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    png = plates.pixels(tmp_path / 'bundle' / first.resources[0].name)
    for (y, x), channel in [((20, 20), 0), ((20, 44), 1), ((44, 20), 2)]:
        assert int(png[y, x, channel]) > max(int(png[y, x, i]) for i in range(3) if i != channel) + 40
        assert png[y, x, 3] == 255
    with plates.render_session(max_invocations=0) as work:
        warm = c.compile_bundle(plan, (asset,), engine=scene_render, cache=tmp_path / 'cache')
    assert work.invocations == 0 and warm.work.cache_hits == 1 and warm.digest == first.digest


def test_uvs_and_pixels_survive_the_clay_to_canonical_basis_conversion():
    a = textured()
    raw = model()
    canonical = clay.Mesh(
        raw.material, raw.vertices * (1, 1, -1), raw.normals * (1, 1, -1), raw.triangles[:, ::-1], raw.uvs
    )
    b = replace(a, meshes=(c.plate_mesh(canonical, basis='canonical'),))
    first = c.prepare_plate(prepared_plate_plan(a), 'host', a)
    second = c.prepare_plate(prepared_plate_plan(b), 'host', b)
    assert first.xml == second.xml and first.resources == second.resources


def test_authored_rafa_knit_material_reaches_the_worker_without_losing_its_map():
    from srstudio import rafa

    material = rafa.MATERIALS['teal']
    item = c.plate_source('host', (replace(model(), material='teal'),), (material,), basis='clay')
    base = prepared_plate_plan(item)
    binding = replace(
        base.bindings[0],
        memory_bytes=16 * 1024**2,
        plates=(replace(base.bindings[0].plates[0], memory_bytes=16 * 1024**2),),
    )
    plan = c.preflight(base.spec, (binding,))
    asset = c.prepare_plate(plan, 'host', item)
    assert item.textures[0].pixels == material.normal_map.pixels.tobytes()
    assert item.materials[0].sheen == material.sheen
    node = ET.fromstring(asset.xml).find('materials/material')
    assert node.get('normalMap') in {r.name for r in asset.resources}
    assert float(node.get('normalScale')) == material.normal_scale


@pytest.mark.parametrize(
    'bad', ['meshes', 'materials', 'material-type', 'texture-type', 'aggregate-mesh', 'aggregate-texture']
)
def test_source_snapshot_bounds_work_before_retaining_all_inputs(bad):
    meshes, materials = (model(),), (plates.Material('skin', '#FFFFFF'),)
    if bad == 'meshes':
        meshes = list(meshes)
    elif bad == 'materials':
        materials = ()
    elif bad == 'material-type':
        materials = (None,)
    elif bad == 'texture-type':
        materials = (replace(materials[0], color_map='not a texture'),)
    elif bad == 'aggregate-mesh':
        large = clay.Mesh('skin', np.zeros((100000, 3)), np.zeros((100000, 3)), np.zeros((1, 3), int))
        meshes = (large, large)
    else:
        materials = (replace(materials[0], color_map=plates.Texture(np.zeros((1024, 2048, 4), np.uint8))),)
    with pytest.raises(c.CompositionError):
        c.plate_source('host', meshes, materials, basis='clay')


@pytest.mark.parametrize('boundary', ['source', 'wire'])
def test_combined_raw_texture_and_geometry_bytes_are_bounded(boundary):
    from srstudio import _composition_plate_wire as wire

    item = plain_source()
    large = c.PlateTexture('large', 2048, 1024, bytes(8 * 1024**2))
    item = replace(item, textures=(large,))
    with pytest.raises(c.CompositionError):
        if boundary == 'source':
            wire.validate_source(item)
        else:
            encoded = wire.source_encode(plain_source())
            import base64

            encoded['textures'] = [
                {
                    'id': 'large',
                    'width': large.width,
                    'height': large.height,
                    'pixels': base64.b64encode(large.pixels).decode(),
                }
            ]
            wire.source_decode(encoded)


def test_repeating_uv_coordinates_are_not_clamped_to_one_tile():
    raw = replace(model(), uvs=model().uvs * 4 - 2)
    item = textured()
    item = replace(item, meshes=(c.plate_mesh(raw, basis='clay'),))
    asset = c.prepare_plate(prepared_plate_plan(item), 'host', item)
    obj = next(r.data.decode() for r in asset.resources if r.name.endswith('.obj'))
    rows = [line for line in obj.splitlines() if line.startswith('vt ')]
    assert rows == [
        'vt -2.0000000 2.0000000',
        'vt 2.0000000 2.0000000',
        'vt 2.0000000 -2.0000000',
        'vt -2.0000000 -2.0000000',
    ]


def fake_renderer(tmp_path):
    import sys

    fixture = plates.write_png(tmp_path / 'fixture.png', np.full((64, 64, 4), 255, np.uint8))
    engine = tmp_path / 'engine'
    engine.write_text(f'''#!{sys.executable}
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[2]).getroot()
for material in root.findall('materials/material'):
    for name in ('baseColorMap', 'normalMap'):
        if material.get(name):
            assert Path(material.get(name)).read_bytes().startswith(bytes([137,80,78,71]))
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(Path({str(fixture)!r}).read_bytes())
''')
    engine.chmod(0o700)
    return engine


def test_texture_change_invalidates_cache_and_forged_resources_never_reach_renderer(tmp_path):
    item = textured()
    engine = fake_renderer(tmp_path)
    plan = prepared_plate_plan(item)
    asset = c.prepare_plate(plan, 'host', item)
    with plates.render_session(max_invocations=2) as work:
        first = c.compile_bundle(plan, (asset,), engine=engine, cache=tmp_path / 'cache')
        texture = item.textures[0]
        changed = replace(texture, pixels=bytes([0, 0, 255, 255]) * (texture.width * texture.height))
        updated = replace(item, textures=(changed, *item.textures[1:]))
        second_plan = prepared_plate_plan(updated)
        second_asset = c.prepare_plate(second_plan, 'host', updated)
        second = c.compile_bundle(second_plan, (second_asset,), engine=engine, cache=tmp_path / 'cache')
        assert work.invocations == 2 and first.work.new_plates == second.work.new_plates == 1
    assert len(list((tmp_path / 'cache').rglob('record.json'))) == 2
    forged = replace(
        asset, resources=tuple(replace(r, data=b'changed') if r.name.endswith('.png') else r for r in asset.resources)
    )
    with plates.render_session(max_invocations=0) as work:
        with pytest.raises(c.CompositionError):
            c.compile_bundle(plan, (forged,), engine=engine, cache=tmp_path / 'untouched')
    assert work.invocations == 0 and not (tmp_path / 'untouched').exists()


def test_more_than_128_closed_mesh_and_texture_resources_can_be_published(tmp_path):
    textures = tuple(c.PlateTexture(f't{i}', 1, 1, bytes([i, 64, 255, 255])) for i in range(128))
    materials = tuple(
        c.PlateMaterial(f'm{i}', '#FFFFFF', color_map=f't{i * 2}', normal_map=f't{i * 2 + 1}') for i in range(64)
    )
    item = c.PlateSource(
        'host', (c.plate_mesh(replace(model(), material='m0'), basis='clay'),), materials, textures=textures
    )
    base = prepared_plate_plan(item)
    plan = c.preflight(base.spec, (replace(base.bindings[0], nodes=512),))
    asset = c.prepare_plate(plan, 'host', item)
    assert len(asset.resources) == 129
    bundle = c.emit_bundle(
        plan, (asset,), tmp_path / 'bundle', engine=fake_renderer(tmp_path), cache=tmp_path / 'cache'
    )
    assert bundle.work.new_plates == 1 and (tmp_path / 'bundle' / 'scene.xml').read_bytes() == bundle.xml
