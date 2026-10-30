"""The toon family's numbers are numbers (ADR 0035): each case feeds a bool where a module took ``math.isfinite``
(or ``!= 0``) for a number check, which takes ``True`` as 1 and ``False`` as 0."""

from __future__ import annotations

import pytest

from srstudio import toon_dinner, toon_props, toon_sets
from srstudio.toon import ToonDataError
from support.toon_props import canvas, measure

STATES = [(0.0, "TAP CARD", "idle"), (3.0, "DECLINED", "bad")]


def drawn(fn, *args, **kw):
    cv = canvas()
    fn(cv, cv.comp, *args, **kw)


@pytest.mark.parametrize(
    "call",
    [
        lambda: toon_sets.cycle_keys([(0.0, 1.0)], True, 0.0, 2.0),
        lambda: toon_sets.cycle_keys([(0.0, 1.0)], 2.0, True, 2.0),
        lambda: toon_sets.cycle_keys([(0.0, 1.0)], 2.0, 0.0, True),
        lambda: drawn(toon_sets.plant, scale=True),
        lambda: drawn(toon_props.mug, steam=[(True, 2.0)]),
        lambda: drawn(toon_props.mug, steam=[(0.0, True)]),
        lambda: drawn(toon_props.toasts, [toon_props.Toast(True, 3.0, "Rex", "x")]),
        lambda: drawn(toon_props.toasts, [toon_props.Toast(0.0, True, "Rex", "x")]),
        lambda: toon_props.scale_keys([(True, 1.0)]),
        lambda: toon_props.scale_keys([(0.0, True)]),
        lambda: drawn(toon_props.logo, shadow=(True, 2.0)),
        lambda: drawn(toon_props.logo, shadow=(0.0, True)),
        lambda: drawn(toon_props.badge, "Fern", True, 4.0, measure),
        lambda: drawn(toon_props.badge, "Fern", 0.0, True, measure),
        lambda: drawn(toon_dinner.card_reader, [(False, "TAP CARD", "idle")]),
        lambda: drawn(toon_dinner.card_reader, [STATES[0], (True, "DECLINED", "bad")]),
    ],
)
def test_a_bool_is_not_a_second_or_a_scale(call):
    with pytest.raises(ToonDataError):
        call()
