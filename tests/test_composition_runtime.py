"""Public composition work runs under kernel limits and validates worker replies before publication."""

import importlib
import json
import sys
from dataclasses import replace

import pytest

from srstudio import composition as c
from support.composition import paper


def runtime():
    return importlib.import_module('srstudio._composition_runtime')


def test_raw_sources_are_prepared_and_compiled_in_one_limited_worker():
    spec, binding, xml = paper(animated=True)
    plan = c.preflight(spec, (binding,))
    raw = c.VectorSource(binding.id, xml)
    compiled = c.compile_scene(plan, (raw,))
    prepared = c.prepare_vector(binding, xml, budget=spec.budget)
    assert c.compile_scene(plan, (prepared,)) == compiled


def test_public_compile_never_calls_the_in_process_compiler(monkeypatch):
    from srstudio import _composition_emit

    spec, binding, xml = paper()
    assets = (c.prepare_vector(binding, xml),)

    def forbidden(*args, **kwargs):
        pytest.fail('public compilation escaped the bounded worker')

    monkeypatch.setattr(_composition_emit, 'compile_scene', forbidden)
    assert c.compile_scene(c.preflight(spec, (binding,)), assets).xml


def test_prepare_deadline_is_enforced_before_the_parser_can_finish():
    spec, binding, xml = paper()
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_vector(binding, xml, budget=replace(spec.budget, timeout=1e-6))
    assert caught.value.to_dict()['path'] == 'budget.timeout'


def test_compile_timeout_keeps_existing_output_and_leaves_no_staging_files(tmp_path, monkeypatch):
    rt = runtime()
    spec, binding, xml = paper()
    spec = replace(spec, budget=replace(spec.budget, timeout=0.2))
    source = c.VectorSource(binding.id, xml)
    monkeypatch.setattr(rt, '_worker_command', lambda: (sys.executable, '-c', 'import time; time.sleep(60)'))
    path = tmp_path / 'scene.xml'
    path.write_bytes(b'previous')
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(c.preflight(spec, (binding,)), (source,), path, overwrite=True)
    assert caught.value.to_dict()['path'] == 'budget.timeout'
    assert path.read_bytes() == b'previous'
    assert list(tmp_path.iterdir()) == [path]


def test_compile_memory_cap_reaches_the_worker_before_any_work(tmp_path, monkeypatch):
    rt = runtime()
    spec, binding, xml = paper()
    memory = 128 * 1024**2
    spec = replace(spec, budget=replace(spec.budget, max_memory_bytes=memory))
    code = f'''import resource, sys
assert resource.getrlimit(resource.RLIMIT_AS) == ({memory}, {memory})
try:
    bytearray({memory * 2})
except MemoryError:
    sys.stderr.buffer.write(b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\\n')
    sys.exit(86)
raise AssertionError('memory limit was not enforced')
'''
    monkeypatch.setattr(rt, '_worker_command', lambda: (sys.executable, '-c', code))
    output = tmp_path / 'new' / 'scene.xml'
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(c.preflight(spec, (binding,)), (c.VectorSource(binding.id, xml),), output)
    assert caught.value.to_dict()['path'] == 'budget.max_memory_bytes'
    assert not output.parent.exists()


@pytest.mark.parametrize(
    'reply',
    [
        b'',
        b'not-json',
        b'{}',
        b'{"schema":1,"schema":2}',
        b'{"schema":"srstudio.composition-worker/1.0.0","status":"ok","extra":1}',
    ],
)
def test_invalid_worker_replies_never_publish_output(tmp_path, monkeypatch, reply):
    rt = runtime()
    from srstudio._bounded_process import ProcessResult

    spec, binding, xml = paper()
    monkeypatch.setattr(rt, 'run', lambda *args, **kwargs: ProcessResult(reply, b'', 0))
    path = tmp_path / 'scene.xml'
    path.write_bytes(b'previous')
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(c.preflight(spec, (binding,)), (c.VectorSource(binding.id, xml),), path, overwrite=True)
    assert caught.value.to_dict()['code'] == 'composition.worker.protocol'
    assert path.read_bytes() == b'previous'


def test_remote_payload_failure_keeps_repair_fields():
    spec, binding, xml = paper()
    tiny = replace(binding, bounds=c.Bounds((0, 0, 0), (1, 1, 0)))
    with pytest.raises(c.CompositionError) as caught:
        c.compile_scene(c.preflight(spec, (tiny,)), (c.VectorSource(binding.id, xml),))
    diagnostic = caught.value.to_dict()
    assert diagnostic['code'] == 'composition.payload'
    assert diagnostic['path'] == 'payload.bounds'
    assert diagnostic['expected'] and diagnostic['remedy']


def test_worker_request_schema_is_closed():
    worker = importlib.import_module('srstudio._composition_worker')
    with pytest.raises(c.CompositionError):
        worker.dispatch(json.dumps({'schema': worker.SCHEMA, 'operation': 'compile', 'surprise': True}).encode())


def test_preparation_obeys_the_declared_node_budget_before_launch(monkeypatch):
    rt = runtime()
    spec, binding, xml = paper()

    def forbidden(*args, **kwargs):
        pytest.fail('known node budget exhaustion reached a worker')

    monkeypatch.setattr(rt, 'run', forbidden)
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_vector(binding, xml, budget=replace(spec.budget, max_nodes=1))
    assert caught.value.to_dict()['code'] == 'composition.budget'


def test_mutated_prepared_metadata_is_refused_with_a_typed_error():
    spec, binding, xml = paper()
    prepared = c.prepare_vector(binding, xml)
    with pytest.raises(c.CompositionError):
        c.compile_scene(c.preflight(spec, (binding,)), (replace(prepared, bounds=None),))


def request(operation='compile'):
    from dataclasses import asdict

    from srstudio import _composition_wire as wire

    spec, binding, xml = paper()
    if operation == 'prepare':
        return {'schema': wire.SCHEMA, 'operation': operation, 'binding': asdict(binding), 'xml': wire.xml_encode(xml)}
    return {
        'schema': wire.SCHEMA,
        'operation': operation,
        'plan': asdict(c.preflight(spec, (binding,))),
        'assets': [{'id': binding.id, 'xml': wire.xml_encode(xml), 'prepared': None}],
    }


@pytest.mark.parametrize('operation', ['compile', 'prepare'])
def test_worker_dispatch_validates_real_sources_and_emits_closed_results(operation):
    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker

    data = request(operation)
    result = worker.dispatch(wire.dumps(data))
    assert result['schema'] == wire.SCHEMA and result['status'] == 'ok'
    if operation == 'compile':
        assert result['plan_digest'] == data['plan']['digest']
        assert b'<composition>' in wire.xml_decode(result['xml'])
    else:
        assert result['prepared']['nodes'] > 0


@pytest.mark.parametrize('change', ['operation', 'plan', 'assets-type', 'id', 'duplicate', 'prepared'])
def test_worker_rechecks_malformed_or_stale_request_data(change):
    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker

    data = request()
    if change == 'operation':
        data['operation'] = 'unknown'
    elif change == 'plan':
        data['plan']['digest'] = '0' * 64
    elif change == 'assets-type':
        data['assets'] = 'xml'
    elif change == 'id':
        data['assets'][0]['id'] = 'missing'
    elif change == 'duplicate':
        data['assets'] *= 2
    else:
        data['assets'][0]['prepared'] = {
            'digest': '0' * 64,
            'bounds': data['plan']['bindings'][0]['bounds'],
            'nodes': 1,
        }
    with pytest.raises(c.CompositionError):
        worker.dispatch(wire.dumps(data))


@pytest.mark.parametrize('bad', ['digest', 'plan', 'nodes', 'xml', 'status', 'diagnostic'])
def test_worker_reply_identity_and_types_are_checked(tmp_path, monkeypatch, bad):
    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker
    from srstudio._bounded_process import ProcessResult

    rt = runtime()
    data = request()
    reply = worker.dispatch(wire.dumps(data))
    if bad == 'digest':
        reply['digest'] = '0' * 64
    elif bad == 'plan':
        reply['plan_digest'] = '0' * 64
    elif bad == 'nodes':
        reply['nodes'] = True
    elif bad == 'xml':
        reply['xml'] = 'not base64!'
    elif bad == 'status':
        reply['status'] = 'unknown'
    else:
        reply = {'schema': wire.SCHEMA, 'status': 'error', 'diagnostic': {}}
    monkeypatch.setattr(rt, 'run', lambda *args, **kwargs: ProcessResult(wire.dumps(reply), b'', 0))
    spec, binding, xml = paper()
    with pytest.raises(c.CompositionError) as caught:
        c.emit_scene(c.preflight(spec, (binding,)), (c.VectorSource(binding.id, xml),), tmp_path / 'scene.xml')
    assert caught.value.to_dict()['code'] == 'composition.worker.protocol'
    assert list(tmp_path.iterdir()) == []


def test_worker_main_preserves_diagnostics_and_has_a_fixed_memory_failure_message(monkeypatch):
    import io
    from types import SimpleNamespace

    from srstudio import _composition_wire as wire
    from srstudio import _composition_worker as worker

    output = io.BytesIO()
    monkeypatch.setattr(worker.sys, 'path', list(sys.path))
    monkeypatch.setattr(worker.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'{}')))
    monkeypatch.setattr(worker.sys, 'stdout', SimpleNamespace(buffer=output))
    worker.main()
    reply = wire.loads(output.getvalue())
    assert reply['status'] == 'error'
    assert reply['diagnostic']['code'] == 'composition.worker.protocol'

    def memory_failure(*args):
        raise MemoryError

    def exit_(code):
        raise SystemExit(code)

    messages = []
    monkeypatch.setattr(worker, 'dispatch', memory_failure)
    monkeypatch.setattr(worker.os, 'write', lambda fd, data: messages.append((fd, data)))
    monkeypatch.setattr(worker.os, '_exit', exit_)
    with pytest.raises(SystemExit) as caught:
        worker.main()
    assert caught.value.code == 86
    assert messages == [(2, b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\n')]


def test_remote_part_version_failure_retains_its_typed_cause():
    from srstudio.parts import UnknownVersionError

    _, binding, xml = paper()
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_vector(replace(binding, version=999999), xml)
    assert isinstance(caught.value.__cause__, UnknownVersionError)


def test_worker_startup_failure_exposes_bounded_stderr_for_agent_repair(monkeypatch):
    from srstudio._bounded_process import BoundedProcessError

    rt = runtime()
    spec, binding, xml = paper()

    def fail(*args, **kwargs):
        error = BoundedProcessError('worker failed', code='process.exit', actual=1)
        error.stderr = b'ImportError: missing runtime dependency'
        raise error

    monkeypatch.setattr(rt, 'run', fail)
    with pytest.raises(c.CompositionError) as caught:
        c.compile_scene(c.preflight(spec, (binding,)), (c.VectorSource(binding.id, xml),))
    result = caught.value.to_dict()
    assert result['code'] == 'composition.worker.exit'
    assert result['actual']['stderr'] == 'ImportError: missing runtime dependency'


def test_limb_cause_round_trip_keeps_context_and_residual():
    from srstudio import _composition_wire as wire
    from srstudio.limbs.errors import LimbError

    cause = LimbError('contact residual', code='contact', residual=0.125, context={'time': 0.5})
    restored = wire.cause_decode(wire.cause_encode(cause))
    assert type(restored) is LimbError
    assert restored.residual == cause.residual
    assert restored.context == cause.context
    assert restored.to_dict() == cause.to_dict()
