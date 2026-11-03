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


@pytest.mark.parametrize(
    ("eyes", "mouth", "arms", "wear", "word"),
    [
        ("wide", "smile", "desk", (), "mouth"),  # grown-on-me's typo, which reached the build before
        ("glare", "flat", "desk", (), "eyes"),
        ("wide", "flat", "wave", (), "arms"),
        ("wide", "flat", "desk", ("hat",), "wear"),
        ("", "flat", "desk", (), "eyes"),
        (None, "flat", "desk", (), "eyes"),
    ],
)
def test_an_act_names_only_expressions_the_rigs_have(eyes, mouth, arms, wear, word) -> None:
    with pytest.raises(ToonDataError, match=word):
        Act(eyes, mouth, arms, wear)


def test_an_act_keeps_every_expression_the_rigs_have() -> None:
    from srstudio import toon

    for eyes in toon.EYES:
        assert Act(eyes, "flat", "desk").eyes == eyes
    for mouth in toon.MOUTHS:
        assert Act("wide", mouth, "desk").mouth == mouth
    for arms in toon.ARMS:
        assert Act("wide", "flat", arms).arms == arms
    assert Act("wide", "flat", "desk", toon.WEAR).wear == toon.WEAR


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


def test_a_shoulder_follows_the_placement_and_the_mirror() -> None:
    assert toon_pair.shoulder((430.0, 876.0), 0.72) == pytest.approx((355.84, 783.84))
    assert toon_pair.shoulder((430.0, 876.0), 0.72, side="right") == pytest.approx((532.96, 783.84))
    assert toon_pair.shoulder((430.0, 876.0), 0.72, mirror=True) == pytest.approx((532.96 - 28.8, 783.84))


def test_a_shoulder_is_left_or_right() -> None:
    with pytest.raises(ToonDataError, match="left or right"):
        toon_pair.shoulder((0.0, 0.0), 1.0, side="middle")


def test_a_reach_runs_from_the_shoulder_to_the_target() -> None:
    root = toon_pair.shoulder((430.0, 876.0), 0.72)
    degrees, length = toon_pair.aim(root, (root[0] - 100.0, root[1] - 100.0))
    assert degrees == pytest.approx(225.0)
    assert length == pytest.approx(141.42, abs=0.01)


def test_reach_draws_an_arm_rooted_on_the_figure_and_landing_at_its_second() -> None:
    cv = canvas()
    at, target = (430.0, 876.0), (300.0, 700.0)
    arm = toon_pair.reach(cv, cv.comp, at, target, "#efe8ee", 2.0, 3.0, scale=0.72)
    root = toon_pair.shoulder(at, 0.72)
    assert (arm.x, arm.y) == (fx(root[0]), fy(root[1]))
    assert (arm.start, arm.end) == (2.0, 3.0)
    assert b"rotation" in cv.scene.to_bytes(layout="pretty")


def test_reach_refuses_a_target_at_the_shoulder_and_a_target_too_far() -> None:
    cv = canvas()
    at = (430.0, 876.0)
    with pytest.raises(ToonDataError, match="too close"):
        toon_pair.reach(cv, cv.comp, at, toon_pair.shoulder(at, 0.72), "#efe8ee", 2.0, 3.0, scale=0.72)
    with pytest.raises(ToonDataError, match="too far"):
        toon_pair.reach(cv, cv.comp, at, (-400.0, 100.0), "#efe8ee", 2.0, 3.0, scale=0.72)


def test_reach_refuses_a_span_with_no_time_to_land() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="land"):
        toon_pair.reach(cv, cv.comp, (430.0, 876.0), (300.0, 700.0), "#efe8ee", 2.0, 2.05, scale=0.72)
