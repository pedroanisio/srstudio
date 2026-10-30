"""What test_tip_tablet.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import CAFE, Canvas, flat_counter


def canvas(font: str | None = "font") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4, background=CAFE.background)
    return Canvas(scene, CAFE, font_asset=font, namer=flat_counter("n"))
