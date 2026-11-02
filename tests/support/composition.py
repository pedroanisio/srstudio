"""A real pinned paper drawing for composition payload and emission tests."""

import sys
from dataclasses import replace

import numpy as np
from sr_core.scene import Scene

from srstudio import Canvas, clay, parts, plates, proxy
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


def mesh():
    """A one-quad textured mesh named for the plate material ``skin``, with UVs on its corners."""
    return clay.Mesh(
        'skin',
        np.array([[-0.25, -0.25, 0], [0.25, -0.25, 0], [0.25, 0.25, 0], [-0.25, 0.25, 0]]),
        np.tile([0.0, 0.0, -1.0], (4, 1)),
        np.array([[0, 2, 1], [0, 3, 2]]),
        np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]),
    )


def mixed():
    """A plan with one prepared plate under one screen-space vector mark, and both prepared inputs."""
    item = plate_source()
    base = prepared_plate_plan(item)
    scene = Scene(version='auto')
    scene.add_project(width=64, height=64, fps='24', duration=1)
    canvas = Canvas(scene, font_asset=None, width=64, height=64)
    canvas.rect(canvas.comp, 0, 0, 8, 8, '#FF0000')
    xml = scene.to_bytes()
    mark = c.AssetBinding('mark', 'rafa', 1, 'vector', c.Bounds((0, 0, 0), (8, 8, 0)), nodes=16, memory_bytes=16384)
    layer = c.LayerSpec(
        'mark', 'mark', 1, c.TemporalPolicy(0, 1), role='information', space='screen', transform=c.Transform((3, 4, 0))
    )
    plan = c.preflight(replace(base.spec, layers=base.spec.layers + (layer,)), base.bindings + (mark,))
    return plan, (c.prepare_plate(plan, 'host', item), c.VectorSource('mark', xml))


def renderer(tmp_path, body=None):
    """A stand-in engine that copies a blue 64 px PNG to its --output, or runs ``body`` instead."""
    fixture = tmp_path / 'fixture.png'
    plates.write_png(fixture, np.full((64, 64, 4), (0, 0, 255, 255), dtype=np.uint8))
    engine = tmp_path / 'engine'
    engine.write_text(
        f'#!{sys.executable}\n'
        + (
            body
            or f'''import sys
from pathlib import Path
assert Path(sys.argv[2]).is_file()
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(Path({str(fixture)!r}).read_bytes())
'''
        )
    )
    engine.chmod(0o700)
    return engine


PROXY_TONES = ('#102030', '#506070', '#90A0B0', '#D0E0F0')


def proxy_source(*, under=False, oversample=2):
    """A two-box clay model as a proxy source: the body behind, the seat under when ``under``."""
    model = clay.Model()
    model.box('body', (0, 0, 0), (0.2, 0.2, 0.2))
    model.box('seat', (0.15, 0, 0.15), (0.1, 0.1, 0.1))
    recipe = proxy.Recipe(
        {'body': PROXY_TONES, 'seat': PROXY_TONES},
        behind=frozenset({'body'}),
        under=frozenset({'seat'}) if under else frozenset(),
        oversample=oversample,
    )
    return c.proxy_source('host', tuple(model.meshes()), recipe, basis='clay', lighting='scene')
