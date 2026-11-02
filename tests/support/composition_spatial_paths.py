"""A spatial vector path plan, shared by the spatial path and timeline tests."""

from srstudio import composition as c

POINTS = ((-1.0, -1.0, 0.0), (1.0, -1.0, 1.0), (1.0, 1.0, 1.0), (-1.0, 1.0, 0.0))


def fixture(*, keys=(), closed=True):
    path = c.FormPath(POINTS, keys=keys, closed=closed)
    forms = (c.FormSurface('surface', ('#000000', '#ffffff'), path=path),)
    source = c.VectorSource(
        'shape',
        b'<scene version="1.1"><project width="64" height="64" fps="4" duration="1"/>'
        b'<composition><shape id="surface" shape="path" path="M -1 -1 L 1 -1 L 1 1 L -1 1 Z" '
        b'width="64" height="64" fill="#ffffff" stroke="#000000" strokeWidth="2"/></composition></scene>',
    )
    binding = c.AssetBinding(
        'shape',
        'candidate.spatial-path',
        1,
        'vector',
        c.Bounds((-2, -2, -2), (2, 2, 2)),
        nodes=10,
        memory_bytes=65536,
        duration=1,
        forms=forms,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
    )
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(4),
        1,
        7,
        'meter',
        c.CameraSpec('perspective', (5, 2, 10), (0, 0, 0), (32, 32), 20, 10),
        c.LightRig('lit', (c.LightSpec('fill', 'ambient', '#ffffff', 1),)),
        (c.LayerSpec('shape', 'shape', 1, c.TemporalPolicy(0, 1)),),
        c.RenderBudget(),
    )
    return spec, binding, source
