"""The typed failures of ``srstudio.retarget`` (ADR 0188). Each carries a stable code, the path that failed, what was
found and what was expected, so a caller or an agent repairs the input from the error rather than from its prose."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SrstudioError

REMEDIES = {
    "retarget.input": "Pass a motion_bridge.MotionClip, a skeleton.SkeletonProfile and arguments in the stated bounds.",
    "retarget.limit": "Pass clamp=True to hold every listed control at its limit, or widen the profile's limits.",
    "retarget.warp": "Start the clip on a beat of the song, with a tempo ratio and a span the warp can hold.",
    "retarget.anchors": "Give the clip's beats as finite seconds in strictly increasing order.",
    "retarget.overlap": "Give at least two clip beats inside the clip, and a song span that reaches the second one.",
    "retarget.rate": "Pick a song whose tempo is nearer the clip's, or change per= so each stretch stays in range.",
}


class RetargetError(SrstudioError):
    """Anything srstudio.retarget refuses."""

    def __init__(self, message: str, *, code: str, path: str, actual: object = None, expected: object = None):
        super().__init__(
            f"{path}: {message}", code=code, path=path, actual=actual, expected=expected, remedy=REMEDIES[code]
        )
        self.code = code
        self.path = path


class RetargetInputError(RetargetError, ValueError):
    """An argument that is not what the call takes: another type, a frame the clip does not have, a bound passed."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, code="retarget.input", path=path, actual=actual, expected=expected)


@dataclass(frozen=True)
class LimitBreach:
    """One control a clip turns past this character's limit: when (seconds on the clock sampled), which control, the
    value the clip asks for and the limits it must lie in."""

    time_s: float
    key: str
    value: float
    low: float
    high: float


class RetargetLimitError(RetargetError, ValueError):
    """The clip turns controls past the profile's limits and the caller did not ask for clamping. ``breaches`` lists
    them in order, up to ``retarget.MAX_LISTED``; ``total`` counts them all."""

    def __init__(self, breaches: tuple[LimitBreach, ...], total: int):
        shown = "; ".join(
            f"{b.key}={b.value:.6g} at {b.time_s:.4g}s outside {b.low:.6g}..{b.high:.6g}" for b in breaches[:8]
        )
        more = f" and {total - 8} more" if total > 8 else ""
        super().__init__(
            f"{total} control value(s) past their limits: {shown}{more}",
            code="retarget.limit",
            path="clip",
            actual=[[b.time_s, b.key, b.value] for b in breaches],
            expected=[[b.key, [b.low, b.high]] for b in breaches],
        )
        self.breaches = breaches
        self.total = total


class BeatWarpError(RetargetError, ValueError):
    """A beat warp that cannot be built: a start off the song's grid, or a setting outside its bounds."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None, code: str = ""):
        super().__init__(message, code=code or "retarget.warp", path=path, actual=actual, expected=expected)


class AnchorOrderError(BeatWarpError):
    """The clip's beats are not finite seconds in strictly increasing order, so no monotonic map runs through them."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, path=path, actual=actual, expected=expected, code="retarget.anchors")


class EmptyOverlapError(BeatWarpError):
    """Fewer than two beats lie where both the clip and the song span are, so no stretch can be measured."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, path=path, actual=actual, expected=expected, code="retarget.overlap")


class WarpRateError(BeatWarpError):
    """A stretch between two beats would play the clip slower or faster than the stated range."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, path=path, actual=actual, expected=expected, code="retarget.rate")
