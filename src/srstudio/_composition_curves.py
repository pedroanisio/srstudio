"""Conservative continuous envelopes for native vector springs and default splines.

Spring energy bounds displacement and velocity without sampling. Cubic Bezier
control hulls bound Catmull-Rom/default TCB segments. Source XML is never baked.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from . import composition as c
from ._curves import spline_coefficients, spring_response

CURVES = frozenset({'spring', 'catmull-rom', 'tcb'})
KEY_ATTRIBUTES = frozenset({'stiffness', 'damping', 'mass', 'carry'})
MAX_CARRIED_SEGMENTS = 8  # Native carry recursively evaluates the preceding segment twice.


def fail(expected: str) -> c.CompositionError:
    return c._fail('payload.animate', None, expected, 'composition.payload')


def curve(animation: ET.Element, key: ET.Element) -> str:
    return key.get('interpolation', animation.get('defaultInterpolation', 'linear'))


def advanced(animation: ET.Element) -> bool:
    return any(curve(animation, key) in CURVES for key in animation)


def validate(animation: ET.Element) -> None:
    carried = 0
    for index, key in enumerate(animation):
        kind = curve(animation, key)
        if KEY_ATTRIBUTES.intersection(key.attrib) and kind != 'spring':
            raise fail('spring parameters only on spring keys')
        if kind in CURVES and animation.get('property') == 'visible':
            raise fail('numeric properties for spring and spline interpolation')
        if kind != 'spring':
            carried = 0
            continue
        for name, default in (('stiffness', '100'), ('damping', '10'), ('mass', '1')):
            value = float(key.get(name, default))
            minimum = 0 if name == 'damping' else 1e-9
            if not math.isfinite(value) or not minimum <= value <= 1e9:
                raise fail('finite spring stiffness/mass in [1e-9, 1e9] and damping in [0, 1e9]')
        carry = key.get('carry', 'false')
        if carry not in ('true', 'false', '1', '0'):
            raise fail('a boolean spring carry value')
        carried = carried + 1 if index and carry in ('true', '1') else 0
        if index < len(animation) - 1 and carried > MAX_CARRIED_SEGMENTS:
            raise fail(f'at most {MAX_CARRIED_SEGMENTS} consecutive carried spring segments')


def _speed(kind: str, difference: float, span: float) -> float:
    """Bound arrival finite differences, including the engine's minimum difference step."""
    if kind == 'hold':
        return 0.0  # A held segment ends at its old value when evaluated by carry.
    h = max(1e-9, min(1e-3, 0.1 * span))
    if kind.startswith('expo-'):
        # Native exponential easing snaps exactly to the endpoint: its small
        # residual jump also contributes to a following spring's carried speed.
        return abs(difference) * (10 * math.log(2) / span + 2**-10 / h)
    factor = {'linear': 1.0, 'sine': math.pi / 2, 'quad': 2.0, 'cubic': 3.0, 'quart': 4.0, 'quint': 5.0}.get(
        kind.split('-')[0]
    )
    # Circular easing has an unbounded endpoint derivative, but the engine's
    # incoming finite difference is bounded by the whole value interval.
    return abs(difference) * factor / span if factor is not None else abs(difference) / h


def bounds(animation: ET.Element) -> tuple[float, float]:
    keys = tuple((float(k.attrib['time']), float(k.attrib['value'])) for k in animation)
    values = [v for _, v in keys]
    if len(keys) < 2:
        return min(values), max(values)
    splines = spline_coefficients(keys) if any(curve(animation, k) in ('catmull-rom', 'tcb') for k in animation) else ()
    speed = 0.0
    for i, ((start, a), (end, b)) in enumerate(zip(keys, keys[1:], strict=False)):
        key, span = animation[i], end - start
        kind = curve(animation, key)
        if kind == 'spring':
            stiffness, damping, mass = (
                float(key.get(n, d)) for n, d in (('stiffness', '100'), ('damping', '10'), ('mass', '1'))
            )
            w = math.sqrt(stiffness / mass)
            z = damping / (2 * math.sqrt(stiffness * mass))
            incoming = speed if i and key.get('carry', 'false') in ('true', '1') else 0.0
            amplitude = math.hypot(a - b, incoming / w)
            step, release = spring_response(span, w, z)
            tail = abs(a - b) * abs(1 - step) + incoming * abs(release)
            # The physical oscillator loses energy for nonnegative damping.
            # Native endpoint correction adds at most |tail| displacement and
            # |tail|/span speed. These bounds also cover carried arrivals.
            excursion = amplitude + tail
            values.extend((b - excursion, b + excursion))
            speed = w * amplitude + tail / span
        elif kind in ('catmull-rom', 'tcb'):
            _, c2, c1, c0 = splines[i]
            hull = (a, c0 + c1 / 3, c0 + (2 * c1 + c2) / 3, b)
            values.extend(hull)
            speed = max(3 * abs(y - x) / span for x, y in zip(hull, hull[1:], strict=False))
        else:
            speed = _speed(kind, b - a, span)
        if not math.isfinite(speed) or any(not math.isfinite(v) or abs(v) > 1e9 for v in values[-4:]):
            raise fail('finite curve envelopes within +/-1e9 source units')
    low, high = min(values), max(values)
    # Native weighted sums can round even a constant nonzero carried channel.
    # Identically zero channels remain exact, avoiding a spurious rotation disc.
    margin = max(1.0, abs(low), abs(high)) * 1e-10 if low or high else 0.0
    return low - margin, high + margin
