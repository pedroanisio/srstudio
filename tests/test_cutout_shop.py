"""Cutout at the barber's: the mirror, the cape, the tools on the shelf and the hair past the lens."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_shop, registry
from support.tip_tablet import canvas

CHECKED = cutout_shop.CutoutShopError


def texts(cv) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"]


def ids(cv) -> set[str]:
    return {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("id")}


def errors(cv) -> list:
    return [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message]


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("prop", "barber-cape"),
        ("prop", "hedge-trimmer"),
        ("prop", "lawnmower"),
        ("prop", "hair-fall"),
        ("location", "barbershop"),
    ],
)
def test_each_is_a_registered_cutout_part(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "cutout" and entry.summary


@pytest.mark.parametrize("spread", [False, True])
def test_a_cape_is_drawn_worn_or_flung_open(spread):
    cv = canvas()
    cutout_shop.barber_cape(cv, cv.comp, spread=spread)
    assert "barber-cape" in ids(cv) and not errors(cv)


@pytest.mark.parametrize("bad", [{"width": 0}, {"height": -1}, {"width": "wide"}])
def test_a_cape_refuses_a_size_it_cannot_have(bad):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_shop.barber_cape(cv, cv.comp, **bad)


@pytest.mark.parametrize("draw", [cutout_shop.hedge_trimmer, cutout_shop.lawnmower], ids=["hedge-trimmer", "lawnmower"])
def test_the_tools_refuse_a_scale_they_cannot_have(draw):
    cv = canvas()
    with pytest.raises(CHECKED):
        draw(cv, cv.comp, scale=0)


def test_a_mower_faces_one_way_or_the_other():
    cv = canvas()
    cutout_shop.lawnmower(cv, cv.comp, facing=-1, id="left")
    cutout_shop.lawnmower(cv, cv.comp, facing=1, id="right")
    assert {"left", "right"} <= ids(cv) and not errors(cv)
    with pytest.raises(CHECKED):
        cutout_shop.lawnmower(cv, cv.comp, facing=0)


def test_hair_falls_one_sheet_per_fall():
    cv = canvas()
    cutout_shop.hair_fall(cv, cv.comp, falls=[(1.0, 0.5), (1.4, 0.5)])
    assert {"hair-fall-sheet-1", "hair-fall-sheet-2"} <= ids(cv) and not errors(cv)


@pytest.mark.parametrize("bad", [(), ((1.0, 0.0),), ((1.0, -2.0),), (("soon", 1.0),)])
def test_hair_refuses_a_fall_with_no_length(bad):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_shop.hair_fall(cv, cv.comp, falls=bad)


def test_hair_is_the_same_from_a_seed():
    def drawn(seed):
        cv = canvas()
        cutout_shop.hair_fall(cv, cv.comp, seed=seed)
        return cv.scene.to_bytes()

    assert drawn(3) == drawn(3) != drawn(4)


def test_the_barbershop_calls_its_slots_and_shows_its_price():
    cv = canvas()
    called = []
    cutout_shop.barbershop(cv, cv.comp, in_mirror=called.append, on_counter=called.append, shots=[(0.0, 2.0)])
    assert len(called) == 2 and "TRIM $22" in texts(cv) and not errors(cv)


def test_the_barbershop_can_go_without_a_price():
    cv = canvas()
    cutout_shop.barbershop(cv, cv.comp, price="")
    assert not texts(cv)
