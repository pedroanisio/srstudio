"""The one cover of every Okayville reel: the same band over the reel's own art (ADR 0074)."""

import dataclasses
import html
import re

import pytest

from srstudio import thumbnail
from srstudio.sample import SYSTEM_FONTS
from srstudio.thumbnail import ShowCover, Thumbnail, ThumbnailError, covered, grid_box, layout

FONT = next(f for f in SYSTEM_FONTS if f.exists())
FONT_BYTES = FONT.read_bytes()
WIDTH, HEIGHT = 1080, 1920


@pytest.fixture(autouse=True)
def condensed(monkeypatch):
    """The fixture font is far wider than the display face the cover is set in: measure as that face does."""
    monkeypatch.setattr(thumbnail.fonts, "text_width", lambda font, text, size: 0.44 * size * len(text))


def cover(**kw) -> ShowCover:
    return ShowCover(**{"headline": "THE MEETING\nNEVER ENDED", "at": 2.0, "number": 212, **kw})


def compose(thumb) -> bytes:
    scene = thumbnail.compose(thumb, backdrop="b.png", font="f.ttf", font_bytes=FONT_BYTES, width=WIDTH, height=HEIGHT)
    return scene.to_bytes()


def words(document: bytes) -> list[str]:
    return [html.unescape(w) for w in re.findall(r'<text [^>]*?text="([^"]*)"', document.decode())]


def test_the_template_is_valid_for_a_number_and_a_premise():
    assert cover().problems() == []


@pytest.mark.parametrize("number", [0, -3, 1.5, True, "12"])
def test_a_missing_or_wrong_number_is_refused(number):
    assert any("number" in p for p in cover(number=number).problems())


def test_a_premise_of_six_words_is_refused():
    assert any("5 words" in p for p in cover(headline="ONE TWO THREE\nFOUR FIVE SIX").problems())


def test_the_template_is_the_same_on_every_reel_so_its_look_cannot_be_changed_per_reel():
    assert any("kicker" in p for p in cover(kicker="SAGA").problems())
    assert any("place" in p for p in cover(place="top").problems())
    assert any("accent" in p for p in cover(accent="#ff0000").problems())
    assert any("lines" in p for p in cover(headline="ONE\nTWO\nTHREE").problems())


@pytest.mark.parametrize(
    "series,number", [("Saga", 0), ("", 4), ("Saga", -1), ("Saga 2", 4), ("SAGA", 4), ("Saga", True)]
)
def test_a_series_needs_its_name_and_its_number_together(series, number):
    assert any("series" in p for p in cover(series=series, series_number=number).problems())


def test_the_band_starts_at_the_same_place_whatever_the_premise():
    one = layout(cover(headline="GOOD"), FONT_BYTES, WIDTH, HEIGHT)
    two = layout(cover(), FONT_BYTES, WIDTH, HEIGHT)
    assert one.shade == two.shade
    assert one.picture == two.picture
    assert one.shade[0] == thumbnail.BAND_TOP


def test_everything_the_band_says_sits_inside_the_grid():
    gx, gy, gw, gh = grid_box(WIDTH, HEIGHT)
    thumb = cover(series="Saga", series_number=19)
    lay = layout(thumb, FONT_BYTES, WIDTH, HEIGHT)
    assert gy <= thumbnail.BAND_TOP
    assert lay.lines[-1][0] + round(lay.size * thumbnail.LEADING) <= gy + gh - thumbnail.BAND_MARGIN
    assert all(width <= gw - 2 * thumbnail.MARGIN for _, width in lay.lines)


def test_a_label_that_does_not_fit_the_row_is_refused_not_drawn():
    with pytest.raises(ThumbnailError, match="wider"):
        layout(cover(series="Extraordinarily", series_number=1000), FONT_BYTES, WIDTH, HEIGHT)


def test_the_premise_stays_big_enough_for_a_thumbnail():
    assert layout(cover(headline="NO"), FONT_BYTES, WIDTH, HEIGHT).size > thumbnail.PREMISE_MIN
    with pytest.raises(ThumbnailError, match="wider"):
        layout(cover(headline="PNEUMONOULTRAMICROSCOPICSILICOVOLCANOCONIOSIS"), FONT_BYTES, WIDTH, HEIGHT)


def test_the_band_says_the_show_the_number_and_the_premise():
    assert words(compose(cover())) == ["OKAYVILLE", "#212", "THE MEETING", "NEVER ENDED"]


def test_a_series_episode_carries_its_number_on_the_band():
    said = words(compose(cover(series="Saga", series_number=19)))
    assert said == ["OKAYVILLE", "#212", "SAGA #19", "THE MEETING", "NEVER ENDED"]


def test_two_covers_share_the_band_and_differ_only_in_what_they_say():
    def band(document: bytes) -> list[str]:
        return re.findall(r'<(?:rect|shape)[^>]*shape="rect"[^>]*>', document.decode())

    assert band(compose(cover())) == band(compose(cover(number=7, headline="ANOTHER REEL", at=9.0)))


def test_the_art_underneath_is_the_reel_s_own():
    assert 'id="backdrop-layer"' in compose(cover()).decode()


def test_a_face_under_the_band_is_covered_and_one_above_it_is_not():
    thumb = cover()
    under = (400.0, thumbnail.BAND_TOP + 20.0, 200.0, 200.0)
    above = (400.0, 500.0, 200.0, 200.0)
    assert covered(thumb, FONT_BYTES, WIDTH, HEIGHT, [under, above]) == [under]


def test_the_zoom_can_push_a_face_under_the_band():
    face = (480.0, 700.0, 120.0, 120.0)
    assert covered(cover(), FONT_BYTES, WIDTH, HEIGHT, [face]) == []
    assert covered(cover(zoom=2.0, focus=(540.0, 400.0)), FONT_BYTES, WIDTH, HEIGHT, [face]) == [face]


def test_the_template_needs_the_reels_own_frame():
    with pytest.raises(ThumbnailError, match="1080"):
        layout(cover(), FONT_BYTES, 1080, 1080)


def test_a_plain_thumbnail_draws_what_it_drew():
    """The published covers: the template lives beside them and changes none."""
    plain = Thumbnail("A HEADLINE", 1.0, kicker="Saga 08")
    assert [f.name for f in dataclasses.fields(plain)] == [
        "headline", "at", "kicker", "focus", "zoom", "accent", "place",
    ]  # fmt: skip
    assert words(compose(plain)) == ["SAGA 08", "A HEADLINE", "A HEADLINE"]


# -- a show named in more words (ADR 0233) -----------------------------------------------------------------------------
def test_a_show_named_in_more_words_says_its_episode_on_a_row_of_its_own():
    thumb = cover(series="Juno & Pip", series_number=2, number=216, headline="READY IN FIVE MINUTES")
    assert thumb.problems() == []
    assert thumb.episodic
    assert thumb.tag == "Juno & Pip · EP 2"
    assert words(compose(thumb)) == ["OKAYVILLE", "#216", "JUNO & PIP · EP 2", "READY IN FIVE MINUTES"]
    document = compose(thumb).decode()
    row = re.search(r'<text [^>]*?id="header-series"[^>]*>', document)
    assert row is not None


def test_the_episode_row_sits_between_the_top_row_and_the_premise_inside_the_grid():
    gx, gy, gw, gh = grid_box(WIDTH, HEIGHT)
    thumb = cover(series="Juno & Pip", series_number=2, number=216)
    lay = layout(thumb, FONT_BYTES, WIDTH, HEIGHT)
    header_end = thumbnail.HEADER_TOP + round(thumbnail.HEADER_SIZE * thumbnail.LEADING)
    row_end = thumbnail.SERIES_TOP + round(thumbnail.SERIES_SIZE * thumbnail.LEADING)
    assert header_end <= thumbnail.SERIES_TOP
    assert row_end + thumbnail.SERIES_GAP <= lay.lines[0][0]
    assert lay.lines[-1][0] + round(lay.size * thumbnail.LEADING) <= gy + gh - thumbnail.BAND_MARGIN
    assert lay.size >= thumbnail.PREMISE_MIN
    assert lay.shade == layout(cover(), FONT_BYTES, WIDTH, HEIGHT).shade


def test_a_one_word_series_keeps_its_place_on_the_top_row_and_draws_no_episode_row():
    thumb = cover(series="Saga", series_number=19)
    assert not thumb.episodic
    assert thumb.tag == "Saga #19"
    assert 'id="header-series"' not in compose(thumb).decode()
    assert layout(thumb, FONT_BYTES, WIDTH, HEIGHT) == layout(cover(), FONT_BYTES, WIDTH, HEIGHT)


@pytest.mark.parametrize(
    ("series", "number"),
    [("Juno & Pip", 0), ("Juno &", 2), ("juno-and-pip", 2), ("Juno & Pip!", 2), ("Juno  Pip", 2), ("Juno & Pip", -2)],
)
def test_a_show_without_a_name_or_a_place_is_refused(series, number):
    assert any("series" in p for p in cover(series=series, series_number=number).problems())


def test_an_episode_tag_wider_than_the_band_is_refused_not_drawn():
    long = "Extraordinarily Long Names Never Ending Shows Forever"
    with pytest.raises(ThumbnailError, match="wider"):
        layout(cover(series=long, series_number=1), FONT_BYTES, WIDTH, HEIGHT)
