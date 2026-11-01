"""The Stick interview: the room, the desk with its bottom drawer, a sheet on the desk and the resume insert."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, Signature, flat_counter, registry, stick, stick_interview
from srstudio.canvas import CanvasError


def canvas(*, font: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter" if font else None, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def gated(cv: Canvas) -> list[ET.Element]:
    return [a for a in xml(cv).iter("animate") if a.get("property") == "opacity"]


def test_the_set_and_its_props_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {
        ("location", "stick-interview-room"),
        ("prop", "stick-interview-desk"),
        ("prop", "stick-desk-page"),
        ("prop", "stick-resume-insert"),
    } <= names


@pytest.mark.parametrize(
    "draw",
    [lambda cv: stick_interview.desk(cv, cv.comp, 2.0), lambda cv: stick_interview.resume_insert(cv, cv.comp, 2.0)],
)
def test_the_desk_and_the_insert_each_carry_both_signature_marks(draw):
    cv = canvas()
    cv.signature = Signature()
    draw(cv)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_the_room_keeps_its_far_plane_out_of_focus():
    cv = canvas()
    stick_interview.room(cv, cv.comp, 2.0)
    assert "interview-far-blur" in cv.scene.to_bytes(layout="pretty").decode()


def test_the_shut_drawer_is_one_still_drawing():
    cv = canvas(font=False)
    stick_interview.desk(cv, cv.comp, 2.0)
    assert not gated(cv)


def test_the_drawer_slides_through_its_steps_after_a_shut_frame():
    cv = canvas()
    stick_interview.desk(cv, cv.comp, 4.0, opens=1.0)
    assert len(gated(cv)) == stick_interview.DRAWER_STEPS + 1


def test_a_drawer_that_starts_open_needs_a_font_for_its_menus():
    silent = canvas(font=False)
    with pytest.raises(CanvasError, match="menus"):
        stick_interview.desk(silent, silent.comp, 2.0, is_open=True)


def test_the_open_drawer_shows_three_menus():
    cv = canvas()
    stick_interview.desk(cv, cv.comp, 2.0, is_open=True)
    words = cv.scene.to_bytes(layout="pretty").decode()
    assert all(name in words for name in ("PIZZA", "THAI", "WOK"))


@pytest.mark.parametrize(
    "kw", [dict(opens=-1.0), dict(opens=1.9), dict(opens=float("nan")), dict(opens=0.5, is_open=True)]
)
def test_a_drawer_that_cannot_open_is_refused(kw):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="drawer"):
        stick_interview.desk(cv, cv.comp, 2.0, **kw)


def test_the_pull_moves_out_and_down_with_the_drawer():
    x0, y0 = stick_interview.drawer_handle(0.0)
    x1, y1 = stick_interview.drawer_handle(1.0)
    assert x0 == x1 and y1 > y0


@pytest.mark.parametrize("amount", [-0.1, 1.1, float("nan")])
def test_a_drawer_outside_its_run_is_refused(amount):
    with pytest.raises(stick.StickDataError, match="drawer"):
        stick_interview.drawer_handle(amount)


def test_a_page_face_down_shows_no_ring():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="face down"):
        stick_interview.page(cv, cv.comp, 500, 1000, face_down=True, ringed=True)


@pytest.mark.parametrize("line", ["", "  ", "A" * (stick_interview.LINE_LETTERS + 1)])
def test_a_ringed_line_that_does_not_fit_is_refused(line):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="ringed line"):
        stick_interview.resume_insert(cv, cv.comp, 2.0, line=line)


def test_the_resume_needs_a_font():
    cv = canvas(font=False)
    with pytest.raises(CanvasError, match="resume"):
        stick_interview.resume_insert(cv, cv.comp, 2.0)


@pytest.mark.parametrize("draw", [stick_interview.room, stick_interview.desk, stick_interview.resume_insert])
@pytest.mark.parametrize("end", [0, -1.0, float("nan")])
def test_a_shot_with_no_length_is_refused(draw, end):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="positive shot length"):
        draw(cv, cv.comp, end)


def test_the_two_hands_meet_over_the_desk():
    left = stick.hand_at(stick_interview.POSES["shake-up"], at=stick_interview.LEFT_AT)
    right = stick.hand_at(stick_interview.POSES["shake-up"], at=stick_interview.RIGHT_AT, flip=True)
    assert left == pytest.approx(right)


@pytest.mark.parametrize("pose", sorted(stick_interview.POSES))
def test_every_pose_draws_on_the_figure(pose):
    cv = canvas()
    stick.rig(cv, cv.comp, [stick.RigKey(0.0, pose)], 2.0, poses=stick_interview.POSES)
