"""Pedro drives, then flies, in the layered drawing of DRAWING.md: the 30 s piece with its rigid objects as cel plates
under their ink, Pedro converted to the same flat bands and an ink ring, one light, one finish, and the captions above.

    python pedro_drive_toon.py OUT_DIR [--encode] [--bare] [--grain=AMOUNT]

``--bare`` leaves the finish off, the picture the palette and the information gates are measured on; ``--grain=0``
leaves the grain off, and any other amount sets it.

The layers:
- rigid objects (the car, the jet): :func:`srstudio.wire_car_prop.plate` and :func:`srstudio.wire_jet_prop.plate`, the
  model's own surfaces cut into four tones by the light, with the strokes of the same projection over them;
- the character (Pedro, on plates): the engine's gradient-map through a stepped ramp, and an outline ring behind it;
- the environment: the dusk road and the night sky, with their streaks thrown out of focus and a haze on the horizon;
- information (the captions): vector, above the finish, never graded.
"""

from __future__ import annotations

import hashlib
import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pedro_drive as base
import pedro_drive_head as head
from pedro_drive import DriveError

from srstudio import look, pedro_host, wire_car, wire_car_prop, wire_jet_prop
from srstudio.wire_draw import Plate

# The ramp every surface of Pedro is mapped through (luminance, darkest to lightest) and the ink round him.
PEDRO_BANDS = ((0.24, "#1c1a38"), (0.42, "#6b4a72"), (0.50, "#b8647a"), (0.78, "#e0905e"), (1.00, "#ffe2b8"))
INK = "#0b0a1c"
RING = 5  # pixels of his ink ring on a plate
# The one finish, applied once to the whole picture.
FINISH = {
    "bloom": {"threshold": 0.72, "intensity": 0.35, "radius": 22},
    "vignette": {"amount": 0.5, "radius": 640, "softness": 0.55},
    "film-grain": {"amount": 0.12, "size": 1.6, "seed": 1031},
}
FAR_BLUR = 9  # px of blur on the streaks of the road: the lights behind the car are out of focus
# How each shot's camera sees its vehicle: in perspective, from this many metres from its middle.
OPTICS: dict[str, dict[str, Any]] = {
    "car-wide": {"view": "side-high", "distance": 6.5},
    "car-close": {"distance": 4.0},
    "jet-wide": {"distance": 24.0},
    "cockpit": {"distance": 14.0},
    "jet-away": {"distance": 30.0},
}
# His head through each shot (the shot's own clock): the moods and blinks of the cut, and the turn to the lens.
HEADS: dict[str, tuple[head.Script, str, bool]] = {
    "car-wide": (head.Script(phase=0.2), "blazer", False),
    "car-close": (
        head.Script(
            moods=((0.0, "neutral"), (4.4, "raised-brow"), (5.9, "smile")),
            blinks=(1.4, 3.2),
            holds=((4.4, 5.0, -3.0),),
            lens=(5.5, 5.9, -35.0),
            phase=0.9,
        ),
        "blazer",
        False,
    ),
    "cockpit": (
        head.Script(moods=((0.0, "neutral"), (2.0, "smile")), blinks=(4.6, 7.0), lens=(8.0, 8.4, -35.0), phase=1.7),
        "puffer",
        True,
    ),
}
PHASES = 8  # the turns of a wheel's spokes are drawn at this many angles, each wheel layer for the frames it is at
WHEEL_TURNS = 1.2  # revolutions a second while the world goes by at one screen height a second
PLATE_OF: dict[Callable[..., Any], Callable[..., Plate]] = {
    wire_car_prop.wire_car: wire_car_prop.plate,
    wire_jet_prop.wire_jet: wire_jet_prop.plate,
}
EDGE_OF: dict[Callable[..., Any], Callable[..., tuple[float, float]]] = {
    wire_car_prop.wire_car: wire_car_prop.edge,
    wire_jet_prop.wire_jet: wire_jet_prop.edge,
}
REACH = 0.6  # metres either side of his head over which the top of the door or the coaming is measured


def key_light() -> tuple[float, float, float]:
    """The direction towards the key light Pedro's plates are lit by, in the wire models' axes: the sculpt's key sits
    up, toward the lens and to the left of the head (his lit side is the one that faces the left of the picture, and
    the nose of a wire model is to the left as well)."""
    key = next(light for light in pedro_host.LIGHTS if light.id == "key")
    if key.at is None:
        raise DriveError("the key light of the sculpt's rig has no place")
    target = pedro_host.CAMERA.target
    dx, dy, dz = (key.at[i] - target[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    return (-abs(dx) / length, abs(dy) / length, abs(dz) / length)


class TonePiece(base.Piece):
    NAME = "pedro-drive-toon"

    def __init__(self, root: Path, *, finish: bool = True, grain: float | None = None) -> None:
        super().__init__(root)
        self.light = key_light()
        self.plates: dict[str, str] = {}
        self.picture = self.cv.group(self.cv.comp, "picture")
        if finish:
            effects = {kind: dict(attrs) for kind, attrs in FINISH.items()}
            if grain is not None:
                if grain > 0:
                    effects["film-grain"]["amount"] = grain
                else:
                    del effects["film-grain"]
            look.grade(self.cv, self.picture, "finish", effects)
        ramp = self.cv.grad("pedro-ramp", self.ramp(), (0, 0, 1, 0))
        self.tone = self.cv.effect("pedro-tone", "gradient-map", paint=ramp)
        self.ring = self.cv.effect("pedro-ring", "outline", size=RING, color=INK, softness=0)

    @staticmethod
    def ramp() -> list[tuple[float, str]]:
        """The stepped ramp: each band's colour from where the one before ends to where it ends."""
        stops, start = [], 0.0
        for end, colour in PEDRO_BANDS:
            stops += [(start, colour), (end, colour)]
            start = end
        return stops

    # -- the camera, his head, the wheels -------------------------------------------------------------------
    def optics(self, shot: str) -> dict[str, Any]:
        return dict(OPTICS[shot])

    def cast(self, shot: str, faces):
        if shot not in HEADS:
            return faces
        script, dress, glasses = HEADS[shot]
        span = (faces[0][1], faces[-1][2])
        return head.track(span, script, dress=dress, glasses=glasses, speed=base.speed)

    def rolling(self, rig, shot: dict[str, Any], span: tuple[float, float]) -> None:
        """The wheels of the car, turning: a layer of each wheel at each of :data:`PHASES` angles of a spoke's turn,
        each shown for the frames the wheel is at that angle. Below the body, which is open where a wheel shows."""
        cv = self.cv
        pitch = 2 * math.pi / wire_car.make_car(shot["seed"]).spokes
        seen: list[list[tuple[float, float]]] = [[] for _ in range(PHASES)]
        for frame in range(round(span[0] * base.FPS), round(span[1] * base.FPS)):
            turned = 2 * math.pi * WHEEL_TURNS * float(self.travel[frame])
            seen[round((turned % pitch) / pitch * PHASES) % PHASES].append((frame / base.FPS, (frame + 1) / base.FPS))
        for index, spans in enumerate(seen):
            if not spans:
                continue
            layer = cv.group(rig, cv.uid("rolling"), opacity=0.0)
            self.gate(layer, *spans)
            for axle in ("front", "rear"):
                wheel = {**shot, "wheels": axle, "spin": index * pitch / PHASES}
                self.slab(layer, wire_car_prop.plate(self.light, **wheel))
                wire_car_prop.wire_car(cv, layer, light=self.light, **wheel)

    # -- the layers -----------------------------------------------------------------------------------------
    def man(self, parent, faces, at, presence):
        """Him twice: an ink ring round his plate, and over it the plate through the stepped ramp."""
        self.cv.apply(super().man(parent, faces, at, presence), self.ring)
        return self.cv.apply(super().man(parent, faces, at, presence), self.tone)

    def slab(self, parent, plate: Plate) -> None:
        """A vehicle's surfaces, as the picture ``plate`` is, in ``parent``."""
        name = hashlib.sha256(plate.png).hexdigest()[:12]
        target = self.root / "assets" / "vehicle" / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(plate.png)
        if name not in self.plates:
            self.cv.assets.add_image(
                id=f"vehicle-{name}", src=f"assets/vehicle/{name}.png", width=plate.width, height=plate.height
            )
            self.plates[name] = f"vehicle-{name}"
        parent.add_layer(id=self.cv.uid("vehicle-layer"), asset=self.plates[name], x=plate.x, y=plate.y)

    def vehicle(self, prop, rig, **shot) -> None:
        self.slab(rig, PLATE_OF[prop](self.light, **shot))
        prop(self.cv, rig, light=self.light, **shot)

    def occupied(
        self, rig, prop, find, shot: dict[str, Any], anchor: str, belt: float, presence: float, faces, panel, reach
    ):
        """A vehicle with a man in it: its surfaces and lines above the top of the door (or the coaming) behind him,
        then him, then its surfaces and lines below it in front of him. The surfaces are solid, so the door hides the
        foot of his plate and there is no panel to paint. The top is measured in the model's own surfaces, ``belt``
        metres under his head, a line the camera in perspective may see slanted."""
        cv, plate = self.cv, PLATE_OF[prop]
        at = find(anchor, light=self.light, **shot)
        edge, tilt = EDGE_OF[prop](anchor, belt, REACH, light=self.light, **shot)
        if prop is wire_car_prop.wire_car and "around" not in shot:  # the wheels are in view: they turn under the body
            self.rolling(rig, shot, (faces[0][1], faces[-1][2]))
            shot = {**shot, "wheels": "body"}
        for front, span in enumerate(((-1e5, edge), (edge, 1e5))):
            if front:
                self.man(rig, faces, at, presence)
            self.slab(rig, plate(self.light, rows=span, tilt=tilt, **shot))
            prop(cv, rig, rows=span, tilt=tilt, light=self.light, **shot)

    def far(self, stage, kind: str):
        """The streaks of the road are lights out of focus behind the car; a haze lies on the horizon of each."""
        cv = self.cv
        if kind == "road":
            self.glow(stage, "road-haze", "#e0905e55", (-260, 260, 700))
            return look.depth(cv, stage, f"far-{kind}", FAR_BLUR)
        self.glow(stage, "sky-haze", "#9ed0e877", (60, 380, 680))
        return stage

    def glow(self, stage, name: str, colour: str, rows: tuple[float, float, float]) -> None:
        """A haze on the horizon: ``colour`` thickens from nothing at the first row to its full strength at the second
        and thins to nothing again at the third (rows of ``stage``), so it has no edge anywhere in the frame."""
        top, middle, bottom = rows
        look.fade(self.cv, stage, name, colour, middle, top, 2 * base.W, -base.W)
        look.fade(self.cv, stage, f"{name}-below", colour, middle, bottom, 2 * base.W, -base.W)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    root = Path(argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    grain = next((float(a.split("=")[1]) for a in argv[2:] if a.startswith("--grain=")), None)
    scene = TonePiece(root, finish="--bare" not in argv[2:], grain=grain).build()
    print(scene)
    if "--encode" in argv[2:]:
        import os

        print(base.encode(scene, Path(os.environ["SRSTUDIO_ENGINE"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
