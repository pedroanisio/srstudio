#!/usr/bin/env python3
"""Pedro drives to work, then flies the jet: a silent 30 s piece in his own likeness (ADR 0072).

python3 pedro_drive.py PROJECT            # PROJECT/pedro-drive.scene.xml and assets
python3 pedro_drive.py PROJECT --encode   # and the finished PROJECT/pedro-drive.mp4

A pilot, not a channel reel: it has no release and no post, and it renders outside the Instagram folder. His plates
render into SRSTUDIO_PLATES, by default ``generated/plates`` beside SRSTUDIO_RENDERS. The wire car and the wire jet are
drawn at the scale of the man (``srstudio.wire_car_prop.anchor``): the close-ups are projected at the metre, not
magnified, so the head sits on the headrest and the lines stay as fine as in the wide shots.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from pedro_drive_plates import PLATES
from sr_core.scene import Scene

from srstudio import Canvas, files, flat_counter, gpu, pedro_host, plates, wire_car_prop, wire_jet_prop
from srstudio.canvas import VOID
from srstudio.errors import SrstudioError

W, H, FPS, DURATION = 1080, 1920, 30, 30.0
SAFE_X, SAFE_W = 80, 840  # the vertical safe area's width (ADR on layouts): captions stay inside it
METRES_PER_PIXEL = 0.23 / 850.0  # his crown to his chin is 0.23 m and 850 px of a plate
HEAD = (540.0, 760.0)  # where the middle of his head is on a plate
CREAM, AMBER, TEAL = "#fff4dc", "#ffb066", "#7fd6d0"
CAR_BELT, JET_BELT = 0.30, 0.21  # metres below his head where the door's top or the coaming is
CAR_PANEL, JET_PANEL = "#0f0d1f", "#08162b"
FONT = "space-grotesk-700"


class DriveError(SrstudioError, ValueError):
    """The piece cannot be built: a plate, a font or a tool it needs is missing or wrong."""


def need(name: str, what: str) -> str:
    """The environment variable ``name``, or a typed refusal that says what it must name."""
    value = os.environ.get(name)
    if not value:
        raise DriveError(f"{name} must name {what}")
    return value


# -- the cut: each shot is a span of the 30 s ------------------------------------------------------------------
CAR_WIDE = (0.0, 3.0)
CAR_CLOSE = (3.0, 10.0)
FLASH = (9.9, 10.4)
JET_WIDE = (10.4, 14.0)
COCKPIT = (14.0, 23.0)
JET_AWAY = (23.0, 30.0)

# the cast of the car's close-up and the cockpit's: (plate, from, to)
CAR_FACES = (
    ("car-calm", 3.0, 4.4),
    ("car-blink", 4.4, 4.55),
    ("car-calm", 4.55, 7.4),
    ("car-up", 7.4, 8.0),
    ("car-brow", 8.0, 8.5),
    ("car-turn", 8.5, 8.9),
    ("car-lens", 8.9, 10.0),
)
JET_FACES = (
    ("jet-calm", 14.0, 16.0),
    ("jet-smile", 16.0, 18.6),
    ("jet-blink", 18.6, 18.75),
    ("jet-smile", 18.75, 21.0),
    ("jet-blink", 21.0, 21.15),
    ("jet-smile", 21.15, 22.0),
    ("jet-turn", 22.0, 22.4),
    ("jet-lens", 22.4, 23.0),
)
CAPTIONS = (  # (text, from, to, y of its middle)
    ("MONDAY.", 0.3, 2.9, 330),
    ("TRAFFIC.", 6.4, 8.5, 330),
    ("NOT TODAY.", 8.9, 9.9, 330),
    ("TUESDAY.", 10.6, 13.8, 330),
    ("NO TRAFFIC.", 15.2, 22.0, 330),
    ("SEE YOU MONDAY.", 26.0, 29.6, 330),
)


def smooth(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def inside(span: tuple[float, float], t: float) -> bool:
    return span[0] <= t < span[1]


def speed(t: float) -> float:
    """How fast the world goes by, in screen heights per second: it cruises, queues to a halt, and goes again."""
    if t < 5.6:
        return 1.0
    if t < 6.6:
        return 1.0 - smooth((t - 5.6) / 1.0)
    if t < 8.9:
        return 0.0
    if t < 10.0:
        return smooth((t - 8.9) / 1.1) * 1.4
    if t < 23.0:
        return 2.2
    return 2.2 + 0.8 * smooth((t - 23.0) / 4.0)


def distance(frames: int) -> np.ndarray:
    """The world's travel so far, in screen heights, at each frame."""
    steps = np.array([speed(i / FPS) for i in range(frames)])
    return np.cumsum(steps) / FPS


class Piece:
    NAME = "pedro-drive"

    def __init__(self, root: Path) -> None:
        self.root = root
        scene = Scene(version="auto")
        scene.add_project(width=W, height=H, fps=str(FPS), duration=DURATION, background=VOID.background)
        self.cv = Canvas(scene, VOID, font_asset="caption-font", width=W, height=H, namer=flat_counter("k"))
        self.frames = round(DURATION * FPS)
        self.travel = distance(self.frames)
        self.images: dict[str, str] = {}
        self.picture = self.cv.comp  # what the shots are drawn into; information goes above it, on the composition
        self.add_font()

    # -- files ----------------------------------------------------------------------------------------------
    def add_font(self) -> None:
        fonts = Path(need("SRSTUDIO_FONTS", "the directory that holds the caption font"))
        source = fonts / f"{FONT}.ttf"
        if not source.exists():
            raise DriveError(f"the caption font {source} is missing")
        target = self.root / "assets" / "fonts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        self.cv.assets.add_font(
            id="caption-font",
            src=f"assets/fonts/{source.name}",
            family="Space Grotesk",
            weight="700",
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            license="OFL-1.1",
        )

    def plate(self, name: str | tuple) -> tuple[str, Path]:
        """The asset id of a plate, rendering it where it is missing, and the file the project holds. ``name`` is one of
        :data:`PLATES`, or a ``(face, degrees, dress, glasses)`` of its own."""
        if isinstance(name, tuple):
            face, degrees, dress, glasses = name
            name = "x" + hashlib.sha256(repr(name).encode()).hexdigest()[:10]
        elif name not in PLATES:
            raise DriveError(f"no plate called {name!r}; one of {', '.join(PLATES)}")
        else:
            face, degrees, dress, glasses = PLATES[name]
        engine = Path(need("SRSTUDIO_ENGINE", "the scene-render binary"))
        cache = Path(
            os.environ.get("SRSTUDIO_PLATES")
            or Path(need("SRSTUDIO_RENDERS", "the renders directory")).parent / "plates"
        )
        made = plates.render(
            pedro_host.view(face, degrees, dress=dress, glasses=glasses),
            engine=engine,
            cache=cache,
            fonts=Path(os.environ["SRSTUDIO_FONTS"]),
        )
        target = self.root / "assets" / "pedro" / made.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(made, target)
        if name not in self.images:
            self.cv.assets.add_image(id=f"pedro-{name}", src=f"assets/pedro/{made.name}", width=W, height=H)
            self.images[name] = f"pedro-{name}"
        return self.images[name], target

    # -- pieces ---------------------------------------------------------------------------------------------
    def gate(self, node, *spans: tuple[float, float]) -> None:
        self.cv.gate(node, spans)

    def caption(self, text: str, start: float, end: float, y: float) -> None:
        cv = self.cv
        pop = cv.group(cv.comp, cv.uid("caption"), x=SAFE_X + SAFE_W / 2, y=y, opacity=0.0)
        self.gate(pop, (start, end))
        cv.pop_in(pop, start)
        size = int(min(118, SAFE_W / (len(text) * 0.68)))
        name = cv.uid("caption-text")
        cv.text(pop, name, text, -SAFE_W / 2, -90, SAFE_W, 180, size, color=CREAM)

    def backdrop(self, span: tuple[float, float], kind: str) -> None:
        """What goes by: a dusk road of light streaks, or a night sky with its cloud bank. ``kind`` is ``road``,
        ``sky``; the world's travel is :func:`distance` so every streak slows when the traffic does."""
        cv = self.cv
        rng = random.Random(f"pedro-{kind}-{span[0]}")
        first, last = round(span[0] * FPS), round(span[1] * FPS)
        stage = cv.group(self.picture, cv.uid(kind), x=W / 2, y=H / 2, opacity=0.0)
        self.gate(stage, span)
        if kind == "road":
            wall = cv.grad("road-sky", [(0, "#070914"), (0.55, "#1a1633"), (1, "#3b2036")], (0, 0, 0, 1))
        else:
            wall = cv.grad("night-sky", [(0, "#03050d"), (0.5, "#0b2347"), (1, "#1d4f78")], (0, 0, 0, 1))
        cv.rect(stage, -W, -H * 1.5, W * 2, H * 3, wall)
        if kind == "sky":
            horizon = cv.grad("sea-of-cloud", [(0, "#4b86a8"), (1, "#0d2a44")], (0, 0, 0, 1))
            cv.rect(stage, -W, 330, W * 2, H * 2, horizon)
            self.roll(stage, span)
        field = self.far(stage, kind)
        streaks = (
            [
                (rng.uniform(-0.05, 0.95), rng.uniform(70, 360), rng.uniform(3, 7), rng.choice((AMBER, CREAM, TEAL)))
                for _ in range(26)
            ]
            if kind == "road"
            else [(rng.uniform(0.1, 0.9), rng.uniform(260, 900), rng.uniform(14, 34), "#e8f3ffcc") for _ in range(16)]
        )
        for place, length, thick, colour in streaks:
            y = -H / 2 + place * H
            reach = rng.uniform(0.35, 1.5)  # nearer streaks travel further for the same distance
            x0 = rng.uniform(0, W + 2 * length)
            node = cv.group(field, cv.uid("streak"), x=-W, y=y)
            if kind == "road":
                cv.line(node, 0, 0, length, 0, colour + "99", thick)
            else:
                cv.ellipse(node, 0, -thick / 2, length, thick, colour[:7] + "40")
            span_px = W + 2 * length
            keys = []
            for frame in range(first, last):
                x = (x0 + reach * 1.15 * self.travel[frame] * W) % span_px - length
                keys.append((frame / FPS, round(x - W / 2, 1)))
            cv.keys(node, "x", keys)
        if kind == "road":
            self.queue(stage)

    def far(self, stage, kind: str):
        """The group the streaks of a backdrop go into: the stage itself, for a piece that draws them sharp."""
        return stage

    def roll(self, node, span: tuple[float, float]) -> None:
        """The horizon rolls as the jet banks: slowly one way, then the other."""
        first, last = round(span[0] * FPS), round(span[1] * FPS)
        keys = [(f / FPS, round(-self.bank(f / FPS), 2)) for f in range(first, last)]
        self.cv.keys(node, "rotation", keys)

    @staticmethod
    def bank(t: float) -> float:
        """The jet's roll in degrees at ``t``."""
        if inside(JET_WIDE, t):
            return 14 * math.sin((t - JET_WIDE[0]) * 1.5)
        if inside(COCKPIT, t):
            return 9 * math.sin((t - COCKPIT[0]) * 0.7) + 3 * math.sin((t - COCKPIT[0]) * 2.1)
        return 6 * math.sin((t - JET_AWAY[0]) * 0.9)

    def queue(self, stage) -> None:
        """Brake lights of the queue ahead, which come up as the traffic stops."""
        cv = self.cv
        glow = cv.rgrad("brake", [(0, "#ff4a3acc"), (0.45, "#ff4a3a55"), (1, "#ff4a3a00")], (0.5, 0.5, 0.5))
        for x, y, r in ((-330, -150, 80), (-120, -90, 60), (200, -190, 95), (400, -60, 55), (-60, -300, 45)):
            lamp = cv.group(stage, cv.uid("lamp"), opacity=0.0)
            cv.keys(lamp, "opacity", [(0, 0), (5.8, 0), (6.8, 1), (8.9, 1), (9.5, 0)], hold=False)
            cv.ellipse(lamp, x - r, y - r, 2 * r, 2 * r, glow)

    def shake(self, node, span: tuple[float, float], size: float, seed: str) -> None:
        """A vehicle's small movement: ``size`` pixels of drift and a few bumps. The queue stops it."""
        rng = random.Random(seed)
        first, last = round(span[0] * FPS), round(span[1] * FPS)
        keys, y = [], 0.0
        for frame in range(first, last):
            t = frame / FPS
            v = min(1.0, speed(t) + (0.08 if inside(JET_AWAY, t) or inside(COCKPIT, t) else 0.0))
            if not frame % 2:
                _, y = rng.uniform(-1, 1) * size * v, rng.uniform(-1, 1) * size * v
            keys.append((t, round(y, 1)))
        self.cv.keys(node, "y", keys)

    def optics(self, shot: str) -> dict[str, Any]:
        """What a shot's camera is told besides where and how big: its view and its distance. The piece looks at every
        vehicle flat, from the side, unless a subclass says otherwise."""
        return {}

    def cast(self, shot: str, faces: Sequence[tuple[Any, float, float]]) -> Sequence[tuple[Any, float, float]]:
        """His plates through a shot: ``(plate, from, to)``, where a plate is a name of :data:`PLATES` or a spec."""
        return faces

    def man(self, parent, faces: Sequence[tuple[Any, float, float]], at, presence: float):
        """Him, placed by the vehicle's anchor ``at`` (an :class:`srstudio.wire_draw.Anchor`), a plate at a time. The
        plate stops at the bottom of the frame: the vehicle's door or coaming hides where."""
        cv = self.cv
        k = at.scale * METRES_PER_PIXEL * presence
        base = cv.group(parent, cv.uid("pedro"), x=at.x - HEAD[0] * k, y=at.y - HEAD[1] * k, scaleX=k, scaleY=k)
        for name, start, end in faces:
            asset, _ = self.plate(name)
            pose = cv.group(base, cv.uid("pose"), opacity=0.0)
            self.gate(pose, (start, end))
            pose.add_layer(id=cv.uid("pedro-layer"), asset=asset, x=0, y=0)
        return base

    def occupied(
        self, rig, prop, find, shot: dict[str, Any], anchor: str, belt: float, presence: float, faces, panel: str, reach
    ):
        """A vehicle with a man in it: the lines above the belt line behind him, then him, then the door or coaming
        (solid, so it hides the foot of his plate), then the lines below the belt line in front of it. ``belt`` is
        metres below the anchor; ``reach`` the metres of panel either side of him, or ``None`` for the full width."""
        cv = self.cv
        at = find(anchor, **shot)
        height = at.y + belt * at.scale  # canvas row of the belt line
        rows = height - shot["at"][1]  # and as the prop counts it: from the middle of its picture
        prop(cv, rig, rows=(-1e5, rows), **shot)
        self.man(rig, faces, at, presence)
        if reach is None:
            cv.rect(rig, -W, height, 3 * W, 2 * H, panel)
        else:
            cv.rect(rig, at.x - reach * at.scale, height, 2 * reach * at.scale, 0.2 * at.scale, panel)
        prop(cv, rig, rows=(rows, 1e5), **shot)

    def vehicle(self, prop, rig, **shot) -> None:
        """A vehicle with no one in it, drawn as strokes into ``rig``."""
        prop(self.cv, rig, **shot)

    def hud(self, x: float, y: float) -> None:
        """A head-up display ahead of the pilot: its reticle, its horizon ladder that rolls against the jet's bank, and
        two read-outs."""
        cv = self.cv
        node = cv.group(self.picture, cv.uid("hud"), x=x, y=y, opacity=0.0)
        self.gate(node, COCKPIT)
        cv.rect(node, -150, -190, 300, 380, cv.clear, stroke=TEAL + "88", sw=3, radius=18)
        cv.ellipse(node, -42, -42, 84, 84, cv.clear, stroke=TEAL, sw=4)
        cv.ellipse(node, -5, -5, 10, 10, TEAL)
        for a, b in ((-105, -55), (55, 105)):
            cv.line(node, a, 0, b, 0, TEAL, 4)
        ladder = cv.group(node, cv.uid("ladder"))
        cv.line(ladder, -135, 0, 135, 0, TEAL, 3)
        for k in (-2, -1, 1, 2):
            cv.line(ladder, -48, k * 64, 48, k * 64, TEAL + "aa", 3)
        first, last = round(COCKPIT[0] * FPS), round(COCKPIT[1] * FPS)
        cv.keys(ladder, "rotation", [(f / FPS, round(-self.bank(f / FPS), 2)) for f in range(first, last)])
        cv.text(node, cv.uid("hud-speed"), "640", -146, 150, 120, 34, 26, color=TEAL, align="start")
        cv.text(node, cv.uid("hud-height"), "9400", 26, 150, 120, 34, 26, color=TEAL, align="end")

    def streak_flash(self) -> None:
        cv = self.cv
        flash = cv.group(cv.comp, cv.uid("flash"), opacity=0.0)
        cv.rect(flash, 0, 0, W, H, "#ffffff")
        cv.keys(
            flash,
            "opacity",
            [(0, 0), (FLASH[0], 0), (FLASH[0] + 0.1, 0.95), (FLASH[0] + 0.2, 0.95), (FLASH[1], 0)],
            hold=False,
        )

    # -- the shots ------------------------------------------------------------------------------------------
    def car_wide(self) -> None:
        cv = self.cv
        self.backdrop(CAR_WIDE, "road")
        rig = cv.group(self.picture, cv.uid("rig"), opacity=0.0)
        self.gate(rig, CAR_WIDE)
        shot: dict[str, Any] = {
            **dict(at=(W / 2, 1000), width=1000, seed="monday", view="side"),
            **self.optics("car-wide"),
        }
        self.occupied(
            rig, wire_car_prop.wire_car, wire_car_prop.anchor, shot, "driver-head", CAR_BELT, 1.25,
            self.cast("car-wide", [("car-calm", *CAR_WIDE)]), "#1b1734", 0.30,
        )  # fmt: skip
        self.shake(rig, CAR_WIDE, 3.0, "car-wide")
        cv.keys(rig, "scaleX", [(0, 1.0), (CAR_WIDE[1], 1.06)], hold=False)
        cv.keys(rig, "scaleY", [(0, 1.0), (CAR_WIDE[1], 1.06)], hold=False)

    def car_close(self) -> None:
        cv = self.cv
        self.backdrop(CAR_CLOSE, "road")
        rig = cv.group(self.picture, cv.uid("rig"), opacity=0.0)
        self.gate(rig, CAR_CLOSE)
        shot: dict[str, Any] = {
            **dict(at=(W / 2, 990), width=W, seed="monday", view="side", around="driver-head", span=1.25, height=H),
            **self.optics("car-close"),
        }
        self.occupied(
            rig, wire_car_prop.wire_car, wire_car_prop.anchor, shot, "driver-head", CAR_BELT, 1.3,
            self.cast("car-close", CAR_FACES), CAR_PANEL, None,
        )  # fmt: skip
        self.shake(rig, CAR_CLOSE, 5.0, "car-close")

    def jet_wide(self) -> None:
        cv = self.cv
        self.backdrop(JET_WIDE, "sky")
        rig = cv.group(self.picture, cv.uid("rig"), x=W / 2, y=960, opacity=0.0)
        self.gate(rig, JET_WIDE)
        shot: dict[str, Any] = {
            **dict(at=(0, 0), width=1500, seed="tuesday", view="front-quarter", model="kestrel"),
            **self.optics("jet-wide"),
        }
        self.vehicle(wire_jet_prop.wire_jet, rig, **shot)
        first, last = round(JET_WIDE[0] * FPS), round(JET_WIDE[1] * FPS)
        cv.keys(rig, "rotation", [(f / FPS, round(self.bank(f / FPS), 2)) for f in range(first, last)])
        cv.keys(rig, "scaleX", [(JET_WIDE[0], 0.55), (JET_WIDE[1], 0.78)], hold=False, kind="sine-in-out")
        cv.keys(rig, "scaleY", [(JET_WIDE[0], 0.55), (JET_WIDE[1], 0.78)], hold=False, kind="sine-in-out")

    def cockpit(self) -> None:
        cv = self.cv
        self.backdrop(COCKPIT, "sky")
        rig = cv.group(self.picture, cv.uid("rig"), opacity=0.0)
        self.gate(rig, COCKPIT)
        shot: dict[str, Any] = {
            **dict(
                at=(W / 2, 980),
                width=W,
                seed="tuesday",
                view="side",
                model="kestrel",
                around="pilot-head",
                span=1.25,
                height=H,
            ),
            **self.optics("cockpit"),
        }
        self.occupied(
            rig, wire_jet_prop.wire_jet, wire_jet_prop.anchor, shot, "pilot-head", JET_BELT, 1.4,
            self.cast("cockpit", JET_FACES), JET_PANEL, None,
        )  # fmt: skip
        self.shake(rig, COCKPIT, 3.0, "cockpit")
        self.hud(215, 800)

    def jet_away(self) -> None:
        cv = self.cv
        self.backdrop(JET_AWAY, "sky")
        rig = cv.group(self.picture, cv.uid("rig"), x=W / 2, y=980, opacity=0.0)
        self.gate(rig, JET_AWAY)
        shot: dict[str, Any] = {
            **dict(at=(0, 0), width=1300, seed="tuesday", view="side", model="kestrel"),
            **self.optics("jet-away"),
        }
        self.vehicle(wire_jet_prop.wire_jet, rig, **shot)
        a, b = JET_AWAY
        first, last = round(a * FPS), round(b * FPS)
        cv.keys(rig, "rotation", [(f / FPS, round(self.bank(f / FPS) * 0.6, 2)) for f in range(first, last)])
        cv.keys(rig, "x", [(a, W / 2), (b, 150)], hold=False, kind="cubic-in")
        cv.keys(rig, "y", [(a, 980), (b, 520)], hold=False, kind="cubic-in")
        cv.keys(rig, "scaleX", [(a, 0.85), (b, 0.12)], hold=False, kind="cubic-in")
        cv.keys(rig, "scaleY", [(a, 0.85), (b, 0.12)], hold=False, kind="cubic-in")

    def fade_out(self) -> None:
        cv = self.cv
        dark = cv.group(cv.comp, cv.uid("dark"), opacity=0.0)
        cv.rect(dark, 0, 0, W, H, VOID.background)
        cv.keys(dark, "opacity", [(0, 0), (DURATION - 0.6, 0), (DURATION, 1)], hold=False)

    def build(self) -> Path:
        self.car_wide()
        self.car_close()
        self.jet_wide()
        self.cockpit()
        self.jet_away()
        for text, start, end, y in CAPTIONS:
            self.caption(text, start, end, y)
        self.streak_flash()
        self.fade_out()
        scene = self.root / f"{self.NAME}.scene.xml"
        scene.write_bytes(self.cv.scene.to_bytes())
        return scene


def encode(scene: Path, engine: Path) -> Path:
    """The pilot's master beside its scene, write-once (ADR 0170): a re-run refuses before it encodes, and a failed
    encode leaves nothing under the master's name."""
    out = files.must_be_free(scene.with_suffix(".mp4"))
    stage = out.with_name(f".{out.name}.encoding.mp4")
    try:
        with gpu.held():
            done = subprocess.run(
                [str(engine), "encode", scene.name, "-o", stage.name, "--hw", "software"],
                cwd=scene.parent,
                capture_output=True,
                text=True,
            )
        if done.returncode:
            raise DriveError(f"the encode failed ({done.returncode}): {done.stdout[-800:]} {done.stderr[-800:]}")
        return files.install_once(stage, out)
    finally:
        stage.unlink(missing_ok=True)


def main(argv: Sequence[str], run: Callable[[Path, Path], Path] = encode) -> int:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    root = Path(argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    scene = Piece(root).build()
    print(scene)
    if "--encode" in argv[2:]:
        print(run(scene, Path(need("SRSTUDIO_ENGINE", "the scene-render binary"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
