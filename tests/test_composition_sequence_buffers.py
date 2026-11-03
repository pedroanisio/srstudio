"""A raster sequence carries each distinct mesh buffer once: on the wire and in the source cap.

Held snapshots repeat static geometry (a rest, a table) beside moving geometry.
The sequence payload is a content-addressed buffer table plus per-snapshot
references, and the eight-MiB cap counts exactly the table that crosses to the
worker. Snapshot identities and render-job keys do not change.
"""

import base64
import hashlib

import pytest

from srstudio import composition as c
from support.composition_sequences import held_sequence, sequence

BACKENDS = ['plates', 'proxy']
# Identities recorded before the buffer table existed; cached renders must stay valid.
DIGESTS = {
    'plates': (
        '06321afb2b3fd88e5e4d6ec5d9b33456ac273f312ba15afb564403f2b27ca167',
        (
            '4dee431a376945ccabe1f9b071909b8e5980ad62c86d0e8e6f0a9b9ba8ebdd7c',
            '3e311be34cf26900354e5424eb23d2ed1146652200351aec041e82ab8677d9a4',
        ),
    ),
    'proxy': (
        '6939f5d9cd9d559eb950bda26e05b1f9347083d67f9073c2f824637619ca3e78',
        (
            '340cd8c98e3c47aa33cded016fe7080c9094ff399c18c3aef76e3914d595fcf3',
            '3b3a1e3a1c2f34441e668f26d114102bf80ba5682b628b6f8d2a493e83d9ea21',
        ),
    ),
}


def _distinct(item):
    found = {}
    for frame in item.frames:
        for mesh in frame.source.meshes:
            for buffer in (mesh.vertices, mesh.normals, mesh.triangles, mesh.uvs):
                if buffer is not None:
                    found[hashlib.sha256(buffer).hexdigest()] = buffer
    return found


def _wire(item):
    from srstudio import _composition_sequence_runtime as runtime
    from srstudio import _composition_wire as wire

    return wire.dumps({'schema': wire.SCHEMA, 'value': runtime.encode(item)})


def _roundtrip(data):
    from srstudio import _composition_wire as wire

    return wire.loads(wire.dumps({'schema': wire.SCHEMA, 'value': data}))['value']


@pytest.mark.parametrize('backend', BACKENDS)
def test_each_distinct_buffer_crosses_the_wire_exactly_once(backend):
    item = held_sequence(backend)
    text = _wire(item)
    for buffer in _distinct(item).values():
        assert text.count(base64.b64encode(buffer)) == 1


@pytest.mark.parametrize('backend', BACKENDS)
def test_the_source_cap_counts_the_bytes_the_payload_carries(backend):
    from srstudio import _composition_sequence as payload

    short, long = sequence(backend), held_sequence(backend)
    assert _distinct(short).keys() == _distinct(long).keys()
    counted = payload.validate_source(long)
    unique = sum(map(len, _distinct(long).values()))
    repeated = sum(
        len(buffer)
        for frame in long.frames
        for mesh in frame.source.meshes
        for buffer in (mesh.vertices, mesh.normals, mesh.triangles, mesh.uvs)
        if buffer is not None
    )
    assert repeated > 50 * unique
    # Snapshots differ only by small material or recipe records; geometry is counted once.
    assert unique <= counted < unique + 1024 * len(long.frames)
    # Serialized geometry is the base64 of the counted table, not a copy per snapshot.
    assert len(_wire(long)) < 4 / 3 * counted + 1024 * len(long.frames)


@pytest.mark.parametrize('backend', BACKENDS)
def test_decoding_restores_the_sequence_and_shares_identical_buffers(backend):
    from srstudio import _composition_sequence_runtime as runtime

    item = held_sequence(backend)
    decoded = runtime.decode(_roundtrip(runtime.encode(item)))
    assert decoded == item
    first, other = decoded.frames[0].source.meshes[0], decoded.frames[2].source.meshes[0]
    for field in ('vertices', 'normals', 'triangles'):
        assert getattr(first, field) is getattr(other, field)


@pytest.mark.parametrize('backend', BACKENDS)
def test_snapshot_identities_and_render_job_keys_are_unchanged(backend):
    item = sequence(backend)
    digest, keys = DIGESTS[backend]
    assert c.raster_sequence_digest(item) == digest
    assert tuple(job.key for job in c.raster_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2)) == keys


@pytest.mark.parametrize(
    'field', ['mismatch', 'unknown-reference', 'unused', 'duplicate', 'inline', 'table-type', 'entry-field', 'empty']
)
@pytest.mark.parametrize('backend', BACKENDS)
def test_the_buffer_table_is_verified(backend, field):
    from srstudio import _composition_sequence_runtime as runtime

    data = _roundtrip(runtime.encode(sequence(backend)))
    meshes = data['frames'][0]['source']
    meshes = (meshes['geometry'] if backend == 'proxy' else meshes)['meshes']
    if field == 'mismatch':
        data['buffers'][0]['data'] = base64.b64encode(b'\0' * 24).decode('ascii')
    elif field == 'unknown-reference':
        meshes[0]['vertices'] = '0' * 64
    elif field == 'unused':
        extra = b'\1' * 24
        data['buffers'].append(
            {'digest': hashlib.sha256(extra).hexdigest(), 'data': base64.b64encode(extra).decode('ascii')}
        )
    elif field == 'duplicate':
        data['buffers'].append(dict(data['buffers'][0]))
    elif field == 'inline':
        reference = meshes[0]['vertices']
        meshes[0]['vertices'] = next(entry['data'] for entry in data['buffers'] if entry['digest'] == reference)
    elif field == 'table-type':
        data['buffers'] = {}
    elif field == 'entry-field':
        data['buffers'][0]['callback'] = 'anything'
    else:
        data['buffers'] = []
    with pytest.raises(c.CompositionError):
        runtime.decode(data)


@pytest.mark.parametrize('backend', BACKENDS)
def test_distinct_geometry_past_the_cap_is_refused_on_both_sides(backend, monkeypatch):
    from srstudio import _composition_plate_wire as pw
    from srstudio import _composition_sequence_runtime as runtime

    item = held_sequence(backend)
    data = _roundtrip(runtime.encode(item))
    unique = sum(map(len, _distinct(item).values()))
    # The whole table fits even though the snapshots repeat it 240 times over.
    monkeypatch.setattr(pw, 'MAX_BYTES', unique + 1024 * len(item.frames))
    assert runtime.decode(data) == item
    c.raster_sequence_digest(item)
    monkeypatch.setattr(pw, 'MAX_BYTES', unique - 1)
    with pytest.raises(c.CompositionError):
        c.raster_sequence_digest(item)
    with pytest.raises(c.CompositionError):
        runtime.decode(data)
