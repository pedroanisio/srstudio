"""Native candidate information and project background in the shared proof.

Text geometry and colors retain the legacy candidate's layout. That candidate
has no drawing approval: exact preservation does not confer style adoption.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace

from examples.drawing_hand import hand_scene
from examples.drawing_proof import DURATION, SIZE, schedule
from examples.drawing_world import WorldStudy
from sr_core.scene import Scene

from srstudio import Canvas, fonts, sample
from srstudio import composition as c
from srstudio import scene_motion as m


def information_source(*, size: tuple[int, int] = SIZE) -> tuple[c.AssetBinding, c.VectorSource]:
    """Pin font bytes and license with the native title, subtitle and caption pill."""
    schedule(fps=1, size=size)
    path = next((p for p in sample.SYSTEM_FONTS if p.is_file()), None)
    if path is None:
        raise FileNotFoundError('DejaVu Sans Bold is required')
    data = path.read_bytes()
    facts = fonts.inspect_ttf(data)
    font = c.VectorFont('font', data, sample.dejavu_license())
    scene = Scene(version='auto')
    scene.add_project(width=size[0], height=size[1], fps='24', duration=DURATION, fontPolicy='pinned')
    cv = Canvas(scene, width=size[0], height=size[1], font_asset='font', local_time=True)
    cv.assets.add_font(
        id='font',
        src='font.ttf',
        family=facts.family,
        weight=str(facts.weight),
        sha256=hashlib.sha256(data).hexdigest(),
        license='LICENSE.txt',
    )
    group = cv.group(cv.comp, 'information', scaleX=size[0] / SIZE[0], scaleY=size[1] / SIZE[1])
    cv.text(group, 'title', 'A SHARED VIEW', 80, 100, 920, 100, 62, color='#26303a')
    cv.text(group, 'subtitle', 'One car. One hand. One continuing moment.', 80, 220, 920, 100, 30, color='#4a5666')
    cv.rect(group, 80, 1680, 920, 130, '#26303a', radius=32)
    cv.text(group, 'caption', 'Keep hold. The camera can move.', 110, 1712, 860, 80, 36, color='#ffffff')
    root = ET.fromstring(scene.to_bytes())
    for text in root.findall('assets/text'):
        text.set('overflow', 'clip')
    source = c.VectorSource('information', ET.tostring(root), (font,))
    binding = c.AssetBinding(
        'information',
        'candidate.hybrid-information',
        1,
        'vector',
        c.Bounds((0, 0, 0), (*size, 0)),
        nodes=sum(1 for _ in root.iter()),
        memory_bytes=16 * (len(data) + len(source.xml)),
        duration=DURATION,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source)),
    )
    return binding, source


def complete_scene(*, fps: int = 12, size: tuple[int, int] = SIZE) -> WorldStudy:
    """Compose all candidate picture layers and native protected information."""
    world = hand_scene(fps=fps, size=size)
    timeline = world.timeline
    info, info_xml = information_source(size=size)
    clock = c.TemporalPolicy(0, DURATION)
    spec = replace(
        timeline.base.spec,
        background='#efe8df',
        layers=(
            *timeline.base.spec.layers,
            c.LayerSpec('information', 'information', 1, clock, space='screen', role='information'),
        ),
    )
    return WorldStudy(
        m.plan_scene(
            spec,
            (*timeline.base.bindings, info),
            timeline.motion,
            rasters=timeline.rasters,
            purpose=timeline.base.purpose,
        ),
        (*world.vectors, info_xml),
    )
