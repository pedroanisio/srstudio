"""Reverify sources, render/cache bounded plates, and publish complete mixed-scene bundles."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from . import _bundle_output, plates
from . import _composition_plate_wire as plate_wire
from . import _composition_proxy as proxy_payload
from . import _composition_wire as wire
from . import composition as c
from ._composition_emit import check_expansion
from ._composition_png import MAX_BYTES
from ._composition_preflight import _digest
from ._composition_runtime import _call
from ._outputs import _check_directory, pinned_directories

Assets = tuple[c.PreparedVector | c.VectorSource | c.PreparedPlate | c.PreparedProxy, ...]
CACHE_SCHEMA = 'srstudio.composition-render/1.0.0'
# Graphics backends need larger scratch/mapped files than the final PNG cap.
MAX_RENDER_FILE_BYTES = 256 * 1024**2


def _failure(path: str, expected: str, code: str = 'composition.payload') -> c.CompositionError:
    return c._fail(path, None, expected, code)


def _read(path: Path, maximum: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise _failure('file', 'a bounded regular input file')
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise _failure('file', 'input within the declared byte limit')
    return data


def _engine_hash(engine: Path) -> str:
    fd = os.open(engine, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= 1024**3:
            raise _failure('engine', 'a regular renderer executable of at most one GiB', 'composition.render')
        remaining, digest = info.st_size, hashlib.sha256()
        while remaining:
            block = stream.read(min(remaining, 1024**2))
            if not block:
                raise _failure('engine', 'an unchanged renderer executable', 'composition.render')
            remaining -= len(block)
            digest.update(block)
        if stream.read(1):
            raise _failure('engine', 'an unchanged renderer executable', 'composition.render')
    return digest.hexdigest()


def _inputs(
    plan: c.ValidatedScenePlan, assets: Assets
) -> tuple[dict[str, c.PreparedVector], dict[str, c.PreparedPlate | c.PreparedProxy]]:
    if type(plan) is not c.ValidatedScenePlan or type(assets) is not tuple or not 1 <= len(assets) <= c.MAX_LAYERS:
        raise _failure('plan/assets', 'a validated plan and bounded immutable asset tuple')
    if c.preflight(plan.spec, plan.bindings) != plan:
        raise _failure('plan', 'the current validated plan', 'composition.version')
    bindings = {b.id: b for b in plan.bindings}
    layers = {layer.id: layer for layer in plan.spec.layers}
    vectors: dict[str, c.VectorSource | c.PreparedVector] = {}
    raster_sources: dict[str, c.PreparedPlate | c.PreparedProxy] = {}
    total = 0
    for asset in assets:
        if type(asset) is c.PreparedPlate or type(asset) is c.PreparedProxy:
            if (
                type(asset.layer) is not str
                or asset.layer in raster_sources
                or asset.layer not in layers
                or type(asset.binding) is not c.AssetBinding
                or bindings.get(layers[asset.layer].asset) != asset.binding
                or asset.binding.backend != ('proxy' if type(asset) is c.PreparedProxy else 'plates')
            ):
                raise _failure('assets', 'one prepared raster for each supported placement')
            if type(asset) is c.PreparedPlate:
                if (
                    type(asset.xml) is not bytes
                    or type(asset.resources) is not tuple
                    or len(asset.resources) > plate_wire.MAX_RESOURCES
                ):
                    raise _failure('assets', 'bounded immutable prepared plate evidence')
                total += plate_wire.validate_source(asset.source)
            elif type(asset) is c.PreparedProxy:
                if (
                    type(asset.passes) is not tuple
                    or not 2 <= len(asset.passes) <= 4
                    or any(type(p) is not c.PreparedPlate for p in asset.passes)
                ):
                    raise _failure('assets', 'bounded immutable prepared proxy evidence')
                total += proxy_payload.validate_source(asset.source)
            raster_sources[asset.layer] = asset
        elif type(asset) is c.VectorSource or type(asset) is c.PreparedVector:
            if type(asset) is c.PreparedVector:
                if type(asset.binding) is not c.AssetBinding or bindings.get(asset.binding.id) != asset.binding:
                    raise _failure('assets', 'prepared vector evidence for this binding')
                name = asset.binding.id
            elif type(asset) is c.VectorSource:
                name = asset.id
            if type(name) is not str or name in vectors or name not in bindings or bindings[name].backend != 'vector':
                raise _failure('assets', 'one source for every vector binding')
            if type(asset.xml) is not bytes:
                raise _failure('assets.xml', 'immutable XML bytes')
            total += len(asset.xml)
            vectors[name] = asset
        else:
            raise _failure('assets', 'VectorSource, PreparedVector, PreparedPlate or PreparedProxy records')
        if total > MAX_BYTES:
            raise _failure('assets', 'at most eight MiB of combined source buffers', 'composition.budget')
    if set(vectors) != {b.id for b in bindings.values() if b.backend == 'vector'} or set(raster_sources) != {
        layer.id for layer in layers.values() if bindings[layer.asset].backend != 'vector'
    }:
        raise _failure('assets', 'exactly the supported inputs for every manifest layer')
    check_expansion(plan, {b.id: len(vectors[b.id].xml) if b.backend == 'vector' else 1024 for b in bindings.values()})
    checked_vectors: dict[str, c.PreparedVector] = {}
    checked_plates: dict[str, c.PreparedPlate | c.PreparedProxy] = {}
    for name, asset in sorted(vectors.items()):
        checked = c.prepare_vector(bindings[name], asset.xml, budget=plan.spec.budget)
        if type(asset) is c.PreparedVector and checked != asset:
            raise _failure('assets.' + name, 'unchanged prepared vector evidence')
        checked_vectors[name] = checked
    for layer, plate in sorted(raster_sources.items()):
        checked_plate: c.PreparedPlate | c.PreparedProxy
        if isinstance(plate, c.PreparedProxy):
            checked_plate = c.prepare_proxy(plan, layer, plate.source)
        else:
            checked_plate = c.prepare_plate(plan, layer, plate.source)
        if checked_plate != plate:
            raise _failure('assets.' + layer, 'unchanged prepared plate evidence')
        checked_plates[layer] = checked_plate
    return checked_vectors, checked_plates


def _png(data: bytes, asset: c.PreparedPlate, budget: c.RenderBudget) -> str:
    return _png_size(data, asset.width, asset.height, budget)


def _png_size(data: bytes, width: int, height: int, budget: c.RenderBudget) -> str:
    response = _call(
        {
            'schema': wire.SCHEMA,
            'operation': 'validate-png',
            'png': wire.xml_encode(data),
            'width': width,
            'height': height,
        },
        budget,
    )
    wire.fields(response, {'schema', 'status', 'digest'})
    digest = hashlib.sha256(data).hexdigest()
    if response['digest'] != digest:
        raise wire.fail(None, 'the exact verified PNG identity')
    return digest


def _key(asset: c.PreparedPlate, engine_hash: str) -> str:
    return _digest(
        {
            'schema': CACHE_SCHEMA,
            'engine': engine_hash,
            'xml': hashlib.sha256(asset.xml).hexdigest(),
            'resources': [(r.name, hashlib.sha256(r.data).hexdigest()) for r in asset.resources],
        }
    )


def _record(key: str, engine_hash: str, asset: c.PreparedPlate, digest: str) -> dict:
    return {
        'schema': CACHE_SCHEMA,
        'key': key,
        'engine': engine_hash,
        'image': digest,
        'width': asset.width,
        'height': asset.height,
    }


def _cached(entry: Path, key: str, engine_hash: str, asset: c.PreparedPlate, budget: c.RenderBudget) -> bytes | None:
    try:
        info = entry.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(info.st_mode):
        raise _failure('cache', 'an immutable private render directory', 'composition.cache')
    try:
        record = json.loads(_read(entry / 'record.json', 4096), object_pairs_hook=wire._unique)
        data = _read(entry / 'image.png', MAX_BYTES)
        if (
            type(record) is not dict
            or type(record.get('width')) is not int
            or type(record.get('height')) is not int
            or record != _record(key, engine_hash, asset, hashlib.sha256(data).hexdigest())
        ):
            raise _failure(
                'cache', 'a cache record matching the complete render and image identities', 'composition.cache'
            )
    except (OSError, ValueError, RecursionError) as error:
        raise _failure(
            'cache', 'an intact verified cache entry; remove or repair it explicitly', 'composition.cache'
        ) from error
    _png(data, asset, budget)
    return data


def _render(
    entry: Path, key: str, engine_hash: str, asset: c.PreparedPlate, engine: Path, budget: c.RenderBudget
) -> bytes:
    with (
        pinned_directories((entry,), private=True) as directories,
        tempfile.TemporaryDirectory(prefix='.srstudio-render-', dir=entry.parent) as temporary,
    ):
        work = Path(temporary)
        source = work / 'plate.scene.xml'
        plates._private_bytes(source, asset.xml)
        for resource in asset.resources:
            path = work / resource.name
            path.parent.mkdir(exist_ok=True, mode=0o700)
            plates._private_bytes(path, resource.data)
        printed_bytes = 0
        for resource in asset.resources:
            if not resource.name.endswith('.scene.xml'):
                continue
            document = work / resource.name
            picture = work / resource.name.replace('.scene.xml', '.png')
            project = ET.fromstring(resource.data).find('project')
            assert project is not None
            width, height = int(project.attrib['width']), int(project.attrib['height'])
            plates._engine_render(engine, document, picture)
            if _engine_hash(engine) != engine_hash:
                raise _failure('engine', 'unchanged renderer bytes throughout label rendering', 'composition.render')
            data = _read(picture, MAX_BYTES)
            _png_size(data, width, height, budget)
            printed_bytes += len(data)
            if printed_bytes > MAX_BYTES:
                raise _failure('print', 'at most eight MiB of rendered print resources', 'composition.budget')
            picture.chmod(0o600)
        output = work / 'image.png'
        plates._engine_render(engine, source, output)
        if _engine_hash(engine) != engine_hash:
            raise _failure('engine', 'the same renderer bytes throughout the invocation', 'composition.render')
        data = _read(output, MAX_BYTES)
        digest = _png(data, asset, budget)
        record = json.dumps(_record(key, engine_hash, asset, digest), sort_keys=True).encode()
        _check_directory(entry.parent, directories[entry.parent])
        try:
            _bundle_output.publish(entry, {'image.png': data, 'record.json': record})
        except FileExistsError as error:
            previous = _cached(entry, key, engine_hash, asset, budget)
            if previous != data:
                raise _failure(
                    'cache', 'deterministic pixels matching the concurrent cache writer', 'composition.cache'
                ) from error
        return data


def compile_bundle(plan: c.ValidatedScenePlan, assets: Assets, *, engine: Path, cache: Path) -> c.CompiledBundle:
    if not isinstance(engine, Path) or not isinstance(cache, Path):
        raise _failure('engine/cache', 'Path values for renderer and cache')
    vectors, prepared = _inputs(plan, assets)
    budget = plan.spec.budget
    images: dict[str, bytes] = {}
    try:
        engine = engine.resolve()
        engine_hash = _engine_hash(engine) if prepared else ''
        jobs = {}
        layer_keys = {}
        for layer, placement in prepared.items():
            passes = placement.passes if isinstance(placement, c.PreparedProxy) else (placement,)
            keys = []
            for asset in passes:
                key = _key(asset, engine_hash)
                jobs[key] = asset
                keys.append(key)
            layer_keys[layer] = tuple(keys)
        entries = {key: cache / 'composition' / engine_hash / key for key in jobs}
        # Validate all warm entries before starting any cold renderer work.
        for key, asset in jobs.items():
            cached = _cached(entries[key], key, engine_hash, asset, budget)
            if cached is not None:
                images[key] = cached
        warm = len(images)
        cold = len(jobs) - warm
        if cold > budget.max_new_plates:
            raise _failure('budget.max_new_plates', 'cold renders within the plan limit', 'composition.budget')
        with plates.render_session(
            max_invocations=budget.max_engine_invocations,
            timeout=budget.timeout,
            max_memory_bytes=budget.max_memory_bytes,
            max_file_bytes=MAX_RENDER_FILE_BYTES,
        ) as work:
            for key, asset in jobs.items():
                if key not in images:
                    with plates.render_session(
                        max_invocations=next(
                            j.engine_invocations for j in asset.binding.plates if j.key == asset.source_digest
                        ),
                        timeout=budget.timeout,
                        max_memory_bytes=budget.max_memory_bytes,
                        max_file_bytes=MAX_RENDER_FILE_BYTES,
                    ):
                        images[key] = _render(entries[key], key, engine_hash, asset, engine, budget)
        from ._composition_proxy_runtime import convert

        raster_images = {}
        for layer, placement in prepared.items():
            raw = tuple(images[key] for key in layer_keys[layer])
            raster_images[layer] = convert(plan, placement, raw) if isinstance(placement, c.PreparedProxy) else raw[0]
        resources = {hashlib.sha256(data).hexdigest(): data for data in raster_images.values()}
        if sum(map(len, resources.values())) + sum(len(v.xml) for v in vectors.values()) > MAX_BYTES:
            raise _failure('budget.bundle', 'at most eight MiB of combined vector/image inputs', 'composition.budget')
        response = _call(
            {
                'schema': wire.SCHEMA,
                'operation': 'compile-bundle',
                'plan': asdict(plan),
                'vectors': [{'id': name, 'xml': wire.xml_encode(v.xml)} for name, v in vectors.items()],
                'rasters': [
                    {
                        'layer': layer,
                        'png': wire.xml_encode(raster_images[layer]),
                        'meters_per_unit': asset.source.meters_per_unit,
                    }
                    for layer, asset in prepared.items()
                ],
            },
            budget,
        )
        wire.fields(response, {'schema', 'status', 'xml', 'digest', 'plan_digest', 'nodes'})
        xml = wire.xml_decode(response['xml'])
        if response['digest'] != hashlib.sha256(xml).hexdigest() or response['plan_digest'] != plan.digest:
            raise wire.fail(None, 'compiled content and manifest identities matching the request')
        if type(response['nodes']) is not int or not 1 <= response['nodes'] <= plan.cost.nodes:
            raise wire.fail(None, 'a node count within the manifest bound')
        if len(xml) + sum(map(len, resources.values())) > MAX_BYTES:
            raise _failure('budget.bundle', 'at most eight MiB of complete bundle files', 'composition.budget')
        if prepared and _engine_hash(engine) != engine_hash:
            raise _failure('engine', 'an unchanged renderer throughout the build', 'composition.render')
        files = tuple(c.BundleResource('image-' + digest + '.png', data) for digest, data in sorted(resources.items()))
        digest = _digest(
            {'xml': response['digest'], 'resources': [(r.name, hashlib.sha256(r.data).hexdigest()) for r in files]}
        )
        return c.CompiledBundle(
            xml, files, digest, plan.digest, response['nodes'], c.BundleWork(cold, warm, work.invocations)
        )
    except (OSError, plates.PlateError) as error:
        raise _failure('render', 'successful bounded rendering and cache publication', 'composition.render') from error


def emit_bundle(
    plan: c.ValidatedScenePlan, assets: Assets, output: Path, *, engine: Path, cache: Path
) -> c.CompiledBundle:
    if not isinstance(output, Path) or output.name in ('', '.', '..') or not isinstance(cache, Path):
        raise _failure('output/cache', 'distinct directory Paths')
    if output.exists() or output.is_symlink():
        raise _failure('output', 'a new bundle directory', 'composition.output')
    target, storage = output.resolve(), cache.resolve()
    if target.is_relative_to(storage) or storage.is_relative_to(target):
        raise _failure('output/cache', 'non-overlapping bundle and cache directories', 'composition.output')
    bundle = compile_bundle(plan, assets, engine=engine, cache=cache)
    try:
        _bundle_output.publish(output, {'scene.xml': bundle.xml, **{r.name: r.data for r in bundle.resources}})
    except OSError as error:
        raise _failure(
            'output', 'atomic publication to a new directory on a filesystem supporting renameat2', 'composition.output'
        ) from error
    return bundle
