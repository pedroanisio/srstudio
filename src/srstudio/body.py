"""Opt-in spatial biped support, rooted torso motion and authored stepping.

The contract is quasi-static: a declared mass proxy must project into the convex
hull of planted soles. It is not a dynamics engine, collision solver or human gait
certificate. Every requested sample is validated; compilation also checks a bounded
grid and event boundaries. Units: meters, seconds, radians; x right, y down, z forward.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from sr_core.scene import Composition, Group

from . import _body_solve as solver
from ._body_support import support_area as support_area
from ._body_support import support_footprint as support_footprint
from ._body_support import support_hull as support_hull
from ._body_support import support_margin as support_margin
from ._body_types import BodyError as BodyError
from ._body_types import BodyKey as BodyKey
from ._body_types import BodyPose as BodyPose
from ._body_types import BodyProfile as BodyProfile
from ._body_types import BodyScore as BodyScore
from ._body_types import FootAnchor as FootAnchor
from ._body_types import LegPose as LegPose
from ._body_types import Step as Step
from ._body_types import fail, scalar
from .canvas import Canvas
from .limbs.projection import Camera

MAX_SAMPLES = 20_000


def parse_body(data: object) -> BodyScore:
    """Decode srstudio.body/1.0.0 or 1.1.0 without coercion; compile_body validates support."""
    from ._body_parse import parse

    return parse(data)


@dataclass(frozen=True)
class BodyPlan:
    score: BodyScore
    checked_times: tuple[float, ...]

    @property
    def profile(self) -> BodyProfile:
        return self.score.profile

    @property
    def duration(self) -> float:
        return self.score.duration

    def describe(self) -> dict:
        """Machine-readable scope; sampled support must not be mistaken for dynamics."""
        from ._body_draw import MAX_FRAMES, MAX_NODES

        return {
            'schema': 'srstudio.body-plan/1.0.0',
            'score_schema': 'srstudio.body/1.1.0',
            'units': {'distance': 'meters', 'time': 'seconds', 'angle': 'radians'},
            'axes': {'x': 'right', 'y': 'down', 'z': 'anatomical forward; camera convention toward viewer'},
            'clock': 'original performance seconds',
            'profile': asdict(self.profile),
            'support': {
                'method': 'static mass projection inside planted-foot convex hull',
                'ground': 'world y=0',
                'continuous_certificate': False,
                'mass_fractions': {'torso_head_arms': 0.6, 'each_thigh': 0.12, 'each_shin': 0.06, 'each_foot': 0.02},
            },
            'capabilities': {
                'root': True,
                'torso': True,
                'legs': True,
                'world_sole_anchors': True,
                'rooted_shoulders': True,
                'flat_foot_steps': True,
                'flight': False,
                'stairs': False,
                'foot_roll': False,
                'collision_solver': False,
                'hand_contacts': False,
            },
            'drawing': {
                'styles': ['solid', 'wire'],
                'sampling': 'held at fps on the original clock plus contact events',
                'max_frames': MAX_FRAMES,
                'max_nodes': MAX_NODES,
                'drawing_approval': None,
            },
            'validation_hz': self.score.validation_hz,
            'validation_samples': len(self.checked_times),
            'max_validation_samples': MAX_SAMPLES,
        }

    def sample(self, time: float) -> BodyPose:
        scalar(time, 'time', 0, self.duration)
        return solver.sample(self.score, time)

    def window(self, start: float, end: float) -> BodyWindow:
        scalar(start, 'window.start', 0, self.duration)
        scalar(end, 'window.end', 0, self.duration)
        if start >= end:
            raise fail('window', (start, end), 'a positive interval within the performance')
        return BodyWindow(self, start, end)


@dataclass(frozen=True)
class BodyWindow:
    plan: BodyPlan
    start: float
    end: float

    def sample(self, time: float) -> BodyPose:
        scalar(time, 'window.time', 0, self.end - self.start)
        return self.plan.sample(self.start + time)

    def place(
        self,
        cv: Canvas,
        parent: Composition | Group,
        *,
        camera: Camera,
        at: float = 0,
        fps: int = 24,
        style: str = 'solid',
        id: str | None = None,
    ) -> Group:
        """Draw held body poses with a static camera expressed in parent pixel units.

        Both styles are original candidate drawings. They do not inherit approval
        from a registered character. All geometry is checked before scene mutation.
        """
        from ._body_draw import place

        return place(self, cv, parent, camera=camera, at=at, fps=fps, style=style, id=id)


def compile_body(score: BodyScore) -> BodyPlan:
    """Validate authored support on a bounded grid plus all contact/key boundaries."""
    if not isinstance(score, BodyScore):
        raise fail('score', score, 'a typed BodyScore')
    scalar(score.duration, 'duration', 0.001, 600)
    if type(score.validation_hz) is not int or not 1 <= score.validation_hz <= 120:
        raise fail('validation_hz', score.validation_hz, 'an integer in 1..120')
    if not isinstance(score.profile, BodyProfile):
        raise fail('profile', score.profile, 'a typed BodyProfile')
    score.profile.__post_init__()
    for name, kind, maximum in (('roots', BodyKey, 1000), ('stance', FootAnchor, 2), ('steps', Step, 1000)):
        rows = getattr(score, name)
        if not isinstance(rows, tuple) or len(rows) > maximum or any(not isinstance(row, kind) for row in rows):
            raise fail(name, None, f'an immutable tuple of at most {maximum} {kind.__name__} records')
        for row in rows:
            row.__post_init__()
    if len(score.stance) != 2 or {f.side for f in score.stance} != {'left', 'right'}:
        raise fail('stance', None, 'one initial world anchor for each foot')
    if not score.roots or score.roots[0].time != 0 or score.roots[-1].time > score.duration:
        raise fail('roots', None, 'ordered root keys from zero, within the duration')
    for a, b in zip(score.roots, score.roots[1:], strict=False):
        if round(a.time, 6) >= round(b.time, 6):
            raise fail('roots', None, 'strictly increasing keys at scene precision')
        speed = 1.875 * a.root.origin.distance(b.root.origin) / (b.time - a.time)
        if speed > score.profile.max_root_speed:
            raise fail('roots.speed', speed, f'peak translation speed <= {score.profile.max_root_speed}m/s')
    previous = 0.0
    feet = {f.side: f.frame for f in score.stance}
    for i, step in enumerate(score.steps):
        if step.start < previous or step.end >= score.duration:
            raise fail(f'steps[{i}]', (step.start, step.end), 'ordered non-overlapping steps landing before duration')
        stride = feet[step.side].origin.distance(step.target.origin)
        if stride > score.profile.max_stride:
            raise fail(f'steps[{i}].target', stride, f'a stride <= {score.profile.max_stride} meters')
        feet[step.side] = step.target
        previous = step.end
    estimate = math.ceil(score.duration * score.validation_hz) + len(score.roots) + len(score.steps) * 5 + 2
    if estimate > MAX_SAMPLES:
        raise fail('samples', estimate, f'at most {MAX_SAMPLES} validation samples', 'body.budget')
    times = {
        0.0,
        score.duration,
        *(i / score.validation_hz for i in range(math.ceil(score.duration * score.validation_hz))),
    }
    times.update(k.time for k in score.roots)
    for step in score.steps:
        times.update(
            (step.start, step.end, (step.start + step.end) / 2, max(0, step.start - 1e-7), max(0, step.end - 1e-7))
        )
    plan = BodyPlan(score, tuple(sorted(times)))
    for time in plan.checked_times:
        plan.sample(time)
    return plan
