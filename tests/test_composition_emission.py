"""Payload verification and atomic scene emission, including actual engine clocks."""

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError, replace

import pytest

from srstudio import composition as c
from support.composition import engine_eval as evaluate
from support.composition import paper, window


def test_real_payload_compiles_deterministically_with_closed_resources_and_scoped_ids():
    spec, binding, xml = paper()
    asset = c.prepare_vector(binding, xml)
    plan = c.preflight(spec, (binding,))
    result = c.compile_scene(plan, (asset,))
    assert c.compile_scene(plan, (asset,)) == result
    assert result.plan_digest == plan.digest
    assert len(result.digest) == 64
    root = ET.fromstring(result.xml)
    assert root.find('project').get('width') == '320'
    assert root.find('composition/group').get('x') == '20'
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    assert len(ids) == len(set(ids))
    assert 'url(#l0__paper)' in result.xml.decode()
    assert result.nodes == len(list(root.iter()))
    with pytest.raises(FrozenInstanceError):
        asset.xml = b'changed'


@pytest.mark.parametrize(
    'bad', ['xml', 'dtd', 'resource', 'expression', 'effect', 'bounds', 'nodes', 'memory', 'backend']
)
def test_payload_refusals_are_typed_and_do_not_change_the_input(bad):
    _, binding, xml = paper()
    if bad == 'xml':
        xml = b'<scene>'
    elif bad == 'dtd':
        xml = b'<!DOCTYPE scene [<!ENTITY value "abc">]>' + xml.split(b'?>', 1)[1]
    elif bad in ('resource', 'expression', 'effect'):
        element = {
            'resource': b'<include id="other" src="other.xml"/>',
            'expression': b'<expression property="x">time * 10</expression>',
            'effect': b'<shake amplitude="100"/>',
        }[bad]
        xml = xml.replace(b'</group>', element + b'</group>', 1)
        binding = replace(binding, nodes=binding.nodes + 1, memory_bytes=len(xml) * 16)
    elif bad == 'bounds':
        binding = replace(binding, bounds=c.Bounds((0, 0, 0), (1, 1, 0)))
    elif bad == 'nodes':
        binding = replace(binding, nodes=1)
    elif bad == 'memory':
        binding = replace(binding, memory_bytes=1)
    elif bad == 'backend':
        binding = replace(binding, backend='plates')
    before = xml
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_vector(binding, xml)
    assert caught.value.to_dict()['code'].startswith('composition.')
    assert xml == before


def test_animation_envelope_includes_intermediate_rotation_extrema():
    _, binding, xml = paper(animated=True)
    xml = xml.replace(b'property="x"', b'property="rotation"').replace(b'value="40"', b'value="180"')
    binding = replace(binding, memory_bytes=len(xml) * 16)
    # Both the first and last drawings could fit a thin horizontal box; the
    # intervening quarter turn must also be bounded without sampling frames.
    binding = replace(binding, bounds=c.Bounds((-350, -170, 0), (350, 170, 0)))
    with pytest.raises(c.CompositionError, match='bounds'):
        c.prepare_vector(binding, xml)
    roomy = replace(binding, bounds=c.Bounds((-400, -400, 0), (400, 400, 0)))
    c.prepare_vector(roomy, xml)


@pytest.mark.parametrize('bad', ['forged-cost', 'missing', 'duplicate', 'changed-binding', 'changed-payload'])
def test_compiler_rechecks_plan_and_payload_identity(bad):
    spec, binding, xml = paper()
    plan = c.preflight(spec, (binding,))
    asset = c.prepare_vector(binding, xml)
    assets = (asset,)
    if bad == 'forged-cost':
        plan = replace(plan, cost=replace(plan.cost, nodes=0))
    elif bad == 'missing':
        assets = ()
    elif bad == 'duplicate':
        assets *= 2
    elif bad == 'changed-binding':
        assets = (replace(asset, binding=replace(binding, nodes=binding.nodes + 1)),)
    else:
        assets = (replace(asset, xml=xml.replace(b'#E1E1D7', b'#FFFFFF')),)
    with pytest.raises(c.CompositionError):
        c.compile_scene(plan, assets)


def test_emit_is_self_contained_private_and_preserves_existing_output_by_default(tmp_path):
    spec, binding, xml = paper()
    plan, assets = c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),)
    path = tmp_path / 'scene.xml'
    compiled = c.emit_scene(plan, assets, path)
    assert path.read_bytes() == compiled.xml
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(c.CompositionError):
        c.emit_scene(plan, assets, path)
    assert path.read_bytes() == compiled.xml
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_second_asset_does_not_create_output_directories(tmp_path):
    spec, binding, xml = paper()
    second = replace(binding, id='other')
    spec = replace(spec, layers=spec.layers + (replace(spec.layers[0], id='other', asset='other'),))
    plan = c.preflight(spec, (binding, second))
    assets = (c.prepare_vector(binding, xml), c.prepare_vector(second, xml))
    broken = replace(assets[1], xml=b'<scene>')
    output = tmp_path / 'absent' / 'scene.xml'
    with pytest.raises(c.CompositionError):
        c.emit_scene(plan, (assets[0], broken), output)
    assert not output.parent.exists()


def test_failed_atomic_replace_retains_previous_scene(tmp_path, monkeypatch):
    import os

    spec, binding, xml = paper()
    plan, assets = c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),)
    path = tmp_path / 'scene.xml'
    path.write_bytes(b'previous')

    def fail(*args, **kwargs):
        raise OSError('disk failure')

    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(plan, assets, path, overwrite=True)
    assert isinstance(caught.value.__cause__, OSError)
    assert path.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [path]


def test_engine_preserves_source_clock_through_offset_and_rate(tmp_path, scene_render):
    spec, binding, xml = paper(animated=True)
    source = tmp_path / 'source.xml'
    source.write_bytes(xml)
    spec = window(spec)
    target = tmp_path / 'scene.xml'
    c.emit_scene(c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),), target)
    for time in (0.5, 0.75, 1.25):
        original = {n['id']: n for n in evaluate(scene_render, source, 0.25 + (time - 0.5) * 1.5)}
        actual = {n['id']: n for n in evaluate(scene_render, target, time)}
        before, after = original['motion'], actual['l0__motion']
        assert after['world'][4] == pytest.approx(before['world'][4] + 20)
        assert after['world'][5] == pytest.approx(before['world'][5] + 30)
    for time in (0.25, 1.5):
        nodes = evaluate(scene_render, target, time)
        assert not any(n.get('draw', True) for n in nodes if n['id'].startswith('l0__'))


@pytest.mark.parametrize('projection', ['orthographic', 'perspective'])
def test_engine_parent_transform_and_camera_project_once(tmp_path, scene_render, projection):
    spec, binding, xml = paper()
    parent = replace(spec.layers[0], transform=c.Transform((0.2, 0.3, 1), (0, 0, 90), 0.01))
    child = replace(parent, id='child', parent=parent.id, transform=c.Transform((2, 3, 0), (0, 0, -30), 2))
    spec = replace(
        spec, camera=c.CameraSpec(projection=projection, origin=(160, 120), scale=100), layers=(parent, child)
    )
    path = tmp_path / 'scene.xml'
    result = c.emit_scene(c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),), path)
    root = ET.fromstring(result.xml)
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    assert len(set(ids)) == len(ids)
    nodes = {n['id']: n for n in evaluate(scene_render, path, 0)}
    factor = 10 / 9 if projection == 'perspective' else 1
    # Parent maps the child's local (2,3) to (.17,.32,1); its source
    # scale is .02 world units and total in-plane rotation is 60 degrees.
    import math

    angle, scale = math.radians(60), 2 * factor
    assert nodes['l1__motion']['world'] == pytest.approx(
        [
            math.cos(angle) * scale,
            math.sin(angle) * scale,
            -math.sin(angle) * scale,
            math.cos(angle) * scale,
            160 + 17 * factor,
            120 + 32 * factor,
        ]
    )


@pytest.mark.parametrize(
    'change',
    [
        'extrapolation',
        'overshoot',
        'key-order',
        'duplicate-track',
        'normalized',
        'static-clock',
        'project-clock',
        'paint',
        'nan',
        'percent',
        'schema',
        'empty',
        'unbounded-shape',
        'shape-kind',
        'depth',
    ],
)
def test_payload_semantics_refuse_features_without_a_complete_bound(change):
    _, binding, xml = paper(animated=True)
    root = ET.fromstring(xml)
    animation = root.find('.//animate')
    shape = root.find('.//shape')
    if change == 'extrapolation':
        animation.set('extrapolateAfter', 'linear')
    elif change == 'overshoot':
        animation[0].set('interpolation', 'back-out')
    elif change == 'key-order':
        animation[1].set('time', '0')
    elif change == 'duplicate-track':
        root.find(".//group[@id='motion']").append(ET.fromstring(ET.tostring(animation)))
    elif change == 'normalized':
        animation.set('timeBase', 'normalized')
    elif change == 'static-clock':
        binding = replace(binding, duration=None)
        root.find(".//group[@id='motion']").remove(animation)
        shape.set('start', '0.5')
    elif change == 'project-clock':
        root.find('project').set('duration', '1')
    elif change == 'paint':
        shape.set('fill', 'url(#missing)')
    elif change == 'nan':
        animation[0].set('value', 'nan')
    elif change == 'percent':
        shape.set('x', '50%')
    elif change == 'schema':
        root.find('project').set('width', '-10')
    elif change == 'empty':
        root.find('composition').clear()
    elif change == 'unbounded-shape':
        shape.set('shape', 'rect')
        shape.attrib.pop('width')
    elif change == 'shape-kind':
        shape.set('shape', 'star')
    else:
        node = root.find('composition')
        for index in range(65):
            node = ET.SubElement(node, 'group', {'id': f'nested{index}'})
    xml = ET.tostring(root)
    binding = replace(binding, nodes=1000, memory_bytes=len(xml) * 16)
    with pytest.raises(c.CompositionError):
        c.prepare_vector(binding, xml)


def test_repeated_sources_check_expansion_budget_before_copying(monkeypatch):
    from srstudio import _composition_emit

    spec, binding, xml = paper()
    spec = replace(spec, layers=tuple(replace(spec.layers[0], id=f'layer{i}') for i in range(50)))
    # The manifest accounts for one prepared asset, but 50 placements need
    # their own emitted XML. The compiler must account for that expansion.
    assets = (c.prepare_vector(binding, xml),)
    plan = c.preflight(spec, (binding,))
    spec = replace(spec, budget=replace(spec.budget, max_memory_bytes=plan.cost.memory_bytes))

    def no_copy(*args, **kwargs):
        pytest.fail('the known expansion budget must be checked before copying XML trees')

    monkeypatch.setattr(_composition_emit.ET, 'fromstring', no_copy)
    with pytest.raises(c.CompositionError) as caught:
        c.compile_scene(c.preflight(spec, (binding,)), assets)
    assert caught.value.to_dict()['code'] == 'composition.budget'


def test_timeout_never_publishes_a_scene(tmp_path, monkeypatch):
    from srstudio import _composition_emit

    spec, binding, xml = paper()
    plan, assets = c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),)
    readings = iter((0, plan.spec.budget.timeout + 1))
    monkeypatch.setattr(_composition_emit.time, 'monotonic', lambda: next(readings))
    output = tmp_path / 'new' / 'scene.xml'
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(plan, assets, output)
    assert caught.value.to_dict()['path'] == 'budget.timeout'
    assert not output.parent.exists()


def test_successful_overwrite_publishes_one_complete_scene(tmp_path):
    spec, binding, xml = paper()
    output = tmp_path / 'scene.xml'
    output.write_bytes(b'old')
    result = c.emit_scene(c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),), output, overwrite=True)
    assert output.read_bytes() == result.xml
    assert list(tmp_path.iterdir()) == [output]


def test_rendered_cut_matches_the_original_approved_drawing_at_its_source_time(tmp_path, scene_render):
    import numpy as np

    from srstudio import plates

    spec, binding, xml = paper(animated=True)
    spec = replace(window(spec), camera=replace(spec.camera, origin=(0, 0)))
    source, target = tmp_path / 'source.xml', tmp_path / 'compiled.xml'
    source.write_bytes(xml)
    c.emit_scene(c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),), target)
    images = []
    for name, scene, time in (('source', source, 0.625), ('compiled', target, 0.75)):
        image = tmp_path / f'{name}.png'
        subprocess.run(
            [str(scene_render), 'render', str(scene), '--time', str(time), '--output', str(image), '--strict'],
            capture_output=True,
            check=True,
            timeout=60,
        )
        images.append(plates.pixels(image))
    assert images[0].shape == (240, 320, 4)
    assert images[0][..., :3].max() > images[0][..., :3].min()
    assert np.array_equal(*images)


@pytest.mark.parametrize('property,values', [('opacity', ('0.2', '0.8')), ('visible', ('false', 'true'))])
def test_bounded_visibility_and_opacity_keys_preserve_the_payload(property, values):
    _, binding, xml = paper(animated=True)
    root = ET.fromstring(xml)
    animation = root.find('.//animate')
    animation.set('property', property)
    for key, value in zip(animation, values, strict=True):
        key.set('value', value)
    xml = ET.tostring(root)
    binding = replace(binding, memory_bytes=len(xml) * 16)
    assert c.prepare_vector(binding, xml).xml == xml


@pytest.mark.parametrize('property,value', [('opacity', '1.1'), ('visible', 'maybe'), ('x', 'invalid')])
def test_invalid_animation_values_fail_with_typed_errors(property, value):
    _, binding, xml = paper(animated=True)
    root = ET.fromstring(xml)
    animation = root.find('.//animate')
    animation.set('property', property)
    animation[0].set('value', value)
    xml = ET.tostring(root)
    binding = replace(binding, memory_bytes=len(xml) * 16)
    with pytest.raises(c.CompositionError):
        c.prepare_vector(binding, xml)


def test_rectangles_ellipses_and_static_negative_scale_have_measured_bounds():
    from sr_core.scene import Scene

    from srstudio import Canvas

    _, binding, _ = paper()
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None, width=320, height=240)
    group = cv.group(cv.comp, 'shapes', x=20, scaleX=-2, scaleY=3)
    cv.rect(group, 0, 0, 10, 10, '#ff0000')
    cv.ellipse(group, 10, 0, 10, 10, '#0000ff')
    xml = scene.to_bytes()
    binding = replace(binding, nodes=100, memory_bytes=len(xml) * 16, bounds=c.Bounds((-20, 0, 0), (20, 30, 0)))
    prepared = c.prepare_vector(binding, xml)
    assert prepared.bounds == binding.bounds


def test_screen_information_keeps_pixel_coordinates_under_a_world_camera(tmp_path, scene_render):
    spec, binding, xml = paper()
    layer = replace(spec.layers[0], role='information', space='screen', transform=c.Transform((10, 20, 0), scale=0.5))
    spec = replace(spec, layers=(layer,), camera=c.CameraSpec(position=(8, 2, 10), scale=2000))
    path = tmp_path / 'scene.xml'
    c.emit_scene(c.preflight(spec, (binding,)), (c.prepare_vector(binding, xml),), path)
    node = next(n for n in evaluate(scene_render, path, 0) if n['id'] == 'l0__motion')
    assert node['world'] == pytest.approx([0.5, 0, 0, 0.5, 10, 20])


@pytest.mark.parametrize('change', ['animated-gradient', 'nan-gradient'])
def test_gradient_definitions_cannot_escape_finite_source_clock_validation(change):
    _, binding, xml = paper(animated=True)
    root = ET.fromstring(xml)
    gradient = root.find('./paints/linearGradient')
    if change == 'animated-gradient':
        animation = ET.SubElement(gradient, 'animate', {'property': 'x'})
        ET.SubElement(animation, 'key', {'time': '0', 'value': '0'})
        ET.SubElement(animation, 'key', {'time': '1', 'value': '1'})
    else:
        gradient.set('x1', 'NaN')
    xml = ET.tostring(root)
    binding = replace(binding, nodes=1000, memory_bytes=len(xml) * 16)
    with pytest.raises(c.CompositionError):
        c.prepare_vector(binding, xml)


def test_misplaced_animation_root_has_a_typed_refusal():
    _, binding, _ = paper(animated=True)
    with pytest.raises(c.CompositionError):
        c.prepare_vector(binding, b'<animate property="x"><key time="0" value="0"/></animate>')
