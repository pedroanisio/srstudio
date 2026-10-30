"""Toon past the desk: the sofa that carries the signature anywhere, the plain ledge, the outdoor sets, and what
moves in a shot (the arm, the gull, the Zs). Every part refuses data it cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, signature, toon_rooms, toon_world
from srstudio.canvas import Signature
from srstudio.toon import ToonDataError


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def drawn(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def marks(monkeypatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(signature, "cactus", lambda *a, **k: calls.append("cactus"))
    monkeypatch.setattr(signature, "code", lambda *a, **k: calls.append("code"))
    return calls


@pytest.mark.parametrize("name", ["toon-sofa-back", "toon-far-wall", "toon-yard", "toon-dump", "toon-ledge"])
def test_each_set_piece_draws_with_no_data_of_its_own(name):
    entry = next(e for e in registry.entries() if e.name == name)
    cv = canvas()
    entry.builder(cv, cv.group(cv.comp, "g"))
    assert len(list(drawn(cv).find("composition").iter())) > 2


@pytest.mark.parametrize("ground", toon_world.GROUNDS)
def test_a_sofa_signs_once_on_every_ground(monkeypatch, ground):
    calls = marks(monkeypatch)
    cv = canvas()
    toon_world.sofa(cv, cv.group(cv.comp, "g"), ground)
    assert sorted(calls) == ["cactus", "code"]


def test_a_far_sofa_is_not_signed_a_second_time(monkeypatch):
    calls = marks(monkeypatch)
    cv = canvas()
    toon_world.sofa(cv, cv.group(cv.comp, "g"), signed=False)
    assert calls == []


def test_the_ledge_carries_both_marks(monkeypatch):
    calls = marks(monkeypatch)
    cv = canvas()
    toon_world.ledge(cv, cv.group(cv.comp, "g"))
    assert sorted(calls) == ["cactus", "code"]


def test_no_desk_draws_nothing():
    cv = canvas()
    toon_world.no_desk(cv, cv.group(cv.comp, "g"))
    assert not list(next(e for e in drawn(cv).iter("group") if e.get("id") == "g"))


def test_a_sofa_refuses_a_ground_it_does_not_have():
    cv = canvas()
    with pytest.raises(ToonDataError, match="stands on one of"):
        toon_world.sofa(cv, cv.group(cv.comp, "g"), "moon")


@pytest.mark.parametrize("scale", [0, -1.0, float("nan"), "big", None])
def test_placed_refuses_a_scale_that_is_not_positive(scale):
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale must be positive"):
        toon_world.placed(cv, cv.group(cv.comp, "g"), (0.0, 0.0), scale, lambda g: None)


def test_placed_scales_about_its_pivot():
    cv = canvas()
    held = []
    group = toon_world.placed(cv, cv.group(cv.comp, "g"), (430.0, 704.0), 0.5, held.append)
    assert held == [group]


@pytest.mark.parametrize(("start", "end"), [(-1.0, 2.0), (3.0, 3.0), (3.0, 1.0), (float("nan"), 2.0)])
def test_a_road_refuses_a_span_that_does_not_run_forward(start, end):
    cv = canvas()
    with pytest.raises(ToonDataError, match="a road scrolls"):
        toon_world.road(cv, cv.group(cv.comp, "g"), start, end)


def test_a_road_drifts_its_planes_at_their_own_speeds_inside_its_span():
    cv = canvas()
    toon_world.road(cv, cv.group(cv.comp, "g"), 1.0, 3.0)
    travels = {
        abs(float(keys[0].get("value")) - float(keys[-1].get("value")))
        for a in drawn(cv).iter("animate")
        if a.get("property") == "x"
        for keys in [list(a.iter("key"))]
    }
    layers = toon_world.RoadLayers
    assert len(travels) == 3 and max(travels) / min(travels) == pytest.approx(layers.POSTS / layers.HILLS, rel=1e-3)


@pytest.mark.parametrize(("land", "end"), [(0.1, 3.0), (2.0, 2.0), (2.0, 1.0)])
def test_a_gull_needs_its_flight_before_it_lands(land, end):
    cv = canvas()
    with pytest.raises(ToonDataError, match="to fly in"):
        toon_world.gull(cv, cv.group(cv.comp, "g"), land=land, end=end)


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"holding": "brick"}, "a paw holds"),
        ({"side": 0.0}, "from the right"),
        ({"spans": ((1.0, 1.1),)}, "for each span"),
        ({"spans": ((-1.0, 1.0),)}, "for each span"),
    ],
)
def test_a_paw_refuses_what_it_cannot_do(kw, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_world.paw(cv, cv.group(cv.comp, "g"), **kw)


@pytest.mark.parametrize("holding", ["remote", "note", ""])
def test_a_paw_comes_and_goes_inside_its_span(holding):
    cv = canvas()
    toon_world.paw(cv, cv.group(cv.comp, "g"), ((1.0, 2.0),), holding=holding, presses=(1.5,))
    groups = [g for g in drawn(cv).iter("group") if g.get("start")]
    assert groups and float(groups[0].get("start")) == 1.0 and float(groups[0].get("end")) == 2.0


def test_zs_rise_only_inside_their_spans():
    cv = canvas()
    toon_world.snores(cv, cv.group(cv.comp, "g"), ((1.0, 2.0), (4.0, 4.5)))
    starts = [float(g.get("start")) for g in drawn(cv).iter("group") if g.get("start")]
    assert starts and all(1.0 <= s < 2.0 or 4.0 <= s < 4.5 for s in starts)


@pytest.mark.parametrize("gone", toon_rooms.LOUNGE_BARE)
def test_the_lounge_can_lose_each_of_its_things(gone):
    whole, less = canvas(), canvas()
    toon_rooms.lounge(whole, whole.group(whole.comp, "g"), end=3.0)
    toon_rooms.lounge(less, less.group(less.comp, "g"), end=3.0, bare=(gone,))
    assert less.scene.to_bytes(layout="pretty") != whole.scene.to_bytes(layout="pretty")


def test_the_lounge_refuses_to_lose_what_it_does_not_have():
    cv = canvas()
    with pytest.raises(ToonDataError, match="the lounge can lose"):
        toon_rooms.lounge(cv, cv.group(cv.comp, "g"), end=3.0, bare=("sofa",))


def test_a_still_lounge_keys_no_router_light():
    blinking, still = canvas(), canvas()
    toon_rooms.lounge(blinking, blinking.group(blinking.comp, "g"), end=3.0)
    toon_rooms.lounge(still, still.group(still.comp, "g"), end=3.0, blink=False)
    assert len(list(drawn(still).iter("key"))) < len(list(drawn(blinking).iter("key")))
