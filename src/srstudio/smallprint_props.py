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
    "PLACES",
    "STATES",
    "PropError",
    "draw",
    "finished",
    "materials",
    "onion",
    "paper",
    "part_plates",
    "roll",
    "tear_plate",
    "tears",
    "tower",
    "worktop",
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
}
_DRAW: dict[str, Callable[..., None]] = {
    "smallprint-tower": tower,
    "smallprint-paper": paper,
    "smallprint-roll": roll,
    "smallprint-onion": onion,
}
PLACES: dict[str, tuple[float, float, float, float, float]] = {  # x, y, z, yaw, scale on the worktop
    "smallprint-tower": (-62.0, -248.0, -80.0, -10.0, 1.4),  # at his right, clear of his face and mouth
    "smallprint-paper": (40.0, -248.0, -80.0, -12.0, 1.6),
    "smallprint-roll": (34.0, -248.0, -80.0, -6.0, 1.0),
    "smallprint-onion": (30.0, -248.0, -78.0, -6.0, 1.0),
}
GRIPS: dict[str, tuple[str, tuple[float, float, float]]] = {  # his hand: a kind, and where (the knife's moves)
    "smallprint-tower": ("rest", (82.0, -248.0, -70.0)),
    "smallprint-paper": ("rest", (80.0, -248.0, -70.0)),
    "smallprint-roll": ("rest", (80.0, -248.0, -74.0)),
    "smallprint-onion": ("fist", (78.0, -252.0, -84.0)),
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
    kind, (hx, hy, hz) = GRIPS[prop]
    if kind == "fist":  # the knife rides up and down, and his fist with it
        hy = y - KNIFE_LIFT[state.split("-")[1]] - 4.0
        rafa.reach(model, (hx + 12.0, hy + 2.0, hz + 20.0))
        fist(model, hx, hy, hz)
    else:
        rafa.reach(model, (hx + 5.0, hy - 9.0, hz + 22.0))
        rafa.rest(model, hx, hy, hz)
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
