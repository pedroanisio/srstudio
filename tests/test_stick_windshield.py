"""The Stick windshield two-shot: the car seen from its hood, the couple in the front seats (Dev driving, Noor
beside him) with the road receding in the rear window behind them, the front-facing seated poses, and the
dashboard in front of them with the wheel and a phone that buzzes in its mount and is put face down."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_windshield
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#bda77a")
    return Canvas(
        scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature() if signed else None
    )


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def keys_of(root: ET.Element, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
        if a.get("property") == prop
    ]


def test_the_parts_and_the_couple_are_registered_in_the_stick_style():
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (("location", "stick-windshield"), ("prop", "stick-windshield-dash")):
        assert entries[name].kind == kind and entries[name].style == "stick"
    assert set(stick_windshield.COUPLE) == {"dev", "noor"}
    assert stick_windshield.COUPLE["dev"] == stick.PLAIN  # the R3 driver keeps his look
    for look in stick_windshield.COUPLE.values():
        stick.check_look(look)
    assert stick_windshield.COUPLE["noor"] != stick_windshield.COUPLE["dev"]


def test_the_seats_put_the_faces_above_the_captions_and_the_dashboard_hides_the_laps():
    for at in (stick_windshield.PASSENGER_AT, stick_windshield.DRIVER_AT):
        for name, pose in stick_windshield.FRONT.items():
            hx, hy = pose.head[0] + at[0], pose.head[1] + at[1]
            assert stick.HEAD_R < hx < 1080 - stick.HEAD_R, name  # the whole head in frame
            assert hy + stick.HEAD_R < stick.WORD_Y, name  # the face clear of the word captions
            assert pose.hip[1] > stick_windshield.DASH_TOP, name  # the lap is under the dashboard
    left = stick_windshield.FRONT["sit"].head[0] + stick_windshield.PASSENGER_AT[0]
    right = stick_windshield.FRONT["sit"].head[0] + stick_windshield.DRIVER_AT[0]
    assert right - left > 3 * stick.HEAD_R  # two heads apart, the rear window between them


def test_the_driving_hands_hold_the_wheel_s_rim():
    (cx, cy), (rx, ry) = stick_windshield.WHEEL_AT, stick_windshield.WHEEL_R
    for name in ("drive", "cite"):
        pose = stick_windshield.FRONT[name]
        held = [h for h in pose.hands if abs(math.hypot((h[0] + stick_windshield.DRIVER_AT[0] - cx) / rx,
                                                         (h[1] - cy) / ry) - 1) < 0.12]  # fmt: skip
        assert len(held) == (2 if name == "drive" else 1), name  # citing history, one hand leaves the wheel


def test_the_road_recedes_in_the_rear_window_without_end():
    cv = canvas()
    stick_windshield.windshield(cv, cv.comp, 3.0, speed=1.0)
    root = xml(cv)
    masks = [m for m in root.iter("mask") if m.get("type") == "path"]
    assert [m.get("path") for m in masks] == [stick_windshield.REAR_WINDOW]
    (sx,) = keys_of(root, "scaleX")
    assert sx[0] == (0.0, 1.0) and sx[-1][0] >= 3.0  # the road shrinks toward the horizon all shot long
    shrinking = [(a, b) for a, b in zip(sx, sx[1:], strict=False) if b[1] < a[1]]
    assert len(shrinking) >= 3 and all(b[1] == pytest.approx(1 / stick_windshield.RECEDE) for _, b in shrinking)
    assert keys_of(root, "scaleY") == [sx]
    parked = canvas()
    stick_windshield.windshield(parked, parked.comp, 3.0, speed=0.0)
    assert keys_of(xml(parked), "scaleX") == []  # a parked car's road holds still


def test_the_car_is_signed_on_the_dashboard_and_the_hood():
    cv = canvas(signed=True)
    stick_windshield.windshield(cv, cv.comp, 2.0)
    stick_windshield.dashboard(cv, cv.comp, 2.0)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_the_phone_buzzes_in_its_mount_and_lies_face_down_from_its_time():
    cv = canvas()
    stick_windshield.dashboard(cv, cv.comp, 4.0, buzz=(1.0,), down=2.5)
    root = xml(cv)
    (shake,) = keys_of(root, "x")
    assert shake[0][0] == 0.0 and any(1.0 < t < 1.3 and v != shake[0][1] for t, v in shake)
    gates = keys_of(root, "opacity")
    assert [(0.0, 1.0), (2.5, 0.0)] in gates  # the mounted phone leaves its mount
    assert [(0.0, 0.0), (2.5, 1.0)] in gates  # and lies face down on the dashboard
    assert [(0.0, 0.0), (1.0, 1.0), (1.35, 0.0)] in gates  # with buzz marks while it shakes
    quiet = canvas()
    stick_windshield.dashboard(quiet, quiet.comp, 4.0)
    assert keys_of(xml(quiet), "x") == [] and keys_of(xml(quiet), "opacity") == []


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda cv: stick_windshield.windshield(cv, cv.comp, 0.0), "length"),
        (lambda cv: stick_windshield.windshield(cv, cv.comp, math.inf), "length"),
        (lambda cv: stick_windshield.windshield(cv, cv.comp, 2.0, speed=-1.0), "speed"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, -1.0), "length"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, 2.0, buzz=(1.5, 0.5)), "buzz"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, 2.0, buzz=(3.0,)), "buzz"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, 2.0, down=2.0), "down"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, 2.0, down=-0.1), "down"),
        (lambda cv: stick_windshield.dashboard(cv, cv.comp, 2.0, buzz=(1.5,), down=1.0), "face down"),
    ],
)
def test_the_windshield_and_the_dashboard_refuse_what_they_cannot_show(call, match):
    with pytest.raises(StickDataError, match=match):
        call(canvas())
