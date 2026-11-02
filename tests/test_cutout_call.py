"""A video call on a laptop, and the phone beside it that will not leave a man alone."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_call
from support.tip_tablet import canvas


def scene(cv) -> str:
    return cv.scene.to_bytes().decode()


def ids(cv) -> list[str]:
    return [e.get("id", "") for e in ET.fromstring(cv.scene.to_bytes()).iter("group")]


def test_a_tile_draws_whoever_is_on_the_call_inside_its_frame():
    cv = canvas()
    seen = []

    def sitter(group):
        seen.append(group)

    cutout_call.video_tile(cv, cv.comp, inside=sitter, plate="HIRING MANAGER")
    assert len(seen) == 1
    assert "HIRING MANAGER" in scene(cv)


def test_the_frame_is_drawn_over_the_sitter_so_nobody_hangs_out_of_the_tile():
    cv = canvas()
    cutout_call.video_tile(cv, cv.comp, inside=lambda g: cv.group(g, "sitter"))
    order = ids(cv)
    assert order.index("sitter") < order.index("video-tile-frame")


def test_a_tile_letters_only_what_the_reel_gives_it():
    cv = canvas()
    cutout_call.video_tile(cv, cv.comp)
    assert not [e for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("shape") == "text"]


@pytest.mark.parametrize(
    "options",
    [
        dict(width=0),
        dict(height=float("nan")),
        dict(plate="   "),
        dict(plate="X" * (cutout_call.PLATE_CHARS + 1)),
        dict(inside="manager"),
    ],
)
def test_a_tile_refuses_what_it_cannot_draw(options):
    cv = canvas()
    with pytest.raises(cutout_call.CutoutCallError):
        cutout_call.video_tile(cv, cv.comp, **options)


def test_a_line_lands_on_the_phone_at_its_time_and_stays():
    cv = canvas()
    cutout_call.desk_phone(cv, cv.comp, lines=[(1.0, "CALL ME"), (1.5, "DON'T WORRY")])
    text = scene(cv)
    assert "CALL ME" in text and "DON'T WORRY" in text
    assert "desk-phone-line-1" in ids(cv)


def test_a_phone_that_buzzes_shakes_only_when_asked():
    still, buzzing = canvas(), canvas()
    cutout_call.desk_phone(still, still.comp)
    cutout_call.desk_phone(buzzing, buzzing.comp, buzzes=[(0.0, 0.4)])
    assert 'property="x"' not in scene(still).split("desk-phone-body", 1)[1]
    assert 'property="x"' in scene(buzzing).split("desk-phone-body", 1)[1]


def test_a_phone_lying_face_down_turns_over_at_its_time():
    cv = canvas()
    cutout_call.desk_phone(cv, cv.comp, title="MOM (9)", turns=2.0)
    assert 'property="scaleX"' in scene(cv)
    assert "desk-phone-back" in ids(cv)


def test_a_phone_face_up_has_no_back_to_show():
    cv = canvas()
    cutout_call.desk_phone(cv, cv.comp, title="MOM")
    assert "desk-phone-back" not in ids(cv)


@pytest.mark.parametrize(
    "options",
    [
        dict(scale=0),
        dict(scale=float("inf")),
        dict(lines=[(1.0, " ")]),
        dict(lines=[(2.0, "A"), (1.0, "B")]),
        dict(lines=[(-1.0, "A")]),
        dict(lines=[(0.0, "X" * (cutout_call.PHONE_CHARS + 1))]),
        dict(lines=[(float(k), "A") for k in range(cutout_call.PHONE_LINES + 1)]),
        dict(title="X" * (cutout_call.PHONE_CHARS + 1)),
        dict(buzzes=[(2.0, 1.0)]),
        dict(turns=-1.0),
    ],
)
def test_a_phone_refuses_what_it_cannot_draw(options):
    cv = canvas()
    with pytest.raises(cutout_call.CutoutCallError):
        cutout_call.desk_phone(cv, cv.comp, **options)
