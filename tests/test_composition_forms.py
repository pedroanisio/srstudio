"""Authored vector surfaces respond to the shared light rig and source clock."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m


def form(*, animated=False):
    keys = (c.FormKey(0, (0, 0, 0), (0, 0, 1)), c.FormKey(0.5, (0, 0, 0), (0, 0, -1))) if animated else ()
    surfaces = (c.FormSurface('face', ('#000000', '#ffffff'), keys=keys),)
    source = c.VectorSource(
        'face',
        b'<scene version="1.1"><project width="64" height="64" fps="4" duration="1"/>'
        b'<composition><shape id="face" shape="rect" x="-10" y="-10" width="20" height="20" '
        b'fill="#ffffff"/></composition></scene>',
    )
    binding = c.AssetBinding(
        'face',
        'candidate.lit-face',
        1,
        'vector',
        c.Bounds((-10, -10, 0), (10, 10, 0)),
        nodes=16,
        memory_bytes=65536,
        duration=1,
        forms=surfaces,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=surfaces)),
    )
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(4),
        1,
        7,
        'meter',
        c.CameraSpec(origin=(32, 32), scale=1),
        c.LightRig('lit', (c.LightSpec('key', 'directional', '#ffffff', 1, yaw=180),)),
        (c.LayerSpec('face', 'face', 1, c.TemporalPolicy(0, 1)),),
        c.RenderBudget(),
    )
    return c.preflight(spec, (binding,), purpose='candidate-review'), source


def test_static_form_is_lit_from_shared_world_direction():
    plan, source = form()
    sample = c.form_lighting(plan, 'face', 0)[0]
    assert sample.color == '#ffffff'
    assert sample.normal == pytest.approx((0, 0, 1))
    assert sample.irradiance == pytest.approx((1, 1, 1))
    compiled = c.compile_scene(plan, (source,))
    assert ET.fromstring(compiled.xml).find('.//shape').get('fill') == '#ffffff'
    spec = replace(plan.spec, lights=c.LightRig('lit', (replace(plan.spec.lights.lights[0], yaw=0),)))
    dark = c.preflight(spec, plan.bindings, purpose=plan.purpose)
    assert c.form_lighting(dark, 'face', 0)[0].color == '#000000'
    assert ET.fromstring(c.compile_scene(dark, (source,)).xml).find('.//shape').get('fill') == '#000000'


def test_source_pose_keys_and_shared_light_cuts_enter_timeline(tmp_path):
    plan, source = form(animated=True)
    timeline = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
    assert 0.5 in {span.start for span in timeline.spans}
    result = m.compile_timeline(timeline, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    root = ET.fromstring(result.xml)
    samples = [
        (float(group.get('start')), group.find('.//shape').get('fill')) for group in root.findall('composition/group')
    ]
    assert samples[0] == (0, '#ffffff')
    assert next(color for time, color in samples if time == 0.5) == '#000000'
    assert result.work == c.BundleWork(0, 0, 0)
    assert not (tmp_path / 'cache').exists()


def test_static_emission_refuses_unsampled_form_motion_before_publication(tmp_path):
    plan, source = form(animated=True)
    with pytest.raises(c.CompositionError, match='compile_timeline'):
        c.emit_bundle(plan, (source,), tmp_path / 'out', engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    assert list(tmp_path.iterdir()) == []


def test_parent_rotation_folds_into_normals_once():
    plan, source = form()
    forms = (replace(plan.bindings[0].forms[0], normal=(1, 0, 0)),)
    binding = replace(
        plan.bindings[0], forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    parent = replace(plan.spec.layers[0], id='parent', transform=c.Transform(rotation=(0, 0, 90)))
    layer = replace(plan.spec.layers[0], parent='parent', transform=c.Transform(rotation=(0, 0, 90)))
    lights = c.LightRig('lit', (replace(plan.spec.lights.lights[0], yaw=-90),))
    turned = c.preflight(replace(plan.spec, lights=lights, layers=(parent, layer)), (binding,), purpose=plan.purpose)
    assert c.form_lighting(turned, 'face', 0)[0].normal == pytest.approx((-1, 0, 0))
    assert c.form_lighting(turned, 'face', 0)[0].color == '#000000'


@pytest.mark.parametrize('bad', ['missing', 'unknown', 'palette', 'normal', 'clock', 'pin', 'information'])
def test_invalid_form_contracts_do_not_reach_output(tmp_path, bad):
    plan, source = form()
    binding = plan.bindings[0]
    surface = binding.forms[0]
    if bad == 'missing':
        binding = replace(binding, forms=())
    elif bad == 'unknown':
        binding = replace(binding, forms=(replace(surface, node='unknown'),))
        binding = replace(
            binding, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=binding.forms))
        )
    elif bad == 'palette':
        binding = replace(binding, forms=(replace(surface, palette=('red',)),))
    elif bad == 'normal':
        binding = replace(binding, forms=(replace(surface, normal=(0, 0, 0)),))
    elif bad == 'clock':
        binding = replace(binding, forms=(replace(surface, keys=(c.FormKey(2, (0, 0, 0), (0, 0, 1)),)),))
    elif bad == 'pin':
        binding = replace(binding, forms=(replace(surface, palette=('#ff0000', '#00ff00')),))
    else:
        plan = replace(
            plan, spec=replace(plan.spec, layers=(replace(plan.spec.layers[0], role='information', space='screen'),))
        )
    with pytest.raises(c.CompositionError):
        checked = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
        c.emit_bundle(checked, (source,), tmp_path / 'out', engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('timeline', [False, True])
def test_source_buffer_budget_includes_authored_surface_metadata(tmp_path, monkeypatch, timeline):
    from srstudio import _composition_bundle as bundle

    plan, source = form()
    monkeypatch.setattr(bundle, 'MAX_BYTES', len(source.xml))

    def forbidden(*args, **kwargs):
        pytest.fail('aggregate source limit must fail before a worker starts')

    monkeypatch.setattr(c, 'prepare_vector', forbidden)
    with pytest.raises(c.CompositionError):
        if timeline:
            planned = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
            m.compile_timeline(planned, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
        else:
            c.compile_bundle(plan, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')


def test_form_event_expansion_is_bounded_before_allocating_a_long_timeline():
    from srstudio._composition_forms import events

    plan, _ = form()
    surface = replace(
        plan.bindings[0].forms[0],
        keys=(c.FormKey(0, (0, 0, 0), (0, 0, 1), 'linear'), c.FormKey(600, (1, 0, 0), (0, 0, 1))),
    )
    binding = replace(plan.bindings[0], duration=600, forms=(surface,))
    layer = replace(plan.spec.layers[0], temporal=c.TemporalPolicy(0, 600))
    with pytest.raises(c.CompositionError, match='4096'):
        events(binding, layer, c.FrameRate(120))


def test_linear_pose_sampling_is_normalized_and_order_independent():
    plan, source = form()
    surface = replace(
        plan.bindings[0].forms[0],
        keys=(c.FormKey(0, (0, 0, 0), (0, 0, 1), 'linear'), c.FormKey(1, (1, 0, 0), (1, 0, 0))),
    )
    binding = replace(
        plan.bindings[0],
        forms=(surface,),
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=(surface,))),
    )
    plan = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    expected = c.form_lighting(plan, 'face', 0.5)[0]
    assert expected.point == pytest.approx((0.5, 0, 0))
    assert expected.normal == pytest.approx((2**-0.5, 0, 2**-0.5))
    c.form_lighting(plan, 'face', 1)
    c.form_lighting(plan, 'face', 0)
    assert c.form_lighting(plan, 'face', 0.5)[0] == expected


def test_ambient_color_and_sphere_area_size_affect_the_authored_palette():
    plan, source = form()
    surface = replace(plan.bindings[0].forms[0], palette=('#000000', '#ff0000', '#ffffff'))
    binding = replace(
        plan.bindings[0],
        forms=(surface,),
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=(surface,))),
    )
    rig = c.LightRig('lit', (c.LightSpec('ambient', 'ambient', '#ff0000', 1),))
    red = c.preflight(replace(plan.spec, lights=rig), (binding,), purpose=plan.purpose)
    assert c.form_lighting(red, 'face', 0)[0].color == '#ff0000'
    rig = c.LightRig('lit', (c.LightSpec('area', 'sphere-area', '#ffffff', 4, (0, 0, 2), radius=1),))
    bright = c.preflight(replace(plan.spec, lights=rig), (binding,), purpose=plan.purpose)
    assert c.form_lighting(bright, 'face', 0)[0].irradiance == pytest.approx((1, 1, 1))
    rig = replace(rig, lights=(replace(rig.lights[0], radius=0.5),))
    dim = c.preflight(replace(plan.spec, lights=rig), (binding,), purpose=plan.purpose)
    assert c.form_lighting(dim, 'face', 0)[0].irradiance == pytest.approx((0.25, 0.25, 0.25))


@pytest.mark.parametrize('value', [None, [], False, {}, [1]])
def test_form_source_hash_refuses_untyped_recipe_containers(value):
    _, source = form()
    with pytest.raises(c.CompositionError):
        c.vector_source_digest(source, forms=value)


def test_timeline_preserves_nonzero_source_clock_through_light_cut_and_pixels(tmp_path, scene_render):
    from PIL import Image

    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    plan, source = form(animated=True)
    layer = replace(plan.spec.layers[0], temporal=c.TemporalPolicy(0.25, 1, 0.125))
    information = c.VectorSource(
        'info',
        source.xml.replace(b'x="-10" y="-10" width="20" height="20"', b'x="0" y="0" width="8" height="8"').replace(
            b'#ffffff', b'#00ff00'
        ),
    )
    info_binding = replace(
        plan.bindings[0],
        id='info',
        part='candidate.info',
        forms=(),
        bounds=c.Bounds((0, 0, 0), (8, 8, 0)),
        candidate=c.CandidateSource('toon', c.vector_source_digest(information)),
    )
    info_layer = c.LayerSpec('info', 'info', 1, c.TemporalPolicy(0, 1), role='information', space='screen')
    spec = replace(plan.spec, layers=(layer, info_layer))
    light = spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(m.LightTrack('key', (m.LightKey(0, light, 'hold'), m.LightKey(0.8, replace(light, yaw=0), 'hold'))),)
    )
    timeline = m.plan_scene(spec, (*plan.bindings, info_binding), motion, purpose=plan.purpose)
    result = m.emit_timeline(
        timeline, (source, information), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache'
    )
    assert result.work == c.BundleWork(0, 0, 0)
    assert {0.625, 0.8} <= {span.start for span in timeline.spans}
    observed = {}
    for time, expected in ((0.8, 255), (0.25, 255), (0.625, 0), (0.4, 255), (0.8, 255)):
        output = tmp_path / f'frame-{time}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'bundle/scene.xml'),
                    '--time',
                    str(time),
                    '--output',
                    str(output),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536),
            )
        with Image.open(output) as picture:
            rgba = picture.convert('RGBA')
            assert rgba.getpixel((32, 32)) == (expected, expected, expected, 255)
            assert rgba.getpixel((4, 4)) == (0, 255, 0, 255)
            if time in observed:
                assert rgba.tobytes() == observed[time]
            observed[time] = rgba.tobytes()


def test_ink_fields_keep_authored_brush_crescents():
    from sr_core.scene import Scene

    from srstudio import Canvas, brush

    plan, _ = form()
    scene = Scene(version='auto')
    scene.add_project(width=64, height=64, fps='4', duration=1)
    cv = Canvas(scene, width=64, height=64, font_asset=None)
    crescent = brush.crescent(((-8, -8), (0, -10), (8, -8)), 2, (0, 0))
    data = 'M ' + ' L '.join(f'{x} {y}' for x, y in crescent) + ' Z'
    node = cv.path(cv.comp, data, fill='#804020', stroke='#111111', sw=1)
    source = c.VectorSource('face', scene.to_bytes())
    fields = (c.FormSurface(node.id, mode='ink'),)
    binding = replace(
        plan.bindings[0],
        nodes=32,
        bounds=c.Bounds((-20, -20, 0), (20, 20, 0)),
        forms=fields,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=fields)),
    )
    plan = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    assert c.form_lighting(plan, 'face', 0)[0].color is None
    compiled = c.compile_scene(plan, (source,))
    shape = ET.fromstring(compiled.xml).find('.//shape')
    assert shape.get('fill') == '#804020' and shape.get('stroke') == '#111111'


@pytest.mark.parametrize(
    'bad',
    [
        'duplicate',
        'albedo',
        'ink-palette',
        'ink-keys',
        'antipodal',
        'key-order',
        'initial-point',
        'duration',
        'bounds',
        'backend',
        'many',
    ],
)
def test_host_surface_contract_is_validated_before_hashing_or_preparing(bad):
    from srstudio._composition_forms import validate

    plan, _ = form()
    binding = plan.bindings[0]
    surface = binding.forms[0]
    fields = (surface,)
    if bad == 'duplicate':
        fields *= 2
    elif bad == 'albedo':
        fields = (replace(surface, albedo='red'),)
    elif bad == 'ink-palette':
        fields = (replace(surface, mode='ink'),)
    elif bad == 'ink-keys':
        fields = (replace(surface, mode='ink', palette=(), keys=(c.FormKey(0, surface.point, surface.normal),)),)
    elif bad == 'antipodal':
        fields = (
            replace(
                surface,
                keys=(c.FormKey(0, surface.point, surface.normal, 'linear'), c.FormKey(1, surface.point, (0, 0, -1))),
            ),
        )
    elif bad == 'key-order':
        fields = (replace(surface, keys=(c.FormKey(0, surface.point, surface.normal),) * 2),)
    elif bad == 'initial-point':
        fields = (replace(surface, keys=(c.FormKey(0, (1, 0, 0), surface.normal),)),)
    elif bad == 'duration':
        fields = (
            replace(
                surface, keys=(c.FormKey(0, surface.point, surface.normal), c.FormKey(2, surface.point, surface.normal))
            ),
        )
    elif bad == 'bounds':
        fields = (replace(surface, point=(11, 0, 0)),)
    elif bad == 'backend':
        binding = replace(binding, backend='plates')
    else:
        fields *= 257
    with pytest.raises(c.CompositionError):
        validate(fields, binding)


@pytest.mark.parametrize('time', [-1, 1.01, True, float('nan'), float('inf'), '0'])
def test_form_sampling_refuses_invalid_source_times(time):
    plan, _ = form()
    with pytest.raises(c.CompositionError):
        c.form_lighting(plan, 'face', time)


def test_form_sampling_revalidates_plan_layer_and_sphere_envelope():
    plan, _ = form()
    for changed, name in ((replace(plan, digest='0' * 64), 'face'), (plan, 'unknown')):
        with pytest.raises(c.CompositionError):
            c.form_lighting(changed, name, 0)
    binding = replace(plan.bindings[0], forms=())
    unlit = c.preflight(replace(plan.spec, lights=c.LightRig('flat')), (binding,), purpose=plan.purpose)
    with pytest.raises(c.CompositionError, match='authored form'):
        c.form_lighting(unlit, 'face', 0)
    rig = c.LightRig('lit', (c.LightSpec('area', 'sphere-area', '#ffffff', 1, radius=1),))
    invalid = c.preflight(replace(plan.spec, lights=rig), plan.bindings, purpose=plan.purpose)
    with pytest.raises(c.CompositionError, match='outside sphere'):
        m.plan_scene(invalid.spec, invalid.bindings, m.SceneMotion(), purpose=plan.purpose)


def test_form_digest_includes_fields_but_not_record_order_and_obeys_total_bytes(monkeypatch):
    from srstudio import _composition_text as text

    plan, source = form()
    fields = (*plan.bindings[0].forms, c.FormSurface('outline', mode='ink'))
    assert c.vector_source_digest(source, forms=fields) == c.vector_source_digest(source, forms=fields[::-1])
    assert c.vector_source_digest(source, forms=fields) != c.vector_source_digest(source)
    monkeypatch.setattr(text, 'MAX_BYTES', len(source.xml))
    with pytest.raises(c.CompositionError, match='form buffers'):
        c.vector_source_digest(source, forms=fields)


@pytest.mark.parametrize('bad', ['field', 'pin', 'fill'])
def test_timeline_worker_revalidates_form_fields_and_content(bad):
    from srstudio import _composition_wire as wire
    from srstudio import _scene_motion_wire as tw
    from srstudio._scene_motion_worker import dispatch

    plan, source = form(animated=True)
    timeline = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
    raw = dict(
        schema=wire.SCHEMA,
        operation='compile-timeline',
        timeline=tw.encode(timeline),
        vectors=[dict(id=source.id, xml=wire.xml_encode(source.xml))],
        images=[],
        placements=[],
    )
    if bad == 'field':
        raw['timeline']['bindings'][0]['forms'][0]['untrusted'] = True
    elif bad == 'pin':
        raw['vectors'][0]['xml'] = wire.xml_encode(source.xml.replace(b'#ffffff', b'#123456'))
    else:
        source = replace(source, xml=source.xml.replace(b'#ffffff', b'none'))
        binding = replace(
            plan.bindings[0],
            candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=plan.bindings[0].forms)),
        )
        timeline = m.plan_scene(plan.spec, (binding,), m.SceneMotion(), purpose=plan.purpose)
        raw['timeline'] = tw.encode(timeline)
        raw['vectors'][0]['xml'] = wire.xml_encode(source.xml)
    with pytest.raises(c.CompositionError):
        dispatch(wire.dumps(raw))


def test_form_event_union_is_bounded_and_linear_palettes_coalesce(monkeypatch):
    from srstudio._composition_forms import events

    plan, source = form()
    surface = replace(
        plan.bindings[0].forms[0],
        keys=(c.FormKey(0, (0, 0, 0), (0, 0, 1), 'linear'), c.FormKey(1, (1, 0, 0), (1, 0, 0))),
    )
    binding = replace(
        plan.bindings[0],
        forms=(surface,),
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=(surface,))),
    )
    timeline = m.plan_scene(plan.spec, (binding,), m.SceneMotion(), purpose=plan.purpose)
    # White stays nearest until the .75 output sample; no redundant spans at .25 and .5.
    assert [(s.start, s.end) for s in timeline.spans] == [(0, 0.75), (0.75, 1)]
    monkeypatch.setattr(m, 'MAX_TIMELINE_SAMPLES', 2)
    held = replace(surface, keys=tuple(c.FormKey(t, (0, 0, 0), (0, 0, 1)) for t in (0, 0.1, 0.2, 0.3)))
    with pytest.raises(c.CompositionError, match='at most 2'):
        events(replace(binding, forms=(held,)), plan.spec.layers[0], plan.spec.fps)


def test_form_guide_example_is_executable():
    import re
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = guide.split('## Author vector form lighting\n', 1)
    assert len(section) == 2
    code = re.search(r'```python\n(.*?)```', section[1], re.S)
    assert code is not None
    namespace = {}
    exec(compile(code[1], 'composition-preflight.md:forms', 'exec'), namespace)
    assert namespace['lit'].color == '#d09050'


def test_fractional_source_rate_keeps_the_exact_mapped_hold_boundary(tmp_path):
    plan, source = form(animated=True)
    clock = c.TemporalPolicy(0.1, 1, 0.125, 0.7)
    layer = replace(plan.spec.layers[0], temporal=clock)
    spec = replace(plan.spec, layers=(layer,))
    boundary = clock.start + (0.5 - clock.source_start) / clock.rate
    # Inverting the floating-point scene clock lands just before the authored key.
    assert clock.source_start + (boundary - clock.start) * clock.rate < 0.5
    timeline = m.plan_scene(spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
    assert boundary in {span.start for span in timeline.spans}
    result = m.compile_timeline(timeline, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    spans = ET.fromstring(result.xml).findall('composition/group')
    assert (
        next(group for group in spans if float(group.get('start')) == boundary).find('.//shape').get('fill')
        == '#000000'
    )


def test_static_worker_accounts_for_form_metadata_in_combined_input_limit(monkeypatch):
    from srstudio import _composition_emit as emitter
    from srstudio._composition_forms import size
    from srstudio._composition_vector import prepare_vector

    plan, source = form()
    root = ET.fromstring(source.xml)
    content = root.find('composition')
    original = content[0]
    content.remove(original)
    palette = tuple('#' + format(i, 'x') * 6 for i in range(16))
    fields = tuple(c.FormSurface(f'patch{i}', palette) for i in range(32))
    for field in fields:
        content.append(ET.Element('shape', {**original.attrib, 'id': field.node}))
    source = replace(source, xml=ET.tostring(root))
    binding = replace(
        plan.bindings[0],
        forms=fields,
        nodes=40,
        memory_bytes=1024**2,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=fields)),
    )
    plan = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    prepared = prepare_vector(binding, source.xml)
    maximum = len(source.xml) + size(fields) - 1
    assert 2048 + len(source.xml) + 64 * binding.nodes < maximum
    monkeypatch.setattr(emitter, 'MAX_XML_BYTES', maximum)
    with pytest.raises(c.CompositionError, match='combined source'):
        emitter.compile_scene(plan, (prepared,))
