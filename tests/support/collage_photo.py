"""What test_collage_photo.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import COLLAGE, Canvas
from srstudio.canvas import Signature
from srstudio.collage_group import Place

PLACES = {"gary": Place(230, 1800, 0.55), "kai": Place(850, 1800, 0.5), "rosa": Place(540, 1800, 0.58)}


LAUGH = {"gary": ("wide", "o", "shrug"), "kai": ("closed", "grin", "face"), "rosa": ("closed", "grin", "hold")}


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=20.0, background="#ffe5d9")
    return Canvas(scene, COLLAGE.palettes[0], font_asset="caption", signature=Signature())
