"""The ink props' numbers are numbers (ADR 0035): each case feeds a bool where a module took ``math.isfinite`` for
a number check, which takes ``True`` as 1 and ``False`` as 0."""

from __future__ import annotations

import pytest

from srstudio import ink_doorbell, ink_meter
from srstudio.errors import SrstudioError
from srstudio.ink_meter import AppRow
from test_ink_meter import canvas, take


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((False, "OK"),)),
        lambda cv: ink_meter.kerb(cv, cv.comp, take(), view=(True, 0.0, 880.0)),
        lambda cv: ink_meter.kerb(cv, cv.comp, take(), tow=True),
        lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", at=True),)),
        lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), progress=(0.0, True)),
        lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), stars=True),
        lambda cv: ink_doorbell.doorbell(cv, cv.comp, take(), 300, 500, mark=("allow", True)),
        lambda cv: ink_doorbell.doorbell_view(cv, cv.comp, take("human", 2.0, "lens"), tags=((False, "UNKNOWN"),)),
    ],
)
def test_a_bool_is_not_a_second_a_scale_or_a_count(call):
    with pytest.raises(SrstudioError):
        call(canvas())
