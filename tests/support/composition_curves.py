"""The hybrid figure's actual native source, shared by the curve and timeline tests."""

import hashlib

from srstudio import composition as c


def figure_source(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[2]))
    from examples.drawing_proof import figure_performance
    from sr_core.scene import Scene

    from srstudio import Canvas

    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=6)
    cv = Canvas(scene, font_asset=None)
    figure_performance().window(0, 6).place(cv, cv.comp, id='figure')
    xml = scene.to_bytes()
    binding = c.AssetBinding(
        'figure',
        'candidate.hybrid-figure',
        1,
        'vector',
        c.Bounds((-10000, -10000, 0), (10000, 10000, 0)),
        duration=6,
        nodes=3000,
        memory_bytes=64 * 1024**2,
        candidate=c.CandidateSource('toon', hashlib.sha256(xml).hexdigest()),
    )
    return binding, xml
