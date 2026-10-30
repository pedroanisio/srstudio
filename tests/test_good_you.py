"""Good, You (Stick 12) as data: the first second is held, repeated lines are word for word the same so they share a
recording, the injuries come in the sheet's order, and it stops on the sip."""

import sys
from collections import Counter
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import good_you_audio

        return good_you_audio
    finally:
        sys.path.pop(0)


def test_the_opening_holds_and_the_hook_is_the_line(data):
    assert data.SCRIPT.still == pytest.approx(1.0)
    assert data.HOOK == data.SCRIPT.takes[0].text
    assert data.SCRIPT.bed is None


def test_the_deadpan_is_one_recording_of_each_line(data):
    said = Counter((t.actor, t.text) for t in data.SCRIPT.takes if not t.is_effect)
    assert said[("a", data.HOW)] == 3 and said[("b", data.GOOD_YOU)] == 5 and said[("a", data.GOOD)] == 5
    speeds = {t.speed for t in data.SCRIPT.takes if t.text in (data.HOW, data.GOOD_YOU, data.GOOD)}
    assert len(speeds) == 1


def test_the_weeks_run_in_order_and_it_stops_on_the_sip(data):
    weeks = list(dict.fromkeys(t.shot for t in data.SCRIPT.takes))
    assert weeks == list(data.SHOTS)
    assert data.SCRIPT.takes[-1].shot == "sip"


def test_a_label_marks_every_week_after_the_first(data):
    assert "mon1" not in data.DAYS and set(data.DAYS) == {"mon2", "mon3", "mon4", "mon5", "friday"}
