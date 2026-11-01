"""Cutout, what changes hands: each prop draws, is registered, and refuses what it cannot draw."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_handed, registry
from support.tip_tablet import canvas

CHECKED = cutout_handed.CutoutHandedError


def ids(cv) -> set[str]:
    return {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("id")}


def texts(cv) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"]


@pytest.mark.parametrize("name", ["cv-folder", "phone-post", "big-thumb", "coat-over", "cafe-door"])
def test_each_is_a_registered_cutout_prop(name):
    entry = registry.get("prop", name)
    assert entry.style == "cutout" and entry.summary


def test_a_folder_is_shut_and_opens_in_its_spans():
    cv = canvas()
    cutout_handed.cv_folder(cv, cv.comp, open_spans=[(1.0, 2.0)], label="RESUME")
    assert {"cv-folder-shut", "cv-folder-open"} <= ids(cv) and "RESUME" in texts(cv)


@pytest.mark.parametrize(
    "kw",
    [
        {"scale": 0},
        {"scale": "big"},
        {"label": ""},
        {"label": "CURRICULUM"},
        {"open_spans": [(2.0, 1.0)]},
        {"open_spans": [(3.0, 4.0), (1.0, 2.0)]},
    ],
)
def test_a_folder_refuses_what_it_cannot_draw(kw):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_handed.cv_folder(cv, cv.comp, **kw)


def bytes_of(cv) -> str:
    return cv.scene.to_bytes().decode()


def test_a_post_shows_an_empty_heart_until_it_is_liked():
    cv = canvas()
    cutout_handed.phone_post(cv, cv.comp)
    assert "Be the first to like this." in bytes_of(cv) and "1 like" not in bytes_of(cv)
    cv = canvas()
    cutout_handed.phone_post(cv, cv.comp, liked_at=2.0)
    assert cutout_handed.RED in bytes_of(cv) and "1 like" in bytes_of(cv)


def test_a_message_comes_with_its_time():
    cv = canvas()
    cutout_handed.phone_post(cv, cv.comp, message=("Diane", "Thank you.\nSunday?"), message_at=3.0)
    assert "Sunday?" in bytes_of(cv)


def test_a_message_can_rest_higher_and_stays_put_by_default():
    def rest(**kwargs) -> float:
        cv = canvas()
        cutout_handed.phone_post(cv, cv.comp, message=("Diane", "Sunday?"), message_at=3.0, **kwargs)
        root = ET.fromstring(cv.scene.to_bytes())
        node = next(e for e in root.iter() if e.get("id") == "phone-post-message")
        track = next(e for e in node.iter() if e.get("property") == "y")
        return float(list(track)[-1].get("value"))

    assert rest() == 0.0
    assert rest(message_shift=-54.0) == -54.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"scale": 0}, "scale"),
        ({"name": ""}, "name has 1 to 16"),
        ({"date": "x" * 17}, "date has 1 to 16"),
        ({"liked_at": -1}, "liked_at"),
        ({"message": ("Diane", "hi")}, "both its text and its time"),
        ({"message_at": 2.0}, "both its text and its time"),
        ({"message": ("Diane", "x" * 31), "message_at": 1.0}, "up to 4 lines"),
        ({"message": ("Diane", "a\nb\nc\nd\ne"), "message_at": 1.0}, "up to 4 lines"),
    ],
)
def test_a_post_it_cannot_draw_is_refused(kwargs, match):
    cv = canvas()
    with pytest.raises(CHECKED, match=match):
        cutout_handed.phone_post(cv, cv.comp, **kwargs)


def test_a_thumb_is_scaled_and_refuses_a_bad_scale():
    cv = canvas()
    cutout_handed.big_thumb(cv, cv.comp, 100, 200, skin="#ABCDEF")
    assert "#ABCDEF" in bytes_of(cv)
    with pytest.raises(CHECKED, match="scale"):
        cutout_handed.big_thumb(cv, cv.comp, scale=-1)


def test_a_coat_goes_on_one_side_then_the_other():
    cv = canvas()
    cutout_handed.coat_over(cv, cv.comp, 1.0, 1.5)
    root = ET.fromstring(cv.scene.to_bytes())
    ids = {e.get("id") for e in root.iter()}
    assert {"coat-over-left", "coat-over-right"} <= ids


@pytest.mark.parametrize("args", [(-1.0, 2.0), (1.0, 0.0)])
def test_a_coat_at_no_time_is_refused(args):
    cv = canvas()
    with pytest.raises(CHECKED, match="a coat goes on at a time"):
        cutout_handed.coat_over(cv, cv.comp, *args)


def test_a_coat_ending_above_the_waist_is_refused():
    cv = canvas()
    with pytest.raises(CHECKED, match="below the waist"):
        cutout_handed.coat_over(cv, cv.comp, 1.0, 2.0, bottom=150)


def test_a_door_letters_its_sign():
    cv = canvas()
    cutout_handed.cafe_door(cv, cv.comp)
    assert "CLOSED" in bytes_of(cv)


def test_a_narrow_door_can_set_its_sign_smaller_and_the_default_stays():
    plain, small = canvas(), canvas()
    cutout_handed.cafe_door(plain, plain.comp)
    cutout_handed.cafe_door(small, small.comp, sign_size=22)
    assert bytes_of(plain) != bytes_of(small)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"width": 0}, "width"),
        ({"height": -1}, "height"),
        ({"sign_size": 0}, "sign_size"),
        ({"sign": ""}, "sign has 1 to 8"),
        ({"sign": "x" * 9}, "sign"),
    ],
)
def test_a_door_it_cannot_draw_is_refused(kwargs, match):
    cv = canvas()
    with pytest.raises(CHECKED, match=match):
        cutout_handed.cafe_door(cv, cv.comp, **kwargs)
