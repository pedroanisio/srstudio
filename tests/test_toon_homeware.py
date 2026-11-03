"""Toon homeware: each part is registered, draws what its data says and refuses what cannot be drawn."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import Canvas, registry, toon, toon_homeware
from support.toon_props import canvas

PARTS = (
    "toon-baby-monitor",
    "toon-blower",
    "toon-cupcakes",
    "toon-device-list",
    "toon-dishwasher",
    "toon-lasagna",
    "toon-monitor-receiver",
    "toon-mower",
    "toon-profile-list",
    "toon-rack",
    "toon-scribble",
    "toon-shampoo",
    "toon-soup-tubs",
    "toon-swing-door",
    "toon-plate-of-toast",
)


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def words(cv: Canvas) -> list[str]:
    return ["".join(t.itertext()).strip() or t.get("text", "") for t in tree(cv).iter("text")]


def scene(cv: Canvas) -> bytes:
    return cv.scene.to_bytes(layout="pretty")


def size(draw) -> int:
    cv = canvas()
    draw(cv)
    return len(scene(cv))


@pytest.mark.parametrize("name", PARTS)
def test_every_part_is_registered(name):
    assert ("prop", name) in {(e.kind, e.name) for e in registry.entries()}


def test_a_dishwasher_draws_one_more_dish_for_each_load():
    empty = size(lambda cv: toon_homeware.dishwasher(cv, cv.comp, end=4.0))
    loaded = size(lambda cv: toon_homeware.dishwasher(cv, cv.comp, loads=(1.0, 2.0), end=4.0))
    assert loaded > empty


def test_a_full_dishwasher_refuses_the_next_dish():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="dishes"):
        toon_homeware.dishwasher(cv, cv.comp, loads=tuple(float(i) for i in range(1, 40)), end=50.0)


@pytest.mark.parametrize("loads", [(2.0, 1.0), (-1.0,), (1.0, 1.0)])
def test_loads_rise_from_zero(loads):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="rise"):
        toon_homeware.dishwasher(cv, cv.comp, loads=loads, end=4.0)


def test_a_dish_never_lands_after_the_dishwasher_has_gone():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="end"):
        toon_homeware.dishwasher(cv, cv.comp, loads=(3.0,), end=2.0)


@pytest.mark.parametrize("rows", [0, 5, 1.5, "2"])
def test_a_rack_has_one_to_four_rows(rows):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="rows"):
        toon_homeware.rack(cv, cv.comp, rows=rows)


def test_a_rack_rolls_inside_its_time_on_screen():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="rolls"):
        toon_homeware.rack(cv, cv.comp, roll=(1.0, 9.0), start=0.0, end=2.0)


def test_a_receiver_stays_up_through_its_last_pulse():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="pulse"):
        toon_homeware.monitor_receiver(cv, cv.comp, pulses=(3.0,), end=2.0)


def test_a_door_stays_up_through_its_last_close():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="close"):
        toon_homeware.swing_door(cv, cv.comp, opens=((3.0, 4.0),), end=2.0)


@pytest.mark.parametrize("spans", [((2.0, 1.0),), ((1.0, 3.0), (2.0, 4.0)), ((1.0,),)])
def test_door_spans_rise_and_do_not_overlap(spans):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="pairs|rise"):
        toon_homeware.swing_door(cv, cv.comp, opens=spans, end=9.0)


@pytest.mark.parametrize(("rows", "cols"), [(0, 2), (7, 2), (2, 0), (2, 7)])
def test_a_tray_is_one_to_six_by_one_to_six(rows, cols):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="tray"):
        toon_homeware.cupcakes(cv, cv.comp, rows=rows, cols=cols)


def test_cupcakes_leave_after_they_arrive():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="leave"):
        toon_homeware.cupcakes(cv, cv.comp, start=3.0, end=3.0)


def test_a_bottle_only_gives_a_bubble_when_asked():
    assert size(lambda cv: toon_homeware.shampoo(cv, cv.comp, bubble=1.0)) > size(
        lambda cv: toon_homeware.shampoo(cv, cv.comp)
    )


def test_a_bubble_comes_at_a_time():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="bubble"):
        toon_homeware.shampoo(cv, cv.comp, bubble="soon")


@pytest.mark.parametrize("counts", [(), ((1.0, 0),), ((0.0, 1),) * 1 + ((1.0, 99),)])
def test_a_stack_of_tubs_is_bounded(counts):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="stack"):
        toon_homeware.soup_tubs(cv, cv.comp, counts=counts, end=9.0)


def test_a_profile_screen_prints_each_name():
    cv = canvas()
    toon_homeware.profile_list(cv, cv.comp, ("Mia", "Brock", "Guest"))
    assert {"Mia", "Brock", "Guest"} <= set(words(cv))


@pytest.mark.parametrize("names", [(), ("a",) * 7])
def test_a_profile_screen_holds_one_to_six(names):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="rows"):
        toon_homeware.profile_list(cv, cv.comp, names)


@pytest.mark.parametrize("name", ["", "A name far too long for its tile on a phone"])
def test_a_profile_name_must_fit(name):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="characters"):
        toon_homeware.profile_list(cv, cv.comp, (name,))


def test_a_profile_screen_is_a_list_of_round_avatars_under_its_own_words():
    cv = canvas()
    toon_homeware.profile_list(cv, cv.comp, ("Mia", "Brock"))
    drawn = cv.scene.to_bytes().decode()
    assert "Who's on the couch?" in drawn and "Who's watching" not in drawn
    assert toon_homeware.AVATARS[0] in drawn and toon_homeware.AVATARS[1] in drawn
    assert toon_homeware.AVATARS[2] not in drawn, "one avatar a name"
    assert toon_homeware.DARK_SCREEN[0] not in drawn, "no dark page behind them"


def test_a_device_list_stays_dark_unless_given_other_paints():
    dark, pale = canvas(), canvas()
    toon_homeware.device_list(dark, dark.comp)
    toon_homeware.device_list(pale, pale.comp, paints=toon_homeware.LIGHT_SCREEN)
    drawn = dark.scene.to_bytes().decode()
    assert toon_homeware.DARK_SCREEN[0] in drawn and toon_homeware.DARK_SCREEN[0] not in pale.scene.to_bytes().decode()


def test_a_door_draws_legs_on_its_guest_only_when_asked():
    plain, legged = canvas(), canvas()
    toon_homeware.swing_door(plain, plain.comp, opens=((1.0, 2.0),), end=4.0)
    toon_homeware.swing_door(legged, legged.comp, opens=((1.0, 2.0),), end=4.0, legs=True)
    assert len(legged.scene.to_bytes()) > len(plain.scene.to_bytes())


def test_a_device_list_holds_one_to_four_rows():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="rows"):
        toon_homeware.device_list(cv, cv.comp, rows=())


@pytest.mark.parametrize("draw", [toon_homeware.profile_list, toon_homeware.device_list])
def test_a_screen_leaves_after_it_arrives(draw):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="leaves"):
        draw(cv, cv.comp, start=4.0, end=2.0)


@pytest.mark.parametrize("width", [100, 600, "wide"])
def test_a_scribble_has_a_width_a_caption_could_have(width):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="wide"):
        toon_homeware.scribble(cv, cv.comp, ((0.0, 1.0),), width=width)


@pytest.mark.parametrize("draw", [toon_homeware.mower, toon_homeware.blower])
def test_a_garden_tool_shudders_only_while_it_runs(draw):
    still = size(lambda cv: draw(cv, cv.comp))
    assert size(lambda cv: draw(cv, cv.comp, running=((1.0, 2.0),))) > still


@pytest.mark.parametrize('draw', [toon_homeware.mower, toon_homeware.blower])
@pytest.mark.parametrize('local', [False, True])
def test_running_tools_alternate_displacement_and_rest_between_spans(draw, local):
    cv = canvas()
    cv.local_time = local
    draw(cv, cv.comp, running=((0.25, 0.75), (1.25, 1.75)))
    animation = next(tree(cv).iter('animate'))
    assert (animation.get('timeBase') == 'local') == local
    keys = [(float(k.get('time')), float(k.get('value'))) for k in animation.iter('key')]

    def at(t):
        return next(value for time, value in reversed(keys) if time <= t)

    assert at(0) == at(1) == at(2) == 0
    for start in (0.25, 1.25):
        values = [at(start + d) for d in (0.01, 0.10, 0.18, 0.26)]
        assert all(a * b < 0 for a, b in zip(values, values[1:], strict=False))
        assert {abs(v) for v in values} == {toon.fh(3)}


@pytest.mark.parametrize(
    'counts', [((0, 3), (1, 1), (2, 2)), ((0, 2), (1, 2), (2, 1)), ((0, 1), (1, 3), (2, 2), (3, 3))]
)
def test_tub_visibility_matches_every_count_including_decreases(counts):
    cv = canvas()
    toon_homeware.soup_tubs(cv, cv.comp, counts=counts, end=4)
    tubs = [g for g in tree(cv).iter('group') if g.get('start') is not None]

    def visible(t):
        return sum(float(g.get('start')) <= t < float(g.get('end')) for g in tubs)

    assert visible(-0.1) == visible(4) == 0
    for t, count in counts:
        assert visible(t) == visible(t + 0.5) == count


def test_engine_evaluates_alternating_tool_motion_and_decreasing_tub_counts(tmp_path, scene_render):
    from support.acting import canvas as unlettered_canvas
    from support.acting import evaluate

    cv = unlettered_canvas()
    toon_homeware.mower(cv, cv.comp, running=((0.25, 0.75),))
    tool = cv.comp.elements()[0]
    toon_homeware.soup_tubs(cv, cv.comp, counts=((0, 3), (1, 1), (2, 2)), end=3)
    tub_ids = {g.id for g in cv.scene.iter('group') if g.start is not None}
    assert cv.scene.check(schema=True) == []
    path = tmp_path / 'homeware.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time, expected_y, count in ((0.26, toon.fh(3), 3), (0.35, -toon.fh(3), 3), (1, 0, 1), (2, 0, 2), (3, 0, 0)):
        nodes = evaluate(scene_render, path, time)
        actual = next(n for n in nodes if n['id'] == tool.id)
        assert actual['world'][5] == pytest.approx(expected_y)
        assert sum(n['id'] in tub_ids and n['draw'] and n['world_opacity'] > 0 for n in nodes) == count


@pytest.mark.parametrize(
    "draw",
    [
        toon_homeware.dishwasher,
        toon_homeware.baby_monitor,
        toon_homeware.shampoo,
        toon_homeware.mower,
        toon_homeware.blower,
        toon_homeware.lasagna,
        toon_homeware.toast,
    ],
)
@pytest.mark.parametrize("at", [(1.0,), "here", None])
def test_a_part_needs_a_point(draw, at):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match=r"\(x, y\)"):
        draw(cv, cv.comp, at=at)


@pytest.mark.parametrize("draw", [toon_homeware.baby_monitor, toon_homeware.lasagna, toon_homeware.toast])
@pytest.mark.parametrize("scale", [0, -1, "big"])
def test_a_part_needs_a_scale(draw, scale):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="scale"):
        draw(cv, cv.comp, scale=scale)
