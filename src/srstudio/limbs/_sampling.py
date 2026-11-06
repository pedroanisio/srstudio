"""Bounded coverage of authored actions and contacts on an emission grid."""

from bisect import bisect_left, bisect_right

from .errors import Diagnostic, LimbError
from .motion import Motion


def coverage(motion: Motion, times: tuple[float, ...], duration: float, fps: int) -> tuple[Diagnostic, ...]:
    """Refuse invisible events; disclose missed phases without claiming continuous safety.

    Cropped-away events are intentional. A sample at the exclusive end does not
    cover an event. Binary searches keep work bounded by events * log(samples).
    """
    diagnostics = []

    def covered(start: float, end: float, path: str, *, required: bool, interior: bool = False) -> None:
        end = min(end, duration)
        if start >= end:
            return
        i = (bisect_right if interior else bisect_left)(times, start)
        if i < len(times) and times[i] < end:
            return
        remedy = 'Lengthen or move the event onto the output grid, or increase BakeOptions.fps (maximum 120).'
        if required:
            raise LimbError(
                'authored event has no emitted sample',
                code='motion.sampling',
                path=path,
                actual={'start_s': start, 'end_s': end, 'samples': 0},
                expected='at least one emitted sample in the authored interval',
                remedy=remedy,
                context={'fps': fps},
            )
        diagnostics.append(Diagnostic('motion.phase-sampling', f'{path} has no emitted sample. {remedy}'))

    for i, action in enumerate(motion.actions):
        if action.name == 'rest':
            continue
        path = f'motion.actions[{i}]'
        covered(action.start, action.end, path, required=True, interior=True)
        edges = (
            action.start,
            action.start + action.preparation * action.duration,
            action.stroke_at,
            action.stroke_at + action.hold * action.duration,
            action.end,
        )
        for name, start, end in zip(('preparation', 'stroke', 'hold', 'recovery'), edges, edges[1:], strict=False):
            covered(start, end, f'{path}.{name}', required=False)
    for i, contact in enumerate(motion.contacts):
        covered(contact.start, contact.end, f'motion.contacts[{i}]', required=True)
    return tuple(diagnostics)
