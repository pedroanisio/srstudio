"""The Stick road ahead and the phone that gives directions on it."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, Signature, flat_counter, registry, stick, stick_satnav
from srstudio.canvas import CanvasError


def canvas(*, font: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter" if font else None, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animated(cv: Canvas) -> set[str]:
    return {a.get("property") or "" for a in xml(cv).iter("animate")}


def test_the_set_and_its_prop_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {("location", "stick-rough-road"), ("prop", "stick-nav-insert")} <= names


@pytest.mark.parametrize(
    "draw", [lambda cv: stick_satnav.ahead(cv, cv.comp, 2.0), lambda cv: stick_satnav.nav_insert(cv, cv.comp, 2.0)]
)
def test_each_shot_carries_both_signature_marks(draw):
    cv = canvas()
    cv.signature = Signature()
    draw(cv)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


@pytest.mark.parametrize("surface", stick_satnav.SURFACES)
def test_every_surface_runs_at_the_camera(surface):
    cv = canvas()
    stick_satnav.ahead(cv, cv.comp, 2.0, surface=surface)
    assert {"scaleX", "scaleY"} <= animated(cv)


def test_only_a_bad_surface_shakes_the_frame():
    smooth, rough = canvas(), canvas()
    stick_satnav.ahead(smooth, smooth.comp, 2.0, surface="street")
    stick_satnav.ahead(rough, rough.comp, 2.0, surface="grass")
    assert "y" not in animated(smooth) and "y" in animated(rough)


def test_the_marks_land_on_themselves_after_one_pass():
    assert stick_satnav._depth(1) * stick_satnav.GROW == pytest.approx(stick_satnav._depth(0))


def test_the_ground_stops_when_the_fence_is_reached():
    cv = canvas()
    stick_satnav.ahead(cv, cv.comp, 4.0, surface="grass", fence=2.0)
    times = [float(k.get("t") or k.get("time") or 0) for k in xml(cv).iter("key")]
    assert not times or max(times) <= 2.0 + 1 / stick_satnav.RATE["grass"]


@pytest.mark.parametrize(
    ("kw", "match"), [(dict(surface="sea"), "surface"), (dict(fence=0), "fence"), (dict(fence=9.0), "fence")]
)
def test_a_road_that_cannot_be_drawn_is_refused(kw, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick_satnav.ahead(cv, cv.comp, 2.0, **kw)


@pytest.mark.parametrize("draw", [stick_satnav.ahead, stick_satnav.nav_insert])
@pytest.mark.parametrize("end", [0, -1.0, float("nan")])
def test_a_shot_with_no_length_is_refused(draw, end):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="positive shot length"):
        draw(cv, cv.comp, end)


@pytest.mark.parametrize("screen", sorted(stick_satnav.SCREENS))
def test_every_screen_draws_and_its_words_fit_the_banner(screen):
    cv = canvas()
    stick_satnav.nav_insert(cv, cv.comp, 2.0, screen=screen, buzz=(0.1,))
    assert len(stick_satnav.SCREENS[screen].words) <= 20
    assert "x" in animated(cv)


def test_recalculating_spins():
    cv = canvas()
    stick_satnav.nav_insert(cv, cv.comp, 2.0, screen="recalculating")
    assert "rotation" in animated(cv)


def test_an_unknown_screen_a_stray_buzz_and_a_silent_canvas_are_refused():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="screen"):
        stick_satnav.nav_insert(cv, cv.comp, 2.0, screen="tv")
    with pytest.raises(stick.StickDataError, match="buzz"):
        stick_satnav.nav_insert(cv, cv.comp, 2.0, buzz=(5.0,))
    silent = canvas(font=False)
    with pytest.raises(CanvasError, match="instruction"):
        stick_satnav.nav_insert(silent, silent.comp, 2.0)


def test_the_phone_stays_clear_of_the_bug_box_and_the_caption_band():
    assert stick_satnav.SCREEN_X + stick_satnav.SCREEN_W + 26 < 926
    assert stick_satnav.SCREEN_Y + stick_satnav.SCREEN_H + 56 < 1600


def test_the_pointing_pose_reaches_across_toward_the_driver():
    from srstudio import stick_windshield as ws

    x, _ = stick.hand_at(stick_satnav.POSES["point"], at=ws.PASSENGER_AT)
    assert ws.SEATS[0] < x < ws.SEATS[1]
