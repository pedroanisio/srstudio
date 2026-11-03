"""Authored spatial vector paths share the plate camera without a second 2D projection."""

import math
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import Vec3
from support.composition_spatial_paths import POINTS, fixture


def points(node):
    return tuple(map(float, node.get('path').replace('M', '').replace('L', '').replace('Z', '').split()))


@pytest.mark.parametrize('parent', [False, True])
@pytest.mark.parametrize('projection', ['orthographic', 'perspective'])
def test_spatial_path_matches_shared_camera_and_keeps_screen_stroke_width(parent, projection):
    spec, binding, source = fixture()
    spec = replace(spec, camera=replace(spec.camera, projection=projection))
    if parent:
        root = replace(spec.layers[0], id='parent', transform=c.Transform((0.2, -0.1, 0.3), (10, 25, 5), 1.4))
        spec = replace(
            spec, layers=(root, replace(spec.layers[0], parent='parent', transform=c.Transform((0.1, 0.2, 0))))
        )
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    result = c.compile_scene(plan, (source,))
    root = ET.fromstring(result.xml)
    shape = list(root.iter('shape'))[-1]
    expected = tuple(v for p in POINTS for v in c.spatial_camera(plan, 'shape').project(Vec3(*p)).xy)
    assert points(shape) == pytest.approx(expected, abs=1e-9)
    group = root.find('composition')[-1]
    assert float(group.get('scaleX', '1')) == 1 and float(group.get('x', '0')) == 0
    assert shape.get('strokeWidth') == '2' and shape.get('fill') == '#ffffff'


def test_path_motion_enters_timeline_even_when_light_colors_are_unchanged(tmp_path):
    moved = tuple((x + 0.5, y, z) for x, y, z in POINTS)
    spec, binding, source = fixture(keys=(c.PathKey(0, POINTS), c.PathKey(0.35, moved)))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion(), purpose='candidate-review')
    assert 0.35 in {span.start for span in timeline.spans}
    bundle = m.compile_timeline(timeline, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    groups = ET.fromstring(bundle.xml).findall('composition/group')
    assert points(groups[0].find('.//shape')) != points(groups[-1].find('.//shape'))
    assert bundle.work.engine_invocations == 0 and not (tmp_path / 'cache').exists()


def test_linear_path_keys_use_frame_grid_and_keep_random_access_world_vertices():
    moved = tuple((x + 0.5, y, z) for x, y, z in POINTS)
    spec, binding, source = fixture(keys=(c.PathKey(0, POINTS, 'linear'), c.PathKey(1, moved)))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion(), purpose='candidate-review')
    assert {0, 0.25, 0.5, 0.75} <= {span.start for span in timeline.spans}
    plan = timeline.base
    for time in (0.75, 0, 0.5, 0.25, 0.75):
        expected = tuple((x + 0.5 * time, y, z) for x, y, z in POINTS)
        assert c.form_lighting(plan, 'shape', time)[0].vertices == expected
    with pytest.raises(c.CompositionError, match='compile_timeline'):
        c.compile_scene(plan, (source,))


@pytest.mark.parametrize('bad', ['few', 'many', 'shape', 'nan', 'clock', 'topology', 'bounds', 'mixed'])
def test_invalid_spatial_geometry_is_refused_before_publication(tmp_path, bad):
    spec, binding, source = fixture()
    with pytest.raises(c.CompositionError):
        path = binding.forms[0].path
        if bad == 'few':
            path = replace(path, points=POINTS[:2])
        elif bad == 'many':
            path = replace(path, points=POINTS * 65)
        elif bad == 'shape':
            path = replace(path, points=((0, 0),) * 3)
        elif bad == 'nan':
            path = replace(path, points=((math.nan, 0, 0), *POINTS[1:]))
        elif bad == 'clock':
            path = replace(path, keys=(c.PathKey(0.1, POINTS),))
        elif bad == 'topology':
            path = replace(path, keys=(c.PathKey(0, POINTS), c.PathKey(1, POINTS[:3])))
        elif bad == 'bounds':
            path = replace(path, points=((50, 0, 0), *POINTS[1:]))
        forms = (replace(binding.forms[0], path=path),)
        if bad == 'mixed':
            forms += (c.FormSurface('other', mode='ink'),)
        binding = replace(
            binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
        )
        plan = c.preflight(spec, (binding,), purpose='candidate-review')
        c.emit_scene(plan, (source,), tmp_path / 'out.xml')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'change',
    [
        (b'<composition>', b'<composition><group id="local" x="1">'),
        (b'shape="path"', b'shape="rect"'),
        (b'/></composition>', b'><animate property="x"><key time="0" value="0"/></animate></shape></composition>'),
    ],
)
def test_local_xml_geometry_cannot_transform_an_already_projected_path(change):
    spec, binding, source = fixture()
    xml = source.xml.replace(*change)
    if b'<group' in xml:
        xml = xml.replace(b'</composition>', b'</group></composition>')
    source = replace(source, xml=xml)
    binding = replace(binding, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=binding.forms)))
    with pytest.raises(c.CompositionError, match='identity XML|native path|only opacity'):
        c.compile_scene(c.preflight(spec, (binding,), purpose='candidate-review'), (source,))


def test_geometry_pin_and_near_plane_are_checked_before_output(tmp_path):
    spec, binding, source = fixture()
    with pytest.raises(c.CompositionError):
        c.preflight(
            replace(spec, camera=replace(spec.camera, position=(0, 0, 1))), (binding,), purpose='candidate-review'
        )
    changed = replace(binding.forms[0], path=replace(binding.forms[0].path, closed=False))
    plan = c.preflight(spec, (replace(binding, forms=(changed,)),), purpose='candidate-review')
    with pytest.raises(c.CompositionError):
        c.emit_scene(plan, (source,), tmp_path / 'bad.xml')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('attribute', ['anchorX', 'anchorY'])
def test_anchor_transforms_cannot_shift_projected_geometry(attribute):
    spec, binding, source = fixture()
    source = replace(source, xml=source.xml.replace(b'strokeWidth="2"', f'strokeWidth="2" {attribute}="0.1"'.encode()))
    binding = replace(binding, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=binding.forms)))
    with pytest.raises(c.CompositionError, match='identity XML'):
        c.compile_scene(c.preflight(spec, (binding,), purpose='candidate-review'), (source,))


def test_projected_path_expansion_is_bounded_before_starting_a_worker(monkeypatch):
    from srstudio import _composition_emit as emitter
    from srstudio import _composition_runtime as runtime

    spec, binding, source = fixture()
    forms = (replace(binding.forms[0], path=c.FormPath(POINTS * 64)),)
    binding = replace(
        binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    monkeypatch.setattr(emitter, 'MAX_XML_BYTES', 4096)

    def forbidden(*args, **kwargs):
        pytest.fail('projected XML expansion must be checked before launching the worker')

    monkeypatch.setattr(runtime, '_call', forbidden)
    with pytest.raises(c.CompositionError, match='expansion'):
        c.compile_scene(plan, (source,))


def test_timeline_expansion_includes_each_projected_path_copy(monkeypatch):
    from srstudio import _scene_motion_wire as wire

    spec, binding, source = fixture()
    forms = (replace(binding.forms[0], path=c.FormPath(POINTS * 64)),)
    binding = replace(
        binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    prepared = c.prepare_vector(binding, source.xml)
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion(), purpose='candidate-review')
    monkeypatch.setattr(wire.pw, 'MAX_BYTES', 8000)
    with pytest.raises(c.CompositionError, match='expansion'):
        wire.expansion(timeline, {'shape': prepared})


def test_open_ink_path_preserves_style_and_has_no_implicit_closing_segment():
    spec, binding, source = fixture(closed=False)
    forms = (replace(binding.forms[0], mode='ink', palette=(), path=c.FormPath(POINTS[:2], closed=False)),)
    binding = replace(
        binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    shape = ET.fromstring(c.compile_scene(plan, (source,)).xml).find('.//shape')
    assert shape.get('fill') == '#ffffff' and 'Z' not in shape.get('path')
    assert len(points(shape)) == 4 and c.form_lighting(plan, 'shape', 0)[0].color is None


@pytest.mark.parametrize('change', ['duration', 'duplicate', 'bool'])
def test_additional_path_contract_failures(change):
    spec, binding, source = fixture()
    with pytest.raises(c.CompositionError):
        if change == 'bool':
            path = c.FormPath(POINTS, closed=1)
        elif change == 'duplicate':
            path = c.FormPath(POINTS, (c.PathKey(0, POINTS), c.PathKey(0, POINTS)))
        else:
            path = c.FormPath(POINTS, (c.PathKey(0, POINTS), c.PathKey(2, POINTS)))
        forms = (replace(binding.forms[0], path=path),)
        binding = replace(
            binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
        )
        c.preflight(spec, (binding,), purpose='candidate-review')


def test_fractional_source_clock_keeps_geometry_at_the_exact_held_boundary(tmp_path):
    moved = tuple((x + 0.5, y, z) for x, y, z in POINTS)
    spec, binding, source = fixture(keys=(c.PathKey(0, POINTS), c.PathKey(0.5, moved)))
    clock = c.TemporalPolicy(0.1, 1, 0.125, 0.7)
    spec = replace(spec, layers=(replace(spec.layers[0], temporal=clock),))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion(), purpose='candidate-review')
    boundary = clock.start + (0.5 - clock.source_start) / clock.rate
    bundle = m.compile_timeline(timeline, (source,), engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    group = next(g for g in ET.fromstring(bundle.xml).findall('composition/group') if float(g.get('start')) == boundary)
    expected = tuple(v for point in moved for v in c.spatial_camera(timeline.base, 'shape').project(Vec3(*point)).xy)
    assert points(group.find('.//shape')) == pytest.approx(expected)


def test_spatial_path_guide_example_is_executable():
    import re
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = guide.split('## Project authored spatial paths\n', 1)
    assert len(section) == 2
    example = re.search(r'```python\n(.*?)```', section[1], re.S)
    assert example is not None
    namespace = {}
    exec(compile(example[1], 'composition-preflight.md:spatial-paths', 'exec'), namespace)
    assert namespace['compiled'].xml


def test_actual_render_registers_spatial_polygon_and_repeats_out_of_order(tmp_path, scene_render):
    import numpy as np
    import shapely
    from PIL import Image

    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    spec, binding, source = fixture()
    source = replace(
        source,
        xml=source.xml.replace(b'strokeWidth="2"', b'strokeWidth="0" strokeCap="butt"').replace(
            b'stroke="#000000"', b'stroke="#00000000"'
        ),
    )
    binding = replace(binding, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=binding.forms)))
    camera = replace(spec.camera, origin=(160, 120), scale=60)
    layer = replace(spec.layers[0], transform=c.Transform((0.3, 0.2, 0), (17, 20, 3), 0.9))
    spec = replace(spec, width=320, height=240, camera=camera, layers=(layer,))
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, camera, 'hold'), m.CameraKey(0.5, replace(camera, position=(-5, 2, 10)), 'hold'))
    )
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    compiled = m.emit_timeline(timeline, (source,), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    assert compiled.work.engine_invocations == 0
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
        active = next(span for span in timeline.spans if span.start <= time < span.end)
        view = c.spatial_camera(timeline.samples[active.scene], 'shape')
        polygon = shapely.Polygon([view.project(Vec3(*p)).xy for p in POINTS])
        y, x = np.indices((240, 320))
        centers = shapely.points(x + 0.5, y + 0.5)
        mask = shapely.contains(polygon, centers)
        away = shapely.distance(polygon.boundary, centers) > 1
        interior, exterior = mask & away, ~mask & away
        assert interior.any() and np.all(pixels[interior] == 255)
        assert np.all(pixels[exterior, :3] == 0)
        if time in seen:
            assert pixels.tobytes() == seen[time]
        seen[time] = pixels.tobytes()
