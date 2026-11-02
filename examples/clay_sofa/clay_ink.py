"""The room's line on the clay: an outline drawn over the composite from a pass painting each part its own colour.

The lounge plates draw the room in black, a heavy line round the sofa and the pillows and a fine one everywhere else
(``examples/paintover_proof/lounge_plates.py``: ``INK``, ``INK_WIDTH``, ``FINE_WIDTH``). The clay takes the same line,
read from that file rather than copied: the heavy one where a figure meets the room or the other figure, the fine one
where one of its parts meets another (an arm over the belly, an ear over the head).

    ROOM_LINE                     # Line(colour, heavy, fine), as the room's plates draw it
    id_colour(who, part) -> rgb   # the flat colour the ID pass paints a part with
    ink(picture, ids, line)       # the picture with the line drawn where the ID pass changes part
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
from scipy import ndimage

PLATES = Path(__file__).resolve().parent.parent / "paintover_proof" / "lounge_plates.py"
PARTS = ("skin", "ear0", "ear1", "arm-left", "arm-right", "paw-left", "paw-right", "remote")  # a pad is its paw
WHO = ("mae", "bruno")


class InkError(ValueError):
    """An ID colour asked of a part the clay does not have, or passes that do not line up."""


class Line(NamedTuple):
    colour: str
    heavy: float  # pixels on the 1080-wide frame
    fine: float


def _room_line(path: Path = PLATES) -> Line:
    """``INK``, ``INK_WIDTH`` and ``FINE_WIDTH`` as the room's plates assign them, read without running the file (it
    needs the room's own engine library, which the clay does not)."""
    wanted = {"INK", "INK_WIDTH", "FINE_WIDTH"}
    found: dict[str, object] = {}
    for node in ast.parse(path.read_text()).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in wanted:
            found[target.id] = ast.literal_eval(node.value)
        elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
            for item, each in zip(target.elts, node.value.elts, strict=True):
                if isinstance(item, ast.Name) and item.id in wanted:
                    found[item.id] = ast.literal_eval(each)
    try:
        colour, heavy, fine = found["INK"], found["INK_WIDTH"], found["FINE_WIDTH"]
    except KeyError as missing:
        raise InkError(f"{path.name} no longer assigns {missing}: the room's line is not known") from None
    if not (isinstance(colour, str) and isinstance(heavy, (int, float)) and isinstance(fine, (int, float))):
        raise InkError(f"{path.name}: the room's line is not a colour and two widths")
    return Line(colour, float(heavy), float(fine))


ROOM_LINE = _room_line()


def id_colour(who: str, part: str) -> np.ndarray:
    """The ID pass's colour for ``part`` of ``who``: blue full for Bruno and off for Mae, so a heavy line runs between
    the two figures; red and green from the part, never both off, so no part is the sofa's black."""
    if who not in WHO:
        raise InkError(f"no figure {who!r}")
    if part not in PARTS:
        raise InkError(f"no part {part!r} on the clay")
    k = PARTS.index(part) + 1  # 1..8: three steps on red and on green, never both off
    red, green = (k % 3) / 2.0, (k // 3) / 2.0
    return np.array((red, green, 1.0 if who == "bruno" else 0.0))


def _labels(ids: np.ndarray) -> np.ndarray:
    """Each ID pixel as the integer of the part whose colour it is nearest, 0 for the room (the clear, the sofa's
    black): a pixel the raster blends at an edge goes to one side of it, never to a gap of its own."""
    palette = [np.zeros(3)] + [id_colour(w, p) for w in WHO for p in PARTS]
    rgb = ids[..., :3]
    out = np.zeros(ids.shape[:2], dtype=np.int32)
    best = np.full(ids.shape[:2], np.inf)
    for n, colour in enumerate(palette):
        distance = ((rgb - colour) ** 2).sum(axis=2)
        nearer = distance < best
        out[nearer], best[nearer] = n, distance[nearer]
    out[ids[..., 3] <= 0.5] = 0
    return out


def paw_pixels(ids: np.ndarray, line: Line) -> np.ndarray:
    """Where the ID pass shows a paw, or the forearm drawn in its colour, of either figure, grown by half of
    ``line``'s heavy width so the paw's own line round it is taken in too."""
    paws = [1 + w * len(PARTS) + PARTS.index(p) for w in range(len(WHO)) for p in ("paw-left", "paw-right")]
    found = np.isin(_labels(ids), paws)
    grow = math.ceil(line.heavy / 2.0)
    return ndimage.binary_dilation(found, iterations=grow) if found.any() and grow > 0 else found


def _edges(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Boolean maps of the pixels on either side of a crack between labels: heavy where a figure meets the room or the
    other figure, fine where two parts of one figure meet."""
    figure = (labels - 1) // len(PARTS)  # -1 for the room, then 0 and 1
    figure[labels == 0] = -1
    heavy = np.zeros(labels.shape, dtype=bool)
    fine = np.zeros(labels.shape, dtype=bool)
    for axis in (0, 1):
        n = labels.shape[axis]
        a, b = labels.take(range(n - 1), axis=axis), labels.take(range(1, n), axis=axis)
        fa, fb = figure.take(range(n - 1), axis=axis), figure.take(range(1, n), axis=axis)
        cut = a != b
        for found, which in ((cut & (fa != fb), heavy), (cut & (fa == fb), fine)):
            before, after = [slice(None)] * 2, [slice(None)] * 2
            before[axis], after[axis] = slice(0, n - 1), slice(1, n)
            which[tuple(before)] |= found
            which[tuple(after)] |= found
    return heavy, fine


def _rgb(colour: str) -> np.ndarray:
    text = colour.lstrip("#")
    if len(text) != 6:
        raise InkError(f"not a colour: {colour!r}")
    return np.array([int(text[k : k + 2], 16) / 255.0 for k in (0, 2, 4)])


def _stroke(beside: np.ndarray, width: float) -> np.ndarray:
    """Coverage of a line ``width`` pixels wide centred on the cracks the ``beside`` pixels touch (each half a pixel
    from its crack), its last half pixel shaded."""
    if not beside.any():
        return np.zeros(beside.shape)
    distance = ndimage.distance_transform_edt(~beside) + 0.5
    return np.clip(width / 2.0 - distance + 0.5, 0.0, 1.0)


def ink(picture: np.ndarray, ids: np.ndarray, line: Line) -> np.ndarray:
    """``picture`` with ``line`` drawn over it: heavy round each figure, fine between its parts. Only the line's pixels
    change, and the picture's alpha is raised to cover them."""
    if picture.shape[:2] != ids.shape[:2] or picture.shape[2] != 4 or ids.shape[2] != 4:
        raise InkError(f"the picture {picture.shape} and the ID pass {ids.shape} do not line up")
    heavy, fine = _edges(_labels(ids))
    cover = np.maximum(_stroke(heavy, line.heavy), _stroke(fine, line.fine))
    out = picture.copy()
    out[..., :3] = out[..., :3] * (1.0 - cover[..., None]) + _rgb(line.colour) * cover[..., None]
    out[..., 3] = np.maximum(out[..., 3], cover)
    return out
