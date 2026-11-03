"""An open laptop in Toon: it draws from defaults, notes land on their seconds, nothing letters a word, bad input is
refused."""

from __future__ import annotations

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_laptop
from srstudio.toon import ToonDataError
from srstudio.toon_laptop import Note, Quad


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def raw(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


def test_the_part_is_registered() -> None:
    assert registry.get("prop", "toon-open-laptop").builder is toon_laptop.open_laptop


def test_a_quad_maps_its_corners_and_its_middle() -> None:
    q = Quad((10.0, 20.0), (110.0, 20.0), (110.0, 120.0), (10.0, 120.0))
    assert q.at(0.0, 0.0) == (10.0, 20.0)
    assert q.at(1.0, 1.0) == (110.0, 120.0)
    assert q.at(0.5, 0.5) == (60.0, 70.0)


def test_it_draws_from_its_defaults_with_no_text_at_all() -> None:
    cv = canvas()
    toon_laptop.open_laptop(cv, cv.comp)
    assert toon_laptop.SCREEN.lower() in raw(cv).lower()
    assert "<text" not in raw(cv)


def test_a_note_is_gated_to_the_second_it_lands() -> None:
    cv = canvas()
    toon_laptop.open_laptop(cv, cv.comp, (Note(0.3, 0.3, 2.5), Note(0.7, 0.7, 4.0)))
    out = raw(cv)
    assert toon_laptop.NOTE.lower() in out.lower()
    assert 'start="2.5"' in out and 'start="4"' in out


def test_a_peeled_note_lifts_and_goes_back_on_its_span() -> None:
    plain, peeled = canvas(), canvas()
    toon_laptop.open_laptop(plain, plain.comp, (Note(0.3, 0.3, 1.0),))
    toon_laptop.open_laptop(peeled, peeled.comp, (Note(0.3, 0.3, 1.0, peel=(3.0, 4.0)),))
    assert 'rotation' not in raw(plain)
    assert 'rotation' in raw(peeled)


@pytest.mark.parametrize(
    "note",
    [
        Note(1.5, 0.5, 1.0),
        Note(0.5, -0.1, 1.0),
        Note(0.5, 0.5, -1.0),
        Note(0.5, 0.5, 2.0, peel=(1.0, 3.0)),
        Note(0.5, 0.5, 2.0, peel=(4.0, 3.0)),
    ],
)
def test_bad_notes_are_refused(note: Note) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_laptop.open_laptop(cv, cv.comp, (note,))


def test_notes_must_land_in_order() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="order"):
        toon_laptop.open_laptop(cv, cv.comp, (Note(0.3, 0.3, 4.0), Note(0.7, 0.7, 2.0)))


@pytest.mark.parametrize(
    "quad",
    [
        Quad((100.0, 100.0), (50.0, 100.0), (50.0, 200.0), (100.0, 200.0)),  # left and right swapped
        Quad((10.0, 200.0), (110.0, 200.0), (110.0, 100.0), (10.0, 100.0)),  # upside down
        Quad((10.0, 20.0), (float("nan"), 20.0), (110.0, 120.0), (10.0, 120.0)),
    ],
)
def test_a_quad_that_is_not_a_screen_is_refused(quad: Quad) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_laptop.open_laptop(cv, cv.comp, quad=quad)
