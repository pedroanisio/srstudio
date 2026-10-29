"""The audio modules' refusals are their own SrstudioError subclasses and still the ValueError they always were
(ADR 0034): soundtrack, subtitles, foley and generated."""

from __future__ import annotations

import wave

import pytest

from srstudio import foley, generated, soundtrack, subtitles
from srstudio.errors import SrstudioError


def refused(call, error: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_soundtrack_refusals_are_soundtrack_errors(tmp_path):
    eight_bit = tmp_path / "eight.wav"
    with wave.open(str(eight_bit), "wb") as w:
        w.setparams((1, 1, 8000, 0, "NONE", "not compressed"))
        w.writeframes(b"\x80" * 80)
    refused(lambda: soundtrack.Soundtrack(eight_bit), soundtrack.SoundtrackError, "16-bit PCM")
    refused(lambda: soundtrack.PhonemeStyle(rate=0), soundtrack.SoundtrackError, "rate")
    refused(lambda: soundtrack.PhonemeStyle(lead=-0.1), soundtrack.SoundtrackError, "lead")


def test_a_negative_minimum_page_is_a_subtitle_error():
    refused(lambda: subtitles.chunk_words([], 1.0, min_seconds=-1), subtitles.SubtitleError, "min_seconds")


def test_foley_refusals_are_foley_errors():
    refused(lambda: foley.typing_bursts([], threshold=0), foley.FoleyError, "threshold")
    refused(lambda: foley.keystrokes([0.5], 1.0, rate=100), foley.FoleyError, "rate")
    refused(lambda: foley.buzz([0.0], 1.0, length=5), foley.FoleyError, "length")


def test_generated_refusals_are_generated_errors():
    def item(**kw):
        return generated.Generated(
            **{"id": "line", "kind": "speech", "provider": "p", "model": "m", "prompt": "hi", "cache": "a.wav", **kw}
        )

    refused(lambda: item(id="1 bad"), generated.GeneratedError, "XML name")
    refused(lambda: item(cache="../a.wav"), generated.GeneratedError, "inside")
    refused(lambda: generated.load_clips("nope"), generated.GeneratedError, "not a list")
    refused(lambda: generated.load_clips([{"surprise": 1}]), generated.GeneratedError, "unknown field")


def test_a_clip_missing_a_required_field_is_a_generated_error_naming_it():
    clip = {"generated": {"id": "line"}, "sha256": "0" * 64, "placement": {}}
    refused(lambda: generated.load_clips([clip]), generated.GeneratedError, r"clip.generated: missing field\(s\) \[")
