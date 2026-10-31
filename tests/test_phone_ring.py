"""A phone that rings: the trill is a sound of its own, and a Collage ``ring`` beat plays it on its beat."""

import math
import struct
import wave

import pytest

from srstudio import foley
from srstudio.collage_sketch import EVENTS, sound_effects
from srstudio.sketch import Beat


def test_a_ring_is_a_trill_and_not_a_tone():
    assert len({a for a, _, _ in foley.RING}) == 2  # two notes, swapping
    assert all(a == b for a, b, _ in foley.RING)  # that do not slide
    assert 0.6 <= sum(n for _, _, n in foley.RING) <= 1.2  # one ring, not the whole call


def test_the_ring_is_heard_only_after_its_cue():
    rate = 8000
    out = foley.tones([0.5], 2.0, foley.RING, rate=rate)
    before = out[: int(0.5 * rate)]
    during = out[int(0.5 * rate) : int(1.2 * rate)]
    assert all(v == 0 for v in before)
    assert math.sqrt(sum(v * v for v in during) / len(during)) > 0.05


def test_a_ring_too_near_the_end_is_refused():
    with pytest.raises(foley.FoleyError):
        foley.tones([1.5], 2.0, foley.RING)


def _beat(start: float, event: str) -> Beat:
    return Beat(start, "gary", "", "open", "flat", "hold", None, None, event, ())


def test_a_ring_beat_writes_its_own_effect(tmp_path):
    assert "ring" in EVENTS
    effects = sound_effects([_beat(0.0, ""), _beat(1.0, "ring"), _beat(2.5, "ring")], 4.0, tmp_path, 7)
    assert [e["id"] for e in effects] == ["ring"]
    with wave.open(str(tmp_path / effects[0]["audio"])) as wav:
        rate, frames = wav.getframerate(), wav.readframes(wav.getnframes())
    samples = struct.unpack(f"<{len(frames) // 2}h", frames)
    assert len(samples) == 4 * rate
    assert all(v == 0 for v in samples[: rate])  # silent until the first ring
    assert any(samples[rate : 2 * rate])


def test_a_reel_without_a_ring_beat_writes_none(tmp_path):
    assert sound_effects([_beat(0.0, "")], 4.0, tmp_path, 7) == []
