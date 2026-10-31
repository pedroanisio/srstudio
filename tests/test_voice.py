"""The ElevenLabs voice client: typed parse, semantic checks, failure path, no retries, cache.

No network: the transport is injected. Audio is a real MP3 made by ffmpeg, so decoding and the
duration cross-check run for real.
"""

import base64
import json
import math
import shutil
import subprocess

import pytest

from srstudio.voice import Alignment, ElevenLabsClient, Speech, Voice, VoiceOutputError, VoiceSettings, parse_response
from support.voice import Binary

ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required to decode speech")
TEXT = "In your chair."
VOICE = Voice(role="candidate", id="bIHbv24MWmeRgasZH58o", name="Will")
SETTINGS = VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.24, speed=1.0)


def alignment(text=TEXT, step=0.07):
    n = len(text)
    return {
        "characters": list(text),
        "character_start_times_seconds": [round(i * step, 3) for i in range(n)],
        "character_end_times_seconds": [round((i + 1) * step, 3) for i in range(n)],
    }


@pytest.fixture(scope="module")
def mp3(tmp_path_factory) -> bytes:
    """One second of a 220 Hz tone as MP3: about as long as ``alignment()`` says the line is."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    out = tmp_path_factory.mktemp("mp3") / "tone.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=1.05",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(out),
        ],
        check=True,
    )
    return out.read_bytes()


def response(audio=b"ID3fake", text=TEXT, **over):
    body = {
        "audio_base64": base64.b64encode(audio).decode(),
        "alignment": alignment(text),
        "normalized_alignment": alignment(" " + text + " "),
    }
    body.update(over)
    return body


# -- typed parse ------------------------------------------------------------------------------------
def test_valid_response_parses_into_typed_speech():
    speech = parse_response(response(), TEXT)
    assert isinstance(speech, Speech) and isinstance(speech.alignment, Alignment)
    assert speech.alignment.text == TEXT
    assert speech.audio == b"ID3fake"
    assert math.isclose(speech.alignment.end, len(TEXT) * 0.07)


@pytest.mark.parametrize("bad", [None, [], "audio", 42])
def test_non_object_response_is_rejected(bad):
    with pytest.raises(VoiceOutputError, match="object"):
        parse_response(bad, TEXT)


def test_unknown_top_level_field_is_rejected():
    with pytest.raises(VoiceOutputError, match="unknown field"):
        parse_response(response(debug_text="I am the real script"), TEXT)


@pytest.mark.parametrize("missing", ["audio_base64", "alignment"])
def test_missing_required_field_is_rejected(missing):
    body = response()
    del body[missing]
    with pytest.raises(VoiceOutputError, match=missing):
        parse_response(body, TEXT)


def test_null_quality_check_is_accepted():
    """The live API sends ``quality_check: null`` (as in all 26 shipped timing files)."""
    assert parse_response(response(quality_check=None), TEXT).alignment.text == TEXT


@pytest.mark.parametrize("flag", [{"passed": False}, "low", True, []])
def test_a_raised_quality_check_is_rejected(flag):
    with pytest.raises(VoiceOutputError, match="quality_check"):
        parse_response(response(quality_check=flag), TEXT)


def test_unknown_alignment_field_is_rejected():
    body = response()
    body["alignment"]["phonemes"] = []
    with pytest.raises(VoiceOutputError, match="unknown field"):
        parse_response(body, TEXT)


# -- semantic validation ---------------------------------------------------------------------------
def test_speech_of_a_different_text_is_rejected():
    """The provider aligned other words than the ones requested: the line would be wrong on screen."""
    with pytest.raises(VoiceOutputError, match="does not match"):
        parse_response(response(text="In my chair."), TEXT)


def test_truncated_alignment_is_rejected():
    body = response()
    for key in body["alignment"]:
        body["alignment"][key] = body["alignment"][key][:5]
    with pytest.raises(VoiceOutputError, match="does not match"):
        parse_response(body, TEXT)


def test_alignment_arrays_of_unequal_length_are_rejected():
    body = response()
    body["alignment"]["character_end_times_seconds"].pop()
    with pytest.raises(VoiceOutputError, match="length"):
        parse_response(body, TEXT)


@pytest.mark.parametrize(
    "field,index,value,match",
    [
        ("character_start_times_seconds", 3, -0.5, "negative"),
        ("character_start_times_seconds", 3, float("nan"), "finite"),
        ("character_end_times_seconds", 3, float("inf"), "finite"),
        ("character_start_times_seconds", 4, 0.0, "order"),  # goes backwards
        ("character_end_times_seconds", 2, 0.01, "before its start"),  # ends before it starts
        ("character_start_times_seconds", 2, "0.2", "number"),
    ],
)
def test_impossible_timings_are_rejected(field, index, value, match):
    body = response()
    body["alignment"][field][index] = value
    with pytest.raises(VoiceOutputError, match=match):
        parse_response(body, TEXT)


@pytest.mark.parametrize("payload,match", [("%%%not base64%%%", "base64"), ("", "empty")])
def test_bad_or_empty_audio_is_rejected(payload, match):
    with pytest.raises(VoiceOutputError, match=match):
        parse_response(response(audio_base64=payload), TEXT)


def test_characters_must_be_single_strings():
    body = response()
    body["alignment"]["characters"][0] = "In"
    with pytest.raises(VoiceOutputError, match="character"):
        parse_response(body, TEXT)


# -- client: failure path, bounds, cache ------------------------------------------------------------
class Transport:
    def __init__(self, body=None, exc=None):
        self.body, self.exc, self.calls = body, exc, []

    def __call__(self, url, payload, headers):
        self.calls.append((url, payload, headers))
        if self.exc:
            raise self.exc
        return self.body, "req-123"


@ffmpeg
def test_client_synthesises_decodes_and_caches(tmp_path, mp3):
    transport = Transport(response(audio=mp3))
    client = ElevenLabsClient(tmp_path / "cache", key="sk-secret", transport=transport)
    line = client.synthesize(TEXT, VOICE, SETTINGS)
    assert line.text == TEXT and line.voice == VOICE
    assert line.wav.exists() and 0.9 < line.duration < 1.3
    import wave

    with wave.open(str(line.wav)) as w:  # a real header, not the piped placeholder
        assert w.getframerate() == 48000 and w.getnchannels() == 1
        assert abs(w.getnframes() / 48000 - line.duration) < 1e-6
    assert len(line.samples()) == round(line.duration * 48000)
    assert len(transport.calls) == 1
    again = client.synthesize(TEXT, VOICE, SETTINGS)  # cached: no second paid request
    assert len(transport.calls) == 1 and again.timing_file == line.timing_file
    stored = line.timing_file.read_text()
    assert "sk-secret" not in stored and "audio_base64" not in stored
    meta = json.loads(stored)
    assert meta["request_id"] == "req-123" and meta["voice_name"] == "Will"


@ffmpeg
def test_cached_files_are_reverified_on_read(tmp_path, mp3):
    client = ElevenLabsClient(tmp_path / "cache", key="k", transport=Transport(response(audio=mp3)))
    line = client.synthesize(TEXT, VOICE, SETTINGS)
    meta = json.loads(line.timing_file.read_text())
    meta["alignment"]["characters"][0] = "X"  # tampered cache
    line.timing_file.write_text(json.dumps(meta))
    with pytest.raises(VoiceOutputError, match="does not match"):
        ElevenLabsClient(tmp_path / "cache", key="", transport=Transport()).synthesize(TEXT, VOICE, SETTINGS)


@pytest.mark.parametrize("stored", ["[1, 2]", '"text"', "{not json", ""])
def test_a_cached_timing_file_that_is_not_an_object_is_refused(tmp_path, mp3, stored):
    client = ElevenLabsClient(tmp_path / "cache", key="k", transport=Transport(response(audio=mp3)))
    client.synthesize(TEXT, VOICE, SETTINGS).timing_file.write_text(stored)
    with pytest.raises(VoiceOutputError, match="not a JSON object"):
        ElevenLabsClient(tmp_path / "cache", key="", transport=Transport()).synthesize(TEXT, VOICE, SETTINGS)


@pytest.mark.parametrize("stored", ["[1, 2]", "{not json", ""])
def test_a_cached_transcript_record_that_is_not_an_object_is_refused(tmp_path, stored):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    ElevenLabsClient(tmp_path / "c", key="k", multipart_transport=Multipart(transcript("In your chair."))).transcribe(
        wav
    )
    (record,) = (tmp_path / "c").glob("stt-*.json")
    record.write_text(stored)
    with pytest.raises(VoiceOutputError, match="not a JSON object"):
        ElevenLabsClient(tmp_path / "c", key="").transcribe(wav)


def test_transport_failure_is_not_retried(tmp_path):
    transport = Transport(exc=RuntimeError("HTTP 500"))
    client = ElevenLabsClient(tmp_path, key="k", transport=transport)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.synthesize(TEXT, VOICE, SETTINGS)
    assert len(transport.calls) == 1


def test_invalid_output_writes_nothing_to_the_cache(tmp_path):
    client = ElevenLabsClient(tmp_path, key="k", transport=Transport(response(text="Something else.")))
    with pytest.raises(VoiceOutputError):
        client.synthesize(TEXT, VOICE, SETTINGS)
    assert list(tmp_path.iterdir()) == []


def test_missing_key_for_uncached_line_is_a_clear_error(tmp_path):
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        ElevenLabsClient(tmp_path, key="", transport=Transport(response())).synthesize(TEXT, VOICE, SETTINGS)


@ffmpeg
def test_audio_much_longer_than_its_alignment_is_rejected(tmp_path, mp3):
    """One second of audio for a line the alignment says lasts 0.07 s × 3 characters."""
    body = response(audio=mp3, text="Hi.")
    client = ElevenLabsClient(tmp_path, key="k", transport=Transport(body))
    with pytest.raises(VoiceOutputError, match="duration"):
        client.synthesize("Hi.", VOICE, SETTINGS)


@ffmpeg
def test_silent_audio_is_rejected(tmp_path):
    out = tmp_path / "silence.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "1.0",
            "-c:a",
            "libmp3lame",
            str(out),
        ],
        check=True,
    )
    client = ElevenLabsClient(tmp_path / "c", key="k", transport=Transport(response(audio=out.read_bytes())))
    with pytest.raises(VoiceOutputError, match="silent"):
        client.synthesize(TEXT, VOICE, SETTINGS)


def test_settings_are_range_checked():
    with pytest.raises(ValueError):
        VoiceSettings(stability=1.5, similarity_boost=0.75, style=0.2, speed=1.0)
    with pytest.raises(ValueError):
        VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.2, speed=3.0)


# -- sound effects -----------------------------------------------------------------------------------
from srstudio.voice import Transcript, TranscriptMismatch, check_transcript, parse_transcript  # noqa: E402


@ffmpeg
def test_sound_effect_is_generated_verified_and_cached(tmp_path, mp3):
    binary = Binary(mp3)
    client = ElevenLabsClient(tmp_path, key="k", binary_transport=binary)
    clip = client.sound_effect("a squeaky office chair", 1.0)
    assert clip.wav.exists() and abs(clip.duration - 1.0) < 0.2
    assert binary.calls[0][1] == {"text": "a squeaky office chair", "duration_seconds": 1.0, "prompt_influence": 0.6}
    assert "sound-generation" in binary.calls[0][0]
    client.sound_effect("a squeaky office chair", 1.0)
    assert len(binary.calls) == 1  # cached
    assert "k" not in json.loads(clip.file.read_text()).get("request", {}).values()


@pytest.mark.parametrize("seconds", [0.1, 0.49, 23, float("nan")])
def test_sound_effect_length_outside_the_api_range_is_refused(tmp_path, seconds):
    with pytest.raises(ValueError):
        ElevenLabsClient(tmp_path, key="k", binary_transport=Binary(b"x")).sound_effect("thud", seconds)


@ffmpeg
def test_sound_effect_of_the_wrong_length_is_rejected(tmp_path, mp3):
    """Asked for 3 s, got about 1 s: the model ignored the request."""
    client = ElevenLabsClient(tmp_path / "c", key="k", binary_transport=Binary(mp3))
    with pytest.raises(VoiceOutputError, match="duration"):
        client.sound_effect("a long creak", 3.0)
    assert not (tmp_path / "c").exists()


@pytest.mark.parametrize("audio,match", [(b"", "empty"), (b"<html>error</html>", "decode")])
def test_empty_or_undecodable_sound_effect_is_rejected(tmp_path, audio, match):
    client = ElevenLabsClient(tmp_path, key="k", binary_transport=Binary(audio))
    with pytest.raises(VoiceOutputError, match=match):
        client.sound_effect("thud", 1.0)


def test_sound_effect_transport_failure_is_not_retried(tmp_path):
    binary = Binary(exc=RuntimeError("HTTP 429"))
    with pytest.raises(RuntimeError):
        ElevenLabsClient(tmp_path, key="k", binary_transport=binary).sound_effect("thud", 1.0)
    assert len(binary.calls) == 1


# -- speech-to-text check ----------------------------------------------------------------------------
def transcript(text="No. Just the chair.", **over):
    words = [
        {"text": w, "start": i * 0.2, "end": i * 0.2 + 0.15, "type": "word", "speaker_id": "speaker_0", "logprob": -0.1}
        for i, w in enumerate(text.split())
    ]
    body = {
        "language_code": "eng",
        "language_probability": 0.99,
        "text": text,
        "words": words,
        "transcription_id": "t-1",
    }
    body.update(over)
    return body


def test_transcript_parses_into_typed_words():
    t = parse_transcript(transcript())
    assert isinstance(t, Transcript) and t.text == "No. Just the chair." and len(t.words) == 4


@pytest.mark.parametrize(
    "body,match",
    [
        ([], "object"),
        (transcript(secret="x"), "unknown field"),
        ({"language_code": "en", "language_probability": 1, "words": []}, "text"),
        (transcript(language_probability=1.7), "language_probability"),
        (transcript(words=[{"text": "No", "start": 0.5, "end": 0.2, "type": "word"}]), "ends before"),
        (transcript(words=[{"text": "No", "start": 0, "end": 0.2, "type": "word", "mood": "x"}]), "unknown field"),
        (transcript(words=[{"text": "No", "start": -0.3, "end": 0.2, "type": "word"}]), "word 0 starts before"),
        (
            transcript(
                words=[
                    {"text": "No.", "start": 0.4, "end": 0.6, "type": "word"},
                    {"text": " ", "start": 0.6, "end": 0.6, "type": "spacing"},
                    {"text": "Just", "start": 0.1, "end": 0.3, "type": "word"},
                ]
            ),
            "word 2 starts before word 1",
        ),
    ],
)
def test_malformed_transcripts_are_rejected(body, match):
    with pytest.raises(VoiceOutputError, match=match):
        parse_transcript(body)


@pytest.mark.parametrize(
    "heard, script",
    [
        ("It was $187", "It was a hundred and eighty-seven dollars."),
        ("It was 187 dollars.", "It was one hundred eighty-seven dollars."),
        ("It was $250.", "It was two hundred and fifty dollars."),
        ("It was a hundred dollars.", "It was $100."),
    ],
)
def test_a_dollar_amount_is_the_same_words_however_the_recogniser_writes_it(heard, script):
    check_transcript(parse_transcript(transcript(heard)), script)


@pytest.mark.parametrize(
    "heard, script",
    [
        ("It was $186", "It was a hundred and eighty-seven dollars."),
        ("It was 187 pounds.", "It was a hundred and eighty-seven dollars."),
        ("It was $287", "It was a hundred and eighty-seven dollars."),
        ("It was $187.40", "It was a hundred and eighty-seven dollars."),
    ],
)
def test_another_amount_or_another_money_is_still_a_mismatch(heard, script):
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript(heard)), script)


@pytest.mark.parametrize(
    "heard", ["No. Just the chair.", "no just the chair", "No, just the chair!", "No… Just the chair."]
)
def test_transcript_matching_the_script_passes(heard):
    check_transcript(parse_transcript(transcript(heard)), "No. Just the chair.")


def test_spelled_and_digit_numbers_are_equivalent():
    check_transcript(
        parse_transcript(transcript("Where do you see yourself in 5 years?")),
        "Where do you see yourself in five years?",
    )


@pytest.mark.parametrize(
    ("heard", "script"),
    [
        ("12%. Please smile harder", "Twelve percent. Please smile harder."),
        ("Your well-being is our top priority.", "Your wellbeing is our top priority."),
        ("Log in to the well being portal.", "Log in to the wellbeing portal."),
    ],
)
def test_a_percent_sign_and_a_compound_split_or_joined_read_as_the_same_words(heard, script):
    check_transcript(parse_transcript(transcript(heard)), script)


@pytest.mark.parametrize("heard", ["12. Please smile harder", "Your well-being is our top party.", "Your wellbeings"])
def test_a_compound_still_has_to_carry_every_scripted_letter(heard):
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript(heard)), "Your wellbeing is our top priority.")


def test_a_hearing_the_operator_accepted_passes_and_nothing_else_does():
    reel = parse_transcript(transcript("Reel is also premium."))
    with pytest.raises(TranscriptMismatch):
        check_transcript(reel, "Real is also premium.")
    check_transcript(reel, "Real is also premium.", accepted=("Reel is also premium.",))
    check_transcript(reel, "Real is also premium.", accepted=("reel, is also premium",))  # the same normalisation
    for other in (("Real is premium.",), ("Reel is also premium too.",), ()):
        with pytest.raises(TranscriptMismatch, match="Real is also premium"):
            check_transcript(reel, "Real is also premium.", accepted=other)


@pytest.mark.parametrize(
    ("heard", "script"),
    [
        ("SR 1028?", "S-R... one-oh-two-eight?"),  # a code read digit by digit, 0 as "oh"
        ("S-R, 1028?", "S-R... one-oh-two-eight?"),
        ("SR one zero two eight?", "S-R... 1028?"),  # 0 as "zero", the digits on the script's side
        ("S R 1028", "S R one thousand twenty eight"),  # the cardinal reading still matches
        ("Room 1 0 4.", "Room 104."),
        ("Code 007.", "Code oh oh seven."),  # leading zeros are read too
    ],
)
def test_a_digit_string_matches_its_digit_by_digit_reading(heard, script):
    check_transcript(parse_transcript(transcript(heard)), script)


@pytest.mark.parametrize(
    ("heard", "script"),
    [
        ("SR 1029?", "S-R... one-oh-two-eight?"),  # another digit
        ("SAR 1028?", "S-R... one-oh-two-eight?"),  # the letters misheard
        ("SR 10280?", "S-R... one-oh-two-eight?"),  # an extra digit
        ("SR 102?", "S-R... one-oh-two-eight?"),  # a missing digit
        ("SR 1028?", "S-R... one-two-eight?"),  # the script's digits lack the zero
        ("SR 1028?", "S-R... one-oh-two-eight-oh?"),
        ("SR 10 28?", "S-R... one-thousand-twenty-eight?"),  # two numbers are not one cardinal
        ("SR one oh two eight?", "S-R... one thousand twenty eight?"),  # spelled digits are not the cardinal
    ],
)
def test_a_wrong_digit_string_is_still_refused(heard, script):
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript(heard)), script)


def test_a_superscript_digit_is_a_mismatch_not_a_crash():
    """``str.isdigit`` holds for "²", which ``int`` cannot read: a heard superscript is a word that does not match."""
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript("Room 4²")), "Room four two")


def test_a_transcript_with_too_many_numbers_to_compare_is_refused_not_explored():
    """Each digit string has up to three readings, so their combinations are bounded before any is built."""
    flood = " ".join(["10"] * 40)
    with pytest.raises(TranscriptMismatch, match="too many numbers"):
        check_transcript(parse_transcript(transcript(flood)), " ".join(["ten"] * 40))


@pytest.mark.parametrize("heard", ["No. Just the chairs.", "Just the chair.", "No. Just the chair. Thank you.", ""])
def test_transcript_that_differs_from_the_script_fails(heard):
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript(heard)), "No. Just the chair.")


class Multipart:
    def __init__(self, body):
        self.body, self.calls = body, []

    def __call__(self, url, fields, files, headers):
        self.calls.append((url, fields, files, headers))
        return self.body, "stt-1"


def test_transcribe_sends_the_audio_once_and_returns_a_typed_transcript(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    multipart = Multipart(transcript("In your chair."))
    t = ElevenLabsClient(tmp_path, key="k", multipart_transport=multipart).transcribe(wav)
    assert t.text == "In your chair."
    url, fields, files, headers = multipart.calls[0]
    assert "speech-to-text" in url and fields["model_id"] == "scribe_v1" and files["file"][1] == b"RIFF....WAVE"
    assert len(multipart.calls) == 1


def test_transcript_audio_duration_is_accepted_when_a_real_length():
    assert parse_transcript(transcript(audio_duration_secs=1.09)).text == "No. Just the chair."


@pytest.mark.parametrize("value", [-1, "1.0", float("nan")])
def test_transcript_audio_duration_must_be_a_non_negative_number(value):
    with pytest.raises(VoiceOutputError, match="audio_duration_secs"):
        parse_transcript(transcript(audio_duration_secs=value))


# -- speech-to-text cache ------------------------------------------------------------------------------
def test_transcripts_are_cached_by_audio_and_language(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    multipart = Multipart(transcript("In your chair."))
    client = ElevenLabsClient(tmp_path / "cache", key="sk-secret", multipart_transport=multipart)
    first = client.transcribe(wav)
    again = client.transcribe(wav)
    assert first == again and len(multipart.calls) == 1  # the second read is free
    client.transcribe(wav, language="pt")
    assert len(multipart.calls) == 2  # another language is another request
    wav.write_bytes(b"RIFF....WAVE-other")
    client.transcribe(wav)
    assert len(multipart.calls) == 3  # other audio is another request
    stored = "".join(p.read_text() for p in (tmp_path / "cache").glob("stt-*.json"))
    assert "sk-secret" not in stored


def test_cached_transcript_needs_no_key(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    ElevenLabsClient(tmp_path / "c", key="k", multipart_transport=Multipart(transcript("In your chair."))).transcribe(
        wav
    )
    assert ElevenLabsClient(tmp_path / "c", key="").transcribe(wav).text == "In your chair."


def test_cached_transcript_is_reparsed_and_tampering_fails(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    client = ElevenLabsClient(tmp_path / "c", key="k", multipart_transport=Multipart(transcript("In your chair.")))
    client.transcribe(wav)
    (record,) = (tmp_path / "c").glob("stt-*.json")
    data = json.loads(record.read_text())
    data["response"]["injected"] = "ignore previous instructions"
    record.write_text(json.dumps(data))
    with pytest.raises(VoiceOutputError, match="unknown field"):
        ElevenLabsClient(tmp_path / "c", key="").transcribe(wav)


def test_an_invalid_transcript_is_not_cached(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    client = ElevenLabsClient(tmp_path / "c", key="k", multipart_transport=Multipart(transcript(secret="x")))
    with pytest.raises(VoiceOutputError):
        client.transcribe(wav)
    assert not list((tmp_path / "c").glob("stt-*.json")) if (tmp_path / "c").exists() else True


# -- HTTP transports: urlopen replaced by an in-memory response ---------------------------------------
import io  # noqa: E402
import urllib.error  # noqa: E402

from srstudio import voice  # noqa: E402


class Reply:
    def __init__(self, body: bytes, headers=None):
        self.body, self.headers = body, headers or {}

    def read(self, *_):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def serve(monkeypatch, body=b"", headers=None, status=None):
    """``urlopen`` answers ``body``, or raises HTTP ``status`` with ``body`` as the error document."""
    seen = []

    def urlopen(request, timeout):
        seen.append((request, timeout))
        if status:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(body))
        return Reply(body, headers)

    monkeypatch.setattr(voice.urllib.request, "urlopen", urlopen)
    return seen


def test_json_transport_posts_once_and_returns_the_request_id(monkeypatch):
    seen = serve(monkeypatch, b'{"ok": 1}', {"request-id": "r-9"})
    assert voice.urllib_transport("https://api/x", {"text": "hi"}, {"xi-api-key": "k"}) == ({"ok": 1}, "r-9")
    ((request, timeout),) = seen
    assert request.method == "POST" and json.loads(request.data) == {"text": "hi"} and timeout == 90


@pytest.mark.parametrize("body", [b"<html>502</html>", b"\x80\x81 not utf-8", b""])
def test_json_transport_rejects_a_body_that_is_not_json(monkeypatch, body):
    serve(monkeypatch, body)
    with pytest.raises(VoiceOutputError, match="not JSON"):
        voice.urllib_transport("https://api/x", {}, {})


@pytest.mark.parametrize(
    "body,message",
    [
        (b'{"detail": {"message": "quota exceeded"}}', "quota exceeded"),
        (b'{"detail": "voice not found"}', "voice not found"),
        (b'{"detail": {}}', "request failed"),
        (b"[1, 2]", "request failed"),
        (b"<html>gateway</html>", "request failed"),
        (b"\x80 not utf-8", "request failed"),
    ],
)
@pytest.mark.parametrize("kind", ["json", "binary", "multipart"])
def test_http_errors_carry_only_the_provider_message(monkeypatch, body, message, kind):
    serve(monkeypatch, body, status=429)
    call = {
        "json": lambda: voice.urllib_transport("https://api/x", {}, {}),
        "binary": lambda: voice.urllib_binary_transport("https://api/x", {}, {}),
        "multipart": lambda: voice.urllib_multipart_transport("https://api/x", {}, {}, {}),
    }[kind]
    with pytest.raises(RuntimeError, match=f"^ElevenLabs HTTP 429: {message}$") as err:
        call()
    assert not isinstance(err.value, VoiceOutputError)


def test_binary_transport_returns_the_audio_bytes(monkeypatch):
    seen = serve(monkeypatch, b"ID3audio", {"x-request-id": "x-1"})
    assert voice.urllib_binary_transport("https://api/sfx", {"text": "thud"}, {}) == (b"ID3audio", "x-1")
    assert seen[0][1] == 120


def test_multipart_transport_encodes_fields_and_files(monkeypatch):
    seen = serve(monkeypatch, b'{"text": "hi"}')
    body, request_id = voice.urllib_multipart_transport(
        "https://api/stt", {"model_id": "scribe_v1"}, {"file": ("a.wav", b"RIFFdata", "audio/wav")}, {"xi-api-key": "k"}
    )
    assert body == {"text": "hi"} and request_id is None
    request = seen[0][0]
    boundary = request.get_header("Content-type").split("boundary=")[1]
    data = request.data
    assert data.startswith(f"--{boundary}\r\n".encode()) and data.endswith(f"--{boundary}--\r\n".encode())
    assert b'name="model_id"\r\n\r\nscribe_v1\r\n' in data
    assert b'name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\nRIFFdata\r\n' in data


@pytest.mark.parametrize("body", [b"oops", b"\x80\x81"])
def test_multipart_transport_rejects_a_body_that_is_not_json(monkeypatch, body):
    serve(monkeypatch, body)
    with pytest.raises(VoiceOutputError, match="not JSON"):
        voice.urllib_multipart_transport("https://api/stt", {}, {}, {})


# -- remaining rejection paths ---------------------------------------------------------------------------
def wav_of(samples, rate=48000):
    import array
    import wave

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(array.array("h", samples).tobytes())
    return out.getvalue()


@pytest.mark.parametrize(
    "data,match",
    [
        ("chars", "must be an object"),
        ({"characters": list("Hi"), "character_start_times_seconds": [0, 1]}, "character_end_times_seconds"),
        ({**alignment(), "characters": "In your chair."}, "characters is missing or not a list"),
    ],
)
def test_alignment_that_is_not_three_lists_is_rejected(data, match):
    with pytest.raises(VoiceOutputError, match=match):
        Alignment.parse(data)


def test_audio_that_is_not_a_base64_string_is_rejected():
    with pytest.raises(VoiceOutputError, match="audio_base64 is not a string"):
        parse_response(response(audio_base64=["SUQz"]), TEXT)


@pytest.mark.parametrize(
    "body,match",
    [
        ({**transcript(), "text": ["No."]}, "must be strings"),
        (transcript(language_code=None), "must be strings"),
        (transcript(words="No. Just the chair."), "words must be a list"),
        (transcript(words=["No."]), "word 0 is not an object"),
        (transcript(words=[{"start": 0, "end": 0.2, "type": "word"}]), "word 0 lacks text or type"),
        (transcript(words=[{"text": "No", "start": 0, "end": 0.2, "type": 1}]), "word 0 lacks text or type"),
        (transcript(words=[{"text": "No", "start": True, "end": 0.2, "type": "word"}]), "word 0 start"),
    ],
)
def test_transcripts_with_wrongly_typed_fields_are_rejected(body, match):
    with pytest.raises(VoiceOutputError, match=match):
        parse_transcript(body)


@pytest.mark.parametrize(
    "heard,script",
    [
        ("I'm 25.", "I'm twenty five."),
        ("Room 40.", "Room forty."),
        ("Since 1999!", "since 1999"),  # beyond the scripts' range: compared digit by digit
        ("Rock '' roll", "rock roll"),  # a bare apostrophe is no word
        ("Great point, Mr. Lamp.", "Great point, Mister Lamp."),  # a spoken title is written abbreviated
        ("Thanks, Mrs Hill and Dr. Ng.", "Thanks, Missus Hill and Doctor Ng."),
    ],
)
def test_number_and_apostrophe_normalisation(heard, script):
    check_transcript(parse_transcript(transcript(heard)), script)


def test_an_abbreviated_title_is_still_the_word_it_stands_for():
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript("Great point, Mr. Lamp.")), "Great point, Master Lamp.")


def test_a_year_read_in_pairs_does_not_match_the_cardinal_its_digits_spell():
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript("Since 1999!")), "Since nineteen ninety-nine!")


@pytest.mark.parametrize(
    ("heard", "said"),
    [
        ("for 900 years", "for nine hundred years"),
        ("only 105 left", "only one hundred five left"),
        ("1999 of them", "one thousand nine hundred ninety-nine of them"),
        ("20000 credits", "twenty thousand credits"),
    ],
)
def test_hundreds_and_thousands_match_their_cardinal_words(heard, said):
    check_transcript(parse_transcript(transcript(heard)), said)


def test_silent_sound_effect_is_rejected():
    with pytest.raises(VoiceOutputError, match="sound effect is silent"):
        voice.verify_effect(wav_of([0] * 48000), 1.0)


def test_empty_clip_counts_as_silent():
    with pytest.raises(VoiceOutputError, match="silent"):
        voice.verify_effect(wav_of([]), 1.0)


@pytest.mark.parametrize("influence", [-0.1, 1.5])
def test_prompt_influence_outside_unit_range_is_refused(tmp_path, influence):
    binary = Binary(b"ID3")
    with pytest.raises(ValueError, match="prompt_influence"):
        ElevenLabsClient(tmp_path, key="k", binary_transport=binary).sound_effect("thud", 1.0, influence)
    assert binary.calls == []


def test_uncached_sound_effect_without_key_is_a_clear_error(tmp_path):
    binary = Binary(b"ID3")
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        ElevenLabsClient(tmp_path, key="", binary_transport=binary).sound_effect("thud", 1.0)
    assert binary.calls == []


@ffmpeg
def test_cached_sound_effect_is_reverified_and_its_samples_read(tmp_path, mp3):
    client = ElevenLabsClient(tmp_path, key="k", binary_transport=Binary(mp3))
    clip = client.sound_effect("a squeaky office chair", 1.0)
    assert len(clip.samples()) == round(clip.duration * 48000)
    original = clip.wav.read_bytes()
    clip.wav.unlink()  # cache hit without the wav: decoded again from the mp3 and re-verified
    again = ElevenLabsClient(tmp_path, key="").sound_effect("a squeaky office chair", 1.0)
    assert again.duration == clip.duration
    assert again.wav.read_bytes() == original
    assert len(again.samples()) == round(again.duration * 48000)
    clip.wav.write_bytes(wav_of([0] * 48000))  # a tampered cached wav is re-verified, not trusted
    with pytest.raises(VoiceOutputError, match="silent"):
        ElevenLabsClient(tmp_path, key="").sound_effect("a squeaky office chair", 1.0)


@ffmpeg
def test_cached_line_rebuilds_a_missing_wav_from_the_mp3(tmp_path, mp3):
    client = ElevenLabsClient(tmp_path, key="k", transport=Transport(response(audio=mp3)))
    line = client.synthesize(TEXT, VOICE, SETTINGS)
    original = line.wav.read_bytes()
    line.wav.unlink()
    again = ElevenLabsClient(tmp_path, key="").synthesize(TEXT, VOICE, SETTINGS)
    assert again.wav.read_bytes() == original and again.duration == line.duration


@pytest.mark.parametrize("stored", [[], {"request": {}}])
def test_a_corrupt_transcript_record_is_rejected(tmp_path, stored):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    ElevenLabsClient(tmp_path / "c", key="k", multipart_transport=Multipart(transcript("In your chair."))).transcribe(
        wav
    )
    (record,) = (tmp_path / "c").glob("stt-*.json")
    record.write_text(json.dumps(stored))
    with pytest.raises(VoiceOutputError, match="not a transcript record"):
        ElevenLabsClient(tmp_path / "c", key="").transcribe(wav)


def test_uncached_transcript_without_key_is_a_clear_error(tmp_path):
    wav = tmp_path / "line.wav"
    wav.write_bytes(b"RIFF....WAVE")
    multipart = Multipart(transcript())
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        ElevenLabsClient(tmp_path, key="", multipart_transport=multipart).transcribe(wav)
    assert multipart.calls == []


@pytest.mark.parametrize(
    ("heard", "script"),
    [
        ("He thinks about it every night at 3:00 AM", "He thinks about it every night at three a.m."),
        ("3:00 AM, Vera?", "Three a.m., Vera."),
        ("Lunch is at 12:00 PM.", "Lunch is at twelve p.m."),
        ("Back at 3:00.", "Back at three."),
    ],
)
def test_speech_to_text_writes_an_hour_as_a_clock_and_the_hour_still_matches(heard, script):
    check_transcript(parse_transcript(transcript(heard)), script)


@pytest.mark.parametrize(
    "heard",
    [
        "He called at 3:30 AM",  # other minutes are other words
        "He called at 4:00 AM",  # another hour
        "He called at 3:00 PM",  # the other half of the day
        "He called at 3:00",  # the words dropped
        "He called at 300 AM",  # not a clock
        "He called at 13:00 AM",  # a clock the line did not say
        "He called at 3:000 AM",  # not a clock either
    ],
)
def test_a_clock_reading_changes_no_other_word(heard):
    with pytest.raises(TranscriptMismatch):
        check_transcript(parse_transcript(transcript(heard)), "He called at three a.m.")


def test_a_script_that_says_the_zeros_still_hears_them():
    check_transcript(parse_transcript(transcript("Room 3:00")), "Room three oh oh")
