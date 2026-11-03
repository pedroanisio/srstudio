"""The documented 12-fps complete candidate fits the shared eight-MiB source cap.

The cup rests stand still through each painter window, so 78 of the 80 hand
snapshots repeat rest geometry that is already in the payload. The sequence
payload carries each distinct buffer once, and the cap counts that payload.
"""

import base64
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
DOCUMENTED = {'intervals': 80, 'jobs': 196, 'nodes': 180_355, 'memory': 6_837_269_832}


@pytest.fixture(scope='module')
def complete():
    sys.path.insert(0, str(ROOT))
    try:
        yield importlib.import_module('examples.drawing_information').complete_scene()
    finally:
        sys.path.remove(str(ROOT))


def test_the_documented_twelve_fps_plan_is_the_one_measured(complete):
    timeline = complete.timeline
    cost = timeline.cost
    assert (len(timeline.spans), cost.engine_invocations, cost.nodes, cost.memory_bytes) == tuple(DOCUMENTED.values())
    guide = ' '.join((ROOT / 'docs/drawing-proof.md').read_text().split())
    assert 'complete scene has 80 intervals, 196 raw render jobs, 180,355 planned nodes' in guide


def test_the_twelve_fps_complete_scene_passes_the_compilers_source_cap(complete):
    from srstudio import _composition_bundle as bundle
    from srstudio._scene_motion_bundle import _vectors
    from srstudio._scene_motion_plan import _sources

    timeline = complete.timeline
    rasters = sum(info.size for info in _sources(timeline.base, timeline.rasters).values())
    # The compiler's own first check: CompositionError past eight MiB of combined source buffers.
    prepared = _vectors(timeline, complete.vectors)
    assert prepared.keys() == {source.id for source in complete.vectors}
    assert bundle.MAX_BYTES == 8 * 1024**2
    assert rasters + sum(len(source.xml) for source in complete.vectors) < bundle.MAX_BYTES


def test_the_hand_payload_carries_each_rest_once(complete):
    from srstudio import _composition_sequence as payload
    from srstudio import _composition_sequence_runtime as runtime
    from srstudio import _composition_wire as wire

    hand = next(source for source in complete.timeline.rasters if source.id == 'hand')
    stands = {frame.source.meshes[-1].vertices for frame in hand.frames}
    assert len(hand.frames) == 80 and len(stands) == 2
    assert {frame.source.meshes[-1].material for frame in hand.frames} == {'support'}
    text = wire.dumps({'schema': wire.SCHEMA, 'value': runtime.encode(hand)})
    for stand in stands:
        assert text.count(base64.b64encode(stand)) == 1
    assert len(text) < 4 / 3 * payload.validate_source(hand) + 4096 * len(hand.frames)
