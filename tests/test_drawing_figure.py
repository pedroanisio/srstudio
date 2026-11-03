"""The native figure retains its source clock in the shared world candidate."""

import importlib
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import Vec3


@pytest.fixture(autouse=True)
def example_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))


@pytest.fixture(scope='module')
def study():
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(Path(__file__).parents[1]))
        return importlib.import_module('examples.drawing_figure').figure_scene()


def test_native_figure_joins_full_world_without_relabeling_picture_or_copying_meshes(study):
    timeline = study.timeline
    assert timeline.base.purpose == 'candidate-review'
    assert len(timeline.spans) == 66  # Repeated samples in the held opening share one interval.
    assert len(timeline.rasters) == 1
    assert timeline.cost.engine_invocations == 28
    assert timeline.cost.nodes < timeline.base.spec.budget.max_nodes
    assert len(study.vectors) == 3
    binding = next(b for b in timeline.base.bindings if b.id == 'figure')
    assert binding.forms == (c.FormSurface('figure', mode='ink'),)
    assert binding.candidate.source_digest == c.vector_source_digest(study.vectors[-1], forms=binding.forms)
    layers = timeline.base.spec.layers
    assert [layer.id for layer in layers] == ['floor', 'shadow', 'figure-back', 'car', 'figure-front']
    assert all(layer.space == 'world' and layer.role == 'picture' for layer in layers)
    assert layers[2].temporal == c.TemporalPolicy(0, 3, state='figure')
    assert layers[4].temporal == c.TemporalPolicy(3, 6, 3, continuity='cut', state='figure')


def test_figure_root_registers_to_world_on_both_sides_of_depth_and_camera_cuts(study):
    from examples.drawing_figure import world_root
    from examples.drawing_proof import sample

    binding = next(b for b in study.timeline.base.bindings if b.id == 'figure')
    anchor = Vec3(*binding.anchors[0].position)
    for span in reversed(study.timeline.spans):
        plan = study.timeline.samples[span.scene]
        layer = 'figure-back' if span.start < 3 else 'figure-front'
        assert layer in span.layers
        root = world_root(span.start)
        assert c.spatial_camera(plan, layer).project(anchor).xy == pytest.approx(
            sample(span.start).view.project(((root.x, root.y, -root.z),))[0], abs=1e-9
        )
        clock = next(item.temporal for item in plan.spec.layers if item.id == layer)
        assert clock.source_start + (span.start - clock.start) * clock.rate == pytest.approx(span.start)


def test_unsupported_figure_profile_is_refused(study):
    plan = study.timeline.base
    layers = list(plan.spec.layers)
    layers[2] = replace(layers[2], transform=replace(layers[2].transform, rotation=(0, 90, 0)))
    with pytest.raises(c.CompositionError, match='frontal'):
        c.preflight(replace(plan.spec, layers=tuple(layers)), plan.bindings, purpose=plan.purpose)


def test_opening_holds_the_world_and_keeps_the_figure_to_the_left_of_the_car(study):
    initial = next(s for s in study.timeline.spans if s.start <= 0 < s.end)
    quarter = next(s for s in study.timeline.spans if s.start <= 0.25 < s.end)
    assert initial.scene == quarter.scene
    source = next(b for b in study.timeline.base.bindings if b.id == 'figure')
    point = c.spatial_camera(study.timeline.base, 'figure-back').project(Vec3(*source.anchors[0].position))
    assert 200 < point.xy[0] < 350


@pytest.mark.parametrize('time', [-0.01, 6.01, float('nan'), True])
def test_invalid_root_clock_is_refused(time):
    from examples.drawing_figure import world_root

    with pytest.raises(ValueError):
        world_root(time)


def test_authored_root_hold_and_depth_cut_are_explicit():
    from examples.drawing_figure import world_root

    assert world_root(0) == world_root(0.25) == world_root(0.5) == Vec3(-210, 0, -115)
    assert world_root(3 - 1e-6).distance(Vec3(-230, 0, -115)) < 1e-9
    assert world_root(3) == Vec3(-110, 0, 115)
    assert world_root(6) == Vec3(40, 0, 115)


def test_ground_anchor_uses_the_actual_bento_sole_coordinate_system():
    from examples.drawing_figure import ROOT

    from srstudio import toon_bento as bento
    from srstudio.toon import fx, fy

    # The foot path ends at drawing y=881. Bento maps his original drawing
    # into Toon reference space before the native frame conversion.
    sole = bento._at(bento.PIVOT_X, 881)
    assert ROOT == (fx(sole[0]), fy(sole[1]), 0)


def vector_scene(study, *, floor=False):
    layers = tuple(
        layer for layer in study.timeline.base.spec.layers if layer.asset == 'figure' or (floor and layer.id == 'floor')
    )
    names = {layer.id for layer in layers}
    assets = {layer.asset for layer in layers}
    spec = replace(study.timeline.base.spec, layers=layers)
    bindings = tuple(b for b in study.timeline.base.bindings if b.id in assets)
    motion = replace(
        study.timeline.motion, transforms=tuple(t for t in study.timeline.motion.transforms if t.layer in names)
    )
    return m.plan_scene(spec, bindings, motion, purpose=study.timeline.base.purpose), tuple(
        s for s in study.vectors if s.id in assets
    )


def test_full_cadence_world_vectors_fit_the_existing_output_cap(study, tmp_path):
    timeline, sources = vector_scene(study, floor=True)
    output = m.emit_timeline(
        timeline, sources, tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
    )
    assert output.work.engine_invocations == 0
    assert not (tmp_path / 'cache').exists()
    assert len(output.xml) < 8 * 1024**2
    root = ET.fromstring(output.xml)
    figure = ET.fromstring(next(s.xml for s in sources if s.id == 'figure'))
    floor = ET.fromstring(next(s.xml for s in sources if s.id == 'floor'))
    assert len(list(root.iter('shape'))) == 2 * len(list(figure.iter('shape'))) + 14 * len(list(floor.iter('shape')))


@pytest.fixture(scope='module')
def native_render_inputs(study, scene_render, tmp_path_factory):
    root = tmp_path_factory.mktemp('native-figure')
    timeline, sources = vector_scene(study)
    result = m.emit_timeline(timeline, sources, root / 'ink', engine=scene_render, cache=root / 'cache')
    assert result.work.engine_invocations == 0
    original = replace(
        timeline.base.bindings[0], forms=(), candidate=c.CandidateSource('toon', c.vector_source_digest(sources[0]))
    )
    return timeline, sources, original, root / 'ink/scene.xml'


@pytest.mark.parametrize('time', [0.5, 2.1, 3.95, 4, 4.05, 5.5])
def test_real_ink_figure_matches_untouched_flat_drawing_across_camera_cut(
    native_render_inputs, scene_render, tmp_path, time
):
    from srstudio import plates
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    timeline, sources, original, compiled = native_render_inputs
    span = next(span for span in timeline.spans if span.start <= time < span.end)
    sample = timeline.samples[span.scene]
    flat = replace(sample.spec, lights=c.LightRig('flat'))
    oracle = tmp_path / f'original-{time}.xml'
    c.emit_scene(c.preflight(flat, (original,), purpose=sample.purpose), sources, oracle)
    images = []
    for name, path in (('ink', compiled), ('original', oracle)):
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
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        images.append(plates.pixels(output))
    assert np.count_nonzero(images[0][:, :, 3]) > 10000
    assert np.array_equal(*images), time
