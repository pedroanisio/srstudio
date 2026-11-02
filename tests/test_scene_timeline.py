"""Whole-scene motion schedules retain clocks and enforce aggregate work bounds."""

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from support.composition import paper, plate_source, prepared_plate_plan


def fixture():
    source = plate_source()
    base = prepared_plate_plan(source)
    spec = replace(base.spec, fps=c.FrameRate(4))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.1, 0, 0))))),
        )
    )
    return spec, base.bindings, motion, source


def plan(spec, bindings, motion, sources):
    return m.plan_scene(spec, bindings, motion, rasters=sources)


def test_timeline_covers_the_clip_on_the_exact_output_clock():
    spec, bindings, motion, source = fixture()
    timeline = plan(spec, bindings, motion, (source,))
    assert [(s.start, s.end) for s in timeline.spans] == [(0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1)]
    assert [timeline.samples[s.scene].spec.layers[0].transform.translation[0] for s in timeline.spans] == pytest.approx(
        [0, 0.025, 0.05, 0.075]
    )
    assert timeline.cost.frames == 4
    assert timeline.cost.output_pixels == 4 * 64 * 64
    assert timeline.cost.unique_plates == timeline.cost.engine_invocations == 4
    assert timeline.cost.samples == 4 * bindings[0].plates[0].samples * 64 * 64
    assert timeline == plan(spec, bindings, motion, (source,))
    assert all(sample.spec.layers[0].temporal == spec.layers[0].temporal for sample in timeline.samples)
    with pytest.raises(FrozenInstanceError):
        timeline.digest = ''


def test_static_views_coalesce_without_charging_for_every_output_frame():
    spec, bindings, _, source = fixture()
    timeline = plan(spec, bindings, m.SceneMotion(), (source,))
    assert len(timeline.spans) == len(timeline.samples) == 1
    assert (timeline.spans[0].start, timeline.spans[0].end) == (0, 1)
    assert timeline.cost.frames == 4
    assert timeline.cost.unique_plates == 1


def test_held_off_grid_cut_and_repeated_views_reuse_work():
    spec, bindings, _, source = fixture()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'host',
                (
                    m.TransformKey(0, c.Transform(), 'hold'),
                    m.TransformKey(0.3, c.Transform((0.1, 0, 0)), 'hold'),
                    m.TransformKey(0.6, c.Transform()),
                ),
            ),
        )
    )
    timeline = plan(spec, bindings, motion, (source,))
    assert [(s.start, s.end) for s in timeline.spans] == [(0, 0.3), (0.3, 0.6), (0.6, 1)]
    assert [s.scene for s in timeline.spans] == [0, 1, 0]
    assert timeline.cost.unique_plates == 2


def test_fractional_fps_does_not_accumulate_clock_error():
    spec, bindings, motion, source = fixture()
    spec = replace(spec, fps=c.FrameRate(30000, 1001))
    timeline = plan(spec, bindings, motion, (source,))
    assert [s.start for s in timeline.spans] == [float(Fraction(n * 1001, 30000)) for n in range(30)]
    assert timeline.spans[-1].end == 1
    assert timeline.cost.frames == 30


@pytest.mark.parametrize(
    'limit', ['max_new_plates', 'max_engine_invocations', 'max_samples', 'max_nodes', 'max_memory_bytes']
)
def test_combined_budget_rejects_a_sequence_of_individually_affordable_views(limit):
    spec, bindings, motion, source = fixture()
    single = m.sample_scene(spec, bindings, motion, 0)
    cost = {
        'max_new_plates': single.cost.unique_plates,
        'max_engine_invocations': single.cost.engine_invocations,
        'max_samples': single.cost.samples,
        'max_nodes': single.cost.nodes,
        'max_memory_bytes': single.cost.memory_bytes,
    }
    restricted = replace(spec, budget=replace(spec.budget, **{limit: cost[limit]}))
    c.preflight(restricted, bindings)
    with pytest.raises(c.CompositionError, match=limit):
        plan(restricted, bindings, motion, (source,))


def sequence_fixture():
    spec, bindings, motion, first = fixture()
    second = replace(first, materials=(replace(first.materials[0], color='#00AAFF'),))
    source = c.RasterSequence(
        'host', 2, (c.RasterFrame(0, first), c.RasterFrame(0.5, second), c.RasterFrame(1.5, first))
    )
    binding = replace(bindings[0], duration=2, plates=c.raster_jobs(source, width=64, height=64, memory_bytes=1024**2))
    layer = replace(spec.layers[0], temporal=c.TemporalPolicy(0.1, 0.85, 0.25, 2))
    return replace(spec, layers=(layer,)), (binding,), source


def test_source_snapshot_windows_map_once_and_hidden_spans_do_not_render():
    spec, bindings, source = sequence_fixture()
    timeline = plan(spec, bindings, m.SceneMotion(), (source,))
    active = [s for s in timeline.spans if s.rasters]
    assert [(s.start, s.end, s.rasters[0].frame) for s in active] == [
        (0.1, 0.225, 0),
        (0.225, 0.725, 1),
        (0.725, 0.85, 2),
    ]
    assert timeline.spans[0].layers == () and timeline.spans[-1].layers == ()
    assert timeline.cost.unique_plates == 2
    assert timeline.rasters == (source,)


def test_only_visible_source_jobs_are_charged():
    spec, bindings, source = sequence_fixture()
    spec = replace(spec, layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0.1, 0.2, 0.75, 1)),))
    timeline = plan(spec, bindings, m.SceneMotion(), (source,))
    assert timeline.cost.unique_plates == 1
    assert [s.rasters[0].frame for s in timeline.spans if s.rasters] == [1]


def test_camera_light_and_parent_changes_all_distinguish_render_work():
    spec, bindings, _, source = fixture()
    light = spec.lights.lights[0]
    motions = (
        m.SceneMotion(
            camera=(
                m.CameraKey(0, spec.camera),
                m.CameraKey(1, replace(spec.camera, position=(0.1, 0, 10), target=(0.1, 0, 0))),
            )
        ),
        m.SceneMotion(
            lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, intensity=0.2)))),)
        ),
        m.SceneMotion(
            transforms=(
                m.TransformTrack(
                    'host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform(rotation=(0, 0, 90))))
                ),
            )
        ),
    )
    for motion in motions:
        assert plan(spec, bindings, motion, (source,)).cost.unique_plates == 4


def test_duplicate_placements_share_jobs_but_have_separate_spans():
    spec, bindings, motion, source = fixture()
    child = replace(spec.layers[0], id='child', parent='host')
    spec = replace(spec, layers=(*spec.layers, child))
    timeline = plan(spec, bindings, motion, (source,))
    assert timeline.cost.unique_plates == 4
    assert all(len(s.rasters) == 2 for s in timeline.spans)


def test_vector_timeline_requires_no_raster_inputs_and_preserves_source_animation():
    spec, binding, _ = paper(animated=True)
    spec = replace(spec, fps=c.FrameRate(4))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('paper', (m.TransformKey(0, c.Transform()), m.TransformKey(2, c.Transform((10, 0, 0))))),
        )
    )
    timeline = plan(spec, (binding,), motion, ())
    assert timeline.cost.unique_plates == timeline.cost.engine_invocations == 0
    assert len(timeline.spans) == 8
    assert all(not s.rasters and s.layers == ('paper',) for s in timeline.spans)


@pytest.mark.parametrize(
    'bad', ['missing', 'extra', 'mutable', 'duplicate', 'backend', 'source-key', 'sequence-clock', 'bytes', 'overscan']
)
def test_untrusted_or_incomplete_raster_inputs_are_refused(bad):
    spec, bindings, motion, source = fixture()
    sources = (source,)
    if bad == 'missing':
        sources = ()
    elif bad == 'extra':
        sources = (source, replace(source, id='extra'))
    elif bad == 'mutable':
        sources = [source]
    elif bad == 'duplicate':
        sources = (source, source)
    elif bad == 'backend':
        sources = (object(),)
    elif bad == 'source-key':
        sources = (replace(source, materials=(replace(source.materials[0], color='#FF0000'),)),)
    elif bad == 'sequence-clock':
        spec, bindings, sequence = sequence_fixture()
        sources = (replace(sequence, duration=3),)
    elif bad == 'bytes':
        sources = (replace(source, meshes=(replace(source.meshes[0], vertices=b'x' * (8 * 1024**2 + 1)),)),)
    else:
        motion = m.SceneMotion(
            camera=(m.CameraKey(0, spec.camera), m.CameraKey(1, replace(spec.camera, origin=(0, 32))))
        )
    with pytest.raises(c.CompositionError):
        plan(spec, bindings, motion, sources)


def test_intermediate_invalid_camera_is_checked_even_when_authored_endpoints_are_valid():
    spec, bindings, _, source = fixture()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera), m.CameraKey(1, replace(spec.camera, position=(0, 0, -10))))
    )
    with pytest.raises(c.CompositionError, match='camera'):
        plan(spec, bindings, motion, (source,))


def test_terminal_view_is_checked_but_never_rendered_as_an_extra_frame():
    spec, bindings, _, source = fixture()
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera, 'hold'), m.CameraKey(1, replace(spec.camera, position=(0, 0, 0))))
    )
    with pytest.raises(c.CompositionError):
        plan(spec, bindings, motion, (source,))


def test_planning_never_launches_a_worker_renderer_or_reads_a_cache(monkeypatch):
    from srstudio import _composition_runtime, plates

    def refuse(*args, **kwargs):
        pytest.fail('planning must not launch execution')

    monkeypatch.setattr(_composition_runtime, '_call', refuse)
    monkeypatch.setattr(plates, '_engine_render', refuse)
    spec, bindings, motion, source = fixture()
    assert plan(spec, bindings, motion, (source,)).cost.unique_plates == 4


def test_identical_parent_paths_fit_one_job_and_match_prepared_render_identity():
    from srstudio._composition_bundle import _key

    spec, bindings, _, source = fixture()
    child = replace(spec.layers[0], id='child', parent='host')
    spec = replace(spec, layers=(*spec.layers, child), budget=replace(spec.budget, max_new_plates=1))
    checked = c.preflight(spec, bindings)
    assert checked.cost.unique_plates == 1
    a = c.prepare_plate(checked, 'host', source)
    b = c.prepare_plate(checked, 'child', source)
    assert _key(a, 'e' * 64) == _key(b, 'e' * 64)
    assert plan(spec, bindings, m.SceneMotion(), (source,)).cost.unique_plates == 1


@pytest.mark.parametrize('kind', ['frames', 'events', 'records', 'contact-samples'])
def test_timeline_expansion_and_contact_proofs_are_bounded(kind, monkeypatch):
    spec, bindings, motion, source = fixture()
    if kind == 'frames':
        monkeypatch.setattr(m, 'MAX_TIMELINE_SAMPLES', 3)
    elif kind == 'events':
        monkeypatch.setattr(m, 'MAX_TIMELINE_SAMPLES', 4)
        motion = replace(motion, camera=(m.CameraKey(0, spec.camera), m.CameraKey(0.1, spec.camera)))
    elif kind == 'records':
        monkeypatch.setattr(m, 'MAX_TIMELINE_RECORDS', 1)
    else:
        a = replace(spec.layers[0], id='a', parent='host')
        b = replace(a, id='b')
        spec = replace(
            spec,
            layers=(*spec.layers, a, b),
            contacts=(c.ContactSpec('a', 'grip', 'b', 'grip', 0, 1),),
            budget=replace(spec.budget, max_contact_samples=2),
        )
        bindings = (replace(bindings[0], anchors=(c.Anchor('grip', (0, 0, 0)),)),)
    with pytest.raises(c.CompositionError):
        plan(spec, bindings, motion, (source,))


def proxy_fixture():
    from support.composition import proxy_source

    spec, bindings, _, _ = fixture()
    source = proxy_source(oversample=1)
    binding = replace(
        bindings[0],
        backend='proxy',
        memory_bytes=64 * 1024**2,
        plates=c.proxy_jobs(source, width=64, height=64, memory_bytes=8 * 1024**2),
    )
    return spec, (binding,), source


def test_proxy_id_pass_is_reused_when_only_world_light_intensity_changes():
    spec, bindings, source = proxy_fixture()
    light = spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, intensity=0.2)))),)
    )
    timeline = plan(spec, bindings, motion, (source,))
    # Four light passes, one stable part-ID pass.
    assert timeline.cost.unique_plates == 5


@pytest.mark.parametrize('bad', ['under', 'passes', 'proxy-memory', 'oversample', 'input-memory', 'job-samples'])
def test_all_raster_views_and_declared_conversion_work_are_checked(bad):
    spec, bindings, source = proxy_fixture()
    if bad == 'under':
        spec = replace(spec, layers=(replace(spec.layers[0], passes=('under',)),))
    elif bad == 'passes':
        spec = replace(spec, layers=(replace(spec.layers[0], passes=('back', 'front')),))
    elif bad == 'proxy-memory':
        bindings = (replace(bindings[0], memory_bytes=4096),)
    elif bad == 'oversample':
        source = replace(source, recipe=replace(source.recipe, oversample=4))
        spec = replace(spec, budget=replace(spec.budget, max_frame_pixels=4096))
    elif bad == 'input-memory':
        bindings = (replace(bindings[0], memory_bytes=1),)
    else:
        bindings = (replace(bindings[0], plates=tuple(replace(j, samples=1) for j in bindings[0].plates)),)
    with pytest.raises(c.CompositionError):
        plan(spec, bindings, m.SceneMotion(), (source,))


def test_retained_scene_metadata_is_included_in_memory_work():
    import json
    from dataclasses import asdict

    spec, binding, _ = paper()
    # Tiny declared drawing work must not erase the planner's own storage.
    binding = replace(binding, nodes=1, memory_bytes=1)
    spec = replace(spec, fps=c.FrameRate(4))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('paper', (m.TransformKey(0, c.Transform()), m.TransformKey(2, c.Transform((10, 0, 0))))),
        )
    )
    timeline = plan(spec, (binding,), motion, ())
    records = {*[sample.digest for sample in timeline.samples], timeline.terminal.digest}
    retained = {sample.digest: sample for sample in (*timeline.samples, timeline.terminal)}
    encoded = sum(len(json.dumps(asdict(retained[key]), separators=(',', ':')).encode()) for key in records)
    assert timeline.cost.memory_bytes >= timeline.base.cost.memory_bytes + encoded * 8


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_aggregate_job_estimate_matches_actual_prepared_renderer_identities(backend):
    from srstudio._composition_bundle import _key

    if backend == 'plates':
        spec, bindings, _, source = fixture()
    else:
        spec, bindings, source = proxy_fixture()
    light = spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(m.LightTrack('ambient', (m.LightKey(0, light), m.LightKey(1, replace(light, intensity=0.2)))),)
    )
    timeline = plan(spec, bindings, motion, (source,))
    actual = set()
    for span in timeline.spans:
        sampled = timeline.samples[span.scene]
        prepared = (
            c.prepare_plate(sampled, 'host', source)
            if backend == 'plates'
            else c.prepare_proxy(sampled, 'host', source)
        )
        passes = prepared.passes if isinstance(prepared, c.PreparedProxy) else (prepared,)
        actual.update(_key(asset, 'e' * 64) for asset in passes)
    assert len(actual) == timeline.cost.unique_plates


def test_documented_timeline_example_executes():
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = guide.split('## Plan a scene timeline\n', 1)[1]
    snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
    namespace = {}
    exec(compile(snippet, '<scene-timeline-guide>', 'exec'), namespace)
    assert len(namespace['timeline'].spans) == 4
    assert namespace['timeline'].cost.unique_plates == 4


@pytest.mark.parametrize('cut', [False, True])
def test_long_constant_or_held_clips_do_not_expand_into_pointless_frame_samples(cut):
    spec, bindings, _, source = fixture()
    spec = replace(
        spec,
        duration=600,
        fps=c.FrameRate(120),
        layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0, 600)),),
        budget=replace(spec.budget, max_frames=72000),
    )
    motion = (
        m.SceneMotion(
            transforms=(
                m.TransformTrack(
                    'host', (m.TransformKey(0, c.Transform(), 'hold'), m.TransformKey(300, c.Transform((0.1, 0, 0))))
                ),
            )
        )
        if cut
        else m.SceneMotion()
    )
    timeline = plan(spec, bindings, motion, (source,))
    assert timeline.cost.frames == 72000
    assert len(timeline.spans) == len(timeline.samples) == (2 if cut else 1)
    assert timeline.cost.unique_plates == (2 if cut else 1)
