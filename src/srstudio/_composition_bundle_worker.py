"""Worker-only mixed layer assembly; raster images and vector XML are verified first."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from . import _composition_text as text_assets
from . import _composition_wire as wire
from . import composition as c
from ._composition_emit import assemble, check_expansion
from ._composition_forms import size as form_bytes
from ._composition_png import MAX_BYTES, verify
from ._composition_sequence import spans
from ._composition_vector import prepare_vector


def compile_bundle(request: dict) -> c.CompiledScene:
    wire.fields(request, {'schema', 'operation', 'plan', 'vectors', 'rasters'})
    plan = wire.record(c.ValidatedScenePlan, request['plan'])
    if c.preflight(plan.spec, plan.bindings, purpose=plan.purpose) != plan:
        raise wire.fail(None, 'the current validated manifest')
    if any(type(request[k]) is not list or len(request[k]) > c.MAX_LAYERS for k in ('vectors', 'rasters')):
        raise wire.fail(None, 'bounded source lists')
    bindings = {b.id: b for b in plan.bindings}
    layers = {layer.id: layer for layer in plan.spec.layers}
    roots, sizes = {}, {}
    rasters: dict[str, dict] = {}
    total = 0
    started = time.monotonic()

    def checkpoint() -> None:
        if time.monotonic() - started > plan.spec.budget.timeout:
            raise c._fail('budget.timeout', None, 'bundle assembly within the deadline', 'composition.budget')

    for item in request['vectors']:
        name, xml, fonts = wire.vector_decode(item)
        if type(name) is not str or name in roots or name not in bindings or bindings[name].backend != 'vector':
            raise wire.fail(None, 'one source per vector binding')
        total += len(xml) + text_assets.validate(fonts) + form_bytes(bindings[name].forms)
        if total > MAX_BYTES:
            raise wire.fail(total, 'at most eight MiB of combined bundle inputs')
        asset = prepare_vector(bindings[name], xml, fonts=fonts)
        roots[name], sizes[name] = text_assets.portable(ET.fromstring(asset.xml), fonts), len(xml) + 256 * len(fonts)
        checkpoint()
    image_names = set()
    for item in request['rasters']:
        animated = type(item) is dict and 'times' in item
        value = wire.fields(
            item,
            {'layer', 'meters_per_unit', 'times', 'images', 'frames'}
            if animated
            else {'layer', 'png', 'meters_per_unit'},
        )
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
        if animated:
            duration = bindings[layers[name].asset].duration
            if duration is None or any(
                type(value[k]) is not list or not 1 <= len(value[k]) <= c.MAX_RECORD_ITEMS
                for k in ('times', 'images', 'frames')
            ):
                raise wire.fail(None, 'bounded frames/images/times and a finite source duration')
            schedule = spans(tuple(value['times']), duration, layers[name].temporal)
            if len(value['frames']) != len(schedule) or any(
                type(i) is not int or not 0 <= i < len(value['images']) for i in value['frames']
            ):
                raise wire.fail(None, 'one valid image reference for each visible snapshot')
            if set(value['frames']) != set(range(len(value['images']))):
                raise wire.fail(None, 'exactly the referenced raster images')
            images = value['images']
        else:
            if bindings[layers[name].asset].duration is not None:
                raise wire.fail(None, 'a raster timeline for an animated binding')
            images = [value['png']]
        decoded = []
        for encoded in images:
            png = wire.xml_decode(encoded)
            digest = verify(png, view.width, view.height)
            if digest not in image_names:
                total += len(png)
                image_names.add(digest)
            if total > MAX_BYTES:
                raise wire.fail(total, 'at most eight MiB of combined bundle inputs')
            decoded.append(
                {
                    'id': 'img_' + digest,
                    'name': 'image-' + digest + '.png',
                    'width': view.width,
                    'height': view.height,
                    'offset': view.offset,
                }
            )
            checkpoint()
        if animated:
            rasters[name] = {
                'frames': [
                    {**decoded[index], 'start': span.start, 'end': span.end}
                    for index, span in zip(value['frames'], schedule, strict=True)
                ]
            }
        else:
            rasters[name] = decoded[0]
        sizes[layers[name].asset] = max(
            sizes.get(layers[name].asset, 0), 1024 + (128 * len(schedule) if animated else 0)
        )
        checkpoint()
    if set(roots) != {b.id for b in bindings.values() if b.backend == 'vector'} or set(rasters) != {
        layer.id for layer in layers.values() if bindings[layer.asset].backend != 'vector'
    }:
        raise wire.fail(None, 'exactly the supported sources for every manifest layer')
    check_expansion(plan, sizes)
    result = assemble(plan, roots, rasters, checkpoint)
    return result
