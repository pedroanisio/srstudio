"""The drawing modules' refusals are their own SrstudioError subclasses and still the ValueError they always were
(ADR 0034): canvas, camera, look and Ink."""

from __future__ import annotations

import pytest

from srstudio import camera, ink, look
from srstudio.canvas import CanvasError
from srstudio.errors import SrstudioError
from test_ink_layout import router_take, square_canvas


def refused(call, error: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_canvas_refusals_are_canvas_errors():
    _, cv = square_canvas()
    refused(lambda: cv.effect(" ", "blur", radius=2), CanvasError, "needs a name")
    refused(lambda: cv.instance(cv.comp, "i", "nowhere"), CanvasError, "no symbol 'nowhere'")
    refused(lambda: cv.gate(cv.group(cv.comp, "g"), [(2, 1)]), CanvasError, "visibility span")


def test_camera_refusals_are_camera_errors():
    _, cv = square_canvas()
    g = cv.group(cv.comp, "setup")
    refused(lambda: camera.crash_zoom(cv, g, at=-1, scale=1.4), camera.CameraError, "at -1")
    refused(lambda: camera.crash_zoom(cv, g, at=1, scale=1.4, duration=2), camera.CameraError, "slower than a snap")
    refused(lambda: camera.spin(cv, g, 1, turns=0), camera.CameraError, "turns >= 1")


def test_look_refusals_are_look_errors():
    _, cv = square_canvas()
    refused(lambda: look.grade(cv, cv.comp, "g", {}), look.LookError, "at least one effect")
    refused(lambda: look.depth(cv, cv.comp, "far", 0), look.LookError, "positive")


def test_ink_refusals_are_ink_errors():
    _, cv = square_canvas()
    g = cv.group(cv.comp, "r")
    refused(lambda: ink.router(cv, g, router_take(), 0, 0, power="sideways"), ink.InkError, "power")
    refused(lambda: ink.router(cv, g, router_take(), 0, 0, drop_at=9.0), ink.InkError, "drop_at")
    refused(lambda: ink.hand(cv, g, 0, 0, action="wave"), ink.InkError, "action")
    refused(lambda: ink.router_scene(cv, g, router_take(shot="moon")), ink.InkError, "unknown shot 'moon'")
