"""An arm that follows a hand, and the café actors' arms a reel can take over."""

import math
import xml.etree.ElementTree as ET

import pytest

from srstudio import cast
from srstudio.cast import CastError
from srstudio.cutout_reach import ReachError, hand_at, reach
from srstudio.rig import Performance
from support.tip_tablet import canvas

TRACK = [(0.0, 300.0, 700.0), (1.0, 700.0, 900.0), (2.0, 200.0, 900.0)]


def scene(cv) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def keyed(root, id: str, prop: str) -> dict[float, float]:
    node = next(e for e in root.iter() if e.get("id") == id)
    track = next(e for e in node.iter() if e.get("property") == prop)
    return {float(k.get("time")): float(k.get("value")) for k in track}


def test_the_hand_holds_at_each_end_and_passes_its_points():
    assert hand_at(TRACK, -1) == (300.0, 700.0)
    assert hand_at(TRACK, 1.0) == (700.0, 900.0)
    assert hand_at(TRACK, 9) == (200.0, 900.0)
    assert hand_at(TRACK, 0.5) == pytest.approx((500.0, 800.0))


def test_the_arm_always_ends_on_the_hand():
    cv = canvas()
    reach(cv, cv.comp, "arm", (100.0, 600.0), TRACK)
    root = scene(cv)
    rotation, length = keyed(root, "arm", "rotation"), keyed(root, "arm", "scaleX")
    x, y = keyed(root, "arm-hand", "x"), keyed(root, "arm-hand", "y")
    assert len(rotation) >= 60
    for t in rotation:
        tip = 100.0 * length[t]
        assert 100.0 + tip * math.cos(math.radians(rotation[t])) == pytest.approx(x[t], abs=0.01)
        assert 600.0 + tip * math.sin(math.radians(rotation[t])) == pytest.approx(y[t], abs=0.01)


def test_an_arm_crossing_straight_left_turns_the_short_way():
    cv = canvas()
    reach(cv, cv.comp, "arm", (500.0, 500.0), [(0.0, 100.0, 530.0), (1.0, 100.0, 470.0)])
    angles = list(keyed(scene(cv), "arm", "rotation").values())
    assert max(angles) - min(angles) < 20


def test_a_sleeve_is_a_wider_arm():
    cv = canvas()
    reach(cv, cv.comp, "arm", (0.0, 0.0), TRACK, sleeve="#335577")
    assert "#335577" in cv.scene.to_bytes().decode()


@pytest.mark.parametrize(
    ("shoulder", "track", "match"),
    [
        ((0.0, 0.0), [], "at least one"),
        ((0.0, 0.0), [(0.0, 1.0)], "points of finite numbers"),
        ((0.0, 0.0), [(0.0, math.nan, 1.0)], "points of finite numbers"),
        ((0.0, 0.0), [(1.0, 5.0, 5.0), (1.0, 6.0, 6.0)], "rising time"),
        ((0.0, 0.0), [(1.0, 5.0, 5.0), (0.5, 6.0, 6.0)], "rising time"),
        ((5.0, 5.0), [(1.0, 5.0, 5.0)], "no arm to draw"),
    ],
)
def test_a_track_it_cannot_draw_is_refused(shoulder, track, match):
    cv = canvas()
    with pytest.raises(ReachError, match=match):
        reach(cv, cv.comp, "arm", shoulder, track)


def body(actor, seated=False, **extras) -> str:
    cv = canvas()
    who = actor(cv, seated=seated) if seated else actor(cv)
    who.build(cv.comp, 540, 900, perf=Performance(extras=extras))
    return cv.scene.to_bytes().decode()


def test_the_barista_stands_on_legs_only_when_asked():
    apron = "M-43 119 L-54 327"
    assert "M15 462" not in body(cast.Barista) and body(cast.Barista, legs=False) == body(cast.Barista)
    drawn = body(cast.Barista, legs=True)
    assert drawn.index("M-53 310") < drawn.index(apron)  # the legs come out from under the apron
    assert "M15 462" in drawn


def test_the_barista_refuses_legs_that_are_not_a_yes_or_no():
    with pytest.raises(cast.CastError, match="True or False"):
        body(cast.Barista, legs="standing")


def test_a_free_arm_leaves_out_the_arm_and_the_hand_on_that_side():
    drawn = body(cast.Barista, free_arms=("right",))
    assert "M68 141 L101 205 L117 208" not in drawn and "M-66 140 L-104 212 L-119 229" in drawn
    assert 'x="108"' not in drawn and 'x="-128"' in drawn


def test_a_free_arm_leaves_out_what_that_hand_holds():
    drawn = body(cast.Customer, seated=True, free_arms=("left", "right"))
    assert "customer-park-phone" not in drawn and "coffee-cup" not in drawn


@pytest.mark.parametrize("actor", [cast.Rosa, cast.Candidate, cast.Manager])
def test_an_office_actor_leaves_out_a_free_arm_alone(actor):
    both = body(actor)
    assert body(actor, free_arms=()) == both
    left, right = f"M-66 148 L-87 235 L-79 {actor.bottom}", f"M67 148 L86 233 L77 {actor.bottom}"
    assert left in both and right in both
    one = body(actor, free_arms=("right",))
    assert left in one and right not in one
    assert left not in body(actor, free_arms=("left", "right"))


def test_an_office_arm_that_is_articulated_cannot_be_left_out():
    cv = canvas()
    with pytest.raises(CastError, match="articulated arm cannot be left out"):
        cast.Candidate(cv).build(
            cv.comp, 540, 900, perf=Performance(extras={"free_arms": ("right",), "arms": "articulated"})
        )


def test_without_it_the_arms_are_the_drawn_ones():
    assert body(cast.Barista, free_arms=()) == body(cast.Barista)
    assert "M-66 140 L-104 212 L-119 229 M68 141 L101 205 L117 208" in body(cast.Barista)


@pytest.mark.parametrize("free", ["left", ("up",), ("left", "down")])
@pytest.mark.parametrize("actor", [cast.Barista, cast.Rosa])
def test_a_side_that_is_not_one_is_refused(actor, free):
    cv = canvas()
    with pytest.raises(CastError, match="free_arms names screen sides"):
        actor(cv).build(cv.comp, 540, 900, perf=Performance(extras={"free_arms": free}))
def test_a_side_that_is_not_one_is_refused(free):
    cv = canvas()
    with pytest.raises(CastError, match="free_arms names screen sides"):
        cast.Barista(cv).build(cv.comp, 540, 900, perf=Performance(extras={"free_arms": free}))
