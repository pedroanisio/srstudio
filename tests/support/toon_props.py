"""What test_toon_props.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter

D = 6.0


def canvas(font="comic-neue") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=font, namer=flat_counter("k"))


def measure(text: str) -> float:
    return 20.0 * len(text)
