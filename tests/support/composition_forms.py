"""A lit vector form plan, shared by the form and timeline tests."""

from srstudio import composition as c


def form(*, animated=False):
    keys = (c.FormKey(0, (0, 0, 0), (0, 0, 1)), c.FormKey(0.5, (0, 0, 0), (0, 0, -1))) if animated else ()
    surfaces = (c.FormSurface('face', ('#000000', '#ffffff'), keys=keys),)
    source = c.VectorSource(
        'face',
        b'<scene version="1.1"><project width="64" height="64" fps="4" duration="1"/>'
        b'<composition><shape id="face" shape="rect" x="-10" y="-10" width="20" height="20" '
        b'fill="#ffffff"/></composition></scene>',
    )
    binding = c.AssetBinding(
        'face',
        'candidate.lit-face',
        1,
        'vector',
        c.Bounds((-10, -10, 0), (10, 10, 0)),
        nodes=16,
        memory_bytes=65536,
        duration=1,
        forms=surfaces,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=surfaces)),
    )
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        64,
        64,
        c.FrameRate(4),
        1,
        7,
        'meter',
        c.CameraSpec(origin=(32, 32), scale=1),
        c.LightRig('lit', (c.LightSpec('key', 'directional', '#ffffff', 1, yaw=180),)),
        (c.LayerSpec('face', 'face', 1, c.TemporalPolicy(0, 1)),),
        c.RenderBudget(),
    )
    return c.preflight(spec, (binding,), purpose='candidate-review'), source
