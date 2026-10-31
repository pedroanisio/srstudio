"""Cutout across a counter: the pen on its chain."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_counter, registry
from srstudio.signature import Signature
from support.tip_tablet import canvas

CHECKED = cutout_counter.CutoutCounterError
WALK = ((2.0, 300.0, 1000.0), (4.0, 900.0, 1000.0))  # a hand walking right at 300 px a second


def animations(cv, node: str, prop: str) -> list[tuple[float, float]]:
    for element in ET.fromstring(cv.scene.to_bytes()).iter():
        if element.get("id") != node:
            continue
        for animate in element.iter():
            if animate.tag.endswith("animate") and animate.get("property") == prop:
                return [(float(k.get("time")), float(k.get("value"))) for k in animate if k.tag.endswith("key")]
    raise AssertionError(f"{node} has no {prop} keys")


def errors(cv) -> list:
    return [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message]


def test_the_pen_is_registered_as_a_cutout_prop():
    assert registry.get("prop", "pen-on-chain").style == "cutout"


def test_the_chain_runs_out_when_the_hand_is_its_length_from_the_foot():
    run = cutout_counter.chain_run(300, 1000, 480, WALK)
    assert run.taut == pytest.approx(3.6)
    assert (run.snap, run.home) == (None, None)


def test_a_chain_that_never_runs_out_has_no_taut_moment():
    assert cutout_counter.chain_run(300, 1000, 900, WALK).taut is None


def test_a_snap_lands_the_pen_home_after_its_recoil():
    run = cutout_counter.chain_run(300, 1000, 480, WALK, snap=3.8)
    assert run.home == pytest.approx(3.8 + cutout_counter.CHAIN_RECOIL)


def test_the_pen_stops_dead_at_the_end_of_the_chain_however_far_the_hand_goes():
    cv = canvas()
    run = cutout_counter.pen_on_chain(cv, cv.comp, 300, 1000, length=480, grip=WALK)
    keys = animations(cv, "pen-on-chain-pen", "x")
    assert max(v for _, v in keys) == pytest.approx(780, abs=0.01)
    assert keys[-1][1] == pytest.approx(780, abs=0.01)
    assert run.taut == pytest.approx(3.6)
    assert errors(cv) == []


def test_nothing_moves_before_the_grip():
    cv = canvas()
    cutout_counter.pen_on_chain(cv, cv.comp, 300, 1000, length=480, grip=WALK)
    for name in ("pen-on-chain-pen", "pen-on-chain-link-15"):
        early = [v for t, v in animations(cv, name, "x") if t <= WALK[0][0]]
        assert len(set(early)) == 1


def test_the_pen_snaps_back_to_its_cradle_and_the_chain_settles_where_it_began():
    cv = canvas()
    run = cutout_counter.pen_on_chain(cv, cv.comp, 300, 1000, length=480, grip=WALK, snap=3.8)
    pen = animations(cv, "pen-on-chain-pen", "x")
    assert pen[-1][1] == 300
    assert [v for t, v in pen if t >= run.home] == [300] * len([v for t, v in pen if t >= run.home])
    flying = [v for t, v in pen if run.snap < t < run.home]
    assert flying == sorted(flying, reverse=True), "it flies straight home"
    link = animations(cv, "pen-on-chain-link-15", "y")
    assert link[-1][1] == pytest.approx(link[0][1], abs=1.0)


def test_a_taut_chain_is_a_straight_line_and_a_slack_one_hangs():
    assert cutout_counter._link(0, 0, (480, 0), 480, 0.5, 0.0)[1] == pytest.approx(0)
    assert cutout_counter._link(0, 0, (240, 0), 480, 0.5, 0.0)[1] > 50


@pytest.mark.parametrize(
    ("kw", "pattern"),
    [
        (dict(length=0), "length"),
        (dict(length=float("nan")), "length"),
        (dict(grip=((1.0, 0.0, 0.0),)), "two"),
        (dict(grip=((2.0, 0.0, 0.0), (1.0, 0.0, 0.0))), "rise"),
        (dict(grip=((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))), "rise"),
        (dict(snap=3.0), "taut"),
        (dict(length=900, snap=3.8), "taut"),
        (dict(scale=0), "scale"),
    ],
)
def test_a_chain_that_cannot_be_drawn_is_refused(kw, pattern):
    cv = canvas()
    args = dict(length=480, grip=WALK) | kw
    with pytest.raises(CHECKED, match=pattern):
        cutout_counter.pen_on_chain(cv, cv.comp, 300, 1000, **args)


def test_the_poster_says_what_it_is_given():
    cv = canvas()
    cutout_counter.paper_poster(cv, cv.comp, 100, 100, text="HERE FOR YOU")
    assert errors(cv) == []
    assert b"HERE FOR YOU" in cv.scene.to_bytes()


@pytest.mark.parametrize(
    ("kw", "pattern"),
    [(dict(text=" "), "says"), (dict(width=0), "size"), (dict(size=0), "tilt"), (dict(tilt=float("inf")), "tilt")],
)
def test_a_poster_that_cannot_be_drawn_is_refused(kw, pattern):
    cv = canvas()
    with pytest.raises(CHECKED, match=pattern):
        cutout_counter.paper_poster(cv, cv.comp, 0, 0, **kw)


def test_a_clock_is_still_until_a_jump_and_then_twenty_minutes_on():
    cv = canvas()
    cutout_counter.jump_clock(cv, cv.comp, 540, 300, start=(3, 10), jumps=((4.0, 20), (9.0, 20)))
    keys = animations(cv, "jump-clock-minute", "rotation")
    assert keys[0] == (0, 60)
    assert keys[1] == (4.0, 60)
    assert keys[2] == (pytest.approx(4.0 + cutout_counter.CLOCK_SPIN), 180)
    assert keys[3] == (9.0, 180)
    assert keys[4][1] == 300
    assert errors(cv) == []


def test_the_hour_hand_goes_a_twelfth_as_far():
    cv = canvas()
    cutout_counter.jump_clock(cv, cv.comp, jumps=((4.0, 60),))
    keys = animations(cv, "jump-clock-hour", "rotation")
    assert keys[-1][1] - keys[1][1] == pytest.approx(30)


@pytest.mark.parametrize(
    ("kw", "pattern"),
    [
        (dict(start=(13, 0)), "hour"),
        (dict(start=(3, 60)), "hour"),
        (dict(radius=0), "radius"),
        (dict(spin=0), "positive time"),
        (dict(jumps=((1.0, 0),)), "jump is"),
        (dict(jumps=((-1.0, 5),)), "jump is"),
        (dict(jumps=((1.0, 5), (1.2, 5))), "stopped"),
    ],
)
def test_a_clock_that_cannot_be_drawn_is_refused(kw, pattern):
    cv = canvas()
    with pytest.raises(CHECKED, match=pattern):
        cutout_counter.jump_clock(cv, cv.comp, **kw)


def test_the_sandwich_draws_and_refuses_a_bad_scale():
    cv = canvas()
    cutout_counter.sandwich(cv, cv.comp, 100, 100)
    assert errors(cv) == []
    with pytest.raises(CHECKED, match="scale"):
        cutout_counter.sandwich(cv, cv.comp, 100, 100, scale=0, id="other")


def signed():
    cv = canvas()
    cv.signature = Signature()
    return cv


def test_the_back_room_is_a_door_then_a_push_with_the_hall_going_faster():
    cv = signed()
    cutout_counter.back_room(cv, cv.comp, opens=1.0, push=(1.2, 3.2), shots=[(0, 5)])
    assert errors(cv) == []
    room = animations(cv, "back-room-room", "scaleX")
    hall = animations(cv, "back-room-hall", "scaleX")
    assert (room[0][1], room[-1][1]) == (cutout_counter.ROOM_FAR, 1.0)
    assert hall[-1][1] / hall[0][1] > room[-1][1] / room[0][1]
    assert animations(cv, "back-room-door", "scaleX")[1] == (1.0, 1.0)


@pytest.mark.parametrize(
    ("kw", "pattern"),
    [(dict(push=(3.0, 2.0)), "push"), (dict(opens=2.0, push=(1.0, 3.0)), "door opens"), (dict(plate=" "), "nameplate")],
)
def test_a_back_room_that_cannot_be_drawn_is_refused(kw, pattern):
    cv = signed()
    with pytest.raises(CHECKED, match=pattern):
        cutout_counter.back_room(cv, cv.comp, **kw)
