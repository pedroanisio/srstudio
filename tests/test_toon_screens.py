"""A laptop's lid and a system's notice: the notice is short enough to read and shows only in its span."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_screens
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def test_the_parts_are_registered() -> None:
    assert registry.get("prop", "toon-laptop-lid").builder is toon_screens.lid
    assert registry.get("graphic", "toon-notice").builder is toon_screens.notice


def test_a_notice_carries_both_its_lines_at_a_size_read_on_a_phone() -> None:
    cv = canvas()
    toon_screens.notice(cv, cv.comp, "APPLICATION 9", "REJECTED", 1.0, 3.0)
    raw = cv.scene.to_bytes(layout="pretty").decode()
    assert "APPLICATION 9" in raw and "REJECTED" in raw
    assert toon_screens.READ_SIZE >= 40


def test_a_notice_too_long_to_read_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_screens.notice(cv, cv.comp, "x" * (toon_screens.NOTICE_MAX + 1), "NO", 1.0, 3.0)


def test_a_notice_ending_before_it_starts_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_screens.notice(cv, cv.comp, start=3.0, end=1.0)


def test_a_lid_that_shuts_animates_and_one_that_stays_open_does_not() -> None:
    cv = canvas()
    toon_screens.lid(cv, cv.comp)
    still = len(list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter()))
    cv = canvas()
    toon_screens.lid(cv, cv.comp, shut=2.0)
    assert len(list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter())) > still
