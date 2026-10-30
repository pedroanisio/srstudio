"""What test_soft_props.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import WARM, Canvas, flat_counter


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10.0, background=WARM.background)
    return Canvas(scene, WARM, font_asset="caption-font", namer=flat_counter("k"))
