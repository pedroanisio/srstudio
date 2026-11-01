"""A smoke detector and a folder: each draws from its defaults, changes only on its cue, and refuses a bad cue."""

from __future__ import annotations

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_alarm
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def raw(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


def test_the_parts_are_registered() -> None:
    assert registry.get("prop", "toon-smoke-detector").builder is toon_alarm.smoke_detector
    assert registry.get("prop", "toon-folder").builder is toon_alarm.folder


def test_a_detector_stays_green_with_no_cue() -> None:
    cv = canvas()
    toon_alarm.smoke_detector(cv, cv.comp)
    assert toon_alarm.LED.lower() in raw(cv).lower()
    assert toon_alarm.ALARM.lower() not in raw(cv).lower()


def test_a_detector_turns_red_on_its_cue() -> None:
    cv = canvas()
    toon_alarm.smoke_detector(cv, cv.comp, red=4.5)
    assert toon_alarm.ALARM.lower() in raw(cv).lower()
    assert "4.5" in raw(cv)


@pytest.mark.parametrize("bad", [-1.0, "soon"])
def test_a_bad_cue_is_refused(bad: object) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="red"):
        toon_alarm.smoke_detector(cv, cv.comp, red=bad)  # type: ignore[arg-type]
    with pytest.raises(ToonDataError, match="opens"):
        toon_alarm.folder(cv, cv.comp, opened=bad)  # type: ignore[arg-type]


def test_a_folder_shut_for_good_shows_no_photograph() -> None:
    cv = canvas()
    toon_alarm.folder(cv, cv.comp)
    shut = raw(cv)
    cv = canvas()
    toon_alarm.folder(cv, cv.comp, opened=2.0)
    assert toon_alarm.SKY.lower() in raw(cv).lower() and toon_alarm.SKY.lower() not in shut.lower()


def test_a_bad_scale_or_point_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale"):
        toon_alarm.folder(cv, cv.comp, scale=0)
    with pytest.raises(ToonDataError, match="reference point"):
        toon_alarm.smoke_detector(cv, cv.comp, at=(1.0,))  # type: ignore[arg-type]
