"""A whip pan between two shots built from groups: they leave and arrive fast, paper streaks hide the cut."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, camera, collage, flat_counter
from srstudio.camera import CameraError
from srstudio.canvas import Signature
from srstudio.collage_sketch import EVENTS, StagingError, check_whips, sound_effects
from srstudio.sketch import Beat


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    return Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())


def keyed(cv: Canvas, group: str, prop: str) -> list[tuple[float, float]]:
    """The ``prop`` keys directly on the group with id ``group``."""
    root = ET.fromstring(cv.scene.to_bytes())
    node = next(e for e in root.iter() if e.get("id") == group)
    anim = next(e for e in node if e.tag.endswith("animate") and e.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in anim]


@pytest.fixture
def comp():
    cv = canvas()
    return cv, cv.comp


def test_a_leaving_shot_ends_a_frame_away_and_an_arriving_shot_lands_home(comp):
    cv, parent = comp
    out = cv.group(parent, "out")
    camera.whip(cv, out, 2.0, leaving=True)
    assert keyed(cv, "out", "x") == [(round(2.0 - camera.WHIP, 6), 0.0), (2.0, -1080.0)]
    arrive = cv.group(parent, "in")
    camera.whip(cv, arrive, 2.0, leaving=False)
    assert keyed(cv, "in", "x") == [(2.0, 1080.0), (round(2.0 + camera.WHIP, 6), 0.0)]


def test_a_whip_can_run_the_other_way(comp):
    cv, parent = comp
    out = cv.group(parent, "out")
    camera.whip(cv, out, 2.0, leaving=True, direction=1)
    assert keyed(cv, "out", "x")[-1] == (2.0, 1080.0)


@pytest.mark.parametrize("at", [float("nan"), -1.0, 0.05])
def test_a_whip_needs_time_before_its_cut(comp, at):
    cv, parent = comp
    with pytest.raises(CameraError):
        camera.whip(cv, cv.group(parent, "g"), at, leaving=True)


def test_a_whip_goes_left_or_right(comp):
    cv, parent = comp
    with pytest.raises(CameraError):
        camera.whip(cv, cv.group(parent, "g"), 2.0, leaving=True, direction=0)


def test_the_streaks_cover_the_frame_only_around_the_cut(comp):
    cv, parent = comp
    g = camera.whip_streaks(cv, parent, 2.0, ("#112233", "#445566"), seed=3)
    xml = cv.scene.to_bytes(layout="pretty").decode()
    assert xml.count("#112233") + xml.count("#445566") == camera.WHIP_BANDS
    assert keyed(cv, g.id, "opacity") == [
        (round(2.0 - camera.WHIP, 6), 0.0),
        (2.0, 1.0),
        (round(2.0 + camera.WHIP, 6), 0.0),
    ]


def test_the_streaks_need_a_colour(comp):
    cv, parent = comp
    with pytest.raises(CameraError):
        camera.whip_streaks(cv, parent, 2.0, ())


def _beat(start: float, event: str, who: str = "gary") -> Beat:
    return Beat(start, who, "", "open", "flat", "hold", None, None, event, ())


def test_a_whip_beat_is_known_and_sounds_a_whoosh(tmp_path):
    assert "whip" in EVENTS
    effects = sound_effects([_beat(0.0, ""), _beat(1.0, "whip")], 4.0, tmp_path, 7)
    assert [e["id"] for e in effects] == ["whoosh"]


def test_a_shot_that_whips_in_and_out_is_refused():
    beats = [_beat(0.0, ""), _beat(1.0, "whip", "rosa"), _beat(2.0, "whip", "gary")]
    with pytest.raises(StagingError, match="whips in and out"):
        check_whips(beats, 4.0, "x")
    check_whips(beats[:2], 4.0, "x")
