"""Geometric and temporal quality evidence, independent of any particular drawing style."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import LimbError
from .geometry import ProjectedPose
from .model import ArmProfile
from .motion import Sample


@dataclass(frozen=True)
class MotionReport:
    samples: int
    max_bone_error: float
    max_contact_error: float
    max_speed: float
    max_acceleration: float
    bounds: tuple[float, float, float, float]
    hidden_parts: int = 0
    nodes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def audit(
    samples: tuple[Sample, ...],
    poses: tuple[ProjectedPose, ...],
    profile: ArmProfile,
    *,
    hidden_parts: int = 0,
    nodes: int = 0,
) -> MotionReport:
    if not samples or len(samples) != len(poses):
        raise LimbError("quality audit needs matching nonempty samples and projected poses")
    bone = max(
        max(
            abs(s.arm.shoulder.distance(s.arm.elbow) - profile.upper),
            abs(s.arm.elbow.distance(s.arm.wrist) - profile.forearm),
        )
        for s in samples
    )
    contact = max((d.residual for s in samples for d in s.contacts), default=0.0)
    if bone > profile.length * 1e-6 or contact > 1e-6:
        raise LimbError(
            "limb quality audit failed bone-length or contact tolerance", code="quality", residual=max(bone, contact)
        )
    velocities = []
    for a, b in zip(samples, samples[1:], strict=False):
        if b.time <= a.time:
            raise LimbError("quality samples must be in strictly increasing time order")
        velocities.append((b.time, (b.arm.wrist - a.arm.wrist) / (b.time - a.time)))
    accelerations = [(b[1] - a[1]).length / (b[0] - a[0]) for a, b in zip(velocities, velocities[1:], strict=False)]
    points = [p for pose in poses for part in pose.parts for p in part.polygon]
    if not points:
        raise LimbError("quality audit has no visible geometry")
    xs, ys = zip(*points, strict=True)
    return MotionReport(
        len(samples),
        bone,
        contact,
        max((v.length for _, v in velocities), default=0.0),
        max(accelerations, default=0.0),
        (min(xs), min(ys), max(xs), max(ys)),
        hidden_parts,
        nodes,
    )
