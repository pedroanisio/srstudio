"""Validate authored convex receiver masks against explicit caster and light anchors."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict

from . import composition as c
from ._composition_preflight import _anchor
from .limbs.math3d import Vec3


def definition(record: c._Record) -> dict:
    """Unused optional scene fields do not change existing identities or metadata costs."""

    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in ('shadow_mask', 'background') or v is not None}
        if isinstance(value, (tuple, list)):
            return [clean(v) for v in value]
        return value

    return clean(asdict(record))


def fail(layer: str, expected: str, actual=None) -> c.CompositionError:
    return c._fail('layers.' + layer + '.shadow', actual, expected, 'composition.shadow')


def polygon(layer: c.LayerSpec, surface: c.FormSurface, poses: dict) -> tuple[tuple[Vec3, ...], Vec3]:
    path = surface.path
    if path is None or not path.closed or path.keys:
        raise fail(layer.id, 'a static closed spatial polygon for the receiver and authored mask')
    frame, scale = poses[layer.id]
    points = tuple(frame.point(Vec3(*p) * scale) for p in path.points)
    normal = (points[1] - points[0]).cross(points[2] - points[0])
    if normal.length <= 1e-10:
        raise fail(layer.id, 'a nondegenerate convex shadow polygon')
    normal = normal.unit()
    if any(abs((point - points[0]).dot(normal)) > 1e-8 for point in points):
        raise fail(layer.id, 'coplanar shadow polygon vertices')
    # Every vertex must lie strictly on the inner side of every nonincident edge.
    # This excludes self-intersections and repeated/collinear corners as well as concavity.
    for i, (a, b) in enumerate(zip(points, (*points[1:], points[0]), strict=True)):
        if any(
            (b - a).cross(p - a).dot(normal) <= 1e-10
            for j, p in enumerate(points)
            if j not in (i, (i + 1) % len(points))
        ):
            raise fail(layer.id, 'a strictly convex shadow polygon without repeated vertices')
    return points, normal


def inside(point: Vec3, polygon: tuple[Vec3, ...], normal: Vec3, tolerance: float) -> bool:
    return abs((point - polygon[0]).dot(normal)) <= tolerance and all(
        (b - a).cross(point - a).dot(normal) >= -tolerance * (b - a).length
        for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True)
    )


def validate(spec: c.ScenePlan, layers: dict, assets: dict, poses: dict, *, already: int) -> int:
    lights = {light.id: light for light in spec.lights.lights}
    indices = {layer.id: i for i, layer in enumerate(spec.layers)}
    paired: set[str] = set()
    samples = 0
    for mask in spec.layers:
        shadow = mask.shadow_mask
        if shadow is None:
            continue
        if shadow.caster not in layers or shadow.receiver not in layers:
            raise fail(mask.id, 'existing caster and receiver layers')
        caster, receiver = layers[shadow.caster], layers[shadow.receiver]
        if caster.id in paired or caster.shadow_receiver != receiver.id:
            raise fail(mask.id, 'exactly one authored mask paired with the caster shadow_receiver')
        paired.add(caster.id)
        if not indices[receiver.id] < indices[mask.id] < indices[caster.id]:
            raise fail(mask.id, 'receiver, mask, then caster in painter order')
        if any(layer.space != 'world' or layer.role != 'picture' for layer in (mask, caster, receiver)):
            raise fail(mask.id, 'world picture layers for caster, mask and receiver')
        if mask.parent != receiver.id or mask.shadow_receiver is not None or receiver.shadow_mask is not None:
            raise fail(mask.id, 'a mask parented to its receiver, without chained mask receivers')
        if (mask.temporal.start, mask.temporal.end) != (caster.temporal.start, caster.temporal.end) or not (
            receiver.temporal.start <= mask.temporal.start < mask.temporal.end <= receiver.temporal.end
        ):
            raise fail(mask.id, 'a mask covering exactly the caster interval inside the receiver interval')
        forms = assets[mask.asset].forms
        if len(forms) != 1 or forms[0].mode != 'ink':
            raise fail(mask.id, 'one explicit ink polygon for the authored shadow mask')
        receivers = {surface.node: surface for surface in assets[receiver.asset].forms}
        if shadow.receiver_surface not in receivers:
            raise fail(mask.id, 'a named spatial receiver surface')
        ground, normal = polygon(receiver, receivers[shadow.receiver_surface], poses)
        contour, mask_normal = polygon(mask, forms[0], poses)
        if any(not inside(point, ground, normal, 1e-8) for point in contour):
            raise fail(mask.id, 'the complete mask on and inside the receiver surface')
        light = lights.get(shadow.light)
        if light is None or light.kind != 'directional' or light.intensity <= 0:
            raise fail(mask.id, 'an existing positive-intensity directional shadow light')
        yaw, pitch = math.radians(light.yaw), math.radians(light.pitch)
        travel = Vec3(math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
        denominator = travel.dot(normal)
        if abs(denominator) < 1e-8:
            raise fail(mask.id, 'a shadow light not parallel to the receiver plane')
        resolved = []
        times = {mask.temporal.start, mask.temporal.end}
        for layer, name in ((caster, shadow.caster_anchor), (mask, shadow.mask_anchor)):
            anchors = {anchor.name: anchor for anchor in assets[layer.asset].anchors}
            if name not in anchors:
                raise fail(mask.id, 'named caster and mask anchors')
            anchor = anchors[name]
            resolved.append((layer, anchor))
            clock = layer.temporal
            times.update(
                time
                for key in anchor.keys
                if mask.temporal.start
                < (time := clock.start + (key.time - clock.source_start) / clock.rate)
                < mask.temporal.end
            )
        if already + samples + len(times) > spec.budget.max_contact_samples:
            raise c._fail(
                'budget.max_contact_samples',
                already + samples + len(times),
                f'<= {spec.budget.max_contact_samples}',
                'composition.budget',
            )
        # Static planes/masks and directional projection make anchor differences affine
        # between the union of source keys. Endpoint checks bound each complete segment.
        for time in sorted(times):
            points = []
            for layer, anchor in resolved:
                clock = layer.temporal
                local = _anchor(
                    anchor,
                    clock.source_start + (time - clock.start) * clock.rate,
                    tuple(key.time for key in anchor.keys),
                )
                frame, scale = poses[layer.id]
                points.append(frame.point(local * scale))
            origin, center = points
            distance = (ground[0] - origin).dot(normal) / denominator
            projected = origin + travel * distance
            if (
                distance < -1e-8
                or (projected - center).length > shadow.tolerance
                or not inside(center, contour, mask_normal, 1e-8)
            ):
                raise fail(
                    mask.id,
                    'a forward caster projection matching an anchor inside its shadow mask',
                    {'time': time, 'residual': (projected - center).length},
                )
            samples += 1
    for caster in spec.layers:
        if caster.shadow_receiver is not None and caster.id not in paired:
            raise c._fail(
                'layers.' + caster.id + '.shadow_receiver',
                caster.shadow_receiver,
                'one explicit authored shadow mask; requested shadows cannot be omitted',
                'composition.capability',
            )
    return samples


def nodes(plan: c.ValidatedScenePlan, asset: str) -> tuple[tuple[str, str], ...]:
    layers = {layer.id: layer for layer in plan.spec.layers}
    bindings = {binding.id: binding for binding in plan.bindings}
    result = set()
    for layer in plan.spec.layers:
        shadow = layer.shadow_mask
        if shadow is None:
            continue
        if layer.asset == asset:
            result.add(('mask', bindings[asset].forms[0].node))
        if layers[shadow.receiver].asset == asset:
            result.add(('receiver', shadow.receiver_surface))
    return tuple(sorted(result))


def verify_payload(root: ET.Element, required: tuple[tuple[str, str], ...]) -> None:
    if type(required) is not tuple or len(required) > 2 * c.MAX_LAYERS:
        raise fail('payload', 'bounded shadow node roles')
    parents = {child: parent for parent in root.iter() for child in parent}
    shapes = {node.get('id'): node for node in root.iter('shape')}
    for entry in required:
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or entry[0] not in ('mask', 'receiver')
            or type(entry[1]) is not str
        ):
            raise fail('payload', 'typed mask/receiver node roles')
        role, name = entry
        if name not in shapes:
            raise fail('payload', 'existing shadow shapes')
        shape = shapes[name]
        fill = shape.get('fill', '')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', fill) or (
            len(fill) == 9 and int(fill[-2:], 16) == 0
        ):
            raise fail(name, 'a visible solid fill on the shadow mask and receiver')
        if role == 'mask' and float(shape.get('strokeWidth', '0')) != 0:
            raise fail(name, 'a fill-only shadow mask contained by its declared polygon')
        current = shape
        while current is not root:
            if current.get('visible', 'true') not in ('true', '1'):
                raise fail(name, 'visible shadow and receiver geometry through every ancestor')
            if (
                any(k in current.attrib for k in ('start', 'end', 'timeOffset', 'timeScale'))
                or current.find('animate') is not None
            ):
                raise fail(name, 'static shadow payload visibility; layer windows own its complete interval')
            if not 0 < float(current.get('opacity', '1')) <= 1:
                raise fail(name, 'positive shadow and receiver opacity through every ancestor')
            current = parents[current]


def verify_roots(plan: c.ValidatedScenePlan, roots: dict[str, ET.Element]) -> None:
    for name, root in roots.items():
        required = nodes(plan, name)
        if required:
            verify_payload(root, required)


def prepare_vector(
    plan: c.ValidatedScenePlan, binding: c.AssetBinding, asset: c.VectorSource | c.PreparedVector
) -> c.PreparedVector:
    """Verify source visibility in the existing bounded preparation worker, before raster work."""
    from ._composition_runtime import prepare_vector as prepare

    required = nodes(plan, binding.id)
    if not required:
        return c.prepare_vector(binding, asset.xml, fonts=asset.fonts, budget=plan.spec.budget)
    return prepare(binding, asset.xml, fonts=asset.fonts, budget=plan.spec.budget, shadow_nodes=required)
