"""The Stick flat: the studio with the kitchen toilet and the painted window, and the fold-down bed that can hold a
sleeper who talks in his sleep."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_flat
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature())


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def opacity_keys(cv: Canvas) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


GARY = stick.Look(hair="bald")


def test_the_parts_are_registered_for_the_stick_style():
    for kind, name in (("location", "stick-studio-flat"), ("prop", "stick-murphy-bed")):
        assert registry.get(kind, name).style == "stick"


def test_the_flat_draws_its_kitchen_and_both_signature_marks():
    cv = canvas()
    stick_flat.studio(cv, cv.comp)
    root = xml(cv)
    ids = [g.get("id") or "" for g in root.iter("group")]
    assert any(i.startswith("sig-cactus") for i in ids)
    assert len(list(root.iter("shape"))) + len(list(root.iter("rect"))) > 40


def test_a_bed_that_never_drops_stays_up_and_one_dropped_from_the_start_stays_down():
    cv = canvas()
    stick_flat.murphy_bed(cv, cv.comp, 3.0)
    assert opacity_keys(cv) == []  # only the closed cabinet, the whole shot
    cv = canvas()
    stick_flat.murphy_bed(cv, cv.comp, 3.0, drop_at=0.0, sleeper=GARY)
    assert opacity_keys(cv) == []  # only the open bed and its sleeper, the whole shot


def test_the_bed_folds_down_on_its_cue_through_a_mid_frame():
    cv = canvas()
    stick_flat.murphy_bed(cv, cv.comp, 3.0, drop_at=1.0, sleeper=GARY)
    keys = opacity_keys(cv)
    fold = stick_flat.FOLD
    assert any(k[0] == (0.0, 1.0) and (1.0, 0.0) in k for k in keys)  # closed until the cue
    assert any((1.0, 1.0) in k and (round(1.0 + fold, 3), 0.0) in k for k in keys)  # the mid frame
    assert any((round(1.0 + fold, 3), 1.0) in k for k in keys)  # down after it


def test_the_sleeper_talks_only_while_the_bed_is_down():
    cv = canvas()
    stick_flat.murphy_bed(cv, cv.comp, 3.0, drop_at=0.0, sleeper=GARY, talk=((1.0, 1.5),))
    assert any((1.0, 1.0) in k and (1.5, 0.0) in k for k in opacity_keys(cv))
    with pytest.raises(StickDataError, match="talk"):
        stick_flat.murphy_bed(canvas(), None, 3.0, drop_at=1.0, sleeper=GARY, talk=((0.5, 0.8),))
    with pytest.raises(StickDataError, match="talk"):
        stick_flat.murphy_bed(canvas(), None, 3.0, drop_at=0.0, sleeper=GARY, talk=((1.0, 0.8),))
    with pytest.raises(StickDataError, match="sleeper"):
        stick_flat.murphy_bed(canvas(), None, 3.0, drop_at=0.0, talk=((1.0, 1.5),))


def test_bad_timings_are_refused():
    with pytest.raises(StickDataError, match="length"):
        stick_flat.murphy_bed(canvas(), None, 0.0)
    with pytest.raises(StickDataError, match="drop"):
        stick_flat.murphy_bed(canvas(), None, 3.0, drop_at=3.0)
    with pytest.raises(StickDataError, match="drop"):
        stick_flat.murphy_bed(canvas(), None, 3.0, drop_at=-0.1)
