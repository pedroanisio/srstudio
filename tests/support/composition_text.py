"""A pinned-font native caption plan, shared by the text and timeline tests."""

import hashlib
import xml.etree.ElementTree as ET

from sr_core.scene import Scene

from srstudio import Canvas, fonts, sample
from srstudio import composition as c


def caption():
    data = next(p for p in sample.SYSTEM_FONTS if p.exists()).read_bytes()
    facts = fonts.inspect_ttf(data)
    font = c.VectorFont('font', data, sample.dejavu_license())
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='2', duration=2, fontPolicy='pinned')
    cv = Canvas(scene, font_asset='font', width=320, height=240)
    cv.assets.add_font(
        id='font',
        src='original.ttf',
        family=facts.family,
        weight=str(facts.weight),
        sha256=hashlib.sha256(data).hexdigest(),
        license='LICENSE.txt',
    )
    cv.text(cv.comp, 'caption', 'Hold on. Café!', 10, 20, 300, 60, 24, color='#ffffff')
    root = ET.fromstring(scene.to_bytes())
    root.find('assets/text').set('overflow', 'clip')
    source = c.VectorSource('info', ET.tostring(root), (font,))
    binding = c.AssetBinding(
        'info',
        'candidate.info',
        1,
        'vector',
        c.Bounds((10, 20, 0), (310, 80, 0)),
        nodes=20,
        memory_bytes=16 * (len(data) + len(source.xml)),
        duration=2,
        candidate=c.CandidateSource('cutout', c.vector_source_digest(source)),
    )
    spec = c.ScenePlan(
        c.StylePin('cutout', c.style_revision('cutout')),
        320,
        240,
        c.FrameRate(2),
        2,
        7,
        'meter',
        c.CameraSpec(scale=1),
        c.LightRig('flat'),
        (c.LayerSpec('info', 'info', 1, c.TemporalPolicy(0, 2), space='screen'),),
        c.RenderBudget(),
    )
    return c.preflight(spec, (binding,), purpose='candidate-review'), source
