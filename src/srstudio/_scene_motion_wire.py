"""Closed timeline inputs shared by the bounded emitter and its host."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._scene_motion_compact import Layout

from . import _composition_plate_wire as pw
from . import _composition_proxy_runtime as proxy
from . import _composition_sequence_runtime as sequence
from . import _composition_wire as wire
from . import composition as c
from . import scene_motion as m
from ._composition_preflight import _graph

MAX_WIRE_BYTES = 32 * 1024**2
Reference = tuple[int, str, int | None]


def checked(timeline: m.SceneTimeline) -> m.SceneTimeline:
    if (
        type(timeline) is not m.SceneTimeline
        or type(timeline.base) is not c.ValidatedScenePlan
        or type(timeline.terminal) is not c.ValidatedScenePlan
        or type(timeline.motion) is not m.SceneMotion
        or type(timeline.cost) is not c.CostEstimate
        or type(timeline.digest) is not str
        or len(timeline.digest) != 64
        or type(timeline.samples) is not tuple
        or not 1 <= len(timeline.samples) <= m.MAX_TIMELINE_SAMPLES
        or type(timeline.spans) is not tuple
        or not 1 <= len(timeline.spans) <= m.MAX_TIMELINE_SAMPLES
        or any(type(p) is not c.ValidatedScenePlan for p in timeline.samples)
        or any(type(s) is not m.SceneSpan for s in timeline.spans)
    ):
        raise wire.fail(None, 'a bounded immutable SceneTimeline')
    total = 0
    for record in (
        timeline.base,
        timeline.terminal,
        timeline.motion,
        timeline.cost,
        *timeline.samples,
        *timeline.spans,
    ):
        count = [0]
        _graph(record, count)
        total += count[0]
        if total > m.MAX_TIMELINE_RECORDS:
            raise wire.fail(None, 'bounded timeline record visits')
    expected = m.plan_scene(
        timeline.base.spec,
        timeline.base.bindings,
        timeline.motion,
        rasters=timeline.rasters,
        purpose=timeline.base.purpose,
    )
    if expected != timeline:
        raise wire.fail(None, 'the current reproducible scene timeline')
    return expected


def encode(timeline: m.SceneTimeline) -> dict:
    sources = []
    for source in timeline.rasters:
        if isinstance(source, c.PlateSource):
            kind, data = 'plates', pw.source_encode(source)
        elif isinstance(source, c.ProxySource):
            kind, data = 'proxy', proxy.encode(source)
        else:
            kind, data = 'sequence', sequence.encode(source)
        sources.append({'kind': kind, 'source': data})
    return {
        'spec': asdict(timeline.base.spec),
        'bindings': [asdict(b) for b in timeline.base.bindings],
        'motion': asdict(timeline.motion),
        'rasters': sources,
        'digest': timeline.digest,
        'purpose': timeline.base.purpose,
    }


def decode(value: object) -> m.SceneTimeline:
    data = wire.fields(value, {'spec', 'bindings', 'motion', 'rasters', 'digest', 'purpose'})
    if any(type(data[k]) is not list or len(data[k]) > c.MAX_LAYERS for k in ('bindings', 'rasters')):
        raise wire.fail(None, 'bounded binding/source lists')
    sources = []
    for item in data['rasters']:
        item = wire.fields(item, {'kind', 'source'})
        if item['kind'] == 'plates':
            source: m.RasterSource = pw.source_decode(item['source'])
        elif item['kind'] == 'proxy':
            source = proxy.decode(item['source'])
        elif item['kind'] == 'sequence':
            source = sequence.decode(item['source'])
        else:
            raise wire.fail(None, 'a supported raster source kind')
        sources.append(source)
    result = m.plan_scene(
        wire.record(c.ScenePlan, data['spec']),
        tuple(wire.record(c.AssetBinding, b) for b in data['bindings']),
        wire.record(m.SceneMotion, data['motion']),
        rasters=tuple(sources),
        purpose=data['purpose'],
    )
    if data['digest'] != result.digest:
        raise wire.fail(None, 'the exact recomputed timeline identity')
    return result


def references(timeline: m.SceneTimeline) -> tuple[Reference, ...]:
    return tuple(dict.fromkeys((span.scene, r.layer, r.frame) for span in timeline.spans for r in span.rasters))


def expansion(timeline: m.SceneTimeline, vectors: dict[str, c.PreparedVector]) -> Layout | None:
    from ._scene_motion_compact import select

    return select(timeline, vectors, pw.MAX_BYTES)
