"""The collage family's numbers are numbers (ADR 0035): each case feeds ``True`` where a module took
``math.isfinite`` (or ``isinstance(int | float)``) for a number check, which takes a bool as 1."""

from __future__ import annotations

import pytest

from srstudio import collage, collage_photo
from srstudio.collage_group import Lineup, Place
from srstudio.errors import SrstudioError
from support.collage import D, pose
from support.collage import canvas as collage_canvas
from support.collage_group import PLACES as GROUP_PLACES
from support.collage_group import REACTIONS
from support.collage_photo import LAUGH, PLACES
from support.collage_photo import canvas as photo_canvas

LOOK = dict(name="x", summary="s", skin="#a0522d", hair="short", hair_color="#222222", top="#335577")


def photo(fn, *args, **kw):
    cv = photo_canvas()
    fn(cv, cv.comp, *args, **kw)


def printed(**kw):
    photo(collage_photo.print_photo, PLACES, LAUGH, **({"x": 0, "y": 0, "width": 900} | kw))


def placed(rosa: Place):
    Lineup(GROUP_PLACES | {"rosa": rosa}, REACTIONS, spans=((0.0, 2.0),))


def entered(enter):
    cv = collage_canvas()
    collage.figure(cv, cv.comp, collage.LOOKS["jun"], [pose()], D, enter=enter)


@pytest.mark.parametrize(
    "call",
    [
        lambda: collage.Look(**LOOK, blink=True),
        lambda: entered(True),
        lambda: photo(collage_photo.viewfinder, start=True),
        lambda: photo(collage_photo.viewfinder, start=0.0, tick=True),
        lambda: photo(collage_photo.timer, 0, 0, start=True),
        lambda: photo(collage_photo.flash, True),
        lambda: photo(collage_photo.flash, 1.0, hold=True),
        lambda: printed(width=True),
        lambda: printed(crop=(True, 0, 540, 960)),
        lambda: placed(Place(True, 1920.0, 0.5)),
        lambda: placed(Place(540.0, 1920.0, True)),
        lambda: Lineup(GROUP_PLACES, REACTIONS, spans=((True, 2.0),)),
        lambda: Lineup(GROUP_PLACES, REACTIONS, spans=((0.0, True),)),
    ],
)
def test_a_bool_is_not_a_second_a_size_or_a_position(call):
    with pytest.raises(SrstudioError):
        call()
