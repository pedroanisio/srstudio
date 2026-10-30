"""The Stick entrance: a lobby seen from inside, the street through its doorway, the glass door and who comes along."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, Signature, flat_counter, registry, stick, stick_door


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def test_the_set_and_its_props_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {
        ("location", "stick-entrance"),
        ("prop", "stick-glass-door"),
        ("prop", "stick-snow-cap"),
        ("prop", "stick-marathon"),
    } <= names


@pytest.mark.parametrize("draw", [stick_door.entrance, stick_door.street])
def test_each_set_carries_both_signature_marks(draw):
    cv = canvas()
    cv.signature = Signature()
    draw(cv, cv.comp, 4.0)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_the_light_is_keyed_only_when_night_falls():
    still, falling = canvas(), canvas()
    stick_door.entrance(still, still.comp, 4.0)
    stick_door.entrance(falling, falling.comp, 4.0, night=((0.0, 0.0), (3.0, 0.8)))
    count = lambda cv: sum(a.get("property") == "opacity" for a in xml(cv).iter("animate"))  # noqa: E731
    assert count(falling) > count(still)


@pytest.mark.parametrize(
    "night", [(), ((1.0, 0.5),), ((0.0, 2.0),), ((0.0, 0.1), (0.0, 0.2)), ((0.0, 0.1), (9.0, 0.2))]
)
def test_the_night_keys_are_refused_when_they_cannot_be_drawn(night):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="night"):
        stick_door.entrance(cv, cv.comp, 4.0, night=night)


def test_the_door_has_a_frame_per_step_of_its_swing_and_ends_shut():
    assert stick_door.door_edge(0) == pytest.approx(stick_door.OPEN_EDGE)
    assert stick_door.door_edge(stick_door.SWING_STEPS) == pytest.approx(stick_door.DOORWAY[0])
    edges = [stick_door.door_edge(i) for i in range(stick_door.SWING_STEPS + 1)]
    assert edges == sorted(edges, reverse=True)
    cv = canvas()
    stick_door.door(cv, cv.comp, 4.0, shut=1.0)
    drawn, shut = canvas(), canvas()
    stick_door.door(drawn, drawn.comp, 4.0)
    stick_door.door(shut, shut.comp, 4.0, closed=True)
    assert len(list(xml(cv).iter("shape"))) == (stick_door.SWING_STEPS + 1) * len(list(xml(drawn).iter("shape")))
    assert xml(shut).find(".//shape").get("path") != xml(drawn).find(".//shape").get("path")
    with pytest.raises(stick.StickDataError, match="closed"):
        stick_door.door(canvas(), None, 4.0, shut=1.0, closed=True)


@pytest.mark.parametrize("shut", [0.0, 4.0, -1.0, float("nan")])
def test_a_door_cannot_shut_outside_its_shot(shut):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="shut"):
        stick_door.door(cv, cv.comp, 4.0, shut=shut)


def test_the_holder_s_hand_reaches_the_door_s_edge_in_every_holding_pose():
    edge = stick_door.OPEN_EDGE
    for name in ("hold", "hold-a", "hold-b"):
        x = stick_door.HOLDER_AT[0] - stick_door.HOLD[name].hands[1][0]  # mirrored about the holder's place
        assert abs(x - edge) < 30, name
    assert stick_door.HOLD["drop"].hands[1][1] > stick_door.HOLD["hold"].hands[1][1] + 200  # the arm has given out


def test_the_shaking_arm_alternates_and_stays_inside_the_span():
    keys = stick_door.shaking(0.5, 1.5, stick.Face())
    assert [k.pose for k in keys[:3]] == ["hold-a", "hold-b", "hold-a"]
    assert keys[0].start == 0.5 and keys[-1].start < 1.5
    with pytest.raises(stick.StickDataError, match="shak"):
        stick_door.shaking(1.0, 1.0, stick.Face())


def test_a_place_on_the_path_grows_as_it_nears_the_door_and_stands_on_the_path():
    far, near = stick_door.on_path(0.1), stick_door.on_path(0.9)
    assert far[2] < near[2]
    for depth in (0.1, 0.9):
        x, y, scale = stick_door.on_path(depth)
        foot = y + 1700 * scale
        assert stick_door.VANISH[1] < foot <= stick_door.DOORWAY[1] + stick_door.DOORWAY[3] + 1
        assert stick_door.DOORWAY[0] < x + 540 * scale < stick_door.DOORWAY[0] + stick_door.DOORWAY[2]
    with pytest.raises(stick.StickDataError, match="depth"):
        stick_door.on_path(stick_door.MAX_DEPTH + 0.1)
    with pytest.raises(stick.StickDataError, match="lane"):
        stick_door.on_path(0.5, 2.0)
    assert stick_door.on_path(0.5, -1.0)[0] < stick_door.on_path(0.5, 1.0)[0]


def test_a_jogger_draws_two_frames_turn_about():
    cv = canvas()
    stick_door.jogger(cv, cv.comp, 2.0, look=stick.Look(), face=stick.Face())
    assert len(stick_door.steps(2.0, 6.0)[0]) >= 5
    with pytest.raises(stick.StickDataError, match="rate"):
        stick_door.steps(2.0, 0.0)


def test_the_approach_keys_refuse_a_path_out_of_order():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="approach"):
        stick_door.approach(cv, cv.comp, ((1.0, 0.2), (0.5, 0.4)))


def test_the_snow_cap_grows_and_refuses_a_step_it_has_not_got():
    cv = canvas()
    stick_door.snow_cap(cv, cv.comp, 100, 100, 3)
    with pytest.raises(stick.StickDataError, match="snow"):
        stick_door.snow_cap(cv, cv.comp, 100, 100, 9)


def test_snow_stays_in_its_box():
    cv = canvas()
    stick_door.snow(cv, cv.comp, 3.0, x=100, y=200, w=500, h=1000)
    ys = [float(k.get("value")) for a in xml(cv).iter("animate") if a.get("property") == "y" for k in a.iter("key")]
    assert ys and 200 <= min(ys) and max(ys) <= 1200.5


def test_the_marathon_runs_past_within_its_shot():
    cv = canvas()
    stick_door.marathon(cv, cv.comp, 2.0)
    with pytest.raises(stick.StickDataError, match="marathon"):
        stick_door.marathon(cv, cv.comp, 0.0)
