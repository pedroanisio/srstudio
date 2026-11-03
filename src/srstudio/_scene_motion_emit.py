"""Worker-owned timeline assembly with verified references and original source clocks."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

from sr_core.scene import Scene, read

from . import _composition_text as text_assets
from . import _composition_wire as wire
from . import _scene_motion_wire as tw
from . import composition as c
from ._composition_emit import _number, _placement
from ._composition_forms import size as form_bytes
from ._composition_png import MAX_BYTES, verify
from ._composition_preflight import _pose
from ._composition_vector import prepare_vector


def compile_timeline(request: dict) -> c.CompiledScene:
    wire.fields(request, {'schema', 'operation', 'timeline', 'vectors', 'images', 'placements'})
    if request['operation'] != 'compile-timeline':
        raise wire.fail(None, 'compile-timeline')
    from ._composition_forms import apply

    timeline = tw.decode(request['timeline'])
    spec = timeline.base.spec
    required = set(tw.references(timeline))
    for name, maximum in (('vectors', c.MAX_LAYERS), ('images', len(required)), ('placements', len(required))):
        if type(request[name]) is not list or len(request[name]) > maximum:
            raise wire.fail(None, 'bounded timeline input lists')
    bindings = {b.id: b for b in timeline.base.bindings if b.backend == 'vector'}
    vectors = {}
    total = 0
    for value in request['vectors']:
        name, xml, fonts = wire.vector_decode(value)
        if type(name) is not str or name not in bindings or name in vectors:
            raise wire.fail(None, 'one source per vector binding')
        total += len(xml) + text_assets.validate(fonts) + form_bytes(bindings[name].forms)
        if total > MAX_BYTES:
            raise wire.fail(None, 'bounded combined bundle inputs')
        vectors[name] = prepare_vector(bindings[name], xml, fonts=fonts)
    if vectors.keys() != bindings.keys():
        raise wire.fail(None, 'exactly the required vector sources')
    layout = tw.expansion(timeline, vectors)
    images = {}
    for value in request['images']:
        item = wire.fields(value, {'digest', 'png'})
        data = wire.xml_decode(item['png'])
        digest = hashlib.sha256(data).hexdigest()
        if item['digest'] != digest or digest in images:
            raise wire.fail(None, 'unique content-addressed image inputs')
        total += len(data)
        if total > MAX_BYTES:
            raise wire.fail(None, 'bounded combined bundle inputs')
        images[digest] = data
    placements: dict[tw.Reference, dict] = {}
    sources = {source.id: source for source in timeline.rasters}
    image_metadata = {}
    checked_images = set()
    for value in request['placements']:
        item = wire.fields(value, {'scene', 'layer', 'frame', 'image'})
        if (
            type(item['scene']) is not int
            or type(item['layer']) is not str
            or (item['frame'] is not None and type(item['frame']) is not int)
            or type(item['image']) is not str
        ):
            raise wire.fail(None, 'typed scene/layer/frame/image references')
        reference = (item['scene'], item['layer'], item['frame'])
        if reference not in required or reference in placements or item['image'] not in images:
            raise wire.fail(None, 'one image for each required raster placement')
        plan = timeline.samples[item['scene']]
        layer = next(layer for layer in plan.spec.layers if layer.id == item['layer'])
        raster_source = sources[layer.asset]
        unit = (
            raster_source.frames[0].source.meters_per_unit
            if isinstance(raster_source, c.RasterSequence)
            else raster_source.meters_per_unit
        )
        view = c.plate_view(plan, layer.id, meters_per_unit=unit)
        digest = item['image']
        check = (digest, view.width, view.height)
        if check not in checked_images:
            verify(images[digest], view.width, view.height)
            checked_images.add(check)
        metadata = {
            'id': 'img_' + digest,
            'src': 'image-' + digest + '.png',
            'width': str(view.width),
            'height': str(view.height),
        }
        image_metadata[digest] = metadata
        placements[reference] = {'image': metadata['id'], 'offset': view.offset}
    if placements.keys() != required or image_metadata.keys() != images.keys():
        raise wire.fail(None, 'exactly the referenced raster placements and images')
    roots = {name: ET.fromstring(asset.xml) for name, asset in vectors.items()}
    from ._composition_shadows import verify_roots

    verify_roots(timeline.base, roots)
    version = max(
        (root.attrib['version'] for root in roots.values()), default='1.1', key=lambda s: tuple(map(int, s.split('.')))
    )
    root = ET.Element('scene', {'version': version})
    ET.SubElement(
        root,
        'project',
        {
            'width': str(spec.width),
            'height': str(spec.height),
            'fps': f'{spec.fps.numerator}/{spec.fps.denominator}',
            'duration': _number(spec.duration),
            'seed': str(spec.seed),
            **({'background': spec.background} if spec.background is not None else {}),
        },
    )
    has_text = any(asset.fonts for asset in vectors.values())
    if has_text:
        root.find('project').set('fontPolicy', 'pinned')  # type: ignore[union-attr]
    shelf = None
    if images or has_text:
        shelf = ET.SubElement(root, 'assets')
        for digest in sorted(images):
            ET.SubElement(shelf, 'image', image_metadata[digest])
    paints = ET.SubElement(root, 'paints')
    content = ET.SubElement(root, 'composition')
    if layout is not None:
        from ._scene_motion_compact import assemble

        assemble(timeline, vectors, placements, layout, content, shelf, paints)
    for index, span in enumerate(() if layout is not None else timeline.spans):
        if not span.layers:
            continue
        plan = timeline.samples[span.scene]
        layers = {layer.id: layer for layer in plan.spec.layers}
        poses: dict = {}
        for layer in plan.spec.layers:
            _pose(layer, layers, poses, set())
        outer = ET.SubElement(
            content, 'group', {'id': f's{index}', 'start': _number(span.start), 'end': _number(span.end)}
        )
        samples = {r.layer: r.frame for r in span.rasters}
        for number, name in enumerate(span.layers):
            layer = layers[name]
            prefix = f's{index}__l{number}'
            if name in samples:
                raster = placements[span.scene, name, samples[name]]
                group = ET.SubElement(
                    outer, 'group', {'id': prefix, 'x': _number(raster['offset'][0]), 'y': _number(raster['offset'][1])}
                )
                ET.SubElement(group, 'layer', {'id': prefix + '__image', 'asset': raster['image'], 'x': '0', 'y': '0'})
                continue
            asset = vectors[layer.asset]
            source = text_assets.portable(ET.fromstring(asset.xml), asset.fonts)
            apply(source, plan, layer, span.start, scene_clock=True)
            text_assets.scope(source, prefix)
            source_assets = source.find('assets')
            if source_assets is not None and len(source_assets):
                assert shelf is not None
                shelf.extend(source_assets)
            source_paints = source.find('paints')
            if source_paints is not None:
                paints.extend(source_paints)
            temporal = layer.temporal
            group = ET.SubElement(
                outer,
                'group',
                {
                    'id': prefix,
                    **_placement(layer, plan.spec, poses, asset.binding),
                    'start': _number(temporal.start),
                    'end': _number(temporal.end),
                    'timeOffset': _number((temporal.start - temporal.source_start) / temporal.rate),
                    'timeScale': _number(temporal.rate),
                },
            )
            original = source.find('composition')
            assert original is not None  # prepare_vector verified structure
            group.extend(original)
    if not len(paints):
        root.remove(paints)
    from ._composition_review import mark

    xml = mark(ET.tostring(root, encoding='utf-8', xml_declaration=True), timeline.base)
    nodes = sum(1 for _ in root.iter())
    if (
        nodes > timeline.cost.nodes
        or len(xml) + sum(map(len, images.values())) + sum(len(r.data) for r in text_assets.resources(vectors.values()))
        > MAX_BYTES
        or len(xml) * 8 > spec.budget.max_memory_bytes
    ):
        raise c._fail('budget.output', (nodes, len(xml)), 'bounded timeline output', 'composition.budget')
    scene = read(xml)
    assert isinstance(scene, Scene)
    errors = scene.check(schema=True)
    if errors:
        raise wire.fail([str(error) for error in errors[:8]], 'a schema-valid compiled timeline')
    return c.CompiledScene(xml, hashlib.sha256(xml).hexdigest(), timeline.digest, nodes)
