"""Standalone composition worker. The launcher installs resource limits before this file runs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCHEMA = 'srstudio.composition-worker/1.0.0'


def dispatch(raw: bytes) -> dict:
    from srstudio import _composition_wire as wire
    from srstudio import composition as c
    from srstudio._composition_emit import compile_scene
    from srstudio._composition_vector import prepare_vector

    request = wire.loads(raw)
    operation = request.get('operation')
    if operation == 'prepare':
        wire.fields(request, {'schema', 'operation', 'binding', 'xml'})
        binding = wire.record(c.AssetBinding, request['binding'])
        asset = prepare_vector(binding, wire.xml_decode(request['xml']))
        return {'schema': SCHEMA, 'status': 'ok', 'prepared': wire.prepared_metadata(asset)}
    if operation != 'compile':
        raise wire.fail(operation, 'prepare or compile')
    wire.fields(request, {'schema', 'operation', 'plan', 'assets'})
    plan = wire.record(c.ValidatedScenePlan, request['plan'])
    if type(request['assets']) is not list or not 1 <= len(request['assets']) <= c.MAX_LAYERS:
        raise wire.fail(None, 'a bounded list of source payloads')
    # Recheck all manifest relationships before parsing any geometry.
    if c.preflight(plan.spec, plan.bindings) != plan:
        raise c._fail('plan', plan.digest, 'the current preflight result', 'composition.version')
    bindings = {b.id: b for b in plan.bindings}
    assets = []
    seen = set()
    for source in request['assets']:
        source = wire.fields(source, {'id', 'xml', 'prepared'})
        name = source['id']
        if type(name) is not str or name not in bindings or name in seen:
            raise wire.fail(name, 'one source for each used binding')
        seen.add(name)
        xml = wire.xml_decode(source['xml'])
        asset = prepare_vector(bindings[name], xml)
        if source['prepared'] is not None and asset != wire.prepared(bindings[name], xml, source['prepared']):
            raise c._fail('assets.' + name, None, 'unchanged prepared payload evidence', 'composition.payload')
        assets.append(asset)
    result = compile_scene(plan, tuple(assets))
    return {
        'schema': SCHEMA,
        'status': 'ok',
        'xml': wire.xml_encode(result.xml),
        'digest': result.digest,
        'plan_digest': result.plan_digest,
        'nodes': result.nodes,
    }


def main() -> None:
    # Prefer the installed source containing this worker, including alternate
    # worktrees. No caller-supplied module names or executable objects cross IPC.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        from srstudio import _composition_wire as wire
        from srstudio import composition as c

        try:
            result = dispatch(sys.stdin.buffer.read(wire.MAX_WIRE_BYTES + 1))
        except c.CompositionError as error:
            result = {
                'schema': SCHEMA,
                'status': 'error',
                'diagnostic': error.to_dict(),
                'cause': wire.cause_encode(error.__cause__),
            }
        sys.stdout.buffer.write(wire.dumps(result))
    except MemoryError:
        # Fixed bytes avoid allocating a diagnostic after an allocation failure.
        os.write(2, b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\n')
        os._exit(86)


if __name__ == '__main__':
    main()
