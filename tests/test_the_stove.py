"""The Stove (Stick 13) as data: arm B moves from frame one, the hook is the first line and the last, Dev keeps his
voice, each visit to the house is older than the last, and the U-turns reuse one recording."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
R3_DEV = "bIHbv24MWmeRgasZH58o"  # Will, Dev's voice in Repeat After Me


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_stove_audio

        return the_stove_audio
    finally:
        sys.path.pop(0)


def test_arm_b_has_no_held_opening_and_no_bed(data):
    assert not data.SCRIPT.still
    assert data.SCRIPT.bed is None


def test_the_hook_opens_and_closes_it(data):
    assert data.SCRIPT.takes[0].text == data.HOOK == data.SCRIPT.takes[-1].text
    assert data.SCRIPT.takes[-1].speed == pytest.approx(0.8)


def test_dev_keeps_his_voice(data):
    assert data.SCRIPT.voices["dev"].id == R3_DEV


def test_every_u_turn_is_the_same_recording(data):
    turns = [t for t in data.SCRIPT.takes if t.shot.startswith("turn")]
    assert len(turns) == 3 and len({(t.prompt, t.seconds) for t in turns}) == 1


def test_the_street_ages(data):
    assert data.TREE[1] < data.TREE[2] < data.TREE[3]
    assert data.KID_SCALE[1] < data.KID_SCALE[2] < data.KID_SCALE[3]
    assert data.NEIGHBOUR[3].hair == "bald"
