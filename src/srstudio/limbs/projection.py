"""One projection owner: spatial poses enter a camera, then the drawing parent's inverse 2D transform."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LimbError
from .math3d import Frame, Vec3, number

_IDENTITY = Frame()


@dataclass(frozen=True)
class Affine:
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def __post_init__(self) -> None:
        for n in ("a", "b", "c", "d", "e", "f"):
            number(getattr(self, n), n)

    def point(self, xy: tuple[float, float]) -> tuple[float, float]:
        x, y = xy
        return (self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f)

    def inverse(self) -> Affine:
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-12:
            raise LimbError("drawing parent has a singular transform", code="projection")
        return Affine(
            self.d / det,
            -self.b / det,
            -self.c / det,
            self.a / det,
            (self.c * self.f - self.d * self.e) / det,
            (self.b * self.e - self.a * self.f) / det,
        )


@dataclass(frozen=True)
class Projected:
    xy: tuple[float, float]
    depth: float
    scale: float

    def __post_init__(self) -> None:
        if not isinstance(self.xy, tuple) or len(self.xy) != 2:
            raise LimbError("projected coordinates need an immutable x/y pair", code="projection")
        for value in (*self.xy, self.depth, self.scale):
            number(value, "projected coordinate or scale")
        if self.scale <= 0:
            raise LimbError("projected scale must remain positive", code="projection")


_PARENT = Affine()


@dataclass(frozen=True)
class Camera:
    projection: str = "orthographic"
    distance: float = 10.0
    focal: float = 10.0
    scale: float = 100.0
    origin: tuple[float, float] = (0, 0)
    view: Frame = Frame()
    near: float = 0.01

    def __post_init__(self) -> None:
        if self.projection not in ("orthographic", "perspective"):
            raise LimbError("camera projection must be orthographic or perspective")
        for n in ("distance", "focal", "scale", "near"):
            if number(getattr(self, n), n) <= 0:
                raise LimbError(f"camera {n} must be positive")
        if len(self.origin) != 2:
            raise LimbError("camera origin must contain x and y")
        for v in self.origin:
            number(v, "camera origin")

    def project(self, value: Vec3, *, frame: Frame = _IDENTITY, parent: Affine = _PARENT) -> Projected:
        p = self.view.inverse_point(frame.point(value))
        factor = 1.0
        if self.projection == "perspective":
            distance = self.distance - p.z
            if distance <= self.near:
                raise LimbError("point crosses the camera near plane", code="projection")
            factor = self.focal / distance
        xy = (self.origin[0] + p.x * self.scale * factor, self.origin[1] + p.y * self.scale * factor)
        return Projected(parent.inverse().point(xy), p.z, self.scale * factor)
