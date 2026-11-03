"""The held_frames build of 31 Oct's library, kept so the fixed how-are-you master rebuilds from a commit (ADR 0216).

A canvas with ``held_frames=True`` keys every held change half a frame before the first frame that shows it, so no
frame repeats the one before; interpolated keys stay where they are, and a canvas without it keys as before.
"""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas
from srstudio.held_keys import HeldKeyError, held_key


def canvas(held_frames: bool, fps: str = "30") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps=fps, duration=3)
    return Canvas(scene, OFFICE, held_frames=held_frames)


def keys_on(cv: Canvas, id: str) -> dict[str, list[float]]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return {
        a.get("property"): [float(k.get("time")) for k in a.findall("key")]
        for a in root.find(f".//group[@id='{id}']").findall("animate")
    }


def test_a_held_change_on_a_frame_is_keyed_half_a_frame_before_it():
    cv = canvas(held_frames=True)
    g = cv.group(cv.comp, "g")
    cv.keys(g, "opacity", [(0, 0), (2 / 30, 1), (0.266667, 0)])
    assert keys_on(cv, "g")["opacity"] == pytest.approx([0.0, 1.5 / 30, 7.5 / 30], abs=1e-12)


def test_interpolated_keys_stay_where_they_are():
    cv = canvas(held_frames=True)
    g = cv.group(cv.comp, "g")
    cv.keys(g, "y", [(0, 0), (0.266667, 8)], hold=False)
    assert keys_on(cv, "g")["y"] == [0.0, 0.266667]


def test_a_canvas_without_held_frames_keys_as_before():
    cv = canvas(held_frames=False)
    g = cv.group(cv.comp, "g")
    cv.keys(g, "opacity", [(0, 0), (0.266667, 1)])
    assert keys_on(cv, "g")["opacity"] == [0.0, 0.266667]


def test_a_ntsc_rate_keys_half_a_frame_of_its_own():
    cv = canvas(held_frames=True, fps="30000/1001")
    g = cv.group(cv.comp, "g")
    cv.keys(g, "opacity", [(0, 0), (1001 / 30000, 1)])
    assert keys_on(cv, "g")["opacity"] == pytest.approx([0.0, 0.5 * 1001 / 30000], abs=1e-12)


@pytest.mark.parametrize("time", [-1.0, float("nan")])
def test_a_bad_time_is_refused(time):
    with pytest.raises(HeldKeyError, match="finite second from 0") as caught:
        held_key(time, 30)
    assert caught.value.code == "held_key.time"


@pytest.mark.parametrize("fps", ["241", "480"])  # the scene schema refuses 0 and words itself
def test_a_canvas_on_a_rate_with_no_grid_is_refused(fps):
    cv = canvas(held_frames=True, fps=fps)
    g = cv.group(cv.comp, "g")
    with pytest.raises(HeldKeyError):
        cv.keys(g, "opacity", [(0, 0), (0.5, 1)])
