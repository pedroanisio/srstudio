"""Standalone composition worker. The launcher installs resource limits before this file runs."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

SCHEMA = 'srstudio.composition-worker/1.0.0'


def dispatch(raw: bytes) -> dict:
    from srstudio import _composition_wire as wire
    from srstudio import composition as c
    from srstudio._composition_emit import compile_scene
    from srstudio._composition_vector import prepare_vector

    request = wire.loads(raw)
    operation = request.get('operation')
    if operation == 'prepare-sequence':
        from srstudio._composition_sequence_runtime import decode as sequence_decode
        from srstudio._composition_sequence_runtime import frame_encode
        from srstudio._composition_sequence_worker import prepare_sequence

        wire.fields(request, {'schema', 'operation', 'plan', 'layer', 'source'})
        plan = wire.record(c.ValidatedScenePlan, request['plan'])
        sequence = prepare_sequence(plan, request['layer'], sequence_decode(request['source']))
        return {
            'schema': SCHEMA,
            'status': 'ok',
            'frames': [frame_encode(f) for f in sequence.frames],
            'digest': sequence.digest,
        }
    if operation == 'prepare-proxy':
        from srstudio import _composition_plate_wire as pw
        from srstudio._composition_proxy_runtime import decode
        from srstudio._composition_proxy_worker import prepare_proxy

        wire.fields(request, {'schema', 'operation', 'plan', 'layer', 'source'})
        plan = wire.record(c.ValidatedScenePlan, request['plan'])
        proxy_asset = prepare_proxy(plan, request['layer'], decode(request['source']))
        return {
            'schema': SCHEMA,
            'status': 'ok',
            'passes': [pw.prepared_encode(p) for p in proxy_asset.passes],
            'digest': proxy_asset.digest,
        }
    if operation in ('convert-proxy', 'convert-proxy-frame'):
        import hashlib

        from srstudio._composition_proxy_worker import convert

        output = convert(request)
        return {
            'schema': SCHEMA,
            'status': 'ok',
            'png': wire.xml_encode(output),
            'digest': hashlib.sha256(output).hexdigest(),
        }
    if operation == 'validate-png':
        from srstudio._composition_png import verify

        wire.fields(request, {'schema', 'operation', 'png', 'width', 'height'})
        digest = verify(wire.xml_decode(request['png']), request['width'], request['height'])
        return {'schema': SCHEMA, 'status': 'ok', 'digest': digest}
    if operation == 'compile-bundle':
        from srstudio._composition_bundle_worker import compile_bundle

        bundle_scene = compile_bundle(request)
        return {
            'schema': SCHEMA,
            'status': 'ok',
            'xml': wire.xml_encode(bundle_scene.xml),
            'digest': bundle_scene.digest,
            'plan_digest': bundle_scene.plan_digest,
            'nodes': bundle_scene.nodes,
        }
    if operation == 'prepare-plate':
        from srstudio import _composition_plate_wire as plate_wire
        from srstudio._composition_plate import prepare_plate

        wire.fields(request, {'schema', 'operation', 'plan', 'layer', 'source'})
        plan = wire.record(c.ValidatedScenePlan, request['plan'])
        plate_asset = prepare_plate(plan, request['layer'], plate_wire.source_decode(request['source']))
        return {'schema': SCHEMA, 'status': 'ok', 'prepared': plate_wire.prepared_encode(plate_asset)}
    if operation == 'prepare':
        wire.fields(
            request,
            {'schema', 'operation', 'binding', 'xml'}
            | ({'fonts'} if 'fonts' in request else set())
            | ({'shadow_nodes'} if 'shadow_nodes' in request else set()),
        )
        binding = wire.record(c.AssetBinding, request['binding'])
        asset = prepare_vector(
            binding, wire.xml_decode(request['xml']), fonts=wire.fonts_decode(request.get('fonts', []))
        )
        if 'shadow_nodes' in request:
            import xml.etree.ElementTree as ET

            from srstudio._composition_shadows import verify_payload

            roles = request['shadow_nodes']
            if (
                type(roles) is not list
                or len(roles) > 2 * c.MAX_LAYERS
                or any(type(role) is not list for role in roles)
            ):
                raise wire.fail(None, 'bounded shadow node roles')
            verify_payload(ET.fromstring(asset.xml), tuple(tuple(role) for role in roles))
        return {'schema': SCHEMA, 'status': 'ok', 'prepared': wire.prepared_metadata(asset)}
    if operation != 'compile':
        raise wire.fail(operation, 'prepare, prepare-plate, validate-png, compile or compile-bundle')
    wire.fields(request, {'schema', 'operation', 'plan', 'assets'})
    plan = wire.record(c.ValidatedScenePlan, request['plan'])
    if type(request['assets']) is not list or not 1 <= len(request['assets']) <= c.MAX_LAYERS:
        raise wire.fail(None, 'a bounded list of source payloads')
    # Recheck all manifest relationships before parsing any geometry.
    if c.preflight(plan.spec, plan.bindings, purpose=plan.purpose) != plan:
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


def main(handler: Callable[[bytes], dict] | None = None, *, maximum: int = 16 * 1024**2) -> None:
    # Prefer the installed source containing this worker, including alternate
    # worktrees. No caller-supplied module names or executable objects cross IPC.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        from srstudio import _composition_wire as wire
        from srstudio import composition as c

        try:
            result = (dispatch if handler is None else handler)(sys.stdin.buffer.read(maximum + 1))
        except c.CompositionError as error:
            result = {
                'schema': SCHEMA,
                'status': 'error',
                'diagnostic': error.to_dict(),
                'cause': wire.cause_encode(error.__cause__),
            }
        sys.stdout.buffer.write(wire.dumps(result, maximum=maximum))
    except MemoryError:
        # Fixed bytes avoid allocating a diagnostic after an allocation failure.
        os.write(2, b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\n')
        os._exit(86)


if __name__ == '__main__':
    main()
