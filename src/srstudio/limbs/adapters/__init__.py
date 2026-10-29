"""Style adapters own ink and surface treatment; all receive the same projected anatomical pose."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Protocol

from ... import brush
from ...canvas import Canvas
from ..errors import LimbError
from ..geometry import ProjectedPose, path
from ..math3d import bounded


@dataclass(frozen=True)
class Capabilities:
    perspective: bool = True
    articulated_digits: bool = True
    native_planar: bool = True
    deformation: tuple[str, ...] = ("contour",)


@dataclass(frozen=True)
class Appearance:
    skin: str | None = None
    sleeve: str | None = None
    outline: str = "#16151b"
    line_width: float = 3.0
    detail: float = 0.65

    def __post_init__(self) -> None:
        for color in (self.skin, self.sleeve, self.outline):
            if color is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", color):
                raise LimbError(f"limb color {color!r} must be hexadecimal RGB or RGBA")
        bounded(self.line_width, 0, 100, "outline width")
        bounded(self.detail, 0, 1, "hand detail")


class Adapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> Capabilities: ...

    def draw(self, cv: Canvas, parent: Any, pose: ProjectedPose, appearance: Appearance, *, id: str) -> Any: ...


def _shade(color: str, amount: float) -> str:
    return "#" + "".join(f"{min(255, max(0, round(int(color[i : i + 2], 16) * amount))):02x}" for i in (1, 3, 5))


def _brush_path(shape: brush.Shape) -> str:
    out = f"M{shape[0]:.5f} {shape[1]:.5f}"
    for i in range(2, len(shape), 6):
        out += " C" + " ".join(f"{v:.5f}" for v in shape[i : i + 6])
    return out + " Z"


@dataclass(frozen=True)
class VectorAdapter:
    name: str
    skin: str
    sleeve: str
    treatment: str = "flat"
    capabilities: Capabilities = Capabilities()

    def draw(self, cv: Canvas, parent: Any, pose: ProjectedPose, appearance: Appearance, *, id: str) -> Any:
        group = cv.group(parent, id)
        for part in pose.parts:
            skin = appearance.skin or self.skin
            color = (appearance.sleeve or self.sleeve) if part.role == "sleeve" else skin
            outline, weight = appearance.outline, appearance.line_width
            points = part.polygon
            if self.treatment == "paper":
                # Stable per-part texture: frame IDs are deliberately excluded, so seeking and motion cannot boil.
                digest = hashlib.sha256(part.name.encode()).digest()
                points = tuple(
                    (x + (digest[i % 32] / 255 - 0.5) * 1.5, y + (digest[(i + 7) % 32] / 255 - 0.5) * 1.5)
                    for i, (x, y) in enumerate(points)
                )
                weight = 0
            elif self.treatment == "cel":
                weight = 0
            elif self.treatment == "pen":
                color, weight = "#fffdf7", max(1, weight * 0.55)
            elif self.treatment == "stick" and part.role == "sleeve":
                color, weight = outline, 0
                points = part.polygon
            elif self.treatment == "soft":
                weight *= 1.1
            fill = color
            if self.treatment == "vinyl":
                fill = cv.grad(
                    f"{id}-{part.name.replace(':', '-')}-vinyl",
                    [(0, _shade(color, 1.22)), (0.45, color), (1, _shade(color, 0.72))],
                    (0, 0, 0.8, 1),
                )
            if (
                self.treatment == "brush"
                and not part.authored
                and len(part.centerline) >= 2
                and max(math.dist(part.centerline[0], p) for p in part.centerline) > 1e-7
            ):
                d = _brush_path(brush.stroke(part.centerline, max(0.1, part.width), brush.EVEN))
            else:
                d = path(points)
            node = cv.path(group, d, fill, outline if weight else cv.clear, weight)
            if self.treatment in ("vinyl", "comic") and appearance.detail:
                a, b = part.centerline[0], part.centerline[-1]
                if math.dist(a, b) > 2:
                    cv.line(
                        group,
                        a[0],
                        a[1],
                        b[0],
                        b[1],
                        _shade(color, 1.3),
                        max(1, part.width * (0.13 if self.treatment == "vinyl" else 0.10)),
                        opacity=appearance.detail * 0.45,
                    )
            if part.name == "palm" and pose.palm_view == "palm" and appearance.detail > 0:
                x, y = part.centerline[0]
                cv.path(
                    group,
                    f"M{x - part.width * 0.22:g} {y:g} Q{x:g} {y + part.width * 0.12:g} {x + part.width * 0.2:g} {y:g}",
                    stroke=_shade(skin, 0.7),
                    sw=max(0.6, weight * 0.45),
                    opacity=appearance.detail,
                )
            if part.name.startswith("digit:") and pose.palm_view == "back" and appearance.detail > 0:
                x, y = part.centerline[-1]
                r = max(0.5, part.width * 0.22)
                cv.ellipse(group, x - r, y - r, 2 * r, r * 1.1, _shade(skin, 1.12), opacity=appearance.detail)
            # Keep node ownership local to this adapter invocation; all anonymous paths use Canvas.uid.
            assert node is not None
        return group


_ADAPTERS: dict[str, Adapter] = {}


def register_adapter(name: str, adapter: Adapter) -> None:
    if (
        not name
        or not callable(getattr(adapter, "draw", None))
        or not isinstance(getattr(adapter, "capabilities", None), Capabilities)
    ):
        raise LimbError("a limb adapter needs a name, draw method and explicit Capabilities")
    if name in _ADAPTERS:
        raise LimbError(f"limb adapter {name!r} is already registered")
    _ADAPTERS[name] = adapter


def adapter_for(name: str) -> Adapter:
    try:
        return _ADAPTERS[name]
    except KeyError:
        raise LimbError(f"no limb adapter {name!r}; registered: {', '.join(_ADAPTERS)}") from None


for _adapter in (
    VectorAdapter("cutout", "#e4b494", "#dbe5e5"),
    VectorAdapter("ink", "#fffdf7", "#fffdf7", "pen"),
    VectorAdapter("soft", "#fffdf9", "#fffdf9", "soft"),
    VectorAdapter("cel", "#e9c8ac", "#4e919a", "cel"),
    VectorAdapter("stick", "#e5c29d", "#15151b", "stick"),
    VectorAdapter("toon", "#edbf99", "#6fb2cf", "brush"),
    VectorAdapter("saga", "#bd8a68", "#eee0c6", "comic"),
    VectorAdapter("collage", "#ebbf9b", "#c87e9c", "paper"),
    VectorAdapter("gloss", "#edb39d", "#b993de", "vinyl"),
):
    register_adapter(_adapter.name, _adapter)
