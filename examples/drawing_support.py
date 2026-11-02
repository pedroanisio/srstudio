"""World-anchored per-foot support for the candidate's native Bento figure.

Each painter window owns one quasi-static ``srstudio.body`` plan: weight shifts
over the stance sole, the other foot steps along the body's lateral axis, and
every planted sole stays fixed in world space. The declared depth replacement
at three seconds starts a new plan, as the cut already does for the root.

The native drawing is a frontal card standing in world space: upright, at the
body's pelvis ground point, facing the body's authored yaw. Its orientation is
actor state, constant through each window and through the camera cut at four
seconds, so drawn points (shoulder, soles) keep their world positions when only
the camera changes. Cameras must stay inside the declared frontal envelope.
Bento's own leg drawings are deformed per output frame: the trouser top follows
the native lean/breath of the torso and the foot sits on the world sole, which
lies in the card plane. Units: body meters, world centimeters, native source
pixels and Bento drawing units.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from bisect import bisect_right
from collections.abc import Callable
from functools import cache

from examples.acting_continuity import carry_motion
from examples.drawing_figure import SCALE
from examples.drawing_proof import DURATION, SIZE, Sample, figure_performance, sample, schedule
from sr_core.scene import Scene

from srstudio.acting import PerformancePlan

from srstudio import Canvas, body, toon
from srstudio import composition as c
from srstudio import toon_bento as bento
from srstudio.limbs import Quaternion, Vec3
from srstudio.limbs.math3d import Frame
from srstudio.toon_cast import PIVOT, _draw

DRAWING_METERS = bento.SIZE * toon.SCALE * SCALE / 100  # Meters per Bento drawing unit.
LEG_X = {'left': 218.0, 'right': 328.0}  # toon_bento._leg origins, by screen side.
_CENTER, _HIP, _FOOT, _SOLE = 34.5, 700.0, 814.0, 881.0  # Leg column, trouser top, foot top, sole.
PELVIS = (sum(LEG_X.values()) / 2 + _CENTER, _SOLE)  # Drawing point under the pelvis, on the ground.
PELVIS_HEIGHT = (_SOLE - _HIP) * DRAWING_METERS
SEAT = bento._off(PIVOT)  # The lean/breath pivot in drawing units.
PROFILE = body.BodyProfile(
    hip_width=(LEG_X['right'] - LEG_X['left']) * DRAWING_METERS,
    thigh=0.25,
    shin=0.25,
    ankle_height=0.10,
    foot_width=120 * DRAWING_METERS,  # The drawn foot spans x-19..x+101.
    heel=0.08,
    toe=0.14,
    support_margin=0.01,
)
EVENTS = (carry_motion().attachments[0].attach, carry_motion().attachments[0].release)
# Window start, root x/z (meters), lateral travel, opening hold, card yaw (degrees). Each yaw minimizes the
# window's largest camera angle from the card normal (14.9 and 29.85 degrees), within VIEW_ENVELOPE.
_WINDOWS = {'back': (0.0, -2.10, -1.15, -0.20, 0.5, 28.9), 'front': (3.0, -1.10, 1.15, 0.20, 0.0, 7.2)}
VIEW_ENVELOPE = 30.0  # Degrees between the card normal and the direction to the camera.
_LEAN, _SHIFT_IN, _STEP, _SHIFT, _SETTLE = 0.55, 0.3, 0.5, 0.7, 0.4
_FPS = 24

Point = tuple[float, float]
Place = Callable[[float, float], Point]


def _time(time: float) -> float:
    if type(time) not in (int, float) or not 0 <= time <= DURATION:
        raise ValueError('support time must lie in 0..6 seconds')
    return float(time)


def _side(side: str) -> str:
    if side not in LEG_X:
        raise ValueError('support side must be left or right')
    return side


def _window(time: float) -> str:
    return 'back' if _time(time) < 3 else 'front'


def card_rotation(window: str) -> Quaternion:
    """The body's and card's authored world yaw for one painter window."""
    if window not in _WINDOWS:
        raise ValueError('support window must be back or front')
    return Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(_WINDOWS[window][5]))


def _score(window: str) -> body.BodyScore:
    """Two flat-foot sidesteps: shift over the stance sole, step, shift, step, settle."""
    _start, x, z, travel, hold, _yaw = _WINDOWS[window]
    rotation = card_rotation(window)
    half = PROFILE.hip_width / 2
    lead, trail = ('left', 'right') if travel < 0 else ('right', 'left')
    feet = {'left': -half, 'right': half}  # Lateral offsets along the body's x axis.
    origin = Vec3(x, 0, z)

    def at(lateral: float, height: float = 0) -> Frame:
        return Frame(origin + rotation.rotate(Vec3(lateral, 0, 0)) + Vec3(0, height, 0), rotation)

    def key(time: float, lateral: float) -> body.BodyKey:
        return body.BodyKey(round(time, 6), at(lateral, -PELVIS_HEIGHT))

    roots = [key(0, 0)] + ([key(hold, 0)] if hold else [])
    steps = []
    time = hold + _SHIFT_IN
    for side in (lead, trail):
        stance = trail if side == lead else lead
        middle = (feet['left'] + feet['right']) / 2
        over = middle + _LEAN * (feet[stance] - middle)
        roots += [key(time, over), key(time + _STEP, over)]
        feet[side] += travel
        steps.append(body.Step(side, round(time, 6), round(time + _STEP, 6), at(feet[side]), 0.05))
        time += _STEP + _SHIFT
    roots.append(key(time - _SHIFT + _SETTLE, (feet['left'] + feet['right']) / 2))
    stance = tuple(body.FootAnchor(s, at(half if s == 'right' else -half)) for s in LEG_X)
    return body.BodyScore(3.0, tuple(roots), stance, tuple(steps), PROFILE)


@cache
def body_plan(window: str) -> body.BodyPlan:
    """The validated support plan of one painter window, on window-local seconds."""
    card_rotation(window)
    return body.compile_body(_score(window))


def body_pose(time: float) -> body.BodyPose:
    """Sampled body on the performance clock; the depth replacement at three seconds starts the front plan."""
    window = _window(time)
    return body_plan(window).sample(time - _WINDOWS[window][0])


@cache
def _schedule(fps: int, events: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(frame.time for frame in schedule(fps=fps, events=events))


def held(time: float, *, fps: int = 12, events: tuple[float, ...] = EVENTS) -> float:
    """The shared world sample (root and soles) held at an output time."""
    times = _schedule(fps, events)
    return times[bisect_right(times, _time(time)) - 1]


def native(point: Point) -> Point:
    """Bento drawing units to unrounded native source pixels."""
    x, y = bento._at(*point)
    return x * toon.SCALE, (y - toon.REF_TOP) * toon.SCALE


def _drawing(point: Point) -> Point:
    return bento._off((point[0] / toon.SCALE, point[1] / toon.SCALE + toon.REF_TOP))


def _rotation(transform: c.Transform) -> Quaternion:
    rotation = Quaternion()
    for axis, angle in zip((Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)), transform.rotation, strict=True):
        rotation = Quaternion.axis_angle(axis, math.radians(angle)) * rotation
    return rotation


def to_world(transform: c.Transform, point: Point) -> Vec3:
    """A native card point in canonical world centimeters."""
    return Vec3(*transform.translation) + _rotation(transform).rotate(Vec3(point[0], point[1], 0) * transform.scale)


def card_transform(time: float) -> c.Transform:
    """Upright card with the drawn pelvis ground point on the body's pelvis ground point."""
    window = _window(time)
    rotation = card_rotation(window)
    root = body_pose(time).root.origin
    origin = Vec3(root.x * 100, 0, root.z * 100) - rotation.rotate(Vec3(*native(PELVIS), 0) * SCALE)
    return c.Transform((origin.x, origin.y, origin.z), (0, _WINDOWS[window][5], 0), SCALE)


def camera_center(frame: Sample) -> Vec3:
    p = frame.view.position
    return Vec3(p[0], p[1], -p[2])


def view_angle(frame: Sample) -> float:
    """Degrees between the card normal and the direction from the body root to the camera."""
    root = body_pose(frame.time).root.origin
    ground = Vec3(root.x * 100, 0, root.z * 100)
    normal = card_rotation(_window(frame.time)).rotate(Vec3(0, 0, 1))
    return math.degrees(math.acos(max(-1.0, min(1.0, normal.dot((camera_center(frame) - ground).unit())))))


def support_transform(frame: Sample) -> c.Transform:
    """Card placement for a shared world sample; refuses cameras outside the frontal envelope."""
    angle = view_angle(frame)
    if angle > VIEW_ENVELOPE:
        raise ValueError(f'support camera views the frontal card at {angle:.3f} degrees, beyond {VIEW_ENVELOPE}')
    return card_transform(frame.time)


def register(time: float, world: Vec3) -> Point:
    """Native card point of a world point in the card plane; refuses points off that plane."""
    transform = card_transform(time)
    local = _rotation(transform).inverse().rotate(world - Vec3(*transform.translation)) * (1 / transform.scale)
    if abs(local.z) > 1e-6:
        raise ValueError(f'support point lies {local.z * transform.scale:.6g} cm off the figure card')
    return local.x, local.y


def drawn_sole(time: float, side: str, *, fps: int = 12, events: tuple[float, ...] = EVENTS) -> Point:
    """Drawing-unit sole point of the world sole at the held sample."""
    side = _side(side)
    moment = held(time, fps=fps, events=events)
    leg = next(leg for leg in body_pose(moment).legs if leg.side == side)
    return _drawing(register(moment, leg.sole.origin * 100))


def deformation(lean: float, stretch: float, delta: Point) -> Place:
    """Trouser top rides the torso's lean/breath about the seat; the foot moves rigidly by delta."""
    cosine, sine = math.cos(math.radians(lean)), math.sin(math.radians(lean))

    def place(x: float, y: float) -> Point:
        dx, dy = x - SEAT[0], (y - SEAT[1]) * stretch
        torso = (SEAT[0] + dx * cosine - dy * sine, SEAT[1] + dx * sine + dy * cosine)
        weight = min(1.0, max(0.0, (y - _HIP) / (_FOOT - _HIP)))
        return (
            (1 - weight) * torso[0] + weight * (x + delta[0]),
            (1 - weight) * torso[1] + weight * (y + delta[1]),
        )

    return place


@cache
def _performance() -> PerformancePlan:
    return figure_performance()  # The attached clip shares this head clock exactly.


def leg_place(time: float, side: str, *, fps: int = 12, events: tuple[float, ...] = EVENTS) -> Place:
    performance = _performance()
    head = performance.sample(_time(time)).head
    assert head is not None and performance.rig.head_rig is not None
    sole = drawn_sole(time, side, fps=fps, events=events)
    delta = (sole[0] - LEG_X[side] - _CENTER, sole[1] - _SOLE)
    return deformation(head.lean, 1 + head.breath * performance.rig.head_rig.style.breath_scale, delta)


def leg_layers(time: float, *, fps: int = 12, events: tuple[float, ...] = EVENTS) -> dict[str, tuple]:
    return {
        side: tuple(bento._leg(x, leg_place(time, side, fps=fps, events=events))) for side, x in LEG_X.items()
    }


def foot_offset(time: float, side: str, *, fps: int = 12, events: tuple[float, ...] = EVENTS) -> Point:
    """Native-pixel translation of the rigid foot region from its drawn rest pose."""
    sole = drawn_sole(time, side, fps=fps, events=events)
    unit = bento.SIZE * toon.SCALE
    return (sole[0] - LEG_X[side] - _CENTER) * unit, (sole[1] - _SOLE) * unit


def legs_source(*, fps: int = 12, events: tuple[float, ...] = EVENTS) -> tuple[c.AssetBinding, c.VectorSource]:
    """Bento's legs on the source clock: per-frame trousers and rigidly translated feet.

    The foot region of the deformation is a pure translation, so the unchanged
    foot drawing moves with hold keys; only the trouser shape is redrawn when
    the torso's lean/breath or the sole changes. Equal neighbours share one run.
    """
    times = sorted(set(_schedule(fps, events)) | {i / _FPS for i in range(DURATION * _FPS)})
    scene = Scene(version='auto')
    scene.add_project(width=SIZE[0], height=SIZE[1], fps='24', duration=DURATION)
    canvas = Canvas(scene, font_asset=None)
    group = canvas.group(canvas.comp, 'legs', start=0, end=DURATION)
    for side, x in LEG_X.items():
        trousers: list[list] = []
        offsets: list[tuple[float, Point]] = []
        for time in times:
            trouser = bento._leg(x, leg_place(time, side, fps=fps, events=events))[0]
            if not trousers or trousers[-1][1] != trouser:
                trousers.append([time, trouser])
            offset = foot_offset(time, side, fps=fps, events=events)
            if not offsets or offsets[-1][1] != offset:
                offsets.append((time, offset))
        leg = canvas.group(group, f'legs-{side}')
        for (start, trouser), end in zip(trousers, [run[0] for run in trousers[1:]] + [DURATION], strict=True):
            frame = canvas.group(leg, canvas.uid(f'legs-{side}-trouser'), start=round(start, 6), end=round(end, 6))
            _draw(canvas, frame, (trouser,))
        foot = canvas.group(leg, f'legs-{side}-foot')
        for axis, index in (('x', 0), ('y', 1)):
            canvas.keys(foot, axis, [(round(time, 6), round(value[index], 6)) for time, value in offsets], local=False)
        _draw(canvas, foot, bento._leg(x)[1:])
    source = c.VectorSource('legs', scene.to_bytes())
    forms = (c.FormSurface('legs', mode='ink'),)
    binding = c.AssetBinding(
        'legs',
        'candidate.hybrid-supported-legs',
        1,
        'vector',
        c.Bounds((-10000, -10000, 0), (10000, 10000, 0)),
        anchors=(c.Anchor('pelvis', (*native(PELVIS), 0.0)),),
        nodes=sum(1 for _ in ET.fromstring(source.xml).iter()),
        memory_bytes=64 * 1024**2,
        duration=DURATION,
        forms=forms,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
    )
    return binding, source
