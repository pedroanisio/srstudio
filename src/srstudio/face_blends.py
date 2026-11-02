"""Explicit authored facial deformation, sampled on the original performance clock.

Blenders own geometry, never inferred topology or opacity crossfades. The bounded
track prepares all geometry before a scene is changed. Rendering holds samples;
``sample`` exposes the continuous intent, not a claim of continuous raster output.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from . import checks
from ._curves import progress
from .errors import SrstudioError
from .toon_cast import Layer, _eye, _mouth

if TYPE_CHECKING:
    from .toon import Pose
    from .toon_head import HeadRig

MAX_FRAMES = 1000
MAX_COORDINATES = 2_000_000
CURVES = ('linear', 'sine-in-out', 'cubic-in-out', 'quint-in-out')


class FaceBlendError(SrstudioError, ValueError):
    """An undeclared, conflicting or unbounded facial deformation."""


def _fail(path, actual, expected, code='face_blend.input'):
    return FaceBlendError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Choose an explicitly declared expression pair and one facial owner on the performance clock.',
    )


@dataclass(frozen=True)
class FacePose:
    eyes: str
    mouth: str

    def __post_init__(self) -> None:
        if any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in (self.eyes, self.mouth)):
            raise _fail('face', (self.eyes, self.mouth), 'two names of 1..128 characters')


@dataclass(frozen=True)
class FaceSample:
    source: FacePose
    target: FacePose
    weight: float

    def __post_init__(self) -> None:
        if not isinstance(self.source, FacePose) or not isinstance(self.target, FacePose):
            raise _fail('blend.expressions', None, 'typed FacePose endpoints')
        if not checks.number(self.weight) or not 0 <= self.weight <= 1:
            raise _fail('blend.weight', self.weight, 'a normalized weight in 0..1')


@dataclass(frozen=True)
class FaceBlend:
    start: float
    end: float
    source: FacePose
    target: FacePose
    curve: str = 'sine-in-out'

    def __post_init__(self) -> None:
        if not (
            checks.number(self.start)
            and checks.number(self.end)
            and 0 <= self.start < self.end <= 600
            and round(self.start, 6) == self.start
            and round(self.end, 6) == self.end
        ):
            raise _fail('blend.interval', (self.start, self.end), '0 <= start < end <= 600 at six-decimal precision')
        if not isinstance(self.source, FacePose) or not isinstance(self.target, FacePose):
            raise _fail('blend.expressions', None, 'typed FacePose endpoints')
        if self.source == self.target or self.curve not in CURVES:
            raise _fail('blend', self.curve, {'distinct_expressions': True, 'curves': CURVES})

    def sample(self, time: float) -> FaceSample:
        if not checks.number(time):
            raise _fail('time', time, 'a finite performance second')
        return FaceSample(self.source, self.target, progress(self.curve, (time - self.start) / (self.end - self.start)))


@dataclass(frozen=True)
class FaceLayers:
    eyes: tuple[Layer, ...]
    mouth: tuple[Layer, ...]


@runtime_checkable
class FaceBlender(Protocol):
    """Explicit directed pairs and a pure geometry sampler in reference pixels.

    Endpoints must match the rig's static faces. Unsupported channels, such as a
    topology-changing mouth, require another declared pair/driver, never a fallback.
    """

    @property
    def transitions(self) -> tuple[tuple[FacePose, FacePose], ...]: ...

    def layers(self, sample: FaceSample) -> FaceLayers: ...


@dataclass(frozen=True)
class FaceFrame:
    start: float
    end: float
    layers: FaceLayers


@dataclass(frozen=True)
class FaceTrack:
    blends: tuple[FaceBlend, ...]
    fps: int = 30

    def __post_init__(self) -> None:
        if type(self.fps) is not int or not 1 <= self.fps <= 120:
            raise _fail('face.fps', self.fps, 'an integer in 1..120')
        if not isinstance(self.blends, tuple) or not 1 <= len(self.blends) <= 1000:
            raise _fail('face.blends', None, '1..1000 typed blends')
        previous = 0.0
        for blend in self.blends:
            if not isinstance(blend, FaceBlend) or blend.start < previous:
                raise _fail('face.blends', None, 'ordered, non-overlapping FaceBlends')
            previous = blend.end
        if sum(math.ceil((b.end - b.start) * self.fps) + 1 for b in self.blends) > MAX_FRAMES:
            raise _fail('face.frames', None, f'at most {MAX_FRAMES} held frames', 'face_blend.budget')

    def sample(self, time: float) -> FaceSample | None:
        if not checks.number(time):
            raise _fail('time', time, 'a finite performance second')
        return next((b.sample(time) for b in self.blends if b.start <= time < b.end), None)

    def prepare(self, rig: HeadRig, poses: tuple[Pose, ...], duration: float) -> tuple[FaceFrame, ...]:
        from .toon import Pose
        from .toon_head import HeadRig

        if not isinstance(rig, HeadRig) or not checks.number(duration) or not 0 < duration <= 600:
            raise _fail('rig/duration', None, 'a HeadRig and finite duration in (0, 600]')
        if (
            not isinstance(poses, tuple)
            or not 1 <= len(poses) <= 1000
            or any(not isinstance(p, Pose) or not checks.number(p.start) or not 0 <= p.start < duration for p in poses)
            or poses[0].start != 0
            or any(a.start >= b.start for a, b in zip(poses, poses[1:], strict=False))
        ):
            raise _fail('poses', None, '1..1000 ordered poses from zero inside the performance')
        blender = rig.face_blender
        if not isinstance(blender, FaceBlender):
            raise _fail('rig.face_blender', rig.look.name, 'a declared FaceBlender', 'face_blend.unsupported')
        pairs = blender.transitions
        if (
            not isinstance(pairs, tuple)
            or not 1 <= len(pairs) <= 1000
            or any(
                not isinstance(p, tuple) or len(p) != 2 or any(not isinstance(e, FacePose) for e in p) for p in pairs
            )
        ):
            raise _fail('rig.face_blender.transitions', None, '1..1000 directed pairs of FacePose')
        frames = []
        coordinates = 0
        verified = set()
        for blend in self.blends:
            if (blend.source, blend.target) not in pairs:
                raise _fail('blend.expressions', (blend.source, blend.target), pairs, 'face_blend.unsupported')
            if blend.end >= duration:
                raise _fail('blend.end', blend.end, 'arrival before the performance ends')
            held = max((p for p in poses if p.start <= blend.start), key=lambda p: p.start)
            arrived = max((p for p in poses if p.start <= blend.end), key=lambda p: p.start)
            if FacePose(held.eyes, held.mouth) != blend.source or FacePose(arrived.eyes, arrived.mouth) != blend.target:
                raise _fail('blend.expressions', None, 'endpoints matching the held poses at launch and arrival')
            if any(blend.start < p.start < blend.end for p in poses):
                raise _fail('poses', None, 'no pose replacement during an authored blend')
            pair = (blend.source, blend.target)
            if pair not in verified:
                for endpoint, weight in ((blend.source, 0), (blend.target, 1)):
                    layers = blender.layers(FaceSample(blend.source, blend.target, weight))
                    coordinates += _validate_layers(layers)
                    look = rig.look
                    expected = FaceLayers(
                        tuple(
                            _eye(look, look.eyes[0], endpoint.eyes, 1.0) + _eye(look, look.eyes[1], endpoint.eyes, -1.0)
                        ),
                        tuple(_mouth(look, endpoint.mouth)),
                    )
                    if layers != expected:
                        raise _fail('blend.endpoints', None, 'exact endpoint geometry of the bound rig')
                verified.add(pair)
            # The grid is anchored at performance zero, never at a shot/crop boundary.
            times = sorted(
                {
                    blend.start,
                    blend.end,
                    *(
                        round(i / self.fps, 6)
                        for i in range(math.floor(blend.start * self.fps) + 1, math.ceil(blend.end * self.fps))
                        if blend.start < round(i / self.fps, 6) < blend.end
                    ),
                }
            )
            for start, end in zip(times, times[1:], strict=False):
                layers = blender.layers(blend.sample(start))
                coordinates += _validate_layers(layers)
                if coordinates > MAX_COORDINATES:
                    raise _fail('face.coordinates', coordinates, f'at most {MAX_COORDINATES}', 'face_blend.budget')
                frames.append(FaceFrame(start, end, layers))
        return tuple(frames)


def _validate_layers(layers: FaceLayers) -> int:
    if not isinstance(layers, FaceLayers):
        raise _fail('face.layers', None, 'typed FaceLayers')
    count = 0
    for rows in (layers.eyes, layers.mouth):
        if not isinstance(rows, tuple) or not 1 <= len(rows) <= 100:
            raise _fail('face.layers', None, '1..100 layers per facial region')
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 2:
                raise _fail('face.layer', None, 'a shape/color pair')
            shape, color = row
            if (
                not isinstance(shape, tuple)
                or not 8 <= len(shape) <= 20_000
                or (len(shape) - 2) % 6
                or any(not checks.number(v) or abs(v) > 100_000 for v in shape)
                or not isinstance(color, str)
                or not re.fullmatch(r'(?:ink|white|#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)', color)
            ):
                raise _fail('face.layer', None, 'bounded finite cubic geometry and a palette color')
            count += len(shape)
    return count


def segments(frames: tuple[FaceFrame, ...], start: float, end: float):
    """Partition a pose span without restarting any authored frame at a cut."""
    cursor = start
    for frame in frames:
        a, b = max(start, frame.start), min(end, frame.end)
        if a >= b:
            continue
        if cursor < a:
            yield cursor, a, None
        yield a, b, frame.layers
        cursor = b
    if cursor < end:
        yield cursor, end, None
