"""A prop mesh and a canvas for interaction scenes, shared by the interaction and camera-track tests."""

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import Vec3
from srstudio.limbs.interaction import Face, PropMesh


def mesh():
    return PropMesh(
        "panel",
        (
            Face(
                "surface",
                (Vec3(-0.3, 0.6, 0.1), Vec3(0.3, 0.6, 0.1), Vec3(0.3, 1.2, 0.1), Vec3(-0.3, 1.2, 0.1)),
                "#ef9988",
            ),
        ),
    )


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=800, height=800, fps="24", duration=2)
    return Canvas(scene, font_asset=None)
