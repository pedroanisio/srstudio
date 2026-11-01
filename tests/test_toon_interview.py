"""An interview room's parts: each draws from its defaults, the blind falls only on its cue, a sample leaves on its
second, and bad input is refused."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_interview
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def raw(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


@pytest.mark.parametrize(
    ("name", "builder"),
    [
        ("toon-wall-sign", toon_interview.wall_sign),
        ("toon-blind", toon_interview.blind),
        ("toon-tissue-box", toon_interview.tissue_box),
        ("toon-sample-tray", toon_interview.sample_tray),
        ("toon-paper", toon_interview.paper),
    ],
)
def test_the_parts_are_registered_and_draw_from_their_defaults(name: str, builder) -> None:
    assert registry.get("prop", name).builder is builder
    cv = canvas()
    builder(cv, cv.comp)
    assert len(list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter())) > 3


def test_a_sign_says_what_it_is_told() -> None:
    cv = canvas()
    toon_interview.wall_sign(cv, cv.comp, "ACME-FREE TILE")
    assert "ACME-FREE TILE" in raw(cv)


@pytest.mark.parametrize("bad", ["", "   ", "x" * (toon_interview.SIGN_MAX + 1)])
def test_a_sign_that_cannot_be_read_is_refused(bad: str) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="wall sign"):
        toon_interview.wall_sign(cv, cv.comp, bad)


def test_a_blind_is_up_until_its_cue_and_falls_only_with_one() -> None:
    cv = canvas()
    toon_interview.blind(cv, cv.comp)
    assert "scaleY" in raw(cv) and "<anim" not in raw(cv).lower().replace("animate-none", "")
    cv = canvas()
    toon_interview.blind(cv, cv.comp, drop=(2.0, 2.7))
    assert raw(cv).count("2.7") >= 1


@pytest.mark.parametrize("bad", [(3.0, 2.0), (-1.0, 2.0), (2.0, 2.0)])
def test_a_blind_with_a_bad_span_is_refused(bad: tuple[float, float]) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="drops"):
        toon_interview.blind(cv, cv.comp, drop=bad)


def test_a_blind_already_down_cannot_drop() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="already down"):
        toon_interview.blind(cv, cv.comp, drop=(1.0, 2.0), down=True)


def test_a_tray_refuses_an_empty_or_an_overfull_set_and_a_sample_it_does_not_hold() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="1 to 6"):
        toon_interview.sample_tray(cv, cv.comp, colours=())
    with pytest.raises(ToonDataError, match="missing"):
        toon_interview.sample_tray(cv, cv.comp, missing=(9, 1.0))


@pytest.mark.parametrize("builder", [toon_interview.tissue_box, toon_interview.paper])
def test_a_bad_scale_or_point_is_refused(builder) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale"):
        builder(cv, cv.comp, scale=0)
    with pytest.raises(ToonDataError, match="reference point"):
        builder(cv, cv.comp, at=(1.0,))
