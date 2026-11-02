"""Your Rent as data: prices said as words and captioned in dollars, held to each other; the held look; the opener."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import opener, sketch

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import your_rent_data

        return your_rent_data
    finally:
        sys.path.pop(0)


def with_beat(d, line: int, **changes):
    beats = list(d.SKETCH.beats)
    i = next(k for k, b in enumerate(beats) if b.line == line and b.word == 0)
    beats[i] = replace(beats[i], **changes)
    return replace(d.SKETCH, beats=tuple(beats))


def test_the_sketch_as_written_passes(data):
    data.validate()
    assert [b.caption for b in data.SKETCH.beats if b.line in data.PRICES] == [
        "It's $2,200.",
        "$1,800. Utilities included.",
    ]


def test_a_price_captioned_with_another_amount_is_refused(data):
    with pytest.raises(sketch.SketchError, match="not its price"):
        data.validate(with_beat(data, 6, caption="$5,800. Utilities included."))


def test_a_price_whose_figures_are_not_the_words_said_is_refused(data, monkeypatch):
    monkeypatch.setitem(data.PRICES, 6, "$5,800. Utilities included.")
    with pytest.raises(sketch.SketchError, match="not the words said"):
        data.validate(with_beat(data, 6, caption="$5,800. Utilities included."))


def test_the_look_holds_before_the_last_line(data):
    look = next(b for b in data.SKETCH.beats if b.event == "look")
    with pytest.raises(sketch.SketchError, match="holds"):
        data.validate(with_beat(data, len(data.LINES) - 1, start=look.start + 0.5))


def test_the_opening_line_is_the_viewers_and_names_nobody(data):
    assert opener.check(data.TEXT, opener.seconds(data.TEXT), names=data.NAMES) == data.TEXT
    with pytest.raises(opener.OpenerError):
        opener.check(data.TEXT, opener.seconds(data.TEXT) - 0.1, names=data.NAMES)
