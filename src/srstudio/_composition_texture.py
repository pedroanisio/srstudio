"""Owned texture snapshots and worker-only PNG preparation for closed plate sources."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Literal

import numpy as np

from . import clay, plates
from . import composition as c
from ._composition_png import MAX_BYTES
from ._composition_preflight import _digest, _id

MAX_TEXTURES = 128


def _fail(path: str, expected: str) -> c.CompositionError:
    return c._fail('plate.' + path, None, expected, 'composition.payload')


def validate(texture: c.PlateTexture) -> int:
    if type(texture) is not c.PlateTexture or type(texture.id) is not str:
        raise _fail('texture', 'a PlateTexture with an identifier')
    _id(texture.id, 'texture.id')
    if (
        any(type(n) is not int or not 1 <= n <= 8192 for n in (texture.width, texture.height))
        or type(texture.pixels) is not bytes
        or not 1 <= len(texture.pixels) <= MAX_BYTES
        or len(texture.pixels) != texture.width * texture.height * 4
    ):
        raise _fail('texture.pixels', 'exact immutable RGBA8 pixels, dimensions 1..8192, at most eight MiB')
    return len(texture.pixels)


def snapshot(id: str, texture: plates.Texture) -> c.PlateTexture:
    if type(texture) is not plates.Texture:
        raise _fail('texture', 'a plates.Texture')
    pixels = texture.pixels
    if (
        type(pixels) is not np.ndarray
        or pixels.ndim != 3
        or pixels.shape[2] != 4
        or pixels.dtype != np.dtype('uint8')
        or any(not 1 <= n <= 8192 for n in pixels.shape[:2])
        or pixels.size > MAX_BYTES
    ):
        raise _fail('texture.pixels', 'bounded nonempty height-by-width-by-four uint8 pixels')
    result = c.PlateTexture(id, pixels.shape[1], pixels.shape[0], pixels.tobytes(order='C'))
    validate(result)
    return result


def snapshot_source(
    id: str,
    meshes: tuple[clay.Mesh, ...],
    materials: tuple[plates.Material, ...],
    *,
    basis: Literal['canonical', 'clay'],
    meters_per_unit: float | None,
) -> c.PlateSource:
    from ._composition_plate import snapshot as mesh_snapshot
    from ._composition_plate_wire import MAX_MESHES, validate_source

    if any(type(items) is not tuple or not 1 <= len(items) <= MAX_MESHES for items in (meshes, materials)):
        raise _fail('source', 'bounded immutable mesh and material tuples')
    copied = []
    total = 0
    for mesh in meshes:
        frozen = mesh_snapshot(mesh, basis=basis)
        total += sum(len(b) for b in (frozen.vertices, frozen.normals, frozen.triangles, frozen.uvs or b''))
        if total > MAX_BYTES:
            raise _fail('source', 'at most eight MiB of combined mesh and texture bytes')
        copied.append(frozen)
    textures: dict[str, c.PlateTexture] = {}
    converted = []
    for material in materials:
        if type(material) is not plates.Material or material.print is not None:
            raise _fail(
                'material', 'a plates.Material without a printed-label recipe; labels require explicit rendering'
            )
        maps = {}
        for field in ('color_map', 'normal_map'):
            value = getattr(material, field)
            name = ''
            if value is not None:
                texture = snapshot('map', value)
                name = 'tex_' + _digest(
                    {
                        'width': texture.width,
                        'height': texture.height,
                        'pixels': hashlib.sha256(texture.pixels).hexdigest(),
                    }
                )
                if name not in textures:
                    total += len(texture.pixels)
                    if total > MAX_BYTES or len(textures) >= MAX_TEXTURES:
                        raise _fail('source', 'at most eight MiB of combined buffers and 128 textures')
                    textures[name] = replace(texture, id=name)
            maps[field] = name
        converted.append(
            c.PlateMaterial(
                material.id,
                material.color,
                material.roughness,
                material.metallic,
                material.emissive,
                maps['color_map'],
                maps['normal_map'],
                material.normal_scale,
                material.sheen,
                material.subsurface,
            )
        )
    source = c.PlateSource(id, tuple(copied), tuple(converted), meters_per_unit, tuple(textures.values()))
    validate_source(source)
    return source


def prepare(source: c.PlateSource) -> tuple[dict[str, str], dict[str, bytes]]:
    """Run after bounded source validation, inside the preparation worker."""
    textures = {texture.id: texture for texture in source.textures}
    referenced = {name for m in source.materials for name in (m.color_map, m.normal_map) if name}
    if len(textures) != len(source.textures) or set(textures) != referenced:
        raise _fail('textures', 'unique textures matching exactly the material map references')
    paths, resources = {}, {}
    total = 0
    for name, texture in textures.items():
        validate(texture)
        array = np.frombuffer(texture.pixels, np.uint8).reshape(texture.height, texture.width, 4)
        data = plates._png_bytes(array)
        path = 'textures/' + hashlib.sha256(data).hexdigest() + '.png'
        if path not in resources:
            total += len(data)
        if total > MAX_BYTES:
            raise _fail('textures', 'at most eight MiB of encoded texture resources')
        paths[name], resources[path] = path, data
    return paths, resources
