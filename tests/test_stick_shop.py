"""The Stick shop: the self-checkout set, the kiosk and its screens, the avocado and the name badge."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_shop


def canvas(font: str | None = "inter") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [t.get("text") for t in xml(cv).iter("text")]


def gates(root: ET.Element) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
        if a.get("property") == "opacity"
    ]


SCREENS = (
    stick_shop.Screen(0.0, "Place item in the bagging area"),
    stick_shop.Screen(1.0, "Unexpected item in the bagging area", "error"),
    stick_shop.Screen(2.0, "Employee of the month", "award", face=stick.Look(apron="#2f7d57")),
)


def test_the_parts_are_registered_for_the_stick_style():
    for kind, name in (("location", "stick-checkout"), ("prop", "stick-kiosk"), ("prop", "stick-avocado"),
                       ("prop", "stick-name-badge")):  # fmt: skip
        assert registry.get(kind, name).style == "stick"


def test_the_checkout_draws_the_store_with_its_sign_and_signature():
    cv = canvas()
    stick_shop.checkout(cv, cv.comp)
    assert "SELF-CHECKOUT" in texts(cv)
    paths = [s.get("path") or "" for s in xml(cv).iter("shape")]
    assert len(paths) > 60  # shelves of stock, lights, tiles, the bagging shelf
    with pytest.raises(ValueError, match="font"):
        stick_shop.checkout(canvas(None), None)


def test_each_screen_holds_until_the_next_in_its_tone():
    cv = canvas()
    stick_shop.kiosk(cv, cv.comp, SCREENS, 3.0)
    root = xml(cv)
    assert [t for t in texts(cv) if t in {s.text for s in SCREENS}] == [s.text for s in SCREENS]
    fills = [s.get("fill") for s in root.iter("shape")]
    assert stick_shop.TONES["error"] in fills and stick_shop.TONES["award"] in fills
    spans = [g for g in gates(root) if g]
    assert any(k[0] == (0.0, 1.0) and (1.0, 0.0) in k for k in spans)  # the first screen until 1 s
    assert any((2.0, 1.0) in k for k in spans)  # the award from 2 s to the end
    heads = [e for e in root.iter("shape") if e.get("shape") == "ellipse" and e.get("fill") == stick.SKIN]
    assert len(heads) == 1  # the award shows the employee's face


def test_the_lamp_flashes_red_at_each_alarm():
    cv = canvas()
    stick_shop.kiosk(cv, cv.comp, SCREENS[:1], 3.0, alarm=(0.5, 2.0))
    lamp = [g for g in gates(xml(cv)) if g]
    assert len(lamp) == 2
    assert all(any(v == 1.0 for _, v in k) and any(v == 0.0 for _, v in k) for k in lamp)
    quiet = canvas()
    stick_shop.kiosk(quiet, quiet.comp, SCREENS[:1], 3.0)
    assert [g for g in gates(xml(quiet)) if g] == []  # one screen and no alarm: nothing animates


@pytest.mark.parametrize(
    ("screens", "alarm", "match"),
    [
        ((), (), "a screen at 0"),
        ((stick_shop.Screen(0.5, "Hi"),), (), "a screen at 0"),
        ((stick_shop.Screen(0.0, "Hi"), stick_shop.Screen(0.0, "Again")), (), "time order"),
        ((stick_shop.Screen(0.0, "Hi"), stick_shop.Screen(3.0, "Late")), (), "end"),
        ((stick_shop.Screen(0.0, " "),), (), "text"),
        ((stick_shop.Screen(0.0, "x" * (stick_shop.SCREEN_CHARS + 1)),), (), "text"),
        ((stick_shop.Screen(0.0, "Hi", "angry"),), (), "tone"),
        ((stick_shop.Screen(0.0, "Hi", face=stick.Look(hair="mohawk")),), (), "hair"),
        ((stick_shop.Screen(0.0, "Hi"),), (4.0,), "alarm"),
        ((stick_shop.Screen(0.0, "Hi"),), (2.0, 1.0), "alarm"),
    ],
)
def test_the_kiosk_refuses_what_its_screen_cannot_show(screens, alarm, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick_shop.kiosk(canvas(), None, screens, 3.0, alarm=alarm)


def test_the_kiosk_needs_a_positive_length():
    with pytest.raises(stick.StickDataError, match="length"):
        stick_shop.kiosk(canvas(), None, SCREENS[:1], 0.0)


@pytest.mark.parametrize(("screens", "alarm", "match"), [((stick_shop.Screen(0.0, "Hi"),), (-1.0,), "alarm")])
def test_the_kiosk_refuses_an_alarm_before_the_shot(screens, alarm, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick_shop.kiosk(canvas(), None, screens, 3.0, alarm=alarm)


def test_the_kiosk_needs_a_font():
    with pytest.raises(ValueError, match="font"):
        stick_shop.kiosk(canvas(None), None, SCREENS, 3.0)


def test_the_checkout_signs_itself():
    from srstudio.canvas import Signature

    signed = Canvas(Scene(version="auto"), DAYLIGHT, font_asset="inter", signature=Signature())
    stick_shop.checkout(signed, signed.comp)
    ids = [g.get("id") or "" for g in xml(signed).iter("group")]
    assert any(i.startswith("sig-cactus") for i in ids) and any(i.startswith("sig-code") for i in ids)


def test_the_avocado_sits_on_its_point_at_its_scale():
    cv = canvas()
    stick_shop.avocado(cv, cv.comp, 490, 1090, scale=1.5)
    (g,) = [g for g in xml(cv).iter("group") if g.get("x") == "490" and g.get("y") == "1090"]
    assert g.get("scaleX") == "1.5"
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_shop.avocado(cv, cv.comp, 0, 0, scale=0)


def test_the_name_badge_letters_its_name_and_title():
    cv = canvas()
    stick_shop.name_badge(cv, cv.comp, 520, 980, "DEV", "Employee of the month")
    assert texts(cv) == ["DEV", "Employee of the month"]
    for name, title in (("", "x"), ("DEV", " ")):
        with pytest.raises(stick.StickDataError, match="badge"):
            stick_shop.name_badge(cv, cv.comp, 0, 0, name, title)
    with pytest.raises(ValueError, match="font"):
        stick_shop.name_badge(canvas(None), None, 0, 0, "DEV", "x")


def test_a_hand_carries_the_item_where_the_pose_puts_it():
    pose = stick.STANDING["wave"]
    x, y = stick_shop.hand(pose, at=stick_shop.SHOPPER_AT)
    assert (x, y) == (pose.hands[1][0] + stick_shop.SHOPPER_AT[0], pose.hands[1][1] + stick_shop.SHOPPER_AT[1])
    fx, _ = stick_shop.hand(pose, at=stick_shop.CLERK_AT, flip=True)
    assert fx == stick_shop.CLERK_AT[0] - pose.hands[1][0]
