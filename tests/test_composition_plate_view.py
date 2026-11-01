"""Register canonical composition coordinates with the actual plate camera."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import plates, proxy


def manifest(**changes):
    binding = c.AssetBinding(
        'host',
        'rafa',
        1,
        'plates',
        c.Bounds((-1, -1, -1), (1, 1, 1)),
        plates=(c.PlateWork('a' * 64, 64, 64, 48, 4, 1, 1024**2),),
    )
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(),
        1,
        7,
        'meter',
        c.CameraSpec('perspective', (0, 0, 10), (0, 0, 0), (32, 32), 100, 10),
        c.LightRig('lit', (c.LightSpec('ambient', 'ambient', '#FFFFFF', 1),)),
        (c.LayerSpec('host', 'host', 1, c.TemporalPolicy(0, 1)),),
        c.RenderBudget(),
    )
    return c.preflight(replace(spec, **changes), (binding,))


def engine_project(view, point):
    camera = view.camera
    lens = proxy.View(camera.position, camera.target, camera.fov, size=(view.width, view.height))
    return lens.project([view.point(point)])[0] + view.offset


def test_default_mapping_reflects_z_converts_meters_and_matches_pixels():
    view = c.plate_view(manifest(), 'host')
    assert view.camera.position == (0, 0, -1000)
    assert view.camera.target == (0, 0, 0)
    assert view.point((0.2, -0.1, 0.5)) == (20, -10, -50)
    assert view.direction((0, 0, 1)) == (0, 0, -1)
    assert engine_project(view, (0.2, -0.1, 0.5)) == pytest.approx((32 + 200 / 9.5, 32 - 100 / 9.5))
    assert view.offset == (0, 0)
    assert view.reverses_winding is True
    with pytest.raises(FrozenInstanceError):
        view.width = 2


@pytest.mark.parametrize('origin', [(13, 41), (-8.5, 80.5), (100, -20)])
def test_offcenter_origin_uses_overscan_and_an_explicit_single_pixel_offset(origin):
    base = manifest()
    plan = manifest(camera=replace(base.spec.camera, origin=origin))
    view = c.plate_view(plan, 'host')
    assert view.offset[0] <= 0 and view.offset[1] <= 0
    assert view.offset[0] + view.width >= 64 and view.offset[1] + view.height >= 64
    assert view.width % 2 == view.height % 2 == 0
    assert engine_project(view, (0, 0, 0)) == pytest.approx(origin)
    assert engine_project(view, (0.1, 0.2, 0)) == pytest.approx((origin[0] + 10, origin[1] + 20))


def test_parent_rotation_and_scale_are_applied_once_before_camera_projection():
    base = manifest()
    parent = replace(base.spec.layers[0], transform=c.Transform((0.2, 0.3, 0), (0, 0, 90), 2))
    child = replace(parent, id='child', parent='host', transform=c.Transform((0.1, 0, 0), (0, 0, -90), 0.5))
    plan = manifest(layers=(parent, child))
    view = c.plate_view(plan, 'child')
    assert view.point((0.1, 0.2, 0)) == pytest.approx((30, 70, 0))
    assert engine_project(view, (0.1, 0.2, 0)) == pytest.approx((62, 102))
    assert view.direction((1, 0, 0)) == pytest.approx((1, 0, 0))


@pytest.mark.parametrize('unit,scale', [('meter', 100), ('centimeter', 1), ('canonical-arm', 72)])
def test_units_are_explicit_and_canonical_arms_need_authored_physical_length(unit, scale):
    plan = manifest(world_unit=unit)
    options = {'meters_per_unit': 0.72} if unit == 'canonical-arm' else {}
    view = c.plate_view(plan, 'host', **options)
    assert view.point((1, 0, 0)) == (scale, 0, 0)
    assert engine_project(view, (0.1, 0.2, 0)) == pytest.approx((42, 52))


def test_shared_lights_remain_in_world_space_after_layer_placement():
    lights = c.LightRig(
        'lit',
        (
            c.LightSpec('ambient', 'ambient', '#102030', 0.7),
            c.LightSpec('area', 'sphere-area', '#FFEEDD', 150, (2, -3, 4), 0.5),
            c.LightSpec('key', 'directional', '#FFFFFF', 2, yaw=30, pitch=-20),
        ),
    )
    base = manifest()
    layer = replace(base.spec.layers[0], transform=c.Transform((1, 1, 1), (10, 20, 30), 0.5))
    view = c.plate_view(manifest(lights=lights, layers=(layer,)), 'host')
    ambient, area, key = view.lights
    assert ambient == plates.Light('ambient', 'ambient', '#102030', 0.7)
    assert area.at == (200, -300, -400) and area.radius == 50
    assert area.intensity == 150
    assert key.yaw == 150 and key.pitch == -20


@pytest.mark.parametrize(
    'bad', ['orthographic', 'flat', 'screen', 'canonical-arm', 'fov', 'overscan', 'forged', 'missing']
)
def test_unsupported_or_unbounded_views_are_refused_before_any_renderer_work(bad):
    base = manifest()
    if bad == 'orthographic':
        plan = manifest(camera=replace(base.spec.camera, projection='orthographic'))
    elif bad == 'flat':
        plan = manifest(lights=c.LightRig('flat'))
    elif bad == 'screen':
        plan = manifest(layers=(replace(base.spec.layers[0], space='screen'),))
    elif bad == 'canonical-arm':
        plan = manifest(world_unit=bad)
    elif bad == 'fov':
        plan = manifest(camera=replace(base.spec.camera, scale=1e6, focal=1e6))
    elif bad == 'overscan':
        plan = manifest(camera=replace(base.spec.camera, origin=(1e6, 32)))
    elif bad == 'forged':
        plan = replace(base, digest='b' * 64)
    else:
        plan = base
    with pytest.raises(c.CompositionError):
        c.plate_view(plan, 'missing' if bad == 'missing' else 'host')


@pytest.mark.parametrize('value', [0, -1, True, float('nan'), 'meters', 10**400])
def test_invalid_canonical_scale_is_a_typed_refusal(value):
    with pytest.raises(c.CompositionError):
        c.plate_view(manifest(world_unit='canonical-arm'), 'host', meters_per_unit=value)


@pytest.mark.parametrize('point', [(1, 2), (True, 0, 0), (float('inf'), 0, 0), [0, 0, 0], (10**400, 0, 0)])
def test_invalid_source_points_are_typed(point):
    view = c.plate_view(manifest(), 'host')
    with pytest.raises(c.CompositionError):
        view.point(point)


def test_metric_units_cannot_be_silently_overridden():
    with pytest.raises(c.CompositionError):
        c.plate_view(manifest(), 'host', meters_per_unit=0.01)
    assert c.plate_view(manifest(), 'host', meters_per_unit=1) == c.plate_view(manifest(), 'host')


@pytest.mark.parametrize('kind', ['vertical', 'far', 'near', 'pixels', 'memory'])
def test_engine_camera_and_overscan_budget_envelopes_are_checked(kind):
    base = manifest()
    if kind == 'vertical':
        plan = manifest(camera=replace(base.spec.camera, position=(0.01, -10, 0)))
    elif kind == 'far':
        plan = manifest(camera=replace(base.spec.camera, position=(0, 0, 101)))
    elif kind == 'near':
        binding = replace(base.bindings[0], bounds=c.Bounds((-0.001, -0.001, 0), (0.001, 0.001, 0)))
        spec = replace(
            base.spec, camera=replace(base.spec.camera, position=(0, 0, 0.02), near=0.001), world_unit='centimeter'
        )
        plan = c.preflight(spec, (binding,))
    elif kind == 'pixels':
        plan = manifest(
            camera=replace(base.spec.camera, origin=(1, 32)), budget=replace(base.spec.budget, max_frame_pixels=4096)
        )
    else:
        plan = manifest(
            camera=replace(base.spec.camera, origin=(1, 32)),
            budget=replace(base.spec.budget, max_memory_bytes=base.cost.memory_bytes),
        )
    with pytest.raises(c.CompositionError):
        c.plate_view(plan, 'host')


@pytest.mark.parametrize('plan,layer', [(None, 'host'), (manifest(), None)])
def test_invalid_adapter_arguments_are_typed(plan, layer):
    with pytest.raises(c.CompositionError):
        c.plate_view(plan, layer)


def test_real_engine_registers_landmarks_under_offaxis_camera_and_parent_pose(tmp_path, scene_render, record_property):
    from srstudio import clay

    base = manifest()
    parent = replace(base.spec.layers[0], transform=c.Transform((0.1, -0.2, 0), (10, 20, 15), 1.2))
    plan = manifest(camera=c.CameraSpec('perspective', (3, -2, 10), (0, 0, 0), (27, 38), 80, 10), layers=(parent,))
    view = c.plate_view(plan, 'host')
    spots = {'red': (-0.2, -0.1, 0.1), 'green': (0.2, 0.1, -0.1), 'blue': (-0.1, 0.3, 0)}
    palette = {'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF'}
    model = clay.Model()
    for name, position in spots.items():
        model.ell(name, view.point(position), (3, 3, 3))
    image = plates.Plate(
        view.width,
        view.height,
        view.camera,
        view.lights,
        (plates.Placed(model.meshes()),),
        tuple(plates.Material(name, color, emissive=color) for name, color in palette.items()),
    )
    with plates.render_session(max_invocations=1, timeout=120):
        path = plates.render(image, engine=scene_render, cache=tmp_path, fonts=tmp_path)
    pixels = plates.pixels(path)
    camera = plan.spec.camera
    forward = np.subtract(camera.target, camera.position, dtype=float)
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, (0, 1, 0))
    right /= np.linalg.norm(right)
    down = np.cross(right, forward)
    for channel, (name, local) in enumerate(spots.items()):
        rows, cols = np.nonzero(
            (pixels[..., channel] > 100) & (pixels[..., (channel + 1) % 3] < 60) & (pixels[..., 3] > 128)
        )
        assert len(rows) >= 5, name
        world = np.array(view.point(local)) * (0.01, 0.01, -0.01)
        ray = world - camera.position
        expected = np.array(camera.origin) + camera.scale * camera.focal / (ray @ forward) * np.array(
            [ray @ right, ray @ down]
        )
        observed = np.array((cols.mean() + 0.5, rows.mean() + 0.5)) + view.offset
        record_property(name + '_error_pixels', float(np.linalg.norm(observed - expected)))
        assert np.linalg.norm(observed - expected) <= 1, (name, observed, expected)
