"""An arm that bends at the elbow, on the way to a hand that keeps its time."""

from __future__ import annotations

import math

import pytest

from srstudio import cast, cutout_arm
from srstudio.rig import Performance
from support.tip_tablet import canvas


def tip(shoulder, upper, fore, a, b):
    """Forward through the two rotations: where the forearm ends."""
    ax, ay = math.cos(math.radians(a)), math.sin(math.radians(a))
    bx, by = math.cos(math.radians(a + b)), math.sin(math.radians(a + b))
    return shoulder[0] + upper * ax + fore * bx, shoulder[1] + upper * ay + fore * by


@pytest.mark.parametrize("target", [(100, 0), (60, -150), (-120, 90), (0, 200), (-180, -40)])
@pytest.mark.parametrize("bend", [1, -1])
def test_the_two_angles_put_the_forearms_end_on_the_hand(target, bend):
    a, b = cutout_arm.angles((10, 20), 130, 110, (10 + target[0], 20 + target[1]), bend)
    assert tip((10, 20), 130, 110, a, b) == pytest.approx((10 + target[0], 20 + target[1]), abs=1e-6)


def test_the_elbow_bends_the_side_it_is_told():
    assert cutout_arm.angles((0, 0), 100, 100, (120, 0), 1)[1] > 0
    assert cutout_arm.angles((0, 0), 100, 100, (120, 0), -1)[1] < 0


def test_the_hand_eases_and_holds_at_both_ends_of_its_track():
    track = [(1.0, 0, 0), (2.0, 100, 50)]
    assert cutout_arm.hand_at(track, 0.5) == (0, 0)
    assert cutout_arm.hand_at(track, 1.5) == pytest.approx((50, 25))
    assert cutout_arm.hand_at(track, 3.0) == (100, 50)


def test_a_drawn_arm_gives_back_its_groups_and_keys_its_grip_on_the_track():
    cv = canvas()
    arm = cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(0.0, 100, 100), (0.5, 150, 40)])
    assert arm.group is not None and arm.grip is not None
    assert (float(arm.grip.x), float(arm.grip.y)) == (100, 100)


def test_a_finger_is_drawn_only_when_asked():
    plain, pointing = canvas(), canvas()
    cutout_arm.arm(plain, plain.comp, "reach", (0, 0), [(0.0, 100, 100)])
    cutout_arm.arm(pointing, pointing.comp, "reach", (0, 0), [(0.0, 100, 100)], finger=True)
    assert len(pointing.scene.to_bytes()) > len(plain.scene.to_bytes())


def test_a_hand_past_the_arms_length_is_refused_by_its_time():
    cv = canvas()
    with pytest.raises(cutout_arm.CutoutArmError, match=r"1\.5"):
        cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(1.5, 400, 0)], upper=130, fore=130)


def test_a_hand_on_the_elbow_side_of_a_short_forearm_is_refused():
    cv = canvas()
    with pytest.raises(cutout_arm.CutoutArmError):
        cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(1.0, 10, 0)], upper=130, fore=100)


@pytest.mark.parametrize(
    "track",
    [
        [],
        [(1.0, 10)],
        [(1.0, 100, float("nan"))],
        [(1.0, 100, 100), (1.0, 120, 100)],
        [(2.0, 100, 100), (1.0, 120, 100)],
    ],
)
def test_a_track_it_cannot_follow_is_refused(track):
    cv = canvas()
    with pytest.raises(cutout_arm.CutoutArmError):
        cutout_arm.arm(cv, cv.comp, "reach", (0, 0), track)


@pytest.mark.parametrize(
    "options",
    [dict(upper=0), dict(fore=-1), dict(upper=float("inf")), dict(bend=0), dict(bend=2), dict(width=0), dict(hand=-3)],
)
def test_an_arm_it_cannot_draw_is_refused(options):
    cv = canvas()
    with pytest.raises(cutout_arm.CutoutArmError):
        cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(0.0, 100, 100)], **options)


def test_the_rotation_never_takes_the_long_way_round():
    cv = canvas()
    track = [(0.0, -150, 10), (1.0, -150, -10)]
    keys = cutout_arm.arm(cv, cv.comp, "reach", (0, 0), track).rotations
    assert max(abs(b[1] - a[1]) for a, b in zip(keys, keys[1:], strict=False)) < 45


def test_a_hand_takes_the_skin_it_is_given():
    cv = canvas()
    cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(0.0, 100, 100)], skin="#C28A65")
    assert b"#C28A65" in cv.scene.to_bytes()


@pytest.mark.parametrize("skin", ["", 7])
def test_a_skin_that_is_no_colour_is_refused(skin):
    cv = canvas()
    with pytest.raises(cutout_arm.CutoutArmError):
        cutout_arm.arm(cv, cv.comp, "reach", (0, 0), [(0.0, 100, 100)], skin=skin)


def drawn(actor, **extras) -> bytes:
    cv = canvas()
    actor(cv).build(cv.comp, 540, 900, perf=Performance(extras=extras))
    return cv.scene.to_bytes()


def test_a_cafe_actor_leaves_out_an_arm_a_reel_will_draw():
    assert len(drawn(cast.Barista, free_arms=("right",))) < len(drawn(cast.Barista))
    assert len(drawn(cast.Customer, free_arms=("left", "right"))) < len(drawn(cast.Customer, free_arms=("left",)))


def test_a_cafe_actor_with_no_free_arm_is_drawn_as_it_always_was():
    assert drawn(cast.Barista, free_arms=()) == drawn(cast.Barista)


@pytest.mark.parametrize("free", ["left", ("up",), ("left", "back")])
def test_a_free_arm_on_no_known_side_is_refused(free):
    cv = canvas()
    with pytest.raises(cast.CastError, match="free_arms names screen sides"):
        cast.Barista(cv).build(cv.comp, 540, 900, perf=Performance(extras={"free_arms": free}))
