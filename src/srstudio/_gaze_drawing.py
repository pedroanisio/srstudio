"""Explicit pupil-layer contract and opt-in Toon target-gaze emission."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from . import checks
from .canvas import Canvas
from .gaze import GazePlan, _fail, eye_offset
from .head_motion import Channel, HeadPlan
from .toon import Pose, fh
from .toon_cast import LEAN_DEGREES, Layer, Look, Point, _draw, _place

if TYPE_CHECKING:
    from .toon_head import HeadRig

MAX_EMITTED_KEYS = 200000


@dataclass(frozen=True)
class EyeLayers:
    """Authored painter order, moving pupil/iris/glint indices, and their neutral offset.

    Radius and origin are reference-pixel radius and eye-radius offsets. Lids,
    brows and sclera stay static. The untilted drawing owns these declarations.
    """

    layers: tuple[Layer, ...]
    moving: tuple[int, ...]
    radius: float
    origin: Point = (0, 0)

    def __post_init__(self) -> None:
        if type(self.layers) is not tuple or not 1 <= len(self.layers) <= 1000:
            raise _fail('eye.layers', None, '1..1000 authored layers')
        if (
            type(self.moving) is not tuple
            or len(self.moving) > len(self.layers)
            or any(type(i) is not int or not 0 <= i < len(self.layers) for i in self.moving)
            or len(set(self.moving)) != len(self.moving)
        ):
            raise _fail('eye.moving', self.moving, 'distinct indices into the authored layers')
        if not checks.number(self.radius) or not 0 < self.radius <= 1000:
            raise _fail('eye.radius', self.radius, 'a positive bounded radius in reference pixels')
        if (
            type(self.origin) is not tuple
            or len(self.origin) != 2
            or any(not checks.number(v) or abs(v) > 2 for v in self.origin)
        ):
            raise _fail('eye.origin', self.origin, 'two finite offsets in -2..2 eye radii')


@runtime_checkable
class TrackingEyes(Protocol):
    """A drawing that explicitly separates moving pupils from their stationary lids."""

    def tracked_eye(self, look: Look, centre: Point, kind: str, inner: float) -> EyeLayers: ...


@dataclass(frozen=True)
class PreparedGaze:
    plan: GazePlan
    eyes: dict[str, tuple[EyeLayers, EyeLayers]]
    head: HeadPlan


def capabilities(rig: HeadRig) -> dict:
    supported = isinstance(rig.look.drawing, TrackingEyes) and rig.look.drawing.tilt == 0
    return {
        'continuous': supported,
        'eye_output': 'linear pupil transforms; stationary lids and painter order',
        'head_output': 'stylized face_x and nod, added to existing channels within the rig envelope',
        'eye_limits': {'x': [-0.42, 0.42], 'y': [-0.3, 0.3], 'unit': 'eye radii'},
        'clock': 'performance seconds',
        'named_mapping': 'explicit NamedGazeMapping required; no automatic fallback',
        'max_emitted_keys': MAX_EMITTED_KEYS,
    }


def prepare(rig: HeadRig, poses: Sequence[Pose], duration: float, head: HeadPlan, plan: GazePlan) -> PreparedGaze:
    if type(plan) is not GazePlan or duration != plan.spec.duration:
        raise _fail('target_gaze', None, 'a GazePlan covering the same complete performance duration')
    if not capabilities(rig)['continuous']:
        raise _fail('rig', rig.look.name, 'an untilted drawing declaring TrackingEyes', 'gaze.unsupported')
    if any(name != 'ahead' for _, name in head.gaze):
        raise _fail('head.gaze', head.gaze, 'one eye owner: target_gaze or named gaze, not both')
    if not isinstance(poses, (tuple, list)) or not 1 <= len(poses) <= 1000 or any(type(p) is not Pose for p in poses):
        raise _fail('poses', None, '1..1000 typed poses')
    # Every pose can expose several disjoint pupil runs; estimate actual authored
    # runs before writing any scene nodes. No per-frame eye geometry is generated.
    drawing = rig.look.drawing
    assert isinstance(drawing, TrackingEyes)
    eyes = {}
    for kind in dict.fromkeys(p.eyes for p in poses):
        eyes[kind] = tuple(
            drawing.tracked_eye(rig.look, centre, kind, side)
            for centre, side in zip(rig.look.eyes, (1.0, -1.0), strict=True)
        )
    rows = []
    times = sorted(
        {s.time for s in plan.samples}
        | {t for name in ('face_x', 'nod') for t, _ in getattr(head, name).keys if 0 <= t <= duration}
    )
    if len(times) > plan.spec.max_samples:
        raise _fail('head', len(times), 'head keys fitting the gaze sample budget', 'gaze.budget')
    for time in times:
        sample = plan.sample(time)
        rows.append(
            (
                time,
                head.face_x.sample(time) + sample.head_yaw / plan.spec.limits.head_yaw * rig.style.glance_face,
                head.nod.sample(time) + sample.head_pitch / plan.spec.limits.head_pitch * rig.style.nod_px,
            )
        )
    combined = replace(
        head,
        gaze=(),
        face_x=Channel(tuple((t, x) for t, x, _ in rows), curve='linear'),
        nod=Channel(tuple((t, y) for t, _, y in rows), curve='linear'),
    )
    combined.check_bounds(rig.style)
    runs = sum(sum(i == 0 or i - 1 not in eye.moving for i in eye.moving) for pose in poses for eye in eyes[pose.eyes])
    cost = runs * 2 * len(plan.samples) + 3 * len(times)
    if cost > MAX_EMITTED_KEYS:
        raise _fail('target_gaze.keys', cost, f'at most {MAX_EMITTED_KEYS} emitted keys', 'gaze.budget')
    return PreparedGaze(plan, eyes, combined)


def draw_eyes(cv: Canvas, parent, prepared: PreparedGaze, kind: str, arms: str) -> None:
    from .toon_head import _animate

    angle = math.radians(LEAN_DEGREES if arms == 'lean' else 0)
    cosine, sine = math.cos(angle), math.sin(angle)
    for eye in prepared.eyes[kind]:
        moving = set(eye.moving)
        i = 0
        while i < len(eye.layers):
            if i not in moving:
                _draw(cv, parent, _place([eye.layers[i]], arms))
                i += 1
                continue
            end = i + 1
            while end in moving:
                end += 1
            group = cv.group(parent, cv.uid('gaze-pupil'))
            _draw(cv, group, _place(list(eye.layers[i:end]), arms))
            xs, ys = [], []
            for sample in prepared.plan.samples:
                x, y = eye_offset(prepared.plan, sample)
                x, y = (x - eye.origin[0]) * eye.radius, (y - eye.origin[1]) * eye.radius
                xs.append((sample.time, fh(x * cosine - y * sine)))
                ys.append((sample.time, fh(x * sine + y * cosine)))
            _animate(cv, group, 'x', Channel(tuple(xs), curve='linear'))
            _animate(cv, group, 'y', Channel(tuple(ys), curve='linear'))
            i = end
