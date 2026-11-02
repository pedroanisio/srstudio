"""Bound scene sampling, visible raw render work and retained timeline storage."""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from typing import Literal

from . import _composition_plate_wire as pw
from . import _composition_proxy as proxy
from . import _composition_sequence as sequence
from . import composition as c
from . import plates
from . import scene_motion as m
from ._composition_forms import resolved as form_lighting
from ._composition_paths import expansion_bytes as path_expansion
from ._composition_preflight import _digest, _graph, _pose_key
from ._composition_review import check_source


@dataclass(frozen=True)
class _Source:
    source: m.RasterSource
    frames: tuple[c.PlateSource | c.ProxySource, ...]
    raw: tuple[tuple[c.PlateSource, ...], ...]
    keys: tuple[tuple[str, ...], ...]
    digest: str
    size: int


def _limit(spec: c.ScenePlan, name: str, value: int) -> None:
    maximum = getattr(spec.budget, name)
    if value > maximum:
        raise c._fail('budget.' + name, value, f'<= {maximum}', 'composition.budget')


def _metadata_size(record: c._Record) -> int:
    from ._composition_shadows import definition

    return len(json.dumps(definition(record), separators=(',', ':'), allow_nan=False).encode('utf-8'))


def _sources(base: c.ValidatedScenePlan, sources: tuple[m.RasterSource, ...]) -> dict[str, _Source]:
    if type(sources) is not tuple or len(sources) > c.MAX_LAYERS:
        raise m._fail('rasters', 'at most 256 immutable raster sources')
    bindings = {b.id: b for b in base.bindings if b.backend != 'vector'}
    result: dict[str, _Source] = {}
    total = 0
    for source in sources:
        if type(source) is c.RasterSequence:
            size = sequence.validate_source(source)
            frames = tuple(frame.source for frame in source.frames)
            digest = sequence.source_digest(source)
            duration: float | None = source.duration
        elif type(source) is c.PlateSource or type(source) is c.ProxySource:
            size = pw.validate_source(source) if isinstance(source, c.PlateSource) else proxy.validate_source(source)
            frames = (source,)
            digest = sequence.frame_digest(source)
            duration = None
        else:
            raise m._fail('rasters', 'PlateSource, ProxySource or RasterSequence records')
        total += size
        if total > pw.MAX_BYTES:
            raise m._fail('rasters', 'at most eight MiB of combined immutable source buffers')
        if source.id not in bindings or source.id in result:
            raise m._fail('rasters', 'exactly one source per raster binding')
        binding = bindings[source.id]
        check_source(binding, digest)
        backend = 'plates' if isinstance(frames[0], c.PlateSource) else 'proxy'
        if binding.backend != backend or binding.duration != duration:
            raise m._fail('rasters.' + source.id, 'matching binding backend and source duration')
        raw = tuple(sequence.raw_sources(frame) for frame in frames)
        keys = tuple(tuple(pw.source_digest(item) for item in group) for group in raw)
        if {key for group in keys for key in group} != {job.key for job in binding.plates}:
            raise m._fail('rasters.' + source.id, 'exactly the declared raw source job identities')
        if size * 8 > binding.memory_bytes:
            raise m._fail('rasters.' + source.id, 'binding storage covering eight times the source buffers')
        result[source.id] = _Source(source, frames, raw, keys, digest, size)
    if result.keys() != bindings.keys():
        raise m._fail('rasters', 'one immutable source for every raster binding')
    return result


def _events(
    base: c.ValidatedScenePlan, motion: m.SceneMotion, sources: dict[str, _Source]
) -> tuple[tuple[float, ...], dict]:
    spec = base.spec
    events = {0.0, float(spec.duration)}

    def add(time: float) -> None:
        events.add(float(time))
        if len(events) - 1 > m.MAX_TIMELINE_SAMPLES:
            raise m._fail('samples', f'at most {m.MAX_TIMELINE_SAMPLES} combined frame/key/source intervals')

    fps = Fraction(spec.fps.numerator, spec.fps.denominator)
    groups: tuple[tuple[m.Key, ...], ...] = (
        motion.camera,
        *(track.keys for track in motion.lights),
        *(track.keys for track in motion.transforms),
    )
    for keys in groups:
        for key in keys:
            add(key.time)
        for left, right in zip(keys, keys[1:], strict=False):
            if left.easing == 'hold' or left.value == right.value:
                continue
            first = math.ceil(Fraction(str(left.time)) * fps)
            stop = math.ceil(Fraction(str(right.time)) * fps)
            if stop - first > m.MAX_TIMELINE_SAMPLES:
                raise m._fail('samples', f'at most {m.MAX_TIMELINE_SAMPLES} changing frame intervals')
            for frame in range(first, stop):
                add(float(Fraction(frame, 1) / fps))
    from ._composition_forms import events as form_events

    bindings = {binding.id: binding for binding in base.bindings}
    schedules = {}
    for layer in spec.layers:
        add(layer.temporal.start)
        add(layer.temporal.end)
        for time in form_events(bindings[layer.asset], layer, spec.fps):
            add(time)
        info = sources.get(layer.asset)
        if info is not None and isinstance(info.source, c.RasterSequence):
            clock = sequence.spans(
                tuple(frame.time for frame in info.source.frames), info.source.duration, layer.temporal
            )
            schedules[layer.id] = clock
            for span in clock:
                add(span.start)
                add(span.end)
    count = [0]
    _graph((base.spec, base.bindings, motion), count)
    raster_layers = [layer for layer in spec.layers if layer.asset in sources]
    source_records = sum(
        len(sources[layer.asset].frames) + sum(len(group) for group in sources[layer.asset].raw)
        for layer in raster_layers
    )
    # Each view bridge revalidates the complete manifest. Include those visits
    # and every source snapshot in the expansion bound before evaluating views.
    visits = len(events) * (count[0] * (1 + len(raster_layers)) + source_records)
    if visits > m.MAX_TIMELINE_RECORDS:
        raise m._fail('records', f'at most {m.MAX_TIMELINE_RECORDS} planned record visits')
    return tuple(sorted(events)), schedules


def _views(plan: c.ValidatedScenePlan, sources: dict[str, _Source]) -> dict[str, c.PlateView]:
    bindings = {binding.id: binding for binding in plan.bindings}
    views = {}
    for layer in plan.spec.layers:
        if layer.asset not in sources:
            continue
        info = sources[layer.asset]
        binding = bindings[layer.asset]
        view = c.plate_view(plan, layer.id, meters_per_unit=info.frames[0].meters_per_unit)
        oversample = info.frames[0].recipe.oversample if isinstance(info.frames[0], c.ProxySource) else 1
        view = replace(view, width=view.width * oversample, height=view.height * oversample)
        if max(view.width, view.height) > 8192:
            raise m._fail('view', 'oversampled raster dimensions at most 8192')
        _limit(plan.spec, 'max_frame_pixels', view.width * view.height)
        if len(layer.passes) != 1:
            raise m._fail('passes', 'one selected raster pass per placement')
        jobs = {job.key: job for job in binding.plates}
        for frame, raw, keys in zip(info.frames, info.raw, info.keys, strict=True):
            if isinstance(frame, c.ProxySource):
                if layer.passes == ('under',) and not frame.recipe.under:
                    raise m._fail('passes', 'authored under geometry in every proxy snapshot')
                required = info.size * 8 + view.width * view.height * (64 * len(frame.recipe.parts) + 512)
                if binding.memory_bytes < required:
                    raise m._fail('memory', 'binding memory covering proxy conversion and complete source buffers')
            for item, key in zip(raw, keys, strict=True):
                job = jobs[key]
                if (
                    job.width < max((view.width, *(p.recipe.width for p in item.prints)))
                    or job.height < max((view.height, *(p.recipe.height for p in item.prints)))
                    or job.samples < plates.SAMPLES * (1 + len(item.prints))
                    or job.bounces < plates.BOUNCES
                    or job.engine_invocations < 1 + len(item.prints)
                ):
                    raise m._fail('jobs', 'declared work covering every sampled view and print dependency')
        views[layer.id] = view
    return views


def _render_key(view: c.PlateView, raw: str, seed: int) -> str:
    return _digest(
        {
            'raw': raw,
            'seed': seed,
            'camera': asdict(view.camera),
            'lights': [asdict(light) for light in view.lights],
            # Geometry preparation consumes floating point coordinates. Parent
            # composition may change 0 to 0.0 without changing those buffers.
            'pose': _pose_key(view._frame, view._source_scale),
            'world_scale': float(view._world_scale),
            'width': view.width,
            'height': view.height,
        }
    )


def plan_scene(
    spec: c.ScenePlan,
    bindings: tuple[c.AssetBinding, ...],
    motion: m.SceneMotion,
    *,
    rasters: tuple[m.RasterSource, ...],
    purpose: Literal['production', 'candidate-review'] = 'production',
) -> m.SceneTimeline:
    base = m.sample_scene(spec, bindings, motion, 0, purpose=purpose)
    sources = _sources(base, rasters)
    times, schedules = _events(base, motion, sources)
    # Cache complete semantic checks, not only drawings. Identical resolved
    # scenes have the same proof and retain their original source windows.
    known = {_digest(asdict(spec)): base}
    samples: list[c.ValidatedScenePlan] = []
    indices: dict[str, int] = {}
    spans: list[m.SceneSpan] = []
    view_cache: dict[str, dict[str, c.PlateView]] = {}
    render_jobs: dict[str, c.PlateWork] = {}
    assets = {binding.id: binding for binding in base.bindings}
    contact_samples = base.cost.contact_samples
    metadata_bytes = _metadata_size(base) + _metadata_size(motion)
    _limit(spec, 'max_memory_bytes', base.cost.memory_bytes + 8 * metadata_bytes)
    invocations = sample_work = 0
    previous_forms: tuple = ()
    pixels = base.cost.frame_pixels
    for index, time in enumerate(times):
        resolved = m._sample_spec(spec, motion, time)
        if resolved == spec:
            resolved = spec
        fingerprint = _digest(asdict(resolved))
        if fingerprint not in known:
            known[fingerprint] = c.preflight(resolved, bindings, purpose=purpose)
            contact_samples += known[fingerprint].cost.contact_samples
            _limit(spec, 'max_contact_samples', contact_samples)
            metadata_bytes += _metadata_size(known[fingerprint])
            _limit(spec, 'max_memory_bytes', base.cost.memory_bytes + 8 * metadata_bytes)
        sample = known[fingerprint]
        if fingerprint not in view_cache:
            view_cache[fingerprint] = _views(sample, sources)
        views = view_cache[fingerprint]
        pixels = max((pixels, *(view.width * view.height for view in views.values())))
        if index == len(times) - 1:
            terminal = sample
            break
        if fingerprint not in indices:
            indices[fingerprint] = len(samples)
            samples.append(sample)
        active = tuple(layer for layer in sample.spec.layers if layer.temporal.start <= time < layer.temporal.end)
        selected = []
        for layer in active:
            if layer.asset not in sources:
                continue
            info = sources[layer.asset]
            clock = schedules.get(layer.id)
            frame = clock[bisect_right(tuple(span.start for span in clock), time) - 1].sample if clock else None
            selected.append(m.RasterSample(layer.id, frame))
            frame_index = frame if frame is not None else 0
            raw = info.raw[frame_index]
            keys = info.keys[frame_index]
            raw_views = (
                proxy.views(views[layer.id], len(raw))
                if isinstance(info.frames[frame_index], c.ProxySource)
                else (views[layer.id],)
            )
            declared = {job.key: job for job in assets[layer.asset].plates}
            for key, view in zip(keys, raw_views, strict=True):
                render_key = _render_key(view, key, spec.seed)
                if render_key not in render_jobs:
                    job = declared[key]
                    render_jobs[render_key] = job
                    invocations += job.engine_invocations
                    sample_work += job.width * job.height * job.samples
                    _limit(spec, 'max_new_plates', len(render_jobs))
                    _limit(spec, 'max_engine_invocations', invocations)
                    _limit(spec, 'max_samples', sample_work)
        span = m.SceneSpan(
            time, times[index + 1], indices[fingerprint], tuple(layer.id for layer in active), tuple(selected)
        )
        form_state = tuple(
            (
                layer.id,
                tuple((field.color, field.vertices) for field in form_lighting(sample, layer, time, scene_clock=True)),
            )
            for layer in active
            if assets[layer.asset].forms
        )
        if (
            spans
            and previous_forms == form_state
            and (spans[-1].scene, spans[-1].layers, spans[-1].rasters) == (span.scene, span.layers, span.rasters)
        ):
            spans[-1] = replace(spans[-1], end=span.end)
        else:
            spans.append(span)
        previous_forms = form_state
    layer_assets = {layer.id: assets[layer.asset] for layer in spec.layers}
    nodes = 16 + sum(layer_assets[name].nodes + 8 for span in spans for name in span.layers)
    retained_pixels = sum(
        8 * max(job.width * job.height for job in layer_assets[item.layer].plates) + 4096
        for span in spans
        for item in span.rasters
    )
    cost = c.CostEstimate(
        base.cost.frames,
        pixels,
        base.cost.output_pixels,
        nodes,
        len(render_jobs),
        invocations,
        sample_work,
        max((job.bounces for job in render_jobs.values()), default=0),
        base.cost.memory_bytes
        + 256 * max(0, nodes - base.cost.nodes)
        + retained_pixels
        + 8 * metadata_bytes
        + 8 * sum(path_expansion(layer_assets[name]) for span in spans for name in span.layers),
        contact_samples,
    )
    _limit(spec, 'max_nodes', cost.nodes)
    _limit(spec, 'max_memory_bytes', cost.memory_bytes)
    ordered = tuple(sources[name].source for name in sorted(sources))
    digest = _digest(
        {
            'schema': 'srstudio.scene-timeline/1.0.0',
            'base': base.digest,
            'motion': asdict(motion),
            'sources': [(name, sources[name].digest) for name in sorted(sources)],
            'samples': [sample.digest for sample in samples],
            'terminal': terminal.digest,
            'spans': [asdict(span) for span in spans],
            'cost': asdict(cost),
        }
    )
    return m.SceneTimeline(base, motion, ordered, tuple(samples), terminal, tuple(spans), cost, digest)
