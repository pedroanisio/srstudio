"""The Stick table: two people sat at it, the clipboard, the brackets on the wall and the bedding, and each refusal."""

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace

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


def across(cv: Canvas) -> tuple[float, float]:
    """The leftmost and rightmost x of the absolute paths drawn on ``cv``."""
    pairs = [re.findall(r"[ML] (-?[\d.]+) -?[\d.]+", s.get("path")) for s in xml(cv).iter("shape") if s.get("path")]
    xs = [float(x) for found in pairs for x in found]
    return min(xs), max(xs)


def board_and_hands(pose):
    """Where the edge-on board runs, left to right, with the near hand holding it, and where the far hand is."""
    near, _ = stick.hand_at(stick_table.POSES[pose])
    far, _ = stick.hand_at(stick_table.POSES[pose], far=True)
    return (near + stick_table.EDGE_SPAN[0], near + stick_table.EDGE_SPAN[1]), far


def test_the_edge_on_board_is_as_wide_as_the_span_a_pose_is_checked_by():
    cv = canvas()
    stick_table.clipboard(cv, cv.comp)
    assert across(cv) == stick_table.EDGE_SPAN


@pytest.mark.parametrize("pose", ["guard", "up"])
def test_the_rig_draws_under_the_board_so_the_pen_hand_stays_clear_of_it(pose):
    """A far hand behind the edge-on board leaves the pen with no hand on it, out in the air."""
    (left, right), far = board_and_hands(pose)
    assert far < left - stick_table.HAND_CLEAR or far > right + stick_table.HAND_CLEAR


def test_guarding_the_board_the_pen_runs_from_the_hand_onto_it_with_none_in_the_air():
    (left, right), far = board_and_hands("guard")
    tip = far + stick_table.PEN_SPAN[1]
    assert left <= tip <= right


def test_the_pen_is_drawn_about_the_hand_that_holds_it():
    cv = canvas()
    stick_table.pen(cv, cv.comp)
    assert across(cv) == stick_table.PEN_SPAN
    assert stick_table.PEN_SPAN[0] < 0 < stick_table.PEN_SPAN[1]


PEN_IN_HAND = {"write-a": 62.0, "write-b": 70.0, "click": -60.0}


def placed(node: ET.Element, inherited: tuple) -> tuple:
    """``inherited``, a frame's (x, y, turn in degrees, x scale, y scale), with ``node``'s own placement applied."""
    x, y, turn, sx, sy = inherited
    own_x, own_y = float(node.get("x") or 0), float(node.get("y") or 0)
    rad = math.radians(turn)
    dx, dy = own_x * sx, own_y * sy
    return (
        x + dx * math.cos(rad) - dy * math.sin(rad),
        y + dx * math.sin(rad) + dy * math.cos(rad),
        turn + float(node.get("rotation") or 0) * (1 if sx * sy > 0 else -1),
        sx * float(node.get("scaleX") or 1),
        sy * float(node.get("scaleY") or 1),
    )


def strokes(node: ET.Element, frame=(0.0, 0.0, 0.0, 1.0, 1.0)):
    """Every stroked path under ``node`` in the order it is drawn, as (stroke, its points on the frame)."""
    for child in node:
        here = placed(child, frame)
        if child.get("path") and child.get("stroke"):
            x, y, turn, sx, sy = here
            rad = math.radians(turn)
            points = []
            for px, py in re.findall(r"[ML] (-?[\d.]+) (-?[\d.]+)", child.get("path")):
                dx, dy = float(px) * sx, float(py) * sy
                points.append(
                    (x + dx * math.cos(rad) - dy * math.sin(rad), y + dx * math.sin(rad) + dy * math.cos(rad))
                )
            yield child.get("stroke"), child, points
        yield from strokes(child, here)


def to_segment(point, a, b) -> float:
    """How far ``point`` is from the segment ``a`` to ``b``."""
    ax, ay, bx, by = *a, *b
    run = (bx - ax) ** 2 + (by - ay) ** 2
    along = max(0.0, min(1.0, ((point[0] - ax) * (bx - ax) + (point[1] - ay) * (by - ay)) / run))
    return math.dist(point, (ax + along * (bx - ax), ay + along * (by - ay)))


def seated(pose: str, *, flip: bool = False):
    """A figure in ``pose`` with the board and the pen, and each stroke drawn after the board."""
    cv = canvas()
    keys = [stick.RigKey(0.0, pose)]
    place = dict(poses=stick_table.POSES, at=stick_table.RIGHT_AT if flip else stick_table.LEFT_AT, flip=flip)
    stick.rig(cv, cv.comp, keys, 2.0, **place)
    stick_table.board_in_hand(cv, cv.comp, keys, 2.0, tilt=PEN_IN_HAND, **place)
    drawn = list(strokes(xml(cv)))
    last_board = max(i for i, (_, node, _) in enumerate(drawn) if node.get("fill") == stick_table.BOARD)
    return drawn[last_board + 1 :], cv


@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("pose", stick_table.ON_PAGE)
def test_on_the_page_the_arm_comes_over_the_board_and_its_tip_touches_the_pen(pose, flip):
    """The rig draws under the board: an arm that stops at its edge leaves the pen lying on the paper with no hand."""
    over, cv = seated(pose, flip=flip)
    arms = [points for stroke, _, points in over if stroke == cv.ink]
    assert arms, f"no arm is drawn over the board in {pose}"
    pens = [points for stroke, _, points in over if stroke == stick_table.TAIL]
    assert len(arms) == 1 and len(pens) == 1
    assert to_segment(arms[0][-1], *pens[0]) <= (stick.LIMB_FAR + stick_table.PEN_WIDTH) / 2


@pytest.mark.parametrize("pose", stick_table.ON_PAGE)
def test_the_arm_over_the_board_starts_at_the_elbow_and_keeps_the_stroke_of_the_arm_under_it(pose):
    over, cv = seated(pose)
    (_, node, points) = next(item for item in over if item[0] == cv.ink)
    assert points[0] == pytest.approx(
        stick.hand_at(
            replace(stick_table.POSES[pose], hands=stick_table.POSES[pose].elbows), far=True, at=stick_table.LEFT_AT
        )
    )
    assert points[-1] == pytest.approx(stick.hand_at(stick_table.POSES[pose], far=True, at=stick_table.LEFT_AT))
    assert float(node.get("strokeWidth") or node.get("stroke-width")) == stick.LIMB_FAR


@pytest.mark.parametrize("pose", ["point", *stick_table.SHUT])
def test_a_hand_off_the_board_draws_no_arm_over_it(pose):
    over, cv = seated(pose)
    assert not [stroke for stroke, _, _ in over if stroke == cv.ink]


def test_the_arm_over_the_board_holds_the_spans_of_its_pose_and_no_others():
    cv = canvas()
    keys = [stick.RigKey(0.0, "read"), stick.RigKey(0.5, "write-a"), stick.RigKey(1.0, "guard")]
    stick.forearm(cv, cv.comp, keys, 2.0, over=("write-a",), poses=stick_table.POSES, far=True)
    assert len(list(xml(cv).iter("shape"))) == 1
    shown = [(float(k.get("time")), float(k.get("value"))) for k in xml(cv).iter("key")]
    assert shown == [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)]


def test_a_forearm_refuses_what_a_rig_refuses():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="scale"):
        stick.forearm(cv, cv.comp, [stick.RigKey(0.0, "read")], 2.0, over=(), poses=stick_table.POSES, scale=0)
    with pytest.raises(stick.StickDataError, match="unknown pose"):
        stick.forearm(cv, cv.comp, [stick.RigKey(0.0, "nope")], 2.0, over=(), poses=stick_table.POSES)


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
