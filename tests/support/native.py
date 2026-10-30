"""What test_native.py shares with other test modules."""

from __future__ import annotations

from pathlib import Path

from sr_core.scene import Scene

from srstudio import VERTICAL, Canvas
from srstudio.sample import SYSTEM_FONTS

FONT = next((f for f in SYSTEM_FONTS if f.exists()), Path("DejaVuSans-Bold.ttf"))


def canvas(duration=4.0, width=1080, height=1920, safe=True) -> tuple[Scene, Canvas, object]:
    scene = Scene(version="auto")
    project = scene.add_project(width=width, height=height, fps="30", duration=duration, background="#20303A")
    if safe:
        VERTICAL.declare(scene, project)
    output = scene.add_output(id="main", path="out.mp4", codec="h264", width=width, height=height, fps="30")
    cv = Canvas(scene, width=width, height=height)
    cv.assets.add_font(id="caption-font", src=FONT.name, family="DejaVu Sans", weight="700")
    return scene, cv, output


# -- transitions ------------------------------------------------------------------------------------------------------
def shots(cv: Canvas):
    seq = cv.comp.add_sequence(id="shots")
    a = seq.add_group(id="shot-a", end=2.2)
    cv.rect(a, 70, 200, 400, 300, "#E6AA92")
    b = seq.add_group(id="shot-b", end=4.0)
    cv.ellipse(b, 120, 200, 300, 300, "#BFCFCA")
    return seq
