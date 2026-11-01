"""What a lobby keeps on a candidate who keeps coming back."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_lobby
from support.tip_tablet import canvas

YEARS = tuple(str(2014 + n) for n in range(12))


def texts(cv) -> str:
    return cv.scene.to_bytes().decode()


def ids(cv) -> list[str]:
    return [e.get("id", "") for e in ET.fromstring(cv.scene.to_bytes()).iter("group")]


def test_a_plaque_is_lettered_with_its_title_its_name_and_every_year():
    cv = canvas()
    cutout_lobby.wall_plaque(
        cv, cv.comp, 300, 500, title="CANDIDATE OF THE YEAR", name="DAVE", years=YEARS, read=[(9.0, 12.0)]
    )
    text = texts(cv)
    assert "CANDIDATE OF THE YEAR" in text and "DAVE" in text
    assert all(year in text for year in YEARS)


def test_a_plaque_that_is_never_read_carries_only_scrawl():
    cv = canvas()
    cutout_lobby.wall_plaque(cv, cv.comp, 300, 500, name="DAVE", years=YEARS)
    assert "DAVE" not in texts(cv)


@pytest.mark.parametrize(
    "options",
    [
        dict(title=""),
        dict(title="A TITLE MUCH TOO LONG FOR ONE PLATE OF BRASS"),
        dict(name="  "),
        dict(name="A NAME MUCH TOO LONG FOR THE PLATE"),
        dict(years=()),
        dict(years=tuple(str(n) for n in range(13))),
        dict(scale=0),
        dict(scale=float("nan")),
    ],
)
def test_a_plaque_it_cannot_letter_is_refused(options):
    cv = canvas()
    with pytest.raises(cutout_lobby.CutoutLobbyError):
        cutout_lobby.wall_plaque(cv, cv.comp, 300, 500, **options)


def test_a_cake_carries_its_two_lines():
    cv = canvas()
    cutout_lobby.sheet_cake(cv, cv.comp, 540, 1060, lines=("5 YEARS", "SHORTLISTED"))
    assert "5 YEARS" in texts(cv) and "SHORTLISTED" in texts(cv)


@pytest.mark.parametrize(
    "lines", [(), ("ONE",), ("", "TWO"), ("ONE", "TWO", "THREE"), ("ONE", "A LINE TOO LONG FOR A CAKE")]
)
def test_a_cake_it_cannot_pipe_is_refused(lines):
    cv = canvas()
    with pytest.raises(cutout_lobby.CutoutLobbyError):
        cutout_lobby.sheet_cake(cv, cv.comp, 540, 1060, lines=lines)


def test_a_lanyard_draws_the_photo_it_is_given_on_its_card():
    cv = canvas()
    called = []
    cutout_lobby.id_lanyard(cv, cv.comp, 400, 800, photo=called.append)
    assert len(called) == 1
    assert "id-lanyard-photo" in ids(cv)


@pytest.mark.parametrize("options", [dict(label=""), dict(label="NOT A SHORT LABEL AT ALL"), dict(scale=-1)])
def test_a_lanyard_it_cannot_print_is_refused(options):
    cv = canvas()
    with pytest.raises(cutout_lobby.CutoutLobbyError):
        cutout_lobby.id_lanyard(cv, cv.comp, 400, 800, **options)


def test_streamers_hang_one_swag_for_each_gap():
    few, many = canvas(), canvas()
    cutout_lobby.paper_streamers(few, few.comp, 100, 900, 200, swags=2)
    cutout_lobby.paper_streamers(many, many.comp, 100, 900, 200, swags=5)
    assert len(texts(many)) > len(texts(few))


@pytest.mark.parametrize("args", [(900, 100, 200), (100, 100, 200)])
def test_streamers_with_no_span_are_refused(args):
    cv = canvas()
    with pytest.raises(cutout_lobby.CutoutLobbyError):
        cutout_lobby.paper_streamers(cv, cv.comp, *args)


@pytest.mark.parametrize("options", [dict(swags=0), dict(swags=1.5), dict(sag=-1), dict(sag=float("inf"))])
def test_streamers_of_no_shape_are_refused(options):
    cv = canvas()
    with pytest.raises(cutout_lobby.CutoutLobbyError):
        cutout_lobby.paper_streamers(cv, cv.comp, 100, 900, 200, **options)
