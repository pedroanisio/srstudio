"""The Stick front door: the hall, the yard through the doorway, a door that swings in, the truck and the clipboard."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, Signature, flat_counter, registry, stick, stick_door, stick_porch


def canvas(*, font: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter" if font else None, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def test_the_set_and_its_props_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {
        ("location", "stick-hall"),
        ("prop", "stick-front-door"),
        ("prop", "stick-tow-truck"),
        ("prop", "stick-clipboard"),
    } <= names


def test_the_hall_carries_both_signature_marks():
    cv = canvas()
    cv.signature = Signature()
    stick_porch.hall(cv, cv.comp, 4.0)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_the_hall_blurs_only_the_houses_across_the_road_with_the_sheet_named():
    cv = canvas()
    stick_porch.hall(cv, cv.comp, 4.0)
    assert "porch-far-blur" in cv.scene.to_bytes(layout="pretty").decode()


def test_what_stands_in_the_yard_stops_at_the_inside_of_the_door_frame():
    cv = canvas()
    stick_porch.outside(cv, cv.comp)
    x, y, w, _ = stick_door.DOORWAY
    path = next(m.get("path") for m in xml(cv).iter("mask"))
    assert f"{x + stick_porch.JAMB_WIDTH / 2}" in path and f"{x + w - stick_porch.JAMB_WIDTH / 2}" in path


def test_a_shut_door_steps_through_its_swing_then_stays_back():
    cv = canvas()
    stick_porch.front_door(cv, cv.comp, 4.0, opens=0.5)
    gated = [a for a in xml(cv).iter("animate") if a.get("property") == "opacity"]
    assert len(gated) == stick_door.SWING_STEPS + 1  # shut, then a frame per step


def test_a_door_that_opens_at_once_draws_no_shut_frame():
    cv = canvas()
    stick_porch.front_door(cv, cv.comp, 4.0, opens=0.0)
    gated = [a for a in xml(cv).iter("animate") if a.get("property") == "opacity"]
    assert len(gated) == stick_door.SWING_STEPS


def test_a_door_left_open_is_one_still_drawing():
    cv = canvas()
    stick_porch.front_door(cv, cv.comp, 4.0)
    assert not [a for a in xml(cv).iter("animate")]


@pytest.mark.parametrize("opens", [-0.1, 3.99, float("nan"), "soon"])
def test_a_door_that_cannot_finish_its_swing_is_refused(opens):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="opens"):
        stick_porch.front_door(cv, cv.comp, 4.0, opens=opens)


@pytest.mark.parametrize("draw", [stick_porch.hall, stick_porch.front_door, stick_porch.tow_truck])
@pytest.mark.parametrize("end", [0, -1.0, float("nan")])
def test_a_shot_with_no_length_is_refused(draw, end):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="positive shot length"):
        draw(cv, cv.comp, end)


def test_the_truck_stands_in_the_doorway_and_comes_larger_as_it_nears():
    far, near = stick_porch.truck_place(0.2), stick_porch.truck_place(stick_porch.PARKED)
    x, y, w, h = stick_door.DOORWAY
    assert near[2] > far[2] and near[1] > far[1]
    assert x < near[0] < x + w and y < near[1] < y + h


def test_the_hook_comes_down_beside_a_visitor_and_stays_above_his_chest():
    x, y, scale = stick_porch.truck_place(stick_porch.PARKED)
    vx, vy, vscale = stick_door.on_path(stick_porch.VISITOR, stick_porch.VISITOR_LANE)
    head_x = vx + 540 * vscale
    hook_y = y + (stick_porch.BOOM_TOP + stick_porch.HOOK_LOW) * scale
    assert x - head_x > 80  # clear of his head
    assert hook_y < vy + 900 * vscale  # no lower than his chest


def test_a_reversing_truck_is_keyed_and_a_parked_one_is_not():
    moving, parked = canvas(), canvas()
    stick_porch.tow_truck(moving, moving.comp, 4.0, path=((0.0, 0.1), (3.0, 0.6)), drop=3.1)
    stick_porch.tow_truck(parked, parked.comp, 4.0)
    props = lambda cv: {a.get("property") for a in xml(cv).iter("animate")}  # noqa: E731
    assert {"x", "y", "scaleX", "scaleY"} <= props(moving)
    assert "x" not in props(parked)


def test_the_truck_is_unbranded():
    cv = canvas()
    stick_porch.tow_truck(cv, cv.comp, 4.0)
    assert not list(xml(cv).iter("text"))


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(path=((1.0, 0.2), (1.0, 0.4))), "time order"),
        (dict(path=((3.0, 0.2), (2.0, 0.4))), "time order"),
        (dict(path=((0.0, 0.2), (9.0, 0.4))), "inside the shot"),
        (dict(path=((0.0, 0.0), (1.0, 0.4))), "depth"),
        (dict(path=((0.0, 2.0),)), "depth"),
        (dict(drop=3.9), "hook"),
        (dict(drop=-1.0), "hook"),
    ],
)
def test_a_truck_that_cannot_be_drawn_is_refused(kw, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick_porch.tow_truck(cv, cv.comp, 4.0, **kw)


def test_the_clipboard_is_blank_edge_on_and_needs_a_font_only_when_turned():
    silent = canvas(font=False)
    stick_porch.clipboard(silent, silent.comp)
    with pytest.raises(Exception, match="the clipboard's page"):
        stick_porch.clipboard(silent, silent.comp, turned=True)


@pytest.mark.parametrize("heading", ["", "   ", "A" * (stick_porch.BOARD_LETTERS + 1)])
def test_a_heading_that_does_not_fit_the_page_is_refused(heading):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="heading"):
        stick_porch.clipboard(cv, cv.comp, turned=True, heading=heading)


@pytest.mark.parametrize("pose", ["board", "read", "offer", "knob", "small"])
def test_each_pose_draws_on_the_figure(pose):
    cv = canvas()
    keys = [stick.RigKey(0.0, pose)]
    stick.rig(cv, cv.comp, keys, 2.0, poses=stick_porch.POSES)
    assert stick.hand_at(stick_porch.POSES[pose])[1] < 1300


def test_the_householder_stands_right_of_the_doorway_clear_of_the_bug():
    x, y = stick_porch.HOUSEHOLDER_AT
    scale = stick_porch.HOUSEHOLDER_SCALE
    head = stick_porch.POSES["knob"].head
    assert x - scale * head[0] > stick_door.DOORWAY[0] + stick_door.DOORWAY[2]
    assert y + scale * head[1] > 400
