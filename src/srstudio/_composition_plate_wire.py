"""Closed bounded plate payloads and response identities; no executable objects in IPC."""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import asdict, replace

from . import _composition_wire as wire
from . import composition as c
from ._composition_preflight import _digest, _graph, _id
from ._composition_texture import MAX_TEXTURES
from ._composition_texture import validate as validate_texture

MAX_BYTES = 8 * 1024**2
MAX_MESHES = 128
MAX_RESOURCES = MAX_MESHES + MAX_TEXTURES


def _bytes(value: object) -> bytes:
    if type(value) is not bytes or not 1 <= len(value) <= MAX_BYTES:
        raise wire.fail(None, 'immutable nonempty payload bytes within eight MiB')
    return value


def _encode(value: bytes) -> str:
    return base64.b64encode(_bytes(value)).decode('ascii')


def _decode(value: object) -> bytes:
    if type(value) is not str or len(value) > 4 * ((MAX_BYTES + 2) // 3):
        raise wire.fail(None, 'bounded base64 payload bytes')
    try:
        return _bytes(base64.b64decode(value, validate=True))
    except (ValueError, binascii.Error) as error:
        raise wire.fail(None, 'valid nonempty base64 payload bytes') from error


def validate_source(source: c.PlateSource) -> int:
    if type(source) is not c.PlateSource or type(source.id) is not str:
        raise wire.fail(None, 'a PlateSource with an identifier')
    _id(source.id, 'source.id')
    if any(
        type(items) is not tuple or not 1 <= len(items) <= MAX_MESHES for items in (source.meshes, source.materials)
    ):
        raise wire.fail(None, '1..128 immutable meshes and materials')
    if source.meters_per_unit is not None and (
        type(source.meters_per_unit) not in (int, float) or not 1e-6 <= source.meters_per_unit <= 1e6
    ):
        raise wire.fail(None, 'an optional physical scale in 1e-6..1e6')
    total = 0
    for mesh in source.meshes:
        if (
            type(mesh) is not c.PlateMesh
            or type(mesh.material) is not str
            or type(mesh.basis) is not str
            or mesh.basis not in ('canonical', 'clay')
        ):
            raise wire.fail(None, 'PlateMesh records with an explicit source basis')
        _id(mesh.material, 'mesh.material')
        total += sum(len(_bytes(buf)) for buf in (mesh.vertices, mesh.normals, mesh.triangles))
        if mesh.uvs is not None:
            total += len(_bytes(mesh.uvs))
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of total mesh buffers')
    for material in source.materials:
        if type(material) is not c.PlateMaterial:
            raise wire.fail(None, 'PlateMaterial records')
        _graph(material, [0])
    if type(source.textures) is not tuple or len(source.textures) > MAX_TEXTURES:
        raise wire.fail(None, 'at most 128 immutable texture records')
    for texture in source.textures:
        total += validate_texture(texture)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of combined mesh and texture bytes')
    return total


def source_digest(source: c.PlateSource) -> str:
    validate_source(source)
    additions = {'color_map': '', 'normal_map': '', 'normal_scale': 1.0, 'sheen': '', 'subsurface': 0.0}
    legacy = (
        not source.textures
        and all(m.uvs is None for m in source.meshes)
        and all(getattr(m, field) == default for m in source.materials for field, default in additions.items())
    )
    return _digest(
        {
            'schema': 'srstudio.plate-source/1.0.0' if legacy else 'srstudio.plate-source/1.1.0',
            'meshes': [
                {
                    'material': m.material,
                    'basis': m.basis,
                    **{k: hashlib.sha256(getattr(m, k)).hexdigest() for k in ('vertices', 'normals', 'triangles')},
                    **({} if legacy else {'uvs': hashlib.sha256(m.uvs).hexdigest() if m.uvs is not None else None}),
                }
                for m in source.meshes
            ],
            'materials': [
                {k: v for k, v in asdict(m).items() if not legacy or k not in additions} for m in source.materials
            ],
            'meters_per_unit': source.meters_per_unit,
            **(
                {}
                if legacy
                else {
                    'textures': [
                        {
                            'id': t.id,
                            'width': t.width,
                            'height': t.height,
                            'pixels': hashlib.sha256(t.pixels).hexdigest(),
                        }
                        for t in source.textures
                    ]
                }
            ),
        }
    )


def source_encode(source: c.PlateSource) -> dict:
    validate_source(source)
    return {
        'id': source.id,
        'meters_per_unit': source.meters_per_unit,
        'materials': [asdict(m) for m in source.materials],
        'textures': [
            {'id': t.id, 'width': t.width, 'height': t.height, 'pixels': _encode(t.pixels)} for t in source.textures
        ],
        'meshes': [
            {
                'material': m.material,
                'basis': m.basis,
                **{k: _encode(getattr(m, k)) for k in ('vertices', 'normals', 'triangles')},
                'uvs': _encode(m.uvs) if m.uvs is not None else None,
            }
            for m in source.meshes
        ],
    }


def source_decode(value: object) -> c.PlateSource:
    data = wire.fields(value, {'id', 'meters_per_unit', 'materials', 'meshes', 'textures'})
    if any(type(data[k]) is not list or not 1 <= len(data[k]) <= MAX_MESHES for k in ('meshes', 'materials')):
        raise wire.fail(None, 'bounded lists of meshes and materials')
    meshes = []
    total = 0
    for value in data['meshes']:
        m = wire.fields(value, {'material', 'basis', 'vertices', 'normals', 'triangles', 'uvs'})
        buffers = [_decode(m[k]) for k in ('vertices', 'normals', 'triangles')]
        uvs = _decode(m['uvs']) if m['uvs'] is not None else None
        total += sum(map(len, buffers))
        total += len(uvs) if uvs is not None else 0
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of total mesh buffers')
        meshes.append(c.PlateMesh(m['material'], buffers[0], buffers[1], buffers[2], m['basis'], uvs))
    if type(data['textures']) is not list or len(data['textures']) > MAX_TEXTURES:
        raise wire.fail(None, 'a bounded texture list')
    textures = []
    for value in data['textures']:
        t = wire.fields(value, {'id', 'width', 'height', 'pixels'})
        texture = c.PlateTexture(t['id'], t['width'], t['height'], _decode(t['pixels']))
        total += validate_texture(texture)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of combined mesh and texture bytes')
        textures.append(texture)
    source = c.PlateSource(
        data['id'],
        tuple(meshes),
        tuple(wire.record(c.PlateMaterial, m) for m in data['materials']),
        data['meters_per_unit'],
        tuple(textures),
    )
    validate_source(source)
    return source


def identity(asset: c.PreparedPlate) -> str:
    return _digest(
        {
            'plan': asset.plan_digest,
            'source': asset.source_digest,
            'layer': asset.layer,
            'xml': hashlib.sha256(asset.xml).hexdigest(),
            'resources': [(r.name, hashlib.sha256(r.data).hexdigest()) for r in asset.resources],
            'bounds': asdict(asset.bounds),
            'nodes': asset.nodes,
            'size': [asset.width, asset.height],
            'offset': asset.offset,
        }
    )


def prepared_encode(asset: c.PreparedPlate) -> dict:
    return {
        'xml': _encode(asset.xml),
        'resources': [{'name': r.name, 'data': _encode(r.data)} for r in asset.resources],
        'bounds': asdict(asset.bounds),
        'nodes': asset.nodes,
        'width': asset.width,
        'height': asset.height,
        'offset': asset.offset,
        'digest': asset.digest,
    }


def prepared_decode(value: object, plan: c.ValidatedScenePlan, layer: str, source: c.PlateSource) -> c.PreparedPlate:
    data = wire.fields(value, {'xml', 'resources', 'bounds', 'nodes', 'width', 'height', 'offset', 'digest'})
    binding = next(b for b in plan.bindings if b.id == source.id)
    if type(data['resources']) is not list or not 1 <= len(data['resources']) <= MAX_RESOURCES:
        raise wire.fail(None, 'a bounded resource list')
    xml = _decode(data['xml'])
    resources = []
    names = set()
    total = len(xml)
    for entry in data['resources']:
        r = wire.fields(entry, {'name', 'data'})
        content = _decode(r['data'])
        digest = hashlib.sha256(content).hexdigest()
        expected = r['name']
        if (
            type(expected) is not str
            or expected not in ('meshes/' + digest + '.obj', 'textures/' + digest + '.png')
            or expected in names
        ):
            raise wire.fail(None, 'unique content-addressed mesh or texture paths')
        total += len(content)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of prepared resources')
        names.add(expected)
        resources.append(c.PlateResource(expected, content))
    view = c.plate_view(plan, layer, meters_per_unit=source.meters_per_unit)
    if any(type(data[k]) is not int for k in ('width', 'height', 'nodes')) or not 1 <= data['nodes'] <= binding.nodes:
        raise wire.fail(None, 'typed bounded dimensions and node count')
    offset = data['offset']
    if (
        type(offset) is not list
        or len(offset) != 2
        or any(type(v) not in (int, float) for v in offset)
        or (data['width'], data['height']) != (view.width, view.height)
        or offset != list(view.offset)
    ):
        raise wire.fail(None, 'the requested plate view dimensions and offset')
    bounds = wire.record(c.Bounds, data['bounds'])
    if any(a > b for a, b in zip(bounds.minimum, bounds.maximum, strict=True)) or any(
        lo < allowed_lo - 1e-9 or hi > allowed_hi + 1e-9
        for lo, hi, allowed_lo, allowed_hi in zip(
            bounds.minimum, bounds.maximum, binding.bounds.minimum, binding.bounds.maximum, strict=True
        )
    ):
        raise wire.fail(None, 'measured source bounds inside the binding')
    asset = c.PreparedPlate(
        binding,
        source,
        layer,
        plan.digest,
        source_digest(source),
        xml,
        tuple(resources),
        bounds,
        data['nodes'],
        view.width,
        view.height,
        view.offset,
        '',
    )
    if data['digest'] != identity(asset):
        raise wire.fail(None, 'the complete prepared-content identity')
    return replace(asset, digest=data['digest'])
