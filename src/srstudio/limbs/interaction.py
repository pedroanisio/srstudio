"""Depth-composited spatial hand/prop interactions with bounded, history-independent baking."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Any, Protocol

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .compile import BakeOptions, _frame_count, _resolve_options, _scene_time
from .correctives import ContourCorrection
from .errors import LimbError
from .geometry import ProjectedPose, path, project_pose
from .math3d import Frame, Vec3
from .motion import Motion, TransformTrack, sample_motion
from .projection import Affine, Camera, CameraTrack
from .validation import MotionReport, audit

_CAMERA = Camera()
_OPTIONS = BakeOptions()
_PARENT = Affine()


def _name(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value):
        raise LimbError(f"interaction ID {value!r} must be an XML name")


class FrameSource(Protocol):
    def sample(self, time: float) -> Frame: ...


@dataclass(frozen=True)
class AttachedProp:
    motion: Motion
    name: str

    def __post_init__(self) -> None:
        if self.name not in {a.name for a in self.motion.attachments}:
            raise LimbError(f"prop {self.name!r} has no attachment")

    def sample(self, time: float) -> Frame:
        return self.motion.prop_frame(self.name, time)


@dataclass(frozen=True)
class Face:
    name: str
    vertices: tuple[Vec3, ...]
    fill: str
    outline: str = "#23202b"

    def __post_init__(self) -> None:
        _name(self.name)
        if not 3 <= len(self.vertices) <= 1024:
            raise LimbError("prop faces need 3..1024 vertices")
        for color in (self.fill, self.outline):
            if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", color):
                raise LimbError("prop colors must be hexadecimal RGB or RGBA")
        origin = self.vertices[0]
        if not any(
            (a - origin).cross(b - origin).length > 1e-10
            for a, b in zip(self.vertices[1:], self.vertices[2:], strict=False)
        ):
            raise LimbError("prop face must have non-collinear vertices")


@dataclass(frozen=True)
class PropMesh:
    name: str
    faces: tuple[Face, ...]

    def __post_init__(self) -> None:
        _name(self.name)
        names = [f.name for f in self.faces]
        if not 1 <= len(names) <= 1024 or len(names) != len(set(names)):
            raise LimbError("prop mesh needs 1..1024 uniquely named faces")


@dataclass(frozen=True)
class PropDrawing:
    mesh: PropMesh
    track: FrameSource


@dataclass(frozen=True)
class Participant:
    name: str
    motion: Motion
    style: str = "toon"
    appearance: Appearance = Appearance()
    correctives: tuple[ContourCorrection, ...] = ()

    def __post_init__(self) -> None:
        _name(self.name)
        adapter_for(self.style)


@dataclass(frozen=True)
class InteractionResult:
    root: Any
    frames: int
    reports: tuple[tuple[str, MotionReport], ...]
    nodes: int
    depth_orders: tuple[tuple[tuple[str, float], ...], ...]


@dataclass(frozen=True)
class _Surface:
    name: str
    depth: float
    participant: Participant | None = None
    pose: ProjectedPose | None = None
    face: Face | None = None
    polygon: tuple[tuple[float, float], ...] = ()


def bake_interaction(
    cv: Canvas,
    parent: Any,
    participants: tuple[Participant, ...],
    props: tuple[PropDrawing, ...],
    *,
    id: str,
    camera: Camera | CameraTrack = _CAMERA,
    options: BakeOptions = _OPTIONS,
    parent_transform: Affine = _PARENT,
) -> InteractionResult:
    """Sort prop faces and individual limb surfaces together, far to near, on every held frame.

    Meshes and hands must use the same canonical coordinate system. Attachment tracks can be sampled in any
    order. Sorting uses average surface depth (the painter algorithm); intersecting surfaces must be split into
    separate faces by the author. The default duration covers known actions, roots, prop tracks and releases;
    custom frame sources require an explicit duration. An implicitly timed attached prop holds its released
    composited pose through the scene's end; without a scene duration it needs an explicit one. There is no hidden
    physical simulation.

    CameraTrack samples use scene seconds (including options.offset). Its cuts
    join the bake grid without resetting motion time. During an implicitly
    extended released-prop hold, source poses freeze while the camera continues.
    """
    options = _resolve_options(cv, options)
    assert options.fps is not None
    _name(id)
    names = [p.name for p in participants] + [p.mesh.name for p in props]
    if not names or len(names) > 128 or len(names) != len(set(names)):
        raise LimbError("interaction needs 1..128 uniquely named participants and props")
    if any(
        str(n.attributes().get("id", "")) == id or str(n.attributes().get("id", "")).startswith(id + "-")
        for n in cv.scene.iter()
    ):
        raise LimbError(f"interaction ID {id!r} is already in use")
    released_hold_end: float | None = None
    if options.duration is not None:
        duration = options.duration
    else:
        ends = [p.motion.end for p in participants]
        for prop in props:
            if isinstance(prop.track, TransformTrack):
                ends.append(prop.track.keys[-1].time)
            elif isinstance(prop.track, AttachedProp):
                ends.append(next(a.release for a in prop.track.motion.attachments if a.name == prop.track.name))
            else:
                raise LimbError(f"prop {prop.mesh.name}: custom frame sources require BakeOptions(duration=...)")
        duration = max(ends, default=0) or 1.0
    count = _frame_count(duration, options)
    if options.duration is None and any(isinstance(prop.track, AttachedProp) for prop in props):
        project = next(cv.scene.iter("project"), None)
        scene_duration = project.attributes().get("duration") if project is not None else None
        if scene_duration is None:
            raise LimbError("attached props need a scene duration or an explicit BakeOptions(duration=...)")
        try:
            project_end = float(scene_duration)
        except (ValueError, TypeError, OverflowError) as exc:
            raise LimbError("attached props need a finite scene duration") from exc
        if not math.isfinite(project_end) or project_end < 0 or math.ulp(project_end) > 1e-6:
            raise LimbError("attached props need a representable scene duration")
        if _scene_time(project_end) > _scene_time(options.offset + duration):
            released_hold_end = project_end
    times = tuple(i / options.fps for i in range(count)) + ((duration,) if released_hold_end is not None else ())
    scene_times = tuple(options.offset + time for time in times)
    if type(camera) is CameraTrack:
        camera.__post_init__()
        scene_end = released_hold_end if released_hold_end is not None else options.offset + duration
        if scene_end > camera.duration:
            raise LimbError('camera track must cover the complete bake interval', code='projection')
        if released_hold_end is not None:
            count = _frame_count(scene_end - options.offset, options)
            times = tuple(i / options.fps for i in range(count))
            scene_times = tuple(options.offset + time for time in times)
        events = dict(zip(scene_times, times, strict=True))
        if released_hold_end is not None:
            events[options.offset + duration] = duration
        for sample in camera.samples:
            if options.offset < sample.time < scene_end:
                events[sample.time] = sample.time - options.offset
        scene_times = tuple(sorted(events))
        times = tuple(events[time] for time in scene_times)
        cameras = tuple(camera.sample(time) for time in scene_times)
    elif type(camera) is Camera:
        cameras = (camera,) * len(times)
    else:
        raise LimbError('interaction camera must be Camera or CameraTrack', code='projection')
    frame_total = len(times)
    if frame_total > options.max_frames:
        raise LimbError("interaction frame budget exceeded", code="budget")
    surface_count = sum(3 + len(p.motion.hand.digits) for p in participants) + sum(len(p.mesh.faces) for p in props)
    estimate = frame_total * (2 + surface_count * 24) + 1
    if estimate > options.max_nodes:
        raise LimbError(f"interaction budget exceeded: {count} frames, at most {estimate} nodes", code="budget")
    intervals = tuple(
        (
            _scene_time(time),
            _scene_time(scene_times[i + 1])
            if i + 1 < len(scene_times)
            else _scene_time(released_hold_end if released_hold_end is not None else options.offset + duration),
        )
        for i, time in enumerate(scene_times)
    )
    if any(start >= end for start, end in intervals):
        raise LimbError('camera/bake cuts must have distinct representable scene times', code='projection')
    inverse = parent_transform.inverse()
    reports = []
    frames: list[list[_Surface]] = [[] for _ in range(frame_total)]
    for participant in participants:
        if options.quality is not None:
            options.quality.check_scope(participant.motion, participant.style, options.fps)
        adapter = adapter_for(participant.style)
        if (
            any(view.projection == "perspective" for view in cameras)
            and not adapter.capabilities.perspective
            or len(participant.motion.hand.digits) > 1
            and not adapter.capabilities.articulated_digits
            or "contour" not in adapter.capabilities.deformation
        ):
            raise LimbError(f"adapter {participant.style} cannot draw the requested interaction", code="capability")
        samples = tuple(
            replace(
                sample_motion(
                    participant.motion,
                    min(time, duration) if released_hold_end is not None else time,
                    track=participant.name,
                ),
                time=time,
            )
            for time in times
        )
        poses = tuple(
            project_pose(
                s,
                view,
                width=participant.motion.arm.width,
                parent=parent_transform,
                thickness=participant.motion.hand.thickness,
                correctives=participant.correctives,
            )
            for s, view in zip(samples, cameras, strict=True)
        )
        reports.append((participant.name, audit(samples, poses, participant.motion.arm, quality=options.quality)))
        for frame, pose in zip(frames, poses, strict=True):
            for part in pose.parts:
                frame.append(
                    _Surface(f"{participant.name}:{part.name}", part.depth, participant, pose.select({part.name}))
                )
    for prop in props:
        for time, frame, view in zip(times, frames, cameras, strict=True):
            transform = prop.track.sample(min(time, duration) if released_hold_end is not None else time)
            for face in prop.mesh.faces:
                projected = [view.project(p, frame=transform) for p in face.vertices]
                frame.append(
                    _Surface(
                        f"{prop.mesh.name}:{face.name}",
                        sum(p.depth for p in projected) / len(projected),
                        face=face,
                        polygon=tuple(inverse.point(p.xy) for p in projected),
                    )
                )
    for frame in frames:
        frame.sort(key=lambda s: (s.depth, s.name))
    before = len(list(cv.scene.iter()))
    root = cv.group(parent, id)
    for i, frame in enumerate(frames):
        group = cv.group(root, f"{id}-frame-{i:06d}")
        start, end = intervals[i]
        cv.gate(group, [(start, end)])
        for j, surface in enumerate(frame):
            if surface.participant is not None and surface.pose is not None:
                adapter_for(surface.participant.style).draw(
                    cv, group, surface.pose, surface.participant.appearance, id=f"{id}-drawing-{i:06d}-{j:04d}"
                )
            elif surface.face is not None:
                cv.path(group, path(surface.polygon), surface.face.fill, surface.face.outline, 1.5)
    nodes = len(list(cv.scene.iter())) - before
    return InteractionResult(
        root,
        frame_total,
        tuple((name, replace(report, nodes=nodes)) for name, report in reports),
        nodes,
        tuple(tuple((surface.name, surface.depth) for surface in frame) for frame in frames),
    )
