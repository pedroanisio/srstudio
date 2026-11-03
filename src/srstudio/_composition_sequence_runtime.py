"""Closed raster-sequence IPC and bounded public preparation."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, replace

from . import _composition_plate_wire as pw
from . import _composition_proxy as proxy_payload
from . import _composition_proxy_runtime as proxy
from . import _composition_sequence as payload
from . import _composition_wire as wire
from . import composition as c
from ._composition_runtime import _call


def encode(source: c.RasterSequence) -> dict:
    """Snapshots reference a content-addressed table that carries each distinct mesh buffer once."""
    payload.validate_source(source)
    table = pw.BufferTable()
    frames = [
        {
            'time': frame.time,
            'backend': 'plates' if isinstance(frame.source, c.PlateSource) else 'proxy',
            'source': pw.source_encode(frame.source, table)
            if isinstance(frame.source, c.PlateSource)
            else proxy.encode(frame.source, table),
        }
        for frame in source.frames
    ]
    return {
        'id': source.id,
        'duration': source.duration,
        'buffers': [{'digest': digest, 'data': pw._encode(data)} for digest, data in table.buffers.items()],
        'frames': frames,
    }


def _table(value: object) -> tuple[pw.BufferTable, int]:
    if type(value) is not list or not 1 <= len(value) <= c.MAX_RECORD_ITEMS * 4 * pw.MAX_MESHES:
        raise wire.fail(None, 'a nonempty bounded buffer table')
    buffers: dict[str, bytes] = {}
    total = 0
    for entry in value:
        item = wire.fields(entry, {'digest', 'data'})
        data = pw._decode(item['data'])
        if type(item['digest']) is not str or item['digest'] in buffers:
            raise wire.fail(None, 'distinct buffer table digests')
        if hashlib.sha256(data).hexdigest() != item['digest']:
            raise wire.fail(None, 'buffer table entries matching their SHA-256 digests')
        total += len(data)
        if total > pw.MAX_BYTES:
            raise payload.fail('buffers', 'at most eight MiB of combined timeline inputs')
        buffers[item['digest']] = data
    return pw.BufferTable(buffers), total


def decode(value: object) -> c.RasterSequence:
    data = wire.fields(value, {'id', 'duration', 'buffers', 'frames'})
    if type(data['frames']) is not list or not 1 <= len(data['frames']) <= c.MAX_RECORD_ITEMS:
        raise wire.fail(None, '1..1024 raster snapshots')
    table, total = _table(data['buffers'])
    frames = []
    for entry in data['frames']:
        frame = wire.fields(entry, {'time', 'backend', 'source'})
        source: c.PlateSource | c.ProxySource
        if frame['backend'] == 'plates':
            source = pw.source_decode(frame['source'], table)
            size = pw.validate_source(source)
        elif frame['backend'] == 'proxy':
            source = proxy.decode(frame['source'], table)
            size = proxy_payload.validate_source(source)
        else:
            raise wire.fail(None, 'a plates or proxy snapshot')
        # The table already counted the geometry; add only this snapshot's own records.
        total += size - payload.geometry_bytes(source)
        if total > pw.MAX_BYTES:
            raise payload.fail('buffers', 'at most eight MiB of combined timeline inputs')
        frames.append(c.RasterFrame(frame['time'], source))
    if table.used != table.buffers.keys():
        raise wire.fail(None, 'a buffer table without unreferenced entries')
    result = c.RasterSequence(data['id'], data['duration'], tuple(frames))
    if payload.validate_source(result) != total:
        raise wire.fail(None, 'a decoded sequence whose counted bytes match its payload')
    return result


def frame_encode(frame: c.PreparedRasterFrame, table: pw.BufferTable | None = None) -> dict:
    """Encode one prepared snapshot; with a table, its resources reference the reply's table."""
    if isinstance(frame.asset, c.PreparedPlate):
        data = pw.prepared_encode(frame.asset, table)
    else:
        data = {
            'schema': wire.SCHEMA,
            'status': 'ok',
            'passes': [pw.prepared_encode(p, table) for p in frame.asset.passes],
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
    wire.fields(response, {'schema', 'status', 'frames', 'resources', 'digest'})
    if type(response['frames']) is not list or len(response['frames']) != len(source.frames):
        raise wire.fail(None, 'complete preparation evidence for every source snapshot')
    table, _ = _table(response['resources'])
    frames = []
    for raw, snapshot in zip(response['frames'], source.frames, strict=True):
        entry = wire.fields(raw, {'time', 'prepared'})
        if type(entry['time']) not in (int, float) or entry['time'] != snapshot.time:
            raise wire.fail(None, 'unchanged typed snapshot times')
        asset = (
            pw.prepared_decode(entry['prepared'], plan, layer, snapshot.source, table=table)
            if isinstance(snapshot.source, c.PlateSource)
            else proxy.prepared_decode(entry['prepared'], plan, layer, snapshot.source, sequence=True, table=table)
        )
        frames.append(c.PreparedRasterFrame(snapshot.time, asset))
    if table.used != table.buffers.keys():
        raise wire.fail(None, 'a resource table without unreferenced entries')
    result = c.PreparedRasterSequence(binding, source, layer, plan.digest, tuple(frames), '')
    if response['digest'] != payload.identity(result):
        raise wire.fail(None, 'the complete prepared sequence identity')
    return replace(result, digest=response['digest'])
