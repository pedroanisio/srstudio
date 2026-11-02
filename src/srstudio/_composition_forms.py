"""Bounded authored surface fields, shared-light evaluation and palette-only vector shading."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from bisect import bisect_right
from dataclasses import asdict
from fractions import Fraction

from . import composition as c
from ._composition_preflight import _graph, _id, _pose
from .limbs.math3d import Vec3

_COLOR = re.compile(r'#[0-9a-fA-F]{6}\Z')


def fail(expected: str) -> c.CompositionError:
    return c._fail('forms', None, expected, 'composition.forms')


def validate(forms: tuple[c.FormSurface, ...], binding: c.AssetBinding | None = None) -> None:
    if type(forms) is not tuple or len(forms) > 256 or any(type(f) is not c.FormSurface for f in forms):
        raise fail('an immutable tuple of at most 256 FormSurface records')
    _graph(forms, [0])
    seen = set()
    for surface in forms:
        _id(surface.node, 'forms.node')
        if surface.node in seen:
            raise fail('one lighting field per shape ID')
        seen.add(surface.node)
        if not _COLOR.fullmatch(surface.albedo):
            raise fail('a #RRGGBB albedo')
        if surface.mode == 'ink':
            if surface.palette or surface.keys:
                raise fail('ink surfaces without palettes or pose keys')
        elif not 2 <= len(surface.palette) <= 16 or any(not _COLOR.fullmatch(color) for color in surface.palette):
            raise fail('two to sixteen authored #RRGGBB palette colors')
        points = [surface.point, *(key.point for key in surface.keys)]
        normals = [surface.normal, *(key.normal for key in surface.keys)]
        if any(abs(Vec3(*normal).length - 1) > 1e-6 for normal in normals):
            raise fail('unit surface normals')
        if surface.keys and (
            surface.keys[0].time != 0
            or surface.keys[0].point != surface.point
            or surface.keys[0].normal != surface.normal
            or any(a.time >= b.time for a, b in zip(surface.keys, surface.keys[1:], strict=False))
        ):
            raise fail('ordered unique source keys starting at the declared initial point and normal at zero')
        for left, right in zip(surface.keys, surface.keys[1:], strict=False):
            if left.interpolation == 'linear' and Vec3(*left.normal).dot(Vec3(*right.normal)) <= -1 + 1e-6:
                raise fail(
                    'non-antipodal normals for normalized linear interpolation; use an authored intermediate key'
                )
        if binding is not None:
            if binding.backend != 'vector':
                raise fail('vector bindings for authored form surfaces')
            if surface.keys and (binding.duration is None or surface.keys[-1].time > binding.duration):
                raise fail('pose keys within the complete declared source duration')
            if surface.mode != 'ink' and any(
                not low <= coordinate <= high
                for point in points
                for coordinate, low, high in zip(point, binding.bounds.minimum, binding.bounds.maximum, strict=True)
            ):
                raise fail('authored surface points inside the declared asset bounds')


def definition(forms: tuple[c.FormSurface, ...]) -> list[dict]:
    validate(forms)
    return [asdict(surface) for surface in sorted(forms, key=lambda surface: surface.node)]


def size(forms: tuple[c.FormSurface, ...]) -> int:
    return len(json.dumps(definition(forms), separators=(',', ':'), allow_nan=False).encode()) if forms else 0


def verify(root: ET.Element, binding: c.AssetBinding) -> None:
    if not binding.forms:
        return
    validate(binding.forms, binding)
    shapes = {node.get('id'): node for node in root.iter('shape')}
    if set(shapes) != {surface.node for surface in binding.forms} or root.find('assets/text') is not None:
        raise fail(
            'one explicit diffuse or ink field for every shape, with native information kept in a separate layer'
        )
    for surface in binding.forms:
        if surface.mode == 'diffuse' and not _COLOR.fullmatch(shapes[surface.node].get('fill', '')):
            raise fail('a solid #RRGGBB fill on diffuse shapes; keep gradients and outlines in explicit ink fields')


def _sample(surface: c.FormSurface, time: float, clock: c.TemporalPolicy | None = None) -> tuple[Vec3, Vec3]:
    if not surface.keys:
        return Vec3(*surface.point), Vec3(*surface.normal)
    # Use the planner's mapped boundaries directly. Inverting a fractional
    # source rate can land one ULP before a held key and erase its change.
    times = [clock.start + (key.time - clock.source_start) / clock.rate if clock else key.time for key in surface.keys]
    index = max(0, bisect_right(times, time) - 1)
    left = surface.keys[index]
    point, normal = Vec3(*left.point), Vec3(*left.normal)
    if index + 1 < len(surface.keys) and left.interpolation == 'linear':
        right = surface.keys[index + 1]
        fraction = (time - times[index]) / (times[index + 1] - times[index])
        point += (Vec3(*right.point) - point) * fraction
        normal = (normal * (1 - fraction) + Vec3(*right.normal) * fraction).unit()
    return point, normal


def _rgb(color: str) -> tuple[float, ...]:
    values = tuple(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values)


def _tuple(vector: Vec3) -> tuple[float, float, float]:
    return vector.x, vector.y, vector.z


def resolved(
    plan: c.ValidatedScenePlan, layer: c.LayerSpec, time: float, *, scene_clock: bool = False
) -> tuple[c.FormLight, ...]:
    binding = next(binding for binding in plan.bindings if binding.id == layer.asset)
    if not binding.forms:
        return ()
    maximum = plan.spec.duration if scene_clock else (binding.duration or 600)
    if type(time) not in (int, float) or not math.isfinite(time) or not 0 <= time <= maximum:
        raise fail('a finite nonnegative sample time within the source duration')
    frame, scale = _pose(layer, {item.id: item for item in plan.spec.layers}, {}, set())
    result = []
    for surface in binding.forms:
        point, normal = _sample(surface, time, layer.temporal if scene_clock else None)
        point, normal = frame.point(point * scale), frame.rotation.rotate(normal)
        energy = [0.0, 0.0, 0.0]
        if surface.mode == 'diffuse':
            for light in plan.spec.lights.lights:
                if light.kind == 'ambient':
                    weight = light.intensity
                elif light.kind == 'directional':
                    yaw, pitch = math.radians(light.yaw), math.radians(light.pitch)
                    travel = Vec3(math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
                    weight = light.intensity * max(0.0, -normal.dot(travel))
                else:
                    delta = Vec3(*light.position) - point
                    if delta.length <= light.radius:
                        raise fail('surface points outside sphere-area emitters')
                    weight = light.intensity * (light.radius / delta.length) ** 2 * max(0.0, normal.dot(delta.unit()))
                for channel, value in enumerate(_rgb(light.color)):
                    energy[channel] += value * weight
            target = tuple(value * energy[i] * surface.exposure for i, value in enumerate(_rgb(surface.albedo)))
            color = min(
                surface.palette, key=lambda color: sum((a - b) ** 2 for a, b in zip(_rgb(color), target, strict=True))
            )
        else:
            color = None
        result.append(
            c.FormLight(surface.node, _tuple(point), _tuple(normal), (energy[0], energy[1], energy[2]), color)
        )
    return tuple(result)


def lighting(plan: c.ValidatedScenePlan, layer: str, source_time: float) -> tuple[c.FormLight, ...]:
    if type(plan) is not c.ValidatedScenePlan or c.preflight(plan.spec, plan.bindings, purpose=plan.purpose) != plan:
        raise fail('a current validated plan')
    if type(layer) is not str or layer not in {item.id for item in plan.spec.layers}:
        raise fail('an existing layer ID')
    item = next(item for item in plan.spec.layers if item.id == layer)
    if not next(b for b in plan.bindings if b.id == item.asset).forms:
        raise fail('a layer with authored form surfaces')
    return resolved(plan, item, source_time)


def apply(
    root: ET.Element, plan: c.ValidatedScenePlan, layer: c.LayerSpec, time: float, *, scene_clock: bool = False
) -> None:
    nodes = {node.get('id'): node for node in root.iter('shape')}
    for sample in resolved(plan, layer, time, scene_clock=scene_clock):
        if sample.color is not None:
            nodes[sample.node].set('fill', sample.color)


def static(plan: c.ValidatedScenePlan) -> None:
    if any(surface.keys for binding in plan.bindings for surface in binding.forms):
        raise fail('compile_timeline for source-clock form pose keys')


def events(binding: c.AssetBinding, layer: c.LayerSpec, fps: c.FrameRate) -> tuple[float, ...]:
    """Scene intervals needed by the authored fields, including exact off-grid held changes."""
    from .scene_motion import MAX_TIMELINE_SAMPLES

    clock = layer.temporal
    result: set[float] = set()
    intervals = []

    def add(time: float) -> None:
        result.add(time)
        if len(result) > MAX_TIMELINE_SAMPLES:
            raise fail(f'at most {MAX_TIMELINE_SAMPLES} form sample intervals')

    for surface in binding.forms:
        for key in surface.keys:
            scene_time = clock.start + (key.time - clock.source_start) / clock.rate
            if clock.start < scene_time < clock.end:
                add(scene_time)
        for left, right in zip(surface.keys, surface.keys[1:], strict=False):
            if left.interpolation != 'linear' or (left.point, left.normal) == (right.point, right.normal):
                continue
            start = max(clock.start, clock.start + (left.time - clock.source_start) / clock.rate)
            end = min(clock.end, clock.start + (right.time - clock.source_start) / clock.rate)
            rate = Fraction(fps.numerator, fps.denominator)
            first, stop = math.ceil(Fraction(str(start)) * rate), math.ceil(Fraction(str(end)) * rate)
            if stop - first > MAX_TIMELINE_SAMPLES:
                raise fail(f'at most {MAX_TIMELINE_SAMPLES} form sample intervals')
            if first < stop:
                intervals.append((first, stop))
    # Coalesce overlapping grids before expanding; many surfaces may share one pose clock.
    stop = -1
    rate = Fraction(fps.numerator, fps.denominator)
    for first, end in sorted(intervals):
        for frame in range(max(first, stop), end):
            add(float(Fraction(frame, 1) / rate))
        stop = max(stop, end)
    return tuple(sorted(result))
