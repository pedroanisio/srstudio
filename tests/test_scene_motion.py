"""Scene motion samples preserve shared view, light and parent contracts."""

import importlib
import json
from dataclasses import asdict, replace

import pytest

from srstudio import composition as c
from support.composition import plate_plan


def api():
    return importlib.import_module('srstudio.scene_motion')


def motion_scene():
    m = api()
    base = plate_plan()
    camera = replace(base.spec.camera, position=(2, 0, 10), target=(2, 0, 0))
    light = replace(base.spec.lights.lights[0], intensity=3)
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, base.spec.camera), m.CameraKey(1, camera)),
        lights=(m.LightTrack('ambient', (m.LightKey(0, base.spec.lights.lights[0]), m.LightKey(1, light))),),
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((1, 2, 0), (0, 0, 360), 2)))
            ),
        ),
    )
    return m, base, motion


def test_sample_interpolates_shared_camera_lights_and_authored_full_turn():
    m, base, motion = motion_scene()
    sample = m.sample_scene(base.spec, base.bindings, motion, 0.5)
    assert sample.spec.camera.position == (1, 0, 10)
    assert sample.spec.camera.target == (1, 0, 0)
    assert sample.spec.lights.lights[0].intensity == 2
    assert sample.spec.layers[0].transform == c.Transform((0.5, 1, 0), (0, 0, 180), 1.5)
    assert sample == c.preflight(sample.spec, base.bindings)
    assert sample.digest != base.digest
    assert base.spec.layers[0].transform == c.Transform()


def test_sampling_is_random_access_and_does_not_retime_source_clocks():
    m, base, motion = motion_scene()
    times = (0, 0.125, 0.5, 0.875, 1)
    forward = {t: m.sample_scene(base.spec, base.bindings, motion, t) for t in times}
    for t in reversed(times):
        sample = m.sample_scene(base.spec, base.bindings, motion, t)
        assert sample == forward[t]
        assert sample.spec.layers[0].temporal == base.spec.layers[0].temporal


@pytest.mark.parametrize(
    'easing,value', [('linear', 0.25), ('smoothstep', 0.15625), ('smootherstep', 0.103515625), ('hold', 0)]
)
def test_outgoing_easing_is_explicit_with_exact_arrival(easing, value):
    m = api()
    base = plate_plan()
    keys = (m.TransformKey(0, c.Transform(), easing), m.TransformKey(1, c.Transform((1, 0, 0))))
    motion = m.SceneMotion(transforms=(m.TransformTrack('host', keys),))
    assert m.sample_scene(base.spec, base.bindings, motion, 0.25).spec.layers[0].transform.translation[0] == value
    assert m.sample_scene(base.spec, base.bindings, motion, 1).spec.layers[0].transform.translation == (1, 0, 0)


def test_parent_animation_composes_once_and_lights_remain_world_owned():
    m = api()
    base = plate_plan()
    parent = base.spec.layers[0]
    child = replace(parent, id='child', parent='host', transform=c.Transform((0.5, 0, 0)))
    spec = replace(base.spec, layers=(parent, child))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((1, 0, 0), (0, 0, 180))))
            ),
        )
    )
    sample = m.sample_scene(spec, base.bindings, motion, 0.5)
    view = c.plate_view(sample, 'child')
    assert view.point((0, 0, 0)) == pytest.approx((50, 50, 0))
    assert sample.spec.lights == base.spec.lights


def test_last_key_is_held_through_scene_end():
    m = api()
    base = plate_plan()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(0.5, c.Transform((1, 0, 0))))),
        )
    )
    assert m.sample_scene(base.spec, base.bindings, motion, 0.75) == m.sample_scene(base.spec, base.bindings, motion, 1)


def test_strict_roundtrip_and_immutable_records():
    m, base, motion = motion_scene()
    assert m.parse_motion(json.dumps(asdict(motion))) == motion
    assert m.parse_motion(asdict(motion)) == motion
    with pytest.raises(AttributeError):
        motion.camera = ()
    assert m.sample_scene(base.spec, base.bindings, m.SceneMotion(), 0.5) == base


@pytest.mark.parametrize(
    'bad', ['unknown', 'duplicate', 'schema', 'boolean', 'nonfinite', 'oversized', 'cycle', 'invalid-json']
)
def test_malformed_motion_is_a_typed_refusal(bad):
    m = api()
    value = asdict(m.SceneMotion())
    if bad == 'unknown':
        value['callback'] = 'run'
    elif bad == 'duplicate':
        value = '{"camera": [], "camera": []}'
    elif bad == 'schema':
        value['schema'] = 'srstudio.scene-motion/99.0.0'
    elif bad in ('boolean', 'nonfinite'):
        value['camera'] = [{'time': True if bad == 'boolean' else float('nan'), 'value': asdict(c.CameraSpec())}]
    elif bad == 'oversized':
        value = ' ' * (c.MAX_INPUT_BYTES + 1)
    elif bad == 'cycle':
        value['camera'] = value
    else:
        value = '{'
    with pytest.raises(c.CompositionError):
        m.parse_motion(value)


@pytest.mark.parametrize('time', [-0.1, 1.1, True, float('nan'), float('inf'), '0.5', 10**400])
def test_sample_time_is_finite_and_inside_scene(time):
    m, base, motion = motion_scene()
    with pytest.raises(c.CompositionError):
        m.sample_scene(base.spec, base.bindings, motion, time)


@pytest.mark.parametrize(
    'bad',
    ['empty', 'late-start', 'duplicate-time', 'backwards', 'past-end', 'initial', 'unknown-layer', 'duplicate-track'],
)
def test_transform_tracks_are_closed_ordered_and_start_at_the_base(bad):
    m = api()
    base = plate_plan()
    keys = (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((1, 0, 0))))
    if bad == 'empty':
        keys = ()
    elif bad == 'late-start':
        keys = (replace(keys[0], time=0.1), keys[1])
    elif bad == 'duplicate-time':
        keys = (keys[0], keys[0])
    elif bad == 'backwards':
        keys = tuple(reversed(keys))
    elif bad == 'past-end':
        keys = (keys[0], replace(keys[1], time=2))
    elif bad == 'initial':
        keys = (replace(keys[0], value=c.Transform((1, 0, 0))), keys[1])
    track = m.TransformTrack('missing' if bad == 'unknown-layer' else 'host', keys)
    motion = m.SceneMotion(transforms=(track, track) if bad == 'duplicate-track' else (track,))
    with pytest.raises(c.CompositionError):
        m.sample_scene(base.spec, base.bindings, motion, 0)


def test_camera_cannot_pass_through_its_target_at_the_sample_time():
    m = api()
    base = plate_plan()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, base.spec.camera), m.CameraKey(1, replace(base.spec.camera, position=(0, 0, -10))))
    )
    with pytest.raises(c.CompositionError, match='camera'):
        m.sample_scene(base.spec, base.bindings, motion, 0.5)


@pytest.mark.parametrize('field,value', [('projection', 'orthographic')])
def test_linear_camera_cannot_change_projection(field, value):
    m = api()
    base = plate_plan()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, base.spec.camera), m.CameraKey(1, replace(base.spec.camera, **{field: value})))
    )
    with pytest.raises(c.CompositionError):
        m.sample_scene(base.spec, base.bindings, motion, 0)


@pytest.mark.parametrize('field,value', [('color', '#FF0000'), ('kind', 'directional'), ('id', 'missing')])
def test_light_identity_and_discrete_changes_cannot_be_silently_interpolated(field, value):
    m = api()
    base = plate_plan()
    light = base.spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, **{field: value})))),)
    )
    with pytest.raises(c.CompositionError):
        m.sample_scene(base.spec, base.bindings, motion, 0)


def test_explicit_held_light_color_cut_is_supported():
    m = api()
    base = plate_plan()
    light = base.spec.lights.lights[0]
    red = replace(light, color='#FF0000')
    motion = m.SceneMotion(lights=(m.LightTrack('ambient', (m.LightKey(0, light, 'hold'), m.LightKey(0.5, red))),))
    assert m.sample_scene(base.spec, base.bindings, motion, 0.499).spec.lights.lights[0] == light
    assert m.sample_scene(base.spec, base.bindings, motion, 0.5).spec.lights.lights[0] == red


def test_motion_cannot_claim_continuous_contacts_for_independently_moving_anchors():
    m = api()
    base = plate_plan()
    other = replace(base.spec.layers[0], id='other')
    binding = replace(base.bindings[0], anchors=(c.Anchor('grip', (0, 0, 0)),))
    spec = replace(
        base.spec, layers=base.spec.layers + (other,), contacts=(c.ContactSpec('host', 'grip', 'other', 'grip', 0, 1),)
    )
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((1, 0, 0))))),
        )
    )
    with pytest.raises(c.CompositionError, match='contact'):
        m.sample_scene(spec, (binding,), motion, 0)


def test_common_rigid_parent_motion_preserves_continuous_contact_proof():
    m = api()
    base = plate_plan()
    parent = base.spec.layers[0]
    a = replace(parent, id='a', parent='host', transform=c.Transform((0.5, 0, 0)))
    b = replace(a, id='b')
    binding = replace(base.bindings[0], anchors=(c.Anchor('grip', (0, 0, 0)),))
    spec = replace(base.spec, layers=(parent, a, b), contacts=(c.ContactSpec('a', 'grip', 'b', 'grip', 0, 1),))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((1, 0, 0), (30, 60, 90))))
            ),
        )
    )
    for time in (0, 0.25, 0.5, 0.75, 1):
        assert m.sample_scene(spec, (binding,), motion, time).contacts_checked == 1


@pytest.mark.parametrize('time', [1 - 1e-8, 1 - 1e-10, 0.9999999999999999])
def test_smootherstep_near_arrival_cannot_overshoot_nonnegative_light_power(time):
    m = api()
    base = plate_plan()
    light = base.spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(
            m.LightTrack('ambient', (m.LightKey(0, light, 'smootherstep'), m.LightKey(1, replace(light, intensity=0)))),
        )
    )
    intensity = m.sample_scene(base.spec, base.bindings, motion, time).spec.lights.lights[0].intensity
    assert 0 <= intensity <= 1


@pytest.mark.parametrize(
    'bad',
    [
        'motion-type',
        'forged',
        'aggregate-keys',
        'unknown-light',
        'duplicate-light',
        'held-kind',
        'bad-color',
        'area-radius',
        'key-easing',
    ],
)
def test_adversarial_motion_is_refused_before_sampling_hidden_values(bad):
    m = api()
    base = plate_plan()
    light = base.spec.lights.lights[0]
    motion = m.SceneMotion()
    with pytest.raises(c.CompositionError):
        if bad == 'motion-type':
            motion = {}
        elif bad == 'forged':
            object.__setattr__(motion, 'camera', [])
        elif bad == 'aggregate-keys':
            keys = tuple(m.TransformKey(i / 599, c.Transform()) for i in range(600))
            motion = m.SceneMotion(transforms=(m.TransformTrack('host', keys), m.TransformTrack('child', keys)))
        elif bad == 'key-easing':
            m.TransformKey(0, c.Transform(), 'bounce')
        else:
            if bad == 'held-kind':
                changed = replace(light, kind='directional')
            elif bad == 'bad-color':
                changed = replace(light, color='white')
            elif bad == 'area-radius':
                light = replace(light, kind='sphere-area', radius=0.1)
                base = c.preflight(replace(base.spec, lights=c.LightRig('lit', (light,))), base.bindings)
                changed = replace(light, radius=0)
            else:
                changed = light
            track = m.LightTrack(
                'missing' if bad == 'unknown-light' else 'ambient',
                (m.LightKey(0, light, 'hold'), m.LightKey(1, changed)),
            )
            motion = m.SceneMotion(lights=(track, track) if bad == 'duplicate-light' else (track,))
        m.sample_scene(base.spec, base.bindings, motion, 0)


def test_common_scaling_cannot_claim_contact_tolerance_invariance():
    m = api()
    base = plate_plan()
    a = replace(base.spec.layers[0], id='a', parent='host')
    b = replace(a, id='b', transform=c.Transform((0.01, 0, 0)))
    spec = replace(
        base.spec, layers=(*base.spec.layers, a, b), contacts=(c.ContactSpec('a', 'grip', 'b', 'grip', 0, 1, 0.015),)
    )
    bindings = (replace(base.bindings[0], anchors=(c.Anchor('grip', (0, 0, 0)),)),)
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform(scale=2)))),
        )
    )
    with pytest.raises(c.CompositionError, match='contact'):
        m.sample_scene(spec, bindings, motion, 0)


def test_real_engine_sampled_views_change_pixels_and_reuse_warm_cache(scene_render, tmp_path):
    import numpy as np

    from srstudio._composition_png import decode
    from support.composition import plate_source, prepared_plate_plan

    m = api()
    source = plate_source()
    base = prepared_plate_plan(source)
    # This checks pixels and cache identity, not renderer latency. A cold
    # invocation exceeded 60 s in the combined suite; retain a finite GPU
    # integration budget without changing the SDK's default or timeout tests.
    base = c.preflight(replace(base.spec, budget=replace(base.spec.budget, timeout=120)), base.bindings)
    light = base.spec.lights.lights[0]
    motion = m.SceneMotion(
        camera=(
            m.CameraKey(0, base.spec.camera),
            m.CameraKey(1, replace(base.spec.camera, position=(0.05, 0, 10), target=(0.05, 0, 0))),
        ),
        lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, intensity=0.2)))),),
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.15, 0, 0), (0, 0, 45))))
            ),
        ),
    )
    results = {}
    for time in (0, 1, 0.5, 1, 0):
        sample = m.sample_scene(base.spec, base.bindings, motion, time)
        prepared = c.prepare_plate(sample, 'host', source)
        bundle = c.compile_bundle(sample, (prepared,), engine=scene_render, cache=tmp_path / 'cache')
        if time in results:
            assert bundle.work == c.BundleWork(0, 1, 0)
            assert (bundle.xml, bundle.resources, bundle.digest) == (
                results[time].xml,
                results[time].resources,
                results[time].digest,
            )
        else:
            assert bundle.work == c.BundleWork(1, 0, 1)
            results[time] = bundle
    images = [decode(results[t].resources[0].data, 64, 64) for t in (0, 0.5, 1)]
    centers = [np.nonzero(image[..., 3] > 127)[1].mean() for image in images]
    assert centers[2] > centers[1] > centers[0] + 2
    colors = [image[image[..., 3] == 255, :3].mean() for image in images]
    assert colors[0] > colors[1] > colors[2]
    assert len({result.resources[0].data for result in results.values()}) == 3


def test_documented_scene_motion_example_executes():
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = guide.split('## Sample shared scene motion\n', 1)[1]
    snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
    namespace = {}
    exec(compile(snippet, '<scene-motion-guide>', 'exec'), namespace)
    assert namespace['sample'].spec.layers[0].transform.rotation == (0, 0, 180)
    assert namespace['sample'].spec.camera.position == (0.05, 0, 10)


def test_sample_recomputes_distinct_placement_work_and_enforces_its_budget():
    m = api()
    base = plate_plan()
    child = replace(base.spec.layers[0], id='child')
    spec = replace(base.spec, layers=(*base.spec.layers, child))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('child', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.1, 0, 0))))),
        )
    )
    assert m.sample_scene(spec, base.bindings, motion, 0).cost.unique_plates == 1
    assert m.sample_scene(spec, base.bindings, motion, 1).cost.unique_plates == 2
    restricted = replace(spec, budget=replace(spec.budget, max_new_plates=1))
    with pytest.raises(c.CompositionError, match='max_new_plates'):
        m.sample_scene(restricted, base.bindings, motion, 1)


@pytest.mark.parametrize('easing,order', [('smoothstep', 1), ('smootherstep', 2)])
def test_eased_numeric_channels_have_the_documented_endpoint_derivatives(easing, order):
    m = api()
    base = plate_plan()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform(), easing), m.TransformKey(1, c.Transform((1, 0, 0))))
            ),
        )
    )

    def position(t):
        return m.sample_scene(base.spec, base.bindings, motion, t).spec.layers[0].transform.translation[0]

    h = 1e-4
    assert abs((position(h) - position(0)) / h) < 0.001
    assert abs((position(1) - position(1 - h)) / h) < 0.001
    if order == 2:
        assert abs((position(2 * h) - 2 * position(h) + position(0)) / h**2) < 0.01
        assert abs((position(1) - 2 * position(1 - h) + position(1 - 2 * h)) / h**2) < 0.01


@pytest.mark.parametrize('time', [0.004, 0.024, 0.059])
def test_unchanged_channels_are_bit_exact_even_at_numeric_limits(time):
    m = api()
    base = plate_plan()
    light = replace(base.spec.lights.lights[0], intensity=1e6, position=(7, 0, 0))
    transform = c.Transform(scale=1e-6)
    spec = replace(
        base.spec, lights=c.LightRig('lit', (light,)), layers=(replace(base.spec.layers[0], transform=transform),)
    )
    motion = m.SceneMotion(
        lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, yaw=10)))),),
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, transform), m.TransformKey(1, replace(transform, translation=(0.1, 0, 0))))
            ),
        ),
    )
    sample = m.sample_scene(spec, base.bindings, motion, time)
    assert sample.spec.layers[0].transform.scale == 1e-6
    assert sample.spec.lights.lights[0].intensity == 1e6
    assert sample.spec.lights.lights[0].position == (7, 0, 0)


def test_redundant_keys_preserve_the_static_plan_identity():
    m = api()
    base = plate_plan()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, base.spec.camera), m.CameraKey(1, base.spec.camera)),
        lights=(
            m.LightTrack(
                'ambient', (m.LightKey(0, base.spec.lights.lights[0]), m.LightKey(1, base.spec.lights.lights[0]))
            ),
        ),
        transforms=(m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform()))),),
    )
    assert m.sample_scene(base.spec, base.bindings, motion, 0.37) == base
