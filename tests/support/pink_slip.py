"""What test_pink_slip.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, flat_counter


def canvas(font: str | None = "font") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=6, background=OFFICE.background)
    return Canvas(scene, OFFICE, font_asset=font, namer=flat_counter("n"))
