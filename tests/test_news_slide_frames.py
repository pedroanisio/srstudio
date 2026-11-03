"""A News graphic that slides in arrives on the frame its time names (ADR 0223).

The kit adds its slide to a beat: 10.8 + 0.3 is 11.100000000000001 in floats, a hair after frame 333 at 30 fps, and
the engine showed the words on frame 334. On a ``held_frames`` canvas the sum within float noise of a frame is that
frame's own time; a reel already built keeps the sum it was given.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, flat_counter, held_gate, news_inked, news_kit
from support.news_contracts import measure


def _canvas(held_frames: bool) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=14, background=news_kit.PLUM_DEEP)
    return Canvas(
        scene, news_kit.NEWS.palette(), font_asset="barlow-condensed", namer=flat_counter("n"), held_frames=held_frames
    )


def _starts(cv: Canvas) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [g.get("start") for g in root.iter("group") if g.get("start") is not None]


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: news_inked.lower_third(cv, cv.comp, "DEVELOPING", "A plain headline", 10.8, 13.0, measure),
        lambda cv: news_inked.banner(cv, cv.comp, 10.8, 13.0, measure),
    ],
    ids=["lower-third", "banner"],
)
def test_a_graphic_arrives_on_the_frame_its_time_names(draw):
    cv = _canvas(held_frames=True)
    draw(cv)
    assert "11.1" in _starts(cv)
    assert not any(s.startswith("11.10000000") for s in _starts(cv))
    assert held_gate.late_changes(cv.scene.to_bytes()) == []


def test_a_sum_off_the_frames_is_left_as_it_is():
    """8.41 + 0.3 lands 0.3 of a frame after frame 261: after it, not on it, and the sum stays."""
    cv = _canvas(held_frames=True)
    news_inked.banner(cv, cv.comp, 8.41, 13.0, measure)
    assert repr(8.41 + news_kit.SLIDE) in _starts(cv)


def test_a_reel_already_built_keeps_its_arrival():
    cv = _canvas(held_frames=False)
    news_inked.banner(cv, cv.comp, 10.8, 13.0, measure)
    assert repr(10.8 + news_kit.SLIDE) in _starts(cv)
    assert held_gate.late_changes(cv.scene.to_bytes()) != []
