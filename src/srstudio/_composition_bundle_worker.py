"""Worker-only mixed layer assembly; raster images and vector XML are verified first."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from . import _composition_wire as wire
from . import composition as c
from ._composition_emit import assemble, check_expansion
from ._composition_png import MAX_BYTES, verify
from ._composition_vector import prepare_vector


def compile_bundle(request: dict) -> c.CompiledScene:
    wire.fields(request, {'schema', 'operation', 'plan', 'vectors', 'rasters'})
    plan = wire.record(c.ValidatedScenePlan, request['plan'])
    if c.preflight(plan.spec, plan.bindings) != plan:
        raise wire.fail(None, 'the current validated manifest')
    if any(type(request[k]) is not list or len(request[k]) > c.MAX_LAYERS for k in ('vectors', 'rasters')):
        raise wire.fail(None, 'bounded source lists')
    bindings = {b.id: b for b in plan.bindings}
    layers = {layer.id: layer for layer in plan.spec.layers}
    roots, sizes, rasters = {}, {}, {}
    total = 0
    started = time.monotonic()

    def checkpoint() -> None:
        if time.monotonic() - started > plan.spec.budget.timeout:
            raise c._fail('budget.timeout', None, 'bundle assembly within the deadline', 'composition.budget')

    for item in request['vectors']:
        value = wire.fields(item, {'id', 'xml'})
        name = value['id']
        if type(name) is not str or name in roots or name not in bindings or bindings[name].backend != 'vector':
            raise wire.fail(None, 'one source per vector binding')
        xml = wire.xml_decode(value['xml'])
        total += len(xml)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of combined bundle inputs')
        asset = prepare_vector(bindings[name], xml)
        roots[name], sizes[name] = ET.fromstring(asset.xml), len(xml)
        checkpoint()
    image_names = set()
    for item in request['rasters']:
        value = wire.fields(item, {'layer', 'png', 'meters_per_unit'})
        name = value['layer']
        if (
            type(name) is not str
            or name in rasters
            or name not in layers
            or bindings[layers[name].asset].backend not in ('plates', 'proxy')
        ):
            raise wire.fail(None, 'one raster per plate or proxy placement')
        if len(layers[name].passes) != 1:
            raise wire.fail(None, 'one explicitly selected raster pass per layer')
        view = c.plate_view(plan, name, meters_per_unit=value['meters_per_unit'])
        png = wire.xml_decode(value['png'])
        digest = verify(png, view.width, view.height)
        if digest not in image_names:
            total += len(png)
            image_names.add(digest)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of combined bundle inputs')
        rasters[name] = {
            'id': 'img_' + digest,
            'name': 'image-' + digest + '.png',
            'width': view.width,
            'height': view.height,
            'offset': view.offset,
        }
        sizes[layers[name].asset] = 1024
        checkpoint()
    if set(roots) != {b.id for b in bindings.values() if b.backend == 'vector'} or set(rasters) != {
        layer.id for layer in layers.values() if bindings[layer.asset].backend != 'vector'
    }:
        raise wire.fail(None, 'exactly the supported sources for every manifest layer')
    check_expansion(plan, sizes)
    result = assemble(plan, roots, rasters, checkpoint)
    return result
