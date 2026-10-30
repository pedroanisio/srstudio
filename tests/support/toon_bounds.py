"""Where a drawn group lands on the frame, read from the scene document alone: each shape and text layer under it
taken through the group transforms (``x``/``y``, ``rotation``, ``scaleX``/``scaleY`` about ``anchorX``/``anchorY``)
at their static values. Animated values are not followed, so a part that moves declares the reach of its motion."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from srstudio import Canvas
from srstudio.layout import Box, Matrix, shape_bounds


def _mul(m: Matrix, n: Matrix) -> Matrix:
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def _local(node: ET.Element) -> Matrix:
    def num(name: str, default: float) -> float:
        return float(node.get(name, default))

    t = math.radians(num("rotation", 0))
    ax, ay = num("anchorX", 0), num("anchorY", 0)
    m = (math.cos(t), math.sin(t), -math.sin(t), math.cos(t), num("x", 0), num("y", 0))
    m = _mul(m, (num("scaleX", 1), 0.0, 0.0, num("scaleY", 1), 0.0, 0.0))
    return _mul(m, (1.0, 0.0, 0.0, 1.0, -ax, -ay))


def _boxes(node: ET.Element, m: Matrix, texts: dict[str, ET.Element]):
    for child in node:
        if child.tag == "group":
            yield from _boxes(child, _mul(m, _local(child)), texts)
        elif child.tag == "shape":
            w, h = float(child.get("width", 0)), float(child.get("height", 0))
            at = _mul(m, (1.0, 0.0, 0.0, 1.0, float(child.get("x", 0)), float(child.get("y", 0))))
            yield shape_bounds(child, (w, h)).transformed(at)
        elif child.tag == "layer" and child.get("asset") in texts:
            asset = texts[child.get("asset")]
            at = _mul(m, (1.0, 0.0, 0.0, 1.0, float(child.get("x", 0)), float(child.get("y", 0))))
            yield Box(0, 0, float(asset.get("width")), float(asset.get("height"))).transformed(at)


def drawn(cv: Canvas, group_id: str, overrides: dict[str, dict[str, float]] | None = None) -> Box:
    """The frame-pixel box around everything drawn under the group ``group_id``, its own transform included;
    ``overrides`` sets group attributes first (a group as an animation takes it, ``{id: {"scaleX": 1.2}}``)."""
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    for g in root.iter("group"):
        for name, value in (overrides or {}).get(g.get("id", ""), {}).items():
            g.set(name, str(value))
    texts = {t.get("id"): t for t in root.iter("text")}
    group = next((g for g in root.iter("group") if g.get("id") == group_id), None)
    assert group is not None, f"no group {group_id!r}"
    boxes = list(_boxes(group, _local(group), texts))
    assert boxes, f"group {group_id!r} draws nothing"
    return Box(min(b.x0 for b in boxes), min(b.y0 for b in boxes), max(b.x1 for b in boxes), max(b.y1 for b in boxes))


def marks(cv: Canvas) -> list[str]:
    """The ids of the signature marks' groups on the canvas."""
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g.get("id") for g in root.iter("group") if g.get("id", "").startswith(("sig-cactus", "sig-code"))]
