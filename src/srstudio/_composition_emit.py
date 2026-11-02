"""Compile verified vector layers and atomically install a self-contained scene file."""

from __future__ import annotations

import hashlib
import math
import os
import secrets
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from sr_core.scene import Scene, read

from . import _composition_text as text_assets
from . import composition as c
from ._composition_forms import size as form_bytes
from ._composition_preflight import _camera, _pose
from ._composition_vector import MAX_XML_BYTES, prepare_vector
from ._outputs import _check_directory, pinned_directories
from .limbs.math3d import Vec3


def _number(value: float) -> str:
    return format(value, '.17g')


def _placement(layer: c.LayerSpec, spec: c.ScenePlan, poses: dict) -> dict[str, str]:
    frame, scale = poses[layer.id]
    x_axis = frame.rotation.rotate(Vec3(1, 0, 0))
    if layer.space == 'screen':
        x, y, angle = frame.origin.x, frame.origin.y, math.atan2(x_axis.y, x_axis.x)
    else:
        forward, right, down = _camera(spec.camera)
        delta = frame.origin - Vec3(*spec.camera.position)
        factor = spec.camera.scale
        if spec.camera.projection == 'perspective':
            factor *= spec.camera.focal / delta.dot(forward)
        x, y = spec.camera.origin[0] + delta.dot(right) * factor, spec.camera.origin[1] + delta.dot(down) * factor
        scale *= factor
        angle = math.atan2(x_axis.dot(down), x_axis.dot(right))
    return {
        'x': _number(x),
        'y': _number(y),
        'scaleX': _number(scale),
        'scaleY': _number(scale),
        'rotation': _number(math.degrees(angle)),
    }


def check_expansion(plan: c.ValidatedScenePlan, sizes: dict[str, int]) -> None:
    """Account for namespaced copies before launching a worker or allocating trees."""
    bindings = {binding.id: binding for binding in plan.bindings}
    output_bound = 2048 + sum(sizes[layer.asset] + 64 * bindings[layer.asset].nodes for layer in plan.spec.layers)
    memory_bound = plan.cost.memory_bytes + 8 * output_bound
    if output_bound > MAX_XML_BYTES or memory_bound > plan.spec.budget.max_memory_bytes:
        raise c._fail(
            'budget.expansion',
            (output_bound, memory_bound),
            'XML expansion within 8 MiB and the declared memory allowance',
            'composition.budget',
        )


def compile_scene(plan: c.ValidatedScenePlan, assets: tuple[c.PreparedVector, ...]) -> c.CompiledScene:
    started = time.monotonic()
    if type(plan) is not c.ValidatedScenePlan or type(assets) is not tuple or len(assets) > c.MAX_LAYERS:
        raise c._fail('plan/assets', None, 'a validated plan and immutable prepared vector tuple')
    checked = c.preflight(plan.spec, plan.bindings, purpose=plan.purpose)
    if checked != plan:
        raise c._fail('plan', plan.digest, 'the current reproducible preflight result', 'composition.version')
    if any(b.backend != 'vector' for b in plan.bindings):
        raise c._fail('bindings.backend', None, 'a proven vector emission adapter', 'composition.capability')
    budget = plan.spec.budget

    def checkpoint() -> None:
        if time.monotonic() - started > budget.timeout:
            raise c._fail(
                'budget.timeout', budget.timeout, 'compilation within the declared timeout', 'composition.budget'
            )

    if any(
        type(asset) is not c.PreparedVector or type(asset.binding) is not c.AssetBinding or type(asset.xml) is not bytes
        for asset in assets
    ):
        raise c._fail('assets', None, 'PreparedVector records')
    actual = {a.binding.id: a for a in assets}
    if len(actual) != len(assets) or set(actual) != {b.id for b in plan.bindings}:
        raise c._fail('assets', tuple(actual), 'exactly one prepared payload per used binding', 'composition.reference')
    if sum(len(asset.xml) + form_bytes(asset.binding.forms) for asset in assets) > MAX_XML_BYTES:
        raise c._fail('assets', None, 'at most eight MiB of combined source buffers', 'composition.budget')
    # Each placement owns a namespaced copy. Account for serialization and
    # parser working storage before allocating any expanded trees. The extra
    # per-node allowance covers scoped IDs, references and wrapper attributes.
    check_expansion(plan, {name: len(asset.xml) for name, asset in actual.items()})
    roots = {}
    for binding in plan.bindings:
        asset = actual[binding.id]
        if asset.binding != binding or prepare_vector(binding, asset.xml) != asset:
            raise c._fail(
                'assets.' + binding.id, None, 'the verified payload bound to this manifest', 'composition.payload'
            )
        roots[binding.id] = ET.fromstring(asset.xml)
        checkpoint()
    return assemble(plan, roots, {}, checkpoint)


def assemble(
    plan: c.ValidatedScenePlan, roots: dict[str, ET.Element], rasters: dict[str, dict], checkpoint: Callable[[], None]
) -> c.CompiledScene:
    """Shared layer assembly after worker-owned source verification."""
    from ._composition_forms import apply, static

    static(plan)
    spec = plan.spec
    budget = spec.budget
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
        },
    )
    has_text = any(source.find('assets/text') is not None for source in roots.values())
    if has_text:
        root.find('project').set('fontPolicy', 'pinned')  # type: ignore[union-attr]
    if rasters or has_text:
        shelf = ET.SubElement(root, 'assets')
        seen = set()
        images = (image for raster in rasters.values() for image in raster.get('frames', (raster,)))
        for raster in images:
            if raster['id'] not in seen:
                ET.SubElement(
                    shelf,
                    'image',
                    {
                        'id': raster['id'],
                        'src': raster['name'],
                        'width': str(raster['width']),
                        'height': str(raster['height']),
                    },
                )
                seen.add(raster['id'])
    paints = ET.SubElement(root, 'paints')
    content = ET.SubElement(root, 'composition')
    layers = {layer.id: layer for layer in spec.layers}
    poses: dict = {}
    for layer in spec.layers:
        _pose(layer, layers, poses, set())
    for index, layer in enumerate(spec.layers):
        if layer.id in rasters:
            raster = rasters[layer.id]
            if 'frames' in raster:
                parent = ET.SubElement(
                    content,
                    'group',
                    {'id': f'l{index}', 'start': _number(layer.temporal.start), 'end': _number(layer.temporal.end)},
                )
                for sample, frame in enumerate(raster['frames']):
                    group = ET.SubElement(
                        parent,
                        'group',
                        {
                            'id': f'l{index}__frame{sample}',
                            'x': _number(frame['offset'][0]),
                            'y': _number(frame['offset'][1]),
                            'start': _number(frame['start']),
                            'end': _number(frame['end']),
                        },
                    )
                    ET.SubElement(
                        group,
                        'layer',
                        {'id': f'l{index}__frame{sample}__image', 'asset': frame['id'], 'x': '0', 'y': '0'},
                    )
                    checkpoint()
                continue
            group = ET.SubElement(
                content,
                'group',
                {
                    'id': f'l{index}',
                    'x': _number(raster['offset'][0]),
                    'y': _number(raster['offset'][1]),
                    'start': _number(layer.temporal.start),
                    'end': _number(layer.temporal.end),
                },
            )
            ET.SubElement(group, 'layer', {'id': f'l{index}__image', 'asset': raster['id'], 'x': '0', 'y': '0'})
            checkpoint()
            continue
        # Source IDs and references are scoped per placement, including repeated
        # uses of an asset. Parent transforms are already flattened into poses.
        source = ET.fromstring(ET.tostring(roots[layer.asset]))
        apply(source, plan, layer, layer.temporal.source_start)
        text_assets.scope(source, f'l{index}')
        source_assets = source.find('assets')
        if source_assets is not None and len(source_assets):
            shelf.extend(source_assets)
        source_paints = source.find('paints')
        if source_paints is not None:
            paints.extend(source_paints)
        temporal = layer.temporal
        group = ET.SubElement(
            content,
            'group',
            {
                'id': f'l{index}',
                **_placement(layer, spec, poses),
                'start': _number(temporal.start),
                'end': _number(temporal.end),
                # Engine group clock: origin + (t - origin - offset) * scale.
                'timeOffset': _number((temporal.start - temporal.source_start) / temporal.rate),
                'timeScale': _number(temporal.rate),
            },
        )
        source_content = source.find('composition')
        assert source_content is not None  # prepare_vector verified structure
        group.extend(source_content)
        checkpoint()
    if not len(paints):
        root.remove(paints)
    from ._composition_review import mark

    xml = mark(ET.tostring(root, encoding='utf-8', xml_declaration=True), plan)
    nodes = sum(1 for _ in root.iter())
    if nodes > plan.cost.nodes or len(xml) > MAX_XML_BYTES or len(xml) * 8 > budget.max_memory_bytes:
        raise c._fail(
            'budget.output',
            (nodes, len(xml)),
            'output within declared node/memory and XML bounds',
            'composition.budget',
        )
    scene = read(xml)
    assert isinstance(scene, Scene)
    errors = scene.check(schema=True)
    if errors:
        raise c._fail(
            'output.schema', [str(e) for e in errors[:8]], 'a schema-valid compiled scene', 'composition.payload'
        )
    checkpoint()
    return c.CompiledScene(xml, hashlib.sha256(xml).hexdigest(), plan.digest, nodes)


def emit_scene(
    plan: c.ValidatedScenePlan,
    assets: tuple[c.PreparedVector | c.VectorSource, ...],
    output: Path,
    *,
    overwrite: bool = False,
) -> c.CompiledScene:
    compiled = c.compile_scene(plan, assets)
    if not isinstance(output, Path) or type(overwrite) is not bool:
        raise c._fail('output', None, 'a Path and an explicit boolean overwrite policy')
    try:
        with pinned_directories((output,), private=True) as directories:
            parent_fd = directories[output.parent]
            name = '.srstudio-composition-' + secrets.token_hex(12)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(compiled.xml)
                    stream.flush()
                    os.fsync(stream.fileno())
                _check_directory(output.parent, parent_fd)
                if overwrite:
                    os.replace(name, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                else:
                    os.link(name, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            finally:
                try:
                    os.unlink(name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
    except OSError as error:
        raise c._fail(
            'output', str(output), 'an atomically writable scene destination', 'composition.output'
        ) from error
    return compiled
