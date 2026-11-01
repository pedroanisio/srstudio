"""Validate actual static triangle geometry and prepare a closed plate scene in a worker."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from typing import Literal

import numpy as np
from sr_core.scene import Scene, read

from . import clay, plates
from . import composition as c
from ._composition_plate_wire import MAX_BYTES, identity, source_digest, validate_source
from ._composition_preflight import _id
from ._composition_texture import prepare as prepare_textures
from .errors import SrstudioError

_COLOR = re.compile(r'#[0-9a-fA-F]{6}\Z')


def _fail(path: str, expected: str) -> c.CompositionError:
    return c._fail('plate.' + path, None, expected, 'composition.payload')


def snapshot(mesh: clay.Mesh, *, basis: Literal['canonical', 'clay']) -> c.PlateMesh:
    if type(mesh) is not clay.Mesh or basis not in ('clay', 'canonical'):
        raise _fail('mesh', 'a clay.Mesh and an explicit canonical or clay source basis')
    buffers = []
    total = 0
    arrays = [('vertices', '<f8', 'fi', 3), ('normals', '<f8', 'fi', 3), ('triangles', '<i8', 'iu', 3)]
    if mesh.uvs is not None:
        arrays.append(('uvs', '<f8', 'fi', 2))
    for name, dtype, kinds, columns in arrays:
        value = getattr(mesh, name)
        if (
            type(value) is not np.ndarray
            or value.ndim != 2
            or value.shape[1] != columns
            or value.dtype.kind not in kinds
        ):
            raise _fail('mesh.' + name, f'numeric arrays of {columns} columns with integer triangle indices')
        total += value.size * 8
        if not len(value) or total > MAX_BYTES:
            raise _fail('mesh', 'nonempty arrays totaling at most eight MiB after float64/int64 conversion')
        if value.dtype.kind == 'u' and value.max() > 2**63 - 1:
            raise _fail('mesh.triangles', 'indices representable as signed int64')
        buffers.append(value.astype(dtype, copy=False).tobytes(order='C'))
    if type(mesh.material) is not str:
        raise _fail('mesh.material', 'a material identifier')
    _id(mesh.material, 'mesh.material')
    return c.PlateMesh(
        mesh.material, buffers[0], buffers[1], buffers[2], basis, buffers[3] if mesh.uvs is not None else None
    )


def _mesh(mesh: c.PlateMesh) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    if any(len(b) % 24 for b in (mesh.vertices, mesh.normals, mesh.triangles)):
        raise _fail('mesh.buffers', 'whole little-endian float64/int64 triples')
    vertices = np.frombuffer(mesh.vertices, dtype='<f8').reshape(-1, 3)
    normals = np.frombuffer(mesh.normals, dtype='<f8').reshape(-1, 3)
    triangles = np.frombuffer(mesh.triangles, dtype='<i8').reshape(-1, 3)
    if vertices.shape != normals.shape or not np.isfinite(vertices).all() or np.max(np.abs(vertices)) > 2**53:
        raise _fail('mesh.vertices', 'finite bounded vertices and one normal per vertex')
    if (
        not np.isfinite(normals).all()
        or np.max(np.abs(normals)) > 1.001
        or not np.all(np.abs(np.linalg.norm(normals, axis=1) - 1) <= 1e-3)
    ):
        raise _fail('mesh.normals', 'finite unit normals')
    if triangles.min() < 0 or triangles.max() >= len(vertices):
        raise _fail('mesh.triangles', 'indices within the vertex array')
    if np.any(
        (triangles[:, 0] == triangles[:, 1])
        | (triangles[:, 0] == triangles[:, 2])
        | (triangles[:, 1] == triangles[:, 2])
    ):
        raise _fail('mesh.triangles', 'three distinct vertex indices per triangle')
    uvs = None
    if mesh.uvs is not None:
        if len(mesh.uvs) != len(vertices) * 16:
            raise _fail('mesh.uvs', 'one little-endian float64 UV pair per vertex')
        uvs = np.frombuffer(mesh.uvs, dtype='<f8').reshape(-1, 2)
        if not np.isfinite(uvs).all() or np.max(np.abs(uvs)) > 2**53:
            raise _fail('mesh.uvs', 'finite bounded texture coordinates; repeating coordinates are allowed')
    if mesh.basis == 'clay':
        vertices, normals, triangles = vertices * (1, 1, -1), normals * (1, 1, -1), triangles[:, ::-1]
    return vertices, normals, triangles, uvs


def prepare_plate(plan: c.ValidatedScenePlan, layer: str, source: c.PlateSource) -> c.PreparedPlate:
    size = validate_source(source)
    view = c.plate_view(plan, layer, meters_per_unit=source.meters_per_unit)
    selected = next(item for item in plan.spec.layers if item.id == layer)
    if source.id != selected.asset:
        raise _fail('source.id', 'the source bound to the selected layer')
    binding = next(b for b in plan.bindings if b.id == source.id)
    if binding.backend != 'plates' or binding.duration is not None or len(binding.plates) != 1:
        raise _fail('binding', 'a static plate binding with one source job')
    digest = source_digest(source)
    job = binding.plates[0]
    if job.key != digest:
        raise _fail('job.key', 'the exact plate_source_digest of the immutable source')
    if (
        job.width < view.width
        or job.height < view.height
        or job.samples < plates.SAMPLES
        or job.bounces < plates.BOUNCES
    ):
        raise _fail('job', 'bounds covering the actual overscan, path samples and bounces')
    if binding.memory_bytes < size * 8:
        raise _fail('memory_bytes', 'at least eight times the input buffer bytes for preparation storage')
    materials = {}
    for i, material in enumerate(source.materials):
        _id(material.id, 'material.id')
        if (
            material.id in materials
            or not _COLOR.fullmatch(material.color)
            or (material.emissive and not _COLOR.fullmatch(material.emissive))
            or (material.sheen and not _COLOR.fullmatch(material.sheen))
        ):
            raise _fail('materials', 'unique material IDs and #RRGGBB colors')
        materials[material.id] = plates.Material(
            f'mat{i}',
            material.color,
            material.roughness,
            material.metallic,
            material.emissive,
            normal_scale=material.normal_scale,
            sheen=material.sheen,
            subsurface=material.subsurface,
        )
    mapped = {m.id for m in source.materials if m.color_map or m.normal_map}
    rotation = np.array([view.direction(p) for p in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]).T
    translation = np.array(view.point((0, 0, 0)))
    meshes = []
    minima, maxima = [], []
    for mesh in source.meshes:
        if mesh.material not in materials:
            raise _fail('mesh.material', 'a declared material')
        vertices, normals, triangles, uvs = _mesh(mesh)
        if mesh.material in mapped and uvs is None:
            raise _fail('mesh.uvs', 'explicit UV coordinates for every mesh using a texture map')
        minima.append(vertices.min(axis=0))
        maxima.append(vertices.max(axis=0))
        meshes.append(
            clay.Mesh(
                materials[mesh.material].id,
                (vertices @ rotation.T) * (view._source_scale * view._world_scale) + translation,
                normals @ rotation.T,
                triangles[:, ::-1],
                uvs,
            )
        )
    minimum, maximum = np.min(minima, axis=0), np.max(maxima, axis=0)
    if np.any(minimum < np.array(binding.bounds.minimum) - 1e-9) or np.any(
        maximum > np.array(binding.bounds.maximum) + 1e-9
    ):
        raise _fail('bounds', 'actual canonical source geometry inside the declared bounds')
    bounds = c.Bounds(tuple(map(float, minimum)), tuple(map(float, maximum)))  # type: ignore[arg-type]
    try:
        plate = plates.Plate(
            view.width,
            view.height,
            view.camera,
            view.lights,
            (plates.Placed(tuple(meshes)),),
            tuple(materials.values()),
        )
        texture_paths, resources = prepare_textures(source)
        resources.update({f'meshes/{mesh.sha256}.obj': mesh.obj for mesh in meshes})
        total = sum(map(len, resources.values()))
        if total > MAX_BYTES:
            raise _fail('resources', 'at most eight MiB of prepared data')
        root = ET.fromstring(plates.document(plate))
        for node, material in zip(root.findall('materials/material'), source.materials, strict=True):
            if material.color_map:
                node.set('baseColorMap', texture_paths[material.color_map])
            if material.normal_map:
                node.set('normalMap', texture_paths[material.normal_map])
                node.set('normalScale', str(material.normal_scale))
        project = root.find('project')
        assert project is not None
        project.set('seed', str(plan.spec.seed))
        xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        total += len(xml)
        nodes = len(list(root.iter()))
        if total > MAX_BYTES or nodes > binding.nodes or job.memory_bytes < total * 8 + view.width * view.height * 8:
            raise _fail('job', 'prepared resources/nodes within the declared memory, node and payload bounds')
        scene = read(xml)
        assert isinstance(scene, Scene)
        errors = scene.check(schema=True)
        if errors:
            raise _fail('schema', 'a schema-valid plate document: ' + str(errors[:3]))
    except SrstudioError as error:
        if isinstance(error, c.CompositionError):
            raise
        raise _fail('definition', 'a valid plate definition') from error
    asset = c.PreparedPlate(
        binding,
        source,
        layer,
        plan.digest,
        digest,
        xml,
        tuple(c.PlateResource(name, data) for name, data in sorted(resources.items())),
        bounds,
        nodes,
        view.width,
        view.height,
        view.offset,
        '',
    )
    return replace(asset, digest=identity(asset))
