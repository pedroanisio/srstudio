"""What test_stick_car.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter


def canvas(font: str | None = "inter") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"))
