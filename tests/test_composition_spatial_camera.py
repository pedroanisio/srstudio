"""Spatial hand/prop projection uses the same validated camera and parents as raster layers."""

from dataclasses import replace

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import Affine, Frame, Vec3
from srstudio.limbs.errors import LimbError
from support.composition import paper, plate_plan
from support.composition_plate_view import engine_project


@pytest.mark.parametrize(
    'position,target', [((0, 0, 10), (0, 0, 0)), ((3, -2, 10), (0.2, 0.1, 0)), ((-8, 1, 4), (0, 0, 0))]
)
@pytest.mark.parametrize('unit,meters', [('meter', 1), ('centimeter', 0.01), ('canonical-arm', 0.72)])
def test_spatial_camera_matches_plate_projection_through_transformed_parents(position, target, unit, meters):
    base = plate_plan()
    parent = replace(base.spec.layers[0], transform=c.Transform((0.2, -0.1, 0.3), (10, 20, 30), 1.3))
    child = replace(parent, id='child', parent=parent.id, transform=c.Transform((-0.1, 0.2, 0.1), (-5, 12, 18), 0.7))
    plan = plate_plan(
        world_unit=unit,
        camera=replace(base.spec.camera, position=position, target=target, origin=(19, 41)),
        layers=(parent, child),
    )
    raster = c.plate_view(plan, 'child', meters_per_unit=meters)
    spatial = c.spatial_camera(plan, 'child')
    drawing_parent = Affine(1.2, 0.1, -0.2, 0.9, 13, -7)
    for point in ((0, 0, 0), (-0.2, -0.1, 0.1), (0.2, 0.1, -0.1), (-0.1, 0.3, 0)):
        actual = spatial.project(Vec3(*point), parent=drawing_parent)
        assert drawing_parent.point(actual.xy) == pytest.approx(engine_project(raster, point), abs=1e-9)
    # The returned source-space camera already owns layer and parent transforms.
    assert spatial.scale == pytest.approx(plan.spec.camera.scale * 1.3 * 0.7)
    assert spatial.near == pytest.approx(plan.spec.camera.near / (1.3 * 0.7))


def test_world_camera_and_source_camera_agree_without_double_applying_the_layer():
    base = plate_plan()
    layer = replace(base.spec.layers[0], transform=c.Transform((0.2, -0.1, 0.3), (0, 0, 0), 2))
    plan = plate_plan(layers=(layer,))
    local = Vec3(0.1, 0.2, 0.3)
    world = local * 2 + Vec3(*layer.transform.translation)
    assert c.spatial_camera(plan).project(world).xy == pytest.approx(c.spatial_camera(plan, 'host').project(local).xy)
    assert c.spatial_camera(plan) == c.spatial_camera(plan, None)


def test_orthographic_vectors_use_the_same_spatial_bridge_without_claiming_plate_support():
    spec, binding, _ = paper()
    camera = c.spatial_camera(c.preflight(spec, (binding,)), 'paper')
    assert camera.projection == 'orthographic'
    assert camera.project(Vec3(5, 7, 0)).xy == pytest.approx((25, 37))
    base = plate_plan()
    plan = plate_plan(camera=replace(base.spec.camera, projection='orthographic'))
    assert c.spatial_camera(plan).project(Vec3(0.1, 0.2, 0)).xy == pytest.approx((42, 52))
    with pytest.raises(c.CompositionError):
        c.plate_view(plan, 'host')


def test_sampled_shared_camera_and_parent_motion_are_random_access():
    base = plate_plan()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, base.spec.camera), m.CameraKey(1, replace(base.spec.camera, position=(1, -1, 10)))),
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.2, 0, 0), (10, 20, 30))))
            ),
        ),
    )
    observed = {}
    for time in (0, 0.7, 1, 0.2, 0.7, 0):
        plan = m.sample_scene(base.spec, base.bindings, motion, time)
        result = c.spatial_camera(plan, 'host').project(Vec3(0.1, 0.2, 0.3))
        assert result.xy == pytest.approx(engine_project(c.plate_view(plan, 'host'), (0.1, 0.2, 0.3)))
        if time in observed:
            assert result == observed[time]
        observed[time] = result


@pytest.mark.parametrize('bad', ['plan', 'layer-type', 'missing', 'forged', 'screen'])
def test_invalid_plan_or_layer_is_a_typed_refusal(bad):
    plan, layer = plate_plan(), 'host'
    if bad == 'plan':
        plan = {}
    elif bad == 'layer-type':
        layer = []
    elif bad == 'missing':
        layer = 'unknown'
    elif bad == 'forged':
        plan = replace(plan, digest='a' * 64)
    else:
        plan = plate_plan(layers=(replace(plan.spec.layers[0], space='screen'),))
    with pytest.raises(c.CompositionError):
        c.spatial_camera(plan, layer)


def test_spatial_projection_rejects_near_plane_and_singular_drawing_parents():
    camera = c.spatial_camera(plate_plan())
    with pytest.raises(LimbError):
        camera.project(Vec3(0, 0, 10))
    with pytest.raises(LimbError):
        camera.project(Vec3(), parent=Affine(a=0, d=0))
    assert camera.project(Vec3(), frame=Frame(Vec3(0.1, 0, 0))).xy == pytest.approx((42, 32))


def test_real_engine_spatial_landmarks_match_at_full_delivery_size(tmp_path, scene_render, record_property):
    from srstudio import clay, plates

    base = plate_plan()
    spec = replace(
        base.spec,
        width=1080,
        height=1920,
        camera=c.CameraSpec('perspective', (3, -2, 10), (0, 0, 0), (500, 980), 700, 10),
        layers=(replace(base.spec.layers[0], transform=c.Transform((0.1, -0.2, 0), (10, 20, 15), 1.2)),),
    )
    # The view is used to author test landmark geometry; no job declaration is
    # presented as a prepared payload or used for timeline budget certification.
    plan = c.preflight(spec, base.bindings)
    raster, spatial = c.plate_view(plan, 'host'), c.spatial_camera(plan, 'host')
    spots = ((-0.2, -0.1, 0.1), (0.2, 0.1, -0.1), (-0.1, 0.3, 0))
    colors = ('#FF0000', '#00FF00', '#0000FF')
    model = clay.Model()
    for index, point in enumerate(spots):
        model.ell(f'spot{index}', raster.point(point), (0.45, 0.45, 0.45))
    image = plates.Plate(
        raster.width,
        raster.height,
        raster.camera,
        raster.lights,
        (plates.Placed(model.meshes()),),
        tuple(plates.Material(f'spot{i}', color, emissive=color) for i, color in enumerate(colors)),
    )
    with plates.render_session(max_invocations=1, timeout=120):
        path = plates.render(image, engine=scene_render, cache=tmp_path, fonts=tmp_path)
    pixels = plates.pixels(path)
    for channel, point in enumerate(spots):
        rows, cols = np.nonzero(
            (pixels[..., channel] > 100) & (pixels[..., (channel + 1) % 3] < 60) & (pixels[..., 3] > 128)
        )
        assert len(rows) >= 5
        observed = np.array((cols.mean() + 0.5, rows.mean() + 0.5)) + raster.offset
        expected = spatial.project(Vec3(*point)).xy
        error = float(np.linalg.norm(observed - expected))
        record_property(f'spot{channel}_error_pixels', error)
        assert error <= 1, (observed, expected)
