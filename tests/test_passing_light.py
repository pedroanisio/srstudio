"""Light from outside going past: each band lives for its crossing, crosses the whole frame, screens what is under it,
and what cannot be drawn is refused."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, passing_light
from srstudio.canvas import CanvasError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def doc(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def bands_of(cv: Canvas) -> list[ET.Element]:
    return [g for g in doc(cv).iter("group") if g.get("blend") == "screen"]


def drawn(times=(1.0, 4.0), **kw) -> Canvas:
    cv = canvas()
    root = cv.group(cv.comp, "root")
    passing_light.bands(cv, root, times, **kw)
    return cv


def test_a_band_lives_for_its_crossing_and_no_longer():
    a, b = bands_of(drawn((1.0, 4.0), crossing=0.8))
    assert (float(a.get("start")), float(a.get("end"))) == (1.0, 1.8)
    assert (float(b.get("start")), float(b.get("end"))) == (4.0, 4.8)


def test_a_band_crosses_the_whole_frame_on_the_project_clock():
    band = bands_of(drawn((1.0,), crossing=0.8))[0]
    moves = [a for a in band.iter("animate") if a.get("property") == "x"]
    assert len(moves) == 1
    keys = [(float(k.get("time")), float(k.get("value"))) for k in moves[0].iter("key")]
    assert (keys[0][0], keys[-1][0]) == (1.0, 1.8)
    assert keys[0][1] < 0 and keys[-1][1] > 1080


def test_the_other_way_runs_backwards():
    band = bands_of(drawn((1.0,), leftward=True))[0]
    keys = [float(k.get("value")) for a in band.iter("animate") if a.get("property") == "x" for k in a.iter("key")]
    assert keys[0] > 1080 and keys[-1] < 0


def test_the_band_is_soft_at_both_edges():
    text = ET.tostring(doc(drawn((1.0,)))).decode()
    assert "passing-light" in text
    paints = [p for p in doc(drawn((1.0,))).iter("linearGradient")]
    stops = [s.get("color") for s in paints[0].iter("stop")]
    assert stops[0] == stops[-1] == "#000000"  # black adds nothing under a screen


def test_no_band_is_nothing():
    assert bands_of(drawn(())) == []


@pytest.mark.parametrize(
    ("times", "kw"),
    [
        ((-1.0,), {}),
        ((2.0, 1.0), {}),
        ((1.0, 1.5), {"crossing": 0.8}),
        ((1.0,), {"crossing": 0.0}),
        ((1.0,), {"opacity": 0.0}),
        ((1.0,), {"opacity": 1.5}),
        ((1.0,), {"width": 0.0}),
        ((1.0,), {"colour": "amber"}),
        (("soon",), {}),
    ],
)
def test_what_cannot_be_drawn_is_refused(times, kw):
    with pytest.raises(CanvasError):
        drawn(times, **kw)


def test_the_shade_multiplies_the_whole_frame():
    cv = canvas()
    root = cv.group(cv.comp, "root")
    passing_light.shade(cv, root, "#55638f", 0.7)
    group = next(g for g in doc(cv).iter("group") if g.get("blend") == "multiply")
    assert float(group.get("opacity")) == 0.7


@pytest.mark.parametrize(("colour", "opacity"), [("navy", 0.5), ("#55638f", 0.0)])
def test_a_shade_it_cannot_draw_is_refused(colour, opacity):
    cv = canvas()
    with pytest.raises(CanvasError):
        passing_light.shade(cv, cv.group(cv.comp, "root"), colour, opacity)


def test_two_shots_can_each_draw_their_own():
    cv = canvas()
    root = cv.group(cv.comp, "root")
    for start in (1.0, 5.0):
        passing_light.shade(cv, root, "#55638f", 0.7)
        passing_light.bands(cv, root, (start,))
    ids = [g.get("id") for g in doc(cv).iter("group") if g.get("blend")]
    assert len(ids) == len(set(ids)) == 4
