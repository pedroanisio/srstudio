"""The scene-render resolve provider for ElevenLabs: protocol parse, consent, verified generation.

Offline: the HTTP transports are fakes (tests/fakes.py); parse, decode, verification, the speech
check and the cache are the real code.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from fakes import FakeElevenLabs, ffmpeg_required, make_mp3
from srstudio import provider
from srstudio.provider import ProviderError, format_voice, parse_request, parse_voice
from srstudio.voice import VoiceSettings

SETTINGS = VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.24, speed=0.96)
VOICE = format_voice("bIHbv24MWmeRgasZH58o", SETTINGS)
ENV = {"SRSTUDIO_ALLOW_CLOUD": "1", "ELEVENLABS_API_KEY": "sk-secret"}


def request(tmp_path: Path, **over) -> dict:
    body = {
        "protocol": 1,
        "task": "generate",
        "kind": "speech",
        "id": "line-1",
        "provider": "srstudio-elevenlabs",
        "model": "eleven_multilingual_v2",
        "prompt": "In your chair.",
        "voice": VOICE,
        "language": "en",
        "seed": 52026,
        "sampleRate": 48000,
        "bitDepth": 24,
        "timeline": {"projectDuration": 11.0, "start": 1.2},
        "output": str(tmp_path / "work" / "result.wav"),
        "workdir": str(tmp_path / "work"),
        "baseDir": str(tmp_path),
    }
    body.update(over)
    (tmp_path / "work").mkdir(exist_ok=True)
    return body


@pytest.fixture(scope="module")
def tone(tmp_path_factory) -> bytes:
    pytest.importorskip("wave")
    import shutil

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    return make_mp3(tmp_path_factory.mktemp("mp3") / "tone.mp3")


def run(tmp_path, body, fake=None, env=ENV):
    """Runs the provider on one request; returns (answer, exit code)."""
    factory = provider.client_factory(**fake.transports()) if fake else provider.client_factory()
    return provider.run(json.dumps(body), env=env, make_client=factory)


# -- the voice attribute ------------------------------------------------------------------------------
def test_voice_attribute_round_trips_settings():
    spec = parse_voice(VOICE)
    assert spec.voice_id == "bIHbv24MWmeRgasZH58o" and spec.settings == SETTINGS


@pytest.mark.parametrize(
    "voice,match",
    [
        ("", "voice id"),
        ("bad id!?stability=0.4&similarity_boost=0.7&style=0.1", "voice id"),
        ("abcdefgh1234?stability=0.4&similarity_boost=0.7", "style"),
        ("abcdefgh1234?stability=0.4&similarity_boost=0.7&style=0.1&mood=angry", "unknown"),
        ("abcdefgh1234?stability=0.4&stability=0.5&similarity_boost=0.7&style=0.1", "twice"),
        ("abcdefgh1234?stability=high&similarity_boost=0.7&style=0.1", "number"),
        ("abcdefgh1234?stability=4&similarity_boost=0.7&style=0.1", "0..1"),
        ("abcdefgh1234?stability=0.4&similarity_boost=0.7&style=0.1&use_speaker_boost=yes", "true or false"),
    ],
)
def test_malformed_voice_attributes_are_refused(voice, match):
    with pytest.raises(ProviderError, match=match):
        parse_voice(voice)


def test_a_voice_without_hearings_is_written_exactly_as_before():
    """Every pinned line's request key is its voice attribute: no hearing, no change to it."""
    assert VOICE == format_voice("bIHbv24MWmeRgasZH58o", SETTINGS, heard=())
    assert "heard" not in VOICE and parse_voice(VOICE).heard == ()


def test_operator_hearings_round_trip_through_the_voice_attribute():
    voice = format_voice("bIHbv24MWmeRgasZH58o", SETTINGS, heard=("SAR 1028", "S.R. & 1028?"))
    spec = parse_voice(voice)
    assert spec.heard == ("SAR 1028", "S.R. & 1028?") and spec.settings == SETTINGS
    assert voice.startswith(VOICE + "&")  # the settings first, as before; the hearings after them


@pytest.mark.parametrize("heard", [("",), ("  ",), (1028,), "SAR 1028"])
def test_a_hearing_is_a_non_empty_string_in_a_tuple(heard):
    with pytest.raises(ProviderError, match="hearing"):
        format_voice("bIHbv24MWmeRgasZH58o", SETTINGS, heard=heard)


def test_an_empty_hearing_in_a_voice_attribute_is_refused():
    with pytest.raises(ProviderError, match="hearing"):
        parse_voice(VOICE + "&heard=")


# -- the request --------------------------------------------------------------------------------------
def test_request_parses_into_typed_fields(tmp_path):
    req = parse_request(request(tmp_path))
    assert req.kind == "speech" and req.task == "generate" and req.sample_rate == 48000
    assert req.timeline.start == 1.2 and req.base_dir == str(tmp_path)


@pytest.mark.parametrize(
    "over,match",
    [
        ({"protocol": 2}, "protocol"),
        ({"surprise": 1}, "unknown field"),
        ({"timeline": {"projectDuration": 1, "extra": 0}}, "unknown field"),
        ({"kind": None}, "kind"),
        ({"sampleRate": "48000"}, "sampleRate"),
        ({"task": "dream"}, "task"),
        ({"seed": -1}, "seed"),
        ({"duration": float("nan")}, "duration"),
    ],
)
def test_malformed_requests_are_refused(tmp_path, over, match):
    with pytest.raises(ProviderError, match=match):
        parse_request(request(tmp_path, **over))


def test_a_request_that_is_not_json_is_answered_with_an_error(tmp_path):
    answer, code = provider.run("{not json", env=ENV, make_client=provider.client_factory())
    assert code == 1 and answer["ok"] is False and "JSON" in answer["error"]


# -- consent and kinds -----------------------------------------------------------------------------------
def test_nothing_is_sent_without_consent(tmp_path, tone):
    fake = FakeElevenLabs(tone)
    answer, code = run(tmp_path, request(tmp_path), fake, env={"ELEVENLABS_API_KEY": "k"})
    assert code == 1 and "SRSTUDIO_ALLOW_CLOUD" in answer["error"] and fake.calls == []


@pytest.mark.parametrize(
    "over,match",
    [
        ({"kind": "image"}, "does not make image"),
        ({"kind": "music"}, "does not make music"),
        ({"output": "/x/result.mp3"}, "WAV"),
        ({"prompt": None}, "prompt"),
        ({"voice": None}, "voice"),
    ],
)
def test_requests_it_cannot_serve_are_refused_before_any_call(tmp_path, tone, over, match):
    fake = FakeElevenLabs(tone)
    answer, code = run(tmp_path, request(tmp_path, **over), fake)
    assert code == 1 and match in answer["error"] and fake.calls == []


# -- speech -------------------------------------------------------------------------------------------
@ffmpeg_required
def test_speech_is_generated_heard_and_written_at_the_mix_rate(tmp_path, tone):
    fake = FakeElevenLabs(tone)
    answer, code = run(tmp_path, request(tmp_path, sampleRate=44100), fake)
    assert code == 0 and answer["ok"] is True and answer["version"].startswith("srstudio-elevenlabs")
    with wave.open(str(tmp_path / "work" / "result.wav")) as w:
        assert w.getframerate() == 44100 and w.getnchannels() == 1 and 0.9 < w.getnframes() / 44100 < 1.3
    assert [kind for kind, _ in fake.calls] == ["tts", "stt"]
    tts = fake.calls[0][1]
    assert tts["text"] == "In your chair." and tts["seed"] == 52026 and tts["voice_settings"]["speed"] == 0.96
    assert any("heard" in n for n in answer["notes"])


@ffmpeg_required
@pytest.mark.parametrize("rate", [44100, 48000])
@pytest.mark.parametrize("depth", [16, 24, 32])
def test_speech_is_written_as_the_16_bit_pcm_it_was_decoded_to_whatever_the_mix_depth(tmp_path, tone, rate, depth):
    answer, code = run(tmp_path, request(tmp_path, sampleRate=rate, bitDepth=depth), FakeElevenLabs(tone))
    assert code == 0 and answer["ok"] is True
    with wave.open(str(tmp_path / "work" / "result.wav")) as w:
        assert w.getsampwidth() == 2 and w.getframerate() == rate


@ffmpeg_required
def test_speech_the_recogniser_does_not_hear_as_scripted_fails(tmp_path, tone):
    fake = FakeElevenLabs(tone, heard="In your chairs.")
    answer, code = run(tmp_path, request(tmp_path), fake)
    assert code == 1 and "heard" in answer["error"] and "change @seed" in answer["error"]
    assert not (tmp_path / "work" / "result.wav").exists()


@ffmpeg_required
def test_a_hearing_the_operator_approved_passes_and_another_still_fails(tmp_path, tone):
    approved = format_voice("bIHbv24MWmeRgasZH58o", SETTINGS, heard=("In your chairs.",))
    answer, code = run(tmp_path, request(tmp_path, voice=approved), FakeElevenLabs(tone, heard="In your chairs."))
    assert code == 0 and (tmp_path / "work" / "result.wav").exists(), answer
    other = tmp_path / "other"  # its own cache: a fresh take, heard otherwise
    other.mkdir()
    answer, code = run(other, request(other, voice=approved), FakeElevenLabs(tone, heard="In your hair."))
    assert code == 1 and "In your hair" in answer["error"] and not (other / "work" / "result.wav").exists()


@ffmpeg_required
def test_a_hearing_does_not_change_the_take_so_approving_one_costs_nothing(tmp_path, tone):
    fake = FakeElevenLabs(tone, heard="In your chairs.")
    assert run(tmp_path, request(tmp_path), fake)[1] == 1  # paid, cached, refused
    approved = format_voice("bIHbv24MWmeRgasZH58o", SETTINGS, heard=("In your chairs.",))
    assert run(tmp_path, request(tmp_path, voice=approved), fake)[1] == 0
    assert [kind for kind, _ in fake.calls] == ["tts", "stt"]  # the same take and transcript, from the cache


@ffmpeg_required
def test_speech_is_cached_so_a_second_resolve_costs_nothing(tmp_path, tone):
    fake = FakeElevenLabs(tone)
    run(tmp_path, request(tmp_path), fake)
    (tmp_path / "work" / "result.wav").unlink()
    answer, code = run(tmp_path, request(tmp_path, timeline={"projectDuration": 9.0, "start": 3.0}), fake)
    assert code == 0 and (tmp_path / "work" / "result.wav").exists()
    assert [kind for kind, _ in fake.calls] == ["tts", "stt"]  # moved on the timeline: nothing paid again


@ffmpeg_required
def test_a_corrupt_cached_timing_file_is_an_answer_not_a_traceback(tmp_path, tone):
    fake = FakeElevenLabs(tone)
    run(tmp_path, request(tmp_path), fake)
    timing = next(p for p in (tmp_path / "assets" / "elevenlabs").glob("*.json") if not p.name.startswith("stt-"))
    timing.write_text("[]")
    answer, code = run(tmp_path, request(tmp_path), fake)
    assert code == 1 and answer["ok"] is False and "not a JSON object" in answer["error"]


@ffmpeg_required
def test_the_cache_folder_follows_the_environment(tmp_path, tone):
    fake = FakeElevenLabs(tone)
    run(tmp_path, request(tmp_path), fake, env={**ENV, "SRSTUDIO_ELEVENLABS_CACHE": str(tmp_path / "shared")})
    assert list((tmp_path / "shared").glob("*.mp3"))
    assert not (tmp_path / "assets" / "elevenlabs").exists()


@ffmpeg_required
def test_default_cache_is_inside_the_project_and_holds_no_key(tmp_path, tone):
    run(tmp_path, request(tmp_path), FakeElevenLabs(tone))
    cache = tmp_path / "assets" / "elevenlabs"
    assert list(cache.glob("*.mp3"))
    assert all("sk-secret" not in p.read_text() for p in cache.glob("*.json"))


def test_missing_key_for_an_uncached_line_is_an_error(tmp_path, tone):
    answer, code = run(tmp_path, request(tmp_path), FakeElevenLabs(tone), env={"SRSTUDIO_ALLOW_CLOUD": "1"})
    assert code == 1 and "ELEVENLABS_API_KEY" in answer["error"]


# -- sound effects ----------------------------------------------------------------------------------------
@ffmpeg_required
def test_sound_effect_is_generated_at_its_duration(tmp_path, tone):
    fake = FakeElevenLabs(tone, effect_mp3=tone)
    body = request(
        tmp_path, kind="sound-effect", model=provider.SFX_MODEL, voice=None, prompt="a chair squeak", duration=1.0
    )
    answer, code = run(tmp_path, body, fake)
    assert code == 0, answer
    assert fake.calls == [("sfx", {"text": "a chair squeak", "duration_seconds": 1.0, "prompt_influence": 0.6})]


@pytest.mark.parametrize(
    "over,match",
    [
        ({"duration": None}, "duration"),
        ({"duration": 40.0}, "duration"),
        ({"model": "eleven_multilingual_v2"}, provider.SFX_MODEL),
        ({"voice": VOICE}, "voice"),
    ],
)
def test_malformed_sound_effect_requests_are_refused(tmp_path, tone, over, match):
    fake = FakeElevenLabs(tone, effect_mp3=tone)
    base = dict(kind="sound-effect", model=provider.SFX_MODEL, voice=None, prompt="a squeak", duration=1.0)
    answer, code = run(tmp_path, request(tmp_path, **{**base, **over}), fake)
    assert code == 1 and match in answer["error"] and fake.calls == []


@ffmpeg_required
def test_a_silent_or_wrong_length_effect_is_rejected(tmp_path, tone):
    fake = FakeElevenLabs(tone, effect_mp3=tone)  # the tone lasts 1.05 s, not 3 s
    body = request(tmp_path, kind="sound-effect", model=provider.SFX_MODEL, voice=None, prompt="x", duration=3.0)
    answer, code = run(tmp_path, body, fake)
    assert code == 1 and "duration" in answer["error"]


# -- transcription ------------------------------------------------------------------------------------------
def transcribe_request(tmp_path, wav: Path, **over):
    base = dict(
        task="transcribe",
        kind="captions",
        model=provider.STT_MODEL,
        voice=None,
        prompt=None,
        input=str(wav),
        inputSha256="0" * 64,
        output=str(tmp_path / "work" / "result.json"),
    )
    return request(tmp_path, **{**base, **over})


def test_transcription_writes_word_timed_segments(tmp_path):
    wav = tmp_path / "mix.wav"
    wav.write_bytes(b"RIFF....WAVE")
    fake = FakeElevenLabs(b"", heard="No. Just the chair.")
    answer, code = run(tmp_path, transcribe_request(tmp_path, wav), fake)
    assert code == 0, answer
    out = json.loads((tmp_path / "work" / "result.json").read_text())
    (segment,) = out["segments"]
    assert segment["text"] == "No. Just the chair."
    assert [w["text"] for w in segment["words"]] == ["No.", "Just", "the", "chair."]  # spacing is not a word
    assert segment["start"] == segment["words"][0]["start"] and segment["end"] == segment["words"][-1]["end"]
    assert fake.calls == [("stt", {"model_id": "scribe_v1", "language_code": "en"})]


@pytest.mark.parametrize(
    "over,match", [({"input": None}, "input"), ({"output": "/x/r.vtt"}, "JSON"), ({"model": "whisper"}, "scribe_v1")]
)
def test_malformed_transcription_requests_are_refused(tmp_path, over, match):
    wav = tmp_path / "mix.wav"
    wav.write_bytes(b"RIFF")
    fake = FakeElevenLabs(b"")
    answer, code = run(tmp_path, transcribe_request(tmp_path, wav, **over), fake)
    assert code == 1 and match in answer["error"] and fake.calls == []


def test_language_tags_reduce_to_their_primary_subtag(tmp_path):
    wav = tmp_path / "mix.wav"
    wav.write_bytes(b"RIFF")
    fake = FakeElevenLabs(b"", heard="Olá.")
    run(tmp_path, transcribe_request(tmp_path, wav, language="pt-BR"), fake)
    assert fake.calls[0][1]["language_code"] == "pt"


# -- the process -----------------------------------------------------------------------------------------
def test_main_prints_one_json_answer_as_its_last_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(request(tmp_path, kind="image"))))
    monkeypatch.setenv("SRSTUDIO_ALLOW_CLOUD", "1")
    assert provider.main() == 1
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(last) == {"ok": False, "error": "srstudio-elevenlabs does not make image"}
