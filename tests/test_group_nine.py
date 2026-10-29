"""Group 9 (Stick 08) as data: the script checks, two distinct voices, the hook question, the sign never calls a
group before an earlier one, the cap comes on with the reveal and stays, the hold before the punchline and the
button in the cabin."""

import sys
from pathlib import Path

import pytest

from srstudio import stick, stick_airport

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import group_nine_audio

        return group_nine_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_and_opens_on_a_question_with_two_distinct_voices(data):
    data.SCRIPT.check()
    first = data.SCRIPT.takes[0]
    assert first.text.endswith("?") and first.shot == "wide"
    assert len({v.id for v in data.SCRIPT.voices.values()}) == 2


def test_the_looks_draw_and_only_the_pilot_wears_the_cap(data):
    for look in (data.SAM, data.PILOT, data.AGENT, *data.NEIGHBOURS):
        stick.check_look(look)
    assert data.SAM.cap is None and data.PILOT.cap is not None
    assert data.PILOT == stick.Look(hair=data.SAM.hair, glasses=data.SAM.glasses, tie=data.SAM.tie, cap=data.PILOT.cap)


def test_the_sign_calls_rising_groups_on_gate_takes_only(data):
    shots = {t.id: t.shot for t in data.SCRIPT.takes}
    assert all(shots[k] in ("wide", "sam", "agent", "bag") for k in data.NOW)
    groups = [int(v.split()[-1]) for v in data.NOW.values()]
    assert groups == sorted(groups) and all(len(v) <= stick_airport.NOW_CHARS for v in data.NOW.values())
    assert data.BAG_TAG in data.NOW.values()  # the bag's group is called while it is talked about


def test_the_reveal_holds_before_the_punchline_and_the_button_is_in_the_cabin(data):
    takes = list(data.SCRIPT.takes)
    ids = [t.id for t in takes]
    reveal = ids.index(data.CAPPED)
    assert takes[reveal].actor == "sam" and "pilot" in takes[reveal].text and takes[reveal].hold >= 1.2
    punch = takes[reveal + 1]
    assert punch.actor == "agent" and "Group 9" in punch.text
    assert takes[-1].shot == "cabin" and takes[-1].hold >= 1.2 and "middle seat" in takes[-1].text
    assert len(data.SEATS) == len(stick_airport.SEATS) and len(data.NEIGHBOURS) == 2


def test_the_bag_tag_hangs_clear_of_the_podium(data):
    # the podium is drawn last: a tag behind it loses its group
    assert data.BAG_X + stick_airport.TAG_SPAN[1] < stick_airport.PODIUM_X[0]
