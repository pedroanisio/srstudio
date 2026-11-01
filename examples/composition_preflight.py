"""Inspect a real approved drawing's declared composition manifest without rendering."""

from __future__ import annotations

import json
from dataclasses import asdict

from sr_core.scene import Scene

from srstudio import Canvas, parts
from srstudio.composition import (
    Anchor,
    AssetBinding,
    Bounds,
    CameraSpec,
    FrameRate,
    LayerSpec,
    LightRig,
    RenderBudget,
    ScenePlan,
    StylePin,
    TemporalPolicy,
    Transform,
    ValidatedScenePlan,
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


if __name__ == '__main__':
    plan, _ = build_manifest()
    print(json.dumps({'digest': plan.digest, 'cost': asdict(plan.cost)}, indent=2))
