#!/usr/bin/env python3
"""Car Vibe Study — ten seconds of a cartoon redrawn from scratch: the worked example of the default drawing method.

    python3 _car_cel.py PROJECT             # → PROJECT/plates (the car's back, front and under plates)
    python3 car_vibe_study.py PROJECT       # → PROJECT/car-vibe-study.scene.xml (silent; PROJECT holds script.json,
                                            #   assets/Inter-Bold.ttf and plates/)

Two friends in a small mint car sing along to the playlist: a wide shot of the car, the passenger with a hand over
her face, the driver grinning at the window, the passenger again. The car is a 3D model drawn as cel plates by
_car_cel.py (run it first: it writes PROJECT/plates); the people and the city are drawn here in the reference's own
frame (480 x 802 px, scaled 2.25 onto the 1080 x 1920 Stick frame). The body rides the beat over wheels that stay on
the road and turn. The beat, the size of the bounce and the wheels' speed are numbers measured once from the
reference's soundtrack and picture; no frame, footage or audio of the reference is read or embedded. A study of another
creator's cartoon, kept to prove the library (ADR 0091), never a release: it declares no post and no part, and stays out
of episodes/ so nothing ships it.
"""

import math
import os
import sys
from pathlib import Path

import _car_cel as car

from srstudio import STICK, Episode, EpisodeSpec, brush, fonts, look, music, on_beat, subtitles, vehicle

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = Path(sys.argv[1]).resolve()
CAPTION = "The playlist understood the vibe"
SCALE = 2.25  # the reference's 480 px width onto the frame's 1080
TOP = 58  # the reference is 802 px tall, 1804 on the frame: the rest is drawn past its edges
SHOTS = {"wide": (0.0, 3.4), "windshield": (3.4, 6.4), "driver": (6.4, 8.0), "again": (8.0, 10.0)}

INK = "#15121a"
GRAY = "#d6ced3"
CAP = "#c9c0c3"
CAP_DARK = "#aaa2a8"
TAN = "#deb58c"
TAN_DARK = "#b98c66"
SKY_TOP = "#0a92d1"
SKY_LOW = "#6fc3df"
PINK = "#e3afb3"
PINK_DARK = "#c98c99"
ORANGE = "#e8935c"
ORANGE_DARK = "#c26d3a"
YELLOW = "#f0b94d"
GLASS = "#2f8fc4"
LEAF = "#6f9a54"
LEAF_DARK = "#4d7b45"
ROAD = "#575d88"
PAVE = "#dea3af"
SHIRT = "#ece7ea"
GROOVE = music.Groove(bpm=60 / 0.465, offset=1.535)  # the pulse and the first bar of the reference's music, as measured
BOUNCE = {"wide": 7.0, "windshield": 7.0, "driver": 9.6}  # px on the frame, measured on the reference's body
TYRE_BOUNCE = 2.4
BAR_HIT = 1.4  # how much further the body rises on the hit that opens each bar of four
GRADE = {
    "bloom": dict(threshold=0.9, radius=20, intensity=0.16),
    "vignette": dict(amount=0.1, radius=1.1, softness=0.85, color="#1a2030"),
    "film-grain": dict(amount=0.006, size=1.0, seed=2026),
}

ep = Episode(
    EpisodeSpec(
        slug="car-vibe-study",
        title="Car Vibe Study",
        description="A silent ten-second study: two friends sing along in a small mint car, redrawn with the SDK.",
        root=ROOT,
        seed=2026,
        style=STICK,
        local_time=False,
        language="en-US",
        output="study/car-vibe-cel.mp4",
        output_options=dict(
            codec="h264", container="mp4", fps="24", crf="16", preset="medium", pixelFormat="yuv420p", faststart=True
        ),
        accessibility=dict(description="A cartoon of two friends laughing and singing in a small green car."),
        signature=False,
    )
)
cv = ep.cv
NONE = cv.clear
CLOCK = [0.0]  # the start of the shot being drawn: every time below is on the episode's own clock


def at(t: float) -> float:
    return CLOCK[0] + t


def path(g, d: str, fill: str, stroke: str | None = None, sw: float = 0, **kw):
    return cv.path(g, d, fill=fill, stroke=stroke or INK, sw=sw, **kw)


def disc(
    g, cx: float, cy: float, r: float, fill: str, stroke: str | None = None, sw: float = 0, ry: float | None = None
):
    ry = r if ry is None else ry
    return cv.ellipse(g, cx - r, cy - ry, 2 * r, 2 * ry, fill, stroke or INK, sw)


def block(g, x: float, y: float, w: float, h: float, fill: str, radius: float = 0, stroke: str | None = None, sw=0):
    return cv.rect(g, x, y, w, h, fill, stroke or INK, sw, radius=radius)


def mix(colour: str, other: str, share: float) -> str:
    """``colour`` moved ``share`` of the way to ``other``, both ``#rrggbb``."""
    a, b = (tuple(int(c[i : i + 2], 16) for i in (1, 3, 5)) for c in (colour, other))
    return "#" + "".join(f"{round(x + (y - x) * share):02x}" for x, y in zip(a, b, strict=True))


def shape_d(shape: brush.Shape) -> str:
    """A brush shape as a path in the reference's own pixels."""
    out = [f"M {shape[0]:g} {shape[1]:g}"]
    for i in range(2, len(shape), 6):
        out.append("C " + " ".join(f"{v:g}" for v in shape[i : i + 6]))
    return " ".join(out) + " Z"


def ring(cx: float, cy: float, rx: float, ry: float | None = None, n: int = 10, tilt: float = 0.0):
    """``n`` points round an ellipse, turned ``tilt`` degrees: the outline a hand would follow."""
    ry = rx if ry is None else ry
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def inked_fill(g, points, fill, weight: float = 1.7, seed: float = 0.0):
    """A shape filled with ``fill`` and edged with the brush's ink line, heavier on its shaded side."""
    cv.path(g, shape_d(brush.inked(points, weight, seed=seed)), fill=INK, stroke=NONE, sw=0)
    return cv.path(g, shape_d(brush.outline(points)), fill=fill, stroke=NONE, sw=0)


def fill_only(g, points, fill, opacity: float = 1.0):
    return cv.path(g, shape_d(brush.outline(points)), fill=fill, stroke=NONE, sw=0, opacity=opacity)


def ink_line(g, points, weight: float, pressure: brush.Pressure = brush.TAPERED):
    return cv.path(g, shape_d(brush.stroke(points, weight, pressure)), fill=INK, stroke=NONE, sw=0)


def ink_blob(g, cx: float, cy: float, rx: float, ry: float | None = None, tilt: float = 0.0, fill: str = INK):
    return cv.path(
        g, shape_d(brush.ellipse(cx, cy, rx, ry if ry is not None else rx, tilt)), fill=fill, stroke=NONE, sw=0
    )


def stick(g, x1: float, y1: float, x2: float, y2: float, width: float = 3.4, bow: float = 0.05):
    """A limb: one brush line with a slight bow, as a hand draws a straight stroke."""
    dx, dy = x2 - x1, y2 - y1
    mid = ((x1 + x2) / 2 - dy * bow, (y1 + y2) / 2 + dx * bow)
    ink_line(g, [(x1, y1), mid, (x2, y2)], width * 1.1, brush.EVEN)


def head_points(cx: float, cy: float, r: float, seed: float):
    return brush.wobble(ring(cx, cy, r, n=11), r * 0.014, True, steps=2, seed=seed)


def shade_head(g, pts, cx: float, cy: float, r: float, colour: str = "#bdb4ba"):
    """A crescent of shade along the head's lower right, away from the light."""
    fill_only(g, brush.crescent(pts, r * 0.22, (cx - r * 0.35, cy - r * 0.3)), colour, 0.85)


# -- the city behind the glass -------------------------------------------------------------------------------------
def windows(g, x: float, y: float, cols: int, rows: int, w: float, h: float, gap_x: float, gap_y: float, fill=GLASS):
    pane = cv.grad("study-pane", ((0, mix(fill, "#ffffff", 0.45)), (1, fill)), (0, 0, 0, 1))
    for r in range(rows):
        for c in range(cols):
            wx, wy = x + c * (w + gap_x), y + r * (h + gap_y)
            block(g, wx, wy, w, h, "#e9f1f4")
            lit = (r * 3 + c * 5) % 7 == 2
            block(g, wx + 1.5, wy + 1.5, w - 3, h - 3, "#f6d27c" if lit else pane)
            if not lit:
                block(g, wx + 1.5, wy + 1.5, (w - 3) * 0.5, 2, "#ffffff88")


def wall(colour: str, light: float = 0.3) -> str:
    return cv.grad(f"study-wall-{colour[1:]}", ((0, mix(colour, "#ffffff", light)), (1, colour)), (0, 0, 1, 0))


def building(
    g, x: float, y: float, w: float, h: float, wall_colour: str, side: str, roof: str | None = None, wins=None
):
    block(g, x, y, w, h, wall(wall_colour))
    block(g, x + w * 0.82, y, w * 0.18, h, wall(side, 0.12))
    block(g, x, y + h - 14, w, 14, "#00000018")  # the street's shade at the foot
    if roof:
        block(g, x - 4, y - 9, w + 8, 12, roof, 2)
        block(g, x - 4, y + 1, w + 8, 4, "#00000022")
    if wins:
        windows(g, x + 8, y + 14, *wins)


def tree(g, cx: float, base: float, r: float):
    leaf = cv.rgrad("study-leaf", ((0, "#a6cf74"), (0.55, LEAF), (1, LEAF_DARK)), (0.38, 0.3, 0.8))
    disc(g, cx + r * 0.1, base + 1, r * 0.8, "#00000026", ry=r * 0.12)  # the shade on the pavement
    ink_line(g, [(cx, base), (cx + r * 0.03, base - r * 0.5), (cx - r * 0.02, base - r * 0.95)], r * 0.16, brush.EVEN)
    for dx, dy, k in ((-0.55, -1.15, 0.62), (0.5, -1.2, 0.6), (0, -1.55, 0.7), (-0.2, -1.0, 0.7), (0.35, -0.95, 0.55)):
        disc(g, cx + dx * r, base + dy * r, r * k, leaf)
    for dx, dy, k in ((-0.35, -0.85, 0.34), (0.45, -0.8, 0.3), (0.1, -1.3, 0.28)):
        disc(g, cx + dx * r, base + dy * r, r * k, "#3f6b3c88")
    for dx, dy, k in ((-0.45, -1.5, 0.2), (0.2, -1.8, 0.18), (-0.1, -1.2, 0.16)):
        disc(g, cx + dx * r, base + dy * r, r * k, "#c4e69a77")


def city(g, kind: str):
    """The far plane, blurred; ``kind`` picks which buildings stand where in the shot."""
    sky = cv.grad("study-sky", ((0, SKY_TOP), (0.55, "#37a9dc"), (1, SKY_LOW)), (0, 0, 0, 1))
    block(g, -40, -80, 560, 700, sky)
    disc(g, 330, 60, 60, "#ffffff66", ry=14)
    disc(g, 60, 40, 55, "#ffffff55", ry=11)
    if kind == "wide":
        building(g, 190, 215, 118, 140, PINK, PINK_DARK, "#c26d86", (4, 3, 14, 18, 8, 12))
        building(g, 298, 98, 75, 130, "#4d8fc8", "#3b78b0", "#f2f2f2", (3, 5, 11, 11, 6, 9))
        building(g, 20, 65, 160, 215, "#f3c38d", "#d99d63", YELLOW, (4, 6, 20, 21, 6, 8))
        block(g, 35, 85, 85, 140, "#1c8cb0", 2)  # the glass tower's face
        for k in range(1, 5):
            cv.line(g, 35 + k * 17, 85, 35 + k * 17, 225, "#bfe6f0", 1.4)
        for k in range(1, 8):
            cv.line(g, 35, 85 + k * 17.5, 120, 85 + k * 17.5, "#bfe6f0", 1.4)
        building(g, 440, 125, 80, 120, ORANGE, ORANGE_DARK, "#f6c14a", (3, 3, 14, 16, 6, 10))
        block(g, -40, 330, 560, 60, PAVE)
        block(g, -40, 372, 560, 22, "#c98c99")
        for cx, base, r in ((190, 345, 52), (240, 350, 44), (440, 350, 55), (10, 350, 40)):
            tree(g, cx, base, r)
        block(g, -40, 392, 560, 460, ROAD)
    elif kind == "windshield":
        building(g, -10, 120, 130, 190, PINK, PINK_DARK, "#c26d86", (4, 4, 15, 16, 8, 10))
        building(g, 255, 135, 160, 260, ORANGE, ORANGE_DARK, "#f6c14a", (4, 6, 22, 20, 8, 10))
        building(g, 380, 60, 110, 120, "#4d8fc8", "#3b78b0", "#f2f2f2", (3, 4, 14, 14, 8, 10))
        building(g, 130, 150, 90, 150, "#f3c38d", "#d99d63", None, (3, 4, 14, 14, 8, 12))
        for cx, base, r in ((40, 350, 70), (440, 400, 60), (120, 400, 60), (330, 410, 38)):
            tree(g, cx, base, r)
        block(g, -40, 395, 560, 70, PAVE)
        block(g, -40, 450, 560, 400, ROAD)
    else:  # "driver"
        building(g, 240, 210, 190, 150, PINK, PINK_DARK, "#c26d86", (5, 3, 16, 16, 10, 12))
        building(g, -20, 20, 140, 230, ORANGE, ORANGE_DARK, "#f6c14a", (3, 6, 22, 20, 8, 10))
        building(g, 130, 90, 90, 160, "#4d8fc8", "#3b78b0", "#f2f2f2", (3, 5, 14, 14, 6, 10))
        for cx, base, r in ((40, 420, 70), (250, 430, 60), (430, 430, 55)):
            tree(g, cx, base, r)
        block(g, -40, 420, 560, 90, PAVE)
        block(g, -40, 490, 560, 400, ROAD)


# -- the two friends --------------------------------------------------------------------------------------------------
def teeth(g, x: float, y: float, w: float, h: float):
    """A wide grin: a dark mouth with a row of teeth along its top and a hint of tongue."""
    fill_only(g, [(x, y), (x + w * 0.5, y - h * 0.05), (x + w, y), (x + w * 0.82, y + h * 0.82), (x + w * 0.5, y + h),
                  (x + w * 0.18, y + h * 0.82)], INK)  # fmt: skip
    fill_only(g, [(x + w * 0.05, y + h * 0.04), (x + w * 0.5, y), (x + w * 0.95, y + h * 0.04),
                  (x + w * 0.88, y + h * 0.48),
                  (x + w * 0.5, y + h * 0.52), (x + w * 0.12, y + h * 0.48)], "#f6f3f4")  # fmt: skip
    for k in (0.3, 0.5, 0.7):
        cv.line(g, x + w * k, y + h * 0.05, x + w * k, y + h * 0.48, "#b9b2b8", 0.8)
    ink_blob(g, x + w * 0.5, y + h * 0.84, w * 0.2, h * 0.12, 0, "#c95a68")


def grin_shut(g, x: float, y: float, w: float):
    ink_line(g, [(x, y), (x + w / 2, y + w * 0.26), (x + w, y - w * 0.02)], 3.0)


def driver_head(g, cx: float, cy: float, r: float, mouth_open: bool):
    """The driver: a round head under a backwards cap, eyes wide, a grin."""
    pts = head_points(cx, cy, r, 1.0)
    inked_fill(g, pts, GRAY, 1.7, 1.0)
    shade_head(g, pts, cx, cy, r)
    crown = [(cx - r * 1.0, cy - r * 0.15), (cx - r * 0.92, cy - r * 0.7), (cx - r * 0.4, cy - r * 1.0),
             (cx + r * 0.2, cy - r * 1.03), (cx + r * 0.62, cy - r * 0.9), (cx + r * 0.8, cy - r * 0.55),
             (cx + r * 0.3, cy - r * 0.48), (cx - r * 0.1, cy - r * 0.42), (cx - r * 0.55, cy - r * 0.3)]  # fmt: skip
    inked_fill(g, crown, CAP, 1.5, 2.0)
    fill_only(g, brush.crescent(crown, r * 0.14, (cx, cy - r * 0.85)), CAP_DARK, 0.8)
    inked_fill(g, [(cx - r * 1.0, cy - r * 0.15), (cx - r * 1.4, cy + r * 0.12), (cx - r * 1.16, cy + r * 0.22),
                   (cx - r * 0.7, cy + r * 0.02)], CAP_DARK, 1.5, 3.0)  # fmt: skip
    block(g, cx - r * 0.12, cy - r * 0.98, r * 0.36, r * 0.14, "#f4f1f2", 1.5, INK, 1)
    for k in range(3):
        disc(g, cx - r * 0.04 + k * r * 0.1, cy - r * 0.91, 0.9, INK)
    ex = r * 0.28
    for sx in (-1, 1):
        x = cx + r * 0.34 + sx * ex
        ink_blob(g, x, cy - r * 0.02, r * 0.115, r * 0.2)
        ink_line(g, [(x - r * 0.13, cy - r * 0.27), (x, cy - r * 0.4), (x + r * 0.13, cy - r * 0.28)], 2.8)
    mx, my, mw = cx + r * 0.1, cy + r * 0.33, r * 0.78
    if mouth_open:
        teeth(g, mx, my, mw, r * 0.3)
    else:
        grin_shut(g, mx, my, mw)


def friend_head(g, cx: float, cy: float, r: float, mouth_open: bool, squeezed: bool = False):
    """The passenger: a round head with a bun, eyes shut in a laugh, a wide grin."""
    inked_fill(g, head_points(cx - r * 0.62, cy - r * 0.78, r * 0.34, 4.0), GRAY, 1.5, 4.0)
    pts = head_points(cx, cy, r, 5.0)
    inked_fill(g, pts, GRAY, 1.7, 5.0)
    shade_head(g, pts, cx, cy, r)
    for sx in (-1, 1):
        ex = cx + sx * r * 0.34
        lift = 0.2 if squeezed else 0.3
        ink_line(g, [(ex - r * 0.17, cy - r * 0.02), (ex, cy + r * lift), (ex + r * 0.17, cy - r * 0.02)], 3.0)
        ink_line(g, [(ex - r * 0.2, cy - r * 0.1), (ex - r * 0.3, cy - r * 0.16)], 1.9, brush.EVEN)
    mx, my, mw = cx - r * 0.34, cy + r * 0.34, r * 0.72
    if mouth_open:
        teeth(g, mx, my, mw, r * 0.32)
    else:
        grin_shut(g, mx, my, mw)


def hand(g, x: float, y: float, size: float, angle: float = 0):
    """A black glove: a rounded palm, three short fingers and a thumb."""
    node = cv.group(g, cv.uid("hand"), x=x, y=y, rotation=angle)
    cv.path(
        node, shape_d(brush.lump(0, size * 0.1, size * 0.5, size * 0.62, 0.08, seed=3)), fill=INK, stroke=NONE, sw=0
    )
    for k, lift in enumerate((0.0, 0.18, 0.1)):
        ink_blob(node, -size * 0.32 + k * size * 0.32, -size * (0.62 + lift), size * 0.17, size * 0.3)
    ink_blob(node, size * 0.52, -size * 0.12, size * 0.16, size * 0.3, 20)
    ink_blob(node, -size * 0.12, -size * 0.12, size * 0.13, size * 0.24, 0, "#3b3644")
    return node


def mouths(g, drawer, length: float, on: bool = True):
    """``drawer(node, open)`` draws a head with its mouth open and shut as two groups, swapped on every beat and half
    beat: a face singing to the music."""
    for state, when in on_beat.alternate(GROOVE, at(0.0), at(length), first=on).items():
        if when:
            node = cv.group(g, cv.uid("mouth"))
            drawer(node, state)
            cv.gate(node, when)


def sway(node, length: float, one: float, other: float):
    on_beat.sway(cv, node, GROOVE, at(0.0), at(length), one, other)


# -- the shots: the people stand between the car's two plates ----------------------------------------------------------
def torso(g, x: float, top: float, foot: float, width: float, lean: float = 0.0):
    """A pale wedge of shirt under the neck."""
    points = [
        (x - width * 0.22, top),
        (x + width * 0.22, top),
        (x + lean + width * 0.5, foot),
        (x + lean - width * 0.5, foot),
    ]
    inked_fill(g, points, SHIRT, 1.4, 6.0)


def wide(g, length: float):
    """The wide shot: the driver in the side window, the passenger through the windshield, both singing."""
    block(g, 255, 322, 58, 58, TAN, 6, INK, 1.2)  # the passenger's headrest, beside her
    friend = cv.group(g, cv.uid("friend"), anchorX=352, anchorY=368, x=352, y=368)
    sway(friend, length, -3, 2.5)
    torso(friend, 352, 348, 438, 66, 6)
    stick(friend, 340, 362, 322, 430, 3.6)
    stick(friend, 356, 366, 378, 430, 3.6)
    stick(friend, 366, 380, 416, 424, 3.2)
    mouths(friend, lambda gg, o: friend_head(gg, 360, 295, 58, o), length)
    hand(g, 258, 394, 18, -70)
    driver = cv.group(g, cv.uid("driver"), anchorX=92, anchorY=400, x=92, y=400)
    sway(driver, length, 2, -2.5)
    torso(driver, 92, 392, 470, 60, -4)
    stick(driver, 86, 398, 66, 464, 3.6)
    stick(driver, 98, 404, 160, 408, 3.2)
    mouths(driver, lambda gg, o: driver_head(gg, 90, 340, 56, o), length, on=False)


def windshield(g, length: float):
    """Through the windshield: the passenger, hand over her face, her other hand on the wheel side."""
    block(g, 46, 282, 66, 76, TAN, 6, INK, 1.2)  # the rear headrest
    person = cv.group(g, cv.uid("friend"), anchorX=178, anchorY=420, x=178, y=420)
    sway(person, length, 2.5, -2)
    torso(person, 186, 360, 450, 74, 8)
    stick(person, 188, 366, 172, 446, 3.8)
    stick(person, 198, 372, 232, 446, 3.8)
    stick(person, 214, 336, 196, 402, 3.8)
    friend_head(person, 176, 288, 84, True, squeezed=True)
    hand(person, 214, 300, 36, 8)
    hand(g, 50, 392, 22, -75)


def driver_shot(g, length: float):
    """Through the driver's window: the driver, grinning over the door."""
    person = cv.group(g, cv.uid("driver"), anchorX=250, anchorY=520, x=250, y=520)
    sway(person, length, 2, -2)
    torso(person, 250, 415, 520, 78, -6)
    stick(person, 244, 416, 214, 510, 3.8)
    stick(person, 262, 420, 304, 482, 3.8)
    mouths(person, lambda gg, o: driver_head(gg, 258, 352, 75, o), length)
    hand(g, 472, 412, 20, -70)


# -- the frame -------------------------------------------------------------------------------------------------------
def caption(parent):
    """The caption: white words on a black box near the top of the frame, a laughing face at its end."""
    font = (ROOT / STICK.font.src).read_bytes()
    size = 17
    width = math.ceil(fonts.text_width(font, CAPTION, size)) + 16
    total = width + 30
    x0 = (480 - total) / 2
    cv.rect(parent, x0, 118, total, 37, "#000000", None, 0, radius=5)
    cv.text(parent, "study-caption", CAPTION, x0 + 8, 118, width, 37, size, "#ffffff", align="start")
    fx, fy = x0 + width + 14, 136.5
    disc(parent, fx, fy, 8.5, "#f7c431", "#b8851a", 0.8)
    for sx in (-1, 1):
        path(
            parent,
            f"M {fx + sx * 4.5 - 2.5} {fy - 2.4} Q {fx + sx * 4.5} {fy - 5.2} {fx + sx * 4.5 + 2.5} {fy - 2.4}",
            NONE,
            INK,
            1.1,
        )
    path(parent, f"M {fx - 4.5} {fy + 1.2} L {fx + 4.5} {fy + 1.2} Q {fx} {fy + 7.6} {fx - 4.5} {fy + 1.2} Z", INK)
    disc(parent, fx + 7.4, fy - 0.5, 1.5, "#8ad2f0")


SEEN: set[str] = set()


def plate(parent, name: str):
    """A rendered car plate (_car_cel.py), full frame."""
    if name not in SEEN:
        SEEN.add(name)
        cv.assets.add_image(id=f"plate-{name}", src=f"plates/{name}.png", width=1080, height=1920)
    return parent.add_layer(id=cv.uid("plate"), asset=f"plate-{name}", x=0, y=0)


def wheels(parent, name: str, angle: str):
    """The tyres and turning rims, under the body: they barely leave the road."""
    start, end = SHOTS[name]
    node = cv.group(parent, f"wheels-{name}")
    on_beat.ride(cv, node, GROOVE, start, end, TYRE_BOUNCE, BAR_HIT)
    plate(node, f"{angle}-under")
    for i, rim in enumerate(car.rims(car.SHOTS[angle])):
        vehicle.turning_rim(cv, node, rim, car.RIM, start, end, car.SPIN, f"rim-{name}-{i}")


def shot(name: str, angle: str, draw, move: tuple[float, float], shadow: tuple[float, float, float, float]):
    """One shot, gated to its span: the city sliding past behind, the turning wheels on the road, the car's plates
    with the people between them riding the beat over the wheels, and a slow push over it all."""
    start, end = SHOTS[name]
    node = cv.group(ep.comp, f"shot-{name}")
    cv.gate(node, [(start, end)])
    cam = cv.group(node, f"cam-{name}", anchorX=540, anchorY=860, x=540, y=860)
    a, b = move
    for prop in ("scaleX", "scaleY"):
        cv.keys(cam, prop, [(start, a), (end, b)], kind="sine-in-out")
    CLOCK[0] = start
    far = cv.group(cam, f"far-{name}", x=0, y=TOP, scaleX=SCALE, scaleY=SCALE)
    block(far, -60, -120, 600, 1100, ROAD)  # under the blur: its reach past the drawing shows this, not the page
    block(far, -60, -120, 600, 560, SKY_TOP)
    drift = cv.group(look.depth(cv, far, "study-far", 2.0), f"drift-{name}", x=12)
    cv.keys(drift, "x", [(start, 12), (end, -12)], kind="linear")
    city(drift, angle)
    road = cv.group(cam, f"road-{name}", x=0, y=TOP, scaleX=SCALE, scaleY=SCALE)
    look.pool(cv, road, "study-shadow", "#1c1a30c0", *shadow)
    wheels(cam, name, angle)
    rig = cv.group(cam, f"rig-{name}")
    on_beat.ride(cv, rig, GROOVE, start, end, BOUNCE[angle], BAR_HIT)
    plate(rig, f"{angle}-back")
    people = cv.group(rig, f"people-{name}", x=0, y=TOP, scaleX=SCALE, scaleY=SCALE)
    draw(people, end - start)
    plate(rig, f"{angle}-front")
    look.grade(cv, cam, f"study-{name}", GRADE)
    return node


shot("wide", "wide", wide, (1.0, 1.07), (-40, 660, 620, 110))
shot("windshield", "windshield", windshield, (1.0, 1.05), (-60, 730, 620, 130))
shot("driver", "driver", driver_shot, (1.04, 1.0), (-60, 720, 620, 130))
shot("again", "windshield", windshield, (1.05, 1.0), (-60, 730, 620, 130))
words = cv.group(ep.comp, "caption", x=0, y=TOP, scaleX=SCALE, scaleY=SCALE)
caption(words)

subtitles.write_srt(ROOT / "car-vibe-study.srt", [(0.0, 10.0, CAPTION)])
ep.finish(ROOT / "car-vibe-study.scene.xml", ROOT / "qa" / "sdk-validation.json")
