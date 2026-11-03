"""Inspect, verify and optionally emit a real approved drawing without rendering."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, parts
from srstudio.composition import (
    Anchor,
    AssetBinding,
    Bounds,
    CameraSpec,
    CompiledScene,
    FrameRate,
    LayerSpec,
    LightRig,
    RenderBudget,
    ScenePlan,
    StylePin,
    TemporalPolicy,
    Transform,
    ValidatedScenePlan,
    VectorSource,
    compile_scene,
    emit_scene,
    preflight,
    style_revision,
)


def build_manifest() -> tuple[ValidatedScenePlan, bytes]:
    # Asset preparation is separate from read-only manifest preflight. This is a
    # pinned vector drawing with no external resources or renderer calls.
    source = Scene(version='auto')
    source.add_project(width=640, height=360, fps='24', duration=1, seed=17)
    canvas = Canvas(source, font_asset=None, width=640, height=360)
    parts.drawing('papers', 1)(canvas, canvas.comp, x=0, y=0, scale=1, angle=0, seed=3)
    errors = source.check(schema=True)
    if errors:
        raise ValueError(f'paper source is invalid: {errors}')
    xml = source.to_bytes()
    asset = AssetBinding(
        'paper-source',
        'papers',
        1,
        'vector',
        # Authored bounds for this exact preparation, including the strokes.
        Bounds((-16, -8, 0), (291, 155, 0)),
        anchors=(Anchor('drawing-origin', (0, 0, 0)),),
        nodes=sum(1 for _ in source.iter()),
        memory_bytes=len(xml) * 8,
    )
    spec = ScenePlan(
        style=StylePin('cutout', style_revision('cutout')),
        width=640,
        height=360,
        fps=FrameRate(24, 1),
        duration=1,
        seed=17,
        world_unit='meter',
        camera=CameraSpec(origin=(320, 180), scale=1000),
        lights=LightRig('flat'),
        layers=(
            LayerSpec(
                'paper',
                asset.id,
                1,
                TemporalPolicy(0, 1),
                transform=Transform(translation=(-0.15, -0.08, 0), scale=0.001),
            ),
        ),
        budget=RenderBudget(),
    )
    return preflight(spec, (asset,)), xml


def build_scene() -> CompiledScene:
    plan, xml = build_manifest()
    return compile_scene(plan, (VectorSource(plan.bindings[0].id, xml),))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Atomically write a self-contained scene XML file.')
    parser.add_argument('--overwrite', action='store_true', help='Replace an existing output atomically.')
    args = parser.parse_args()
    plan, xml = build_manifest()
    assets = (VectorSource(plan.bindings[0].id, xml),)
    compiled = (
        emit_scene(plan, assets, args.output, overwrite=args.overwrite) if args.output else compile_scene(plan, assets)
    )
    print(
        json.dumps(
            {
                'manifest_digest': plan.digest,
                'scene_digest': compiled.digest,
                'actual_nodes': compiled.nodes,
                'declared_cost': asdict(plan.cost),
            },
            indent=2,
        )
    )
