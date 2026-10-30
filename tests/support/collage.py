"""What test_collage.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import Canvas, collage, flat_counter
from srstudio.canvas import Signature
from srstudio.toon import Pose

D = 6.0


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=collage.PAPER.background)
    return Canvas(
        scene,
        collage.PAPER,
        font_asset="luckiest-guy",
        namer=flat_counter("k"),
        signature=Signature() if signed else None,
    )


def pose(eyes="open", mouth="flat", arms="down", start=0.0) -> Pose:
    return Pose(start, eyes, mouth, arms)
