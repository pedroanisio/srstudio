"""Geometric and temporal quality evidence, independent of any particular drawing style."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .errors import Diagnostic, LimbError
from .geometry import ProjectedPose
from .model import ArmProfile
from .motion import Sample


@dataclass(frozen=True)
class MotionReport:
    """Sampled evidence, not a biomechanical or emotional pass/fail score.

    Speed/acceleration retain their legacy names and measure wrist translation in world canonical units per
    second / second squared. Elbow speed uses that same space; hand angular speed is radians per second.
    Bounds are projected drawing coordinates after camera and parent transforms. Derivatives are finite differences.
    """

    samples: int
    max_bone_error: float
    max_contact_error: float
    max_speed: float
    max_acceleration: float
    bounds: tuple[float, float, float, float]
    hidden_parts: int = 0
    nodes: int = 0
    max_reach_error: float = 0.0
    max_elbow_speed: float = 0.0
    max_hand_angular_speed: float = 0.0

    def to_dict(self) -> dict:
        result = asdict(self)
        result['metric_definitions'] = {
            'max_speed': {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second'},
            'max_acceleration': {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second^2'},
            'max_elbow_speed': {'subject': 'elbow', 'space': 'world', 'unit': 'canonical units/second'},
            'max_hand_angular_speed': {'subject': 'hand frame', 'space': 'world', 'unit': 'radians/second'},
            'bounds': {'subject': 'drawn geometry', 'space': 'drawing parent', 'unit': 'drawing units'},
        }
        return result


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
    elbow_speeds = []
    angular_speeds = []
    for a, b in zip(samples, samples[1:], strict=False):
        if b.time <= a.time:
            raise LimbError("quality samples must be in strictly increasing time order")
        # Each secant velocity belongs to its interval midpoint, including a short final held-pose interval.
        velocities.append((a.time + (b.time - a.time) / 2, (b.arm.wrist - a.arm.wrist) / (b.time - a.time)))
        elbow_speeds.append(a.arm.elbow.distance(b.arm.elbow) / (b.time - a.time))
        rotation = a.hand.frame.rotation.inverse() * b.hand.frame.rotation
        angle = 2 * math.atan2(math.hypot(rotation.x, rotation.y, rotation.z), abs(rotation.w))
        angular_speeds.append(angle / (b.time - a.time))
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
        max(s.arm.residual for s in samples),
        max(elbow_speeds, default=0.0),
        max(angular_speeds, default=0.0),
    )


def motion_diagnostics(samples: tuple[Sample, ...]) -> tuple[Diagnostic, ...]:
    """Keep bounded evidence of allowed anatomical clamps across sampled frames."""
    grouped: dict[str, list[float]] = {}
    for sample in samples:
        for diagnostic in sample.arm.diagnostics:
            grouped.setdefault(diagnostic.code, []).append(diagnostic.residual)
    return tuple(
        Diagnostic(code, f"{len(values)} sampled poses reported {code}; maximum residual {max(values):g}", max(values))
        for code, values in sorted(grouped.items())
    )
