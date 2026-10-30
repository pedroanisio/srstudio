"""The Cutout pink slip: an envelope lettered with a name, which can be held until a moment and then fall to the
floor, tipping as it lands."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import Canvas, props, registry
from support.pink_slip import canvas


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def keys(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_slip_is_a_registered_cutout_prop():
    entry = registry.get("prop", "pink-slip")
    assert entry.style == "cutout" and entry.summary


def test_it_letters_the_name_on_the_envelope():
    cv = canvas()
    props.pink_slip(cv, cv.comp, 600, 1700, name="ERIC")
    assert "ERIC" in {t.get("text") for t in xml(cv).iter("text")}


def test_a_held_slip_shows_only_inside_its_span():
    cv = canvas()
    props.pink_slip(cv, cv.comp, 0, 0, name="ERIC", show=(0.0, 2.5))
    assert [(0.0, 1.0), (2.5, 0.0)] in keys(cv, "opacity")


def test_a_falling_slip_appears_at_the_drop_and_lands_on_its_mark():
    cv = canvas()
    props.pink_slip(cv, cv.comp, 600, 1700, name="ERIC", fall=(2.5, 300), rotation=-6)
    assert [(0.0, 0.0), (2.5, 1.0)] in keys(cv, "opacity")
    ys = next(k for k in keys(cv, "y") if k[0][0] == 2.5)
    assert ys[0] == (2.5, 1400.0) and ys[-1] == pytest.approx((2.5 + props.SLIP_FALL, 1700.0))
    turns = next(k for k in keys(cv, "rotation") if k[0][0] == 2.5)
    assert turns[-1] == pytest.approx((2.5 + props.SLIP_FALL, -6.0)) and turns[0][1] != -6.0  # it tips as it lands


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(name=" "), "name"),
        (dict(name="X" * (props.SLIP_CHARS + 1)), "name"),
        (dict(fall=(-1.0, 200)), "fall"),
        (dict(fall=(1.0, 0)), "fall"),
        (dict(show=(2.0, 1.0)), "show"),
        (dict(show=(0.0, 1.0), fall=(2.0, 100)), "show"),
        (dict(scale=0), "scale"),
    ],
)
def test_it_refuses_a_slip_it_cannot_draw(kw, match):
    with pytest.raises(ValueError, match=match):
        props.pink_slip(canvas(), None, 0, 0, **{"name": "ERIC", **kw})


def test_it_needs_the_caption_font():
    with pytest.raises(ValueError, match="font"):
        props.pink_slip(canvas(None), None, 0, 0, name="ERIC")


def test_a_slip_without_a_name_stays_blank_and_needs_no_font():
    cv = canvas(None)
    props.pink_slip(cv, cv.comp, 0, 0, name=None, show=(0.0, 1.0))
    assert list(xml(cv).iter("text")) == []
