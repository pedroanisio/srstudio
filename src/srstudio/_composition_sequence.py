"""Closed baked raster timelines, conservative work declarations and source-clock windows."""

from __future__ import annotations

from fractions import Fraction

from . import _composition_plate_wire as pw
from . import _composition_proxy as proxy
from . import composition as c
from . import plates
from ._composition_preflight import _digest, _id


def fail(path: str, expected: str) -> c.CompositionError:
    return c._fail('sequence.' + path, None, expected, 'composition.payload')


def times(values: tuple[float, ...], duration: float) -> None:
    if type(duration) not in (int, float) or not 1e-6 <= duration <= 600:
        raise fail('duration', 'a finite source duration in 1e-6..600 seconds')
    if type(values) is not tuple or not 1 <= len(values) <= c.MAX_RECORD_ITEMS:
        raise fail('frames', '1..1024 immutable snapshots')
    previous = -1.0
    for time in values:
        if type(time) not in (int, float) or not previous < time < duration:
            raise fail('time', 'strictly increasing finite snapshot times within the source duration')
        previous = time
    if values[0] != 0:
        raise fail('time', 'a first snapshot at source time zero')


def validate_source(source: c.RasterSequence) -> int:
    if type(source) is not c.RasterSequence or type(source.id) is not str:
        raise fail('source', 'an immutable RasterSequence with an identifier')
    _id(source.id, 'sequence.id')
    if type(source.frames) is not tuple or not 1 <= len(source.frames) <= c.MAX_RECORD_ITEMS:
        raise fail('frames', '1..1024 immutable RasterFrame records')
    if any(type(frame) is not c.RasterFrame for frame in source.frames):
        raise fail('frames', 'RasterFrame records')
    times(tuple(frame.time for frame in source.frames), source.duration)
    kind, units, oversample, total = type(source.frames[0].source), None, None, 0
    seen: set[bytes] = set()
    for index, frame in enumerate(source.frames):
        item = frame.source
        if type(item) not in (c.PlateSource, c.ProxySource) or type(item) is not kind:
            raise fail('backend', 'one supported source backend throughout the timeline')
        total += pw.validate_source(item) if isinstance(item, c.PlateSource) else proxy.validate_source(item)
        # The payload carries each distinct mesh buffer once (a content-addressed
        # table), so a buffer repeated by a held snapshot is counted once too.
        for buffer in _buffers(item):
            if buffer in seen:
                total -= len(buffer)
            seen.add(buffer)
        if index == 0:
            units = item.meters_per_unit
            oversample = item.recipe.oversample if isinstance(item, c.ProxySource) else None
        if item.id != source.id or item.meters_per_unit != units:
            raise fail('frames', 'the same source identifier and physical scale in every snapshot')
        if isinstance(item, c.ProxySource) and item.recipe.oversample != oversample:
            raise fail('oversample', 'the same raw sampling resolution throughout a proxy timeline')
        if total > pw.MAX_BYTES:
            raise fail('buffers', 'at most eight MiB of combined timeline inputs')
    return total


def _buffers(source: c.PlateSource | c.ProxySource) -> tuple[bytes, ...]:
    return tuple(
        buffer
        for mesh in source.meshes
        for buffer in (mesh.vertices, mesh.normals, mesh.triangles, mesh.uvs)
        if buffer is not None
    )


def geometry_bytes(source: c.PlateSource | c.ProxySource) -> int:
    """Mesh buffer bytes of one snapshot, as its own validation counts them."""
    return sum(map(len, _buffers(source)))


def frame_digest(source: c.PlateSource | c.ProxySource) -> str:
    return pw.source_digest(source) if isinstance(source, c.PlateSource) else proxy.source_digest(source)


def source_digest(source: c.RasterSequence) -> str:
    validate_source(source)
    return _digest(
        {
            'schema': 'srstudio.raster-sequence/1.0.0',
            'duration': source.duration,
            'frames': [(frame.time, frame_digest(frame.source)) for frame in source.frames],
        }
    )


def raw_sources(source: c.PlateSource | c.ProxySource) -> tuple[c.PlateSource, ...]:
    return (source,) if isinstance(source, c.PlateSource) else proxy.sources(source)


def jobs(source: c.RasterSequence, *, width: int, height: int, memory_bytes: int) -> tuple[c.PlateWork, ...]:
    validate_source(source)
    if any(type(value) is not int or not 2 <= value <= 8192 for value in (width, height)):
        raise fail('dimensions', 'integer registered view bounds in 2..8192')
    result: dict[str, c.PlateWork] = {}
    for frame in source.frames:
        if isinstance(frame.source, c.ProxySource):
            work = proxy.jobs(frame.source, width=width, height=height, memory_bytes=memory_bytes)
        else:
            item = frame.source
            work = (
                c.PlateWork(
                    pw.source_digest(item),
                    max((width, *(p.recipe.width for p in item.prints))),
                    max((height, *(p.recipe.height for p in item.prints))),
                    plates.SAMPLES * (1 + len(item.prints)),
                    plates.BOUNCES,
                    1 + len(item.prints),
                    memory_bytes,
                ),
            )
        for job in work:
            if job.key in result and result[job.key] != job:
                raise fail('jobs', 'one consistent declaration for each shared raw render')
            result[job.key] = job
    return tuple(result.values())


def context(plan: c.ValidatedScenePlan, layer: str, source: c.RasterSequence) -> c.AssetBinding:
    size = validate_source(source)
    c.plate_view(plan, layer, meters_per_unit=source.frames[0].source.meters_per_unit)
    selected = next(item for item in plan.spec.layers if item.id == layer)
    if selected.asset != source.id:
        raise fail('source.id', 'the source for this layer')
    binding = next(b for b in plan.bindings if b.id == source.id)
    backend = 'plates' if isinstance(source.frames[0].source, c.PlateSource) else 'proxy'
    if binding.backend != backend or binding.duration != source.duration:
        raise fail('binding', 'the exact timeline backend and finite source duration')
    from ._composition_review import check_source

    check_source(binding, source_digest(source))
    keys = {pw.source_digest(raw) for frame in source.frames for raw in raw_sources(frame.source)}
    if keys != {job.key for job in binding.plates}:
        raise fail('jobs', 'exactly the unique raw jobs for every timeline snapshot')
    if size * 8 > binding.memory_bytes:
        raise fail('memory_bytes', 'at least eight times the complete source-buffer size')
    spans(tuple(frame.time for frame in source.frames), source.duration, selected.temporal)
    return binding


def spans(values: tuple[float, ...], duration: float, clock: c.TemporalPolicy) -> tuple[c.RasterSpan, ...]:
    times(values, duration)
    clock.__post_init__()
    start, end, offset, rate = (
        Fraction(str(value)) for value in (clock.start, clock.end, clock.source_start, clock.rate)
    )
    last = offset + (end - start) * rate
    if not start < end or last > Fraction(str(duration)):
        raise fail('clock', 'an ordered clip inside the finite source duration')
    result = []
    for index, (left, right) in enumerate(zip(values, (*values[1:], duration), strict=True)):
        lo, hi = max(offset, Fraction(str(left))), min(last, Fraction(str(right)))
        if lo < hi:
            span = c.RasterSpan(index, float(start + (lo - offset) / rate), float(start + (hi - offset) / rate))
            if span.start >= span.end:
                raise fail('clock', 'snapshot intervals representable as positive scene-time spans')
            result.append(span)
    return tuple(result)


def schedule(plan: c.ValidatedScenePlan, layer: str, source: c.RasterSequence) -> tuple[c.RasterSpan, ...]:
    context(plan, layer, source)
    clock = next(item.temporal for item in plan.spec.layers if item.id == layer)
    return spans(tuple(frame.time for frame in source.frames), source.duration, clock)


def identity(asset: c.PreparedRasterSequence) -> str:
    return _digest(
        {
            'schema': 'srstudio.prepared-raster-sequence/1.0.0',
            'plan': asset.plan_digest,
            'layer': asset.layer,
            'source': source_digest(asset.source),
            'frames': [(frame.time, frame.asset.digest) for frame in asset.frames],
        }
    )
