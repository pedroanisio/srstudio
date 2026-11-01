"""Scene-wide contracts reject unsupported work before drawing or touching a cache."""

import importlib
import json
from dataclasses import FrozenInstanceError, asdict, replace

import pytest


def api():
    return importlib.import_module('srstudio.composition')


def scene():
    c = api()
    return c.ScenePlan(
        style=c.StylePin('cutout', c.style_revision('cutout')),
        width=320,
        height=240,
        fps=c.FrameRate(24, 1),
        duration=1,
        seed=17,
        world_unit='meter',
        camera=c.CameraSpec(),
        lights=c.LightRig('flat'),
        layers=(c.LayerSpec('paper', 'paper-asset', 1, c.TemporalPolicy(0, 1)),),
        budget=c.RenderBudget(),
    )


def bindings():
    c = api()
    return (
        c.AssetBinding(
            'paper-asset',
            'papers',
            1,
            'vector',
            c.Bounds((-0.5, -0.5, 0), (0.5, 0.5, 0)),
            anchors=(c.Anchor('origin', (0, 0, 0)),),
            nodes=100,
            memory_bytes=65536,
        ),
    )


def test_typed_plan_and_strict_json_produce_the_same_immutable_estimate():
    c = api()
    spec = scene()
    parsed = c.parse_scene(json.dumps(asdict(spec)))
    assert parsed == spec
    first = c.preflight(spec, bindings())
    assert c.preflight(parsed, bindings()) == first
    assert first.cost.frames == 24
    assert first.cost.frame_pixels == 320 * 240
    assert first.cost.output_pixels == 24 * 320 * 240
    assert first.cost.unique_plates == first.cost.engine_invocations == 0
    assert first.cost.nodes >= 100
    assert len(first.digest) == 64
    with pytest.raises(FrozenInstanceError):
        first.cost.frames = 25
    with pytest.raises(FrozenInstanceError):
        first.spec.layers[0].id = 'changed'


@pytest.mark.parametrize('where', ['root', 'camera', 'layer', 'time', 'budget'])
def test_unknown_fields_are_refused_at_every_record_boundary(where):
    c = api()
    value = asdict(scene())
    target = {
        'root': value,
        'camera': value['camera'],
        'layer': value['layers'][0],
        'time': value['layers'][0]['temporal'],
        'budget': value['budget'],
    }[where]
    target['surprise'] = True
    with pytest.raises(c.CompositionError) as caught:
        c.parse_scene(json.dumps(value))
    assert caught.value.to_dict()['code'] == 'composition.input'
    assert 'surprise' in caught.value.to_dict()['path']


@pytest.mark.parametrize('change', ['nan', 'boolean', 'missing', 'duplicate', 'too-big'])
def test_malformed_json_and_numeric_inputs_are_typed_refusals(change):
    c = api()
    value = asdict(scene())
    if change == 'nan':
        value['duration'] = float('nan')
    elif change == 'boolean':
        value['width'] = True
    elif change == 'missing':
        del value['world_unit']
    text = json.dumps(value)
    if change == 'duplicate':
        text = text.replace('"width": 320', '"width": 1, "width": 320')
    elif change == 'too-big':
        text = ' ' * (c.MAX_INPUT_BYTES + 1)
    with pytest.raises(c.CompositionError):
        c.parse_scene(text)


@pytest.mark.parametrize('change', ['missing-asset', 'version', 'style', 'duplicate-layer', 'duplicate-binding'])
def test_references_versions_and_ids_resolve_before_work(change):
    c = api()
    spec, assets = scene(), bindings()
    layer = spec.layers[0]
    if change == 'missing-asset':
        spec = replace(spec, layers=(replace(layer, asset='missing'),))
    elif change == 'version':
        spec = replace(spec, layers=(replace(layer, version=2),))
    elif change == 'style':
        spec = replace(spec, style=replace(spec.style, revision='0' * 64))
    elif change == 'duplicate-layer':
        spec = replace(spec, layers=(layer, layer))
    else:
        assets = assets * 2
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, assets)
    assert caught.value.to_dict()['path']


def test_unverified_builder_cannot_borrow_approved_version_metadata(monkeypatch):
    c = api()
    from srstudio import registry

    entry = registry.get('prop', 'papers')
    monkeypatch.setattr(entry, 'builder', lambda *args, **kwargs: pytest.fail('must not draw'))
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(scene(), bindings())
    assert caught.value.to_dict()['code'] == 'composition.version'
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize(
    'field,value', [('max_frames', 23), ('max_output_pixels', 100), ('max_nodes', 1), ('max_memory_bytes', 1)]
)
def test_declared_budgets_refuse_excessive_work(field, value):
    c = api()
    spec = scene()
    spec = replace(spec, budget=replace(spec.budget, **{field: value}))
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, bindings())
    assert caught.value.to_dict()['code'] == 'composition.budget'
    assert field in caught.value.to_dict()['path']


def test_fractional_frame_rate_has_exact_frame_boundaries():
    c = api()
    spec = replace(scene(), fps=c.FrameRate(30000, 1001), duration=1.001)
    assert c.preflight(spec, bindings()).cost.frames == 30


def test_camera_near_plane_and_unsupported_vector_views_refuse():
    c = api()
    spec = scene()
    layer = spec.layers[0]
    for transform in (c.Transform(translation=(0, 0, 10)), c.Transform(rotation=(0, 90, 0))):
        with pytest.raises(c.CompositionError):
            c.preflight(replace(spec, layers=(replace(layer, transform=transform),)), bindings())


def test_contact_references_and_world_alignment_are_checked():
    c = api()
    spec = scene()
    second = replace(spec.layers[0], id='second')
    contact = c.ContactSpec('paper', 'origin', 'second', 'origin', 0, 1, 0.001)
    spec = replace(spec, layers=(*spec.layers, second), contacts=(contact,))
    assert c.preflight(spec, bindings()).contacts_checked == 1
    moved = replace(second, transform=c.Transform(translation=(1, 0, 0)))
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(replace(spec, layers=(spec.layers[0], moved)), bindings())
    assert caught.value.to_dict()['code'] == 'composition.contact'
    with pytest.raises(c.CompositionError):
        c.preflight(replace(spec, contacts=(replace(contact, target_anchor='missing'),)), bindings())


def test_information_cannot_receive_world_effects_or_be_under_picture_layers():
    c = api()
    spec = scene()
    info = replace(spec.layers[0], id='info', role='information', effects=('grain',))
    with pytest.raises(c.CompositionError):
        c.preflight(replace(spec, layers=(spec.layers[0], info)), bindings())
    info = replace(info, effects=())
    with pytest.raises(c.CompositionError):
        c.preflight(replace(spec, layers=(info, spec.layers[0])), bindings())


def test_unsupported_passes_shadows_and_shared_lighting_are_not_dropped():
    c = api()
    spec = scene()
    layer = spec.layers[0]
    bad = [
        replace(spec, layers=(replace(layer, passes=('depth',)),)),
        replace(spec, layers=(replace(layer, shadow_receiver='paper'),)),
        replace(spec, lights=c.LightRig('lit', (c.LightSpec('key', 'directional', '#ffffff', 1),))),
    ]
    for value in bad:
        with pytest.raises(c.CompositionError) as caught:
            c.preflight(value, bindings())
        assert caught.value.to_dict()['code'] == 'composition.capability'


def test_plate_work_is_deduplicated_and_all_render_limits_are_accounted_for():
    c = api()
    spec = scene()
    job = c.PlateWork('a' * 64, 64, 64, 48, 4, 1, 1048576)
    asset = replace(bindings()[0], backend='plates', plates=(job,), nodes=1)
    spec = replace(spec, layers=(*spec.layers, replace(spec.layers[0], id='second')))
    plan = c.preflight(spec, (asset,))
    assert plan.cost.unique_plates == plan.cost.engine_invocations == 1
    assert plan.cost.samples == 64 * 64 * 48
    assert plan.cost.bounces == 4
    for field in ('max_new_plates', 'max_engine_invocations', 'max_samples', 'max_bounces'):
        with pytest.raises(c.CompositionError) as caught:
            c.preflight(replace(spec, budget=replace(spec.budget, **{field: 0})), (asset,))
        assert caught.value.to_dict()['code'] == 'composition.budget'


def test_preflight_never_calls_drawing_builders_or_creates_files(tmp_path, monkeypatch):
    c = api()
    from srstudio import drawing_events

    monkeypatch.setattr(drawing_events, 'call', lambda *a, **k: pytest.fail('preflight must not draw'))
    monkeypatch.chdir(tmp_path)
    c.preflight(scene(), bindings())
    assert list(tmp_path.iterdir()) == []


def test_contact_sampling_is_bounded_before_evaluating_anchor_positions(monkeypatch):
    c = api()
    import srstudio._composition_preflight as implementation

    spec = scene()
    actor = replace(spec.layers[0], id='actor')
    contact = c.ContactSpec('paper', 'origin', 'actor', 'origin', 0, 1)
    spec = replace(spec, layers=(*spec.layers, actor), contacts=(contact,))
    spec = replace(spec, budget=replace(spec.budget, max_contact_samples=1))
    monkeypatch.setattr(implementation, '_anchor', lambda *args: pytest.fail('budget must be checked first'))
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, bindings())
    assert caught.value.to_dict()['code'] == 'composition.budget'


def test_screen_information_is_independent_of_the_world_camera():
    c = api()
    spec = scene()
    info = replace(spec.layers[0], id='info', role='information', space='screen')
    # The world lens is pointed away from the information; a screen overlay has no world near plane.
    camera = replace(spec.camera, position=(0, 0, -10), target=(0, 0, -20))
    result = c.preflight(replace(spec, camera=camera, layers=(info,)), bindings())
    assert result.spec.layers[0].space == 'screen'


def test_continuous_windows_preserve_source_clock_and_parent_pose():
    c = api()
    spec = scene()
    first = replace(spec.layers[0], temporal=c.TemporalPolicy(0, 0.5, state='same'))
    second = replace(first, id='later', temporal=c.TemporalPolicy(0.5, 1, 0.5, continuity='continuous', state='same'))
    assert c.preflight(replace(spec, layers=(first, second)), bindings())
    for time in (replace(second.temporal, source_start=0), replace(second.temporal, rate=2)):
        with pytest.raises(c.CompositionError) as caught:
            c.preflight(replace(spec, layers=(first, replace(second, temporal=time))), bindings())
        assert caught.value.to_dict()['code'] == 'composition.clock'


def test_parent_cycles_and_missing_coordinate_frames_are_refused():
    c = api()
    spec = scene()
    for parent in ('paper', 'missing'):
        with pytest.raises(c.CompositionError) as caught:
            c.preflight(replace(spec, layers=(replace(spec.layers[0], parent=parent),)), bindings())
        assert caught.value.to_dict()['code'] == 'composition.reference'


def test_linear_contact_checks_interior_keys_not_only_endpoints():
    c = api()
    spec = scene()
    actor = replace(spec.layers[0], id='actor', asset='moving')
    anchor = c.Anchor(
        'origin', (0, 0, 0), (c.AnchorKey(0, (0, 0, 0)), c.AnchorKey(0.5, (1, 0, 0)), c.AnchorKey(1, (0, 0, 0)))
    )
    moving = replace(bindings()[0], id='moving', duration=1, anchors=(anchor,))
    contact = c.ContactSpec('paper', 'origin', 'actor', 'origin', 0, 1, 0.01)
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(replace(spec, layers=(*spec.layers, actor), contacts=(contact,)), (*bindings(), moving))
    assert caught.value.to_dict()['code'] == 'composition.contact'
    assert '@0.5' in caught.value.to_dict()['path']


def test_dictionary_input_has_a_total_text_budget_and_rejects_cycles():
    c = api()
    cyclic = {}
    cyclic['child'] = cyclic
    many_keys = {str(i): {('x' * 120) + str(j): 0 for j in range(100)} for i in range(100)}
    for value in (cyclic, {'layers': ['x' * 4096] * 1024}, many_keys):
        with pytest.raises(c.CompositionError) as caught:
            c.parse_scene(value)
        assert caught.value.to_dict()['path'] == 'scene'


@pytest.mark.parametrize('value', ['\ud800', '{"unknown":"\\ud800"}', {'unknown': '\ud800'}])
def test_invalid_unicode_is_a_typed_parse_failure(value):
    c = api()
    with pytest.raises(c.CompositionError):
        c.parse_scene(value)


def test_screen_and_world_coordinates_cannot_be_used_as_one_contact_space():
    c = api()
    spec = scene()
    info = replace(spec.layers[0], id='info', space='screen', role='information')
    contact = c.ContactSpec('paper', 'origin', 'info', 'origin', 0, 1)
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(replace(spec, layers=(*spec.layers, info), contacts=(contact,)), bindings())
    assert caught.value.to_dict()['code'] == 'composition.contact'


def test_parent_scale_and_rotation_apply_once_to_contact_anchors():
    c = api()
    spec = scene()
    parent = replace(spec.layers[0], transform=c.Transform((3, 2, 0), (0, 0, 90), 2))
    child = replace(spec.layers[0], id='child', parent='paper', transform=c.Transform((1, 0, 0)))
    target = replace(spec.layers[0], id='target', transform=c.Transform((3, 4, 0)))
    contact = c.ContactSpec('child', 'origin', 'target', 'origin', 0, 1)
    result = c.preflight(replace(spec, layers=(parent, child, target), contacts=(contact,)), bindings())
    assert result.cost.contact_samples == 2


def test_matching_linear_anchors_preserve_offset_source_clocks_and_endpoint_holds():
    c = api()
    spec = scene()
    anchor = c.Anchor(
        'origin', (0, 0, 0), (c.AnchorKey(0, (0, 0, 0)), c.AnchorKey(0.5, (1, 0, 0)), c.AnchorKey(0.75, (2, 0, 0)))
    )
    assets = (replace(bindings()[0], duration=1, anchors=(anchor,)),)
    first = replace(spec.layers[0], temporal=c.TemporalPolicy(0, 0.75, 0.25))
    second = replace(first, id='second')
    contact = c.ContactSpec('paper', 'origin', 'second', 'origin', 0, 0.75)
    result = c.preflight(replace(spec, layers=(first, second), contacts=(contact,)), assets)
    assert result.cost.contact_samples == 4


@pytest.mark.parametrize(
    'factory',
    [
        lambda c: c.FrameRate(True, 1),
        lambda c: c.FrameRate(24, 0),
        lambda c: c.Transform(translation=[0, 0, 0]),
        lambda c: c.Transform(scale=0),
        lambda c: c.Transform(rotation=(0, 0)),
        lambda c: c.CameraSpec(projection='panoramic'),
        lambda c: c.CameraSpec(near=float('nan')),
        lambda c: c.LayerSpec('id', 'ref', 1, {}),
        lambda c: c.StylePin('cutout', 'a' * 4097),
    ],
)
def test_direct_records_refuse_mutable_untyped_and_nonfinite_fields(factory):
    c = api()
    with pytest.raises(c.CompositionError):
        factory(c)


@pytest.mark.parametrize(
    'case',
    [
        'empty-layers',
        'odd-frame',
        'fps',
        'camera-self',
        'camera-axis',
        'flat-lights',
        'empty-lit',
        'light-color',
        'light-radius',
        'source-duration',
        'reverse-bounds',
        'anchor-initial',
        'anchor-order',
        'vector-jobs',
        'plate-no-jobs',
        'plate-key',
        'conflicting-jobs',
        'source-end',
        'layer-interval',
        'empty-passes',
        'receiver-missing',
        'intersection-missing',
        'intersection-unsupported',
        'split',
        'contact-layer',
        'contact-interval',
        'contact-outside',
        'state-overlap',
        'state-asset',
        'state-placement',
    ],
)
def test_semantic_failures_are_actionable_and_leave_the_input_unchanged(case):
    c = api()
    spec, assets = scene(), bindings()
    layer, asset = spec.layers[0], assets[0]
    job = c.PlateWork('a' * 64, 64, 64, 48, 4, 1, 1024)
    if case == 'empty-layers':
        spec = replace(spec, layers=())
    elif case == 'odd-frame':
        spec = replace(spec, width=321)
    elif case == 'fps':
        spec = replace(spec, fps=c.FrameRate(121, 1))
    elif case == 'camera-self':
        spec = replace(spec, camera=replace(spec.camera, position=(0, 0, 0)))
    elif case == 'camera-axis':
        spec = replace(spec, camera=replace(spec.camera, position=(0, 10, 0)))
    elif case == 'flat-lights':
        spec = replace(spec, lights=c.LightRig('flat', (c.LightSpec('key', 'ambient', '#ffffff', 1),)))
    elif case == 'empty-lit':
        spec = replace(spec, lights=c.LightRig('lit'))
    elif case == 'light-color':
        spec = replace(spec, lights=c.LightRig('lit', (c.LightSpec('key', 'ambient', 'red', 1),)))
    elif case == 'light-radius':
        spec = replace(spec, lights=c.LightRig('lit', (c.LightSpec('key', 'sphere-area', '#ffffff', 1),)))
    elif case == 'source-duration':
        assets = (replace(asset, duration=-1),)
    elif case == 'reverse-bounds':
        assets = (replace(asset, bounds=c.Bounds((1, 0, 0), (0, 0, 0))),)
    elif case == 'anchor-initial':
        assets = (replace(asset, duration=1, anchors=(c.Anchor('origin', (0, 0, 0), (c.AnchorKey(0.1, (0, 0, 0)),)),)),)
    elif case == 'anchor-order':
        assets = (
            replace(
                asset,
                duration=1,
                anchors=(c.Anchor('origin', (0, 0, 0), (c.AnchorKey(0, (0, 0, 0)), c.AnchorKey(0, (0, 0, 0)))),),
            ),
        )
    elif case == 'vector-jobs':
        assets = (replace(asset, plates=(job,)),)
    elif case == 'plate-no-jobs':
        assets = (replace(asset, backend='plates'),)
    elif case == 'plate-key':
        assets = (replace(asset, backend='plates', plates=(replace(job, key='wrong'),)),)
    elif case == 'conflicting-jobs':
        assets = (replace(asset, backend='plates', plates=(job, replace(job, samples=32))),)
    elif case == 'source-end':
        assets = (replace(asset, duration=0.5),)
    elif case == 'layer-interval':
        spec = replace(spec, layers=(replace(layer, temporal=c.TemporalPolicy(0.5, 0.5)),))
    elif case == 'empty-passes':
        spec = replace(spec, layers=(replace(layer, passes=()),))
    elif case == 'receiver-missing':
        spec = replace(spec, layers=(replace(layer, shadow_receiver='absent'),))
    elif case == 'intersection-missing':
        spec = replace(spec, layers=(replace(layer, intersects=('absent',)),))
    elif case == 'intersection-unsupported':
        spec = replace(spec, layers=(replace(layer, intersects=('other',)), replace(layer, id='other')))
    elif case == 'split':
        spec = replace(spec, layers=(replace(layer, depth='split'),))
    elif case.startswith('contact'):
        contact = c.ContactSpec('paper', 'origin', 'paper', 'origin', 0, 1)
        if case == 'contact-layer':
            contact = replace(contact, target='missing')
        elif case == 'contact-interval':
            contact = replace(contact, start=0.5, end=0.5)
        else:
            spec = replace(spec, layers=(replace(layer, temporal=c.TemporalPolicy(0.5, 1)),))
        spec = replace(spec, contacts=(contact,))
    else:
        first = replace(layer, temporal=c.TemporalPolicy(0, 0.5, state='same'))
        second = replace(
            layer, id='second', temporal=c.TemporalPolicy(0.5, 1, 0.5, state='same', continuity='continuous')
        )
        if case == 'state-overlap':
            second = replace(second, temporal=replace(second.temporal, start=0.25))
        elif case == 'state-asset':
            assets = (*assets, replace(asset, id='other'))
            second = replace(second, asset='other')
        else:
            second = replace(second, transform=c.Transform(translation=(1, 0, 0)))
        spec = replace(spec, layers=(first, second))
    before = asdict(spec), [asdict(a) for a in assets]
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, assets)
    assert caught.value.to_dict()['path'] and caught.value.to_dict()['remedy']
    assert (asdict(spec), [asdict(a) for a in assets]) == before
