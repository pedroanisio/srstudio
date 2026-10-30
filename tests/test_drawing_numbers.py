"""The shared drawing modules' numbers are numbers (ADR 0035): each case feeds ``True`` where a module took
``math.isfinite`` (or ``isinstance(int | float)``) for a number check, which takes a bool as 1."""

from __future__ import annotations

import pytest

from srstudio import blob, brush, camera, cel, look, props, soft_props, staging
from srstudio.errors import SrstudioError
from srstudio.soft_props import BadgeState
from srstudio.staging import Move
from support.cel import BOX
from support.ink_layout import square_canvas
from support.pink_slip import canvas as office_canvas
from support.soft_props import canvas as soft_canvas
from support.tip_tablet import canvas as cafe_canvas

BADGE_BOX = (500, 560, 420, 92)


def square(fn, *args, **kw):
    _, cv = square_canvas()
    fn(cv, *args, **kw)


def zoom(**kw):
    _, cv = square_canvas()
    camera.crash_zoom(cv, cv.group(cv.comp, "g"), **({"at": 1.0, "scale": 1.4} | kw))


def soft(fn, *args, **kw):
    cv = soft_canvas()
    fn(cv, cv.comp, *args, **kw)


@pytest.mark.parametrize(
    "call",
    [
        lambda: blob.cue(1.0, "sit", (1.0, 1.0), scale=True),
        lambda: blob.settle([blob.Cue(0, "sit")], True),
        lambda: soft(blob.home, lamp_talk=[(True, 1.2)]),
        lambda: brush.spline([(0, 0), (True, 10)]),
        lambda: brush.stroke([(0, 50), (100, 50)], True),
        lambda: zoom(at=True),
        lambda: zoom(scale=True),
        lambda: zoom(start_scale=True),
        lambda: zoom(at=0.0, back=True),
        lambda: square(lambda cv: cv.gate(cv.group(cv.comp, "g"), [(True, 2.0)])),
        lambda: cel.Pressed(BOX, (), press=True),
        lambda: cel.Pressed(BOX, (), press_seconds=True),
        lambda: cel.Pressed((True, 40.0, 60.0, 60.0), ()),
        lambda: square(lambda cv: look.depth(cv, cv.comp, "far", True)),
        lambda: props.tip_tablet(cafe_canvas(), None, 0, 0, scale=True),
        lambda: props.pink_slip(office_canvas(), None, 0, 0, name="ERIC", scale=True),
        lambda: soft(soft_props.status_badge, [BadgeState("a", "A", "#000000", True, 2.0)], BADGE_BOX),
        lambda: soft(soft_props.status_badge, [BadgeState("a", "A", "#000000", 0.0, 1.0)], (True, 560, 420, 92)),
        lambda: soft(soft_props.cake, "OK", back="BYE", turn_at=True),
        lambda: soft(soft_props.cake, "OK", scale=True),
        lambda: staging.check_move(Move("crash", True, 1.4, 540, 900), 2.0, "take 01"),
    ],
)
def test_a_bool_is_not_a_second_a_scale_or_a_size(call):
    with pytest.raises(SrstudioError):
        call()


def test_a_bool_is_refused_as_a_number_even_where_its_value_would_be_refused_anyway():
    # True is 1: slower than a snap, and too narrow for a name tag; the number check names the real fault
    with pytest.raises(camera.CameraError, match="duration True must be > 0"):
        zoom(duration=True)
    with pytest.raises(soft_props.SoftPropError, match="positive size"):
        soft(soft_props.beach_call, True, 600, name="Rae")


def test_inside_is_false_for_a_bool_span():
    assert staging.inside(0.0, 1.0, 2.0)
    assert not staging.inside(True, 1.5, 2.0)
    assert not staging.inside(0.0, True, 2.0)
