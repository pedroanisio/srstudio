"""A one-way video interview's invented window, and what comes through the door behind the candidate."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_recording
from support.tip_tablet import canvas


def scene(cv) -> str:
    return cv.scene.to_bytes().decode()


def ids(cv) -> list[str]:
    return [e.get("id", "") for e in ET.fromstring(cv.scene.to_bytes()).iter("group")]


def test_the_window_counts_down_one_label_a_second_from_where_it_starts():
    cv = canvas()
    cutout_recording.recording_window(cv, cv.comp, seconds=30, end=12.5)
    text = scene(cv)
    assert "0:30" in text and "0:18" in text
    assert "0:17" not in text  # 12.5 s in, the clock has only reached 0:18


def test_a_stopped_window_holds_its_last_second():
    cv = canvas()
    cutout_recording.recording_window(cv, cv.comp, seconds=30, end=12.5, stop=5.2)
    text = scene(cv)
    assert "0:25" in text and "0:24" not in text


@pytest.mark.parametrize(
    "options",
    [
        dict(seconds=0, end=5.0),
        dict(seconds=601, end=5.0),
        dict(seconds=30, end=0),
        dict(seconds=30, end=5.0, stop=9.0),
        dict(seconds=30, end=5.0, stop=-1.0),
        dict(seconds=30.5, end=5.0),
        dict(seconds=30, end=float("nan")),
    ],
)
def test_a_window_refuses_a_clock_it_cannot_show(options):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        cutout_recording.recording_window(cv, cv.comp, **options)


def test_a_meter_panel_letters_each_meter():
    cv = canvas()
    cutout_recording.meter_panel(cv, cv.comp, 80, 1250, (("EYES", ((0, 0.6), (3, 0.1))), ("SMILE", ((0, 0.9),))))
    text = scene(cv)
    assert "EYES" in text and "SMILE" in text


@pytest.mark.parametrize(
    "meters",
    [
        (),
        (("A", ((0, 0.1),)),) * 5,
        (("", ((0, 0.1),)),),
        (("A LABEL MUCH TOO LONG", ((0, 0.1),)),),
        (("EYES", ()),),
        (("EYES", ((0, 1.2),)),),
        (("EYES", ((0, -0.1),)),),
        (("EYES", ((3, 0.1), (1, 0.2))),),
    ],
)
def test_a_meter_panel_refuses_what_a_bar_cannot_show(meters):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        cutout_recording.meter_panel(cv, cv.comp, 80, 1250, meters)


def test_a_face_box_shows_only_in_its_spans():
    cv = canvas()
    cutout_recording.face_box(cv, cv.comp, 400, 690, 300, spans=[(2.0, 4.0)], id="box")
    assert "box" in ids(cv)


@pytest.mark.parametrize("size", [0, -5, float("nan"), "big"])
def test_a_face_box_refuses_a_size_that_is_not_a_size(size):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        cutout_recording.face_box(cv, cv.comp, 400, 690, size)


def test_a_green_tick_lands_at_its_time():
    cv = canvas()
    cutout_recording.green_tick(cv, cv.comp, 900, 500, at=3.0, id="tick")
    assert "tick" in ids(cv)


@pytest.mark.parametrize("options", [dict(at=-1.0), dict(at=1.0, scale=0), dict(at=float("nan"))])
def test_a_green_tick_refuses_a_time_or_scale_it_cannot_land_on(options):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        cutout_recording.green_tick(cv, cv.comp, 900, 500, **options)


def test_a_bowl_and_a_spoon_have_their_own_groups():
    cv = canvas()
    cutout_recording.cereal_bowl(cv, cv.comp, 500, 900, id="bowl")
    cutout_recording.spoon(cv, cv.comp, 600, 900, id="spoon")
    assert {"bowl", "spoon"} <= set(ids(cv))


@pytest.mark.parametrize("draw", [cutout_recording.cereal_bowl, cutout_recording.spoon])
@pytest.mark.parametrize("scale", [0, -1, float("nan")])
def test_a_bowl_or_a_spoon_refuses_a_scale(draw, scale):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        draw(cv, cv.comp, 500, 900, scale=scale)


def test_a_door_that_opens_keys_its_panel_and_one_that_does_not_stays_shut():
    shut, opening = canvas(), canvas()
    cutout_recording.room_door(shut, shut.comp, 520, 960)
    cutout_recording.room_door(opening, opening.comp, 520, 960, opens=4.0)
    assert 'property="scaleX"' not in scene(shut)
    assert 'property="scaleX"' in scene(opening) or "scaleX" in scene(opening).split("room-door-panel", 1)[1]


@pytest.mark.parametrize("options", [dict(opens=-1.0), dict(opens=float("nan")), dict(scale=0)])
def test_a_door_refuses_a_time_or_scale_it_cannot_use(options):
    cv = canvas()
    with pytest.raises(cutout_recording.CutoutRecordingError):
        cutout_recording.room_door(cv, cv.comp, 520, 960, **options)
