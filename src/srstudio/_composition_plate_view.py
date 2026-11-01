"""Canonical scene coordinates to the plate backend's centimeter-like, +Z-away axes.

Only perspective world layers are supported by the current plates.Camera API.
An off-center principal point uses bounded overscan and a screen-space offset;
shifting the plate alone without overscan would lose visible edge geometry.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from . import composition as c
from . import plates
from ._composition_preflight import _camera, _pose
from .limbs.math3d import Frame, Vec3


def _vector(value: tuple[float, float, float]) -> Vec3:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(v) not in (int, float) or not abs(v) <= 2**53 for v in value)
    ):
        raise c._fail('plate_view.point', None, 'three finite canonical coordinates in an immutable tuple')
    return Vec3(*value)


def _reflect(point: Vec3, scale: float = 1) -> tuple[float, float, float]:
    return point.x * scale, point.y * scale, -point.z * scale


@dataclass(frozen=True)
class PlateView:
    """Immutable projection bridge, not a prepared geometry or rendered-pixel certificate.

    point/direction consume canonical source axes, +Z toward the reference viewer.
    Existing clay meshes use +Z away: convert their authored basis explicitly
    before applying this bridge. Transform vertices with point, normals with
    direction and reverse triangle winding because the bridge reflects Z.
    """

    plan_digest: str
    layer: str
    width: int
    height: int
    offset: tuple[float, float]
    camera: plates.Camera
    lights: tuple[plates.Light, ...]
    _frame: Frame
    _source_scale: float
    _world_scale: float

    @property
    def reverses_winding(self) -> bool:
        return True

    def point(self, source: tuple[float, float, float]) -> tuple[float, float, float]:
        """Source point through all parents, world-unit conversion and backend handedness once."""
        return _reflect(self._frame.point(_vector(source) * self._source_scale), self._world_scale)

    def direction(self, source: tuple[float, float, float]) -> tuple[float, float, float]:
        """Rotate and reflect a source direction/normal, preserving its magnitude."""
        return _reflect(self._frame.rotation.rotate(_vector(source)))


def _units(spec: c.ScenePlan, supplied: float | None) -> float:
    metric = {'meter': 1.0, 'centimeter': 0.01}
    if supplied is not None and (type(supplied) not in (float, int) or not 1e-6 <= supplied <= 1e6):
        raise c._fail('meters_per_unit', supplied, 'a finite physical scale in 1e-6..1e6')
    if spec.world_unit in metric:
        actual = metric[spec.world_unit]
        if supplied is not None and supplied != actual:
            raise c._fail('meters_per_unit', supplied, actual, 'composition.capability')
    elif supplied is None:
        raise c._fail('meters_per_unit', None, 'an authored canonical-arm length in meters', 'composition.capability')
    else:
        actual = supplied
    return 100 * actual


def _lights(rig: c.LightRig, scale: float) -> tuple[plates.Light, ...]:
    result = []
    for light in rig.lights:
        options: dict = {}
        if light.kind == 'sphere-area':
            options = {'at': _reflect(Vec3(*light.position), scale), 'radius': light.radius * scale}
        elif light.kind == 'directional':
            options = {'yaw': (180 - light.yaw + 180) % 360 - 180, 'pitch': light.pitch}
        result.append(plates.Light(light.id, light.kind, light.color, light.intensity, **options))
    return tuple(result)


def plate_view(plan: c.ValidatedScenePlan, layer: str, *, meters_per_unit: float | None = None) -> PlateView:
    if type(plan) is not c.ValidatedScenePlan or type(layer) is not str:
        raise c._fail('plan/layer', None, 'a validated plan and layer identifier')
    if c.preflight(plan.spec, plan.bindings) != plan:
        raise c._fail('plan', plan.digest, 'the current reproducible preflight result', 'composition.version')
    spec = plan.spec
    layers = {item.id: item for item in spec.layers}
    if layer not in layers:
        raise c._fail('layer', layer, 'an existing layer identifier', 'composition.reference')
    item = layers[layer]
    binding = next(asset for asset in plan.bindings if asset.id == item.asset)
    if (
        item.space != 'world'
        or binding.backend not in ('plates', 'proxy')
        or spec.camera.projection != 'perspective'
        or spec.lights.mode != 'lit'
    ):
        raise c._fail('plate_view', layer, 'a lit perspective world plate/proxy layer', 'composition.capability')
    units = _units(spec, meters_per_unit)
    frame, source_scale = _pose(item, layers, {}, set())
    camera = spec.camera
    forward, _, _ = _camera(camera)
    # The engine switches its look-at up hint near vertical. Refuse that envelope
    # until the plate API can carry an explicit roll/up basis.
    if abs(forward.y) > 0.999:
        raise c._fail('camera.target', camera.target, 'a view outside the engine up-axis switch', 'composition.camera')
    width = 2 * math.ceil(max(abs(camera.origin[0]), abs(spec.width - camera.origin[0])))
    height = 2 * math.ceil(max(abs(camera.origin[1]), abs(spec.height - camera.origin[1])))
    memory = plan.cost.memory_bytes + 8 * (width * height - spec.width * spec.height)
    if (
        max(width, height) > 8192
        or width * height > spec.budget.max_frame_pixels
        or memory > spec.budget.max_memory_bytes
    ):
        raise c._fail(
            'budget.plate_view', (width, height, memory), 'overscan within frame/memory limits', 'composition.budget'
        )
    fov = math.degrees(2 * math.atan(width / (2 * camera.scale * camera.focal)))
    if not 0.1 <= fov <= 179:
        raise c._fail('camera.fov', fov, 'a horizontal field of view in 0.1..179 degrees', 'composition.camera')
    # plates.Camera currently uses the engine's 0.1..10000 scene-unit clipping
    # defaults. Check the whole declared geometry, not just its origin.
    for corner in itertools.product(*zip(binding.bounds.minimum, binding.bounds.maximum, strict=True)):
        depth = (frame.point(Vec3(*corner) * source_scale) - Vec3(*camera.position)).dot(forward) * units
        if not 0.1 < depth < 10000:
            raise c._fail(
                'layer.bounds', depth, 'geometry inside the plate camera clipping range', 'composition.camera'
            )
    return PlateView(
        plan.digest,
        layer,
        width,
        height,
        (camera.origin[0] - width / 2, camera.origin[1] - height / 2),
        plates.Camera(_reflect(Vec3(*camera.position), units), _reflect(Vec3(*camera.target), units), fov),
        _lights(spec.lights, units),
        frame,
        source_scale,
        units,
    )
