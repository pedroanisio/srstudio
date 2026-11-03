"""Small Print's worktop props: what Rafa tries the question on, in his clay world, one plate a state (ADR 0195).

Each prop is drawn in Rafa's model units (:mod:`srstudio.rafa`): x right, y down, z away from the lens, its foot on
y = 0. A prop has named states, and a state is one replacement plate, as a stop-motion puppet's replacement parts are:
the penny on the tower and then falling past it, the paper four to seven times folded, the onion whole, halved and
chopped under a knife that is up or down. :func:`worktop` puts a state on his worktop with his frame-right hand on it,
and :func:`tear_plate` is his face at a head pose with two tears on it, to cut a patch from. Nothing here changes how
he is drawn: his body, head and hands are :mod:`srstudio.rafa`'s, and the tears lie on his skin's own surface.

Every part here is ``proposed`` until the operator has seen it on a rendered clip.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import cache, lru_cache

import numpy as np

from . import clay, plates, rafa, rafa_host, rafa_skin
from .clay import Mesh, Model
from .contracts import ParameterContract as P
from .contracts import PartContract
from .errors import SrstudioError
from .plates import Material, Placed, Plate
from .registry import register

__all__ = [
    "GRIPS",
    "HANDS",
    "PLACES",
    "STATES",
    "PropError",
    "apple",
    "bowl",
    "can",
    "draw",
    "finished",
    "goldfish",
    "materials",
    "onion",
    "paper",
    "part_plates",
    "phone",
    "roll",
    "tear_plate",
    "tears",
    "tower",
    "wall",
    "worktop",
    "wrinkles",
]

_CLAY_TILE = 70.0  # rafa's clay tile, so a new prop carries the same thumb marks at the same size
OWN = {  # what is new in his world: name, colour, roughness, metallic, clay-finished
    "copper": ("#B5683B", 0.32, 0.6, False),
    "towerstone": ("#D2C4AA", 0.62, 0.0, True),
    "towershade": ("#9E907B", 0.62, 0.0, True),
    "onionskin": ("#C08442", 0.5, 0.0, True),
    "onionflesh": ("#F0E5C6", 0.42, 0.0, True),
    "board": ("#D7B183", 0.6, 0.0, True),
    "tear": ("#BFE2F0", 0.03, 0.0, False),
    "bowl": ("#E9DCC4", 0.45, 0.0, True),
    "water": ("#8CC7DD", 0.18, 0.0, False),
    "marble": ("#4F86A8", 0.08, 0.0, False),
    "land": ("#C9A97C", 0.62, 0.0, True),
    "wallstone": ("#B99C72", 0.62, 0.0, True),
    "snow": ("#F6F4EE", 0.5, 0.0, True),
    "glass": ("#BCDCE0", 0.1, 0.0, False),
    "goldfish": ("#E8782E", 0.3, 0.0, True),
    "fishmouth": ("#A8402A", 0.4, 0.0, True),
    "fin": ("#F2A25E", 0.35, 0.0, True),
    "flake": ("#D9A441", 0.6, 0.0, True),
    "appleskin": ("#B8352B", 0.4, 0.0, True),
    "appleflesh": ("#F3E7BE", 0.5, 0.0, True),
    "applebrown": ("#A86A35", 0.55, 0.0, True),
    "pip": ("#3F2618", 0.3, 0.0, False),
    "canpaint": ("#2F7FA6", 0.3, 0.35, False),
    "foam": ("#FBF6EA", 0.6, 0.0, True),
}


class PropError(SrstudioError, ValueError):
    """A prop or a state Small Print does not have."""


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Rafa's materials and the new ones, a clay normal map on those that are clay."""
    clay_map = rafa.MATERIALS["oak"].normal_map
    own = {
        name: Material(
            name,
            colour,
            roughness=rough,
            metallic=metal,
            normal_map=clay_map if clayed else None,
            normal_scale=0.55,
            sheen="#FFE9D2" if clayed else "",
        )
        for name, (colour, rough, metal, clayed) in OWN.items()
    }
    return {**rafa.materials(), **own}


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: Rafa's own finish, and the clay tile on a new clay material."""
    if mesh.material in OWN:
        material = materials()[mesh.material]
        return mesh if mesh.uvs is not None or material.normal_map is None else clay.planar(mesh, _CLAY_TILE)
    return rafa.finished(mesh)


def _turned(m: Model, build: Callable[[Model], None], spin: np.ndarray, at: tuple[float, float, float]) -> None:
    """What ``build`` draws about the origin, turned by the matrix ``spin`` and moved to ``at``, into ``m``."""
    sub = Model()
    build(sub)
    for mesh in sub.meshes():
        m.surface(mesh.material, mesh.vertices @ spin.T + np.array(at), mesh.normals @ spin.T, mesh.triangles)


def _spin(about_z: float, about_y: float = 0.0) -> np.ndarray:
    a, b = math.radians(about_z), math.radians(about_y)
    z = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    y = np.array([[math.cos(b), 0.0, math.sin(b)], [0.0, 1.0, 0.0], [-math.sin(b), 0.0, math.cos(b)]])
    return y @ z


def _contract(name: str, states: tuple[str, ...], detail: str) -> PartContract:
    return PartContract(
        parameters=(
            ("m", P(type=Model, unit="Rafa model units", space="model-frame", role="mutable-model")),
            ("state", P(enum=states)),
        ),
        returns=P(type=type(None), role="model-mutation"),
        capabilities=(("returns_scene_handle", False), ("spatial_attachment", False), ("animation", False)),
        constraints=(
            "Appends static triangles for one named state into the caller-owned clay.Model and returns None. "
            "A state is one replacement plate; the reel cuts between them.",
            "Coordinates are Rafa model units: x right, y down, z away from the lens, the foot on y = 0.",
            detail,
        ),
    )


# -- the penny and the tower ------------------------------------------------------------------------------------------
TOWER_STATES = ("top", "fall-1", "fall-2", "fall-3", "landed")
_TIERS = ((26.0, 14.0, 20.0), (21.0, 12.0, 17.0), (16.0, 10.0, 13.0), (11.0, 8.0, 9.0), (7.0, 5.0, 6.0))
_COIN = {  # where the penny is: x, y, z, its tilt across the lens and its turn, in degrees
    "top": (0.0, -50.5, -2.0, 90.0, 0.0),
    "fall-1": (14.0, -40.0, -12.0, 40.0, 30.0),
    "fall-2": (17.0, -26.0, -14.0, 120.0, 70.0),
    "fall-3": (18.0, -12.0, -10.0, 170.0, 20.0),
    "landed": (17.0, -1.2, -6.0, 0.0, 0.0),
}


@register(
    "prop",
    "smallprint-tower",
    summary="A clay model skyscraper with a penny on its top, then falling past it",
    contract=_contract(
        "smallprint-tower", TOWER_STATES, "Five stepped tiers and a spire; the penny's state places it, flat at rest."
    ),
)
def tower(m: Model, state: str = "top") -> None:
    """A stepped clay tower with a spire, about a skyscraper's shape and no one building's, and the penny: on the top
    ledge, three tumbles down past the tower's face, then flat on the worktop."""
    if state not in _COIN:
        raise PropError(f"the tower's states are {TOWER_STATES}, got {state!r}")
    y = 0.0
    for w, h, d in _TIERS:
        m.box("towerstone", (0.0, y - h / 2, 0.0), (w, h, d), 1.2)
        for k in range(-2, 3):  # the piers down the front, the way a tall building's face reads from far off
            m.box("towershade", (k * w / 6, y - h / 2, -d / 2 - 0.2), (0.9, h * 0.8, 0.5), 0.2)
        y -= h
    m.cylinder("steel", (0.0, y - 6.0, 0.0), 0.9, 12.0)
    x, cy, z, tilt, turn = _COIN[state]
    _turned(m, lambda s: s.cylinder("copper", (0.0, 0.6, 0.0), 5.0, 1.2), _spin(tilt, turn), (x, cy, z))


# -- the paper ---------------------------------------------------------------------------------------------------------
PAPER_STATES = tuple(f"fold-{n}" for n in range(1, 8))  # unfolded, a sheet on its edge stands over his chin
_SHEETS = (  # width, height and thickness of a sheet folded n times (n = 0, the open sheet, is never drawn), on its
    # long edge: smaller and thicker at each fold, the late folds bigger than true halving, so a phone reads the lump
    (60.0, 44.0, 0.6),
    (44.0, 30.0, 1.1),
    (30.0, 22.0, 1.8),
    (24.0, 18.0, 3.0),
    (19.0, 15.0, 4.4),
    (15.0, 13.0, 6.0),
    (12.5, 11.5, 8.0),
    (11.0, 10.5, 10.5),
)


@register(
    "prop",
    "smallprint-paper",
    summary="A sheet of paper folded in half up to seven times, standing on its edge",
    contract=_contract(
        "smallprint-paper", PAPER_STATES, "fold-n stands the sheet folded n times on its edge, a fold line per layer."
    ),
)
def paper(m: Model, state: str = "fold-4") -> None:
    """The sheet folded ``n`` times, standing on its long edge: each fold halves it and doubles its layers, so it is a
    card, then a block, then a stubborn lump. The open edge shows a line for each fold."""
    if state not in PAPER_STATES:
        raise PropError(f"the paper's states are {PAPER_STATES}, got {state!r}")
    folds = int(state.removeprefix("fold-"))
    w, h, t = _SHEETS[folds]
    m.box("paper", (0.0, -h / 2, 0.0), (w, h, t), min(0.3 + t * 0.25, 1.8))
    for k in range(1, folds + 1):
        m.box("cream", (-w / 2 - 0.05, -h / 2, -t / 2 + k * t / (folds + 1)), (0.3, h * 0.92, 0.18), 0.0)


@register(
    "prop",
    "smallprint-roll",
    summary="A roll of tissue paper whose sheet runs off the worktop and out of the frame",
    contract=_contract("smallprint-roll", ("roll",), "The sheet runs 520 units to frame left in soft waves."),
)
def roll(m: Model, state: str = "roll") -> None:
    """A tissue roll on its end, its sheet off the front and away to frame left across the worktop, in soft waves, so it
    runs out of the frame however the shot is framed."""
    if state != "roll":
        raise PropError(f"the roll has one state, 'roll', got {state!r}")
    m.cylinder("paper", (0.0, -11.0, 0.0), 11.0, 22.0)
    m.cylinder("cream", (0.0, -22.2, 0.0), 4.0, 0.6)
    xs = np.linspace(-6.0, -520.0, 90)
    for i, (a, b) in enumerate(zip(xs[:-1], xs[1:], strict=True)):
        lift = -0.6 - 3.2 * abs(math.sin(i * 0.45))
        m.box("paper", ((a + b) / 2, lift, -10.0 + 4.0 * math.sin(i * 0.3)), (abs(b - a) + 0.6, 0.5, 18.0), 0.2)


# -- the onion ---------------------------------------------------------------------------------------------------------
ONION_STATES = tuple(f"{cut}-{knife}" for cut in ("whole", "half", "chopped") for knife in ("up", "down"))
KNIFE_LIFT = {"up": 32.0, "down": 16.0}  # how high the knife's spine rides over the worktop


@register(
    "prop",
    "smallprint-onion",
    summary="An onion on a board, whole, halved or chopped, and a knife up or down",
    contract=_contract(
        "smallprint-onion",
        ONION_STATES,
        "<cut>-<knife>: the onion whole, halved or chopped, the knife's blade up or down; the knife's handle is "
        "where his fist goes.",
    ),
)
def onion(m: Model, state: str = "whole-up") -> None:
    """A board, the onion on it whole, or halved with its pale face to the knife, or chopped with a heap of pieces, and
    the knife, its blade along frame left and its edge down, up or down."""
    if state not in ONION_STATES:
        raise PropError(f"the onion's states are {ONION_STATES}, got {state!r}")
    cut, knife = state.split("-")
    m.box("board", (0.0, -2.0, 0.0), (70.0, 4.0, 40.0), 1.5)
    if cut == "whole":
        m.ell("onionskin", (-12.0, -18.0, 0.0), (15.0, 14.0, 15.0))
        m.cylinder("onionskin", (-12.0, -33.0, 0.0), 2.0, 5.0)
    else:
        m.ell("onionskin", (-18.0, -14.0, 2.0), (13.0, 12.0, 13.0))
        m.box("onionflesh", (-8.0, -14.0, 2.0), (1.0, 23.0, 25.0), 1.0)
        for k in range(8 if cut == "chopped" else 3):
            m.box("onionflesh", ((k % 4) * 5.0 + (k // 4) * 1.5, -6.0, -10.0 + (k // 4) * 6.0), (4, 4, 3), 1.0, k * 23)
    spine = -KNIFE_LIFT[knife]
    m.box("steel", (14.0, spine, -6.0), (40.0, 9.0, 0.8), 0.3, rotation=-6.0 if knife == "down" else -14.0)
    m.box("black", (40.0, spine - 3.0, -6.0), (16.0, 5.0, 4.0), 2.0)


# -- the phone ---------------------------------------------------------------------------------------------------------
PHONE_STATES = ("recording", "playing")
_WAVE = (5.0, 9.0, 14.0, 8.0, 17.0, 11.0, 6.0, 13.0, 9.0)  # the playback's bars, tallest in the middle of the take


@register(
    "prop",
    "smallprint-phone",
    summary="A phone standing on the worktop, its screen to the lens, recording or playing a take back",
    contract=_contract(
        "smallprint-phone",
        PHONE_STATES,
        "recording shows a red dot on the screen; playing shows the take as a row of bars. No brand, no lettering.",
    ),
)
def phone(m: Model, state: str = "recording") -> None:
    """A plain phone upright in a little stand, its screen to the lens: a red dot while it records, the take as a row
    of bars while it plays back. Nothing on it is lettered or branded."""
    if state not in PHONE_STATES:
        raise PropError(f"the phone's states are {PHONE_STATES}, got {state!r}")
    m.box("cream", (0.0, -3.0, 4.0), (30.0, 6.0, 18.0), 2.0)
    m.box("case", (0.0, -34.0, 0.0), (28.0, 56.0, 3.6), 3.5)
    m.box("screen", (0.0, -34.0, -1.9), (24.5, 50.0, 0.4), 2.5)
    if state == "recording":
        m.ell("red", (0.0, -36.0, -2.6), (6.0, 6.0, 0.4))
        m.box("white", (0.0, -50.0, -2.3), (12.0, 1.6, 0.3), 0.3)
    else:
        for k, tall in enumerate(_WAVE):
            m.box("mint", (-10.0 + k * 2.5, -36.0, -2.45), (1.4, tall * 1.2, 0.4), 0.3)


# -- the bowl of water -----------------------------------------------------------------------------------------------
BOWL_STATES = ("soaking", "wrinkled")
BOWL_RIM = 20.0  # how high the bowl's rim stands over the worktop
_MARBLES = ((-10.0, 6.0), (2.0, 10.0), (11.0, -2.0), (-4.0, -8.0))  # x, z inside the bowl


@register(
    "prop",
    "smallprint-bowl",
    summary="A bowl of water with marbles in it, his fingers soaking in it or out of it, wrinkled",
    contract=_contract(
        "smallprint-bowl",
        BOWL_STATES,
        "soaking puts his hand in the water, hidden under its surface; wrinkled has it out on the worktop, its "
        "fingertips ridged (wrinkles) and two drops beside it.",
    ),
)
def bowl(m: Model, state: str = "soaking") -> None:
    """A clay bowl filled near its rim with water and a few marbles; out of the water, on ``wrinkled``, two drops on the
    worktop where his hand came out. Where his hand is, :func:`worktop` decides (:data:`HANDS`)."""
    if state not in BOWL_STATES:
        raise PropError(f"the bowl's states are {BOWL_STATES}, got {state!r}")
    m.lid("bowl", (0.0, -BOWL_RIM, 0.0), (30.0, BOWL_RIM, 30.0), 0.5, lower=True)
    m.ell("bowl", (0.0, -BOWL_RIM, 0.0), (31.5, 1.8, 31.5))  # its rim
    m.ell("water", (0.0, -BOWL_RIM - 1.3, 0.0), (28.5, 1.0, 28.5))  # its top just over the rim's, as the bowl is full
    for x, z in _MARBLES:
        m.ell("marble", (x, -BOWL_RIM - 1.6, z), (3.4, 3.4, 3.4))
    if state == "wrinkled":
        for x, z in ((36.0, 2.0), (42.0, 8.0)):
            m.ell("water", (x, -0.4, z), (2.6, 0.6, 2.2))


def wrinkles(m: Model, x: float, y: float, z: float) -> None:
    """Ridges across the tips of :func:`srstudio.rafa.rest`'s hand at ``x, y, z``: three over each finger's tip and
    three over the thumb's, lying on the skin's top where the lens sees them. His hand is his own drawing; this lies on
    it, as the tears lie on his face."""
    tips = [(x + 10 - i * 6.4 - 2, y - 3.2, z - 10 + abs(i - 1.3) * 2.1, 3.1) for i in range(4)]
    tips.append((x - 22, y - 3.5, z - 3, 3.5))
    for tx, ty, tz, r in tips:
        for dz in (-1.4, 0.0, 1.4):
            arc = [(tx + r * math.cos(a), ty - r * math.sin(a) - 0.15, tz + dz) for a in np.linspace(0.35, 2.8, 7)]
            m.tube("lip", arc, 0.6, n=10, sides=8)


# -- the model wall --------------------------------------------------------------------------------------------------
WALL_STATES = ("land", "snow")
_WALL_RUN = ((-38.0, 10.0), (-24.0, -4.0), (-8.0, 2.0), (6.0, -10.0), (22.0, -2.0), (36.0, -14.0))  # x, z of its bends


@register(
    "prop",
    "smallprint-wall",
    summary="A model of a long wall snaking over hills, the same colour as its land, or standing out on fresh snow",
    contract=_contract(
        "smallprint-wall",
        WALL_STATES,
        "land: the wall and its hills in two near-identical earth tones; snow: the same, the land under snow.",
    ),
)
def wall(m: Model, state: str = "land") -> None:
    """A board of rolling land with a crenellated wall snaking across it and two watchtowers, both of the same earth,
    so it is hard to pick out; on ``snow`` the land lies under snow and the wall stands out dark. No one place's
    landmark is copied: a long wall over hills."""
    if state not in WALL_STATES:
        raise PropError(f"the wall's states are {WALL_STATES}, got {state!r}")
    ground = "snow" if state == "snow" else "land"
    m.box("land", (0.0, -2.0, 0.0), (96.0, 4.0, 52.0), 1.6)
    for x, z, w, h in ((-26.0, 12.0, 30.0, 7.0), (14.0, 14.0, 36.0, 9.0), (34.0, -12.0, 22.0, 5.0)):
        m.ell(ground, (x, -3.0, z), (w / 2, h, 9.0))
    if state == "snow":
        m.box("snow", (0.0, -4.2, 0.0), (95.0, 0.6, 51.0), 0.3)
    for (ax, az), (bx, bz) in zip(_WALL_RUN, _WALL_RUN[1:], strict=False):
        run = math.hypot(bx - ax, bz - az)
        yaw = math.degrees(math.atan2(bz - az, bx - ax))

        def course(s: Model, run: float = run) -> None:
            s.box("wallstone", (0.0, -4.0, 0.0), (run + 2.0, 8.0, 3.2), 0.4)
            for k in range(int(run // 3.5)):
                s.box("wallstone", (-run / 2 + 1.75 + k * 3.5, -9.0, 0.0), (1.8, 2.0, 3.2), 0.2)

        _turned(m, course, _spin(0.0, -yaw), ((ax + bx) / 2, -4.0, (az + bz) / 2))
    for x, z in (_WALL_RUN[1], _WALL_RUN[4]):
        m.box("wallstone", (x, -10.0, z), (7.0, 12.0, 7.0), 0.6)


# -- the goldfish -----------------------------------------------------------------------------------------------------
GOLDFISH_STATES = ("swim", "turn", "fed")
_FISHBOWL = (32.0, 18.0, 0.83)  # the bowl: its widest radius, half its height as a whole round, the share of it made
FISHBOWL_RIM = _FISHBOWL[0] * math.sqrt(1.0 - (2.0 * _FISHBOWL[2] - 1.0) ** 2)  # its radius at the rim, about 24
_FISHBOWL_TALL = 2.0 * _FISHBOWL[1] * _FISHBOWL[2]  # how high its rim stands over the worktop, about 30
_FISH = {  # where the fish comes up through the water's top: x, z, which way he faces (1 frame right, -1 frame left)
    "swim": (-5.0, 6.0, -1.0),
    "turn": (6.0, 6.0, 1.0),
    "fed": (0.0, -8.0, 1.0),
}
_FISH_SIZE = (11.0, 5.6, 5.0)  # his half length, half height, half width
_NOSE_UP = {"swim": 38.0, "turn": 38.0, "fed": 48.0}  # degrees his nose points up out of the water


@register(
    "prop",
    "smallprint-goldfish",
    summary="A round glass bowl of water with a goldfish coming up through its top, nose first, mouth open",
    contract=_contract(
        "smallprint-goldfish",
        GOLDFISH_STATES,
        "swim and turn put the fish at the back of the water, facing frame left or right; fed brings him to the front "
        "with flakes on the water. His head comes up out of the water nose first, mouth open, so the lens sees him "
        "over the bowl's rim and he reads alive, not floating.",
    ),
)
def goldfish(m: Model, state: str = "swim") -> None:
    """A round bowl of pale glass filled to near its rim, and a goldfish coming up through the top of the water, his
    head out and his mouth open, as goldfish do at feeding time; on ``fed`` he is at the front among a few flakes. No
    one fish's likeness."""
    if state not in _FISH:
        raise PropError(f"the goldfish's states are {GOLDFISH_STATES}, got {state!r}")
    wide, half, share = _FISHBOWL
    m.lid("glass", (0.0, -half, 0.0), (wide, half, wide), share, lower=True)
    m.ell("glass", (0.0, -_FISHBOWL_TALL, 0.0), (FISHBOWL_RIM + 1.2, 1.4, FISHBOWL_RIM + 1.2))  # its rim
    top = -_FISHBOWL_TALL - 0.6
    m.ell("water", (0.0, top, 0.0), (FISHBOWL_RIM - 0.4, 0.6, FISHBOWL_RIM - 0.4))
    x, z, facing = _FISH[state]
    length, tall, thick = _FISH_SIZE
    up = math.radians(_NOSE_UP[state])
    ahead = (facing * math.cos(up), -math.sin(up))  # along his body, nose first (y grows down)
    over = (-facing * math.sin(up), -math.cos(up))  # square to it, toward his back

    def at(u: float, v: float, dz: float = 0.0) -> tuple[float, float, float]:
        cy = top + 0.8  # his middle at the water: the head out, the tail in the bowl
        return (x + u * ahead[0] + v * over[0], cy + u * ahead[1] + v * over[1], z + dz)

    tilt = -facing * _NOSE_UP[state]
    m.ell("goldfish", at(0.0, 0.0), (length, tall, thick), rotation=tilt)
    m.ell("fin", at(-0.1 * length, tall * 0.95), (3.8, 1.9, 0.8), rotation=tilt - facing * 18.0)  # on his back
    m.ell("black", at(0.55 * length, tall * 0.3, -thick * 0.75), (1.4, 1.4, 0.7))  # his eye, to the lens
    m.ell("fishmouth", at(0.92 * length, -tall * 0.05, -thick * 0.35), (1.3, 1.6, 1.0), rotation=tilt)  # open
    if state == "fed":
        for fx, fz in ((-6.0, -14.0), (5.0, -16.0), (-2.0, -19.0), (9.0, -12.0), (-10.0, -10.0)):
            m.box("flake", (fx, top - 0.9, fz), (2.4, 0.4, 1.8), 0.1)


# -- the apple -------------------------------------------------------------------------------------------------------
APPLE_STATES = ("fresh", "brown", "lemon")


APPLE_R = 15.0  # an apple half's radius
_FACE_TO_LENS = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])  # a quarter turn about x: up to the lens


def _half(m: Model, x: float, foot: float, flesh: str) -> None:
    """One apple half standing on its rim on ``foot``, its cut face to the lens: the flesh, the core with two pips one
    over the other, and the skin round the back."""

    def build(s: Model) -> None:  # face up, about the origin; turned so up looks at the lens
        s.lid("appleskin", (0.0, 0.0, 0.0), (APPLE_R, APPLE_R * 0.9, APPLE_R), 0.5, lower=True)
        s.ell(flesh, (0.0, -0.1, 0.0), (APPLE_R - 1.8, 0.6, APPLE_R - 1.8))  # a ring of red skin shows round it
        s.tube("oakdark", ((0.0, 1.5, APPLE_R - 2.0), (0.4, 1.5, APPLE_R + 1.5), (1.6, 1.2, APPLE_R + 4.5)), 0.9)
        s.ell("cream" if flesh == "appleflesh" else "oaklight", (0.0, -0.5, 0.0), (3.6, 0.3, 6.0))
        for dz in (-2.4, 2.4):
            s.ell("pip", (0.0, -0.8, dz), (1.1, 0.5, 1.9))

    _turned(m, build, _FACE_TO_LENS, (x, foot - APPLE_R, 0.0))


@register(
    "prop",
    "smallprint-apple",
    summary="An apple cut in half on a board, its faces pale, then brown, or one half kept pale by a lemon",
    contract=_contract(
        "smallprint-apple",
        APPLE_STATES,
        "fresh: two pale halves; brown: both faces brown; lemon: the left half brown, the right half pale with a "
        "squeezed lemon half beside it.",
    ),
)
def apple(m: Model, state: str = "fresh") -> None:
    """A board with an apple cut in two, both halves on their backs with their faces to the lens: pale when just cut,
    brown when left, and on ``lemon`` one half left brown and the other kept pale, a squeezed lemon half by it."""
    if state not in APPLE_STATES:
        raise PropError(f"the apple's states are {APPLE_STATES}, got {state!r}")
    m.box("board", (0.0, -2.0, 0.0), (76.0, 4.0, 40.0), 1.5)
    _half(m, -17.0, -4.0, "appleflesh" if state == "fresh" else "applebrown")
    _half(m, 17.0, -4.0, "applebrown" if state == "brown" else "appleflesh")
    if state == "lemon":  # a squeezed half, on its back by the pale half
        m.lid("lemon", (40.0, -11.0, -8.0), (8.0, 7.0, 8.0), 0.5, lower=True)
        m.ell("cream", (40.0, -11.2, -8.0), (7.6, 0.5, 7.6))


# -- the can ---------------------------------------------------------------------------------------------------------
CAN_STATES = ("shake-up", "shake-down", "foam", "calm")
CAN_TALL, CAN_R = 48.0, 12.0  # a soft-drink can, in his units
_SHAKE = {"shake-up": 30.0, "shake-down": 18.0}  # how high his hand lifts the can's foot off the worktop


@register(
    "prop",
    "smallprint-can",
    summary="A plain drink can, shaken up and down in his hand, then open on the worktop, foaming over or calm",
    contract=_contract(
        "smallprint-can",
        CAN_STATES,
        "shake-up and shake-down lift the closed can off the worktop in his hand; foam stands it open with foam over "
        "its top and down its side; calm stands it open with nothing come out. No brand, no lettering.",
    ),
)
def can(m: Model, state: str = "shake-up") -> None:
    """A plain can, one colour with a pale band and no lettering: closed and lifted while he shakes it, then open on
    the worktop, foam welling over its top and running down its side into a puddle, or, after a wait, just open."""
    if state not in CAN_STATES:
        raise PropError(f"the can's states are {CAN_STATES}, got {state!r}")
    foot = -_SHAKE.get(state, 0.0)
    m.cylinder("canpaint", (0.0, foot - CAN_TALL / 2, 0.0), CAN_R, CAN_TALL)
    m.cylinder("white", (0.0, foot - CAN_TALL * 0.42, 0.0), CAN_R + 0.2, 7.0)
    m.cylinder("steel", (0.0, foot - CAN_TALL - 1.0, 0.0), CAN_R - 1.2, 2.0)
    m.box("steel", (0.0, foot - CAN_TALL - 2.3, 2.5), (5.0, 0.6, 9.0), 0.3)  # the tab
    if state in ("foam", "calm"):
        m.ell("black", (0.0, foot - CAN_TALL - 2.1, -5.0), (3.4, 0.4, 2.2))  # it is open
    if state == "foam":
        for dx, dy, r in ((0.0, 4.0, 9.0), (-6.0, 1.5, 7.0), (6.0, 2.0, 7.5), (0.0, 8.5, 6.0)):
            m.ell("foam", (dx, foot - CAN_TALL - dy, -1.0), (r, r * 0.7, r))
        for k, (dx, run) in enumerate(((-7.0, 26.0), (2.0, 38.0), (8.0, 18.0))):
            drip = [(dx, foot - CAN_TALL - 1.0, -CAN_R + 1.5), (dx + 0.5 * k, foot - CAN_TALL + run / 2, -CAN_R - 0.6),
                    (dx - 0.4, foot - CAN_TALL + run, -CAN_R - 0.6)]  # fmt: skip
            m.tube("foam", drip, 2.2, n=12, sides=10)
        m.ell("foam", (CAN_R + 4.0, foot - 0.4, -2.0), (9.0, 0.7, 7.0))  # the puddle at its foot


def fist(m: Model, x: float, y: float, z: float) -> None:
    """His frame-right hand closed round a handle that lies across the lens: :func:`srstudio.rafa.hold` turned on its
    side, so the hand is his own drawing."""
    _turned(m, lambda s: rafa.hold(s, 0.0, 0.0, 0.0), _spin(-90.0), (x, y, z))


# -- the tears ---------------------------------------------------------------------------------------------------------
TEAR_BEADS = (  # under each eye, outward and down, growing to the drop: x, y, half-width, half-height (x mirrored)
    (22.6, -356.0, 0.9, 2.0),
    (23.3, -352.5, 1.2, 2.3),
    (24.0, -348.8, 1.6, 2.6),
    (24.6, -344.6, 2.2, 3.0),
)
TEAR_DEPTH = 0.8  # how far a bead stands off his skin: a glossy lens of water, not a rod


@cache
def _skin_points() -> np.ndarray:
    verts, _normals, _tris, _uvs = rafa_skin.sheet((), None)
    return np.asarray(verts, float)


def _skin_z(x: float, y: float) -> float:
    """The front of his skin at ``x, y``: the nearest surface to the lens there, so a tear lies on it."""
    points = _skin_points()
    near = points[(points[:, 0] - x) ** 2 + (points[:, 1] - y) ** 2 < 4.0]
    if not len(near):
        raise PropError(f"no skin at {x}, {y}")
    return float(near[:, 2].min())


@register(
    "prop",
    "smallprint-tears",
    summary="Two tears on Rafa's cheeks, one under each eye, on his skin's own surface",
    contract=_contract("smallprint-tears", ("tears",), "Built about his neck, as his eyes are; drawn on a pose plate."),
)
def tears(m: Model, state: str = "tears") -> None:
    """A short run of water beads from under each eye, growing to a drop, each a flat lens laid on the front of his
    skin, about his neck as his eyes are, so a head pose turns them with him."""
    if state != "tears":
        raise PropError(f"the tears have one state, 'tears', got {state!r}")
    with m.at(x=-rafa.NECK[0], y=-rafa.NECK[1], z=-rafa.NECK[2]):
        for side in (-1.0, 1.0):
            for x, y, w, h in TEAR_BEADS:
                m.ell("tear", (side * x, y, _skin_z(side * x, y) - TEAR_DEPTH * 0.6), (w, h, TEAR_DEPTH))


def tear_plate(turn: float, nod: float) -> Plate:
    """Him at a head pose with nothing on his face but the tears, to cut against :func:`rafa_host.pose_plate`."""
    sub = Model()
    tears(sub)
    worn = tuple(finished(mesh) for mesh in sub.meshes())
    placed = (Placed(rafa_host._body()), Placed((*rafa_host._skull(), *worn), rafa.NECK, nod, -turn))
    used = plates.materials_of([mesh for item in placed for mesh in item.meshes], materials())
    lights = plates.stage_lights(warm=True, room=False, rim=True)
    return Plate(rafa_host.WIDTH, rafa_host.HEIGHT, rafa_host.CAMERA, lights, placed, used)


# -- on his worktop -------------------------------------------------------------------------------------------------
STATES: dict[str, tuple[str, ...]] = {
    "smallprint-tower": TOWER_STATES,
    "smallprint-paper": PAPER_STATES,
    "smallprint-roll": ("roll",),
    "smallprint-onion": ONION_STATES,
    "smallprint-phone": PHONE_STATES,
    "smallprint-bowl": BOWL_STATES,
    "smallprint-wall": WALL_STATES,
    "smallprint-goldfish": GOLDFISH_STATES,
    "smallprint-apple": APPLE_STATES,
    "smallprint-can": CAN_STATES,
}
_DRAW: dict[str, Callable[..., None]] = {
    "smallprint-tower": tower,
    "smallprint-paper": paper,
    "smallprint-roll": roll,
    "smallprint-onion": onion,
    "smallprint-phone": phone,
    "smallprint-bowl": bowl,
    "smallprint-wall": wall,
    "smallprint-goldfish": goldfish,
    "smallprint-apple": apple,
    "smallprint-can": can,
}
PLACES: dict[str, tuple[float, float, float, float, float]] = {  # x, y, z, yaw, scale on the worktop
    "smallprint-tower": (-62.0, -248.0, -80.0, -10.0, 1.4),  # at his right, clear of his face and mouth
    "smallprint-paper": (40.0, -248.0, -80.0, -12.0, 1.6),
    "smallprint-roll": (34.0, -248.0, -80.0, -6.0, 1.0),
    "smallprint-onion": (30.0, -248.0, -78.0, -6.0, 1.0),
    "smallprint-phone": (-60.0, -248.0, -84.0, -14.0, 1.0),  # at his right, clear of his chin
    "smallprint-bowl": (16.0, -248.0, -80.0, 0.0, 1.0),
    "smallprint-wall": (2.0, -248.0, -70.0, -8.0, 1.0),
    "smallprint-goldfish": (8.0, -248.0, -78.0, 0.0, 1.2),
    "smallprint-apple": (6.0, -248.0, -80.0, -4.0, 1.0),
    "smallprint-can": (58.0, -248.0, -80.0, 0.0, 0.8),  # under his frame-right hand, clear of his chin
}
GRIPS: dict[str, tuple[str, tuple[float, float, float]]] = {  # his hand: a kind, and where (the knife's moves)
    "smallprint-tower": ("rest", (82.0, -248.0, -70.0)),
    "smallprint-paper": ("rest", (80.0, -248.0, -70.0)),
    "smallprint-roll": ("rest", (80.0, -248.0, -74.0)),
    "smallprint-onion": ("fist", (78.0, -252.0, -84.0)),
    "smallprint-phone": ("rest", (34.0, -248.0, -78.0)),
    "smallprint-bowl": ("rest", (72.0, -248.0, -70.0)),
    "smallprint-wall": ("rest", (80.0, -248.0, -72.0)),
    "smallprint-goldfish": ("rest", (76.0, -248.0, -72.0)),
    "smallprint-apple": ("rest", (82.0, -248.0, -72.0)),
    "smallprint-can": ("rest", (92.0, -248.0, -70.0)),
}
HANDS: dict[tuple[str, str], tuple[str, tuple[float, float, float]]] = {  # a state that moves his hand: kind, where
    ("smallprint-bowl", "soaking"): ("dip", (21.0, -256.0, -86.0)),  # in the water, under its surface
    ("smallprint-bowl", "wrinkled"): ("wrinkled", (72.0, -248.0, -70.0)),
    **{("smallprint-can", state): ("hold", (58.0, 0.0, -80.0)) for state in _SHAKE},  # round the can, where it is
}


def draw(m: Model, prop: str, state: str) -> None:
    """``prop`` in ``state``, about its foot."""
    if prop not in STATES:
        raise PropError(f"Small Print's worktop props are {tuple(STATES)}, got {prop!r}")
    _DRAW[prop](m, state)


def worktop(prop: str, state: str, where: str = "rafa-kitchen") -> Plate:
    """The worktop of room ``where`` with ``prop`` on it in ``state`` and his hand on it, on clear, to go in front of
    him: :func:`srstudio.rafa_host.foreground`'s plate, for a prop with states."""
    if where not in rafa_host.ROOM_TOPS:
        raise PropError(f"his rooms are {tuple(rafa_host.ROOM_TOPS)}, got {where!r}")
    model = Model()
    rafa.counter(model, *rafa_host.ROOM_TOPS[where])
    x, y, z, yaw, scale = PLACES.get(prop, (0.0, 0.0, 0.0, 0.0, 1.0))
    with model.at(x, y, z, yaw=yaw, scale=scale):
        draw(model, prop, state)
    kind, (hx, hy, hz) = HANDS.get((prop, state), GRIPS[prop])
    if kind == "fist":  # the knife rides up and down, and his fist with it
        hy = y - KNIFE_LIFT[state.split("-")[1]] - 4.0
        rafa.reach(model, (hx + 12.0, hy + 2.0, hz + 20.0))
        fist(model, hx, hy, hz)
    elif kind == "hold":  # round the lifted can, at the height the shake has it
        hy = y - (_SHAKE[state] + CAN_TALL * 0.4) * scale
        rafa.reach(model, (hx + 16.0, hy + 10.0, hz + 18.0))
        rafa.hold(model, hx + CAN_R * scale - 2.0, hy, hz + 1.0)
    elif kind == "dip":  # his forearm over the rim, the hand under the water
        rafa.reach(model, (hx + 14.0, y - BOWL_RIM - 3.0, hz + 18.0))
        rafa.rest(model, hx, hy, hz)
    else:
        rafa.reach(model, (hx + 5.0, hy - 9.0, hz + 22.0))
        rafa.rest(model, hx, hy, hz)
        if kind == "wrinkled":
            wrinkles(model, hx, hy, hz)
    rafa.near(model, where)
    meshes = tuple(finished(mesh) for mesh in model.meshes())
    lights = plates.stage_lights(warm=True, room=False, rim=True)  # as rafa_host.foreground lights his worktop
    used = plates.materials_of(meshes, materials())
    return Plate(rafa_host.WIDTH, rafa_host.HEIGHT, rafa_host.CAMERA, lights, (Placed(meshes),), used)


def part_plates(name: str) -> tuple[Plate, ...]:
    """What a catalog needs on disk to show the part ``name``: a worktop prop in its first state, under his hand, or
    the tears on him at rest; nothing for a part that is not Small Print's."""
    if name in STATES:
        return (worktop(name, STATES[name][0]),)
    if name == "smallprint-tears":
        return (tear_plate(0.0, 0.0),)
    return ()
