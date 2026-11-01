"""The Stick table: two people sat at it, the clipboard, the brackets on the wall and the bedding, and each refusal."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_home, stick_table


def canvas(*, font: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter" if font else None, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def test_the_parts_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {("prop", "stick-clipboard"), ("prop", "stick-wall-brackets"), ("prop", "stick-folded-bedding")} <= names


def test_the_clipboard_is_blank_edge_on_and_needs_a_font_only_when_turned():
    silent = canvas(font=False)
    stick_table.clipboard(silent, silent.comp)
    with pytest.raises(Exception, match="the clipboard's page"):
        stick_table.clipboard(silent, silent.comp, turned=True)


def test_a_quarter_clipboard_needs_no_font_and_is_never_also_turned():
    silent = canvas(font=False)
    assert stick_table.clipboard(silent, silent.comp, quarter=True) is not None
    with pytest.raises(stick.StickDataError, match="quarter"):
        stick_table.clipboard(silent, silent.comp, turned=True, quarter=True)


@pytest.mark.parametrize("heading", ["", "   ", "A" * (stick_table.BOARD_LETTERS + 1)])
def test_a_heading_that_does_not_fit_the_page_is_refused(heading):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="heading"):
        stick_table.clipboard(cv, cv.comp, turned=True, heading=heading)


@pytest.mark.parametrize("pose", stick_table.POSES)
def test_each_pose_draws_on_the_figure_and_mirrors_to_the_other_chair(pose):
    cv = canvas()
    keys = [stick.RigKey(0.0, pose)]
    stick.rig(cv, cv.comp, keys, 2.0, poses=stick_table.POSES, at=stick_table.LEFT_AT)
    stick.rig(cv, cv.comp, keys, 2.0, poses=stick_table.POSES, at=stick_table.RIGHT_AT, flip=True)


@pytest.mark.parametrize("pose", [p for p in stick_table.POSES if p not in ("up",)])
def test_a_seated_hand_stays_over_the_table_or_clear_of_it(pose):
    """The table is drawn over the figures: a hand below its top would vanish behind it."""
    for far in (False, True):
        _, y = stick.hand_at(stick_table.POSES[pose], far=far, at=stick_table.LEFT_AT)
        assert y <= stick_table.TOP + 6


def test_the_table_stands_between_the_chairs_and_is_narrower_than_the_kitchen_s():
    left, right = stick_table.TABLE_X
    assert stick_home.TABLE_X[0] < left < right < stick_home.TABLE_X[1]
    assert left + right == pytest.approx(1080.0)


def test_the_table_stands_on_the_floor_the_chairs_stand_on():
    cv = canvas()
    stick_table.table(cv, cv.comp)
    feet = [
        float(n.get("y") or 0) + float(n.get("height"))
        for n in xml(cv).iter()
        if 0 < float(n.get("height") or 0) < 1900
    ]
    assert max(feet) == pytest.approx(stick_table.FLOOR - 20.0)


def test_a_table_can_be_set_and_the_default_keeps_its_drawing():
    def drawn(**kwargs):
        cv = canvas()
        stick_home.table(cv, cv.comp, **kwargs)
        return cv.scene.to_bytes(layout="pretty")

    assert drawn() == drawn(span=stick_home.TABLE_X, top=stick_home.TABLE_TOP, legs=420.0)
    assert drawn(legs=300.0) != drawn()
    with pytest.raises(stick.StickDataError, match="table"):
        drawn(span=(800.0, 200.0))


def test_the_seats_are_a_chair_each_with_its_back_away_from_the_table_and_a_shadow():
    cv = canvas()
    stick_table.seats(cv, cv.comp)
    chairs = [g for g in xml(cv).iter("group") if g.get("scaleX") == "-1"]
    assert len(chairs) == 1  # the left chair mirrored, the right one as drawn
    assert sum(1 for s in xml(cv).iter() if float(s.get("opacity") or 1) < 1) == 2  # a shadow under each


def test_brackets_stand_apart_on_the_wall():
    cv = canvas()
    assert stick_table.wall_brackets(cv, cv.comp, 120, 620) is not None
    with pytest.raises(stick.StickDataError, match="span"):
        stick_table.wall_brackets(cv, cv.comp, 120, 620, span=0)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_table.wall_brackets(cv, cv.comp, 120, 620, scale=0)


def test_the_bedding_slides_only_forward_in_time():
    cv = canvas()
    g = stick_table.folded_bedding(cv, cv.comp, 640, stick_table.TOP, slide=((0.5, 1100.0), (1.0, 640.0)))
    assert g is not None
    with pytest.raises(stick.StickDataError, match="slide"):
        stick_table.folded_bedding(cv, cv.comp, 640, 1090, slide=((1.0, 1100.0), (0.5, 640.0)))
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_table.folded_bedding(cv, cv.comp, 640, 1090, scale=-1)


def test_a_chair_can_stand_taller_and_face_the_other_way_and_the_default_keeps_its_drawing():
    def drawn(**kwargs):
        cv = canvas()
        stick_home.chair(cv, cv.comp, 540, 1500, **kwargs)
        return cv.scene.to_bytes(layout="pretty")

    assert drawn() == drawn(rise=0, flip=False)
    assert drawn(rise=190) != drawn()
    assert drawn(flip=True) != drawn()
    with pytest.raises(stick.StickDataError, match="rise"):
        drawn(rise=-1)


def test_a_kitchen_can_leave_the_safe_out_and_the_default_keeps_it():
    def boxes(**kwargs):
        cv = canvas()
        stick_home.kitchen(cv, cv.comp, marks=False, **kwargs)
        return len(list(xml(cv).iter("shape")))

    assert boxes() == boxes(safe=True)
    assert boxes(safe=False) < boxes()
