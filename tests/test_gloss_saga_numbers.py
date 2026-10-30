"""The Gloss and Saga sets' numbers are numbers (ADR 0035): each case feeds ``True`` where a module took
``math.isfinite`` for a number check, which takes a bool as 1."""

from __future__ import annotations

import pytest

from srstudio import gloss
from srstudio import gloss_sets as gs
from srstudio import saga_sets as ss
from srstudio.errors import SrstudioError
from support.gloss import FONT_FILE, D, font
from support.gloss import canvas as gloss_canvas
from support.saga import canvas as saga_canvas


def g(fn, *args, **kw):
    cv = gloss_canvas()
    fn(cv, cv.comp, *args, **kw)


def s(fn, *args, **kw):
    cv = saga_canvas()
    fn(cv, cv.comp, *args, **kw)


NO_FONT = pytest.mark.skipif(FONT_FILE is None, reason="no system font for the notice")


@pytest.mark.parametrize(
    "call",
    [
        lambda: g(gloss.nadia, at=(0, 0), end=D, walk=(True, 2.0, 300)),
        lambda: g(gloss.nadia, at=(0, 0), end=D, walk=(0.5, 2.0, True)),
        lambda: g(gs.plaza, end=True),
        lambda: g(gs.door, at=(540, 1200), end=D, scale=True),
        lambda: g(gs.ticket, at=(0, 0), end=D, number="7", scale=True),
        pytest.param(lambda: g(gs.notice, "T", "B", end=D, font=font(), settle=True), marks=NO_FONT),
        lambda: s(ss.compactor, end=D, walls=(0, 1), travel=True),
        lambda: s(ss.compactor, end=D, walls=(0, 1), start_px=True),
        lambda: s(ss.compactor, end=D, door=True),
        lambda: s(ss.cube_station, at=(540, 800), end=D, boom=True),
        lambda: s(ss.pebble, at=(700, 1480), end=D, lift=True),
    ],
)
def test_a_bool_is_not_a_second_a_scale_or_a_distance(call):
    with pytest.raises(SrstudioError):
        call()
