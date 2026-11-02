"""Big Font as data: the viewer's line read first, and every caption pill kept off the show's bug."""

import sys
from pathlib import Path

import pytest

from srstudio import collage, opener, show

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import big_font_data

        return big_font_data
    finally:
        sys.path.pop(0)


def test_the_opening_line_ends_above_the_first_caption(data):
    rows = data.TEXT.count("\n") + 1
    assert opener.box(600.0, data.OPENER_TOP, rows=rows)[3] <= data.UNDER_OPENER
    assert data.STAGING.caption_tops == {data.FIRST: data.UNDER_OPENER}


def test_the_captions_are_asked_to_clear_the_bug(data):
    assert data.STAGING.clear_bug is True
    assert collage.CAPTION_TOP < show.BUG_BOX[3] + show.CLEAR  # the usual place is in the bug's rows: it matters
