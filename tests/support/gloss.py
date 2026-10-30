"""What test_gloss.py shares with other test modules."""

from __future__ import annotations

from sr_core.scene import Scene

from srstudio import PLASTIC, Canvas, flat_counter
from srstudio.canvas import Signature
from srstudio.sample import SYSTEM_FONTS

FONT_FILE = next((f for f in SYSTEM_FONTS if f.exists()), None)


D = 4.0


def font() -> bytes:
    assert FONT_FILE is not None
    return FONT_FILE.read_bytes()


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PLASTIC.background)
    cv = Canvas(scene, PLASTIC, font_asset="f", namer=flat_counter("g"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv
