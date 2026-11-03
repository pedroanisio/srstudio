"""Reuse native vector clocks when span-by-span copying would exceed output limits."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, replace

from . import _composition_text as text_assets
from . import composition as c
from . import scene_motion as m
from ._composition_emit import _number, _placement
from ._composition_forms import apply, resolved
from ._composition_paths import expansion_bytes
from ._composition_preflight import _pose


@dataclass(frozen=True)
class Layout:
    shared: frozenset[str]
    runs: tuple[tuple[str, tuple[tuple[int, m.SceneSpan], ...]], ...] = ()


def coalesce(timeline: m.SceneTimeline, base: c.LayerSpec) -> tuple[tuple[int, m.SceneSpan], ...]:
    """Join adjacent vector windows only when their complete emitted state is equal.

    The unchanged source clock stays inside each window. Native animation is
    never sampled or frozen here; only placement and authored form values are.
    """
    result: list[tuple[int, m.SceneSpan]] = []
    previous: object = None
    for index, span in enumerate(timeline.spans):
        if base.id not in span.layers:
            continue
        plan = timeline.samples[span.scene]
        layers = {layer.id: layer for layer in plan.spec.layers}
        layer = layers[base.id]
        signature = (
            layer.temporal,
            layer.space,
            _pose(layer, layers, {}, set()),
            plan.spec.camera,
            resolved(plan, layer, span.start, scene_clock=True),
        )
        if result and result[-1][1].end == span.start and signature == previous:
            first, held = result[-1]
            result[-1] = (first, replace(held, end=span.end))
        else:
            result.append((index, span))
        previous = signature
    return tuple(result)


def select(timeline: m.SceneTimeline, vectors: dict[str, c.PreparedVector], maximum: int) -> Layout | None:
    """Keep existing small output byte-for-byte; otherwise prove a compact layout fits."""
    layers = {layer.id: layer for layer in timeline.base.spec.layers}
    counts = Counter(name for span in timeline.spans for name in span.layers)
    weights = {
        name: len(asset.xml) + 256 * (asset.nodes + 8) + expansion_bytes(asset.binding)
        for name, asset in vectors.items()
    }
    bound = 4096 + sum(
        256 + sum(weights.get(layers[name].asset, 2048) for name in span.layers) for span in timeline.spans
    )

    def fits(value: int) -> bool:
        return value <= maximum and timeline.cost.memory_bytes + 8 * value <= timeline.base.spec.budget.max_memory_bytes

    if fits(bound):
        return None
    shared = frozenset(
        name
        for name, count in counts.items()
        if count > 1
        and layers[name].asset in vectors
        and (count - 1) * weights[layers[name].asset] > count * 2048
        and all(surface.mode == 'ink' and surface.path is None for surface in vectors[layers[name].asset].binding.forms)
    )
    if shared:

        def compact_count(counts: Counter[str]) -> int:
            return (
                4096
                + 256 * (len(layers) + len(timeline.spans))
                + sum(weights[layers[name].asset] for name in shared)
                + sum(
                    count * (2048 if name in shared else weights.get(layers[name].asset, 2048))
                    for name, count in counts.items()
                )
            )

        bound = compact_count(counts)
        if fits(bound):
            return Layout(shared)
        # Keep earlier output identities when either existing layout fits.
        # Otherwise omit repeated vector copies introduced solely by another
        # layer's animation. Raster preparation and references stay unchanged.
        runs = tuple(
            (name, coalesce(timeline, layers[name]))
            for name in counts
            if name not in shared and layers[name].asset in vectors
        )
        reduced = counts.copy()
        reduced.update({name: len(spans) - counts[name] for name, spans in runs})
        bound = compact_count(reduced)
        if fits(bound):
            return Layout(shared, runs)
        # Native ink keeps its complete payload: only local IDs/references and
        # portable resource paths change. Measure those edits once per asset
        # instead of charging 256 extra bytes for every anonymous shape/key.
        # Use the longest possible prefix in this layout, including nonshared
        # placements of the same source. Earlier fitting layouts stay unchanged.
        prefix = f'c{len(layers) - 1}_s{len(timeline.spans) - 1}'
        for name in {layers[layer].asset for layer in shared}:
            asset = vectors[name]
            source = text_assets.portable(ET.fromstring(asset.xml), asset.fonts)
            text_assets.scope(source, prefix)
            weights[name] = len(ET.tostring(source))
        bound = compact_count(reduced)
        if fits(bound):
            return Layout(shared, runs)
    raise c._fail('budget.expansion', bound, 'bounded timeline XML and working storage', 'composition.budget')


def _clock(temporal: c.TemporalPolicy) -> dict[str, str]:
    return {
        'start': _number(temporal.start),
        'end': _number(temporal.end),
        'timeOffset': _number((temporal.start - temporal.source_start) / temporal.rate),
        'timeScale': _number(temporal.rate),
    }


def _content(
    asset: c.PreparedVector,
    prefix: str,
    plan: c.ValidatedScenePlan,
    layer: c.LayerSpec,
    start: float,
    shelf: ET.Element | None,
    paints: ET.Element,
) -> ET.Element:
    source = text_assets.portable(ET.fromstring(asset.xml), asset.fonts)
    apply(source, plan, layer, start, scene_clock=True)
    text_assets.scope(source, prefix)
    resources = source.find('assets')
    if resources is not None and len(resources):
        assert shelf is not None  # The verified asset's fonts allocated this shelf.
        shelf.extend(resources)
    gradients = source.find('paints')
    if gradients is not None:
        paints.extend(gradients)
    original = source.find('composition')
    assert original is not None  # Preparation validated its structure.
    return original


def assemble(
    timeline: m.SceneTimeline,
    vectors: dict[str, c.PreparedVector],
    placements: dict[tuple[int, str, int | None], dict],
    layout: Layout,
    content: ET.Element,
    shelf: ET.Element | None,
    paints: ET.Element,
) -> None:
    # Motion cannot reorder layers: each span is a subsequence of this painter
    # order. Transpose the layout so one layer owns its complete interval.
    shared, runs = layout.shared, dict(layout.runs)
    resolved: dict[int, tuple[dict[str, c.LayerSpec], dict]] = {}

    def at(index: int) -> tuple[dict[str, c.LayerSpec], dict]:
        if index not in resolved:
            layers = {layer.id: layer for layer in timeline.samples[index].spec.layers}
            poses: dict = {}
            for layer in layers.values():
                _pose(layer, layers, poses, set())
            resolved[index] = layers, poses
        return resolved[index]

    for number, base in enumerate(timeline.base.spec.layers):
        spans = runs.get(base.id, tuple((i, span) for i, span in enumerate(timeline.spans) if base.id in span.layers))
        if not spans:
            continue
        prefix = f'c{number}'
        outer = ET.SubElement(content, 'group', {'id': prefix + '_layer'})
        if base.id in shared:
            asset = vectors[base.asset]
            frames = []
            for _, span in spans:
                layers, poses = at(span.scene)
                plan = timeline.samples[span.scene]
                frames.append((span.start, _placement(layers[base.id], plan.spec, poses, asset.binding)))
            moving = ET.SubElement(outer, 'group', {'id': prefix + '_placement', **frames[0][1]})
            for prop in frames[0][1]:
                keys: list[tuple[float, str]] = []
                for time, values in frames:
                    if not keys or values[prop] != keys[-1][1]:
                        keys.append((time, values[prop]))
                if len(keys) > 1:
                    channel = ET.SubElement(
                        moving, 'animate', {'property': prop, 'defaultInterpolation': 'hold', 'timeBase': 'composition'}
                    )
                    for time, value in keys:
                        ET.SubElement(channel, 'key', {'time': _number(time), 'value': value})
            # The transform keys run on the scene clock, outside the unchanged
            # affine source clock; cuts cannot restart native spring history.
            group = ET.SubElement(moving, 'group', {'id': prefix, **_clock(base.temporal)})
            first = spans[0][1]
            group.extend(
                _content(
                    asset,
                    prefix,
                    timeline.samples[first.scene],
                    at(first.scene)[0][base.id],
                    first.start,
                    shelf,
                    paints,
                )
            )
            continue
        for index, span in spans:
            plan = timeline.samples[span.scene]
            layers, poses = at(span.scene)
            layer = layers[base.id]
            scoped = f'{prefix}_s{index}'
            window = ET.SubElement(
                outer, 'group', {'id': scoped + '_window', 'start': _number(span.start), 'end': _number(span.end)}
            )
            raster = next((r for r in span.rasters if r.layer == base.id), None)
            if raster is not None:
                image = placements[span.scene, base.id, raster.frame]
                group = ET.SubElement(
                    window, 'group', {'id': scoped, 'x': _number(image['offset'][0]), 'y': _number(image['offset'][1])}
                )
                ET.SubElement(group, 'layer', {'id': scoped + '__image', 'asset': image['image'], 'x': '0', 'y': '0'})
            else:
                asset = vectors[base.asset]
                group = ET.SubElement(
                    window,
                    'group',
                    {'id': scoped, **_placement(layer, plan.spec, poses, asset.binding), **_clock(layer.temporal)},
                )
                group.extend(_content(asset, scoped, plan, layer, span.start, shelf, paints))
