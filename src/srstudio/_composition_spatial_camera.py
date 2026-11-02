"""Map the shared camera into world or resolved source coordinates for spatial bakers."""

from __future__ import annotations

from . import composition as c
from ._composition_preflight import _camera, _pose
from .limbs.math3d import Frame, Quaternion, Vec3
from .limbs.projection import Camera


def spatial_camera(plan: c.ValidatedScenePlan, layer: str | None = None) -> Camera:
    if type(plan) is not c.ValidatedScenePlan or (layer is not None and type(layer) is not str):
        raise c._fail('plan/layer', None, 'a validated plan and optional layer identifier')
    if c.preflight(plan.spec, plan.bindings) != plan:
        raise c._fail('plan', plan.digest, 'the current reproducible preflight result', 'composition.version')
    frame, scale = Frame(), 1.0
    if layer is not None:
        layers = {item.id: item for item in plan.spec.layers}
        if layer not in layers:
            raise c._fail('layer', layer, 'an existing world layer', 'composition.reference')
        if layers[layer].space != 'world':
            raise c._fail('spatial_camera', layer, 'world-space source coordinates', 'composition.capability')
        frame, scale = _pose(layers[layer], layers, {}, set())
    camera = plan.spec.camera
    forward, right, down = _camera(camera)
    target, position = Vec3(*camera.target), Vec3(*camera.position)
    # limbs.Camera looks down -Z from its distance above view.origin. Express
    # that target and basis in source coordinates; input geometry stays local.
    rotation = frame.rotation.inverse() * Quaternion.axes(right, down, -forward)
    return Camera(
        projection=camera.projection,
        distance=(target - position).length / scale,
        focal=camera.focal / scale,
        scale=camera.scale * scale,
        origin=camera.origin,
        view=Frame(frame.inverse_point(target) / scale, rotation),
        near=camera.near / scale,
    )
