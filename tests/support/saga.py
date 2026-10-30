"""What test_saga.py shares with other test modules."""

from __future__ import annotations

from sr_core.scene import Scene

from srstudio import VOID, Canvas, flat_counter
from srstudio.canvas import Signature

D = 4.0


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=VOID.background)
    cv = Canvas(scene, VOID, font_asset="f", namer=flat_counter("s"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv
