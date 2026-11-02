"""Closed raster-sequence IPC and bounded public preparation."""

from __future__ import annotations

from dataclasses import asdict, replace

from . import _composition_plate_wire as pw
from . import _composition_proxy as proxy_payload
from . import _composition_proxy_runtime as proxy
from . import _composition_sequence as payload
from . import _composition_wire as wire
from . import composition as c
from ._composition_runtime import _call


def encode(source: c.RasterSequence) -> dict:
    payload.validate_source(source)
    return {
        'id': source.id,
        'duration': source.duration,
        'frames': [
            {
                'time': frame.time,
                'backend': 'plates' if isinstance(frame.source, c.PlateSource) else 'proxy',
                'source': pw.source_encode(frame.source)
                if isinstance(frame.source, c.PlateSource)
                else proxy.encode(frame.source),
            }
            for frame in source.frames
        ],
    }


def decode(value: object) -> c.RasterSequence:
    data = wire.fields(value, {'id', 'duration', 'frames'})
    if type(data['frames']) is not list or not 1 <= len(data['frames']) <= c.MAX_RECORD_ITEMS:
        raise wire.fail(None, '1..1024 raster snapshots')
    frames = []
    total = 0
    for entry in data['frames']:
        frame = wire.fields(entry, {'time', 'backend', 'source'})
        source: c.PlateSource | c.ProxySource
        if frame['backend'] == 'plates':
            source = pw.source_decode(frame['source'])
            total += pw.validate_source(source)
        elif frame['backend'] == 'proxy':
            source = proxy.decode(frame['source'])
            total += proxy_payload.validate_source(source)
        else:
            raise wire.fail(None, 'a plates or proxy snapshot')
        if total > pw.MAX_BYTES:
            raise payload.fail('buffers', 'at most eight MiB of combined timeline inputs')
        frames.append(c.RasterFrame(frame['time'], source))
    result = c.RasterSequence(data['id'], data['duration'], tuple(frames))
    payload.validate_source(result)
    return result


def frame_encode(frame: c.PreparedRasterFrame) -> dict:
    if isinstance(frame.asset, c.PreparedPlate):
        data = pw.prepared_encode(frame.asset)
    else:
        data = {
            'schema': wire.SCHEMA,
            'status': 'ok',
            'passes': [pw.prepared_encode(p) for p in frame.asset.passes],
            'digest': frame.asset.digest,
        }
    return {'time': frame.time, 'prepared': data}


def prepare_sequence(plan: c.ValidatedScenePlan, layer: str, source: c.RasterSequence) -> c.PreparedRasterSequence:
    binding = payload.context(plan, layer, source)
    response = _call(
        {
            'schema': wire.SCHEMA,
            'operation': 'prepare-sequence',
            'plan': asdict(plan),
            'layer': layer,
            'source': encode(source),
        },
        plan.spec.budget,
    )
    wire.fields(response, {'schema', 'status', 'frames', 'digest'})
    if type(response['frames']) is not list or len(response['frames']) != len(source.frames):
        raise wire.fail(None, 'complete preparation evidence for every source snapshot')
    frames = []
    for raw, snapshot in zip(response['frames'], source.frames, strict=True):
        entry = wire.fields(raw, {'time', 'prepared'})
        if type(entry['time']) not in (int, float) or entry['time'] != snapshot.time:
            raise wire.fail(None, 'unchanged typed snapshot times')
        asset = (
            pw.prepared_decode(entry['prepared'], plan, layer, snapshot.source)
            if isinstance(snapshot.source, c.PlateSource)
            else proxy.prepared_decode(entry['prepared'], plan, layer, snapshot.source, sequence=True)
        )
        frames.append(c.PreparedRasterFrame(snapshot.time, asset))
    result = c.PreparedRasterSequence(binding, source, layer, plan.digest, tuple(frames), '')
    if response['digest'] != payload.identity(result):
        raise wire.fail(None, 'the complete prepared sequence identity')
    return replace(result, digest=response['digest'])
