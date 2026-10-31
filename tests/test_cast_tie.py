"""An office actor's tie can come loose, and the drawing it replaces stays what shipped."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cast
from srstudio.cast import CastError
from srstudio.rig import Performance
from support.tip_tablet import canvas

ACTORS = [cast.Manager, cast.Candidate]  # Rosa's blouse covers the tie the shared body draws
KNOT = "M-11 120 L11 120 L8 146 L-8 146Z"
LOOSE_KNOT = "M-4 166 L20 170 L16 196 L-8 192Z"


def paths(actor, **extras) -> list[str]:
    cv = canvas()
    actor(cv).build(cv.comp, 540, 900, perf=Performance(extras=extras))
    return [e.get("path") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("shape") == "path"]


@pytest.mark.parametrize("actor", ACTORS)
def test_a_loose_tie_replaces_the_knot_and_opens_the_collar(actor):
    drawn = "\n".join(paths(actor, tie="loose"))
    assert KNOT not in drawn and LOOSE_KNOT in drawn
    assert "M-30 122 L0 160 L30 122" in drawn


@pytest.mark.parametrize("actor", ACTORS)
def test_without_it_the_tie_is_the_drawn_one(actor):
    assert paths(actor) == paths(actor, tie=None)
    assert KNOT in "\n".join(paths(actor))


def test_an_unknown_tie_is_refused_by_name():
    cv = canvas()
    with pytest.raises(CastError, match="unknown tie 'bow'; known: loose"):
        cast.Manager(cv).build(cv.comp, 540, 900, perf=Performance(extras={"tie": "bow"}))
