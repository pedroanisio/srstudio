"""The Cutout card reader: a counter-top payment terminal whose screen shows a running total and what it is for."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import Canvas, props, registry
from support.tip_tablet import canvas


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def opacity_keys(cv: Canvas) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


READINGS = ((0.0, "$3.00", "one coffee"), (1.5, "$3.75", "+ cup fee"), (2.5, "$4.25", "+ lid fee"))


def test_the_reader_is_a_registered_cutout_prop():
    entry = registry.get("prop", "card-reader")
    assert entry.style == "cutout" and entry.summary


def test_it_letters_every_amount_bigger_than_its_label():
    cv = canvas()
    props.card_reader(cv, cv.comp, 560, 1240, readings=READINGS)
    texts = {t.get("text"): float(t.get("size")) for t in xml(cv).iter("text")}
    assert {"$3.00", "$3.75", "$4.25", "one coffee", "+ cup fee", "+ lid fee"} <= set(texts)
    assert texts["$3.00"] > 2 * texts["one coffee"]  # the total is what reads across the café


def test_each_reading_holds_until_the_next_and_the_last_to_the_end():
    cv = canvas()
    props.card_reader(cv, cv.comp, 560, 1240, readings=READINGS)
    gates = opacity_keys(cv)
    assert [(0.0, 1.0), (1.5, 0.0)] in gates
    assert [(0.0, 0.0), (1.5, 1.0), (2.5, 0.0)] in gates
    assert [(0.0, 0.0), (2.5, 1.0)] in gates


def test_the_first_reading_is_still_and_each_later_one_pops():
    cv = canvas()
    props.card_reader(cv, cv.comp, 560, 1240, readings=READINGS)
    pops = [
        [float(k.get("time")) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == "scaleX" and len(list(a.iter("key"))) == 4
    ]
    assert sorted(p[1] for p in pops) == [1.5, 2.5]  # a still opening frame stays still


def test_a_single_reading_is_shown_throughout():
    cv = canvas()
    props.card_reader(cv, cv.comp, 0, 0, readings=((0.0, "$3.00", "one coffee"),))
    assert opacity_keys(cv) == []


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(readings=()), "reading"),
        (dict(readings=((0.5, "$3.00", "coffee"),)), "reading"),
        (dict(readings=((0.0, "$3.00", "coffee"), (0.0, "$4.00", "fee"))), "reading"),
        (dict(readings=((0.0, "$3.00", "coffee"), (2.0, "$4.00", "fee"), (1.0, "$5.00", "fee"))), "reading"),
        (dict(readings=((0.0, " ", "coffee"),)), "amount"),
        (dict(readings=((0.0, "$1,000,000.00", "coffee"),)), "amount"),
        (dict(readings=((0.0, "$3.00", "x" * (props.READER_LABEL + 1)),)), "label"),
        (dict(readings=((0.0, "$3.00", "coffee"),), scale=0), "scale"),
        (dict(readings=((0.0, "$3.00", "coffee"),), scale=True), "scale"),
    ],
)
def test_it_refuses_a_screen_it_cannot_show(kw, match):
    with pytest.raises(ValueError, match=match):
        props.card_reader(canvas(), None, 0, 0, **kw)


def test_it_needs_a_font():
    with pytest.raises(ValueError, match="font"):
        props.card_reader(canvas(None), None, 0, 0, readings=((0.0, "$3.00", "coffee"),))


def test_a_popped_reading_scales_about_the_screen_without_moving_off_it():
    cv = canvas()
    props.card_reader(cv, cv.comp, 560, 1240, readings=READINGS)
    pops = [g for g in xml(cv).iter("group") if g.get("anchorY") is not None]
    assert len(pops) == 2
    for g in pops:  # the pivot is placed where it is, so the scale changes size, not position
        assert (float(g.get("x", 0)), float(g.get("y", 0))) == (float(g.get("anchorX")), float(g.get("anchorY")))
