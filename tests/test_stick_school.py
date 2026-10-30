"""The Stick classroom: the room on parent-teacher night, the tiny chair a grown-up perches on, the teacher's desk
and the essay page whose lines come up one at a time, highlighted as they are read."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_school
from support.stick_school import LINES


def canvas(font: str | None = "inter") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [t.get("text") for t in xml(cv).iter("text")]


def keyed(root: ET.Element, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
        if a.get("property") == prop
    ]


def test_the_parts_are_registered_for_the_stick_style():
    for kind, name in (("location", "stick-classroom"), ("prop", "stick-tiny-chair"), ("prop", "stick-teacher-desk"),
                       ("graphic", "stick-essay")):  # fmt: skip
        assert registry.get(kind, name).style == "stick"


def test_the_classroom_letters_its_board_and_refuses_a_long_one():
    cv = canvas()
    stick_school.classroom(cv, cv.comp, board="PARENT NIGHT")
    assert "PARENT NIGHT" in texts(cv) and len(list(xml(cv).iter("shape"))) > 30
    for bad in ("", "X" * (stick_school.BOARD_CHARS + 1)):
        with pytest.raises(stick.StickDataError, match="board"):
            stick_school.classroom(canvas(), None, board=bad)
    with pytest.raises(ValueError, match="font"):
        stick_school.classroom(canvas(None), None)


def test_a_perched_grown_up_has_his_knees_above_his_hip_on_the_tiny_chair():
    seat_y = stick_school.SEAT_Y
    for name, pose in stick_school.PERCHED.items():
        assert all(knee[1] < pose.hip[1] for knee in pose.knees), name
        assert abs(pose.hip[1] - seat_y) <= 12 and all(foot[1] == stick_school.FLOOR_FEET for foot in pose.feet)
    stick.check_keys([stick.RigKey(0, "perch")], 1.0, stick_school.PERCHED)
    cv = canvas()
    stick_school.tiny_chair(cv, cv.comp)
    stick_school.teacher_desk(cv, cv.comp)
    assert len(list(xml(cv).iter("shape"))) > 8


def test_the_teacher_holds_the_page_where_her_hands_are():
    for name in stick_school.READING:
        x, y = stick_school.held(name)
        hands = stick_school.TEACHER_POSES[name].hands
        assert x == pytest.approx(stick_school.TEACHER_AT[0] - sum(h[0] for h in hands) / 2)
        assert y == pytest.approx(sum(h[1] for h in hands) / 2)
        assert stick_school.DESK_X[0] < x  # the page is over the desk, behind it from the parent
    with pytest.raises(stick.StickDataError, match="pose"):
        stick_school.held("wave")


def test_the_essay_shows_only_the_lines_read_so_far():
    cv = canvas()
    stick_school.essay(cv, cv.comp, LINES, title="WHAT MY DAD DOES", by="Max, age 8", shown=2)
    got = texts(cv)
    assert {"WHAT MY DAD DOES", "Max, age 8", LINES[0], LINES[1]} <= set(got) and LINES[2] not in got
    assert keyed(xml(cv), "scaleX") == []  # nothing marked: no highlighter sweeps


def test_the_highlighter_sweeps_the_marked_line_from_its_second():
    cv = canvas()
    stick_school.essay(cv, cv.comp, LINES, title="T", by="B", shown=3, mark=2, mark_at=0.5)
    sweeps = keyed(xml(cv), "scaleX")
    assert sweeps == [[(0.0, 0.0), (0.5, 0.0), (0.5 + stick_school.SWEEP, 1.0)]]


def test_the_grade_and_the_note_are_lettered_when_given():
    cv = canvas()
    stick_school.essay(cv, cv.comp, LINES, title="T", by="B", shown=3, grade="A", note="Edited by Mom")
    assert {"A", "Edited by Mom"} <= set(texts(cv))
    assert keyed(xml(cv), "opacity") == []  # a note from 0 is simply there
    late = canvas()
    stick_school.essay(late, late.comp, LINES, title="T", by="B", shown=3, note="Edited by Mom", note_at=1.2)
    assert keyed(xml(late), "opacity") == [[(0.0, 0.0), (1.2, 0.0), (1.21, 1.0)]]


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(lines=()), "lines"),
        (dict(lines=("x",) * (stick_school.ESSAY_LINES + 1)), "lines"),
        (dict(lines=("",)), "line"),
        (dict(lines=("x" * (stick_school.LINE_CHARS + 1),)), "line"),
        (dict(shown=4), "shown"),
        (dict(shown=-1), "shown"),
        (dict(shown=1, mark=1), "mark"),
        (dict(mark=0, mark_at=-0.5), "mark_at"),
        (dict(grade="ABCD"), "grade"),
        (dict(note="x" * (stick_school.NOTE_CHARS + 1)), "note"),
        (dict(title=""), "title"),
    ],
)
def test_the_essay_refuses_what_it_cannot_letter(kw, match):
    args = dict(lines=LINES, title="T", by="B", shown=3) | kw
    with pytest.raises(stick.StickDataError, match=match):
        stick_school.essay(canvas(), None, **args)
