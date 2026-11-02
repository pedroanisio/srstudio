"""Bounded source-clock body drawing; all projection precedes scene mutation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_core.scene import Composition, Group

from ._body_solve import footprint
from ._body_types import BodyPose, BodyProfile, fail, scalar
from ._transaction import scene_transaction
from .canvas import Canvas
from .limbs.errors import LimbError
from .limbs.math3d import Vec3
from .limbs.projection import Camera

if TYPE_CHECKING:
    from .body import BodyWindow

MAX_FRAMES = 1000
MAX_NODES = 100_000
INK = '#24304A'


@dataclass(frozen=True)
class Primitive:
    depth: float
    kind: str
    points: tuple[tuple[float, float], ...]
    color: str
    size: float


def geometry(pose: BodyPose, profile: BodyProfile, camera: Camera, style: str) -> tuple[Primitive, ...]:
    result = []

    def add(kind, points, color, width=0.006):
        projected = tuple(camera.project(p) for p in points)
        size = sum(p.scale for p in projected) / len(projected) * width
        if size > 1e6 or any(abs(v) > 1e6 for p in projected for v in p.xy):
            raise fail('projection', None, 'geometry within +/-1,000,000 parent pixels', 'body.budget')
        result.append(
            Primitive(
                sum(p.depth for p in projected) / len(projected), kind, tuple(p.xy for p in projected), color, size
            )
        )

    wire = style == 'wire'
    for leg in pose.legs:
        add('line', (leg.hip, leg.knee), '#667ADB', 0.009 if wire else 0.065)
        add('line', (leg.knee, leg.ankle), '#43569B', 0.009 if wire else 0.055)
        corners = footprint(leg.sole, profile)
        top = tuple(p - Vec3(0, profile.ankle_height * 0.75, 0) for p in corners)
        if wire:
            add('polygon', corners, '#81BFA6' if leg.planted else '#E5B663')
            for p in (leg.hip, leg.knee, leg.ankle):
                add('circle', (p,), '#EEF0FA', 0.017)
        else:
            add('polygon', top, '#3C4661')
            for i in range(4):
                j = (i + 1) % 4
                add('polygon', (corners[i], corners[j], top[j], top[i]), '#303B55')
        add('line', (leg.ankle, leg.sole.origin), '#455273', 0.009 if wire else 0.04)
    left, right = pose.legs
    shoulders = tuple(s.origin for s in pose.shoulders)
    if wire:
        add('line', (left.hip, right.hip), INK, 0.012)
        add('line', shoulders, INK, 0.012)
        add('line', (pose.root.origin, pose.torso.point(Vec3(0, -profile.torso_height, 0))), INK, 0.015)
    else:
        add('polygon', (left.hip, right.hip, shoulders[1], shoulders[0]), '#4D9A92')
    for side, shoulder in enumerate(pose.shoulders):
        sign = -1 if side == 0 else 1
        elbow = shoulder.point(Vec3(sign * 0.09, profile.torso_height * 0.48, 0.03))
        hand = shoulder.point(Vec3(sign * 0.07, profile.torso_height * 0.92, 0.04))
        add('line', (shoulder.origin, elbow), '#4D9A92', 0.009 if wire else 0.05)
        add('line', (elbow, hand), '#E3AF7B', 0.009 if wire else 0.04)
        add('circle', (hand,), '#E3AF7B', 0.025)
    neck = pose.torso.point(Vec3(0, -profile.torso_height - 0.06, 0))
    head = pose.torso.point(Vec3(0, -profile.torso_height - 0.2, 0))
    add('line', (pose.torso.point(Vec3(0, -profile.torso_height, 0)), neck), '#E3AF7B', 0.012 if wire else 0.06)
    add('circle', (head,), '#F1C99C', 0.14)
    for x in (-0.045, 0.045):
        eye = pose.torso.point(Vec3(x, -profile.torso_height - 0.22, 0.13))
        add('circle', (eye,), INK, 0.012)
    add('line', tuple(pose.torso.point(Vec3(x, -profile.torso_height - 0.14, 0.13)) for x in (-0.03, 0.03)), INK, 0.008)
    if wire:
        add('polygon', tuple(Vec3(x, 0, z) for x, z in pose.support_polygon), '#C4DFCF')
        plumb = Vec3(pose.center_of_mass.x, 0, pose.center_of_mass.z)
        add('line', (pose.center_of_mass, plumb), '#B36B34', 0.004)
        add('circle', (pose.center_of_mass,), '#DA8541', 0.025)
        add('circle', (plumb,), '#247B58', 0.018)
    return tuple(sorted(result, key=lambda p: p.depth))


def emit(cv: Canvas, parent, primitives: tuple[Primitive, ...]) -> None:
    for p in primitives:
        if p.kind == 'line':
            a, b = p.points
            cv.line(parent, *a, *b, INK, p.size + 3, strokeCap='round')
            cv.line(parent, *a, *b, p.color, p.size, strokeCap='round')
        elif p.kind == 'circle':
            x, y = p.points[0]
            cv.ellipse(parent, x - p.size, y - p.size, p.size * 2, p.size * 2, p.color, INK, 2)
        else:
            d = 'M' + ' L'.join(f'{x:.6f} {y:.6f}' for x, y in p.points) + ' Z'
            cv.path(parent, d, p.color, INK, 2)


def place(window: BodyWindow, cv: Canvas, parent, *, camera: Camera, at: float, fps: int, style: str, id: str | None):
    from .body import compile_body

    if not isinstance(cv, Canvas) or cv._frozen:
        raise fail('canvas', None, 'a running Canvas')
    if not isinstance(parent, (Composition, Group)) or not any(parent is n for n in cv.scene.iter()):
        raise fail('parent', None, 'a composition or group belonging to this canvas')
    scalar(at, 'at', 0, 600)
    if type(camera) is not Camera or style not in ('solid', 'wire'):
        raise fail('camera/style', None, 'a typed static Camera and solid or wire body drawing')
    if type(fps) is not int or not 1 <= fps <= 120:
        raise fail('fps', fps, 'an integer in 1..120')
    if id is not None and (
        not isinstance(id, str)
        or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', id)
        or any(n.attributes().get('id') == id for n in cv.scene.iter())
    ):
        raise fail('id', id, 'a unique XML identifier')
    plan = compile_body(window.plan.score)
    plan.window(window.start, window.end)
    if at + window.end - window.start > 600:
        raise fail('interval', None, 'a placed interval ending by 600 seconds')
    times = {0.0, plan.duration, *(round(i / fps, 6) for i in range(math.ceil(plan.duration * fps)))}
    times.update(t for step in plan.score.steps for t in (step.start, step.end))
    if len(times) - 1 > MAX_FRAMES:
        raise fail('frames', len(times) - 1, f'at most {MAX_FRAMES} body frames', 'body.budget')
    ordered = sorted(times)
    frames, count = [], 0
    try:
        for a, b in zip(ordered, ordered[1:], strict=False):
            primitives = geometry(plan.sample(a), plan.profile, camera, style)
            count += 1 + sum(2 if p.kind == 'line' else 1 for p in primitives)
            if count > MAX_NODES:
                raise fail('nodes', count, f'at most {MAX_NODES} emitted nodes', 'body.budget')
            frames.append((a, b, primitives))
    except LimbError as exc:
        raise fail('camera', str(exc), 'all body geometry in front of the near plane', 'body.projection') from exc
    with scene_transaction(cv.scene, cv):
        group = cv.group(
            parent, id or cv.uid('body'), start=at, end=at + window.end - window.start, timeOffset=at - window.start
        )
        for a, b, primitives in frames:
            emit(cv, cv.group(group, cv.uid('body-frame'), start=a, end=b), primitives)
        return group
