"""The domestic Toon parts: a signed ledge in place of the desk, the one-line key line, the hallway and the horse each
keep the frame's rules, and each refuses what it cannot draw."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, Signature, flat_counter, registry, signature, toon_house
from srstudio.toon import ToonDataError


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("prop", "toon-ledge", toon_house.ledge),
        ("graphic", "toon-key-line", toon_house.key_line),
        ("location", "toon-hallway", toon_house.hallway),
        ("location", "toon-bathroom", toon_house.bathroom),
        ("prop", "toon-shower-water", toon_house.shower_water),
        ("prop", "toon-suds", toon_house.suds),
        ("prop", "toon-towel", toon_house.towel),
        ("prop", "toon-horse", toon_house.horse),
        ("prop", "toon-thermostat", toon_house.thermostat),
        ("prop", "toon-finger", toon_house.finger),
        ("prop", "toon-vent", toon_house.vent),
        ("location", "toon-bedroom", toon_house.bedroom),
        ("prop", "toon-quilt", toon_house.quilt),
        ("prop", "toon-sink", toon_house.sink),
        ("prop", "toon-day-card", toon_house.day_card),
        ("prop", "toon-watering-can", toon_house.watering_can),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    assert registry.get(kind, name).builder is builder


@pytest.mark.parametrize("finish", sorted(toon_house.LEDGES))
def test_a_ledge_carries_the_signature_marks_in_every_finish(finish):
    cv = canvas(signed=True)
    toon_house.ledge(cv, cv.comp, finish)
    assert signature.missing(cv.scene.to_bytes(layout="pretty")) == []


def test_a_ledge_refuses_a_finish_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a ledge is one of"):
        toon_house.ledge(cv, cv.comp, "marble")


def test_a_key_line_lasts_from_its_start_to_its_end_and_shows_its_words():
    cv = canvas()
    toon_house.key_line(cv, cv.comp, "Dad is asleep upstairs.", 0.0, 3.0, measure=measure)
    root = tree(cv)
    assert "Dad is asleep upstairs." in [t.get("text") for t in root.iter("text")]


@pytest.mark.parametrize(
    ("text", "start", "end", "match"),
    [
        ("", 0.0, 3.0, "1 to 34"),
        ("   ", 0.0, 3.0, "1 to 34"),
        ("x" * 35, 0.0, 3.0, "1 to 34"),
        ("Fine.", 3.0, 3.0, "start < end"),
        ("Fine.", -1.0, 3.0, "start < end"),
        ("Fine.", float("nan"), 3.0, "start < end"),
    ],
)
def test_a_key_line_refuses_text_or_a_clock_it_cannot_show(text, start, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.key_line(cv, cv.comp, text, start, end, measure=measure)


def test_a_key_line_refuses_to_run_past_the_margins():
    cv = canvas()
    with pytest.raises(ToonDataError, match="over the frame's margins"):
        toon_house.key_line(cv, cv.comp, "x" * 34, 0.0, 3.0, measure=lambda _text, size: 2.0 * size * 34)


@pytest.mark.parametrize("door", toon_house.DOORS)
def test_the_hallway_draws_with_its_door_shut_or_open(door):
    cv = canvas()
    toon_house.hallway(cv, cv.comp, door)
    assert list(tree(cv).iter("group"))


def test_the_hallway_door_differs_between_its_states():
    shut, opened = canvas(), canvas()
    toon_house.hallway(shut, shut.comp, "shut")
    toon_house.hallway(opened, opened.comp, "open")
    assert shut.scene.to_bytes(layout="pretty") != opened.scene.to_bytes(layout="pretty")


def test_the_hallway_refuses_a_door_state_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="door"):
        toon_house.hallway(cv, cv.comp, "ajar")


def test_a_still_horse_never_blinks_and_a_timed_one_does():
    still, timed = canvas(), canvas()
    toon_house.horse(still, still.comp)
    toon_house.horse(timed, timed.comp, end=8.0)
    assert still.scene.to_bytes(layout="pretty") != timed.scene.to_bytes(layout="pretty")


def test_a_horse_blinks_where_it_is_told():
    told, default = canvas(), canvas()
    toon_house.horse(told, told.comp, end=8.0, blinks=[2.0])
    toon_house.horse(default, default.comp, end=8.0)
    assert told.scene.to_bytes(layout="pretty") != default.scene.to_bytes(layout="pretty")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"scale": 0.1}, "scale"),
        ({"scale": 2.0}, "scale"),
        ({"at": (1,)}, "reference point"),
        ({"at": "here"}, "reference point"),
        ({"start": -1.0}, "start and end"),
        ({"end": -1.0}, "start and end"),
        ({"end": 8.0, "blinks": [3.0, 2.0]}, "blinks"),
    ],
)
def test_a_horse_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.horse(cv, cv.comp, **kwargs)


READINGS = [(0.0, "68"), (1.3, "69"), (6.0, "68")]


def test_a_thermostat_shows_each_reading_until_the_next():
    cv = canvas()
    toon_house.thermostat(cv, cv.comp, READINGS, 8.0)
    root = tree(cv)
    assert sorted(t.get("text") for t in root.iter("text")) == ["68", "68", "69"]
    spans = [(g.get("start"), g.get("end")) for g in root.iter("group") if g.get("start") is not None]
    assert spans == [("0", "1.3"), ("1.3", "6"), ("6", "8")]


def test_a_still_thermostat_takes_one_reading():
    cv = canvas()
    toon_house.thermostat(cv, cv.comp, [(0.0, "68")])
    assert [t.get("text") for t in tree(cv).iter("text")] == ["68"]


@pytest.mark.parametrize(
    ("readings", "end", "kwargs", "match"),
    [
        ([], 8.0, {}, "pairs"),
        (["68"], 8.0, {}, "pairs"),
        ([(1.0, "68")], 8.0, {}, "start at 0"),
        (READINGS, 0.0, {}, "start at 0"),
        ([(0.0, "68"), (9.0, "69")], 8.0, {}, "start at 0"),
        ([(0.0, "68"), (3.0, "69"), (2.0, "70")], 8.0, {}, "readings"),
        ([(0.0, "6")], 8.0, {}, "two digits"),
        ([(0.0, "hot")], 8.0, {}, "two digits"),
        ([(0.0, 68)], 8.0, {}, "two digits"),
        ([(0.0, "68")], 8.0, {"scale": 9.0}, "scale"),
        ([(0.0, "68")], 8.0, {"at": 3}, "reference point"),
    ],
)
def test_a_thermostat_refuses_what_it_cannot_show(readings, end, kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.thermostat(cv, cv.comp, readings, end, **kwargs)


def test_a_finger_glides_to_each_place_it_is_told():
    cv = canvas()
    toon_house.finger(cv, cv.comp, (300, 500), moves=[(2.0, 320, 480)], end=4.0)
    root = tree(cv)
    assert {a.get("property") for a in root.iter("animate")} >= {"x", "y"}


def test_a_finger_shows_only_from_its_start_to_its_end():
    cv = canvas()
    toon_house.finger(cv, cv.comp, start=2.0, end=3.0)
    group = next(g for g in tree(cv).iter("group") if g.get("id") == "finger")
    assert (group.get("start"), group.get("end")) == ("2", "3")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"tip": (1,)}, "reference point"),
        ({"angle": float("nan")}, "angle"),
        ({"start": -1.0}, "start and end"),
        ({"moves": [(1.0, 2, 3)]}, "still finger"),
        ({"moves": [(2.0, 2, 3), (1.0, 2, 3)], "end": 4.0}, "moves"),
    ],
)
def test_a_finger_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.finger(cv, cv.comp, **kwargs)


@pytest.mark.parametrize(("kwargs", "match"), [({"at": "x"}, "reference point"), ({"width": 300.0}, "120 to 240")])
def test_a_vent_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.vent(cv, cv.comp, **kwargs)


@pytest.mark.parametrize("pattern", sorted(toon_house.QUILTS))
def test_a_quilt_carries_the_signature_marks_in_every_pattern(pattern):
    cv = canvas(signed=True)
    toon_house.quilt(cv, cv.comp, pattern)
    assert signature.missing(cv.scene.to_bytes(layout="pretty")) == []


def test_a_quilt_refuses_a_pattern_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a quilt is one of"):
        toon_house.quilt(cv, cv.comp, "tartan")


def test_the_hallway_can_be_plain_wall_with_no_door():
    plain, shut = canvas(), canvas()
    toon_house.hallway(plain, plain.comp, "none")
    toon_house.hallway(shut, shut.comp, "shut")
    assert len(plain.scene.to_bytes(layout="pretty")) < len(shut.scene.to_bytes(layout="pretty"))


def test_the_bedroom_draws():
    cv = canvas()
    toon_house.bedroom(cv, cv.comp)
    assert list(tree(cv).iter("group"))


@pytest.mark.parametrize(
    "stages", [(), ((1.0, "skin"),), ((1.0, "skin"), (2.0, "plant"), (3.0, "mail"), (4.0, "frog"))]
)
def test_a_sink_carries_the_signature_marks_at_every_stage(stages):
    cv = canvas(signed=True)
    toon_house.sink(cv, cv.comp, stages, 8.0)
    assert signature.missing(cv.scene.to_bytes(layout="pretty")) == []


def test_each_stage_of_a_pan_comes_at_its_second_and_stays():
    cv = canvas()
    toon_house.sink(cv, cv.comp, [(1.0, "skin"), (4.0, "frog")], 8.0)
    starts = {g.get("id"): (g.get("start"), g.get("end")) for g in tree(cv).iter("group") if g.get("start")}
    assert starts == {"sink-skin": ("1", "8"), "sink-frog": ("4", "8")}


def test_the_tiny_frog_waves_only_in_a_timed_sink():
    moving, still = canvas(), canvas()
    toon_house.sink(moving, moving.comp, [(1.0, "frog")], 8.0)
    toon_house.sink(still, still.comp, [(0.0, "frog")])
    assert [a.get("property") for a in tree(moving).iter("animate")] == ["rotation"]
    assert list(tree(still).iter("animate")) == []


@pytest.mark.parametrize(
    ("stages", "end", "match"),
    [
        ([(1.0, "moss")], 8.0, "stages come in the order"),
        ([(1.0, "frog"), (2.0, "skin")], 8.0, "stages come in the order"),
        ([(1.0, "skin"), (2.0, "skin")], 8.0, "stages come in the order"),
        ([(2.0, "skin"), (1.0, "plant")], 8.0, "stages"),
        ([(9.0, "skin")], 8.0, "before its end"),
    ],
)
def test_a_sink_refuses_stages_a_pan_cannot_grow(stages, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.sink(cv, cv.comp, stages, end)


def test_a_day_card_shows_each_day_until_the_next():
    cv = canvas()
    toon_house.day_card(cv, cv.comp, [(0.0, 1), (3.0, 60)], 8.0)
    assert sorted(t.get("text") for t in tree(cv).iter("text")) == ["1", "60", "DAY"]


@pytest.mark.parametrize(
    ("days", "end", "match"),
    [
        ([], 8.0, "pairs"),
        ([(1.0, 1)], 8.0, "start at 0"),
        ([(0.0, 1), (9.0, 2)], 8.0, "start at 0"),
        ([(0.0, 1), (1.0, 2)], 0.0, "start at 0"),
        ([(0.0, 0)], 8.0, "1 to 999"),
        ([(0.0, 1000)], 8.0, "1 to 999"),
        ([(0.0, True)], 8.0, "1 to 999"),
        ([(0.0, "1")], 8.0, "1 to 999"),
    ],
)
def test_a_day_card_refuses_days_it_cannot_show(days, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.day_card(cv, cv.comp, days, end)


def test_a_watering_can_drips_only_while_it_pours():
    cv = canvas()
    toon_house.watering_can(cv, cv.comp, start=1.0, end=4.0, pour=2.0)
    falling = [g for g in tree(cv).iter("group") if g.find("animate") is not None]
    assert len(falling) == 3 and all(g.get("start") == "2" for g in falling)


def test_a_still_watering_can_has_no_drops():
    cv = canvas()
    toon_house.watering_can(cv, cv.comp)
    assert list(tree(cv).iter("animate")) == []


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"at": "x"}, "reference point"),
        ({"start": -1.0}, "times >= 0"),
        ({"start": 1.0, "end": 4.0, "pour": 5.0}, "pours within"),
    ],
)
def test_a_watering_can_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.watering_can(cv, cv.comp, **kwargs)


def test_a_tee_is_registered_and_carries_its_invented_print():
    cv = canvas()
    toon_house.tee(cv, cv.comp, (200, 660))
    assert registry.get("prop", "toon-tee").builder is toon_house.tee
    assert tree(cv).findall(".//*")
    assert not [n for n in tree(cv).iter() if n.tag.endswith("text")]  # a picture only: no name, no slogan, no brand


def test_a_tee_scales_about_its_collar():
    cv = canvas()
    toon_house.tee(cv, cv.comp, (200, 660), scale=0.5)
    group = next(n for n in tree(cv).iter() if n.get("id") == "tee")
    assert float(group.get("scaleX")) == float(group.get("scaleY")) == 0.5


def test_a_tee_can_keep_to_a_span_of_time():
    cv = canvas()
    toon_house.tee(cv, cv.comp, (200, 660), start=1.0, end=3.0)
    group = next(n for n in tree(cv).iter() if n.get("id") == "tee")
    assert (float(group.get("start")), float(group.get("end"))) == (1.0, 3.0)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"at": (1,)}, "a tee's place"),
        ({"at": "here"}, "a tee's place"),
        ({"at": (1, 2), "scale": 0.0}, "a tee's scale"),
        ({"at": (1, 2), "colour": "lime"}, "a tee's colour"),
    ],
)
def test_a_tee_refuses_bad_data(kwargs, match):
    cv = canvas()
    args = dict(kwargs)
    with pytest.raises(ToonDataError, match=match):
        toon_house.tee(cv, cv.comp, args.pop("at"), **args)


def test_a_bathroom_is_a_set_with_no_lettering():
    cv = canvas()
    toon_house.bathroom(cv, cv.comp)
    assert tree(cv).findall(".//*")
    assert not [n for n in tree(cv).iter() if n.tag.endswith("text")]


def water(cv) -> list:
    return [n for n in tree(cv).iter() if (n.get("id") or "").startswith("water-")]


def test_water_runs_only_in_its_spans():
    cv = canvas()
    toon_house.shower_water(cv, cv.comp, [(0.0, 0.4), (1.7, 3.0)])
    assert [(float(g.get("start")), float(g.get("end"))) for g in water(cv)] == [(0.0, 0.4), (1.7, 3.0)]


def test_water_falls_for_as_long_as_it_runs():
    cv = canvas()
    toon_house.shower_water(cv, cv.comp, [(1.0, 3.0)])
    tracks = [n for n in tree(cv).iter() if n.tag.endswith("animate") and n.get("property") == "opacity"]
    assert len(tracks) == toon_house.WATER_PHASES
    for track in tracks:
        times = [float(k.get("time")) for k in track]
        assert times[0] == 1.0 and times[-1] == 3.0
        assert len(times) > 2 * (3.0 - 1.0) / toon_house.WATER_PERIOD  # it flickers down; it does not hold


def test_water_starts_at_the_rose_and_never_above_it():
    assert toon_house.water_dashes(100.0, 0) == toon_house.water_dashes(100.0, 0)
    rose_x, rose_y = toon_house.SHOWER_HEAD
    for phase in range(toon_house.WATER_PHASES):
        dashes = toon_house.water_dashes(40.0, phase)
        assert dashes and all(y >= rose_y for (_, y), _ in dashes)
        assert all(x <= rose_x for (x, _), _ in dashes)


def test_water_in_the_clear_span_stops_where_it_is_told():
    assert all(y <= 300.0 for dash in toon_house.water_dashes(250.0, 1, 300.0) for _, y in dash)
    cv, dry = canvas(), canvas()
    toon_house.shower_water(cv, cv.comp, [(0.0, 2.0)], clear=(120.0, 300.0), stop=300.0)
    toon_house.shower_water(dry, dry.comp, [(0.0, 2.0)], clear=(120.0, 300.0))
    assert len(list(tree(cv).iter())) > len(list(tree(dry).iter()))


def test_water_keeps_off_the_span_it_is_told_to_clear():
    cv = canvas()
    toon_house.shower_water(cv, cv.comp, [(0.0, 2.0)], clear=(120.0, 300.0))
    drawn = cv.scene.to_bytes(layout="pretty")
    assert all(not 120.0 <= x <= 300.0 for x in toon_house.streaks((120.0, 300.0)))
    assert drawn
    assert len(toon_house.streaks((120.0, 300.0))) < len(toon_house.streaks(None))


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"spans": []}, "at least one span"),
        ({"spans": [(2.0, 1.0)]}, "rising"),
        ({"spans": [(0.0, 2.0), (1.0, 3.0)]}, "rising"),
        ({"spans": [(0.0, 1.0)], "clear": (5.0, 1.0)}, "clear"),
    ],
)
def test_water_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.shower_water(cv, cv.comp, **kwargs)


@pytest.mark.parametrize("builder", [toon_house.suds, toon_house.towel])
def test_what_a_head_wears_in_the_bathroom_scales_about_its_place_and_keeps_to_its_span(builder):
    cv = canvas()
    builder(cv, cv.comp, (200, 500), scale=0.5, start=1.0, end=3.0, id="worn")
    group = next(n for n in tree(cv).iter() if n.get("id") == "worn")
    assert float(group.get("scaleX")) == float(group.get("scaleY")) == 0.5
    assert (float(group.get("start")), float(group.get("end"))) == (1.0, 3.0)
    assert not [n for n in tree(cv).iter() if n.tag.endswith("text")]


@pytest.mark.parametrize("builder", [toon_house.suds, toon_house.towel])
@pytest.mark.parametrize(
    ("kwargs", "match"), [({"at": "x"}, "reference point"), ({"at": (200, 500), "scale": 0}, "scale")]
)
def test_what_a_head_wears_in_the_bathroom_refuses_what_it_cannot_draw(builder, kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        builder(cv, cv.comp, **kwargs)
