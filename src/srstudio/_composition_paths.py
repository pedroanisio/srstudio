"""Authored spatial vector paths: bounded geometry, source sampling and one shared camera projection."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from bisect import bisect_right
from dataclasses import asdict

from . import composition as c
from ._composition_preflight import _camera
from .limbs.math3d import Frame, Vec3


def fail(expected: str) -> c.CompositionError:
    return c._fail('forms.path', None, expected, 'composition.geometry')


def spatial(binding: c.AssetBinding) -> bool:
    return bool(binding.forms) and all(surface.path is not None for surface in binding.forms)


def expansion_bytes(binding: c.AssetBinding) -> int:
    """One projected copy: two .17g coordinates plus path commands and attributes per vertex."""
    return sum(64 * (len(surface.path.points) + 1) for surface in binding.forms if surface.path is not None)


def validate(forms: tuple[c.FormSurface, ...], binding: c.AssetBinding | None) -> None:
    paths = [surface.path for surface in forms if surface.path is not None]
    if paths and len(paths) != len(forms):
        raise fail(
            'spatial paths for every shape in a spatial vector asset; separate planar artwork into another asset'
        )
    for path in paths:
        minimum = 3 if path.closed else 2
        if not minimum <= len(path.points) <= 256:
            raise fail(f'{minimum}..256 spatial vertices per path')
        if path.keys and (
            path.keys[0].time != 0
            or path.keys[0].points != path.points
            or any(a.time >= b.time for a, b in zip(path.keys, path.keys[1:], strict=False))
        ):
            raise fail('ordered path keys starting at the initial points at source time zero')
        for points in (path.points, *(key.points for key in path.keys)):
            if len(points) != len(path.points):
                raise fail(
                    'the same vertex count at every key; split topology changes into explicit replacement layers'
                )
            if binding is not None and any(
                not low <= v <= high
                for point in points
                for v, low, high in zip(point, binding.bounds.minimum, binding.bounds.maximum, strict=True)
            ):
                raise fail('all spatial vertices within the declared source bounds')
        if binding is not None and path.keys and (binding.duration is None or path.keys[-1].time > binding.duration):
            raise fail('path keys inside the declared complete source duration')


def verify(root: ET.Element, binding: c.AssetBinding) -> None:
    if not spatial(binding):
        return
    for node in root.iter():
        if node.tag == 'shape' and node.get('shape') != 'path':
            raise fail('native path shapes for authored spatial geometry')
        if node.tag in ('shape', 'group', 'composition'):
            transforms = {
                'x': 0.0,
                'y': 0.0,
                'rotation': 0.0,
                'scaleX': 1.0,
                'scaleY': 1.0,
                'anchorX': 0.0,
                'anchorY': 0.0,
            }
            if any(float(node.get(k, str(v))) != v for k, v in transforms.items()):
                raise fail('identity XML transforms; author geometry transforms in the world layer or source vertices')
            if node.get('fill', '').startswith('url(') or node.get('stroke', '').startswith('url('):
                raise fail('solid spatial path colors; gradient-coordinate projection is not supported')
        if node.tag == 'animate' and node.get('property') != 'opacity':
            raise fail('only opacity XML animation on spatial paths; author path motion in PathKey records')


def sample(path: c.FormPath, time: float, clock: c.TemporalPolicy | None) -> tuple[Vec3, ...]:
    if not path.keys:
        return tuple(Vec3(*point) for point in path.points)
    times = [clock.start + (key.time - clock.source_start) / clock.rate if clock else key.time for key in path.keys]
    index = max(0, bisect_right(times, time) - 1)
    left = path.keys[index]
    points = tuple(Vec3(*point) for point in left.points)
    if index + 1 < len(path.keys) and left.interpolation == 'linear':
        fraction = (time - times[index]) / (times[index + 1] - times[index])
        return tuple(a.lerp(Vec3(*b), fraction) for a, b in zip(points, path.keys[index + 1].points, strict=True))
    return points


def world(
    path: c.FormPath | None, time: float, clock: c.TemporalPolicy | None, frame: Frame, scale: float
) -> tuple[tuple[float, float, float], ...]:
    if path is None:
        return ()
    return tuple(tuple(asdict(frame.point(point * scale)).values()) for point in sample(path, time, clock))


def bounds(binding: c.AssetBinding) -> c.Bounds:
    points = [
        point
        for surface in binding.forms
        if surface.path is not None
        for values in (surface.path.points, *(key.points for key in surface.path.keys))
        for point in values
    ]

    def corner(function) -> tuple[float, float, float]:
        return function(p[0] for p in points), function(p[1] for p in points), function(p[2] for p in points)

    return c.Bounds(corner(min), corner(max))


def apply(node: ET.Element, field: c.FormLight, spec: c.ScenePlan, path: c.FormPath) -> None:
    camera = spec.camera
    forward, right, down = _camera(camera)
    points = []
    for vertex in field.vertices:
        delta = Vec3(*vertex) - Vec3(*camera.position)
        depth = delta.dot(forward)
        if depth <= camera.near:
            raise fail('all path vertices beyond the shared camera near plane')
        scale = camera.scale * (camera.focal / depth if camera.projection == 'perspective' else 1)
        point = (camera.origin[0] + delta.dot(right) * scale, camera.origin[1] + delta.dot(down) * scale)
        if not all(math.isfinite(v) for v in point):
            raise fail('finite projected vertices')
        points.append(' '.join(format(v, '.17g') for v in point))
    node.set('path', 'M ' + ' L '.join(points) + (' Z' if path.closed else ''))
    node.set('width', str(spec.width))
    node.set('height', str(spec.height))
