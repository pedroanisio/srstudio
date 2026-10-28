"""Ink 02's audio step: the script's checks, word and phone timings, the schedule, the conform, the voice check."""

import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from srstudio.voice import RATE, Alignment, Voice, VoiceOutputError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_router_audio
    finally:
        sys.path.pop(0)
    return the_router_audio


def alignment(text, step=0.1, offset=0.5):
    n = len(text)
    return Alignment(
        tuple(text), tuple(offset + i * step for i in range(n)), tuple(offset + (i + 1) * step for i in range(n))
    )


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


def test_words_and_phones_are_relative_to_the_trimmed_clip(audio):
    a = alignment("Fine. Off.")  # 10 characters, 0.5..1.5
    words = audio.words_from_alignment(a, "Fine. Off.", trim_start=0.45, speech_duration=1.0)
    assert words == [{"text": "Fine.", "start": 0.05, "end": 0.55}, {"text": "Off.", "start": 0.65, "end": 1.0}]
    phones = audio.phones_from_alignment(a, 0.45, 1.0)
    assert [p["c"] for p in phones] == list("Fine. Off.") and phones[0]["start"] == 0.05 and phones[-1]["end"] == 1.0
    assert [p["c"] for p in audio.phones_from_alignment(a, 1.0, 0.3)] == [" ", "O", "f"]  # the cut drops the rest


def test_words_refuse_a_wrong_alignment_and_a_word_the_trim_cut(audio):
    with pytest.raises(VoiceOutputError, match="spells"):
        audio.words_from_alignment(alignment("Fine. On."), "Fine. Off.", 0, 2)
    with pytest.raises(VoiceOutputError, match="outside the trimmed clip"):
        audio.words_from_alignment(alignment("Fine. Off."), "Fine. Off.", trim_start=1.1, speech_duration=0.4)


def test_schedule_chains_the_takes_and_rounds_up_to_the_frame(audio):
    items = [{"id": "01", "duration": 1.3}, {"id": "02", "duration": 0.71}]
    assert audio.schedule(items) == pytest.approx(math.ceil(2.01 * 24) / 24)
    assert [q["start"] for q in items] == [0, 1.3]
    with pytest.raises(ValueError, match="positive"):
        audio.schedule([{"id": "01", "duration": 0}])
    with pytest.raises(ValueError, match="positive"):
        audio.schedule([{"id": "01", "duration": float("nan")}])


def test_consent_is_required(audio):
    with pytest.raises(SystemExit, match="SRSTUDIO_ALLOW_CLOUD"):
        audio.require_consent({})
    audio.require_consent({"SRSTUDIO_ALLOW_CLOUD": "1"})


def test_confirm_voice_checks_the_name_and_caches_only_the_name(audio, tmp_path):
    voice = Voice(role="router", id="abcdefgh12345678", name="Daniel")
    seen = []

    def fetch(url, headers):
        seen.append((url, headers.get("xi-api-key")))
        return {"name": "Daniel - Authoritative, British", "category": "premade", "settings": {"x": 1}}

    kept = audio.confirm_voice(tmp_path, "k", voice, fetch)
    assert kept == {"voice_id": voice.id, "name": "Daniel - Authoritative, British", "category": "premade"}
    assert seen[0][0].endswith(voice.id)
    record = json.loads((tmp_path / f"voice-{voice.id}.json").read_text())
    assert record == kept and "k" not in json.dumps(record)
    assert audio.confirm_voice(tmp_path, "", voice, fetch) == kept and len(seen) == 1  # cached: no request, no key
    with pytest.raises(VoiceOutputError, match="wants 'Chris'"):
        audio.confirm_voice(tmp_path, "k", Voice(role="h", id="other123", name="Chris"), lambda u, h: {"name": "Dan"})
    with pytest.raises(VoiceOutputError, match="no name"):
        audio.confirm_voice(tmp_path, "k", Voice(role="h", id="other456", name="Chris"), lambda u, h: ["x"])
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        audio.confirm_voice(tmp_path, "", Voice(role="h", id="other789", name="Chris"), fetch)


def tone(path, seconds=1.0, amplitude=0.5):
    n = round(seconds * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", round(amplitude * 32767 * math.sin(i * 0.05))) for i in range(n)))


def test_conform_cuts_levels_and_pads_to_the_sample(audio, tmp_path):
    src, dst = tmp_path / "src.wav", tmp_path / "dst.wav"
    tone(src)
    got = audio.conform(src, dst, 0.2, 0.7, 0.8, -6.0)
    assert got == pytest.approx(0.8, abs=1 / RATE) and dst.exists()
    with wave.open(str(dst), "rb") as w:
        assert (w.getframerate(), w.getnchannels()) == (RATE, 1)
    with pytest.raises(subprocess.CalledProcessError):  # the encoder failing is a failure, not a silent clip
        audio.conform(src, tmp_path / "x.wav", 0.2, 0.7, 0.8, 0.0, ffmpeg="false")
    with pytest.raises(VoiceOutputError, match="expected 48000 Hz"):
        bad = tmp_path / "bad.wav"
        with wave.open(str(bad), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"\0" * 400)
        audio.wav_seconds(bad)
