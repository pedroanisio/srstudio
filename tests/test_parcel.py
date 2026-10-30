"""The Cutout parcel: a taped cardboard box with an address label, held against a chest or set on a floor."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import props, registry
from support.tip_tablet import canvas


def texts(cv) -> dict[str, str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return {t.get("id"): t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"}


def test_the_parcel_is_a_registered_cutout_prop():
    entry = registry.get("prop", "parcel")
    assert entry.style == "cutout" and entry.summary


def test_it_letters_its_label_and_can_go_unlabelled():
    cv = canvas()
    g = props.parcel(cv, cv.comp, 500, 1200, label="DEV · 7C", scale=1.2)
    assert g.id == "parcel" and "DEV · 7C" in texts(cv).values()
    plain = canvas(None)
    props.parcel(plain, plain.comp, 500, 1200, id="box")
    assert texts(plain) == {}
    assert [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message] == []


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(label=""), "label"),
        (dict(label="X" * (props.PARCEL_LABEL + 1)), "label"),
        (dict(scale=0), "scale"),
        (dict(scale=True), "scale"),
    ],
)
def test_it_refuses_a_parcel_it_cannot_draw(kw, match):
    with pytest.raises(ValueError, match=match):
        props.parcel(canvas(), None, 0, 0, **kw)


def test_a_label_needs_a_font():
    with pytest.raises(ValueError, match="font"):
        props.parcel(canvas(None), None, 0, 0, label="DEV")
