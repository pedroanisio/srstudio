"""A reel casts from the voices published reels use, by name."""

import re
from pathlib import Path

import pytest

from srstudio import toon_voices
from srstudio.toon import ToonDataError
from srstudio.voice import Voice

EPISODES = Path(__file__).resolve().parents[1] / "episodes"


def test_a_speaker_gets_its_voice_by_name():
    s = toon_voices.speaker("dad", "Brian", "goat", "deadpan")
    assert s.voice == Voice(role="dad", id=toon_voices.VOICES["Brian"], name="Brian")
    assert s.settings == toon_voices.DELIVERIES["deadpan"]
    assert s.character == "goat"


def test_a_speaker_may_be_heard_only():
    assert toon_voices.speaker("mom", "Laura").character is None


def test_an_unknown_voice_or_delivery_is_refused():
    with pytest.raises(ToonDataError, match="not a voice"):
        toon_voices.speaker("dad", "Morgan")
    with pytest.raises(ToonDataError, match="delivery"):
        toon_voices.speaker("dad", "Brian", delivery="whispered")


def test_every_voice_in_the_table_is_used_by_a_published_script():
    hand_written = "\n".join(p.read_text() for p in EPISODES.glob("*.py") if "toon_voices" not in p.read_text())
    unused = [name for name, id in toon_voices.VOICES.items() if not re.search(id, hand_written)]
    assert not unused


def test_tints_follow_the_cast_and_refuse_a_cast_too_big():
    a, b = toon_voices.speaker("a", "Brian"), toon_voices.speaker("b", "Laura")
    assert toon_voices.tinted(a, b, palette=("#111111", "#222222")) == {"a": "#111111", "b": "#222222"}
    with pytest.raises(ToonDataError, match="tints"):
        toon_voices.tinted(a, b, palette=("#111111",))
