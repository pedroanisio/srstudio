"""The parlour: both sides of its counter, what is handed over it, and hooks that change nothing when unset."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import Canvas, registry, toon, toon_house, toon_parlour
from srstudio.toon_cars import Passing
from support.toon_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list:
    return [t for t in tree(cv).iter("text")]


def fills(cv: Canvas) -> set:
    return {s.get("fill") for s in tree(cv).iter("shape")}


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("prop", "toon-cone"),
        ("prop", "toon-toothpaste-cone"),
        ("prop", "toon-parlour-case"),
        ("location", "toon-parlour-front"),
        ("location", "toon-parlour-back"),
    ],
)
def test_every_part_is_registered(kind, name):
    assert (kind, name) in {(e.kind, e.name) for e in registry.entries()}


def test_a_mint_cone_has_chips_and_a_vanilla_one_none():
    mint, vanilla = canvas(), canvas()
    toon_parlour.cone(mint, mint.comp, flavour="mint")
    toon_parlour.cone(vanilla, vanilla.comp)
    assert toon_parlour.FLECK in fills(mint)
    assert toon_parlour.FLECK not in fills(vanilla)


@pytest.mark.parametrize("flavour", ["strawberry", "", None])
def test_a_flavour_the_parlour_lacks_is_refused(flavour):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="flavour"):
        toon_parlour.cone(cv, cv.comp, flavour=flavour)


@pytest.mark.parametrize("at", [(1.0,), "here", (1.0, "2"), None])
def test_a_cone_needs_a_point(at):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="point"):
        toon_parlour.cone(cv, cv.comp, at)
    with pytest.raises(toon.ToonDataError, match="point"):
        toon_parlour.toothpaste_cone(cv, cv.comp, at)


@pytest.mark.parametrize("scale", [0, -1, "big"])
def test_a_cone_needs_a_scale_over_zero(scale):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="scale"):
        toon_parlour.cone(cv, cv.comp, scale=scale)


def test_the_tube_stands_on_the_swirl_with_its_rotation_about_its_own_place():
    cv = canvas()
    toon_parlour.toothpaste_cone(cv, cv.comp)
    tube = next(g for g in tree(cv).iter("group") if g.get("rotation"))
    assert (tube.get("x"), tube.get("y")) == (tube.get("anchorX"), tube.get("anchorY"))


def test_nothing_in_the_parlour_is_lettered():
    cv = canvas()
    toon_parlour.parlour_front(cv, cv.comp)
    toon_parlour.parlour_back(cv, cv.comp)
    toon_parlour.toothpaste_cone(cv, cv.comp)
    toon_parlour.case(cv, cv.comp)
    assert not texts(cv)


def _held(cv: Canvas, **change):
    args = {
        "spans": ((0.0, 1.0, "mint"), (1.0, 2.0, "toothpaste")),
        "root": (100.0, 784.0),
        "at": (300.0, 600.0),
        "coat": "#123456",
        "hand": "#654321",
        "start": 0.0,
        "end": 2.0,
    }
    return toon_parlour.held(cv, cv.comp, **{**args, **change})


def test_an_arm_swings_about_its_root_and_only_when_told():
    still, swung = canvas(), canvas()
    _held(still)
    _held(swung, swings=((0.0, 0.0), (1.0, 90.0)))
    assert not [a for a in tree(still).iter("animate") if a.get("property") == "rotation"]
    assert [a for a in tree(swung).iter("animate") if a.get("property") == "rotation"]
    arm = next(g for g in tree(swung).iter("group") if g.get("anchorX"))
    assert float(arm.get("anchorX")) == pytest.approx(toon.fx(100.0))
    assert arm.get("x") == arm.get("anchorX") and arm.get("y") == arm.get("anchorY")


def test_a_cone_is_on_the_arm_only_for_its_span():
    cv = canvas()
    _held(cv)
    spans = [(g.get("start"), g.get("end")) for g in tree(cv).iter("group") if g.get("end")]
    assert ("0.0", "1.0") in spans or ("0", "1") in spans
    assert ("1.0", "2.0") in spans or ("1", "2") in spans


@pytest.mark.parametrize(
    "change",
    [
        {"spans": ((0.0, 1.0, "custard"),)},
        {"spans": ((1.0, 1.0, "mint"),)},
        {"root": "elbow"},
        {"at": None},
        {"at": (100.0, 784.0)},
        {"start": 2.0},
        {"start": -1.0},
        {"scale": 0},
    ],
)
def test_an_impossible_arm_is_refused(change):
    with pytest.raises(toon.ToonDataError):
        _held(canvas(), **change)


def test_the_street_goes_by_only_when_it_is_told():
    empty, busy = canvas(), canvas()
    toon_parlour.parlour_front(empty, empty.comp)
    toon_parlour.parlour_front(busy, busy.comp, 0.0, 5.0, (Passing(1.0, "bus"),))
    assert len(list(tree(busy).iter("animate"))) > len(list(tree(empty).iter("animate")))


def test_a_case_needs_a_top():
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="top"):
        toon_parlour.case(cv, cv.comp, "low")


def test_the_parlour_counter_is_a_ledge():
    cv = canvas()
    toon_house.ledge(cv, cv.comp, "parlour")
    assert toon_house.LEDGES["parlour"][1] in fills(cv)


def test_a_ledge_with_no_inset_is_drawn_as_it_was():
    plain, zero = canvas(), canvas()
    toon_house.ledge(plain, plain.comp)
    toon_house.ledge(zero, zero.comp, "oak", 0.0)
    assert plain.scene.to_bytes(layout="pretty") == zero.scene.to_bytes(layout="pretty")


def test_an_inset_moves_the_marks_in(monkeypatch):
    seen = {}
    monkeypatch.setattr(toon_house.signature, "cactus", lambda cv, g, x, y, scale: seen.update(cactus=x))
    monkeypatch.setattr(toon_house.signature, "code", lambda cv, g, x, y, size, **kw: seen.update(code=x))
    cv = canvas()
    toon_house.ledge(cv, cv.comp, "oak", 40.0)
    assert seen == {"cactus": pytest.approx(toon.fx(508)), "code": pytest.approx(toon.fx(540))}


@pytest.mark.parametrize("inset", [-1.0, "far", None])
def test_a_ledge_refuses_a_bad_inset(inset):
    cv = canvas()
    with pytest.raises(toon.ToonDataError, match="inset"):
        toon_house.ledge(cv, cv.comp, "oak", inset)
