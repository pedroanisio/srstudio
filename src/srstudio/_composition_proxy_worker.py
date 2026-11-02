"""Worker-only static proxy geometry preparation and verified pixel conversion."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from . import _composition_plate_wire as pw
from . import _composition_proxy as payload
from . import _composition_wire as wire
from . import composition as c
from . import plates, proxy
from ._composition_plate import prepare_source
from ._composition_png import MAX_BYTES, verify
from ._composition_png import decode as decode_png
from ._composition_proxy_runtime import decode


def prepare_proxy(plan: c.ValidatedScenePlan, layer: str, source: c.ProxySource) -> c.PreparedProxy:
    binding, view, sources = payload.context(plan, layer, source)
    jobs = {job.key: job for job in binding.plates}
    passes = tuple(
        prepare_source(plan, layer, part, binding, jobs[pw.source_digest(part)], pass_view)
        for part, pass_view in zip(sources, payload.views(view, len(sources)), strict=True)
    )
    if (
        sum(p.nodes for p in passes) > binding.nodes
        or sum(len(p.xml) + sum(len(r.data) for r in p.resources) for p in passes) > MAX_BYTES
    ):
        raise payload.fail('resources', 'combined passes within the binding node and eight MiB payload limits')
    asset = c.PreparedProxy(binding, source, layer, plan.digest, passes, '')
    return replace(asset, digest=payload.identity(asset))


def convert(request: dict) -> bytes:
    wire.fields(request, {'schema', 'operation', 'plan', 'layer', 'source', 'images'})
    plan = wire.record(c.ValidatedScenePlan, request['plan'])
    source = decode(request['source'])
    _, view, sources = payload.context(plan, request['layer'], source)
    if type(request['images']) is not list or len(request['images']) != len(sources):
        raise payload.fail('images', 'one verified PNG for each light/ID pass')
    images = tuple(wire.xml_decode(value) for value in request['images'])
    if sum(map(len, images)) > MAX_BYTES:
        raise payload.fail('images', 'at most eight MiB of combined raw PNG inputs')
    arrays = [decode_png(image, view.width, view.height) for image in images]
    style = payload.recipe(source.recipe)
    rgba, parts = proxy.composite(arrays[0], arrays[1], style)
    selected = next(layer.passes[0] for layer in plan.spec.layers if layer.id == request['layer'])
    if selected == 'under':
        rgba, _ = proxy.composite(arrays[2], arrays[3], style)
    elif selected in ('back', 'front'):
        rgba = proxy.split(rgba, parts, style)[0 if selected == 'back' else 1]
    if not np.isfinite(rgba).all():
        raise payload.fail('pixels', 'finite converted RGBA values')
    output = plates._png_bytes(proxy._bytes(proxy._down(rgba, style.oversample)))
    verify(output, view.width // style.oversample, view.height // style.oversample)
    return output
