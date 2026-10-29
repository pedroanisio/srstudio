"""Stick 02's audio step: the script's own checks (the shared steps are tested in test_narration.py)."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import screen_share_audio
    finally:
        sys.path.pop(0)
    return screen_share_audio


def test_the_script_is_nine_takes_in_three_beats(audio):
    audio.check_script()
    assert len(audio.SCRIPT) == 9 and [x.beat for x in audio.SCRIPT][::4] == ["screen", "wrap-up", "friday"]
    assert sum(x.is_effect for x in audio.SCRIPT) == 1 and {x.actor for x in audio.SCRIPT} == {"boss", "dev", "sfx"}


@pytest.mark.parametrize(
    "line, match",
    [
        (dict(id="99", beat="monday"), "unknown beat"),
        (dict(id="99", shot="roof"), "unknown shot"),
        (dict(id="99", actor="printer"), "unknown actor"),
        (dict(id="99", text="  "), "voiced actor"),
        (dict(id="99", hold=-1), "hold"),
        (dict(id="99", actor="sfx", text="beep", prompt="x", seconds=1, longest=1), "bracketed"),
        (dict(id="99", actor="sfx", text="[X]", prompt="x", seconds=60, longest=1), "seconds"),
    ],
)
def test_a_malformed_take_is_refused(audio, line, match):
    base = dict(id="99", beat="screen", actor="dev", shot="close", mood="", text="Hi.", hold=0.1)
    with pytest.raises(ValueError, match=match):
        audio.check_script((audio.Line(**{**base, **line}),))


def test_takes_must_be_unique_and_in_order(audio):
    with pytest.raises(ValueError, match="unique and in order"):
        audio.check_script(audio.SCRIPT[::-1])
