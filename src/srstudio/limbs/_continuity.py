"""Conservative continuity discovery for source tracks, joins and held compiler output.

These descriptions do not sample motion, certify reachability or alter interpolation.
True guarantees apply only to the named scope and stated conditions; false means no guarantee.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .motion import Motion, TransformTrack


def _guarantees(position: bool, velocity: bool, acceleration: bool) -> dict[str, bool]:
    return dict(position=position, velocity=velocity, acceleration=acceleration)


def describe_track(track: TransformTrack) -> dict:
    constant = len(track.keys) == 1
    stopped = track.interpolation == 'smooth' or constant
    endpoints = []
    for key in (track.keys[0], track.keys[-1]):
        endpoints.append(
            {
                'at': key.time,
                'translation_velocity_jump': not stopped and key.velocity is not None and key.velocity.length > 0,
                'rotation_velocity_jump': not stopped
                and key.angular_velocity is not None
                and key.angular_velocity.length > 0,
            }
        )
    return {
        'schema': 'srstudio.continuity/1.0.0',
        'subject': 'transform-track',
        'clock': 'motion seconds',
        'interpolation': track.interpolation,
        'interior_keys': {
            'translation': _guarantees(True, True, True),
            'rotation': _guarantees(True, stopped, stopped),
        },
        'rotation_velocity_matching': 'zero at keys' if stopped else 'approximate spherical controls',
        'endpoint_holds': endpoints,
        'outside': 'nearest frame held; nonzero endpoint velocities stop at the interval boundary',
        'conditions': [
            'Source sampling at interior authored keys, before projection, constraints or compiler baking.',
            'Finite well-conditioned inputs and clock intervals; floating-point evaluation has numerical error.',
            'Continuous rotation uses normalized linear blending for small arcs; exact angular C1/C2 is not promised.',
        ],
    }


def describe_motion(motion: Motion) -> dict:
    return {
        'schema': 'srstudio.continuity/1.0.0',
        'subject': 'motion',
        'clock': 'motion seconds',
        'root': describe_track(motion.root),
        'whole_motion': _guarantees(False, False, False),
        'joins': [
            {
                'after': window.after,
                'start': window.start,
                'end': window.end,
                'guarantees': _guarantees(True, False, False),
                'velocity_matching': 'estimated',
                'velocity_estimator': 'one-sided second-order differences of preserved source motion',
                'conditions': [
                    'Successful source samples with regular, reachable geometry and continuous source boundaries.',
                    'Wrist, hand orientation, elbow plane and effective finger controls; not rendered pixels.',
                    'Root motion, IK branch changes and constraint activation can invalidate derivative matching.',
                ],
            }
            for window in motion._join_windows
        ],
        'contacts': 'Join windows cannot replace active contacts; contact limits are still checked during sampling.',
        'emission': {
            backend: {'sampling': 'held', 'inherits_source_derivatives': False} for backend in ('native', 'baked')
        },
        'conditions': [
            'False means no general guarantee, not that every instance is discontinuous.',
            'Inspect and validate contacts, attachments, action boundaries and projections separately.',
            'Discovery does not validate unsampled poses or certify perceptual quality.',
        ],
    }
