"""A line heard through a phone's speaker: the take is band-limited when it is conformed, and only that take."""

import math
import shutil
import struct
import wave

import pytest

from srstudio import narration, sketch
from srstudio.sketch import Line
from support.sketch import SK, FakeClient, confirm_stub


def _tone(path, hz: float, rate: int = 48000, seconds: float = 0.5) -> None:
    frames = b"".join(
        struct.pack("<h", int(16000 * math.sin(2 * math.pi * hz * i / rate))) for i in range(int(rate * seconds))
    )
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def _rms(path) -> float:
    with wave.open(str(path)) as w:
        raw = w.readframes(w.getnframes())
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def test_a_line_is_not_on_the_phone_unless_it_says_so():
    assert Line("a", "Hello.").phone is False


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is the conform tool")
@pytest.mark.parametrize("hz", [120.0, 7000.0])
def test_a_phone_take_loses_what_a_phone_speaker_cannot_play(tmp_path, hz):
    src, plain, phone = tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"
    _tone(src, hz)
    narration.conform(src, plain, 0.0, 0.5, 0.5, 0.0)
    narration.conform(src, phone, 0.0, 0.5, 0.5, 0.0, effect=sketch.PHONE_SPEAKER)
    assert _rms(phone) < _rms(plain) / 2


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is the conform tool")
def test_the_speech_band_stays_on_a_phone(tmp_path):
    src, plain, phone = tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"
    _tone(src, 1000.0)
    narration.conform(src, plain, 0.0, 0.5, 0.5, 0.0)
    narration.conform(src, phone, 0.0, 0.5, 0.5, 0.0, effect=sketch.PHONE_SPEAKER)
    assert _rms(phone) > _rms(plain) * 0.7


def test_record_passes_the_phone_only_for_a_phone_line(tmp_path):
    lines = (Line(SK.lines[0].speaker, SK.lines[0].text, phone=True), *SK.lines[1:])
    seen: list[str] = []

    def clip(src, dst, clip_in, clip_out, length, gain, ffmpeg, effect=""):
        seen.append(effect)
        shutil.copyfile(src, dst)
        return length

    sk = sketch.Sketch(SK.slug, SK.title, SK.speakers, lines, SK.beats, SK.end, cast=SK.cast)
    sketch.record(sk, tmp_path, FakeClient(tmp_path), confirm=confirm_stub, conform_clip=clip)
    assert seen[0] == sketch.PHONE_SPEAKER
    assert not any(seen[1:])
