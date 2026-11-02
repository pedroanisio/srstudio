"""One projection owner: spatial poses enter a camera, then the drawing parent's inverse 2D transform."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .errors import LimbError
from .math3d import Frame, Quaternion, Vec3, items, number

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
        if len(items(self.origin, "camera origin")) != 2:
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


@dataclass(frozen=True)
class CameraSample:
    """A held spatial camera beginning at an explicit scene-second time."""

    time: float
    camera: Camera

    def __post_init__(self) -> None:
        if not 0 <= number(self.time, 'camera sample time') <= 600:
            raise LimbError('camera sample time must lie in 0..600', code='projection')
        if (
            type(self.camera) is not Camera
            or type(self.camera.origin) is not tuple
            or type(self.camera.view) is not Frame
            or type(self.camera.view.origin) is not Vec3
            or type(self.camera.view.rotation) is not Quaternion
        ):
            raise LimbError('camera samples need immutable Camera and Frame records', code='projection')
        self.camera.__post_init__()
        self.camera.view.origin.__post_init__()


@dataclass(frozen=True)
class CameraTrack:
    """Bounded held camera samples on the scene clock; the terminal sample is optional.

    Spatial interaction bakers merge these cuts with their frame grid. Geometry
    remains on its original local performance clock, even with a bake offset.
    This is sampled projection, not interpolation between camera orientations.
    """

    duration: float
    samples: tuple[CameraSample, ...]

    def __post_init__(self) -> None:
        if not 0 < number(self.duration, 'camera track duration') <= 600:
            raise LimbError('camera track duration must lie in (0, 600]', code='projection')
        if (
            type(self.samples) is not tuple
            or not 1 <= len(self.samples) <= 4097
            or any(type(sample) is not CameraSample for sample in self.samples)
        ):
            raise LimbError('camera track needs 1..4097 immutable CameraSample records', code='projection')
        for sample in self.samples:
            sample.__post_init__()
        if (
            self.samples[0].time != 0
            or self.samples[-1].time > self.duration
            or any(a.time >= b.time for a, b in zip(self.samples, self.samples[1:], strict=False))
        ):
            raise LimbError(
                'camera samples must begin at zero and strictly increase within duration', code='projection'
            )

    def sample(self, time: float) -> Camera:
        if not 0 <= number(time, 'camera sample time') <= self.duration:
            raise LimbError('camera sampling time is outside the track duration', code='projection')
        return self.samples[bisect_right(tuple(sample.time for sample in self.samples), time) - 1].camera
