"""Actual immutable mesh payloads must match plate declarations before rendering."""

import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from srstudio import clay
from srstudio import composition as c
from support.composition import plate_source as source
from support.composition import prepared_plate_plan as plan_for


def test_preparation_is_deterministic_immutable_and_binds_real_geometry_and_resources(tmp_path, monkeypatch):
    item = source()
    plan = plan_for(item)
    monkeypatch.chdir(tmp_path)
    prepared = c.prepare_plate(plan, 'host', item)
    assert c.prepare_plate(plan, 'host', item) == prepared
    assert prepared.plan_digest == plan.digest
    assert prepared.source_digest == c.plate_source_digest(item)
    assert prepared.binding == plan.bindings[0]
    assert prepared.source == item
    assert prepared.bounds.minimum == pytest.approx((-0.1, -0.1, -0.3))
    assert prepared.bounds.maximum == pytest.approx((0.1, 0.1, -0.1))
    root = ET.fromstring(prepared.xml)
    assert root.find('project').get('seed') == '7'
    assert prepared.nodes == len(list(root.iter()))
    assert prepared.offset == (0, 0)
    for resource in prepared.resources:
        assert resource.name == 'meshes/' + hashlib.sha256(resource.data).hexdigest() + '.obj'
    assert {node.get('src') for node in root.findall('assets/mesh')} == {r.name for r in prepared.resources}
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(FrozenInstanceError):
        prepared.xml = b'changed'


def test_snapshot_is_owned_and_clay_and_canonical_bases_produce_identical_engine_geometry():
    model = clay.Model()
    model.box('skin', (0, 0, 0.2), (0.2, 0.2, 0.2))
    mesh = model.meshes()[0]
    first = c.plate_mesh(mesh, basis='clay')
    canonical = clay.Mesh(mesh.material, mesh.vertices * (1, 1, -1), mesh.normals * (1, 1, -1), mesh.triangles[:, ::-1])
    second = c.plate_mesh(canonical, basis='canonical')
    mesh.vertices[:] = 99
    one = c.PlateSource('host', (first,), (c.PlateMaterial('skin', '#C88762'),))
    two = replace(one, meshes=(second,))
    a = c.prepare_plate(plan_for(one), 'host', one)
    b = c.prepare_plate(plan_for(two), 'host', two)
    assert a.xml == b.xml and a.resources == b.resources


@pytest.mark.parametrize(
    'bad',
    [
        'nan',
        'short',
        'index',
        'normal',
        'material',
        'bounds',
        'key',
        'width',
        'samples',
        'bounces',
        'nodes',
        'memory',
        'duration',
        'proxy',
    ],
)
def test_invalid_payload_or_underdeclared_work_is_refused_before_cache_mutation(tmp_path, monkeypatch, bad):
    item = source()
    mesh = item.meshes[0]
    if bad == 'nan':
        item = replace(item, meshes=(replace(mesh, vertices=struct.pack('<d', float('nan')) + mesh.vertices[8:]),))
    elif bad == 'short':
        item = replace(item, meshes=(replace(mesh, vertices=mesh.vertices[:-1]),))
    elif bad == 'index':
        item = replace(item, meshes=(replace(mesh, triangles=struct.pack('<q', -1) + mesh.triangles[8:]),))
    elif bad == 'normal':
        item = replace(item, meshes=(replace(mesh, normals=bytes(len(mesh.normals))),))
    elif bad == 'material':
        item = replace(item, materials=(c.PlateMaterial('missing', '#FFFFFF'),))
    plan = plan_for(item)
    binding = plan.bindings[0]
    if bad == 'bounds':
        binding = replace(binding, bounds=c.Bounds((0, 0, 0), (0.01, 0.01, 0.01)))
    elif bad in ('key', 'width', 'samples', 'bounces'):
        change = {'key': 'b' * 64} if bad == 'key' else {bad: 2}
        binding = replace(binding, plates=(replace(binding.plates[0], **change),))
    elif bad == 'nodes':
        binding = replace(binding, nodes=1)
    elif bad == 'memory':
        binding = replace(binding, memory_bytes=1)
    elif bad == 'duration':
        binding = replace(binding, duration=1)
    elif bad == 'proxy':
        binding = replace(binding, backend='proxy')
    plan = c.preflight(plan.spec, (binding,))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_plate(plan, 'host', item)
    assert caught.value.to_dict()['code'].startswith('composition.')
    assert list(tmp_path.iterdir()) == []


def test_two_different_placements_cannot_share_one_cold_render_budget():
    item = source()
    base = plan_for(item)
    second = replace(base.spec.layers[0], id='second', transform=c.Transform((0.1, 0, 0)))
    plan = c.preflight(replace(base.spec, layers=base.spec.layers + (second,)), base.bindings)
    assert plan.cost.unique_plates == plan.cost.engine_invocations == 2
    assert c.prepare_plate(plan, 'host', item).digest != c.prepare_plate(plan, 'second', item).digest
    with pytest.raises(c.CompositionError):
        c.preflight(replace(plan.spec, budget=replace(plan.spec.budget, max_engine_invocations=1)), plan.bindings)


@pytest.mark.parametrize('color', ['red', '#FFF', '#12345678'])
def test_material_contract_refuses_unimplemented_color_forms(color):
    item = source()
    item = replace(item, materials=(c.PlateMaterial('skin', color),))
    with pytest.raises(c.CompositionError):
        c.prepare_plate(plan_for(item), 'host', item)


def test_preparation_uses_parent_owned_deadline(monkeypatch):
    import sys

    from srstudio import _composition_runtime as runtime

    item = source()
    plan = plan_for(item)
    plan = c.preflight(replace(plan.spec, budget=replace(plan.spec.budget, timeout=0.1)), plan.bindings)
    monkeypatch.setattr(runtime, '_worker_command', lambda: (sys.executable, '-c', 'import time; time.sleep(60)'))
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_plate(plan, 'host', item)
    assert caught.value.to_dict()['code'] == 'composition.budget'


def test_preparation_memory_cap_reaches_worker_without_changing_parent(monkeypatch):
    import resource
    import sys

    from srstudio import _composition_runtime as runtime

    cap = 128 * 1024**2
    before = resource.getrlimit(resource.RLIMIT_AS)
    item = source()
    plan = plan_for(item)
    plan = c.preflight(replace(plan.spec, budget=replace(plan.spec.budget, max_memory_bytes=cap)), plan.bindings)
    code = '''import json, os, resource
print(json.dumps(resource.getrlimit(resource.RLIMIT_AS)), flush=True)
try:
    bytearray(256 * 1024**2)
except MemoryError:
    os.write(2, b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\\n')
    os._exit(86)
raise AssertionError('escaped memory limit')
'''
    monkeypatch.setattr(runtime, '_worker_command', lambda: (sys.executable, '-c', code))
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_plate(plan, 'host', item)
    assert caught.value.to_dict()['code'] == 'composition.budget'
    assert json.loads(caught.value.__cause__.stdout) == [cap, cap]
    assert resource.getrlimit(resource.RLIMIT_AS) == before


@pytest.fixture(scope='module')
def verified_payload():
    item = source()
    plan = plan_for(item)
    return plan, item, c.prepare_plate(plan, 'host', item)


@pytest.mark.parametrize(
    'bad',
    ['extra', 'path', 'blob', 'bounds', 'offset', 'offset-bool', 'width-bool', 'nodes', 'digest', 'duplicate', 'empty'],
)
def test_malformed_worker_payloads_are_refused(verified_payload, monkeypatch, bad):
    from srstudio import _composition_plate_runtime as runtime
    from srstudio import _composition_plate_wire as payload
    from srstudio import _composition_wire as wire

    plan, item, asset = verified_payload
    data = json.loads(json.dumps(payload.prepared_encode(asset)))
    if bad == 'extra':
        data['extra'] = 1
    elif bad == 'path':
        data['resources'][0]['name'] = '../escape.obj'
    elif bad == 'blob':
        data['resources'][0]['data'] = 'not base64!'
    elif bad == 'bounds':
        data['bounds']['minimum'][0] = -100
    elif bad == 'offset':
        data['offset'][0] = 100
    elif bad == 'offset-bool':
        data['offset'] = [False, False]
    elif bad == 'width-bool':
        data['width'] = True
    elif bad == 'nodes':
        data['nodes'] = 0
    elif bad == 'digest':
        data['digest'] = 'b' * 64
    elif bad == 'duplicate':
        data['resources'] *= 2
    else:
        data['resources'] = []
    monkeypatch.setattr(runtime, '_call', lambda *args: {'schema': wire.SCHEMA, 'status': 'ok', 'prepared': data})
    with pytest.raises(c.CompositionError):
        c.prepare_plate(plan, 'host', item)


@pytest.mark.parametrize('bad', ['mesh-type', 'basis', 'uv-shape', 'shape', 'dtype', 'empty', 'unsigned', 'material'])
def test_snapshot_refuses_unsupported_or_lossy_input(bad):
    model = clay.Model()
    model.box('skin', (0, 0, 0), (1, 1, 1))
    mesh = model.meshes()[0]
    if bad == 'mesh-type':
        mesh = None
    elif bad == 'uv-shape':
        mesh = replace(mesh, uvs=np.zeros((len(mesh.vertices), 3)))
    elif bad == 'shape':
        mesh = replace(mesh, vertices=np.zeros((5, 2)))
    elif bad == 'dtype':
        mesh = replace(mesh, vertices=mesh.vertices.astype(object))
    elif bad == 'empty':
        mesh = replace(mesh, vertices=np.zeros((0, 3)))
    elif bad == 'unsigned':
        mesh = replace(mesh, triangles=np.full((1, 3), 2**63, dtype=np.uint64))
    elif bad == 'material':
        mesh = replace(mesh, material=None)
    with pytest.raises(c.CompositionError):
        c.plate_mesh(mesh, basis='surprise' if bad == 'basis' else 'clay')


@pytest.mark.parametrize('bad', ['type', 'meshes', 'materials', 'basis', 'buffer', 'units', 'wrong-material'])
def test_source_protocol_refuses_untyped_or_mutable_records(bad):
    item = source()
    if bad == 'type':
        item = None
    elif bad == 'meshes':
        item = replace(item, meshes=list(item.meshes))
    elif bad == 'materials':
        item = replace(item, materials=())
    elif bad == 'basis':
        item = replace(item, meshes=(replace(item.meshes[0], basis='unknown'),))
    elif bad == 'buffer':
        item = replace(item, meshes=(replace(item.meshes[0], vertices=bytearray(item.meshes[0].vertices)),))
    elif bad == 'units':
        item = replace(item, meters_per_unit=True)
    else:
        item = replace(item, materials=('skin',))
    with pytest.raises(c.CompositionError):
        c.plate_source_digest(item)


def test_worker_source_schema_is_closed(verified_payload):
    from dataclasses import asdict

    from srstudio import _composition_plate_wire as payload
    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker

    plan, item, _ = verified_payload
    request = {
        'schema': wire.SCHEMA,
        'operation': 'prepare-plate',
        'plan': asdict(plan),
        'layer': 'host',
        'source': payload.source_encode(item),
    }
    for field in ('top', 'mesh', 'material'):
        value = json.loads(json.dumps(request))
        target = {
            'top': value['source'],
            'mesh': value['source']['meshes'][0],
            'material': value['source']['materials'][0],
        }[field]
        target['unrecognized'] = 1
        with pytest.raises(c.CompositionError):
            worker.dispatch(wire.dumps(value))


def test_real_prepared_scene_renders_with_only_its_declared_resources(tmp_path, scene_render, record_property):
    from srstudio import plates

    item = source()
    prepared = c.prepare_plate(plan_for(item), 'host', item)
    document = tmp_path / 'plate.scene.xml'
    document.write_bytes(prepared.xml)
    for resource in prepared.resources:
        path = tmp_path / resource.name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(resource.data)
    output = tmp_path / 'plate.png'
    with plates.render_session(max_invocations=1, timeout=120) as stats:
        plates._engine_render(scene_render, document, output)
    assert stats.completed == 1
    pixels = plates.pixels(output)
    assert pixels.shape == (64, 64, 4)
    assert np.count_nonzero(pixels[..., 3]) > 100
    record_property('prepared_digest', prepared.digest)
    record_property('image_sha256', hashlib.sha256(output.read_bytes()).hexdigest())
    record_property('covered_pixels', int(np.count_nonzero(pixels[..., 3])))


@pytest.mark.parametrize('bad', ['repeat-index', 'duplicate-material', 'short-normals', 'job-memory', 'wrong-source'])
def test_remaining_geometry_and_identity_failures_are_explicit(bad):
    item = source()
    mesh = item.meshes[0]
    if bad == 'repeat-index':
        item = replace(item, meshes=(replace(mesh, triangles=struct.pack('<qqq', 0, 0, 1)),))
    elif bad == 'duplicate-material':
        item = replace(item, materials=item.materials * 2)
    elif bad == 'short-normals':
        item = replace(item, meshes=(replace(mesh, normals=mesh.normals[:-24]),))
    plan = plan_for(item)
    if bad == 'job-memory':
        binding = plan.bindings[0]
        plan = c.preflight(plan.spec, (replace(binding, plates=(replace(binding.plates[0], memory_bytes=1),)),))
    elif bad == 'wrong-source':
        item = replace(item, id='other')
    with pytest.raises(c.CompositionError):
        c.prepare_plate(plan, 'host', item)


def test_mesh_payload_sizes_are_checked_before_worker_launch(monkeypatch):
    from srstudio import _composition_plate_wire as payload

    item = source()
    monkeypatch.setattr(payload, 'MAX_BYTES', len(item.meshes[0].vertices))
    with pytest.raises(c.CompositionError):
        payload.validate_source(item)
    with pytest.raises(c.CompositionError):
        payload.source_decode({'id': 'host', 'meshes': 'wrong', 'materials': [], 'meters_per_unit': None})


def test_prepared_error_preserves_underlying_plate_error(monkeypatch):
    from srstudio import _composition_plate as implementation
    from srstudio import plates

    item = source()

    def fail(*args):
        raise plates.PlateError('refused by backend')

    monkeypatch.setattr(plates, 'document', fail)
    with pytest.raises(c.CompositionError) as caught:
        implementation.prepare_plate(plan_for(item), 'host', item)
    assert isinstance(caught.value.__cause__, plates.PlateError)
