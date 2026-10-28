"""Ink 02's audio step: the script's own checks (the shared steps are tested in test_narration.py)."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_router_audio
    finally:
        sys.path.pop(0)
    return the_router_audio


def test_the_script_is_twenty_takes_in_order_and_well_formed(audio):
    audio.check_script()
    assert len(audio.SCRIPT) == 20 and [x.id for x in audio.SCRIPT][::19] == ["01", "20"]
    assert sum(x.is_effect for x in audio.SCRIPT) == 4 and all(x.shot in audio.SHOTS for x in audio.SCRIPT)
    with pytest.raises(ValueError, match="unique and in order"):
        audio.check_script(audio.SCRIPT[::-1])
    bad = audio.Line("99", "sfx", "wide", "", "[X]", 0.1, prompt="x", seconds=30, longest=1)
    with pytest.raises(ValueError, match="seconds"):
        audio.check_script((bad,))
    with pytest.raises(ValueError, match="bracketed"):
        audio.check_script((audio.Line("99", "sfx", "wide", "", "beep", 0.1, prompt="x", seconds=1, longest=1),))
    with pytest.raises(ValueError, match="unknown shot"):
        audio.check_script((audio.Line("99", "human", "roof", "", "Hi.", 0.1),))
    with pytest.raises(ValueError, match="unknown actor"):
        audio.check_script((audio.Line("99", "printer", "desk", "", "Hi.", 0.1),))
    with pytest.raises(ValueError, match="voiced actor"):
        audio.check_script((audio.Line("99", "human", "desk", "", "  ", 0.1),))
