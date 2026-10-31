"""A Stick camera that moves between two framings, in or out: it lands where it was told, it holds before it moves, a
long move cuts into shots with no jump, and a framing it cannot use is refused."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick
from srstudio.canvas import Signature
from srstudio.stick import StickDataError

CLOSE = ((1480.0, 1270.0), 1.7, (540.0, 900.0))
WIDE = ((1480.0, 1400.0), 0.9, (540.0, 900.0))


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature())


def keys(cv: Canvas) -> dict[str, list[tuple[float, float]]]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return {
        a.get("property"): [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
    }


def landed(group_keys, anchor, point):
    """Where ``point`` of the set lands on the last key of a dolly anchored on ``anchor``."""
    x, y, zoom = group_keys["x"][-1][1], group_keys["y"][-1][1], group_keys["scaleX"][-1][1]
    return x + (point[0] - anchor[0]) * zoom, y + (point[1] - anchor[1]) * zoom


def test_a_pull_back_lands_the_second_focus_where_that_framing_puts_it():
    cv = canvas()
    stick.dolly(cv, cv.comp, CLOSE, WIDE, 2.0)
    assert landed(keys(cv), CLOSE[0], WIDE[0]) == pytest.approx(WIDE[2])


def test_a_move_holds_the_first_framing_until_it_starts():
    cv = canvas()
    stick.dolly(cv, cv.comp, CLOSE, WIDE, 2.0, start=0.5)
    zoom = keys(cv)["scaleX"]
    assert [t for t, _ in zoom] == pytest.approx([0.0, 0.5, 2.5])
    assert [z for _, z in zoom] == pytest.approx([1.7, 1.7, 0.9])


def test_a_move_cut_into_shots_meets_itself_at_the_cut():
    cut = stick.between(CLOSE, WIDE, 0.4)
    first, second = canvas(), canvas()
    stick.dolly(first, first.comp, CLOSE, cut, 1.0)
    stick.dolly(second, second.comp, cut, WIDE, 1.0)
    assert landed(keys(first), CLOSE[0], cut[0]) == pytest.approx(cut[2])
    assert keys(first)["scaleX"][-1][1] == pytest.approx(keys(second)["scaleX"][0][1])


@pytest.mark.parametrize(
    ("at", "zoom"), [(0.0, 1.7), (1.0, 0.9), (0.5, 1.3)], ids=["the start", "the end", "halfway, eased"]
)
def test_between_starts_and_ends_on_its_framings(at, zoom):
    assert stick.between(CLOSE, WIDE, at)[1] == pytest.approx(zoom)


@pytest.mark.parametrize(
    ("a", "b", "seconds", "start", "match"),
    [
        (CLOSE, WIDE, 0, 0.0, "lasts some seconds"),
        (CLOSE, WIDE, 1.0, -1.0, "starts at 0"),
        (CLOSE, ((0.0, 0.0), 0, (0.0, 0.0)), 1.0, 0.0, "positive zoom"),
        ("close", WIDE, 1.0, 0.0, "focus, zoom, to"),
        (CLOSE, ((0.0, float("nan")), 1.0, (0.0, 0.0)), 1.0, 0.0, "finite numbers"),
    ],
)
def test_a_move_it_cannot_make_is_refused(a, b, seconds, start, match):
    with pytest.raises(StickDataError, match=match):
        stick.dolly(canvas(), None, a, b, seconds, start=start)


def test_a_point_outside_the_move_is_refused():
    with pytest.raises(StickDataError, match="0 to 1"):
        stick.between(CLOSE, WIDE, 1.2)
