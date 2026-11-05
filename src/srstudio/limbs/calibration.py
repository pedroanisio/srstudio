"""Versioned numeric regression envelopes for explicitly scoped human-arm performances.

Frozen limits come from the shipped reference corpus at 24 Hz with 25% derivative
headroom. They are not physiological limits or a substitute for rendered review.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from importlib import resources
from typing import TypedDict

from .compile import BakeOptions
from .errors import LimbError
from .geometry import project_pose
from .math3d import Vec3
from .model import ArmProfile, DigitProfile, HandProfile
from .motion import Action, Motion
from .projection import Camera
from .serialization import motion_dict
from .validation import QualityProfile, QualityScope, audit

_CONFIG = {'toon-human-conversation/1.0.0': ('toon', 2.0), 'gloss-human-deliberate/1.0.0': ('gloss', 3.0)}
_METRICS = (
    'max_speed',
    'max_acceleration',
    'max_jerk',
    'max_elbow_speed',
    'max_hand_angular_speed',
    'max_hand_angular_acceleration',
)
_ASSET = 'assets/limbs/quality-calibration-1.0.0.json'
# The hand every 1.0.0 envelope was measured with, written out so a later change to HUMAN cannot move it (ADR 0089
# fixes anatomy per version, ADR 0213): HUMAN before its thumb gained a third segment. The frozen source hashes in
# the asset check it.
CALIBRATED_HAND = HandProfile(
    'human',
    0.34,
    0.36,
    (
        DigitProfile('thumb', Vec3(0.16, 0.16, 0), (0.17, 0.13), -0.8, True),
        DigitProfile('index', Vec3(0.11, 0.36, 0), (0.18, 0.12, 0.08), -0.20),
        DigitProfile('middle', Vec3(0.025, 0.36, 0), (0.20, 0.13, 0.09), -0.03),
        DigitProfile('ring', Vec3(-0.065, 0.36, 0), (0.18, 0.12, 0.08), 0.13),
        DigitProfile('little', Vec3(-0.14, 0.36, 0), (0.14, 0.10, 0.07), 0.30),
    ),
)


def _fail(path: str, actual: object, expected: object, code: str = 'quality.scope') -> LimbError:
    return LimbError(
        f'{path} is outside the calibrated scope',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Use the declared preset scope or author and measure a separate QualityProfile.',
    )


def _known(name: str) -> tuple[str, float]:
    if not isinstance(name, str) or name not in _CONFIG:
        raise _fail('preset', name, list(_CONFIG), 'quality.preset')
    return _CONFIG[name]


@dataclass(frozen=True)
class ReferenceCase:
    name: str
    motion: Motion


class _Measurement(TypedDict):
    name: str
    source_sha256: str
    samples: int
    metrics: dict[str, float]


def reference_cases(name: str) -> tuple[ReferenceCase, ...]:
    """The exact immutable authoring corpus used to measure a preset, on CALIBRATED_HAND; both anatomical sides."""
    _, span = _known(name)
    cases: list[ReferenceCase] = []
    for side in ('right', 'left'):
        arm = ArmProfile(side=side)
        cases.extend(
            (
                ReferenceCase(f'point-{side}', Motion(arm, CALIBRATED_HAND, (Action('point', duration=span),))),
                ReferenceCase(f'present-{side}', Motion(arm, CALIBRATED_HAND, (Action('present', duration=span),))),
                ReferenceCase(
                    f'joined-{side}',
                    Motion(
                        arm,
                        CALIBRATED_HAND,
                        (Action('point', duration=span), Action('present', start=span, duration=span)),
                    ).chain(),
                ),
            )
        )
    return tuple(cases)


def measure_reference(name: str) -> dict:
    """Recompute bounded source measurements without emitting geometry or revising frozen limits."""
    _known(name)
    cases: list[_Measurement] = []
    for case in reference_cases(name):
        samples = tuple(case.motion.sample(i / 24) for i in range(math.ceil(case.motion.end * 24) + 1))
        poses = tuple(
            project_pose(s, Camera(), width=case.motion.arm.width, thickness=case.motion.hand.thickness)
            for s in samples
        )
        report = audit(samples, poses, case.motion.arm)
        raw = json.dumps(motion_dict(case.motion), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        cases.append(
            {
                'name': case.name,
                'source_sha256': hashlib.sha256(raw).hexdigest(),
                'samples': len(samples),
                'metrics': {metric: getattr(report, metric) for metric in _METRICS},
            }
        )
    peaks = {metric: max(case['metrics'][metric] for case in cases) for metric in _METRICS}
    return {
        'id': name,
        'fps': 24,
        'headroom': 1.25,
        'cases': cases,
        'peaks': peaks,
        'limits': {
            **{metric: math.ceil(value * 1.25 * 100) / 100 for metric, value in peaks.items()},
            'max_reach_error': 1e-6,
        },
    }


@dataclass(frozen=True)
class QualityPreset:
    """A named frozen envelope; options_for checks its scope before returning compiler options."""

    id: str
    style: str
    limits: tuple[tuple[str, float], ...]
    calibration: str

    def describe(self) -> dict:
        return {
            'schema': 'srstudio.quality-preset/1.0.0',
            'id': self.id,
            'version': self.id.rsplit('/', 1)[1],
            'scope': {
                'style': self.style,
                'fps': 24,
                'clock': 'motion seconds',
                'space': 'canonical world units; no automatic rescaling',
                'upper_arm': 1.0,
                'forearm': 0.9,
                'arm_width': 0.18,
                'hand': 'human',
                'hand_profile': {
                    'symbol': 'srstudio.limbs.calibration.CALIBRATED_HAND',
                    'thumb_segments': list(CALIBRATED_HAND.digits[0].lengths),
                },
                'sides': ['left', 'right'],
                'angular_units': 'radians',
                'drawing_scale': 'camera-controlled; limits use world units',
            },
            'limits': dict(self.limits),
            'calibration': {
                'asset': _ASSET,
                'sha256': self.calibration,
                'headroom': 1.25,
                'derivation': 'ceil(reference maximum * 1.25 * 100) / 100; reach tolerance 1e-6',
            },
            'perceptual_validation': 'not established by numeric calibration',
        }

    def options_for(self, motion: Motion, *, style: str, fps: int, policy: str = 'error') -> BakeOptions:
        scope = QualityScope(self.style, 24, hand=CALIBRATED_HAND)
        scope.check(motion, style, fps)
        limits = dict(self.limits)
        quality = QualityProfile(
            self.id,
            max_speed=limits['max_speed'],
            max_acceleration=limits['max_acceleration'],
            max_jerk=limits['max_jerk'],
            max_elbow_speed=limits['max_elbow_speed'],
            max_hand_angular_speed=limits['max_hand_angular_speed'],
            max_hand_angular_acceleration=limits['max_hand_angular_acceleration'],
            max_reach_error=limits['max_reach_error'],
            policy=policy,
            scope=scope,
        )
        return BakeOptions(fps=24, quality=quality)


def get_preset(name: str) -> QualityPreset:
    style, _ = _known(name)
    raw = resources.files('srstudio').joinpath(_ASSET).read_bytes()
    document = json.loads(raw)
    data = next(row for row in document['profiles'] if row['id'] == name)
    return QualityPreset(name, style, tuple(data['limits'].items()), hashlib.sha256(raw).hexdigest())


def list_presets() -> tuple[dict, ...]:
    return tuple(get_preset(name).describe() for name in _CONFIG)
