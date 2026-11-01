"""Two characters in one Toon shot: each acts on the sketch's beats, moves its head, keeps its own lips, and a beat
left without an act is refused by name."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon_pair
from srstudio.sketch import Beat
from srstudio.toon import ToonDataError, fx, fy
from srstudio.toon_pair import Act
from srstudio.toon_sketch import SEAT, Shot


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


BEATS = (
    Beat(0.0, "hamster", "", "half", "flat", "desk"),
    Beat(2.0, "hamster", "", "half", "flat", "desk"),
    Beat(4.0, "hamster", "", "half", "flat", "desk"),
    Beat(6.0, "fox", "", "half", "flat", "desk"),
)


def shot(start: float = 0.0, end: float = 6.0, mouths=None) -> Shot:
    cv = canvas()
    root = cv.group(cv.comp, "root")
    app = sketch.Appearance("hamster", start, end, [{"start": 0.0, "eyes": "half", "mouth": "flat", "arms": "desk"}])
    return Shot(cv, app, root, root, BEATS, 8.0, lambda *a, **k: 0.0, None, {}, mouths or {})


def groups(s: Shot) -> int:
    return sum(1 for _ in ET.fromstring(s.cv.scene.to_bytes(layout="pretty")).iter("group"))


ACTS = (
    Act("half", "flat", "desk"),
    Act("wide", "flat", "desk"),
    Act("wide", "flat", "desk"),
    Act("side", "flat", "sigh"),
)


def test_poses_start_at_the_shot_and_merge_what_does_not_change() -> None:
    assert toon_pair.poses_of(BEATS, ACTS, 0.0, 6.0) == [
        {"start": 0.0, "eyes": "half", "mouth": "flat", "arms": "desk"},
        {"start": 2.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
    ]


def test_a_shot_that_starts_late_enters_on_the_act_it_cuts_into() -> None:
    assert toon_pair.poses_of(BEATS, ACTS, 3.0, 8.0) == [
        {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
        {"start": 3.0, "eyes": "side", "mouth": "flat", "arms": "sigh"},
    ]


def test_wear_stays_with_the_act() -> None:
    worn = (Act("half", "flat", "desk", ("sweat",)),) * 4
    assert toon_pair.poses_of(BEATS, worn, 0.0, 6.0)[0]["wear"] == ["sweat"]


def test_a_beat_without_an_act_is_refused() -> None:
    with pytest.raises(ToonDataError, match="4 beats, 3 acts"):
        toon_pair.poses_of(BEATS, ACTS[:3], 0.0, 6.0)


def test_a_second_character_stands_at_its_seat_with_its_lips_and_its_head() -> None:
    track = [(0.1, "open"), (0.4, "closed")]
    s = shot(mouths={"rabbit": track})
    g = toon_pair.figure(s, s.back, "rabbit", (150.0, 840.0), ACTS, scale=0.7)
    assert (g.x, g.y) == (fx(150.0), fy(840.0))
    assert (g.anchorX, g.anchorY) == (fx(SEAT[0]), fy(SEAT[1]))
    assert (g.scaleX, g.scaleY) == (0.7, 0.7)
    still = shot(mouths={"rabbit": track})
    toon_pair.figure(still, still.back, "rabbit", (150.0, 840.0), ACTS, scale=0.7, moving=False)
    assert groups(s) > groups(still), "the moving head adds its rig's chain of groups"


def test_a_mirrored_character_faces_the_other_way_at_the_same_size() -> None:
    s = shot()
    g = toon_pair.figure(s, s.back, "bear", (420.0, 840.0), ACTS, scale=0.7, mirror=True)
    assert (g.scaleX, g.scaleY) == (-0.7, 0.7)


def test_a_character_with_no_head_rig_can_stay_still() -> None:
    s = shot()
    toon_pair.figure(s, s.back, "cat", (420.0, 840.0), ACTS, moving=False)
    with pytest.raises(ToonDataError, match="no head rig"):
        toon_pair.figure(s, s.back, "cat", (420.0, 840.0), ACTS)


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan")])
def test_a_scale_is_positive(scale: float) -> None:
    s = shot()
    with pytest.raises(ToonDataError, match="scale"):
        toon_pair.figure(s, s.back, "bear", (420.0, 840.0), ACTS, scale=scale)
