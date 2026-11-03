"""A jog on the spot, fitted to any figure's drawn body, bobbing by exactly the amount the caller asks.

:data:`TEMPLATE` (the Stick door's :data:`srstudio.stick_door.JOG`) is two drawings: ``jog-a`` planted on one foot,
``jog-b`` in the air on the other. Fitting it to a dance figure means giving it that figure's bones, and the figure's
bones are drawn foreshortened, one leg shorter than the other. Fitting each leg to its own drawn length makes each
drawing stand on a different leg length, so the hip, and the crown with it, rises or drops between the two drawings by
however much the reference's foreshortening differs: a reference with legs of 403 and 420 px doubled the bob
(33.7 canon px against the template's 18) and the figure popped at every swap.

:func:`fit_jog` takes the legs as one body instead. Both drawings stand on a support leg as long as the reference's
least foreshortened leg, each drawing's other leg keeps the template's own foreshortening against its support leg, and
the drawings are placed so the crown moves between them by ``bob``, whatever the reference. The upper body takes the
reference's torso, neck and arm lengths along the template's directions.

A standing gate on every multi-character dance (arc4d3, Slack 1793669089.710129): a jog's bob stays within the limit
whatever the fit. The bob is the caller's to choose against its figure's own limit (see
:mod:`srstudio.figure_steps`); this module guarantees it is the bob drawn.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from .errors import SrstudioError
from .stick import Point, RigPose
from .stick_door import JOG

__all__ = ["TEMPLATE", "JogFitError", "fit_jog"]

TEMPLATE: Mapping[str, RigPose] = JOG


class JogFitError(SrstudioError, ValueError):
    """A reference or a bob a jog cannot be fitted to."""


def _length(a: Point, b: Point, what: str) -> float:
    n = math.dist(a, b)
    if not math.isfinite(n) or n <= 0:
        raise JogFitError(f"the reference's {what} has no length")
    return n


def _leg(pose: RigPose, side: int) -> float:
    return math.dist(pose.hip, pose.knees[side]) + math.dist(pose.knees[side], pose.feet[side])


def _support(pose: RigPose) -> int:
    return 0 if pose.feet[0][1] >= pose.feet[1][1] else 1


def _along(a: Point, b: Point, length: float) -> Point:
    d = math.dist(a, b)
    return (a[0] + (b[0] - a[0]) / d * length, a[1] + (b[1] - a[1]) / d * length)


def _scaled(origin: Point, a: Point, b: Point, k: float) -> Point:
    return (origin[0] + (b[0] - a[0]) * k, origin[1] + (b[1] - a[1]) * k)


def fit_jog(ref: RigPose, bob: float, template: Mapping[str, RigPose] = TEMPLATE) -> dict[str, RigPose]:
    """``template``'s drawings on ``ref``'s body: support legs as long as ``ref``'s longer drawn leg, the planted
    drawing's foot where the template plants it, every other drawing's hip (and crown) ``bob`` px above the planted
    one's. Raises :class:`JogFitError` for a bob that is not a height from 0 below the leg's length, or a reference
    with a bone of no length."""
    if isinstance(bob, bool) or not isinstance(bob, (int, float)) or not math.isfinite(bob) or bob < 0:
        raise JogFitError(f"bob must be a height in px from 0, got {bob!r}")
    for side in (0, 1):
        _length(ref.hip, ref.knees[side], "thigh")
        _length(ref.knees[side], ref.feet[side], "shin")
    torso, neck = _length(ref.hip, ref.neck, "torso"), _length(ref.neck, ref.head, "neck")
    upper = [_length(ref.neck, ref.elbows[s], "upper arm") for s in (0, 1)]
    lower = [_length(ref.elbows[s], ref.hands[s], "forearm") for s in (0, 1)]
    leg = max(_leg(ref, 0), _leg(ref, 1))
    if bob >= leg:
        raise JogFitError(f"bob {bob} px is not below the leg's {leg:.1f} px")
    drawn: dict[str, RigPose] = {}
    for name, t in template.items():
        k = leg / _leg(t, _support(t))
        knees = tuple(_scaled(t.hip, t.hip, t.knees[s], k) for s in (0, 1))
        feet = tuple(_scaled(knees[s], t.knees[s], t.feet[s], k) for s in (0, 1))
        neck_at = _along(t.hip, t.neck, torso)
        elbows = tuple(
            _along(neck_at, t.elbows[s], upper[s]) if t.elbows[s] != neck_at else t.elbows[s] for s in (0, 1)
        )
        hands = tuple(_along(elbows[s], t.hands[s], lower[s]) for s in (0, 1))
        toes = None if t.toes is None else tuple(_scaled(feet[s], t.feet[s], t.toes[s], 1.0) for s in (0, 1))
        drawn[name] = RigPose(
            head=_along(neck_at, t.head, neck),
            neck=neck_at,
            hip=t.hip,
            knees=(knees[0], knees[1]),
            feet=(feet[0], feet[1]),
            elbows=(elbows[0], elbows[1]),
            hands=(hands[0], hands[1]),
            toes=None if toes is None else (toes[0], toes[1]),
        )
    planted = max(template, key=lambda n: max(f[1] for f in template[n].feet))
    floor = max(f[1] for f in template[planted].feet)
    first = drawn[planted]
    hip_y = first.hip[1] + floor - max(f[1] for f in first.feet)
    out: dict[str, RigPose] = {}
    for name, p in drawn.items():
        dy = (hip_y if name == planted else hip_y - bob) - p.hip[1]
        out[name] = _shift(p, dy)
    return out


def _shift(p: RigPose, dy: float) -> RigPose:
    m = lambda q: (q[0], q[1] + dy)  # noqa: E731
    pair = lambda q: (m(q[0]), m(q[1]))  # noqa: E731
    return RigPose(
        head=m(p.head),
        neck=m(p.neck),
        hip=m(p.hip),
        knees=pair(p.knees),
        feet=pair(p.feet),
        elbows=pair(p.elbows),
        hands=pair(p.hands),
        toes=None if p.toes is None else pair(p.toes),
    )
