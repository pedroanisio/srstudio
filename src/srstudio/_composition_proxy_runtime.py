"""Bounded proxy preparation/conversion and closed replies at the parent boundary."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, replace

from . import _composition_plate_wire as pw
from . import _composition_proxy as payload
from . import _composition_wire as wire
from . import composition as c
from ._composition_runtime import _call


def encode(source: c.ProxySource) -> dict:
    payload.validate_source(source)
    return {'geometry': pw.source_encode(payload.sources(source)[0]), 'recipe': asdict(source.recipe)}


def decode(value: object) -> c.ProxySource:
    data = wire.fields(value, {'geometry', 'recipe'})
    geometry = pw.source_decode(data['geometry'])
    source = c.ProxySource(
        geometry.id, geometry.meshes, wire.record(c.ProxyRecipe, data['recipe']), geometry.meters_per_unit
    )
    if payload.sources(source)[0] != geometry:
        raise wire.fail(None, 'the exact proxy geometry and derived light materials')
    payload.validate_source(source)
    return source


def prepare_proxy(plan: c.ValidatedScenePlan, layer: str, source: c.ProxySource) -> c.PreparedProxy:
    binding, view, sources = payload.context(plan, layer, source)
    response = _call(
        {
            'schema': wire.SCHEMA,
            'operation': 'prepare-proxy',
            'plan': asdict(plan),
            'layer': layer,
            'source': encode(source),
        },
        plan.spec.budget,
    )
    wire.fields(response, {'schema', 'status', 'passes', 'digest'})
    if type(response['passes']) is not list or len(response['passes']) != len(sources):
        raise wire.fail(None, 'exactly the required light/ID pass evidence')
    passes = tuple(
        pw.prepared_decode(raw, plan, layer, part, view=pass_view)
        for raw, part, pass_view in zip(response['passes'], sources, payload.views(view, len(sources)), strict=True)
    )
    asset = c.PreparedProxy(binding, source, layer, plan.digest, passes, '')
    if response['digest'] != payload.identity(asset):
        raise wire.fail(None, 'the complete proxy preparation identity')
    return replace(asset, digest=response['digest'])


def convert(plan: c.ValidatedScenePlan, asset: c.PreparedProxy, images: tuple[bytes, ...]) -> bytes:
    response = _call(
        {
            'schema': wire.SCHEMA,
            'operation': 'convert-proxy',
            'plan': asdict(plan),
            'layer': asset.layer,
            'source': encode(asset.source),
            'images': [wire.xml_encode(png) for png in images],
        },
        plan.spec.budget,
    )
    wire.fields(response, {'schema', 'status', 'png', 'digest'})
    data = wire.xml_decode(response['png'])
    if response['digest'] != hashlib.sha256(data).hexdigest():
        raise wire.fail(None, 'the complete converted PNG identity')
    return data
