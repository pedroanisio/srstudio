"""The Saga's everyday rooms: a hut with a table and a returns desk, a lifted arm, and props on tracks of their own."""

import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import SAGA, Canvas, registry, saga, saga_everyday, saga_reel, saga_sets
from srstudio.figure_gates import COVER_DEPTH
from srstudio.saga import Arm, SagaError
from srstudio.saga_reel import Entry, Place, Prop, Stage


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background="#000000", seed=1)
    return Canvas(scene, saga.VOID, font_asset="font", width=1080, height=1920)


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def keyed(t, prop: str):
    return [a for a in t.iter("animate") if a.get("property") == prop]


def take(id="01", actor="mabel", duration=4.0):
    return SimpleNamespace(id=id, actor=actor, duration=duration, is_effect=False)


# -- the catalog ------------------------------------------------------------------------------------------------------
def test_the_parts_are_registered_for_the_saga_style_and_named_in_its_parts():
    assert "saga_everyday" in SAGA.parts
    entries = {e.name: e for e in registry.entries()}
    for name in ("saga-hut", "saga-hut-table", "saga-returns", "saga-returns-desk", "saga-basket", "saga-coupon"):
        assert entries[name].style == "saga"


def test_a_stage_names_the_rooms_and_their_props_as_the_styles_own():
    assert saga_sets.SETS["hut"] is saga_everyday.hut and saga_sets.SETS["returns"] is saga_everyday.returns
    assert saga_sets.FRONTS["hut"] is saga_everyday.hut_table
    assert saga_sets.FRONTS["returns"] is saga_everyday.returns_desk
    assert {"plate", "tooth", "form", "basket", "coupon", "dim"} <= set(saga_sets.PROPS)


@pytest.mark.parametrize("room", [saga_everyday.hut, saga_everyday.returns])
def test_a_room_draws_both_signature_marks(room, monkeypatch):
    marks = []
    monkeypatch.setattr(saga_everyday, "_marks", lambda cv, g, cactus, code, *rest: marks.append((cactus, code)))
    cv = canvas()
    room(cv, cv.comp, end=4.0)
    ((cactus, code),) = marks
    for x, y in (cactus, code):
        assert 80 <= x <= 920 and 220 <= y <= 1420
        assert not (926 <= x <= 1044 and 270 <= y <= 332)


def test_no_room_or_desk_is_drawn_for_nothing():
    cv = canvas()
    for draw in (saga_everyday.hut, saga_everyday.hut_table, saga_everyday.returns, saga_everyday.returns_desk):
        with pytest.raises(SagaError):
            draw(cv, cv.comp, end=0)


# -- the arm ----------------------------------------------------------------------------------------------------------
def test_an_arm_swings_from_the_shoulder_and_stretches_along_its_length():
    cv = canvas()
    arm = Arm(((0.0, 0.0, 1.0), (1.0, 120.0, 0.7)))
    saga.draw(cv, cv.comp, "juno", at=(500, 1300), end=3.0, arm=arm)
    t = tree(cv)
    rows = [[float(k.get("value")) for k in a.findall("key")] for a in keyed(t, "rotation")]
    assert rows == [[0.0, -120.0]]
    stretched = [[float(k.get("value")) for k in a.findall("key")] for a in keyed(t, "scaleY")]
    assert [1.0, 0.7] in stretched


def test_a_character_without_a_lifted_arm_is_drawn_as_it_always_was():
    def drawn(**kw):
        cv = canvas()
        saga.draw(cv, cv.comp, "mabel", at=(500, 1300), end=3.0, **kw)
        return cv.scene.to_bytes(layout="pretty")

    assert drawn() == drawn(arm=None)
    assert drawn() != drawn(arm=Arm(((0.0, 40.0, 1.0),)))


def test_a_lifted_arm_leaves_one_arm_hanging_and_no_third():
    def hands(**kw):
        cv = canvas()
        saga.draw(cv, cv.comp, "gloom", at=(500, 1300), end=3.0, **kw)
        return sum(1 for s in tree(cv).iter("shape") if s.get("fill") == "#22242e" and s.get("shape") == "ellipse")

    assert hands() == hands(arm=Arm(((0.0, 40.0, 1.0),))) == 2


def test_an_arm_draws_what_it_holds_before_the_hand_that_grips_it():
    cv = canvas()
    arm = Arm(((0.0, 40.0, 1.0),), holds=saga_everyday.ration_bar)
    saga.draw(cv, cv.comp, "juno", at=(500, 1300), end=3.0, arm=arm)
    assert "#6e7a4a" in cv.scene.to_bytes(layout="pretty").decode()


@pytest.mark.parametrize(
    "keys, why",
    [
        ((), "at least one key"),
        (((1.0, 0.0, 1.0), (0.5, 0.0, 1.0)), "rise"),
        (((-1.0, 0.0, 1.0),), "rise"),
        (((0.0, float("nan"), 1.0),), "finite"),
        (((0.0, 0.0, 3.0),), "stretch"),
        (((0.0, 0.0, 0.1),), "stretch"),
    ],
)
def test_an_arm_that_cannot_be_drawn_is_refused(keys, why):
    with pytest.raises(SagaError, match=why):
        Arm(keys)


# -- the props --------------------------------------------------------------------------------------------------------
def test_a_tooth_falls_from_where_it_starts_to_where_it_lands():
    cv = canvas()
    saga_everyday.tooth(cv, cv.comp, at=(700, 1090), end=4.0, start=(780, 850), falls=(1.0, 1.4))
    t = tree(cv)
    x = [float(k.get("value")) for k in keyed(t, "x")[0].findall("key")]
    assert x == [780.0, 700.0]
    assert float(keyed(t, "y")[0].findall("key")[1].get("value")) == 1090.0


def test_a_tooth_refuses_a_fall_outside_the_shot():
    cv = canvas()
    with pytest.raises(SagaError, match="inside the shot"):
        saga_everyday.tooth(cv, cv.comp, at=(1, 1), end=1.0, start=(2, 2), falls=(0.5, 2.0))


def test_a_coupon_is_gone_when_its_track_reaches_nothing():
    cv = canvas()
    track = ((1.0, 700, 990, 0.3), (1.5, 640, 990, 1.0), (2.0, 600, 1085, 0.0))
    saga_everyday.coupon(cv, cv.comp, at=(700, 990), end=4.0, track=track)
    assert [float(k.get("value")) for k in keyed(tree(cv), "scaleX")[0].findall("key")] == [0.3, 1.0, 0.0]


@pytest.mark.parametrize(
    "track", [(), ((1.0, 2.0),), ((2.0, 1, 1, 1), (1.0, 1, 1, 1)), ((-1.0, 1, 1, 1),), ((0.0, float("inf"), 1, 1),)]
)
def test_a_coupon_track_that_cannot_be_followed_is_refused(track):
    cv = canvas()
    with pytest.raises(SagaError, match="track"):
        saga_everyday.coupon(cv, cv.comp, at=(1, 1), end=4.0, track=track)


def test_a_form_slides_along_its_table_and_gives_up_its_pen():
    cv = canvas()
    saga_everyday.form(cv, cv.comp, at=(380, 1106), end=4.0, slide=((1.0, 380), (2.0, 490)), since=0.9, pen_until=3.0)
    assert [float(k.get("value")) for k in keyed(tree(cv), "x")[0].findall("key")] == [380.0, 490.0]
    with pytest.raises(SagaError, match="pen is taken inside the shot"):
        saga_everyday.form(cv, cv.comp, at=(1, 1), end=1.0, pen_until=2.0)


def test_a_hologram_is_a_dark_puck_until_it_comes_on():
    def texts(**kw):
        cv = canvas()
        saga_everyday.benefits(cv, cv.comp, at=(340, 522), end=2.0, **kw)
        return cv.scene.to_bytes(layout="pretty").count(b"Dental. Vision. Pension.")

    assert texts() == 0
    assert texts(since=0.0) >= 1
    with pytest.raises(SagaError, match="comes on inside the shot"):
        texts(since=2.0)


def test_the_hut_table_goes_on_deep_enough_under_the_cast_behind_it():
    assert saga_everyday.TABLE_BOTTOM - saga_sets.BEHIND["hut"] >= COVER_DEPTH


def test_a_dim_falls_and_lifts_inside_its_span_and_refuses_nothing_to_darken():
    cv = canvas()
    saga_everyday.dim(cv, cv.comp, at=(0, 0), end=4.0, spans=((1.0, 3.0),), depth=0.6, fade=0.3)
    values = [float(k.get("value")) for k in keyed(tree(cv), "opacity")[0].findall("key")]
    assert max(values) == 0.6 and values[-1] == 0.0
    with pytest.raises(SagaError, match="needs a span"):
        saga_everyday.dim(cv, cv.comp, at=(0, 0), end=4.0, spans=())


def test_a_dim_leaves_a_lit_sign_out_of_the_dark():
    cv = canvas()
    saga_everyday.dim(cv, cv.comp, at=(0, 0), end=4.0, spans=((1.0, 3.0),), spared=saga_everyday.RETURNS_LIT)
    t = tree(cv)
    scrim = next(e for e in t.iter() if e.get("fillRule") == "evenodd")
    assert scrim.get("path").count("M") == 1 + len(saga_everyday.RETURNS_LIT)
    assert scrim.get("stroke") == cv.clear
    assert keyed(t, "opacity")


@pytest.mark.parametrize("spared", [((0, 0, 0, 10),), ((-10, 0, 100, 100),), ((1000, 1800, 200, 200),), ((0, 0, 10),)])
def test_a_dim_refuses_a_lit_box_off_the_frame_or_with_no_area(spared):
    cv = canvas()
    with pytest.raises(SagaError, match="lit box"):
        saga_everyday.dim(cv, cv.comp, at=(0, 0), end=4.0, spans=((1.0, 3.0),), spared=spared)


def test_a_wince_needs_a_span_to_hurt_in():
    cv = canvas()
    with pytest.raises(SagaError, match="span"):
        saga_everyday.wince(cv, cv.comp, at=(1, 1), end=1.0, spans=())


def test_a_panels_hole_is_where_the_coupon_is_aimed():
    assert saga_everyday.hole_of((545, 985)) == (590, 1085)


# -- the staging ------------------------------------------------------------------------------------------------------
def test_a_stage_in_the_hut_stands_the_family_behind_the_table():
    stages = {"01": Stage("hut", cast=(Place("mabel", 300, behind=True),), props=(Prop("plate", 700, 1090),))}
    saga_reel.check([take()], stages)
    assert saga_sets.BEHIND["hut"] > saga_everyday.TABLE_TOP


def test_a_stage_refuses_an_arm_on_a_cast_member_with_none_to_lift():
    stages = {"01": Stage("returns", cast=(Place("mabel", 300), Place("seven", 500, arm=Arm(((0.0, 1.0, 1.0),)))))}
    with pytest.raises(SagaError, match="seven has no arm to lift"):
        saga_reel.check([take()], stages)


def test_a_stage_refuses_a_mouth_on_the_one_already_speaking():
    stages = {"01": Stage("hut", cast=(Place("mabel", 300, behind=True, mouth=((0.0, "open"),)),))}
    with pytest.raises(SagaError, match="the take moves the mouth"):
        saga_reel.check([take()], stages)


def test_an_entry_that_is_the_next_line_of_the_last_does_not_rise_again():
    assert Entry("A", "", fade=True).rise and not Entry("A", "", fade=True, rise=False).rise
