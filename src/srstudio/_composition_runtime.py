"""Run public composition work under process limits and validate replies before publication."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import asdict
from pathlib import Path

from . import _composition_wire as wire
from . import composition as c
from ._bounded_process import BoundedProcessError, ProcessLimits, run
from ._composition_emit import check_expansion
from ._composition_preflight import _graph, _id
from ._composition_vector import MAX_XML_BYTES


def _worker_command() -> tuple[str, ...]:
    return sys.executable, '-I', str(Path(__file__).with_name('_composition_worker.py'))


def _call(request: dict, budget: c.RenderBudget) -> dict:
    return _call_worker(request, budget, command=_worker_command(), maximum=wire.MAX_WIRE_BYTES)


def _call_worker(request: dict, budget: c.RenderBudget, *, command: tuple[str, ...], maximum: int) -> dict:
    if type(budget) is not c.RenderBudget:
        raise c._fail('budget', None, 'RenderBudget')
    budget.__post_init__()
    payload = wire.dumps(request, maximum=maximum)
    limits = ProcessLimits(
        timeout=budget.timeout, memory_bytes=budget.max_memory_bytes, stdout_bytes=maximum, stderr_bytes=65536
    )
    try:
        result = run(command, input=payload, limits=limits)
    except BoundedProcessError as error:
        failure = error.to_dict()
        if failure['code'] == 'process.timeout':
            raise c._fail(
                'budget.timeout', budget.timeout, 'worker completion before the hard deadline', 'composition.budget'
            ) from error
        if failure['actual'] == 86 and error.stderr == b'SRSTUDIO_COMPOSITION_MEMORY_LIMIT\n':
            raise c._fail(
                'budget.max_memory_bytes',
                budget.max_memory_bytes,
                'work within the hard address-space cap',
                'composition.budget',
            ) from error
        raise c._fail(
            'worker',
            {'failure': failure, 'stderr': error.stderr.decode('utf-8', errors='replace')[-2000:]},
            'a successful bounded worker with supported kernel limits',
            'composition.worker.' + failure['code'].removeprefix('process.'),
        ) from error
    response = wire.loads(result.stdout, maximum=maximum)
    if response.get('status') == 'error':
        wire.fields(response, {'schema', 'status', 'diagnostic', 'cause'})
        diagnostic = wire.read_diagnostic(response['diagnostic'])
        raise c.CompositionError(
            diagnostic['message'],
            code=diagnostic['code'],
            path=diagnostic['path'],
            actual=diagnostic['actual'],
            expected=diagnostic['expected'],
            remedy=diagnostic['remedy'],
        ) from wire.cause_decode(response['cause'])
    if response.get('status') != 'ok':
        raise wire.fail(None, 'a successful result or typed diagnostic')
    return response


def prepare_vector(binding: c.AssetBinding, xml: bytes, *, budget: c.RenderBudget | None = None) -> c.PreparedVector:
    if type(binding) is not c.AssetBinding:
        raise c._fail('binding', None, 'AssetBinding')
    _graph(binding, [0])
    budget = c.RenderBudget() if budget is None else budget
    if type(budget) is not c.RenderBudget:
        raise c._fail('budget', None, 'RenderBudget')
    budget.__post_init__()
    if binding.nodes > budget.max_nodes:
        raise c._fail('budget.max_nodes', binding.nodes, f'<= {budget.max_nodes}', 'composition.budget')
    response = _call(
        {'schema': wire.SCHEMA, 'operation': 'prepare', 'binding': asdict(binding), 'xml': wire.xml_encode(xml)}, budget
    )
    wire.fields(response, {'schema', 'status', 'prepared'})
    asset = wire.prepared(binding, xml, response['prepared'])
    if asset.digest != hashlib.sha256(xml).hexdigest():
        raise wire.fail(asset.digest, 'the exact source content hash')
    return asset


def compile_scene(plan: c.ValidatedScenePlan, assets: tuple[c.PreparedVector | c.VectorSource, ...]) -> c.CompiledScene:
    if type(plan) is not c.ValidatedScenePlan or type(assets) is not tuple or not 1 <= len(assets) <= c.MAX_LAYERS:
        raise c._fail('plan/assets', None, 'a validated plan and immutable bounded source tuple')
    if c.preflight(plan.spec, plan.bindings, purpose=plan.purpose) != plan:
        raise c._fail('plan', plan.digest, 'the current reproducible preflight result', 'composition.version')
    bindings = {b.id: b for b in plan.bindings}
    sources = []
    sizes = {}
    seen = set()
    total = 0
    for asset in assets:
        if type(asset) is c.PreparedVector:
            if type(asset.binding) is not c.AssetBinding or bindings.get(asset.binding.id) != asset.binding:
                raise c._fail('assets', None, 'prepared evidence for the exact manifest binding', 'composition.payload')
            name, metadata = asset.binding.id, wire.prepared_metadata(asset)
        elif type(asset) is c.VectorSource:
            name, metadata = asset.id, None
        else:
            raise c._fail('assets', None, 'VectorSource or PreparedVector records')
        if type(name) is not str:
            raise c._fail('assets.id', name, 'a source identifier')
        _id(name, 'assets.id')
        if name not in bindings or name in seen:
            raise c._fail('assets.id', name, 'one source for each used binding', 'composition.reference')
        seen.add(name)
        encoded = wire.xml_encode(asset.xml)
        total += len(asset.xml)
        if total > MAX_XML_BYTES:
            raise c._fail('assets.xml', total, 'at most eight MiB of total source XML', 'composition.budget')
        sources.append({'id': name, 'xml': encoded, 'prepared': metadata})
        sizes[name] = len(asset.xml)
    if seen != set(bindings):
        raise c._fail('assets', tuple(seen), 'one source for every used binding', 'composition.reference')
    check_expansion(plan, sizes)
    response = _call(
        {'schema': wire.SCHEMA, 'operation': 'compile', 'plan': asdict(plan), 'assets': sources}, plan.spec.budget
    )
    wire.fields(response, {'schema', 'status', 'xml', 'digest', 'plan_digest', 'nodes'})
    xml = wire.xml_decode(response['xml'])
    if response['digest'] != hashlib.sha256(xml).hexdigest() or response['plan_digest'] != plan.digest:
        raise wire.fail(None, 'content and manifest identities matching the request')
    nodes = response['nodes']
    if type(nodes) is not int or not 1 <= nodes <= plan.cost.nodes:
        raise wire.fail(nodes, 'an actual node count within the manifest bound')
    return c.CompiledScene(xml, response['digest'], response['plan_digest'], nodes)
