"""Closed static proxy sources, deterministic render jobs and shared-view contracts."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Literal, cast

from . import _composition_plate_wire as pw
from . import clay, plates, proxy
from . import composition as c
from ._composition_preflight import _digest, _graph, _id


def fail(path: str, expected: str) -> c.CompositionError:
    return c._fail('proxy.' + path, None, expected, 'composition.payload')


def recipe(value: c.ProxyRecipe) -> proxy.Recipe:
    if type(value) is not c.ProxyRecipe:
        raise fail('recipe', 'an immutable ProxyRecipe')
    _graph(value, [0])
    names = [p.name for p in value.parts]
    if not 1 <= len(names) <= 64 or len(names) != len(set(names)):
        raise fail('parts', '1..64 unique named parts')
    for name in names:
        _id(name, 'proxy.parts.name')
    for group in (value.behind, value.under, *value.quiet):
        if len(group) != len(set(group)):
            raise fail('parts', 'part names without duplicate membership')
    try:
        return proxy.Recipe(
            {p.name: p.tones for p in value.parts},
            value.quiet,
            frozenset(value.behind),
            frozenset(value.under),
            {p.name: p.roughness for p in value.parts},
            lights=(),
            ink=proxy.Ink(**asdict(value.ink)),
            thresholds=value.thresholds,
            soft_edge=value.soft_edge,
            oversample=value.oversample,
            grain_seed=value.grain_seed,
        )
    except proxy.ProxyError as error:
        raise fail('recipe', 'valid proxy tone, ink and part relationships') from error


def sources(source: c.ProxySource) -> tuple[c.PlateSource, ...]:
    if type(source) is not c.ProxySource:
        raise fail('source', 'an immutable ProxySource')
    style = recipe(source.recipe)
    light = tuple(c.PlateMaterial(n, '#9a9a9a', style.rough[n]) for n in style.names)
    ids = tuple(
        c.PlateMaterial(n, '#000000', emissive='#{:02x}{:02x}{:02x}'.format(*style.ids[n])) for n in style.names
    )
    base = c.PlateSource(source.id, source.meshes, light, source.meters_per_unit)
    pw.validate_source(base)
    names = {mesh.material for mesh in source.meshes}
    if names - set(style.names) or set(style.under) - names:
        raise fail('meshes', 'declared material names and actual geometry for every under part')
    result = [base, replace(base, materials=ids)]
    if style.under:
        subset = tuple(mesh for mesh in source.meshes if mesh.material in style.under)
        result.extend((replace(base, meshes=subset), replace(base, meshes=subset, materials=ids)))
    return tuple(result)


def validate_source(source: c.ProxySource) -> int:
    raw = sources(source)
    total = pw.validate_source(raw[0]) + len(str(asdict(source.recipe)).encode('utf-8'))
    if total > pw.MAX_BYTES:
        raise fail('source', 'at most eight MiB of geometry and recipe data')
    return total


def source_digest(source: c.ProxySource) -> str:
    validate_source(source)
    return _digest(
        {
            'schema': 'srstudio.proxy-source/1.0.0',
            'recipe': asdict(source.recipe),
            'passes': [pw.source_digest(p) for p in sources(source)],
        }
    )


def snapshot(
    id: str,
    meshes: tuple[clay.Mesh, ...],
    value: proxy.Recipe,
    *,
    basis: Literal['canonical', 'clay'],
    lighting: Literal['scene'],
    meters_per_unit: float | None,
) -> c.ProxySource:
    if type(value) is not proxy.Recipe or lighting != 'scene':
        raise fail('lighting', "a proxy.Recipe and explicit lighting='scene' ownership")
    if type(meshes) is not tuple or not 1 <= len(meshes) <= pw.MAX_MESHES:
        raise fail('meshes', '1..128 meshes in an immutable tuple')
    try:
        value.__post_init__()
    except proxy.ProxyError as error:
        raise fail('recipe', 'a valid proxy.Recipe snapshot') from error
    style = c.ProxyRecipe(
        tuple(
            c.ProxyPart(n, cast(tuple[str, str, str, str], tuple(value.tones[n])), value.rough.get(n, 0.6))
            for n in value.names
        ),
        tuple(tuple(group) for group in value.quiet),
        tuple(sorted(value.behind)),
        tuple(sorted(value.under)),
        c.ProxyInk(**asdict(value.ink)),
        cast(tuple[float, float, float], tuple(value.thresholds)),
        value.soft_edge,
        value.oversample,
        value.grain_seed,
    )
    copied = []
    total = len(str(asdict(style)).encode('utf-8'))
    for mesh in meshes:
        frozen = c.plate_mesh(mesh, basis=basis)
        total += sum(len(buf) for buf in (frozen.vertices, frozen.normals, frozen.triangles, frozen.uvs or b''))
        if total > pw.MAX_BYTES:
            raise fail('source', 'at most eight MiB of geometry and recipe data')
        copied.append(frozen)
    result = c.ProxySource(id, tuple(copied), style, meters_per_unit)
    validate_source(result)
    return result


def jobs(source: c.ProxySource, *, width: int, height: int, memory_bytes: int) -> tuple[c.PlateWork, ...]:
    validate_source(source)
    if any(type(v) is not int or not 2 <= v <= 8192 for v in (width, height)):
        raise fail('dimensions', 'integer final view bounds in 2..8192')
    size = source.recipe.oversample
    return tuple(
        c.PlateWork(key, width * size, height * size, plates.SAMPLES, plates.BOUNCES, 1, memory_bytes)
        for key in dict.fromkeys(pw.source_digest(p) for p in sources(source))
    )


def context(
    plan: c.ValidatedScenePlan, layer: str, source: c.ProxySource, *, sequence: bool = False
) -> tuple[c.AssetBinding, c.PlateView, tuple[c.PlateSource, ...]]:
    size = validate_source(source)
    view = c.plate_view(plan, layer, meters_per_unit=source.meters_per_unit)
    selected = next(item for item in plan.spec.layers if item.id == layer)
    if selected.asset != source.id:
        raise fail('source.id', 'the source for the selected layer')
    binding = next(b for b in plan.bindings if b.id == source.id)
    if binding.backend != 'proxy' or (binding.duration is not None) != sequence:
        raise fail('binding', 'a finite sequence proxy binding' if sequence else 'a static proxy binding')
    if not sequence:
        from ._composition_review import check_source

        check_source(binding, source_digest(source))
    if len(selected.passes) != 1 or (selected.passes == ('under',) and not source.recipe.under):
        raise fail('passes', 'one selected pass per layer; under requires designated under geometry')
    raw = sources(source)
    declared, required_keys = {j.key for j in binding.plates}, {pw.source_digest(p) for p in raw}
    if not (required_keys <= declared if sequence else required_keys == declared):
        raise fail(
            'jobs',
            'the required raw jobs within the validated sequence'
            if sequence
            else 'exactly the unique proxy_jobs declarations for this source',
        )
    n = source.recipe.oversample
    view = replace(view, width=view.width * n, height=view.height * n)
    pixels = view.width * view.height
    if max(view.width, view.height) > 8192 or pixels > plan.spec.budget.max_frame_pixels:
        raise fail('dimensions', 'oversampled dimensions within 8192 and the frame pixel budget')
    # Part classification creates a pixel x part x RGB distance tensor. Reserve
    # intermediates and output storage as well as the immutable geometry.
    required = size * 8 + pixels * (64 * len(source.recipe.parts) + 512)
    if binding.memory_bytes < required:
        raise fail('memory_bytes', f'at least {required} bytes for geometry and pixel conversion')
    return binding, view, raw


def identity(asset: c.PreparedProxy) -> str:
    return _digest(
        {
            'schema': 'srstudio.prepared-proxy/1.0.0',
            'plan': asset.plan_digest,
            'layer': asset.layer,
            'source': source_digest(asset.source),
            'passes': [p.digest for p in asset.passes],
        }
    )


def views(view: c.PlateView, count: int) -> tuple[c.PlateView, ...]:
    dark = replace(view, lights=(plates.Light('nil', 'ambient', '#000000', 0),))
    return (view, dark) * (count // 2)
