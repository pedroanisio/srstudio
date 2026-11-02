"""Bento's authored leg contours on a sampled, world-anchored biped plan.

Dimensions come from his drawing, not the default human profile. The support
test is the body's explicit static mass proxy, not a dynamics certificate.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from functools import cache

from examples.acting_continuity import carry_motion
from examples.drawing_attached import attached_mesh, attached_performance, attached_scene
from examples.drawing_figure import SCALE as WORLD_SCALE
from examples.drawing_figure import _transform, figure_source
from examples.drawing_hand import hand_recipe
from examples.drawing_proof import SIZE, sample, schedule
from examples.drawing_world import WorldStudy

from srstudio import body, clay, framegraph
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio import toon_bento as bento
from srstudio.acting import PerformancePlan
from srstudio.character_clips import ToonClip
from srstudio.limbs import Frame, Quaternion, Vec3
from srstudio.limbs.motion import Motion
from srstudio.toon import SCALE as NATIVE_SCALE
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT, SHOULDERS

METERS_PER_DRAWING_PIXEL = bento.SIZE * NATIVE_SCALE * WORLD_SCALE / 100
CAMERA_CUTS = (4,)  # drawing_proof.sample replaces the camera here; the trunk turns to face the new view.
CARRY_KEYS = (1.2, 2.0, 2.8, 3.6)


def check_cuts(motion: Motion) -> None:
    """Refuse a prop held by the frontal native shoulder through a camera cut.

    Non-spatial native ink must face the camera exactly, so the trunk, and the
    shoulder the spatial arm hangs from, turns with every new camera. An empty
    arm may follow it; a held prop would jump in world space.
    """
    for attachment in motion.attachments:
        for cut in CAMERA_CUTS:
            if attachment.attach <= cut <= attachment.release:
                raise ValueError(
                    f'{attachment.name} is attached to the frontal shoulder across the camera cut at {cut:g} seconds'
                )


@cache
def candidate_carry() -> Motion:
    """The shared grip path and pickup pose, retimed so the cup is set down before the cut."""
    source = carry_motion()
    contact, attachment = source.contacts[0], source.attachments[0]
    if len(contact.target.keys) != len(CARRY_KEYS) or any(
        key.velocity is not None or key.angular_velocity is not None for key in contact.target.keys
    ):
        raise ValueError('candidate carry retimes four positional grip keys')
    keys = tuple(replace(key, time=time) for key, time in zip(contact.target.keys, CARRY_KEYS, strict=True))
    release = CARRY_KEYS[-1]
    carry = replace(
        source,
        contacts=(replace(contact, end=release, target=replace(contact.target, keys=keys)),),
        attachments=(replace(attachment, release=release),),
    )
    check_cuts(carry)
    return carry


@cache
def body_profile() -> body.BodyProfile:
    """Measured authored spans; the candidate crouches without shortening bones."""
    unit = METERS_PER_DRAWING_PIXEL
    left, right = (bento._HIS_SHOULDERS[side] for side in SHOULDERS)
    return body.BodyProfile(
        hip_width=110 * unit,
        thigh=70 * unit,
        shin=65 * unit,
        ankle_height=46 * unit,
        foot_width=120 * unit,
        heel=0.08,
        toe=0.12,
        torso_height=(bento._at(308, 700)[1] - (left[1] + right[1]) / 2) * NATIVE_SCALE * WORLD_SCALE / 100,
        shoulder_width=(right[0] - left[0]) * NATIVE_SCALE * WORLD_SCALE / 100,
        max_stride=0.2,
    )


@cache
def body_plan() -> body.BodyPlan:
    """Shift left, move the right foot, shift right, then bring the left foot along."""
    profile = body_profile()
    half = profile.hip_width / 2
    roots = tuple(
        body.BodyKey(time, Frame(Vec3(x, -0.43, 0)))
        for time, x in ((0, 0), (0.5, 0), (0.8, -0.04), (1.35, -0.04), (1.9, 0.22), (2.45, 0.22), (3, 0.18))
    )
    stance = tuple(body.FootAnchor(side, Frame(Vec3(x, 0, 0))) for side, x in (('left', -half), ('right', half)))
    steps = (
        body.Step('right', 0.85, 1.35, Frame(Vec3(half + 0.18, 0, 0)), clearance=0.045),
        body.Step('left', 1.95, 2.45, Frame(Vec3(-half + 0.18, 0, 0)), clearance=0.045),
    )
    return body.compile_body(body.BodyScore(3, roots, stance, steps, profile))


def leg_point(leg: body.LegPose, x: float, px: float, py: float, *, foot: bool = False) -> Vec3:
    """Map an authored drawing point onto the solved leg, returning centimeters.

    The foot is rigid in its sole frame. Trouser vertices follow the hip/knee
    or knee/ankle segment and keep their transverse width. Joint locations use
    the same 700/770/835 drawing rows as the measured segment lengths.
    """
    unit = METERS_PER_DRAWING_PIXEL
    if foot:
        return leg.sole.point(Vec3((px - x - 40) * unit, (py - 881) * unit, 0)) * 100
    start, end, first, last = (leg.hip, leg.knee, 700, 770) if py <= 770 else (leg.knee, leg.ankle, 770, 835)
    center = start.lerp(end, (py - first) / (last - first))
    return (center + leg.sole.rotation.rotate(Vec3((px - x - 35) * unit, 0, 0))) * 100


@dataclass(frozen=True)
class LegContour:
    points: tuple[tuple[float, float], ...]
    color: str
    foot: bool


def _simplify(points: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
    """Retain the traced contour within 0.05 authored pixels; bounded input is local artwork."""
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        maximum, selected = 0.0, first
        for index in range(first + 1, last):
            px, py = points[index]
            u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length)) if length else 0.0
            distance = (px - ax - u * dx) ** 2 + (py - ay - u * dy) ** 2
            if distance > maximum:
                maximum, selected = distance, index
        if maximum > 0.05**2:
            keep.add(selected)
            pending.extend(((first, selected), (selected, last)))
    return tuple(points[index] for index in sorted(keep))


@cache
def leg_contours() -> tuple[LegContour, ...]:
    """His trouser, paw outline, toe marks and cuff; no new generic foot silhouette."""
    result = []
    for index, (shape, color) in enumerate(bento._leg(218)):
        path = 'M' + ' '.join(map(str, shape[:2])) + ' C' + ' '.join(map(str, shape[2:])) + ' Z'
        points = tuple(bento._off(point) for point in framegraph.flatten(path)[0])
        result.append(LegContour(_simplify(points), str(color), index != 0))
    return tuple(result)


@cache
def upper_performance() -> PerformancePlan:
    """Use the native upper body, face and head; the new leg layer owns both feet."""
    original = attached_performance()
    assert isinstance(original.clip, ToonClip)
    rig = replace(original.clip.rig, trunk=bento._blazer_layers)
    return replace(original, rig=replace(original.rig, head_rig=rig), clip=replace(original.clip, rig=rig))


def _body_events() -> tuple[float, ...]:
    plan = body_plan()
    return tuple(
        sorted(
            {key.time for key in plan.score.roots}
            | {time for step in plan.score.steps for time in (step.start, step.end)}
        )
    )


def _scene_events() -> tuple[float, ...]:
    """Body events in both painter windows, plus the absolute carry events."""
    carry = {time for attachment in candidate_carry().attachments for time in (attachment.attach, attachment.release)}
    return tuple(sorted({time + offset for time in _body_events() for offset in (0, 3) if time + offset < 6} | carry))


def leg_source(*, fps: int = 12) -> tuple[c.AssetBinding, c.VectorSource]:
    """Emit centimeter spatial paths on the original six-second scene clock."""
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError('body fps must be an integer in 1..120')
    plan = body_plan()
    times = sorted(
        {i / fps for i in range(6 * fps + 1)} | {time + offset for time in _body_events() for offset in (0, 3)}
    )
    poses = tuple(plan.sample(time if time < 3 else time - 3) for time in times)
    fields = []
    contour = leg_contours()[0]
    for side, x in enumerate((218, 328)):
        keys: list[c.PathKey] = []
        for time, pose in zip(times, poses, strict=True):
            points = []
            for px, py in contour.points:
                p = leg_point(pose.legs[side], x, px + x - 218, py)
                points.append((p.x, p.y, p.z))
            vertices = tuple(points)
            if not keys or keys[-1].points != vertices:
                keys.append(c.PathKey(time, vertices))
        fields.append(c.FormSurface(f'trouser-{side}', mode='ink', path=c.FormPath(keys[0].points, tuple(keys))))
    return _source('legs', tuple(fields), (contour.color, contour.color), 6)


def foot_source() -> tuple[c.AssetBinding, c.VectorSource]:
    """One rigid drawing instance per foot; the containing scene owns its sole transform."""
    fields, colors = [], []
    unit = METERS_PER_DRAWING_PIXEL * 100
    for index, contour in enumerate(leg_contours()[1:]):
        points = tuple(((px - 258) * unit, (py - 881) * unit, 0.0) for px, py in contour.points)
        fields.append(c.FormSurface(f'foot-{index}', mode='ink', path=c.FormPath(points)))
        colors.append(contour.color)
    return _source('feet', tuple(fields), tuple(colors), None)


def _source(
    name: str, forms: tuple[c.FormSurface, ...], colors: tuple[str, ...], duration: float | None
) -> tuple[c.AssetBinding, c.VectorSource]:
    root = ET.Element('scene', version='1.1')
    ET.SubElement(root, 'project', width=str(SIZE[0]), height=str(SIZE[1]), fps='24', duration='6')
    comp = ET.SubElement(root, 'composition')
    vertices: list[tuple[float, float, float]] = []
    for surface, color in zip(forms, colors, strict=True):
        assert surface.path is not None
        for points in (surface.path.points, *(key.points for key in surface.path.keys)):
            vertices.extend(points)
        ET.SubElement(
            comp,
            'shape',
            id=surface.node,
            shape='path',
            path='M 0 0 L 1 0 L 1 1 Z',
            width=str(SIZE[0]),
            height=str(SIZE[1]),
            fill=color,
            stroke='#00000000',
            strokeWidth='0',
        )
    source = c.VectorSource(name, ET.tostring(root))
    xs, ys, zs = zip(*vertices, strict=True)
    binding = c.AssetBinding(
        name,
        'candidate.bento-supported-' + name,
        1,
        'vector',
        c.Bounds((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))),
        nodes=sum(1 for _ in root.iter()),
        memory_bytes=64 * 1024**2,
        duration=duration,
        forms=forms,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
    )
    return binding, source


def body_offset(time: float) -> Vec3:
    """World placement in centimeters; the depth replacement at three seconds is a cut."""
    if type(time) not in (int, float) or not 0 <= time <= 6:
        raise ValueError('body scene time must lie in 0..6 seconds')
    return Vec3(-210, 0, -115) if time < 3 else Vec3(-110, 0, 115)


def body_transform(time: float) -> c.Transform:
    """Anchor the native pelvis center to the solved root while retaining the frontal view."""
    offset = body_offset(time)
    pose = body_plan().sample(time if time < 3 else time - 3)
    transform = _transform(sample(time))
    pitch, yaw, _ = transform.rotation
    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(yaw)) * Quaternion.axis_angle(
        Vec3(1, 0, 0), math.radians(pitch)
    )
    performance = upper_performance()
    head = performance.sample(max(0.5, time)).head
    assert head is not None and performance.rig.head_rig is not None
    hip = bento._at(308, 700)
    pivot = Vec3(fx(PIVOT[0]), fy(PIVOT[1]), 0)
    delta = Vec3(fx(hip[0]), fy(hip[1]), 0) - pivot
    breath = 1 + head.breath * performance.rig.head_rig.style.breath_scale
    lean = Quaternion.axis_angle(Vec3(0, 0, 1), math.radians(head.lean))
    native = pivot + lean.rotate(Vec3(delta.x, delta.y * breath, delta.z))
    origin = pose.root.origin * 100 + offset - rotation.rotate(native * WORLD_SCALE)
    return replace(transform, translation=(origin.x, origin.y, origin.z))


def candidate_mesh(time: float) -> tuple[clay.Mesh, ...]:
    """The spatial arm and cup on the supported root, driven by the retimed carry."""
    return attached_mesh(time, placement=body_transform, motion=candidate_carry())


def foot_transform(leg: body.LegPose, time: float) -> c.Transform:
    """Place one rigid foot drawing at its solved sole, toes along the sole's forward axis.

    The paw is drawn from the front, so its card normal (+z) is the toe
    direction; the sole's yaw turns that normal. A tilted sole has no frontal
    paw drawing and is refused instead of flattened.
    """
    rotation = leg.sole.rotation
    if abs(rotation.x) > 1e-12 or abs(rotation.z) > 1e-12:
        raise ValueError(f'{leg.side} foot drawing needs a level sole; only yaw is drawable')
    point = leg.sole.origin * 100 + body_offset(time)
    yaw = math.degrees(2 * math.atan2(rotation.y, rotation.w))
    return c.Transform((point.x, point.y, point.z), (0.0, yaw + 0.0, 0.0))


def body_scene(*, fps: int = 12, size: tuple[int, int] = SIZE) -> WorldStudy:
    """Place Bento's upper body, authored leg paths and attached arm in the shared world."""
    plan = body_plan()
    check_cuts(candidate_carry())
    events = _scene_events()
    original = attached_scene(fps=fps, size=size, events=events)
    timeline = original.timeline
    leg_binding, legs = leg_source(fps=fps)
    foot_binding, feet = foot_source()
    figure, native = figure_source(performance=upper_performance(), candidate='candidate.hybrid-supported-figure')
    snapshots: list[c.RasterFrame] = []
    vertices: list[tuple[float, float, float]] = []
    for frame in schedule(fps=fps, size=size, events=events):
        meshes = candidate_mesh(frame.time)
        vertices.extend((float(x), float(y), float(-z)) for mesh in meshes for x, y, z in mesh.vertices)
        source = c.proxy_source('hand', meshes, hand_recipe(), basis='clay', lighting='scene', meters_per_unit=0.01)
        if not snapshots or source != snapshots[-1].source:
            snapshots.append(c.RasterFrame(frame.time, source))
    hand = c.RasterSequence('hand', 6, tuple(snapshots))
    xs, ys, zs = zip(*vertices, strict=True)
    hand_binding = replace(
        next(binding for binding in timeline.base.bindings if binding.id == 'hand'),
        part='candidate.hybrid-supported-hand-cup',
        bounds=c.Bounds((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))),
        plates=c.raster_jobs(hand, width=size[0], height=size[1], memory_bytes=64 * 1024**2 + size[0] * size[1] * 64),
        candidate=c.CandidateSource('toon', c.raster_sequence_digest(hand)),
    )
    times = sorted(
        {frame.time for frame in schedule(fps=fps, size=size, events=events)} | {frame.time for frame in hand.frames}
    )
    body_keys_list: list[m.TransformKey] = []
    for time in times:
        transform = body_transform(time)
        if not body_keys_list or body_keys_list[-1].value != transform:
            body_keys_list.append(m.TransformKey(time, transform, 'hold'))
    body_keys = tuple(body_keys_list)
    tracks = [
        replace(track, keys=body_keys) if track.layer in ('figure-back', 'figure-front') else track
        for track in timeline.motion.transforms
    ]
    layers = []
    for layer in timeline.base.spec.layers:
        if layer.id in ('figure-back', 'figure-front'):
            layer = replace(layer, transform=body_keys[0].value)
            suffix = layer.id.removeprefix('figure-')
            start = 0 if suffix == 'back' else 3
            offset = body_offset(start)
            clock = c.TemporalPolicy(
                start, start + 3, start, continuity='cut' if start else 'held', state='supported-legs'
            )
            layers.append(
                c.LayerSpec('legs-' + suffix, 'legs', 1, clock, transform=c.Transform((offset.x, 0, offset.z)))
            )
            for side in ('left', 'right'):
                name = f'{side}-foot-{suffix}'
                keys: list[m.TransformKey] = []
                for time in times:
                    pose = plan.sample(time if time < 3 else time - 3)
                    foot = next(leg for leg in pose.legs if leg.side == side)
                    transform = foot_transform(foot, time)
                    # A planted sole has one held transform, not one identical
                    # manifest record for every frame of the camera and body.
                    if not keys or keys[-1].value != transform:
                        keys.append(m.TransformKey(time, transform, 'hold'))
                layers.append(
                    c.LayerSpec(
                        name, 'feet', 1, replace(clock, state=f'supported-{side}-foot'), transform=keys[0].value
                    )
                )
                tracks.append(m.TransformTrack(name, tuple(keys)))
        layers.append(layer)
    bindings = tuple(
        figure if binding.id == 'figure' else hand_binding if binding.id == 'hand' else binding
        for binding in timeline.base.bindings
    )
    return WorldStudy(
        m.plan_scene(
            replace(timeline.base.spec, layers=tuple(layers)),
            (*bindings, leg_binding, foot_binding),
            replace(timeline.motion, transforms=tuple(tracks)),
            rasters=tuple(hand if source.id == 'hand' else source for source in timeline.rasters),
            purpose=timeline.base.purpose,
        ),
        (*[native if source.id == 'figure' else source for source in original.vectors], legs, feet),
    )
