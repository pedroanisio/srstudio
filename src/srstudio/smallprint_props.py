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
    "bread",
    "bowl",
    "can",
    "draw",
    "feather",
    "finished",
    "goldfish",
    "horse",
    "mars",
    "materials",
    "mint",
    "onion",
    "paper",
    "part_plates",
    "phone",
    "roll",
    "sunflower",
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
    "quill": ("#EFE6D2", 0.35, 0.0, False),
    "feather": ("#E9806E", 0.7, 0.0, True),
    "tin": ("#C9D3D0", 0.3, 0.5, False),
    "candy": ("#F7F3EA", 0.35, 0.0, True),
    "crust": ("#B97A3E", 0.62, 0.0, True),
    "stalecrust": ("#A9814F", 0.75, 0.0, True),
    "crumb": ("#EAD7AE", 0.7, 0.0, True),
    "steam": ("#F6F3EC", 0.8, 0.0, True),
    "horse": ("#A86B3C", 0.55, 0.0, True),
    "horsedark": ("#4A2E1E", 0.55, 0.0, True),
    "coat": ("#F3F0E8", 0.6, 0.0, True),
    "coatstripe": ("#25211F", 0.6, 0.0, True),
    "fly": ("#2B2A2E", 0.35, 0.0, False),
    "wing": ("#D8E6EE", 0.12, 0.0, False),
    "pot": ("#B8643F", 0.6, 0.0, True),
    "soil": ("#4A3526", 0.8, 0.0, True),
    "stem": ("#5E8F3A", 0.55, 0.0, True),
    "petal": ("#F2B731", 0.45, 0.0, True),
    "seedhead": ("#5A3A22", 0.7, 0.0, True),
    "lampbody": ("#2F5D62", 0.4, 0.2, False),
    "bulb": ("#FFE58A", 0.15, 0.0, False),
    "bulboff": ("#C9C3B6", 0.2, 0.0, False),
    "marsred": ("#C0532F", 0.62, 0.0, True),
    "marsdark": ("#8C3B24", 0.62, 0.0, True),
    "marscap": ("#F1ECE2", 0.5, 0.0, True),
    "marsinside": ("#A39D93", 0.7, 0.0, True),
    "stand": ("#4B4038", 0.4, 0.3, False),
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


# -- batch 3: the feather, the mint and the glass, the loaf ------------------------------------------------------------
FEATHER_STATES = ("tickle-a", "tickle-b", "rest")
FEATHER_FIST = (54.0, -284.0, -80.0)  # where his frame-right fist holds the quill up, under his chin and in front
_FEATHER_TIP = {"tickle-a": (12.0, -290.0, -36.0), "tickle-b": (24.0, -287.0, -38.0)}  # under his jaw, to his neck


def _feather(m: Model, root: tuple[float, float, float], tip: tuple[float, float, float]) -> None:
    """A quill from ``root`` to ``tip``, its vane a run of flat clay barbs along the last two thirds, widest past the
    middle, so it reads as a feather and not a stick."""
    a, b = np.asarray(root, float), np.asarray(tip, float)
    m.tube("quill", (tuple(a), tuple(a + (b - a) * 0.5 + (0.0, -3.0, 0.0)), tuple(b)), 0.9, n=16, sides=8)
    run = b - a
    turn = math.degrees(math.atan2(run[1], run[0]))
    for k, u in enumerate(np.linspace(0.3, 1.0, 9)):
        wide = 5.5 * math.sin(math.pi * min(1.0, (u - 0.25) / 0.8))
        centre = a + run * u + (0.0, -1.5 * math.sin(math.pi * u), 0.0)
        m.ell("feather", tuple(centre), (4.6, max(wide, 1.4), 1.1), rotation=turn + (8.0 if k % 2 else -8.0))


@register(
    "prop",
    "smallprint-feather",
    summary="A plain coral feather held up to his own neck, wiggling, or laid on the worktop",
    contract=_contract(
        "smallprint-feather",
        FEATHER_STATES,
        "tickle-a and tickle-b hold the quill up in his frame-right fist, its tip under his jaw in two places, a "
        "wiggle; rest lays it on the worktop under his resting hand. The prop is placed at his fist, so its "
        "coordinates are his model's, about the fist.",
    ),
)
def feather(m: Model, state: str = "tickle-a") -> None:
    """A feather, about its quill's root: up from his fist with its tip at his neck, in one of two places, so cutting
    between them wiggles it; or, at ``rest``, lying flat on the worktop."""
    if state not in FEATHER_STATES:
        raise PropError(f"the feather's states are {FEATHER_STATES}, got {state!r}")
    if state == "rest":  # on the worktop, below the fist's place, pointing frame left
        foot = -FEATHER_FIST[1] - 248.0
        _feather(m, (14.0, foot - 7.5, 0.0), (-40.0, foot - 7.5, -6.0))  # the vane on its edge, clear of the top
        return
    fx, fy, fz = FEATHER_FIST
    tx, ty, tz = _FEATHER_TIP[state]
    _feather(m, (-4.0, -8.0, 0.0), (tx - fx, ty - fy, tz - fz))


MINT_STATES = ("tin", "glass")
GLASS_TALL, GLASS_R = 40.0, 11.0
_GLASS_LIFT = 30.0  # how high his hand lifts the glass's foot off the worktop on ``glass``
_TIN = (-36.0, 0.0, -6.0)  # the open tin of mints, at the board's frame-left end
_GLASS_HAND = (40.0 + GLASS_R * 0.8 - 2.0, -248.0 - (_GLASS_LIFT + GLASS_TALL * 0.4) * 0.8, -79.0)  # his model's


@register(
    "prop",
    "smallprint-mint",
    summary="An open tin of plain white mints and a glass of water, standing or lifted in his hand",
    contract=_contract(
        "smallprint-mint",
        MINT_STATES,
        "tin stands the glass on the worktop and puts his hand by the open tin; glass lifts the glass off the worktop "
        "in his hand, the tin still open. No brand, no lettering.",
    ),
)
def mint(m: Model, state: str = "glass") -> None:
    """A round tin of mints with its lid off, a few white mints in it, and a tall glass of water: on the worktop, or
    lifted in his frame-right hand to drink."""
    if state not in MINT_STATES:
        raise PropError(f"the mint's states are {MINT_STATES}, got {state!r}")
    tx, _, tz = _TIN
    m.cylinder("tin", (tx, -3.0, tz), 13.0, 6.0)
    m.cylinder("tin", (tx - 6.0, -1.0, tz + 14.0), 13.5, 2.0)  # its lid, off and behind
    for dx, dz in ((-5.0, -3.0), (4.0, -4.0), (0.0, 4.0), (6.0, 4.0), (-6.0, 5.0)):
        m.ell("candy", (tx + dx, -6.8, tz + dz), (3.6, 1.6, 3.6))
    foot = -_GLASS_LIFT if state == "glass" else 0.0
    m.cylinder("glass", (0.0, foot - GLASS_TALL / 2, 0.0), GLASS_R, GLASS_TALL)
    m.ell("glass", (0.0, foot - GLASS_TALL, 0.0), (GLASS_R + 0.6, 0.9, GLASS_R + 0.6))  # its rim
    m.ell("water", (0.0, foot - GLASS_TALL + 6.0, 0.0), (GLASS_R - 0.8, 0.6, GLASS_R - 0.8))  # the water's top
    m.cylinder("water", (0.0, foot - (GLASS_TALL - 6.0) / 2, -GLASS_R + 1.6), GLASS_R * 0.55, GLASS_TALL - 7.0)


BREAD_STATES = ("knock-up", "knock-down", "warm")
LOAF = (58.0, 24.0, 32.0)  # the loaf's length, height and depth
_BOARD = 3.0
KNOCK_LIFT = {"knock-up": 18.0, "knock-down": 9.0}  # how high his fist's middle rides over the loaf's top


@register(
    "prop",
    "smallprint-bread",
    summary="A loaf on a board, stale and knocked on by his fist, or warmed with steam rising off it",
    contract=_contract(
        "smallprint-bread",
        BREAD_STATES,
        "knock-up and knock-down are the stale loaf, cracked and crumbed, with his fist over it high or knuckles "
        "down on it; warm is the same loaf with steam rising off it and his hand resting by it.",
    ),
)
def bread(m: Model, state: str = "knock-up") -> None:
    """A plain loaf on a board, no one bakery's: stale, its crust dull and cracked with crumbs round it, knocked on; or
    warmed again, its crust glossier and three thin wisps of steam rising off it."""
    if state not in BREAD_STATES:
        raise PropError(f"the bread's states are {BREAD_STATES}, got {state!r}")
    long, tall, deep = LOAF
    m.box("board", (0.0, -_BOARD / 2, 0.0), (long + 22.0, _BOARD, deep + 6.0), 1.2)
    crust = "crust" if state == "warm" else "stalecrust"
    m.box(crust, (0.0, -_BOARD - tall / 2, 0.0), (long, tall, deep), 9.0)
    m.ell(crust, (0.0, -_BOARD - tall + 1.0, 0.0), (long / 2 - 2.0, 5.0, deep / 2 - 2.0))  # its domed top
    if state == "warm":
        for k, x in enumerate((-14.0, 2.0, 16.0)):
            lift = -_BOARD - tall - 5.0  # short, so they stay under his chin
            wisp = [(x, lift, -4.0), (x + 2.0, lift - 5.0, -6.0), (x - 2.0, lift - 10.0, -6.0),
                    (x + 1.0, lift - 13.0 - k, -7.0)]  # fmt: skip
            m.tube("steam", wisp, 1.1, n=16, sides=10)
    else:
        front = -deep / 2 - 0.4
        for x, turn in ((-22.0, 70.0), (6.0, 110.0), (20.0, 80.0)):  # cracks down the dull crust's front
            m.box("oakdark", (x, -_BOARD - tall * 0.55, front), (0.8, tall * 0.5, 0.4), 0.2, rotation=turn - 90.0)
        for x, z in ((-34.0, -12.0), (-31.0, -16.0), (33.0, -14.0), (29.0, -18.0), (-4.0, -19.0)):
            m.ell("crumb", (x, -_BOARD - 1.0, z), (1.6, 1.0, 1.4))


def fist(m: Model, x: float, y: float, z: float) -> None:
    """His frame-right hand closed round a handle that lies across the lens: :func:`srstudio.rafa.hold` turned on its
    side, so the hand is his own drawing."""
    _turned(m, lambda s: rafa.hold(s, 0.0, 0.0, 0.0), _spin(-90.0), (x, y, z))


# -- batch 3: the toy horse ------------------------------------------------------------------------------------------
HORSE_STATES = ("flies", "coat")
HORSE_BODY = (22.0, 9.5, 8.5)  # the body's half-lengths: long, tall, thick
HORSE_BACK = -27.0  # the body's middle over the worktop
_COAT_GROW = 1.1  # how far the coat stands off his body
_FLIES_ON = ((-8.0, -33.5, -5.0), (6.0, -35.5, -2.0), (14.0, -27.0, -8.4))  # x, y, z: two on his back, one on his flank
_FLIES_OFF = ((-20.0, -44.0, -6.0), (-6.0, -47.0, -4.0), (8.0, -42.0, -8.0))  # over the coat, not touching it


def fly(m: Model, x: float, y: float, z: float) -> None:
    """A horse fly about ``x, y, z``: a dark body, its head to frame left, two pale wings folded back over it. Drawn a
    little larger than life, so the lens sees it at the worktop's distance."""
    m.ell("fly", (x, y, z), (3.4, 2.3, 2.3))
    m.ell("fly", (x - 3.5, y + 0.2, z), (1.7, 1.7, 1.7))
    for dz in (-1.6, 1.6):
        m.ell("wing", (x + 2.0, y - 2.4, z + dz), (3.8, 0.6, 1.9), rotation=-14.0)


def _section(x: float, coat: tuple[float, float, float], out: float) -> tuple[float, float]:
    """The half-height and half-thickness of the ellipsoid of half-lengths ``coat`` ``x`` along it, ``out`` more."""
    long, tall, thick = coat
    share = max(0.0, 1.0 - (x / long) ** 2) ** 0.5
    return tall * share + out, thick * share + out


@register(
    "prop",
    "smallprint-horse",
    summary="A clay toy horse in profile, horse flies landed on his back, or in a striped coat they do not land on",
    contract=_contract(
        "smallprint-horse",
        HORSE_STATES,
        "flies: a plain brown horse with three flies on his back and flank; coat: the same horse in a white coat "
        "with black stripes round it, the flies over it, none touching it. Head and legs stay bare, as in the trial.",
    ),
)
def horse(m: Model, state: str = "flies") -> None:
    """A toy horse standing in profile, his head to frame left: a plain brown body on four legs, neck, head, mane and
    tail. On ``flies`` three horse flies sit on him; on ``coat`` he wears a white coat ringed with black stripes over
    his body, his head and legs bare, and the flies hang in the air over it. No one breed's or toy's likeness."""
    if state not in HORSE_STATES:
        raise PropError(f"the horse's states are {HORSE_STATES}, got {state!r}")
    long, tall, thick = HORSE_BODY
    m.ell("horse", (0.0, HORSE_BACK, 0.0), HORSE_BODY)
    for x in (-15.0, 14.0):
        for z in (-4.5, 4.5):
            m.tube("horse", ((x, HORSE_BACK + 4.0, z), (x + 0.6, -9.0, z), (x, -2.0, z)), 2.6, n=10)
            m.ell("horsedark", (x - 0.4, -1.4, z), (3.0, 1.4, 2.8))  # a hoof
    m.tube("horse", ((-16.0, HORSE_BACK - 3.0, 0.0), (-22.0, -40.0, 0.0), (-25.0, -46.0, 0.0)), 5.0, n=12)
    m.ell("horse", (-30.5, -43.0, 0.0), (8.8, 4.4, 4.1), rotation=-30.0)  # the head, its muzzle down to frame left
    m.ell("horsedark", (-36.0, -39.6, -0.6), (2.8, 2.5, 3.4), rotation=-30.0)  # the muzzle
    m.ell("black", (-28.2, -45.6, -3.7), (1.2, 1.2, 0.6))  # his eye, to the lens
    for dz in (-1.8, 1.8):
        m.ell("horse", (-25.0, -49.5, dz), (1.4, 3.0, 1.2), rotation=-12.0)  # his ears
    m.tube("horsedark", ((-24.0, -49.0, 0.0), (-21.0, -43.0, 0.0), (-16.5, -36.0, 0.0)), 2.2, n=12)  # the mane
    m.tube("horsedark", ((long - 1.0, HORSE_BACK - 4.0, 0.0), (long + 5.0, HORSE_BACK, 0.0),
                         (long + 6.0, HORSE_BACK + 12.0, 0.0)), 1.9, n=12)  # fmt: skip  # the tail
    if state == "coat":
        coat = (long - 2.0, tall + _COAT_GROW, thick + _COAT_GROW)
        m.ell("coat", (0.0, HORSE_BACK - 0.6, 0.0), coat)
        for x in np.arange(-15.0, 16.0, 5.0):  # a band round the coat: a thin disc a little wider than it there
            ry, rz = _section(x, coat, 1.0)
            m.ell("coatstripe", (x, HORSE_BACK - 0.6, 0.0), (2.5, ry, rz))
        spots = _FLIES_OFF
    else:
        spots = _FLIES_ON
    for x, y, z in spots:
        fly(m, x, y, z)


# -- batch 3: the sunflower --------------------------------------------------------------------------------------------
SUNFLOWER_STATES = ("dark", "lamp")
SUNFLOWER_HEAD = (-6.0, -52.0, -2.0)  # the flower's middle, east of its stem: frame left is east on his worktop
SUNFLOWER_FACING = 62.0  # degrees about the upright from the lens towards frame left: it faces east, and the lens
LAMP_AT = 30.0  # the lamp's foot, to the west of the pot at frame right


def _front(facing: float) -> tuple[float, float]:
    """The x and z of the way a face turned ``facing`` degrees looks: towards the lens and, turned, to frame left."""
    spin = np.radians(facing)
    return -float(np.sin(spin)), -float(np.cos(spin))


def _along(centre: tuple[float, float, float], facing: float, out: float) -> tuple[float, float, float]:
    """``centre`` moved ``out`` the way a face turned ``facing`` looks, or behind it when ``out`` is negative."""
    fx, fz = _front(facing)
    return centre[0] + fx * out, centre[1], centre[2] + fz * out


def _petals(m: Model, centre: tuple[float, float, float], r: float, facing: float, n: int = 18) -> None:
    """A ring of ``n`` petals round a face of radius ``r`` about ``centre``, the face turned ``facing`` degrees."""
    fx, fz = _front(facing)
    cx, cy, cz = _along(centre, facing, -0.6)
    for k in range(n):
        a = 2.0 * np.pi * k / n
        out = r + 3.2
        dx, dy = out * np.cos(a), out * np.sin(a)  # across the face: along it sideways, perpendicular to its look
        m.ell("petal", (cx - dx * fz, cy + dy, cz + dx * fx), (4.2, 1.7, 0.7), rotation=float(np.degrees(a)),
              rotation_y=facing)  # fmt: skip


@register(
    "prop",
    "smallprint-sunflower",
    summary="A clay sunflower in full bloom in a terracotta pot, facing east, a desk lamp to its west off or on",
    contract=_contract(
        "smallprint-sunflower",
        SUNFLOWER_STATES,
        "dark: a grown sunflower in a pot, its open head facing east (frame left), a desk lamp at its west side, off; "
        "lamp: the same, the lamp's bulb lit, and the flower still facing east, away from it.",
    ),
)
def sunflower(m: Model, state: str = "dark") -> None:
    """A grown sunflower in a terracotta pot: a green stem with two leaves, its open head of yellow petals round a
    brown seed head turned to frame left, which is east on his worktop. A small desk lamp stands to its west, at frame
    right: dark on ``dark``, lit on ``lamp``. The flower faces east in both: a grown one has stopped turning."""
    if state not in SUNFLOWER_STATES:
        raise PropError(f"the sunflower's states are {SUNFLOWER_STATES}, got {state!r}")
    m.cylinder("pot", (0.0, -6.0, 0.0), 8.0, 12.0)
    m.cylinder("pot", (0.0, -12.6, 0.0), 9.2, 2.4)  # the rim
    m.cylinder("soil", (0.0, -13.6, 0.0), 8.2, 0.6)
    hx, hy, hz = SUNFLOWER_HEAD
    m.tube("stem", ((0.0, -13.0, 0.0), (0.6, -30.0, 0.0), (-1.0, -44.0, -0.5), (hx + 3.0, hy + 4.0, hz + 1.5)), 1.5)
    for side, y in ((-1.0, -24.0), (1.0, -32.0)):
        m.ell("stem", (side * 5.2, y, 0.0), (5.0, 1.6, 2.6), rotation=side * -28.0)  # a leaf
    head = (hx, hy, hz)
    m.ell("petal", _along(head, SUNFLOWER_FACING, -0.4), (8.4, 8.4, 1.0), rotation_y=SUNFLOWER_FACING)  # its backing
    _petals(m, head, 6.8, SUNFLOWER_FACING)
    m.ell("seedhead", _along(head, SUNFLOWER_FACING, 0.4), (6.6, 6.6, 1.8), rotation_y=SUNFLOWER_FACING)
    m.ell("stem", _along(head, SUNFLOWER_FACING, -1.6), (6.2, 6.2, 0.9), rotation_y=SUNFLOWER_FACING)  # its green back
    m.box("lampbody", (LAMP_AT, -1.0, 0.0), (13.0, 2.0, 10.0), radius=0.9)  # the lamp's base
    m.tube("lampbody", ((LAMP_AT + 2.0, -1.5, 0.0), (LAMP_AT + 3.0, -20.0, 0.0), (LAMP_AT - 4.0, -32.0, 0.0)), 1.2)
    m.ell("lampbody", (LAMP_AT - 9.0, -32.0, 0.0), (7.0, 4.6, 5.0), rotation=24.0)  # its shade, towards the flower
    m.ell("bulb" if state == "lamp" else "bulboff", (LAMP_AT - 12.0, -28.0, -0.5), (3.2, 3.2, 3.2))
    if state == "lamp":  # its light on the worktop, under the flower's back, and three drawn rays down to it
        m.ell("bulb", (LAMP_AT - 16.0, -0.15, 0.0), (15.0, 0.15, 10.0))
        for dx, dy in ((-9.0, -4.0), (-6.0, 8.0), (-1.0, 11.0)):
            m.tube(
                "bulb",
                ((LAMP_AT - 14.0 + 0.3 * dx, -27.0 + 0.3 * dy, -0.5), (LAMP_AT - 14.0 + dx, -27.0 + dy, -0.5)),
                0.6,
            )


# -- batch 3: Mars -----------------------------------------------------------------------------------------------------
MARS_STATES = ("red", "scratched")
MARS_CENTRE = (0.0, -26.0, 0.0)  # the globe's middle, on a short post over its stand
MARS_RADIUS = 16.0
_MARS_PATCHES = ((-40.0, 10.0), (25.0, -15.0), (60.0, 25.0), (-10.0, -35.0))  # darker ground: degrees round, degrees up
_CRUMBS = ((9.0, -0.8, -9.0), (12.5, -0.7, -7.0), (6.5, -0.6, -11.0), (11.0, -0.6, -11.5))  # on the worktop, in front


def _on_globe(round_: float, up: float, out: float) -> tuple[float, float, float]:
    """A point ``out`` from the globe's middle, ``round_`` degrees from the lens to frame right, ``up`` degrees up."""
    a, b = np.radians(round_), np.radians(up)
    cx, cy, cz = MARS_CENTRE
    return cx + out * float(np.sin(a) * np.cos(b)), cy - out * float(np.sin(b)), cz - out * float(np.cos(a) * np.cos(b))


@register(
    "prop",
    "smallprint-mars",
    summary="A clay Mars globe on a small stand, rust-red with darker ground and a white polar cap, plain or scratched",
    contract=_contract(
        "smallprint-mars",
        MARS_STATES,
        "red: a clay Mars globe on a stand, rust-red with darker patches and a white cap on top; scratched: the same, "
        "with a grey gouge on the side to the lens and grey crumbs on the worktop in front of it.",
    ),
)
def mars(m: Model, state: str = "red") -> None:
    """A clay globe of Mars on a post and a round stand: rust-red, with patches of darker ground and a white polar cap.
    ``scratched`` has a gouge across the side to the lens, grey under the red, and grey crumbs fallen in front of it."""
    if state not in MARS_STATES:
        raise PropError(f"the Mars globe's states are {MARS_STATES}, got {state!r}")
    m.cylinder("stand", (0.0, -1.0, 0.0), 8.0, 2.0)
    m.tube("stand", ((0.0, -2.0, 0.0), (0.0, -11.0, 0.0)), 1.6)
    m.ell("marsred", MARS_CENTRE, (MARS_RADIUS, MARS_RADIUS, MARS_RADIUS))
    for round_, up in _MARS_PATCHES:
        m.ell("marsdark", _on_globe(round_, up, MARS_RADIUS - 1.2), (4.6, 3.4, 2.4), rotation=round_ / 3.0)
    m.ell("marscap", (MARS_CENTRE[0], MARS_CENTRE[1] - MARS_RADIUS + 1.6, 0.0), (7.0, 1.6, 7.0))
    if state == "scratched":
        m.ell("marsinside", _on_globe(12.0, -6.0, MARS_RADIUS - 0.8), (7.5, 1.9, 2.0), rotation=-18.0)
        for spot in _CRUMBS:
            m.ell("marsinside", spot, (1.3, 0.9, 1.3))


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
    "smallprint-feather": FEATHER_STATES,
    "smallprint-mint": MINT_STATES,
    "smallprint-bread": BREAD_STATES,
    "smallprint-horse": HORSE_STATES,
    "smallprint-sunflower": SUNFLOWER_STATES,
    "smallprint-mars": MARS_STATES,
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
    "smallprint-feather": feather,
    "smallprint-mint": mint,
    "smallprint-bread": bread,
    "smallprint-horse": horse,
    "smallprint-sunflower": sunflower,
    "smallprint-mars": mars,
}
PLACES: dict[str, tuple[float, float, float, float, float]] = {  # x, y, z, yaw, scale on the worktop
    "smallprint-tower": (-62.0, -248.0, -80.0, -10.0, 1.4),  # at his right, clear of his face and mouth
    "smallprint-paper": (40.0, -248.0, -80.0, -12.0, 1.6),
    "smallprint-roll": (34.0, -248.0, -80.0, -6.0, 1.0),
    "smallprint-onion": (30.0, -248.0, -78.0, -6.0, 1.0),
    "smallprint-phone": (-60.0, -248.0, -84.0, -14.0, 1.0),  # at his right, clear of his chin
    "smallprint-bowl": (16.0, -248.0, -80.0, 0.0, 1.0),
    "smallprint-wall": (2.0, -248.0, -70.0, -8.0, 1.0),
    "smallprint-goldfish": (8.0, -248.0, -78.0, 0.0, 1.0),
    "smallprint-apple": (6.0, -248.0, -80.0, -4.0, 1.0),
    "smallprint-can": (58.0, -248.0, -80.0, 0.0, 0.8),  # under his frame-right hand, clear of his chin
    "smallprint-feather": (*FEATHER_FIST, 0.0, 1.0),  # about his raised fist, the quill's root
    "smallprint-mint": (40.0, -248.0, -80.0, 0.0, 0.8),  # the glass under his frame-right hand, the tin at his left
    "smallprint-bread": (14.0, -248.0, -80.0, -4.0, 1.0),
    "smallprint-horse": (-36.0, -248.0, -80.0, 0.0, 1.4),  # at frame left, the hovering flies clear of his chin
    "smallprint-sunflower": (-40.0, -248.0, -80.0, 0.0, 1.4),
    "smallprint-mars": (-40.0, -248.0, -80.0, 0.0, 1.4),
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
    "smallprint-feather": ("rest", (80.0, -248.0, -70.0)),
    "smallprint-mint": ("rest", (16.0, -248.0, -76.0)),  # by the tin, the glass standing at its right
    "smallprint-bread": ("rest", (66.0, -248.0, -72.0)),
    "smallprint-horse": ("rest", (74.0, -248.0, -72.0)),
    "smallprint-sunflower": ("rest", (74.0, -248.0, -72.0)),
    "smallprint-mars": ("rest", (74.0, -248.0, -72.0)),
}
HANDS: dict[tuple[str, str], tuple[str, tuple[float, float, float]]] = {  # a state that moves his hand: kind, where
    ("smallprint-bowl", "soaking"): ("dip", (21.0, -256.0, -86.0)),  # in the water, under its surface
    ("smallprint-bowl", "wrinkled"): ("wrinkled", (72.0, -248.0, -70.0)),
    **{("smallprint-can", state): ("hold", (58.0, 0.0, -80.0)) for state in _SHAKE},  # round the can, where it is
    **{("smallprint-feather", state): ("raise", FEATHER_FIST) for state in _FEATHER_TIP},  # the quill up in his fist
    ("smallprint-mint", "glass"): ("raise", _GLASS_HAND),  # round the lifted glass
    **{("smallprint-bread", state): ("knock", (16.0, 0.0, -84.0)) for state in KNOCK_LIFT},  # his fist over the loaf
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
    elif kind == "raise":  # his hand closed round something he holds up, where HANDS puts it
        rafa.reach(model, (hx + 16.0, hy + 10.0, hz + 18.0))
        rafa.hold(model, hx, hy, hz)
    elif kind == "knock":  # his fist over the loaf's top, high or knuckles down
        hy = y - _BOARD - LOAF[1] - 6.0 - KNOCK_LIFT[state]
        rafa.reach(model, (hx + 14.0, hy + 4.0, hz + 22.0))
        fist(model, hx, hy, hz)
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
