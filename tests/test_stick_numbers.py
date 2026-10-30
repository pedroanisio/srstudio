"""The stick family's numbers are numbers (ADR 0035): each case feeds ``True`` where a module took
``math.isfinite`` for a number check, which takes a bool as 1."""

from __future__ import annotations

import pytest

from srstudio import stick, stick_car, stick_flat, stick_gym, stick_school, stick_shop, stick_windshield
from srstudio.errors import SrstudioError
from support.stick_car import canvas
from support.stick_school import LINES
from support.stick_shop import SCREENS


def essay(**kw):
    cv = canvas()
    stick_school.essay(cv, cv.comp, LINES, title="T", by="B", shown=3, **kw)


def drawn(fn, *args, **kw):
    cv = canvas()
    fn(cv, cv.comp, *args, **kw)


@pytest.mark.parametrize(
    "call",
    [
        lambda: stick.word_cues([], size=True),
        lambda: stick.word_cues([], linger=True),
        lambda: stick.word_cues([], min_seconds=True, width=len),
        lambda: drawn(stick.words, [], scrim=True),
        lambda: stick_car.Scroll(speed=True).check(),
        lambda: stick_car.Scroll(offset=True).check(),
        lambda: drawn(stick_car.car, True),
        lambda: drawn(stick_car.car, 2.0, passing=(True,)),
        lambda: drawn(stick_car.car, 2.0, defocus=True),
        lambda: drawn(stick_car.ride, True),
        lambda: drawn(stick_car.ride, 2.0, amplitude=True),
        lambda: drawn(stick_car.laptop, 0, 0, title="Sent", rows=["a"], scale=True),
        lambda: drawn(stick_car.phone, sender="Mom", text="hi", buzz=(True,)),
        lambda: drawn(stick_shop.kiosk, SCREENS[:1], True),
        lambda: drawn(stick_shop.kiosk, SCREENS, 3.0, alarm=(True,)),
        lambda: drawn(stick_shop.avocado, 0, 0, scale=True),
        lambda: drawn(stick_windshield.windshield, True),
        lambda: drawn(stick_windshield.windshield, 2.0, speed=True),
        lambda: drawn(stick_windshield.dashboard, True),
        lambda: drawn(stick_windshield.dashboard, 4.0, buzz=(True,)),
        lambda: drawn(stick_windshield.dashboard, 4.0, down=True),
        lambda: drawn(stick_gym.gym, 5.0, sunrise=True),
        lambda: essay(mark=0, mark_at=True),
        lambda: essay(note="Edited", note_at=True),
        lambda: drawn(stick_flat.murphy_bed, True),
    ],
)
def test_a_bool_is_not_a_number_of_seconds_a_scale_or_a_level(call):
    with pytest.raises(SrstudioError):
        call()
