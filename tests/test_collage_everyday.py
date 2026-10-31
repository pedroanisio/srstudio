"""The Collage everyday props and rooms: they draw, they refuse what they cannot draw, and their timing is the
caller's project clock."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_everyday, collage_sets, flat_counter, foley, registry
from srstudio.canvas import Signature
from srstudio.collage_everyday import EverydayError


def canvas(font: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    if font:
        cv.font_asset = "font"
    return cv


def body(cv: Canvas) -> bytes:
    return cv.scene.to_bytes(layout="pretty")


@pytest.mark.parametrize(
    "name",
    [
        "collage-food",
        "collage-phone",
        "collage-bubble",
        "collage-alarm-clock",
        "collage-cereal-box",
        "collage-duvet",
        "collage-tablecloth",
        "collage-salt-shaker",
        "collage-chip-bag",
        "collage-chip",
        "collage-certificate",
        "collage-snapshot",
        "collage-gust",
        "collage-bill",
        "collage-confetti",
        "collage-arm",
        "collage-bedroom",
        "collage-supermarket",
        "collage-thumb",
        "collage-dining-room",
        "collage-bus-stop",
    ],
)
def test_every_new_part_is_registered(name):
    kind = "location" if name.split("-", 1)[1] in {"bedroom", "supermarket", "dining-room", "bus-stop"} else "prop"
    assert registry.get(kind, name) is not None


@pytest.mark.parametrize("kind", sorted(collage_everyday.FOODS))
def test_every_food_draws_something_of_its_own(kind):
    cv = canvas()
    collage_everyday.food(cv, cv.comp, kind, 540, 960)
    assert b"<shape" in body(cv)


def test_foods_differ_and_an_unknown_one_is_refused():
    drawn = set()
    for kind in collage_everyday.FOODS:
        cv = canvas()
        collage_everyday.food(cv, cv.comp, kind, 540, 960)
        drawn.add(body(cv))
    assert len(drawn) == len(collage_everyday.FOODS)
    with pytest.raises(EverydayError, match="no food"):
        collage_everyday.food(canvas(), canvas().comp, "flan", 0, 0)


@pytest.mark.parametrize("part", sorted(collage_everyday.CHIPS))
def test_every_chip_part_draws(part):
    cv = canvas()
    collage_everyday.chip(cv, cv.comp, 540, 960, part)
    assert b"<shape" in body(cv)


def test_an_unknown_chip_part_is_refused():
    cv = canvas()
    with pytest.raises(EverydayError, match="no chip part"):
        collage_everyday.chip(cv, cv.comp, 0, 0, "dust")


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: collage_everyday.food(cv, cv.comp, "taco", 0, 0, 0),
        lambda cv: collage_everyday.phone(cv, cv.comp, 0, 0, 40, 400),
        lambda cv: collage_everyday.alarm_clock(cv, cv.comp, 0, 0, -1, "1:00"),
        lambda cv: collage_everyday.cereal_box(cv, cv.comp, 0, 0, 0, 10),
        lambda cv: collage_everyday.chip_bag(cv, cv.comp, 0, 0, 10, float("nan"), "X"),
        lambda cv: collage_everyday.bill(cv, cv.comp, "RENT", 0, 0, 0),
        lambda cv: collage_everyday.certificate(cv, cv.comp, "X", 0, 0, 0, 10, size=10),
        lambda cv: collage_everyday.snapshot(cv, cv.comp, 0, 0, 0),
        lambda cv: collage_everyday.salt_shaker(cv, cv.comp, 0, 0, 0),
    ],
)
def test_a_prop_refuses_a_size_it_cannot_draw(call):
    with pytest.raises(EverydayError, match="positive"):
        call(canvas())


def test_the_phone_returns_a_screen_inside_its_bezel():
    cv = canvas()
    screen = collage_everyday.phone(cv, cv.comp, 100, 200, 400, 700)
    assert float(screen.x) == -200 + collage_everyday.BEZEL and float(screen.y) == -350 + collage_everyday.BEZEL


def test_a_bubble_of_mine_is_green_and_theirs_grey():
    mine, theirs = canvas(), canvas()
    collage_everyday.bubble(mine, mine.comp, "yes", 0, 0, 300, 120, size=50, mine=True)
    collage_everyday.bubble(theirs, theirs.comp, "yes", 0, 0, 300, 120, size=50)
    assert b"#c9f2c7" in body(mine) and b"#c9f2c7" not in body(theirs)


def test_a_thumb_refuses_a_size_it_cannot_draw():
    cv = canvas()
    collage_everyday.thumb(cv, cv.comp, 100, 100, 200)
    with pytest.raises(collage_everyday.EverydayError):
        collage_everyday.thumb(cv, cv.comp, 100, 100, -1)


def test_lettering_takes_whole_pixels():
    cv = canvas()
    collage_everyday.chip_bag(cv, cv.comp, 540, 960, 455, 615, "VALUE PACK")  # 0.8 of 455 is not a whole pixel
    assert b"VALUE PACK" in body(cv)


def test_confetti_falls_then_turns_back_up():
    assert collage_everyday._piece_y(0.0, 100.0, 0.0, 4.0, None) == [(0.0, 0.0), (4.0, 400.0)]
    (_, y0), (_, y1), (_, y2) = collage_everyday._piece_y(0.0, 100.0, 0.0, 4.0, 2.0)
    assert y0 < y1 and y2 < y1  # down until the turn, then back up


@pytest.mark.parametrize("start,end,turn", [(2.0, 1.0, None), (-1.0, 1.0, None), (1.0, 2.0, 0.5)])
def test_confetti_refuses_time_that_does_not_run_forward(start, end, turn):
    cv = canvas()
    with pytest.raises(EverydayError, match="confetti"):
        collage_everyday.confetti(cv, cv.comp, start, end, turn=turn)


def test_a_gust_runs_forward():
    cv = canvas()
    with pytest.raises(EverydayError, match="gust"):
        collage_everyday.gust(cv, cv.comp, (0, 0), (1, 1), 2.0, 2.0)
    collage_everyday.gust(cv, cv.comp, (0, 0), (100, 100), 1.0, 2.0)
    assert b"opacity" in body(cv)


def test_an_arm_takes_a_name_or_a_look():
    a, b = canvas(), canvas()
    collage_everyday.arm(a, a.comp, "deb", (0, 0), (100, 100))
    collage_everyday.arm(b, b.comp, collage.LOOKS["deb"], (0, 0), (100, 100))
    assert body(a) == body(b)


def test_chewing_opens_and_shuts_the_mouth_and_keeps_the_track_outside_it():
    track = [(0.5, "open"), (0.8, "closed"), (3.0, "round")]
    out = collage_everyday.chew(track, 1.0, 2.0)
    assert out[:2] == track[:2] and out[-1] == (3.0, "round")
    inside = [v for t, v in out if 1.0 <= t <= 2.0]
    assert set(inside) == {"open", "closed"} and inside[-1] == "closed"
    assert [t for t, _ in out] == sorted(t for t, _ in out)
    with pytest.raises(EverydayError, match="chewing"):
        collage_everyday.chew([], 2.0, 1.0)


def test_the_air_thins_out_and_is_checked():
    sound = foley.air([0.0], 1.0, 0.8, rate=8000)
    n = len(sound) // 8
    early, late = (sum(abs(v) for v in sound[a : a + n]) for a in (0, 5 * n))
    assert early > late > 0
    assert max(abs(v) for v in sound) == pytest.approx(foley.PEAK)
    for bad in (dict(times=[0.9]), dict(length=9.0), dict(rate=10), dict(peak=2.0)):
        with pytest.raises(foley.FoleyError):
            foley.air(**{"times": [0.0], "duration": 1.0, "length": 0.5, **bad})


@pytest.mark.parametrize("name", ["bedroom", "supermarket", "dining-room", "bus-stop"])
def test_the_new_rooms_have_a_shelf_for_the_signature(name):
    assert name in collage_sets.SETS and name in collage_sets.SHELVES


def test_a_night_set_paints_no_warm_light():
    cv = canvas()
    collage_sets.SETS["bedroom"](cv, cv.comp)
    assert b"collage-light" not in body(cv)


# -- the router -------------------------------------------------------------------------------------------------------
def test_the_router_is_registered():
    assert registry.get("prop", "collage-router").builder is collage_everyday.router


def test_a_router_keys_one_lamp_per_stretch_of_its_light():
    one, two = canvas(), canvas()
    collage_everyday.router(one, one.comp, light=((0.0, "off"),))
    collage_everyday.router(two, two.comp, light=((0.0, "off"), (3.0, "green"), (9.0, "off")))
    assert body(two).count(b"<group") - body(one).count(b"<group") == 2
    assert b'time="3' in body(two) and b'time="9' in body(two)


def test_a_router_with_its_plug_pulled_draws_the_cord_hanging():
    plugged, pulled = canvas(), canvas()
    collage_everyday.router(plugged, plugged.comp)
    collage_everyday.router(pulled, pulled.comp, unplugged=4.0)
    assert body(pulled).count(b"<group") == body(plugged).count(b"<group") + 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"light": ()},
        {"light": ((1.0, "green"),)},
        {"light": ((0.0, "purple"),)},
        {"light": ((0.0, "off"), (0.0, "green"))},
        {"light": ((0.0, "off"), (5.0, "green"), (2.0, "off"))},
        {"unplugged": -1.0},
        {"w": 0.0},
    ],
)
def test_a_router_refuses_what_it_cannot_draw(kwargs):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.router(cv, cv.comp, **kwargs)


# -- the lasagna ------------------------------------------------------------------------------------------------------
def test_the_lasagna_is_registered():
    assert registry.get("prop", "collage-lasagna").builder is collage_everyday.lasagna


def test_a_lasagna_shows_every_layer_and_its_dish():
    cv = canvas()
    collage_everyday.lasagna(cv, cv.comp)
    drawn = body(cv)
    assert all(colour.encode() in drawn for _, colour in collage_everyday.LASAGNA_LAYERS)


def test_a_lasagna_scales_with_its_width():
    small, large = canvas(), canvas()
    collage_everyday.lasagna(small, small.comp, w=260.0)
    collage_everyday.lasagna(large, large.comp, w=1040.0)
    assert b"0.5" in body(small) and b"2.0" in body(large) or b"scaleX=\"2" in body(large)


@pytest.mark.parametrize("w", [0.0, -5.0, float("nan")])
def test_a_lasagna_refuses_a_width_it_cannot_draw(w):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.lasagna(cv, cv.comp, w=w)


# -- the flip card ----------------------------------------------------------------------------------------------------
TWO_SIDES = ((0.0, "NO THANKS, I HATE SAVING MONEY"), (3.0, "YES, MY FAMILY DESERVES LESS"))


def test_the_flip_card_is_registered():
    assert registry.get("prop", "collage-flip-card").builder is collage_everyday.flip_card


def test_a_flip_card_shows_each_side_in_its_own_stretch():
    one, two = canvas(), canvas()
    collage_everyday.flip_card(one, one.comp, TWO_SIDES[:1])
    collage_everyday.flip_card(two, two.comp, TWO_SIDES)
    assert body(two).count(b"<group") == body(one).count(b"<group") + 1


def test_a_flip_card_turns_only_when_it_has_another_side():
    one, two = canvas(), canvas()
    collage_everyday.flip_card(one, one.comp, TWO_SIDES[:1])
    collage_everyday.flip_card(two, two.comp, TWO_SIDES)
    assert b'property="scaleX"' in body(two)
    assert b'property="scaleX" defaultInterpolation="hold"' not in body(two)


@pytest.mark.parametrize(
    "sides",
    [
        (),
        ((3.0, "A"), (1.0, "B")),
        ((1.0, "A"), (1.0, "B")),
        ((0.0, "A" * 30),),  # one word wider than the card
        ((0.0, " ".join(["WORD"] * 40)),),  # more rows than the card
        ((0.0, "   "),),
    ],
)
def test_a_flip_card_refuses_a_side_it_could_not_show_whole(sides):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.flip_card(cv, cv.comp, sides)


# -- the magnifying glass ---------------------------------------------------------------------------------------------
def test_the_magnifying_glass_is_registered():
    assert registry.get("prop", "collage-magnifying-glass").builder is collage_everyday.magnifying_glass


def test_a_magnifying_glass_has_a_lens_that_shows_what_is_under_it():
    cv = canvas()
    collage_everyday.magnifying_glass(cv, cv.comp)
    assert b'fill="#cfe8ff40"' in body(cv)


@pytest.mark.parametrize("size", [0.0, -1.0, float("inf")])
def test_a_magnifying_glass_refuses_a_lens_it_cannot_draw(size):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.magnifying_glass(cv, cv.comp, size=size)


# -- the battery insert -----------------------------------------------------------------------------------------------
def test_the_battery_insert_is_registered():
    assert registry.get("prop", "collage-battery-insert").builder is collage_everyday.battery_insert


def test_a_battery_insert_says_its_level_in_red_when_it_is_nearly_gone():
    cv = canvas()
    collage_everyday.battery_insert(cv, cv.comp, levels=((0.0, 1),))
    drawn = body(cv)
    assert b"1%" in drawn
    assert collage_everyday.LOW_BATTERY.encode() in drawn


def test_a_battery_insert_with_charge_left_is_not_red():
    cv = canvas()
    collage_everyday.battery_insert(cv, cv.comp, levels=((0.0, 80),))
    assert collage_everyday.LOW_BATTERY.encode() not in body(cv)


def test_a_battery_insert_goes_black_when_it_dies():
    alive, dead = canvas(), canvas()
    collage_everyday.battery_insert(alive, alive.comp)
    collage_everyday.battery_insert(dead, dead.comp, dead=2.0)
    assert collage_everyday.DEAD_SCREEN.encode() in body(dead)
    assert collage_everyday.DEAD_SCREEN.encode() not in body(alive)


@pytest.mark.parametrize(
    "levels", [(), ((1.0, 5),), ((0.0, 101),), ((0.0, -1),), ((0.0, 5), (0.0, 4)), ((0.0, 5), (float("nan"), 4))]
)
def test_a_battery_insert_refuses_levels_it_cannot_show(levels):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.battery_insert(cv, cv.comp, levels=levels)


@pytest.mark.parametrize("dead", [-1.0, float("inf")])
def test_a_battery_insert_refuses_a_death_off_the_clock(dead):
    cv = canvas()
    with pytest.raises(EverydayError):
        collage_everyday.battery_insert(cv, cv.comp, dead=dead)
