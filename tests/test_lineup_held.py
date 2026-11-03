"""A group held for an opening does not move, and it needs its opener in the lineup."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, flat_counter, sketch
from srstudio.canvas import Signature
from srstudio.collage_group import GroupError, Lineup, Place


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    cv.font_asset = "font"
    return cv


def test_a_held_group_keys_nothing():
    cv = canvas()
    pose = ({"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "down"},)
    lineup = Lineup(
        {"brent": Place(285.0, 1565.0, 0.72), "deb": Place(800.0, 1565.0, 0.72)},
        {"brent": pose, "deb": pose},
        spans=((0.0, 0.45),),
    )
    beats = [sketch.Beat(0.0, "brent", "", "open", "flat", "down", None, None, "", ())]
    face = lineup.held(cv, cv.comp, sketch.appearances(beats, 0.45)[0], {})
    assert face[0] == pytest.approx(285.0)
    assert b"animate" not in cv.scene.to_bytes()


def test_a_held_group_needs_its_opener_in_the_lineup():
    cv = canvas()
    pose = ({"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "down"},)
    lineup = Lineup({"deb": Place(800.0, 1565.0, 0.72)}, {"deb": pose}, spans=((0.0, 0.45),))
    beats = [sketch.Beat(0.0, "brent", "", "open", "flat", "down", None, None, "", ())]
    with pytest.raises(GroupError):
        lineup.held(cv, cv.comp, sketch.appearances(beats, 0.45)[0], {})
