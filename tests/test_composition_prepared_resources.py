"""Sequence preparation replies carry each distinct resource once, and the bound counts that reply.

Prepared passes name their mesh resources by content. Held snapshots and the
light/ID passes of one snapshot repeat those resources; the reply carries a
verified content-addressed table and the passes reference it.
"""

import base64
import hashlib

import pytest

from srstudio import composition as c
from support.composition_sequences import held_sequence, sequence

BACKENDS = ['plates', 'proxy']

# Preparation identities recorded before the resource table existed. An identity includes the style's facts, its
# parts list among them (composition preflight), so a part added to the style moves every pin here.
PREPARED = {
    'plates': (
        '736bf9e0e2a45cf8ef754f773346fa3ceee07025f63d6ba5438c7d57832d1cb1',
        '804f6a03a4c18034f0b65928e11a50e4a25f080b65a8810014b9b62a76e8ea7e',
        '6d787e9f757e0713d94c6f3aa1f6aa051f7def59acaa15e07d07e78a8475d6cf',
    ),
    'proxy': (
        '2a9cf8e0e4797710a5f6af9f7c2a28644bfb3420b6df0ffa7f637e79151518fe',
        'c7266ef3ef9fcd6dfe01a9ea3df62f1348557b896dacd8560ce1d3a880281b9a',
        '60342cde4f76096c71929877032282e76bf23daab265cca09efdddbe8aaf0744',
    ),
}


def _plan(item):
    """The fixture plan with a node budget for every held snapshot's prepared passes."""
    from dataclasses import replace

    from support.composition_sequences import plan_for

    plan = plan_for(item)
    return c.preflight(plan.spec, (replace(plan.bindings[0], nodes=64 * len(item.frames)),))


def _prepare_reply(item):
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    plan = _plan(item)
    request = {
        'schema': wire.SCHEMA,
        'operation': 'prepare-sequence',
        'plan': __import__('dataclasses').asdict(plan),
        'layer': 'host',
        'source': __import__('srstudio._composition_sequence_runtime', fromlist=['encode']).encode(item),
    }
    return plan, wire.dumps(dispatch(wire.dumps(request)))


def _resources(prepared):
    found = {}
    for frame in prepared.frames:
        passes = frame.asset.passes if isinstance(frame.asset, c.PreparedProxy) else (frame.asset,)
        for part in passes:
            for resource in part.resources:
                found[hashlib.sha256(resource.data).hexdigest()] = resource.data
    return found


@pytest.fixture
def direct(monkeypatch):
    from srstudio import _composition_proxy_runtime as proxy_runtime
    from srstudio import _composition_sequence_runtime as runtime
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    def call(request, budget):
        return wire.loads(wire.dumps(dispatch(wire.dumps(request))))

    for module in (runtime, proxy_runtime):
        monkeypatch.setattr(module, '_call', call)
    return call


@pytest.mark.parametrize('backend', BACKENDS)
def test_the_preparation_reply_carries_each_resource_once(backend, direct):

    item = held_sequence(backend, count=60)
    _, text = _prepare_reply(item)
    prepared = c.prepare_raster_sequence(_plan(item), 'host', item)
    resources = _resources(prepared)
    assert resources
    for data in resources.values():
        assert text.count(base64.b64encode(data)) == 1


@pytest.mark.parametrize('backend', BACKENDS)
def test_preparation_identities_are_unchanged_and_resources_shared(backend, direct):
    from support.composition_sequences import plan_for

    item = sequence(backend)
    prepared = c.prepare_raster_sequence(plan_for(item), 'host', item)
    digest, first, second = PREPARED[backend]
    assert prepared.digest == digest
    assert [frame.asset.digest for frame in prepared.frames] == [first, second, first]
    one, three = prepared.frames[0].asset, prepared.frames[2].asset
    one = one.passes[0] if isinstance(one, c.PreparedProxy) else one
    three = three.passes[0] if isinstance(three, c.PreparedProxy) else three
    assert one.resources[0].data is three.resources[0].data


@pytest.mark.parametrize(
    'field', ['mismatch', 'unknown-reference', 'unused', 'duplicate', 'inline', 'table-type', 'missing']
)
@pytest.mark.parametrize('backend', BACKENDS)
def test_the_preparation_resource_table_is_verified(backend, field, direct, monkeypatch):
    from srstudio import _composition_sequence_runtime as runtime
    from support.composition_sequences import plan_for

    item = sequence(backend)

    def corrupt(request, budget):
        reply = direct(request, budget)
        first = reply['frames'][0]['prepared']
        part = first['passes'][0] if backend == 'proxy' else first
        if field == 'mismatch':
            reply['resources'][0]['data'] = base64.b64encode(b'not the mesh').decode('ascii')
        elif field == 'unknown-reference':
            part['resources'][0]['data'] = '0' * 64
        elif field == 'unused':
            extra = b'unused resource'
            reply['resources'].append(
                {'digest': hashlib.sha256(extra).hexdigest(), 'data': base64.b64encode(extra).decode('ascii')}
            )
        elif field == 'duplicate':
            reply['resources'].append(dict(reply['resources'][0]))
        elif field == 'inline':
            reference = part['resources'][0]['data']
            part['resources'][0]['data'] = next(e['data'] for e in reply['resources'] if e['digest'] == reference)
        elif field == 'table-type':
            reply['resources'] = {}
        else:
            del reply['resources']
        return reply

    monkeypatch.setattr(runtime, '_call', corrupt)
    with pytest.raises(c.CompositionError):
        c.prepare_raster_sequence(plan_for(item), 'host', item)


@pytest.mark.parametrize('backend', BACKENDS)
def test_the_preparation_bound_counts_distinct_resources(backend, direct, monkeypatch):
    from srstudio import _composition_plate_wire as pw

    item = held_sequence(backend, count=60)
    plan = _plan(item)
    prepared = c.prepare_raster_sequence(plan, 'host', item)
    distinct = sum(map(len, _resources(prepared).values()))
    xml = sum(
        len(part.xml)
        for frame in prepared.frames
        for part in (frame.asset.passes if isinstance(frame.asset, c.PreparedProxy) else (frame.asset,))
    )
    repeated = sum(
        len(resource.data)
        for frame in prepared.frames
        for part in (frame.asset.passes if isinstance(frame.asset, c.PreparedProxy) else (frame.asset,))
        for resource in part.resources
    )
    assert repeated > 20 * distinct
    monkeypatch.setattr(pw, 'MAX_BYTES', max(xml + distinct, _counted_source(item)) + 1024)
    c.prepare_raster_sequence(plan, 'host', item)
    monkeypatch.setattr(pw, 'MAX_BYTES', xml + distinct - 1)
    with pytest.raises(c.CompositionError):
        c.prepare_raster_sequence(plan, 'host', item)


def _counted_source(item):
    from srstudio import _composition_sequence as payload

    return payload.validate_source(item)
