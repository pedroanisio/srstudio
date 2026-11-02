"""Authored masks name a real planar receiver and retain their caster anchor."""

import xml.etree.ElementTree as ET
from dataclasses import asdict, replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m


def fixture():
    def asset(name, points, color, anchor):
        source = c.VectorSource(
            name,
            (
                '<scene version="1.1"><project width="64" height="64" fps="4" duration="1"/>'
                '<composition><shape id="surface" shape="path" path="M 0 0 L 1 0 L 1 1 Z" '
                f'width="64" height="64" fill="{color}" stroke="#00000000" strokeWidth="0"/>'
                '</composition></scene>'
            ).encode(),
        )
        forms = (c.FormSurface('surface', mode='ink', path=c.FormPath(points)),)
        binding = c.AssetBinding(
            name,
            'candidate.shadow-' + name,
            1,
            'vector',
            c.Bounds((-3, -3, -3), (3, 3, 3)),
            anchors=(c.Anchor('center', anchor),),
            nodes=10,
            memory_bytes=65536,
            forms=forms,
            candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
        )
        return binding, source

    floor = ((-2.0, 0.0, -2.0), (2.0, 0.0, -2.0), (2.0, 0.0, 2.0), (-2.0, 0.0, 2.0))
    mask = ((-0.5, 0.0, -0.4), (0.5, 0.0, -0.4), (0.5, 0.0, 0.4), (-0.5, 0.0, 0.4))
    caster = ((-0.2, -1.5, 0.0), (0.2, -1.5, 0.0), (0.2, -0.5, 0.0), (-0.2, -0.5, 0.0))
    pairs = (
        asset('floor', floor, '#ffffff', (0, 0, 0)),
        asset('mask', mask, '#000000', (0, 0, 0)),
        asset('caster', caster, '#ff0000', (0, -1, 0)),
    )
    clock = c.TemporalPolicy(0, 1)
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(4),
        1,
        7,
        'meter',
        c.CameraSpec('orthographic', (4, -4, 8), (0, 0, 0), (32, 32), 10),
        c.LightRig('lit', (c.LightSpec('key', 'directional', '#ffffff', 1, pitch=-90),)),
        (
            c.LayerSpec('floor', 'floor', 1, clock),
            c.LayerSpec(
                'mask',
                'mask',
                1,
                clock,
                parent='floor',
                shadow_mask=c.ShadowMask('caster', 'floor', 'surface', 'center', 'center', 'key'),
            ),
            c.LayerSpec('caster', 'caster', 1, clock, shadow_receiver='floor'),
        ),
        c.RenderBudget(),
    )
    return spec, tuple(p[0] for p in pairs), tuple(p[1] for p in pairs)


def test_authored_mask_compiles_with_explicit_caster_receiver_and_light():
    spec, bindings, sources = fixture()
    plan = c.preflight(spec, bindings, purpose='candidate-review')
    assert plan.cost.contact_samples == 2
    assert c.parse_scene(asdict(spec)) == spec
    output = c.compile_scene(plan, sources)
    root = ET.fromstring(output.xml)
    assert len(list(root.iter('shape'))) == 3
    assert [s.get('fill') for s in root.iter('shape')] == ['#ffffff', '#000000', '#ff0000']
    assert b'"approval":null' in output.xml


@pytest.mark.parametrize(
    'bad',
    [
        'receiver',
        'caster',
        'surface',
        'anchor',
        'light',
        'ambient',
        'parallel',
        'away',
        'unpaired',
        'duplicate',
        'order',
        'parent',
        'outside',
        'off-plane',
        'anchor-drift',
        'concave-receiver',
        'animated-mask',
        'window',
        'information',
        'budget',
    ],
)
def test_invalid_shadow_contract_fails_before_output_or_cache_mutation(bad, tmp_path):
    spec, bindings, sources = fixture()
    floor, mask, caster = spec.layers
    shadow = mask.shadow_mask
    if bad in ('receiver', 'caster', 'light'):
        shadow = replace(shadow, **{bad: 'missing'})
    elif bad == 'surface':
        shadow = replace(shadow, receiver_surface='missing')
    elif bad == 'anchor':
        shadow = replace(shadow, caster_anchor='missing')
    elif bad == 'ambient':
        spec = replace(spec, lights=c.LightRig('lit', (c.LightSpec('key', 'ambient', '#ffffff', 1),)))
    elif bad in ('parallel', 'away'):
        spec = replace(
            spec, lights=c.LightRig('lit', (replace(spec.lights.lights[0], pitch=0 if bad == 'parallel' else 90),))
        )
    elif bad == 'unpaired':
        caster = replace(caster, shadow_receiver=None)
    elif bad == 'parent':
        mask = replace(mask, parent=None)
    elif bad in ('outside', 'off-plane'):
        mask = replace(mask, transform=c.Transform((3, 0, 0) if bad == 'outside' else (0, -0.1, 0)))
    elif bad == 'anchor-drift':
        caster = replace(caster, transform=c.Transform((0.1, 0, 0)))
    elif bad in ('concave-receiver', 'animated-mask'):
        i = 0 if bad == 'concave-receiver' else 1
        item = bindings[i]
        path = item.forms[0].path
        path = (
            replace(path, points=(path.points[0], path.points[1], (0, 0, 0), path.points[3]))
            if i == 0
            else replace(path, keys=(c.PathKey(0, path.points),))
        )
        forms = (replace(item.forms[0], path=path),)
        item = replace(
            item,
            forms=forms,
            duration=1,
            candidate=c.CandidateSource('toon', c.vector_source_digest(sources[i], forms=forms)),
        )
        bindings = tuple(item if j == i else b for j, b in enumerate(bindings))
    elif bad == 'window':
        caster = replace(caster, temporal=c.TemporalPolicy(0.1, 1))
    elif bad == 'information':
        mask = replace(mask, role='information', space='screen')
    elif bad == 'budget':
        spec = replace(spec, budget=replace(spec.budget, max_contact_samples=1))
    mask = replace(mask, shadow_mask=shadow)
    layers = (floor, mask, caster)
    if bad == 'duplicate':
        layers = (floor, mask, replace(mask, id='another-mask'), caster)
    elif bad == 'order':
        layers = (mask, floor, caster)
    spec = replace(spec, layers=layers)
    with pytest.raises(c.CompositionError):
        c.emit_scene(c.preflight(spec, bindings, purpose='candidate-review'), sources, tmp_path / 'scene.xml')
    assert list(tmp_path.iterdir()) == []


def test_caster_anchor_keys_are_checked_through_the_complete_source_clock():
    spec, bindings, _ = fixture()
    caster = replace(
        bindings[2],
        duration=2,
        anchors=(
            c.Anchor(
                'center',
                (0, -1, 0),
                (c.AnchorKey(0, (0, -1, 0)), c.AnchorKey(1, (0.1, -1, 0)), c.AnchorKey(2, (0, -1, 0))),
            ),
        ),
    )
    spec = replace(spec, layers=(*spec.layers[:2], replace(spec.layers[2], temporal=c.TemporalPolicy(0, 1, 0, 2))))
    with pytest.raises(c.CompositionError, match='shadow'):
        c.preflight(spec, (*bindings[:2], caster), purpose='candidate-review')


def test_parent_translation_and_camera_cut_preserve_receiver_registration(tmp_path):
    spec, bindings, sources = fixture()
    caster = replace(spec.layers[2], parent='floor')
    spec = replace(spec, layers=(*spec.layers[:2], caster))
    motion = m.SceneMotion(
        camera=(
            m.CameraKey(0, spec.camera, 'hold'),
            m.CameraKey(0.5, replace(spec.camera, position=(-4, -4, 8)), 'hold'),
        ),
        transforms=(
            m.TransformTrack('floor', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.25, 0, 0))))),
        ),
    )
    timeline = m.plan_scene(spec, bindings, motion, purpose='candidate-review')
    output = m.emit_timeline(
        timeline, sources, tmp_path / 'scene', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
    )
    assert output.work.engine_invocations == 0 and not (tmp_path / 'cache').exists()
    assert len(list(ET.fromstring(output.xml).iter('shape'))) >= 12


def test_a_requested_shadow_cannot_be_silently_omitted():
    spec, bindings, _ = fixture()
    spec = replace(spec, layers=(spec.layers[0], spec.layers[2]))
    with pytest.raises(c.CompositionError, match='shadow'):
        c.preflight(spec, bindings, purpose='candidate-review')


@pytest.mark.parametrize('backend', ['scene', 'bundle', 'timeline'])
@pytest.mark.parametrize('bad', ['transparent', 'hidden-group', 'invisible', 'timed', 'animation', 'stroke'])
def test_invisible_or_unbounded_mask_payload_is_refused_before_publication(backend, bad, tmp_path):
    spec, bindings, sources = fixture()
    source = sources[1]
    xml = source.xml
    if bad == 'transparent':
        xml = xml.replace(b'fill="#000000"', b'fill="#00000000"')
    elif bad == 'hidden-group':
        xml = xml.replace(b'<composition>', b'<composition><group id="hide" opacity="0">').replace(
            b'</composition>', b'</group></composition>'
        )
    elif bad == 'invisible':
        xml = xml.replace(b'id="surface"', b'id="surface" visible="false"')
    elif bad == 'timed':
        xml = xml.replace(b'id="surface"', b'id="surface" start="0.5"')
    elif bad == 'animation':
        xml = xml.replace(
            b'/></composition>',
            b'><animate property="opacity"><key time="0" value="0"/></animate></shape></composition>',
        )
    else:
        xml = xml.replace(b'stroke="#00000000" strokeWidth="0"', b'stroke="#000000" strokeWidth="5"')
    source = replace(source, xml=xml)
    binding = replace(
        bindings[1],
        duration=1,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=bindings[1].forms)),
    )
    bindings = (bindings[0], binding, bindings[2])
    sources = (sources[0], source, sources[2])
    plan = c.preflight(spec, bindings, purpose='candidate-review')
    with pytest.raises(c.CompositionError, match='shadow'):
        if backend == 'scene':
            c.emit_scene(plan, sources, tmp_path / 'scene.xml')
        elif backend == 'bundle':
            c.emit_bundle(plan, sources, tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache')
        else:
            timeline = m.plan_scene(spec, bindings, m.SceneMotion(), purpose='candidate-review')
            m.emit_timeline(
                timeline, sources, tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
            )
    assert list(tmp_path.iterdir()) == []


def test_real_render_keeps_the_mask_on_its_receiver_across_parent_motion_and_cut(tmp_path, scene_render):
    import numpy as np
    import shapely
    from PIL import Image

    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held
    from srstudio.limbs import Vec3

    spec, bindings, sources = fixture()
    spec = replace(
        spec,
        width=320,
        height=240,
        camera=replace(spec.camera, origin=(160, 120), scale=40),
        layers=(*spec.layers[:2], replace(spec.layers[2], parent='floor')),
    )
    motion = m.SceneMotion(
        camera=(
            m.CameraKey(0, spec.camera, 'hold'),
            m.CameraKey(0.5, replace(spec.camera, position=(-4, -4, 8)), 'hold'),
        ),
        transforms=(
            m.TransformTrack('floor', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.25, 0, 0))))),
        ),
    )
    timeline = m.plan_scene(spec, bindings, motion, purpose='candidate-review')
    result = m.emit_timeline(timeline, sources, tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    assert result.work.engine_invocations == 0
    seen = {}
    for time in (0.75, 0.25, 0.75):
        output = tmp_path / f'{time}.png'
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
        pixels = np.array(Image.open(output).convert('RGBA'))
        span = next(span for span in timeline.spans if span.start <= time < span.end)
        plan = timeline.samples[span.scene]
        y, x = np.indices((240, 320))
        centers = shapely.points(x + 0.5, y + 0.5)
        masks, away = [], np.ones((240, 320), dtype=bool)
        for binding in bindings:
            view = c.spatial_camera(plan, binding.id)
            polygon = shapely.Polygon([view.project(Vec3(*point)).xy for point in binding.forms[0].path.points])
            masks.append(shapely.contains(polygon, centers))
            away &= shapely.distance(polygon.boundary, centers) > 1
        floor, mask, caster = masks
        shadow_pixels = mask & ~caster & away
        ground_pixels = floor & ~mask & ~caster & away
        assert shadow_pixels.any() and ground_pixels.any()
        assert np.all(pixels[shadow_pixels, :3] == 0)
        assert np.all(pixels[ground_pixels] == 255)
        if time in seen:
            assert pixels.tobytes() == seen[time]
        seen[time] = pixels.tobytes()


@pytest.mark.parametrize(
    'roles',
    [None, {}, [['unknown', 'surface']], [['mask', 'missing']], [['mask', False]], [{}], [['mask', 'surface']] * 513],
)
def test_shadow_preparation_worker_rejects_malformed_node_roles(roles):
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    _, bindings, sources = fixture()
    request = {
        'schema': wire.SCHEMA,
        'operation': 'prepare',
        'binding': asdict(bindings[1]),
        'xml': wire.xml_encode(sources[1].xml),
        'shadow_nodes': roles,
    }
    with pytest.raises(c.CompositionError):
        dispatch(wire.dumps(request))


def test_unshadowed_scene_and_timeline_keep_frozen_fingerprints(tmp_path):
    import hashlib

    from support.composition import paper

    spec, binding, xml = paper()
    plan = c.preflight(spec, (binding,))
    source = c.VectorSource(binding.id, xml)
    static = c.compile_scene(plan, (source,))
    track = m.TransformTrack(
        'paper', (m.TransformKey(0, c.Transform()), m.TransformKey(2, c.Transform((10, 5, 0), (0, 0, 5))))
    )
    motion = m.SceneMotion(transforms=(track,))
    timeline = m.plan_scene(spec, (binding,), motion)
    output = m.compile_timeline(timeline, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    # Recorded from the preceding spatial-path implementation, before ShadowMask existed.
    assert plan.digest == '2c4d987d798e77917fd14a8e64de22607e06fd8f66f6398a59ee520df67a2a91'
    assert hashlib.sha256(static.xml).hexdigest() == '0a42eedbc50ab57df2ee2a0bb8e57719cb7f8d855a527eca7151b53306e2ef06'
    assert timeline.digest == '9afe5df3b2b3b6438a5dd6c8d22dced48ccdf892e9defcdd6e663a5d5ee83b87'
    assert hashlib.sha256(output.xml).hexdigest() == 'f18659f0998e5c6ba6c765d6687e3b01b77588c4628258dae397fa543f2c238b'
    assert timeline.cost.memory_bytes == 2213696
