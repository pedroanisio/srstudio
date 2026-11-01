"""Geometric and temporal quality evidence, independent of any particular drawing style."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .errors import Diagnostic, LimbError
from .geometry import ProjectedPose
from .math3d import Vec3, number
from .model import ArmProfile, label
from .motion import Sample
from .props import Sphere, capsule_distance

_LIMITS = (
    'max_speed',
    'max_acceleration',
    'max_jerk',
    'max_elbow_speed',
    'max_hand_angular_speed',
    'max_hand_angular_acceleration',
    'max_reach_error',
    'max_penetration',
)


@dataclass(frozen=True)
class CollisionSphere(Sphere):
    """An authored world-space obstacle checked against upper-arm and forearm capsules, not the drawn mesh."""

    parts: tuple[str, ...] = ('upper', 'forearm')

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.center, Vec3) or number(self.radius, 'obstacle radius') <= 0:
            raise LimbError('an obstacle needs a Vec3 center and positive radius')
        if (
            not isinstance(self.parts, tuple)
            or not self.parts
            or len(self.parts) > 2
            or any(p not in ('upper', 'forearm') for p in self.parts)
            or len(set(self.parts)) != len(self.parts)
        ):
            raise LimbError('obstacle parts must uniquely name upper and/or forearm')


@dataclass(frozen=True)
class QualityProfile:
    """Opt-in character/style limits in canonical world units and seconds; no universal anatomical score.

    A warn profile records findings. An error profile refuses emission on a breach or insufficient samples.
    Collision checks use authored spheres against arm capsules of radius arm.width/2. This is envelope evidence,
    not exact mesh collision or continuous collision detection. Limits must be calibrated for the intended rig.
    """

    name: str
    max_speed: float | None = None
    max_acceleration: float | None = None
    max_jerk: float | None = None
    max_elbow_speed: float | None = None
    max_hand_angular_speed: float | None = None
    max_hand_angular_acceleration: float | None = None
    max_reach_error: float | None = None
    max_penetration: float | None = None
    policy: str = 'error'
    obstacles: tuple[CollisionSphere, ...] = ()
    max_collision_checks: int = 1000000

    def __post_init__(self) -> None:
        label(self.name, 'quality profile name')
        for metric in _LIMITS:
            limit = getattr(self, metric)
            if limit is not None and number(limit, metric) < 0:
                raise LimbError(f'{metric} must be non-negative')
        if self.policy not in ('warn', 'error'):
            raise LimbError('quality policy must be warn or error')
        if (
            not isinstance(self.obstacles, tuple)
            or len(self.obstacles) > 128
            or any(not isinstance(o, CollisionSphere) for o in self.obstacles)
        ):
            raise LimbError('quality obstacles must be a tuple of at most 128 CollisionSpheres')
        if len({o.name for o in self.obstacles}) != len(self.obstacles):
            raise LimbError('obstacle names must be unique')
        if self.max_penetration is not None and not self.obstacles:
            raise LimbError('a penetration limit needs explicit obstacles')
        if type(self.max_collision_checks) is not int or not 1 <= self.max_collision_checks <= 1000000:
            raise LimbError('max_collision_checks must be an integer within 1..1000000')


@dataclass(frozen=True)
class QualityFinding:
    code: str
    metric: str
    actual: float | None
    limit: float
    time: float | None
    remedy: str
    obstacle: str | None = None
    part: str | None = None

    def diagnostic(self) -> Diagnostic:
        return Diagnostic(
            self.code,
            f'{self.metric}: {self.actual!r}, limit {self.limit:g}; {self.remedy}',
            max(0.0, self.actual - self.limit) if self.actual is not None else 0.0,
        )


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
    max_jerk: float = 0.0
    max_hand_angular_acceleration: float = 0.0
    max_penetration: float = 0.0
    quality_profile: str | None = None
    quality_findings: tuple[QualityFinding, ...] = ()

    def to_dict(self) -> dict:
        result = asdict(self)
        result['metric_definitions'] = {
            'max_speed': {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second'},
            'max_acceleration': {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second^2'},
            'max_elbow_speed': {'subject': 'elbow', 'space': 'world', 'unit': 'canonical units/second'},
            'max_hand_angular_speed': {'subject': 'hand frame', 'space': 'world', 'unit': 'radians/second'},
            'max_jerk': {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second^3'},
            'max_hand_angular_acceleration': {'subject': 'hand frame', 'space': 'world', 'unit': 'radians/second^2'},
            'max_penetration': {
                'subject': 'arm capsules versus obstacle spheres',
                'space': 'world',
                'unit': 'canonical units',
            },
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
    quality: QualityProfile | None = None,
) -> MotionReport:
    if quality is not None and not isinstance(quality, QualityProfile):
        raise LimbError('quality must be a QualityProfile')
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
    angular_velocities = []
    for a, b in zip(samples, samples[1:], strict=False):
        if b.time <= a.time:
            raise LimbError("quality samples must be in strictly increasing time order")
        # Each secant velocity belongs to its interval midpoint, including a short final held-pose interval.
        velocities.append((a.time + (b.time - a.time) / 2, (b.arm.wrist - a.arm.wrist) / (b.time - a.time)))
        elbow_speeds.append(a.arm.elbow.distance(b.arm.elbow) / (b.time - a.time))
        rotation = a.hand.frame.rotation.inverse() * b.hand.frame.rotation
        angular_velocities.append(
            ((a.time + b.time) / 2, a.hand.frame.rotation.rotate(rotation.rotation_vector) / (b.time - a.time))
        )
    accelerations = _differentiate(velocities)
    jerks = _differentiate(accelerations)
    angular_accelerations = _differentiate(angular_velocities)
    points = [p for pose in poses for part in pose.parts for p in part.polygon]
    if not points:
        raise LimbError("quality audit has no visible geometry")
    xs, ys = zip(*points, strict=True)
    penetration, obstacle, part, collision_time = _collisions(samples, profile, quality)
    report = MotionReport(
        len(samples),
        bone,
        contact,
        max((v.length for _, v in velocities), default=0.0),
        max((v.length for _, v in accelerations), default=0.0),
        (min(xs), min(ys), max(xs), max(ys)),
        hidden_parts,
        nodes,
        max(s.arm.residual for s in samples),
        max(elbow_speeds, default=0.0),
        max((v.length for _, v in angular_velocities), default=0.0),
        max((v.length for _, v in jerks), default=0.0),
        max((v.length for _, v in angular_accelerations), default=0.0),
        penetration,
    )
    if quality is None:
        return report
    peaks = {
        'max_speed': _peak(velocities),
        'max_acceleration': _peak(accelerations),
        'max_jerk': _peak(jerks),
        'max_hand_angular_speed': _peak(angular_velocities),
        'max_hand_angular_acceleration': _peak(angular_accelerations),
        'max_elbow_speed': max(
            zip((t for t, _ in velocities), elbow_speeds, strict=True), key=lambda v: v[1], default=None
        ),
        'max_reach_error': max(((s.time, s.arm.residual) for s in samples), key=lambda v: v[1]),
        'max_penetration': (collision_time, penetration) if quality.obstacles else None,
    }
    findings = []
    for metric in _LIMITS:
        limit = getattr(quality, metric)
        if limit is None:
            continue
        peak = peaks[metric]
        if peak is None:
            findings.append(
                QualityFinding(
                    'quality.evidence',
                    metric,
                    None,
                    limit,
                    None,
                    'Increase the sample count; derivatives need two to four samples.',
                )
            )
        elif peak[1] > limit:
            findings.append(
                QualityFinding(
                    'quality.limit',
                    metric,
                    peak[1],
                    limit,
                    peak[0],
                    'Move the trajectory or obstacle.'
                    if metric == 'max_penetration'
                    else 'Adjust timing or trajectory, or explicitly revise the character quality profile.',
                    obstacle if metric == 'max_penetration' else None,
                    part if metric == 'max_penetration' else None,
                )
            )
    if findings and quality.policy == 'error':
        first = findings[0]
        context: dict[str, str | int | float] = {'field': first.metric, 'profile': quality.name, 'limit': first.limit}
        if first.actual is not None:
            context['measured'] = first.actual
        if first.time is not None:
            context['time'] = first.time
        raise LimbError(
            first.diagnostic().message, code=first.code, residual=first.diagnostic().residual, context=context
        )
    return replace(report, quality_profile=quality.name, quality_findings=tuple(findings))


def _differentiate(values: list[tuple[float, Vec3]]) -> list[tuple[float, Vec3]]:
    return [((a[0] + b[0]) / 2, (b[1] - a[1]) / (b[0] - a[0])) for a, b in zip(values, values[1:], strict=False)]


def _peak(values: list[tuple[float, Vec3]]) -> tuple[float, float] | None:
    return max(((t, v.length) for t, v in values), key=lambda v: v[1], default=None)


def _collisions(
    samples: tuple[Sample, ...], arm: ArmProfile, quality: QualityProfile | None
) -> tuple[float, str | None, str | None, float]:
    deepest: tuple[float, str | None, str | None, float] = (0.0, None, None, samples[0].time)
    if quality is None:
        return deepest
    if len(samples) * sum(len(o.parts) for o in quality.obstacles) > quality.max_collision_checks:
        raise LimbError('collision quality checks exceed their work budget', code='budget')
    for sample in samples:
        segments = {'upper': (sample.arm.shoulder, sample.arm.elbow), 'forearm': (sample.arm.elbow, sample.arm.wrist)}
        for obstacle in quality.obstacles:
            for part in obstacle.parts:
                a, b = segments[part]
                depth = obstacle.radius + arm.width / 2 - capsule_distance(a, b, obstacle.center, obstacle.center)
                if depth > deepest[0]:
                    deepest = (depth, obstacle.name, part, sample.time)
    return deepest


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
