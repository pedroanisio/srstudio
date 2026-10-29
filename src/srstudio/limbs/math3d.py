"""Dependency-free spatial arithmetic. Coordinates are x right, y down, z toward the viewer; angles are radians."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import LimbError


def number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise LimbError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def bounded(value: float, low: float, high: float, name: str) -> float:
    value = number(value, name)
    if not low <= value <= high:
        raise LimbError(f"{name} must be within {low}..{high}, got {value}", code="joint-limit")
    return value


@dataclass(frozen=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self) -> None:
        for name in ("x", "y", "z"):
            number(getattr(self, name), name)

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> Vec3:
        return self * -1

    def __mul__(self, scale: float) -> Vec3:
        number(scale, "scale")
        return Vec3(self.x * scale, self.y * scale, self.z * scale)

    def __truediv__(self, scale: float) -> Vec3:
        if number(scale, "scale") == 0:
            raise LimbError("division by zero")
        return self * (1 / scale)

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y, self.z)

    def unit(self) -> Vec3:
        if self.length < 1e-12:
            raise LimbError("a direction must not be zero")
        return self / self.length

    def distance(self, other: Vec3) -> float:
        return (self - other).length

    def lerp(self, other: Vec3, amount: float) -> Vec3:
        return self + (other - self) * amount

    def mirror(self) -> Vec3:
        return Vec3(-self.x, self.y, self.z)


@dataclass(frozen=True)
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self) -> None:
        values = [number(getattr(self, n), n) for n in ("w", "x", "y", "z")]
        length = math.hypot(*values)
        if length < 1e-12:
            raise LimbError("a rotation must not be a zero quaternion")
        for name, value in zip(("w", "x", "y", "z"), values, strict=True):
            object.__setattr__(self, name, value / length)

    @classmethod
    def axis_angle(cls, axis: Vec3, angle: float) -> Quaternion:
        angle = number(angle, "angle")
        a = axis.unit() * math.sin(angle / 2)
        return cls(math.cos(angle / 2), a.x, a.y, a.z)

    @classmethod
    def axes(cls, x: Vec3, y: Vec3, z: Vec3) -> Quaternion:
        # Matrix columns are the local axes in the parent frame.
        trace = x.x + y.y + z.z
        if trace > 0:
            s = math.sqrt(trace + 1) * 2
            return cls(s / 4, (y.z - z.y) / s, (z.x - x.z) / s, (x.y - y.x) / s)
        if x.x > y.y and x.x > z.z:
            s = math.sqrt(1 + x.x - y.y - z.z) * 2
            return cls((y.z - z.y) / s, s / 4, (y.x + x.y) / s, (z.x + x.z) / s)
        if y.y > z.z:
            s = math.sqrt(1 + y.y - x.x - z.z) * 2
            return cls((z.x - x.z) / s, (y.x + x.y) / s, s / 4, (z.y + y.z) / s)
        s = math.sqrt(1 + z.z - x.x - y.y) * 2
        return cls((x.y - y.x) / s, (z.x + x.z) / s, (z.y + y.z) / s, s / 4)

    def __neg__(self) -> Quaternion:
        return Quaternion(-self.w, -self.x, -self.y, -self.z)

    def __mul__(self, q: Quaternion) -> Quaternion:
        return Quaternion(
            self.w * q.w - self.x * q.x - self.y * q.y - self.z * q.z,
            self.w * q.x + self.x * q.w + self.y * q.z - self.z * q.y,
            self.w * q.y - self.x * q.z + self.y * q.w + self.z * q.x,
            self.w * q.z + self.x * q.y - self.y * q.x + self.z * q.w,
        )

    def inverse(self) -> Quaternion:
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def rotate(self, point: Vec3) -> Vec3:
        q = Vec3(self.x, self.y, self.z)
        t = q.cross(point) * 2
        return point + t * self.w + q.cross(t)

    def slerp(self, other: Quaternion, amount: float) -> Quaternion:
        bounded(amount, 0, 1, "rotation blend")
        a = (self.w, self.x, self.y, self.z)
        b: tuple[float, ...] = (other.w, other.x, other.y, other.z)
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        if dot < 0:
            b, dot = tuple(-x for x in b), -dot
        if dot > 0.9995:
            return Quaternion(*(x + (y - x) * amount for x, y in zip(a, b, strict=True)))
        theta = math.acos(min(1, dot))
        x, y = math.sin((1 - amount) * theta) / math.sin(theta), math.sin(amount * theta) / math.sin(theta)
        return Quaternion(*(u * x + v * y for u, v in zip(a, b, strict=True)))


@dataclass(frozen=True)
class Frame:
    origin: Vec3 = Vec3()
    rotation: Quaternion = Quaternion()

    def point(self, value: Vec3) -> Vec3:
        return self.origin + self.rotation.rotate(value)

    def inverse_point(self, value: Vec3) -> Vec3:
        return self.rotation.inverse().rotate(value - self.origin)

    def compose(self, child: Frame) -> Frame:
        return Frame(self.point(child.origin), self.rotation * child.rotation)


def along(origin: Vec3, direction: Vec3, twist: float = 0.0, *, across: Vec3 | None = None) -> Frame:
    """A frame whose +y follows a limb and whose +z normally faces the viewer."""
    y = direction.unit()
    if across is None:
        reference = Vec3(0, 0, 1) if abs(y.z) < 0.95 else Vec3(1, 0, 0)
        x = y.cross(reference).unit()
    else:
        x = across - y * across.dot(y)
        if x.length < 1e-10:
            axis = min((Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)), key=lambda a: abs(a.dot(y)))
            x = axis - y * axis.dot(y)
        x = x.unit()
    q = Quaternion.axes(x, y, x.cross(y))
    return Frame(origin, q * Quaternion.axis_angle(Vec3(0, 1, 0), twist))
