"""A real pinned paper drawing for composition payload and emission tests."""

from dataclasses import replace

from sr_core.scene import Scene

from srstudio import Canvas, clay, parts
from srstudio import composition as c


def paper(*, animated=False):
    source = Scene(version='auto')
    source.add_project(width=320, height=240, fps='24', duration=2, seed=17)
    cv = Canvas(source, font_asset=None, width=320, height=240)
    group = cv.group(cv.comp, 'motion')
    parts.drawing('papers', 1)(cv, group, x=0, y=0, scale=1, angle=0, seed=3)
    if animated:
        cv.keys(group, 'x', [(0, 0), (2, 40)], hold=False, local=True)
    xml = source.to_bytes()
    binding = c.AssetBinding(
        'paper-source',
        'papers',
        1,
        'vector',
        c.Bounds((-20, -20, 0), (340, 170, 0)),
        nodes=sum(1 for _ in source.iter()),
        memory_bytes=len(xml) * 16,
        duration=2 if animated else None,
    )
    spec = c.ScenePlan(
        c.StylePin('cutout', c.style_revision('cutout')),
        320,
        240,
        c.FrameRate(),
        2,
        17,
        'meter',
        c.CameraSpec(origin=(20, 30), scale=1),
        c.LightRig('flat'),
        (c.LayerSpec('paper', binding.id, 1, c.TemporalPolicy(0, 2)),),
        c.RenderBudget(),
    )
    return spec, binding, xml


def window(spec):
    return replace(spec, layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0.5, 1.5, 0.25, 1.5)),))


def plate_plan(**changes):
    binding = c.AssetBinding(
        'host',
        'rafa',
        1,
        'plates',
        c.Bounds((-1, -1, -1), (1, 1, 1)),
        plates=(c.PlateWork('a' * 64, 64, 64, 48, 4, 1, 1024**2),),
    )
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(),
        1,
        7,
        'meter',
        c.CameraSpec('perspective', (0, 0, 10), (0, 0, 0), (32, 32), 100, 10),
        c.LightRig('lit', (c.LightSpec('ambient', 'ambient', '#FFFFFF', 1),)),
        (c.LayerSpec('host', 'host', 1, c.TemporalPolicy(0, 1)),),
        c.RenderBudget(),
    )
    return c.preflight(replace(spec, **changes), (binding,))


def plate_source():
    model = clay.Model()
    model.box('skin', (0, 0, 0.2), (0.2, 0.2, 0.2))
    return c.PlateSource(
        'host', (c.plate_mesh(model.meshes()[0], basis='clay'),), (c.PlateMaterial('skin', '#C88762'),)
    )


def prepared_plate_plan(item):
    base = plate_plan()
    binding = replace(
        base.bindings[0],
        nodes=64,
        memory_bytes=1024**2,
        plates=(replace(base.bindings[0].plates[0], key=c.plate_source_digest(item)),),
    )
    return c.preflight(base.spec, (binding,))
