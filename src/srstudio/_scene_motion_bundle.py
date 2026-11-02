"""Stream verified timeline placements through one shared render/cache budget."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from . import _composition_bundle as bundle
from . import _composition_text as text_assets
from . import _composition_wire as wire
from . import _scene_motion_wire as tw
from . import composition as c
from . import plates
from . import scene_motion as m
from ._composition_forms import size as form_bytes
from ._composition_preflight import _digest
from ._composition_proxy_runtime import convert
from ._composition_runtime import _call_worker
from ._scene_motion_plan import _sources

Vectors = tuple[c.VectorSource | c.PreparedVector, ...]


def _vectors(timeline: m.SceneTimeline, assets: Vectors) -> dict[str, c.PreparedVector]:
    if type(assets) is not tuple or len(assets) > c.MAX_LAYERS:
        raise wire.fail(None, 'an immutable bounded vector source tuple')
    bindings = {b.id: b for b in timeline.base.bindings if b.backend == 'vector'}
    sources = {}
    total = sum(info.size for info in _sources(timeline.base, timeline.rasters).values())
    for asset in assets:
        if type(asset) is c.PreparedVector:
            if type(asset.binding) is not c.AssetBinding or bindings.get(asset.binding.id) != asset.binding:
                raise wire.fail(None, 'prepared vector evidence for this binding')
            wire.prepared_metadata(asset)
            name = asset.binding.id
        elif type(asset) is c.VectorSource:
            name = asset.id
        else:
            raise wire.fail(None, 'VectorSource or PreparedVector records')
        if type(name) is not str or name not in bindings or name in sources or type(asset.xml) is not bytes:
            raise wire.fail(None, 'one immutable XML source for each vector binding')
        total += len(asset.xml) + text_assets.validate(asset.fonts) + form_bytes(bindings[name].forms)
        if total > bundle.MAX_BYTES:
            raise wire.fail(None, 'at most eight MiB of combined source buffers')
        sources[name] = asset
    if sources.keys() != bindings.keys():
        raise wire.fail(None, 'exactly the required vector sources')
    result = {}
    from ._composition_shadows import prepare_vector as shadow_prepare

    for name, asset in sources.items():
        verified = shadow_prepare(timeline.base, bindings[name], asset)
        if type(asset) is c.PreparedVector and asset != verified:
            raise wire.fail(None, 'unchanged prepared vector evidence')
        result[name] = verified
    tw.expansion(timeline, result)
    return result


def _prepare(plan: c.ValidatedScenePlan, layer: str, source: m.RasterSource) -> bundle.Placement:
    if isinstance(source, c.RasterSequence):
        return c.prepare_raster_sequence(plan, layer, source)
    if isinstance(source, c.ProxySource):
        return c.prepare_proxy(plan, layer, source)
    return c.prepare_plate(plan, layer, source)


def _frame(placement: bundle.Placement, frame: int | None) -> bundle.Raster:
    if isinstance(placement, c.PreparedRasterSequence):
        assert frame is not None  # references come from a recomputed planner
        return placement.frames[frame].asset
    return placement


def _passes(asset: bundle.Raster) -> tuple[c.PreparedPlate, ...]:
    return asset.passes if isinstance(asset, c.PreparedProxy) else (asset,)


def _worker_command() -> tuple[str, ...]:
    return sys.executable, '-I', str(Path(__file__).with_name('_scene_motion_worker.py'))


def compile_timeline(timeline: m.SceneTimeline, vectors: Vectors, *, engine: Path, cache: Path) -> c.CompiledBundle:
    if not isinstance(engine, Path) or not isinstance(cache, Path):
        raise wire.fail(None, 'Path values for renderer and cache')
    timeline = tw.checked(timeline)
    verified = _vectors(timeline, vectors)
    request = {
        'schema': wire.SCHEMA,
        'operation': 'compile-timeline',
        'timeline': tw.encode(timeline),
        'vectors': [wire.vector_encode(name, v) for name, v in verified.items()],
        'images': [],
        'placements': [],
    }
    wire.dumps(request, maximum=tw.MAX_WIRE_BYTES)
    budget = timeline.base.spec.budget
    sources = {s.id: s for s in timeline.rasters}
    references = tw.references(timeline)
    wanted: dict[tuple[str, str], list[tw.Reference]] = {}
    for reference in references:
        index, layer_name, _ = reference
        wanted.setdefault((timeline.samples[index].digest, layer_name), []).append(reference)
    receipts: dict[tuple[str, str], str] = {}
    jobs: dict[str, tuple[int, int, c.PlateWork]] = {}
    keys: dict[tw.Reference, tuple[str, ...]] = {}
    resources: dict[str, bytes] = {}
    try:
        engine = engine.resolve()
        engine_hash = bundle._engine_hash(engine) if sources else ''
        # Prepare every view and snapshot before any cache writes, then discard
        # its geometry. Retain bounded identities, not an expanded movie of meshes.
        for plan in (*timeline.samples, timeline.terminal):
            for layer in plan.spec.layers:
                if layer.asset not in sources or (plan.digest, layer.id) in receipts:
                    continue
                prepared = _prepare(plan, layer.id, sources[layer.asset])
                receipts[plan.digest, layer.id] = prepared.digest
                for reference in wanted.get((plan.digest, layer.id), ()):
                    raw_passes = _passes(_frame(prepared, reference[2]))
                    keys[reference] = tuple(bundle._key(asset, engine_hash) for asset in raw_passes)
                    for key, plate in zip(keys[reference], raw_passes, strict=True):
                        declared = next(j for j in plate.binding.plates if j.key == plate.source_digest)
                        metadata = (plate.width, plate.height, declared)
                        if key in jobs and jobs[key] != metadata:
                            # Repeated renders may carry conservative differing declarations.
                            old = jobs[key]
                            if old[:2] != metadata[:2]:
                                raise wire.fail(None, 'consistent raw image dimensions')
                            if declared != old[2]:
                                from dataclasses import replace

                                declared = replace(
                                    declared,
                                    width=max(declared.width, old[2].width),
                                    height=max(declared.height, old[2].height),
                                    samples=max(declared.samples, old[2].samples),
                                    bounces=max(declared.bounces, old[2].bounces),
                                    engine_invocations=max(declared.engine_invocations, old[2].engine_invocations),
                                    memory_bytes=max(declared.memory_bytes, old[2].memory_bytes),
                                )
                        jobs[key] = (plate.width, plate.height, declared)
        actual = (
            len(jobs),
            sum(j.engine_invocations for _, _, j in jobs.values()),
            sum(j.width * j.height * j.samples for _, _, j in jobs.values()),
            max((j.bounces for _, _, j in jobs.values()), default=0),
        )
        expected = (
            timeline.cost.unique_plates,
            timeline.cost.engine_invocations,
            timeline.cost.samples,
            timeline.cost.bounces,
        )
        if any(a > b for a, b in zip(actual, expected, strict=True)):
            raise wire.fail(actual, 'actual render work within the planned aggregate bounds')
        if sources and bundle._engine_hash(engine) != engine_hash:
            raise bundle._failure('engine', 'unchanged renderer after preparation', 'composition.render')
        entries = {key: cache / 'composition' / engine_hash / key for key in jobs}
        warm = set()
        for key, (width, height, _) in jobs.items():
            if bundle._cached_size(entries[key], key, engine_hash, width, height, budget) is not None:
                warm.add(key)
        cold = len(jobs) - len(warm)
        done = set(warm)
        placements = {}
        output_bytes = sum(
            len(v.xml) + text_assets.validate(v.fonts) + form_bytes(v.binding.forms) for v in verified.values()
        )
        with plates.render_session(
            max_invocations=min(budget.max_engine_invocations, timeline.cost.engine_invocations),
            timeout=budget.timeout,
            max_memory_bytes=budget.max_memory_bytes,
            max_file_bytes=bundle.MAX_RENDER_FILE_BYTES,
        ) as work:
            for (plan_digest, layer_name), refs in wanted.items():
                plan = timeline.samples[refs[0][0]]
                asset_id = next(item.asset for item in plan.spec.layers if item.id == layer_name)
                prepared = _prepare(plan, layer_name, sources[asset_id])
                if prepared.digest != receipts[plan_digest, layer_name]:
                    raise wire.fail(None, 'unchanged preparation evidence throughout compilation')
                for reference in refs:
                    asset = _frame(prepared, reference[2])
                    raw_images = []
                    for key, raw in zip(keys[reference], _passes(asset), strict=True):
                        if bundle._key(raw, engine_hash) != key:
                            raise wire.fail(None, 'unchanged raw render identity')
                        if key not in done:
                            with plates.render_session(
                                max_invocations=jobs[key][2].engine_invocations,
                                timeout=budget.timeout,
                                max_memory_bytes=budget.max_memory_bytes,
                                max_file_bytes=bundle.MAX_RENDER_FILE_BYTES,
                            ):
                                data = bundle._render(entries[key], key, engine_hash, raw, engine, budget)
                            done.add(key)
                        else:
                            cached = bundle._cached(entries[key], key, engine_hash, raw, budget)
                            if cached is None:
                                raise bundle._failure('cache', 'an unchanged verified entry', 'composition.cache')
                            data = cached
                        raw_images.append(data)
                    image = (
                        convert(plan, asset, tuple(raw_images), sequence=asset.binding.duration is not None)
                        if isinstance(asset, c.PreparedProxy)
                        else raw_images[0]
                    )
                    digest = hashlib.sha256(image).hexdigest()
                    if digest not in resources:
                        output_bytes += len(image)
                        if output_bytes > bundle.MAX_BYTES:
                            raise wire.fail(None, 'at most eight MiB of combined vector/image inputs')
                        resources[digest] = image
                    placements[reference] = digest
        request['images'] = [{'digest': d, 'png': wire.xml_encode(png)} for d, png in sorted(resources.items())]
        request['placements'] = [
            {'scene': r[0], 'layer': r[1], 'frame': r[2], 'image': placements[r]} for r in references
        ]
        response = _call_worker(request, budget, command=_worker_command(), maximum=tw.MAX_WIRE_BYTES)
        wire.fields(response, {'schema', 'status', 'xml', 'digest', 'plan_digest', 'nodes'})
        xml = wire.xml_decode(response['xml'])
        if response['digest'] != hashlib.sha256(xml).hexdigest() or response['plan_digest'] != timeline.digest:
            raise wire.fail(None, 'compiled content and timeline identities matching the request')
        if type(response['nodes']) is not int or not 1 <= response['nodes'] <= timeline.cost.nodes:
            raise wire.fail(None, 'a node count within the timeline bound')
        font_files = text_assets.resources(verified.values())
        if len(xml) + sum(map(len, resources.values())) + sum(len(r.data) for r in font_files) > bundle.MAX_BYTES:
            raise wire.fail(None, 'at most eight MiB of complete bundle files')
        if sources and bundle._engine_hash(engine) != engine_hash:
            raise bundle._failure('engine', 'unchanged renderer throughout compilation', 'composition.render')
        files = tuple(c.BundleResource('image-' + d + '.png', png) for d, png in sorted(resources.items())) + font_files
        digest = _digest(
            {'xml': response['digest'], 'resources': [(r.name, hashlib.sha256(r.data).hexdigest()) for r in files]}
        )
        return c.CompiledBundle(
            xml, files, digest, timeline.digest, response['nodes'], c.BundleWork(cold, len(warm), work.invocations)
        )
    except (OSError, plates.PlateError) as error:
        raise bundle._failure('render', 'successful bounded timeline compilation', 'composition.render') from error


def emit_timeline(
    timeline: m.SceneTimeline, vectors: Vectors, output: Path, *, engine: Path, cache: Path
) -> c.CompiledBundle:
    bundle._validate_destination(output, cache)
    result = compile_timeline(timeline, vectors, engine=engine, cache=cache)
    bundle._publish_bundle(output, result)
    return result
