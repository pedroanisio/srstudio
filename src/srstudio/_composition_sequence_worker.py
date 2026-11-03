"""Verify every raster snapshot before any cache access or renderer launch."""

from __future__ import annotations

from dataclasses import replace

from . import _composition_plate_wire as pw
from . import _composition_sequence as payload
from . import composition as c
from ._composition_plate import prepare_source
from ._composition_proxy_worker import prepare_proxy


def prepare_sequence(plan: c.ValidatedScenePlan, layer: str, source: c.RasterSequence) -> c.PreparedRasterSequence:
    binding = payload.context(plan, layer, source)
    known: dict[str, c.PreparedPlate | c.PreparedProxy] = {}
    frames = []
    total, nodes = 0, 0
    # The reply carries each distinct resource once; prepared XML crosses per snapshot.
    seen: set[bytes] = set()
    for snapshot in source.frames:
        key = payload.frame_digest(snapshot.source)
        if key not in known:
            if isinstance(snapshot.source, c.PlateSource):
                job = next(job for job in binding.plates if job.key == pw.source_digest(snapshot.source))
                view = c.plate_view(plan, layer, meters_per_unit=snapshot.source.meters_per_unit)
                known[key] = prepare_source(plan, layer, snapshot.source, binding, job, view)
            else:
                known[key] = prepare_proxy(plan, layer, snapshot.source, sequence=True)
        asset = known[key]
        passes = asset.passes if isinstance(asset, c.PreparedProxy) else (asset,)
        for part in passes:
            total += len(part.xml)
            for resource in part.resources:
                if resource.data not in seen:
                    seen.add(resource.data)
                    total += len(resource.data)
        nodes += sum(p.nodes for p in passes)
        if total > pw.MAX_BYTES or nodes > binding.nodes or total * 8 > binding.memory_bytes:
            raise payload.fail('resources', 'combined timeline preparation within byte, node and memory bounds')
        frames.append(c.PreparedRasterFrame(snapshot.time, asset))
    result = c.PreparedRasterSequence(binding, source, layer, plan.digest, tuple(frames), '')
    return replace(result, digest=payload.identity(result))
