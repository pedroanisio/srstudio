#!/usr/bin/env python3
"""Draw creationbot's Slack avatar on the sr-core scene SDK: the studio's cactus as a robot, lit visor for a face.

Slack takes a square image from 512 to 2000 px and shows it at about 36 px in a chat row, so the drawing is one big
silhouette and no lettering. Usage: ``creationbot_avatar.py OUT.png`` with ``SRSTUDIO_ENGINE`` set; the scene document
is written beside the PNG.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sr_core.scene import Scene

from srstudio.canvas import Canvas, Palette

SIZE = 1024
INK = "#14202A"
SKY_TOP, SKY_LOW = "#FFC94D", "#F58A3C"
GREEN, GREEN_DARK, GREEN_LIGHT = "#3FB56B", "#23875A", "#7FDB8F"
POT, POT_DARK = "#D9774A", "#A94F33"
VISOR, EYE = "#101A24", "#6DF5E3"
FLOWER, FLOWER_CENTRE = "#FF5E8A", "#FFE27A"
LINE = 14  # the outline's width
LEFT_ARM = "M372 560 L284 560 Q190 560 190 466 L190 372"
RIGHT_ARM = "M652 480 L740 480 Q834 480 834 386 L834 292"
ARM = 118
BODY = (352, 150, 320, 580, 160)  # x, y, width, height, radius


def _body(cv: Canvas, g) -> None:
    """Arms and trunk as one silhouette: every ink shape first, then every green one, so the joins carry no line."""
    x, y, w, h, radius = BODY
    for arm in (LEFT_ARM, RIGHT_ARM):
        cv.path(g, arm, cv.clear, INK, ARM + 2 * LINE)
    cv.rect(g, x - LINE, y - LINE, w + 2 * LINE, h + 2 * LINE, INK, radius=radius + LINE)
    for arm in (LEFT_ARM, RIGHT_ARM):
        cv.path(g, arm, cv.clear, GREEN, ARM)
    cv.rect(g, x, y, w, h, GREEN, radius=radius)
    cv.path(g, "M402 250 Q402 214 436 196", cv.clear, GREEN_LIGHT, 22)
    for rib in (452, 572):
        cv.line(g, rib, 560, rib, 690, GREEN_DARK, 12)
    for sx, sy in ((190, 420), (834, 340), (258, 560), (760, 480)):
        cv.path(
            g, f"M{sx - 15} {sy - 15} L{sx + 15} {sy + 15} M{sx + 15} {sy - 15} L{sx - 15} {sy + 15}", None, INK, 10
        )


def _face(cv: Canvas, g) -> None:
    cv.rect(g, 382, 282, 260, 158, VISOR, INK, LINE, radius=66)
    eyes = cv.group(g, "avatar-eyes")
    for x in (432, 532):
        cv.ellipse(eyes, x, 318, 60, 86, EYE)
    cv.apply(eyes, cv.effect("avatar-eye-glow", "glow", radius=22, intensity=0.8, color=EYE))
    cv.path(g, "M452 500 Q512 556 572 500", cv.clear, INK, 18)


def _flower(cv: Canvas, g) -> None:
    for x, y in ((512, 96), (452, 134), (572, 134), (476, 196), (548, 196)):
        cv.ellipse(g, x - 44, y - 44, 88, 88, FLOWER, INK, LINE)
    cv.ellipse(g, 474, 112, 76, 76, FLOWER_CENTRE, INK, LINE)


def _pot(cv: Canvas, g) -> None:
    """The pot, its rim banded like a clapperboard: this bot makes films."""
    cv.path(g, "M322 760 L366 960 L658 960 L702 760 Z", cv.grad("avatar-pot", [(0, POT), (1, POT_DARK)]), INK, LINE)
    cv.rect(g, 280, 690, 464, 104, INK, radius=26)
    for x in range(300, 690, 70):
        cv.path(g, f"M{x + 34} 708 L{x + 72} 708 L{x + 38} 776 L{x} 776 Z", "#FFFFFF", cv.clear, 0)


def compose() -> Scene:
    """The one-frame scene of the avatar."""
    scene = Scene(version="auto")
    scene.add_project(width=SIZE, height=SIZE, fps="1", duration=1, background=SKY_LOW)
    cv = Canvas(scene, Palette(ink=INK, white="#FFFFFF"), font_asset=None, width=SIZE, height=SIZE)
    cv.rect(cv.comp, 0, 0, SIZE, SIZE, cv.grad("avatar-sky", [(0, SKY_TOP), (1, SKY_LOW)]))
    cv.ellipse(cv.comp, 232, 936, 560, 52, INK, opacity=0.22)
    bot = cv.group(cv.comp, "avatar-bot")
    _body(cv, bot)
    _pot(cv, bot)
    _face(cv, bot)
    _flower(cv, bot)
    return scene


def main(out: Path) -> None:
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    document = out.with_suffix(".scene.xml")
    document.write_bytes(compose().to_bytes())
    subprocess.run([os.environ["SRSTUDIO_ENGINE"], "render", str(document), "-t", "0", "-o", str(out)], check=True)
    for written in (document, out):
        written.chmod(0o600)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
