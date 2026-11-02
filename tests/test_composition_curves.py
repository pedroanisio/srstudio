"""Native rig curves retain their geometry and clocks inside proven source envelopes."""

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from support.composition import paper
from support.composition_curves import figure_source
from support.composition_emission import evaluate


@pytest.fixture(params=['public', 'worker'])
def prepare(request):
    from srstudio import _composition_vector

    return c.prepare_vector if request.param == 'public' else _composition_vector.prepare_vector


def source(curve='spring', values=(0, 30, -10, 20), *, carry=True):
    spec, _, _ = paper()
    root = ET.fromstring(
        '<scene version="1.1"><project width="320" height="240" fps="24" duration="2"/>'
        '<composition><group id="moving" x="100" y="100">'
        '<shape id="box" shape="rect" width="10" height="10" fill="#123456"/>'
        '</group></composition></scene>'
    )
    animation = ET.SubElement(
        root.find('.//group'), 'animate', property='x', defaultInterpolation=curve, timeBase='local'
    )
    for i, value in enumerate(values):
        key = ET.SubElement(animation, 'key', time=str(i * 2 / (len(values) - 1)), value=str(value))
        if curve == 'spring':
            key.attrib.update(stiffness='100', damping='6', mass='1', carry=str(carry and i > 0).lower())
    xml = ET.tostring(root)
    binding = c.AssetBinding(
        'curve',
        'candidate.native-curve',
        1,
        'vector',
        c.Bounds((-5000, -5000, 0), (5000, 5000, 0)),
        duration=2,
        nodes=100,
        memory_bytes=1024**2,
        candidate=c.CandidateSource('cutout', hashlib.sha256(xml).hexdigest()),
    )
    spec = replace(spec, layers=(c.LayerSpec('curve', 'curve', 1, c.TemporalPolicy(0, 2), space='screen'),))
    return spec, binding, xml


def pin(binding, root):
    xml = ET.tostring(root)
    return replace(binding, candidate=replace(binding.candidate, source_digest=hashlib.sha256(xml).hexdigest())), xml


@pytest.mark.parametrize('curve', ['spring', 'catmull-rom', 'tcb'])
def test_native_curves_are_preserved_and_include_interior_excursions(curve, prepare):
    _, binding, xml = source(curve, (0, 30, 30, 0))
    root = ET.fromstring(xml)
    root.find('.//group').set('x', '0')
    binding, xml = pin(binding, root)
    prepared = prepare(binding, xml)
    assert prepared.xml == xml
    assert prepared.bounds.maximum[0] > 40
    assert prepared.bounds.minimum[0] <= 0


@pytest.mark.parametrize('curve', ['spring', 'catmull-rom', 'tcb'])
def test_endpoint_only_bounds_are_refused_for_overshooting_curves(curve, prepare):
    _, binding, xml = source(curve, (0, 30, 30, 0))
    binding = replace(binding, bounds=c.Bounds((0, 0, 0), (110, 110, 0)))
    # The authored static x=100 also belongs to the envelope. Use a zero base
    # to isolate the missing interior excursion from static placement.
    root = ET.fromstring(xml)
    root.find('.//group').set('x', '0')
    binding, xml = pin(replace(binding, bounds=c.Bounds((0, 100, 0), (40, 110, 0))), root)
    with pytest.raises(c.CompositionError) as error:
        prepare(binding, xml)
    assert error.value.to_dict()['path'] == 'payload.bounds'


@pytest.mark.parametrize(
    'bad',
    [
        'zero-mass',
        'negative-damping',
        'nan-stiffness',
        'carry',
        'chain',
        'opacity',
        'custom-tcb',
        'irrelevant',
        'visibility',
        'overflow',
    ],
)
def test_unbounded_or_malformed_curve_inputs_are_refused_before_output(bad, tmp_path, prepare):
    spec, binding, xml = source(values=tuple(range(12)) if bad == 'chain' else (0, 30, -10, 20))
    root = ET.fromstring(xml)
    animation = root.find('.//animate')
    if bad == 'chain':
        pass
    elif bad == 'irrelevant':
        animation[0].set('interpolation', 'linear')
    elif bad == 'visibility':
        animation.set('property', 'visible')
        for key in animation:
            key.set('value', 'true')
    elif bad == 'overflow':
        animation[0].attrib = {'time': '0', 'value': '0', 'interpolation': 'linear'}
        animation[1].set('time', '0.000001')
        animation[1].set('value', '1e9')
        animation[1].set('stiffness', '1e-9')
    elif bad == 'opacity':
        animation.set('property', 'opacity')
        for key, value in zip(animation, ('0', '1', '1', '0'), strict=True):
            key.set('value', value)
    else:
        name, value = {
            'zero-mass': ('mass', '0'),
            'negative-damping': ('damping', '-1'),
            'nan-stiffness': ('stiffness', 'nan'),
            'carry': ('carry', 'yes'),
            'custom-tcb': ('tension', '1'),
        }[bad]
        animation[0].set(name, value)
    binding, xml = pin(binding, root)
    with pytest.raises(c.CompositionError):
        prepare(binding, xml)
    with pytest.raises(c.CompositionError):
        c.emit_scene(
            c.preflight(spec, (binding,), purpose='candidate-review'),
            (c.VectorSource('curve', xml),),
            tmp_path / 'out.xml',
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('first', ['hold', 'linear', 'sine-in-out', 'circ-out', 'expo-out'])
def test_mixed_interpolation_preserves_native_carry_inputs(first, prepare):
    _, binding, xml = source(values=(0, 1, 1))
    root = ET.fromstring(xml)
    root.find('.//animate')[0].attrib = {'time': '0', 'value': '0', 'interpolation': first}
    binding, xml = pin(binding, root)
    prepared = prepare(binding, xml)
    assert prepared.xml == xml
    assert prepared.bounds.minimum[0] <= 0 and prepared.bounds.maximum[0] >= 11


def test_a_single_spring_key_is_a_bounded_hold(prepare):
    _, binding, xml = source(values=(5, 5))
    root = ET.fromstring(xml)
    animation = root.find('.//animate')
    animation.remove(animation[1])
    binding, xml = pin(binding, root)
    prepared = prepare(binding, xml)
    assert prepared.bounds.minimum[0] == 5


def test_actual_hybrid_face_source_is_accepted_without_rewriting_its_animation(monkeypatch):
    binding, xml = figure_source(monkeypatch)
    prepared = c.prepare_vector(binding, xml)
    assert prepared.xml == xml
    assert b'face-blend-eyes' in prepared.xml and b'defaultInterpolation="spring"' in prepared.xml


def test_real_hybrid_face_pixels_survive_shared_timeline_compilation(monkeypatch, scene_render, tmp_path):
    from srstudio import plates
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    binding, xml = figure_source(monkeypatch)
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        1080,
        1920,
        c.FrameRate(24),
        6,
        17,
        'meter',
        c.CameraSpec(),
        c.LightRig('flat'),
        (c.LayerSpec('figure', 'figure', 1, c.TemporalPolicy(0, 6), space='screen'),),
        c.RenderBudget(),
    )
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera, 'hold'), m.CameraKey(4, replace(spec.camera, origin=(1, 1)), 'hold'))
    )
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    result = m.emit_timeline(
        timeline, (c.VectorSource('figure', xml),), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache'
    )
    assert len(timeline.spans) == 2 and result.work.engine_invocations == 0
    original = tmp_path / 'original.xml'
    original.write_bytes(xml)
    hashes = set()
    for time in (4.05, 3.95, 4.0):
        images = []
        for name, path in (('original', original), ('compiled', tmp_path / 'bundle/scene.xml')):
            output = tmp_path / f'{name}-{time}.png'
            with held():
                run(
                    (
                        str(scene_render),
                        'render',
                        str(path),
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
                    limits=ProcessLimits(timeout=120),
                )
            images.append(plates.pixels(output))
        assert images[0].shape == (1920, 1080, 4)
        assert (images[0] == images[1]).all()
        hashes.add(hashlib.sha256(images[0].tobytes()).hexdigest())
    assert len(hashes) == 3  # The cut lies inside a changing expression, not a static fixture.


@pytest.mark.parametrize('curve', ['spring', 'catmull-rom', 'tcb'])
def test_engine_values_stay_in_bounds_and_survive_a_timeline_cut(curve, scene_render, tmp_path):
    spec, binding, xml = source(curve)
    prepared = c.prepare_vector(binding, xml)
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera, 'hold'), m.CameraKey(0.85, replace(spec.camera, origin=(15, 20)), 'hold'))
    )
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    bundle = m.emit_timeline(
        timeline, (c.VectorSource('curve', xml),), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache'
    )
    assert bundle.work.engine_invocations == 0
    original = tmp_path / 'original.xml'
    original.write_bytes(xml)
    for time in (0.13, 0.61, 0.849, 0.85, 0.851, 1.12, 1.73):
        old = next(n for n in evaluate(scene_render, original, time) if n['id'] == 'box')
        new = next(
            n
            for n in evaluate(scene_render, tmp_path / 'bundle/scene.xml', time)
            if n['id'].endswith('__box') and n['draw']
        )
        assert new['world'] == pytest.approx(old['world'])
        assert prepared.bounds.minimum[0] <= old['world'][4] <= prepared.bounds.maximum[0] - 10


def test_carried_spring_envelope_covers_exponential_endpoint_snap(scene_render, tmp_path):
    _, binding, xml = source(values=(0, 1000, 1000))
    root = ET.fromstring(xml)
    root.find('project').set('duration', '101')
    animation = root.find('.//animate')
    animation[0].attrib = {'time': '0', 'value': '0', 'interpolation': 'expo-out'}
    animation[1].set('time', '100')
    animation[2].set('time', '101')
    binding, xml = pin(replace(binding, duration=101), root)
    prepared = c.prepare_vector(binding, xml)
    path = tmp_path / 'source.xml'
    path.write_bytes(xml)
    value = next(n for n in evaluate(scene_render, path, 100.15) if n['id'] == 'box')['world'][4]
    assert prepared.bounds.minimum[0] <= value <= prepared.bounds.maximum[0] - 10


def test_constant_carried_spring_accounts_for_native_roundoff(scene_render, tmp_path):
    _, binding, xml = source(values=(1e8,) * 9)
    root = ET.fromstring(xml)
    for i, key in enumerate(root.find('.//animate')):
        key.set('time', str(i * 1e-5))
    binding, xml = pin(replace(binding, bounds=c.Bounds((-2e8, -2e8, 0), (2e8, 2e8, 0))), root)
    prepared = c.prepare_vector(binding, xml)
    path = tmp_path / 'source.xml'
    path.write_bytes(xml)
    for time in (1.5e-5, 3.5e-5, 6.5e-5, 7.5e-5):
        value = next(n for n in evaluate(scene_render, path, time) if n['id'] == 'box')['world'][4]
        assert prepared.bounds.minimum[0] <= value <= prepared.bounds.maximum[0] - 10
