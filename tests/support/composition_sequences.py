"""Raster sequences and their plans, shared by the sequence tests and the timeline tests."""

from dataclasses import replace

from srstudio import composition as c
from support.composition import plate_plan, plate_source, proxy_source


def sequence(backend='plates'):
    first = plate_source() if backend == 'plates' else proxy_source(oversample=1)
    if backend == 'plates':
        second = replace(first, materials=(replace(first.materials[0], color='#00AAFF'),))
    else:
        second = replace(first, recipe=replace(first.recipe, grain_seed=25))
    return c.RasterSequence('host', 2, (c.RasterFrame(0, first), c.RasterFrame(0.5, second), c.RasterFrame(1.5, first)))


def plan_for(source):
    base = plate_plan()
    backend = 'plates' if isinstance(source.frames[0].source, c.PlateSource) else 'proxy'
    binding = replace(
        base.bindings[0],
        backend=backend,
        duration=2,
        nodes=512,
        memory_bytes=64 * 1024**2,
        plates=c.raster_jobs(source, width=64, height=64, memory_bytes=8 * 1024**2),
    )
    spec = replace(base.spec, duration=2, layers=(replace(base.spec.layers[0], temporal=c.TemporalPolicy(0, 2)),))
    return c.preflight(spec, (binding,))


def engine_nodes(engine, path, time):
    import json

    from srstudio._bounded_process import ProcessLimits, run

    result = run(
        (str(engine.resolve()), 'eval', str(path.resolve()), '--time', str(time), '--json'),
        input=b'',
        limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536),
    )
    return [
        node
        for node in json.loads(result.stdout)['result']['nodes']
        if node['kind'] == 'layer' and node['draw'] and node['world_opacity'] > 0
    ]
