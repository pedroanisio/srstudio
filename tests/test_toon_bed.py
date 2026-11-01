"""A bed for two: it draws from defaults, day is not night, the drawer moves only on cues, bad input is refused."""

from __future__ import annotations

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_bed
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def raw(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


def test_the_parts_are_registered() -> None:
    assert registry.get("location", "toon-double-bed").builder is toon_bed.double_bed
    assert registry.get("prop", "toon-double-quilt").builder is toon_bed.double_quilt
    assert registry.get("prop", "toon-bedside-drawer").builder is toon_bed.bedside_drawer
    assert registry.get("prop", "toon-swung-arm").builder is toon_bed.swung_arm
    assert registry.get("location", "toon-bedroom-corner").builder is toon_bed.floor_corner
    assert registry.get("prop", "toon-quilt-heap").builder is toon_bed.quilt_heap


def test_night_keeps_the_blind_down_and_day_lets_the_sun_in() -> None:
    night, day = canvas(), canvas()
    toon_bed.double_bed(night, night.comp)
    toon_bed.double_bed(day, day.comp, day=True)
    assert toon_bed.BLIND.lower() in raw(night).lower()
    assert toon_bed.SKY.lower() not in raw(night).lower()
    assert toon_bed.SKY.lower() in raw(day).lower()
    assert toon_bed.BLIND.lower() not in raw(day).lower()


def test_the_quilt_carries_one_of_each_mark(monkeypatch: pytest.MonkeyPatch) -> None:
    drawn: list[str] = []
    monkeypatch.setattr(toon_bed.signature, "cactus", lambda *a, **k: drawn.append("cactus"))
    monkeypatch.setattr(toon_bed.signature, "code", lambda *a, **k: drawn.append("code"))
    cv = canvas()
    toon_bed.double_quilt(cv, cv.comp)
    assert sorted(drawn) == ["cactus", "code"]


def test_the_corner_is_day_or_night() -> None:
    night, day = canvas(), canvas()
    toon_bed.floor_corner(night, night.comp)
    toon_bed.floor_corner(day, day.comp, day=True)
    assert raw(night) != raw(day)


def test_only_the_day_quilt_has_sun_on_it() -> None:
    night, day = canvas(), canvas()
    toon_bed.double_quilt(night, night.comp)
    toon_bed.double_quilt(day, day.comp, day=True)
    assert toon_bed.SUN_BAND.lower() not in raw(night).lower()
    assert toon_bed.SUN_BAND.lower() in raw(day).lower()


def test_a_drawer_with_no_cue_stays_shut() -> None:
    cv = canvas()
    toon_bed.bedside_drawer(cv, cv.comp)
    assert "<keyframes" not in raw(cv).lower() and "<animate" not in raw(cv).lower()


def test_a_drawer_buzzes_and_slides_on_its_cues() -> None:
    plain, cued = canvas(), canvas()
    toon_bed.bedside_drawer(plain, plain.comp)
    toon_bed.bedside_drawer(cued, cued.comp, buzzes=(2.0, 5.0), slides=8.0)
    text = raw(cued)
    assert text != raw(plain)
    assert 'time="8.45"' in text and 'time="2.04"' in text


@pytest.mark.parametrize("bad", [-1.0, "soon"])
def test_a_bad_cue_is_refused(bad: object) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="slides"):
        toon_bed.bedside_drawer(cv, cv.comp, slides=bad)  # type: ignore[arg-type]
    with pytest.raises(ToonDataError, match="buzz"):
        toon_bed.bedside_drawer(cv, cv.comp, buzzes=(bad,))  # type: ignore[arg-type]


def test_a_bad_pattern_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="quilt"):
        toon_bed.double_quilt(cv, cv.comp, "tartan")
    with pytest.raises(ToonDataError, match="quilt"):
        toon_bed.quilt_heap(cv, cv.comp, "tartan")


def test_a_heap_reaches_the_foot_of_the_frame_and_refuses_no_width() -> None:
    cv = canvas()
    toon_bed.quilt_heap(cv, cv.comp, "teal")
    assert str(cv.height + 20.0) in raw(cv)
    with pytest.raises(ToonDataError, match="width"):
        toon_bed.quilt_heap(cv, cv.comp, width=0.0)


def test_an_arm_swings_about_its_shoulder() -> None:
    cv = canvas()
    toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "#aa7755", [(1.0, 200.0), (1.4, 180.0)], 1.0, 4.0)
    text = raw(cv)
    assert 'property="rotation"' in text
    assert "1.4" in text


@pytest.mark.parametrize(
    ("swing", "start", "end", "match"),
    [([], 0.0, 1.0, "swing"), ([(1.0, "up")], 0.0, 2.0, "swing"), ([(1.0, 0.0)], 2.0, 1.0, "start")],
)
def test_a_bad_arm_is_refused(swing: list, start: float, end: float, match: str) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "#aa7755", swing, start, end)


def test_an_arm_needs_a_colour_and_a_length() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="coat"):
        toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "brown", [(1.0, 0.0)], 0.0, 2.0)
    with pytest.raises(ToonDataError, match="length"):
        toon_bed.swung_arm(cv, cv.comp, (300.0, 700.0), "#aa7755", [(1.0, 0.0)], 0.0, 2.0, length=0.0)
