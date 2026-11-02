"""The combined candidate keeps native information outside picture lighting."""

import importlib
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from srstudio import composition as c


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_information')


def test_information_preserves_the_candidate_layout_and_pinned_font(example):
    binding, source = example.information_source()
    prepared = c.prepare_vector(binding, source.xml, fonts=source.fonts)
    assert prepared.fonts == source.fonts and len(source.fonts) == 1
    root = ET.fromstring(source.xml)
    text = {n.get('text'): n for n in root.findall('assets/text')}
    assert set(text) == {
        'A SHARED VIEW',
        'One car. One hand. One continuing moment.',
        'Keep hold. The camera can move.',
    }
    assert [n.get('size') for n in text.values()] == ['62', '30', '36']
    assert all(n.get('overflow') == 'clip' for n in text.values())
    assert binding.forms == ()
    assert binding.candidate.source_digest == c.vector_source_digest(source)


def test_background_is_native_at_every_camera_pose(example):
    study = example.complete_scene(fps=2)
    assert len({plan.spec.camera for plan in study.timeline.samples}) > 1
    assert all(plan.spec.background == '#efe8df' for plan in study.timeline.samples)
    assert all(source.id != 'background' for source in study.vectors)


def test_complete_candidate_keeps_information_screen_owned_and_within_bounds(example):
    study = example.complete_scene()
    timeline = study.timeline
    assert {binding.id for binding in timeline.base.bindings} >= {'legs', 'feet'}
    assert sum('-foot-' in layer.id for layer in timeline.base.spec.layers) == 4
    assert {0.85, 1.35, 1.95, 2.45, 3.85, 4.35, 4.95, 5.45} <= {span.start for span in timeline.spans}
    assert timeline.base.spec.background == '#efe8df'
    info = timeline.base.spec.layers[-1]
    assert (info.id, info.space, info.role) == ('information', 'screen', 'information')
    assert info.parent is None
    assert timeline.cost.engine_invocations == 196  # Shared foot, root and contact events sample every picture layer.
    assert timeline.cost.nodes <= 500000
    assert timeline.cost.memory_bytes <= 8 * 1024**3
    for plan in timeline.samples:
        assert plan.spec.layers[-1] == info


def test_missing_font_is_refused_before_source_creation(example, monkeypatch):
    monkeypatch.setattr(example.sample, 'SYSTEM_FONTS', ())
    with pytest.raises(FileNotFoundError, match='DejaVu'):
        example.information_source()


def test_full_cadence_vectors_and_font_fit_existing_bundle_limit(example, tmp_path):
    from dataclasses import replace

    from srstudio import scene_motion as m

    study = example.complete_scene()
    full = study.timeline
    layers = tuple(layer for layer in full.base.spec.layers if layer.asset not in ('car', 'hand', 'shadow'))
    names = {layer.id for layer in layers}
    assets = {layer.asset for layer in layers}
    motion = replace(full.motion, transforms=tuple(track for track in full.motion.transforms if track.layer in names))
    timeline = m.plan_scene(
        replace(full.base.spec, layers=layers),
        tuple(binding for binding in full.base.bindings if binding.id in assets),
        motion,
        purpose=full.base.purpose,
    )
    sources = tuple(source for source in study.vectors if source.id in assets)
    result = m.emit_timeline(
        timeline, sources, tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
    )
    assert result.work.engine_invocations == 0
    assert not (tmp_path / 'cache').exists()
    assert len(result.xml) + sum(len(resource.data) for resource in result.resources) < 8 * 1024**2
    assert len(result.resources) == 2  # One pinned font and its license.


def test_real_information_matches_native_pixels_through_camera_cut(example, scene_render, tmp_path):
    from dataclasses import replace

    from examples.drawing_world import world_scene

    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    world = world_scene(fps=2)
    info, info_xml = example.information_source()
    clock = c.TemporalPolicy(0, 6)
    layers = (c.LayerSpec('information', 'information', 1, clock, role='information', space='screen'),)
    spec = replace(world.timeline.base.spec, layers=layers, background='#efe8df')
    motion = replace(world.timeline.motion, transforms=())
    timeline = m.plan_scene(spec, (info,), motion, purpose='candidate-review')
    result = m.emit_timeline(timeline, (info_xml,), tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    assert result.work.engine_invocations == 0 and not (tmp_path / 'cache').exists()
    original = ET.fromstring(info_xml.xml)
    original.find('project').set('background', '#efe8df')
    oracle = tmp_path / 'original.xml'
    oracle.write_bytes(ET.tostring(original))
    (tmp_path / 'font.ttf').write_bytes(info_xml.fonts[0].data)
    (tmp_path / 'LICENSE.txt').write_text(info_xml.fonts[0].license_text)
    images = []
    for index, (path, time) in enumerate(
        ((oracle, 0), (tmp_path / 'bundle/scene.xml', 0), (tmp_path / 'bundle/scene.xml', 4.05))
    ):
        image = tmp_path / f'information-{index}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(path),
                    '--time',
                    str(time),
                    '--output',
                    str(image),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        images.append(plates.pixels(image))
    assert np.all(images[0][..., 3] == 255)
    assert len(np.unique(images[0].reshape(-1, 4), axis=0)) > 100
    assert np.array_equal(images[0], images[1])
    assert np.array_equal(images[0], images[2])
