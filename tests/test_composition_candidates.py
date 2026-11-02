"""New drawings enter review with their own identity, never an approved part alias."""

import hashlib
from dataclasses import asdict, replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs.math3d import Vec3


def candidate():
    scene = Scene(version='auto')
    scene.add_project(width=64, height=64, fps='2', duration=1)
    cv = Canvas(scene, font_asset=None, width=64, height=64)
    cv.rect(cv.comp, 2, 3, 12, 9, '#DA8844')
    xml = scene.to_bytes()
    binding = c.AssetBinding(
        'tile',
        'candidate.original-tile',
        1,
        'vector',
        c.Bounds((2, 3, 0), (14, 12, 0)),
        nodes=20,
        memory_bytes=16384,
        candidate=c.CandidateSource('cutout', hashlib.sha256(xml).hexdigest()),
    )
    spec = c.ScenePlan(
        c.StylePin('cutout', c.style_revision('cutout')),
        64,
        64,
        c.FrameRate(2),
        1,
        7,
        'meter',
        c.CameraSpec(scale=1),
        c.LightRig('flat'),
        (c.LayerSpec('tile', 'tile', 1, c.TemporalPolicy(0, 1), space='screen'),),
        c.RenderBudget(),
    )
    return spec, binding, xml


def test_candidate_requires_explicit_host_review_and_keeps_unapproved_identity():
    spec, binding, xml = candidate()
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, (binding,))
    assert caught.value.to_dict()['code'] == 'composition.candidate'
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    assert plan.purpose == 'candidate-review'
    assert plan.describe()['candidates'] == [
        {
            'asset': 'tile',
            'part': 'candidate.original-tile',
            'version': 1,
            'style': 'cutout',
            'source_digest': hashlib.sha256(xml).hexdigest(),
            'approval': None,
        }
    ]
    compiled = c.compile_scene(plan, (c.VectorSource('tile', xml),))
    assert b'srstudio.candidate-review/1.0.0' in compiled.xml
    assert b'candidate.original-tile' in compiled.xml
    assert b'"approval":null' in compiled.xml
    assert compiled.plan_digest == plan.digest


@pytest.mark.parametrize('bad', ['approved-alias', 'style', 'digest', 'namespace-only', 'purpose', 'forged-plan'])
def test_candidate_policy_cannot_bypass_approval_or_host_validation(bad):
    spec, binding, xml = candidate()
    purpose = 'candidate-review'
    if bad == 'approved-alias':
        binding = replace(binding, part='papers')
    elif bad == 'style':
        binding = replace(binding, candidate=replace(binding.candidate, style='toon'))
    elif bad == 'digest':
        binding = replace(binding, candidate=replace(binding.candidate, source_digest='x' * 64))
    elif bad == 'namespace-only':
        binding = replace(binding, candidate=None)
    elif bad == 'purpose':
        purpose = True
    else:
        plan = c.preflight(spec, (binding,), purpose=purpose)
        with pytest.raises(c.CompositionError):
            c.compile_scene(replace(plan, purpose='production'), (c.VectorSource('tile', xml),))
        return
    with pytest.raises(c.CompositionError):
        c.preflight(spec, (binding,), purpose=purpose)


def test_agent_scene_json_cannot_enable_review_or_supply_candidate_binding():
    spec, _, _ = candidate()
    for key, value in [('purpose', 'candidate-review'), ('candidate', {}), ('bindings', [])]:
        with pytest.raises(c.CompositionError):
            c.parse_scene({**asdict(spec), key: value})


def test_changed_vector_content_fails_before_publication(tmp_path):
    spec, binding, xml = candidate()
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    changed = xml.replace(b'#DA8844', b'#123456')
    assert changed != xml
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(plan, (c.VectorSource('tile', changed),), tmp_path / 'scene.xml')
    assert caught.value.to_dict()['code'] == 'composition.candidate'
    assert not (tmp_path / 'scene.xml').exists()


def test_review_timeline_preserves_policy_in_samples_workers_and_output(tmp_path):
    spec, binding, xml = candidate()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('tile', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((10, 0, 0))))),
        )
    )
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    assert all(p.purpose == 'candidate-review' for p in (timeline.base, *timeline.samples, timeline.terminal))
    output = m.emit_timeline(
        timeline,
        (c.VectorSource('tile', xml),),
        tmp_path / 'review',
        engine=tmp_path / 'no-engine',
        cache=tmp_path / 'cache',
    )
    assert b'candidate.original-tile' in output.xml
    assert b'"approval":null' in output.xml
    assert output.work.engine_invocations == 0


@pytest.mark.parametrize('bad', ['budget', 'view', 'shadow', 'effect'])
def test_review_retains_existing_capability_and_budget_refusals(bad):
    spec, binding, _ = candidate()
    layer = spec.layers[0]
    if bad == 'budget':
        spec = replace(spec, budget=replace(spec.budget, max_nodes=1))
    elif bad == 'view':
        spec = replace(spec, layers=(replace(layer, space='world', transform=c.Transform(rotation=(0, 45, 0))),))
    elif bad == 'shadow':
        spec = replace(spec, layers=(replace(layer, shadow_receiver='tile'),))
    else:
        spec = replace(spec, layers=(replace(layer, effects=('grain',)),))
    with pytest.raises(c.CompositionError):
        c.preflight(spec, (binding,), purpose='candidate-review')


def raster_case(kind):
    from support.composition import plate_source, prepared_plate_plan, proxy_source
    from support.composition_proxy import plan_for as proxy_plan
    from support.composition_sequences import plan_for as sequence_plan
    from support.composition_sequences import sequence

    if kind == 'plates':
        source = plate_source()
        base, digest, prepare = prepared_plate_plan(source), c.plate_source_digest, c.prepare_plate
    elif kind == 'proxy':
        source = proxy_source(oversample=1)
        base, digest, prepare = proxy_plan(source), c.proxy_source_digest, c.prepare_proxy
    else:
        source = sequence(kind.removeprefix('sequence-'))
        base, digest, prepare = sequence_plan(source), c.raster_sequence_digest, c.prepare_raster_sequence
    binding = replace(
        base.bindings[0], part='candidate.original-box', candidate=c.CandidateSource('toon', digest(source))
    )
    return c.preflight(base.spec, (binding,), purpose='candidate-review'), source, prepare


@pytest.mark.parametrize('kind', ['plates', 'proxy', 'sequence-plates', 'sequence-proxy'])
def test_real_raster_preparation_preserves_review_identity_across_workers(kind):
    plan, source, prepare = raster_case(kind)
    result = prepare(plan, 'host', source)
    assert result.binding.candidate == plan.bindings[0].candidate
    assert result.plan_digest == plan.digest
    timeline = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), rasters=(source,), purpose=plan.purpose)
    assert timeline.base == plan
    assert c.spatial_camera(plan).project(Vec3(0, 0, 0)).xy == (32, 32)


@pytest.mark.parametrize('kind', ['plates', 'proxy', 'sequence-plates', 'sequence-proxy'])
def test_stale_raster_content_pin_fails_before_cache_access(kind, tmp_path):
    plan, source, prepare = raster_case(kind)
    binding = replace(plan.bindings[0], candidate=replace(plan.bindings[0].candidate, source_digest='a' * 64))
    stale = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    with pytest.raises(c.CompositionError) as caught:
        prepare(stale, 'host', source)
    assert caught.value.to_dict()['code'] == 'composition.candidate'
    with pytest.raises(c.CompositionError) as caught:
        m.plan_scene(stale.spec, stale.bindings, m.SceneMotion(), rasters=(source,), purpose=stale.purpose)
    assert caught.value.to_dict()['code'] == 'composition.candidate'
    assert list(tmp_path.iterdir()) == []


def test_production_vector_scene_and_plan_retain_pre_feature_fingerprints():
    from support.composition import paper

    spec, binding, xml = paper()
    plan = c.preflight(spec, (binding,))
    result = c.compile_scene(plan, (c.VectorSource(binding.id, xml),))
    assert plan.digest == '2c4d987d798e77917fd14a8e64de22607e06fd8f66f6398a59ee520df67a2a91'
    assert result.digest == '0a42eedbc50ab57df2ee2a0bb8e57719cb7f8d855a527eca7151b53306e2ef06'
    assert b'candidate-review' not in result.xml


def test_review_is_not_an_approval_bypass_for_registered_bindings(monkeypatch):
    from srstudio import registry
    from support.composition import paper

    spec, binding, _ = paper()
    monkeypatch.setattr(registry.get('prop', 'papers'), 'builder', lambda *args, **kwargs: None)
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, (binding,), purpose='candidate-review')
    assert caught.value.to_dict()['code'] == 'composition.version'


def test_candidate_comment_preserves_valid_xml_for_hyphenated_names():
    import xml.etree.ElementTree as ET

    spec, binding, xml = candidate()
    binding = replace(binding, part='candidate.two--hyphens')
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    result = c.compile_scene(plan, (c.VectorSource(binding.id, xml),))
    assert ET.fromstring(result.xml).tag == 'scene'
    assert b'two\\u002d\\u002dhyphens' in result.xml


def test_forged_review_description_is_revalidated():
    spec, binding, _ = candidate()
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    with pytest.raises(c.CompositionError):
        replace(plan, digest='a' * 64).describe()


def test_one_candidate_version_cannot_name_conflicting_content():
    spec, binding, _ = candidate()
    other = replace(binding, id='other', candidate=replace(binding.candidate, source_digest='b' * 64))
    spec = replace(spec, layers=(*spec.layers, replace(spec.layers[0], id='other', asset='other')))
    with pytest.raises(c.CompositionError) as caught:
        c.preflight(spec, (binding, other), purpose='candidate-review')
    assert caught.value.to_dict()['code'] == 'composition.candidate'


def test_documented_candidate_recipe_executes():
    import re
    from pathlib import Path

    text = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = text.split('## Review a new candidate drawing\n', 1)[1].split('\n## ', 1)[0]
    recipe = re.search(r'```python\n(.*?)\n```', section, re.DOTALL)[1]
    namespace = {}
    exec(compile(recipe, 'docs/composition-preflight.md', 'exec'), namespace)
    assert namespace['compiled'].plan_digest == namespace['plan'].digest


@pytest.mark.parametrize('kind', ['plates', 'proxy', 'sequence-plates', 'sequence-proxy'])
def test_candidate_mixed_bundle_renders_and_reuses_warm_cache(kind, tmp_path, scene_render):
    from srstudio import plates
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    plan, source, prepare = raster_case(kind)
    _, mark, xml = candidate()
    mark = replace(mark, candidate=replace(mark.candidate, style='toon'))
    layer = c.LayerSpec('tile', 'tile', 1, c.TemporalPolicy(0, plan.spec.duration), role='information', space='screen')
    spec = replace(plan.spec, layers=(*plan.spec.layers, layer), fps=c.FrameRate(2))
    plan = c.preflight(spec, (*plan.bindings, mark), purpose=plan.purpose)
    assets = (prepare(plan, 'host', source), c.VectorSource('tile', xml))
    cold = c.emit_bundle(plan, assets, tmp_path / 'cold', engine=scene_render, cache=tmp_path / 'cache')
    assert cold.work.engine_invocations > 0
    assert b'"approval":null' in cold.xml
    with plates.render_session(max_invocations=0):
        warm = c.emit_bundle(plan, assets, tmp_path / 'warm', engine=scene_render, cache=tmp_path / 'cache')
    assert cold.xml == warm.xml and cold.resources == warm.resources
    assert warm.work.engine_invocations == 0
    timeline = m.plan_scene(spec, plan.bindings, m.SceneMotion(), rasters=(source,), purpose=plan.purpose)
    with plates.render_session(max_invocations=0):
        result = m.emit_timeline(
            timeline,
            (c.VectorSource('tile', xml),),
            tmp_path / 'timeline',
            engine=scene_render,
            cache=tmp_path / 'cache',
        )
    assert result.work.engine_invocations == 0
    with held():
        run(
            (
                str(scene_render),
                'render',
                str(tmp_path / 'timeline/scene.xml'),
                '--output',
                str(tmp_path / 'preview.png'),
                '--time',
                '0',
                '--quality',
                'final',
                '--strict',
                '--json',
            ),
            input=b'',
            limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536),
        )
    from PIL import Image

    with Image.open(tmp_path / 'preview.png') as image:
        assert image.size == (64, 64)
        assert image.convert('RGBA').getpixel((5, 6)) == (218, 136, 68, 255)


@pytest.mark.parametrize('change', [None, 'purpose', 'missing-purpose', 'approval', 'pin', 'alias', 'source'])
def test_worker_protocol_revalidates_review_policy_and_source(change):
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    spec, binding, xml = candidate()
    plan = c.preflight(spec, (binding,), purpose='candidate-review')
    request = {
        'schema': wire.SCHEMA,
        'operation': 'compile',
        'plan': asdict(plan),
        'assets': [{'id': 'tile', 'xml': wire.xml_encode(xml), 'prepared': None}],
    }
    if change == 'purpose':
        request['plan']['purpose'] = 'production'
    elif change == 'missing-purpose':
        del request['plan']['purpose']
    elif change == 'approval':
        request['plan']['bindings'][0]['candidate']['approval'] = True
    elif change == 'pin':
        request['plan']['bindings'][0]['candidate']['source_digest'] = 'a' * 64
    elif change == 'alias':
        request['plan']['bindings'][0]['part'] = 'papers'
    elif change == 'source':
        request['assets'][0]['xml'] = wire.xml_encode(xml.replace(b'#DA8844', b'#123456'))
    if change is not None:
        with pytest.raises(c.CompositionError):
            dispatch(wire.dumps(request))
    else:
        result = dispatch(wire.dumps(request))
        assert result['status'] == 'ok'
        assert b'"approval":null' in wire.xml_decode(result['xml'])
