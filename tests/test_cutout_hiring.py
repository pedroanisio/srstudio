"""Cutout at a job interview: the hiring office and the props of applicants who are never quite shown."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_hiring, registry
from support.tip_tablet import canvas

CHECKED = cutout_hiring.CutoutHiringError


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
        ("prop", "job-ad"),
        ("prop", "crayon-cv"),
        ("prop", "crib"),
        ("prop", "paper-hat"),
        ("prop", "roller-blind"),
        ("location", "hiring-office"),
    ],
)
def test_each_is_a_registered_cutout_part(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "cutout" and entry.summary


def test_the_ad_prints_its_two_lines():
    cv = canvas()
    cutout_hiring.job_ad(cv, cv.comp, heading="HIRING", lines=("JUNIOR", "30 YEARS"))
    assert {"HIRING", "JUNIOR", "30 YEARS"} <= set(texts(cv))
    assert errors(cv) == []


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(lines=("ONE",)), "two lines"),
        (dict(lines=("ONE", " ")), "two lines"),
        (dict(lines=("X" * (cutout_hiring.AD_LINE + 1), "TWO")), "two lines"),
        (dict(heading=" "), "heading"),
        (dict(scale=0), "scale"),
    ],
)
def test_it_refuses_an_ad_it_cannot_print(kw, match):
    with pytest.raises(CHECKED, match=match):
        cutout_hiring.job_ad(canvas(), None, **kw)


def test_the_crayon_cv_swings_its_shoes_only_when_asked():
    cv = canvas()
    cutout_hiring.crayon_cv(cv, cv.comp, swings=((0.0, 1.0),))
    assert {"crayon-cv-shoe-left", "crayon-cv-shoe-right"} <= ids(cv)
    assert errors(cv) == []
    still = canvas()
    cutout_hiring.crayon_cv(still, still.comp)
    assert errors(still) == []
    assert still.scene.to_bytes() != cv.scene.to_bytes()


def test_the_crib_holds_a_cv_and_a_rattle():
    cv = canvas()
    cutout_hiring.crib(cv, cv.comp, rattles=((0.0, 1.0),), cv_title="CV")
    assert "CV" in texts(cv) and "crib-rattle" in ids(cv)
    assert errors(cv) == []


@pytest.mark.parametrize(
    ("draw", "kw", "match"),
    [
        (cutout_hiring.crayon_cv, dict(title=" "), "title"),
        (cutout_hiring.crayon_cv, dict(swings=((2.0, 1.0),)), "swing"),
        (cutout_hiring.crayon_cv, dict(scale=0), "scale"),
        (cutout_hiring.crib, dict(cv_title=" "), "title"),
        (cutout_hiring.crib, dict(rattles=((2.0, 1.0),)), "rattle"),
        (cutout_hiring.crib, dict(scale=True), "scale"),
        (cutout_hiring.paper_hat, dict(label=" "), "label"),
        (cutout_hiring.paper_hat, dict(label="X" * (cutout_hiring.HAT_LABEL + 1)), "label"),
        (cutout_hiring.paper_hat, dict(scale=0), "scale"),
        (cutout_hiring.roller_blind, dict(w=0), "width"),
        (cutout_hiring.roller_blind, dict(h=-1), "height"),
    ],
)
def test_the_props_refuse_what_they_cannot_draw(draw, kw, match):
    with pytest.raises(CHECKED, match=match):
        draw(canvas(), None, **kw)


@pytest.mark.parametrize(
    "draw", [cutout_hiring.job_ad, cutout_hiring.crayon_cv, cutout_hiring.crib, cutout_hiring.paper_hat]
)
def test_what_is_lettered_needs_a_font(draw):
    with pytest.raises(CHECKED, match="font"):
        draw(canvas(None), None)


def test_a_blind_with_no_snap_stays_down_and_a_snap_keys_it():
    down, snapping = canvas(None), canvas(None)
    cutout_hiring.roller_blind(down, down.comp)
    cutout_hiring.roller_blind(snapping, snapping.comp, snap=2.0)
    assert errors(snapping) == [] and down.scene.to_bytes() != snapping.scene.to_bytes()


def test_the_office_draws_its_slots_in_depth_order():
    cv = canvas()
    order: list[str] = []
    cutout_hiring.hiring_office(
        cv,
        cv.comp,
        behind_desk=lambda g: order.append("behind"),
        on_desk=lambda g: order.append("on"),
        next_room=lambda g: order.append("next"),
        shots=[(0.0, 1.0)],
        snap=0.5,
    )
    assert order == ["next", "behind", "on"]
    assert "location-hiring-office-blind" in ids(cv)
    assert errors(cv) == []
