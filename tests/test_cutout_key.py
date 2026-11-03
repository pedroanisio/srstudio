"""The one short line a Cutout reel opens on."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import cutout_key
from srstudio.fonts import text_width
from srstudio.show import BUG_BOX
from support.tip_tablet import canvas

FONT = next(Path("/usr/share/fonts").rglob("DejaVuSans-Bold.ttf")).read_bytes()


def bar(cv) -> ET.Element:
    root = ET.fromstring(cv.scene.to_bytes())
    group = next(e for e in root.iter() if e.get("id") == "key-line")
    return next(e for e in group.iter() if e.get("shape") == "rect")


def test_the_bar_is_as_wide_as_its_words_in_the_reels_own_font():
    cv = canvas()
    cutout_key.key_line(cv, cv.comp, "ONE POSITION", 0.0, 2.6, font=FONT)
    width = float(bar(cv).get("width"))
    assert width == pytest.approx(text_width(FONT, "ONE POSITION", cutout_key.SIZE) + cutout_key.PAD, abs=0.01)


def test_it_shows_only_between_its_times():
    cv = canvas()
    node = cutout_key.key_line(cv, cv.comp, "ONE POSITION", 0.2, 2.6, font=FONT)
    assert (node.start, node.end) == (0.2, 2.6)


def test_the_default_place_is_under_the_shows_bug():
    assert cutout_key.TOP >= BUG_BOX[3]


@pytest.mark.parametrize("text", ["", "   ", "A LINE MUCH TOO LONG TO SIT ON ONE BAR OF A PHONE"])
def test_a_line_that_cannot_sit_on_the_bar_is_refused(text):
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.key_line(cv, cv.comp, text, 0.0, 2.0, font=FONT)


@pytest.mark.parametrize("span", [(-1.0, 2.0), (2.0, 2.0), (3.0, 2.0), (0.0, float("inf"))])
def test_a_span_that_ends_before_it_starts_is_refused(span):
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.key_line(cv, cv.comp, "ONE POSITION", *span, font=FONT)


def test_it_never_sits_on_the_bug():
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError, match="bug"):
        cutout_key.key_line(cv, cv.comp, "M" * 15, 0.0, 2.0, font=FONT, top=240)


def test_a_camera_keys_a_set_on_its_frames_and_keeps_scale_even():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    cutout_key.camera(cv, group, [(0.0, (1.0, 0.0, 0.0)), (2.0, (1.5, -270.0, -300.0))])
    text = cv.scene.to_bytes().decode()
    for prop in ("scaleX", "scaleY", "x", "y"):
        assert f'property="{prop}"' in text


def test_the_frame_may_reach_as_far_as_the_set_is_painted():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    cutout_key.camera(cv, group, [(0.0, (1.0, 200.0, 0.0))], box=(-300.0, 0.0, 1380.0, 1920.0))


@pytest.mark.parametrize(
    "frame",
    [
        (1.0, 40.0, 0.0),  # the set's left edge comes into frame
        (1.0, -40.0, 0.0),  # its right edge
        (1.2, 0.0, 40.0),  # its top
        (1.2, 0.0, -600.0),  # its foot
        (0.8, 0.0, 0.0),  # smaller than the frame
        (0.0, 0.0, 0.0),
        (float("nan"), 0.0, 0.0),
    ],
)
def test_a_camera_refuses_a_frame_that_shows_where_the_set_ends(frame):
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.camera(cv, group, [(0.0, frame)])


def test_a_camera_refuses_frames_out_of_order():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.camera(cv, group, [(1.0, (1.0, 0.0, 0.0)), (0.5, (1.0, 0.0, 0.0))])


def test_a_camera_needs_a_frame():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.camera(cv, group, [])


def test_two_frames_at_one_time_are_a_hard_cut():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    wide, close = (1.0, 0.0, 0.0), (1.5, -270.0, -300.0)
    cutout_key.camera(cv, group, [(0.0, wide), (2.0, wide), (2.0, close), (3.0, close)])
    root = ET.fromstring(cv.scene.to_bytes())
    scales = [e for e in root.iter() if e.get("property") == "scaleX"]
    times = [float(k.get("time")) for k in scales[0]]
    assert times == pytest.approx([0.0, 2.0 - cutout_key.CUT, 2.0, 3.0])


def test_between_two_frames_at_different_times_the_camera_moves():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    cutout_key.camera(cv, group, [(0.0, (1.0, 0.0, 0.0)), (2.0, (1.2, -108.0, -192.0))])
    root = ET.fromstring(cv.scene.to_bytes())
    scales = [e for e in root.iter() if e.get("property") == "scaleX"]
    assert [float(k.get("value")) for k in scales[0]] == pytest.approx([1.0, 1.2])


def test_a_cut_at_the_first_instant_has_nothing_to_cut_from():
    cv = canvas()
    group = cv.group(cv.comp, "a-set")
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.camera(cv, group, [(0.0, (1.0, 0.0, 0.0)), (0.0, (1.2, -108.0, -192.0))])
