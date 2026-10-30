"""Take My Phone (Stick 11) as data: the first second is held, the hook is the key line, the two friends have two
voices, the reply is the last thing but her line, and the release is the b arm for a best friend."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import take_my_phone_audio

        return take_my_phone_audio
    finally:
        sys.path.pop(0)


def test_the_opening_holds_and_the_hook_is_the_key_line(data):
    assert data.STILL == pytest.approx(1.0) and data.SCRIPT.still == pytest.approx(1.0)
    assert data.HOOK == "Do NOT let me text him."
    assert data.SCRIPT.bed is None


def test_two_friends_two_voices(data):
    assert data.SCRIPT.voices["her"].id != data.SCRIPT.voices["friend"].id


def test_nothing_follows_her_line(data):
    assert data.SCRIPT.takes[-1].text == "He answered!" and data.SCRIPT.takes[-2].shot == "reply"


def test_the_shots_escalate_in_the_sheet_order(data):
    order = [t.shot for t in data.SCRIPT.takes]
    assert order.index("sit") < order.index("fridge") < order.index("safe") < order.index("gulp") < order.index("calm")


def test_the_phones_are_told_apart(data):
    assert data.HER_PHONE != data.FRIEND_PHONE


def test_the_close_shots_keep_their_faces_in_frame(data):
    for name, x in (("her", 400.0), ("friend", 820.0)):
        (fx, _), zoom, (tx, _) = data.CAMERAS[name]
        assert 92 < tx + (x - fx) * zoom < 988


def test_the_chase_stays_inside_the_frame_and_safe_of_the_table(data):
    cx, cy, rx, ry = data.ORBIT
    assert 92 < cx - rx and cx + rx < 988 and 280 < cy - ry and cy + ry < 1500
