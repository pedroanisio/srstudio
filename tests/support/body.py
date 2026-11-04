"""Small body plans and canvases shared by drawing and agent clock regressions."""

from sr_core.scene import Scene

from srstudio import Canvas, body
from srstudio.limbs import Frame, Vec3


def plan():
    return body.compile_body(
        body.BodyScore(
            2,
            (body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),),
            (body.FootAnchor('left', Frame(Vec3(-0.12, 0, 0))), body.FootAnchor('right', Frame(Vec3(0.12, 0, 0)))),
        )
    )


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=8)
    return Canvas(scene, font_asset=None)
