"""Depth-composited spatial hand/prop interactions with bounded, history-independent baking."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Any, Protocol

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .compile import BakeOptions, _frame_count
from .correctives import ContourCorrection
from .errors import LimbError
from .geometry import ProjectedPose, path, project_pose
from .math3d import Frame, Vec3
from .motion import Motion
from .projection import Affine, Camera
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
    camera: Camera = _CAMERA,
    options: BakeOptions = _OPTIONS,
    parent_transform: Affine = _PARENT,
) -> InteractionResult:
    """Sort prop faces and individual limb surfaces together, far to near, on every held frame.

    Meshes and hands must use the same canonical coordinate system. Attachment tracks can be sampled in any
    order. Sorting uses average surface depth (the painter algorithm); intersecting surfaces must be split into
    separate faces by the author. There is no hidden physical simulation or renderer-dependent state.
    """
    _name(id)
    names = [p.name for p in participants] + [p.mesh.name for p in props]
    if not names or len(names) > 128 or len(names) != len(set(names)):
        raise LimbError("interaction needs 1..128 uniquely named participants and props")
    if any(
        str(n.attributes().get("id", "")) == id or str(n.attributes().get("id", "")).startswith(id + "-")
        for n in cv.scene.iter()
    ):
        raise LimbError(f"interaction ID {id!r} is already in use")
    duration = options.duration or max((a.end for p in participants for a in p.motion.actions), default=1.0)
    count = _frame_count(duration, options)
    surface_count = sum(3 + len(p.motion.hand.digits) for p in participants) + sum(len(p.mesh.faces) for p in props)
    estimate = count * (2 + surface_count * 24) + 1
    if estimate > options.max_nodes:
        raise LimbError(f"interaction budget exceeded: {count} frames, at most {estimate} nodes", code="budget")
    inverse = parent_transform.inverse()
    reports = []
    frames: list[list[_Surface]] = [[] for _ in range(count)]
    for participant in participants:
        adapter = adapter_for(participant.style)
        if (
            camera.projection == "perspective"
            and not adapter.capabilities.perspective
            or len(participant.motion.hand.digits) > 1
            and not adapter.capabilities.articulated_digits
            or "contour" not in adapter.capabilities.deformation
        ):
            raise LimbError(f"adapter {participant.style} cannot draw the requested interaction", code="capability")
        samples = tuple(participant.motion.sample(i / options.fps) for i in range(count))
        poses = tuple(
            project_pose(
                s,
                camera,
                width=participant.motion.arm.width,
                parent=parent_transform,
                thickness=participant.motion.hand.thickness,
                correctives=participant.correctives,
            )
            for s in samples
        )
        reports.append((participant.name, audit(samples, poses, participant.motion.arm)))
        for frame, pose in zip(frames, poses, strict=True):
            for part in pose.parts:
                frame.append(
                    _Surface(f"{participant.name}:{part.name}", part.depth, participant, pose.select({part.name}))
                )
    for prop in props:
        for i, frame in enumerate(frames):
            transform = prop.track.sample(i / options.fps)
            for face in prop.mesh.faces:
                projected = [camera.project(p, frame=transform) for p in face.vertices]
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
        start = math.floor((options.offset + i / options.fps) * 1e6 + 1e-9) / 1e6
        end = math.floor((options.offset + min(duration, (i + 1) / options.fps)) * 1e6 + 1e-9) / 1e6
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
        count,
        tuple((name, replace(report, nodes=nodes)) for name, report in reports),
        nodes,
        tuple(tuple((surface.name, surface.depth) for surface in frame) for frame in frames),
    )
