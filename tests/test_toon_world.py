"""Toon past the desk: the sofa that carries the signature anywhere, the plain ledge, the outdoor sets, and what
moves in a shot (the arm, the gull, the Zs). Every part refuses data it cannot draw."""

import json
import subprocess
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


@pytest.mark.parametrize("name", ["toon-sofa-back", "toon-far-wall", "toon-yard", "toon-dump", "toon-worktop"])
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


def test_the_street_refuses_more_leavers_than_figures_and_a_late_leaver():
    cv = canvas()
    with pytest.raises(ToonDataError, match="cannot leave"):
        toon_world.night_street(cv, cv.group(cv.comp, "g"), [1.0] * (len(toon_world.CROWD) + 1), 6.0)
    with pytest.raises(ToonDataError, match="to leave before"):
        toon_world.night_street(cv, cv.group(cv.comp, "g"), [5.9], 6.0)


def test_a_leaver_reads_before_it_walks_and_stays_gone():
    cv = canvas()
    toon_world.night_street(cv, cv.group(cv.comp, "g"), [1.0], 6.0)
    root = drawn(cv)
    assert sum(1 for g in root.iter("group") if g.get("end")) == 2
    moved = [a for a in root.iter("animate") if a.get("property") == "x"]
    assert len(moved) == 1 and float(next(moved[0].iter("key")).get("time")) == pytest.approx(1.0 + toon_world.READ)


def test_a_flash_goes_at_each_listed_time():
    cv = canvas()
    toon_world.press_room(cv, cv.group(cv.comp, "g"), (1.0, 2.0))
    assert [float(g.get("start")) for g in drawn(cv).iter("group") if g.get("start")] == [1.0, 2.0]


def test_a_lower_third_refuses_text_that_does_not_fit_or_is_blank():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    with pytest.raises(ToonDataError, match="lower third"):
        toon_world.lower_third(cv, g, [(0.0, 1.0, "   ")], lambda t, s: 10.0)
    with pytest.raises(ToonDataError, match="lower third"):
        toon_world.lower_third(cv, g, [(0.0, 1.0, "wide")], lambda t, s: float(cv.width))


def test_a_helicopter_needs_a_second():
    cv = canvas()
    with pytest.raises(ToonDataError, match="needs a second"):
        toon_world.chopper(cv, cv.group(cv.comp, "g"), 1.0, 1.5)


def test_the_helicopter_can_light_a_group_in_front_of_the_character():
    cv = canvas()
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    toon_world.chopper(cv, back, 0.0, 2.0, over=front)
    assert list(next(g for g in drawn(cv).iter("group") if g.get("id") == "front"))


def test_a_paw_takes_as_long_as_it_is_told_to_arrive():
    cv = canvas()
    toon_world.paw(cv, cv.group(cv.comp, "g"), ((1.0, 5.0),), slide=2.0, holding="")
    with pytest.raises(ToonDataError, match="a paw needs 4.0 s"):
        toon_world.paw(cv, cv.group(cv.comp, "g"), ((1.0, 4.0),), slide=2.0, holding="")


def test_a_paw_from_the_left_carries_its_note_ahead_of_the_hand():
    def note_x(side: float) -> float:
        cv = canvas()
        toon_world.paw(cv, cv.group(cv.comp, "g"), ((0.0, 2.0),), side=side, reach=300.0, holding="note")
        notes = [e for e in drawn(cv).iter() if e.get("fill") == toon_world.SLIP]
        assert len(notes) == 1
        return float(notes[0].get("x"))

    assert note_x(-1.0) > toon_world.fx(270.0 + 20.0) - 1
    assert note_x(1.0) < toon_world.fx(320.0)


def test_a_yard_can_leave_its_sign_out():
    cv = canvas()
    toon_world.yard(cv, cv.group(cv.comp, "g"), sign=None, table=False)
    assert "YARD SALE" not in cv.scene.to_bytes(layout="pretty").decode()


@pytest.mark.parametrize("start, end", [(1.0, 1.1), (-1.0, 2.0), (2.0, 1.0)])
def test_a_van_needs_time_to_leave(start, end):
    cv = canvas()
    with pytest.raises(ToonDataError, match="a van drives off"):
        toon_world.van(cv, cv.group(cv.comp, "g"), start, end)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"text": ""}, "1 to 40"),
        ({"text": "x" * 41}, "1 to 40"),
        ({"start": 1.0, "end": 1.2}, "to arrive"),
        ({"start": -1.0, "end": 2.0}, "to arrive"),
    ],
)
def test_a_slip_refuses_what_it_cannot_show(kw, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_world.missed_slip(cv, cv.group(cv.comp, "g"), **kw)


def test_a_slip_keeps_its_words_back_until_it_has_arrived():
    cv = canvas()
    toon_world.missed_slip(cv, cv.group(cv.comp, "g"), "Sorry", 1.0, 3.0)
    starts = [float(g.get("start")) for g in drawn(cv).iter("group") if g.get("start")]
    assert 1.0 + toon_world.SLIP_SLIDE in starts


@pytest.mark.parametrize(
    "kw, match",
    [({"text": " "}, "1 to 40"), ({"start": -1.0}, "goes on at"), ({"start": 2.0, "stuck": 1.0}, "goes on at")],
)
def test_a_note_refuses_what_it_cannot_show(kw, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_world.stuck_note(cv, cv.group(cv.comp, "g"), **kw)


def test_a_note_riding_a_paw_is_blank_until_it_lands():
    cv = canvas()
    toon_world.stuck_note(cv, cv.group(cv.comp, "g"), "Hi", 1.0, 3.0)
    assert 3.0 in [float(g.get("start")) for g in drawn(cv).iter("group") if g.get("start")]


def test_a_chair_and_a_porch_draw():
    cv = canvas()
    toon_world.hall_chair(cv, cv.group(cv.comp, "g"))
    toon_world.porch(cv, cv.group(cv.comp, "g"))
    assert len(list(drawn(cv).iter())) > 20


def test_a_frozen_room_light_level_does_not_change(tmp_path, scene_render):
    """Moved from the episodes repository (ADR 0225): a light level drawn on a frozen canvas keeps its first value."""
    cv = canvas(signed=True)
    with cv.frozen():
        group = toon_rooms._level(cv, cv.comp, [(0, 0.0, "hold"), (0.5, 1.0, "hold")])
    path = tmp_path / "level.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    values = []
    for time in (0, 1):
        output = subprocess.run(
            [str(scene_render), "eval", str(path), "--time", str(time), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)["result"]["nodes"]
        values.append(next(n["opacity"] for n in nodes if n["id"] == group.id))
    assert values == pytest.approx([0, 0])
