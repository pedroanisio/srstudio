"""A sketch cut to a supplied recording: the reading parsed against the lines (good, malformed, incomplete and
adversarial readings), the letters spread over heard words, the decode's checks and the voiced project the Toon build
reads."""

import json
import math
import shutil
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import music, narration, sketch, supplied
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.supplied import SuppliedError
from srstudio.voice import Transcript, Voice, VoiceSettings, Word

SET = VoiceSettings(0.5, 0.75, 0.0)
SPEAKERS = (
    Speaker("phone", Voice("phone", "supplied", "Original audio"), SET),
    Speaker("rex", Voice("rex", "supplied", "Original audio"), SET, "dog"),
)
LINES = (Line("phone", "What a silly question."), Line("rex", "You ask a lot."))
BEATS = (
    Beat(0.0, "dog", "", "wide", "flat", "desk"),
    Beat(0.5, "dog", "What a silly question.", "wide", "flat", "desk", 0, 0),
    Beat(1.0, "dog", "What a silly question.", "half", "flat", "desk", event="push"),
    Beat(2.0, "dog", "You ask a lot.", "half", "flat", "desk", 1, 0),
    Beat(3.0, "dog", "", "closed", "flat", "desk", event="stare"),
)
SK = Sketch("cut-to-it", "Cut to it", SPEAKERS, LINES, BEATS, 4.0, tail=0.5)


def words(*spec):
    """Heard words from (text, start, end) triples, with a gap between each."""
    out = []
    for k, (text, a, b) in enumerate(spec):
        if k:
            out.append(Word(" ", out[-1].end, a, "spacing"))
        out.append(Word(text, a, b, "word"))
    return tuple(out)


HEARD = words(
    ("What", 0.6, 0.7), ("a", 0.75, 0.8), ("silly", 0.9, 1.2), ("question.", 1.25, 1.7),
    ("You", 2.1, 2.2), ("ask", 2.25, 2.4), ("a", 2.45, 2.5), ("lot.", 2.55, 2.8),
)  # fmt: skip
READING = Transcript("en", 1.0, "What a silly question. You ask a lot.", HEARD)


def wav(path: Path, seconds: float, channels: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x01\x00" * channels * int(seconds * 48000))
    return path


# -- the reading ------------------------------------------------------------------------------------------------------
def test_each_line_is_found_as_its_run_of_heard_words():
    heard = supplied.locate(LINES, READING, 3.5)
    assert [(h.line, h.start, h.end) for h in heard] == [(0, 0.6, 1.7), (1, 2.1, 2.8)]
    assert [w.text for w in heard[1].words] == ["You", "ask", "a", "lot."]


def test_a_heard_spelling_the_line_accepts_passes():
    reading = replace(READING, words=tuple(replace(w, text="sillie") if w.text == "silly" else w for w in HEARD))
    with pytest.raises(SuppliedError, match="line 0: heard 'What a sillie question.'"):
        supplied.locate(LINES, reading, 3.5)
    accepted = (replace(LINES[0], heard=("What a sillie question.",)), LINES[1])
    assert len(supplied.locate(accepted, reading, 3.5)) == 2


@pytest.mark.parametrize(
    "reading, match",
    [
        (replace(READING, words=HEARD[:9]), "line 1 .* ran out of words"),  # incomplete
        (replace(READING, words=()), "line 0 .* ran out of words"),  # empty
        (replace(READING, words=(*HEARD, Word("again", 3.0, 3.2, "word"))), "words no line says: 'again'"),
        (replace(READING, words=(*HEARD[:2], Word("(laughs)", 0.7, 0.8, "audio_event"), *HEARD[2:])), "audio_event"),
        (replace(READING, words=(*HEARD[:-1], replace(HEARD[-1], end=9.0))), "past the file"),
        (replace(READING, words=(*HEARD[:-1], replace(HEARD[-1], start=0.1))), "before the word heard before"),
        (replace(READING, words=(replace(HEARD[0], start=-1.0), *HEARD[1:])), "runs from -1.0"),
        (replace(READING, words=(replace(HEARD[0], end=math.nan), *HEARD[1:])), "runs from"),
        (replace(READING, words=tuple(reversed(HEARD))), "before the word heard before|line 0"),  # adversarial order
        (replace(READING, words=tuple(replace(w, text="lot.") for w in HEARD)), "line 0: heard"),  # adversarial words
    ],
)
def test_a_reading_that_does_not_say_the_lines_is_refused(reading, match):
    with pytest.raises(SuppliedError, match=match):
        supplied.locate(LINES, reading, 3.5)


@pytest.mark.parametrize(
    "lines, duration, match",
    [
        (LINES, 0.0, "more than 0 s"),
        (LINES, math.inf, "more than 0 s"),
        ((), 3.5, "at least one line"),
        ((replace(LINES[0], phone=True), LINES[1]), 3.5, "by phone"),
        ((LINES[0], replace(LINES[1], together=True)), 3.5, "together"),
        ((replace(LINES[0], gain=-3.0), LINES[1]), 3.5, "gain"),
    ],
)
def test_lines_or_a_file_the_reading_cannot_be_placed_on_are_refused(lines, duration, match):
    with pytest.raises(SuppliedError, match=match):
        supplied.locate(lines, READING, duration)


def test_letters_share_each_word_evenly_and_spaces_span_the_gaps():
    a = supplied.spread(["What", "a"], (HEARD[0], HEARD[2]), 0.6)
    assert a.text == "What a"
    assert a.starts[:4] == (0.0, 0.025, 0.05, 0.075) and a.ends[3] == pytest.approx(0.1)
    assert (a.starts[4], a.ends[4]) == (pytest.approx(0.1), pytest.approx(0.15))  # the gap
    assert (a.starts[5], a.ends[5]) == (pytest.approx(0.15), pytest.approx(0.2))
    instant = supplied.spread(["a"], (Word("a", 1.0, 1.0, "word"),), 1.0)
    assert instant.ends == (supplied.LETTER_FLOOR,)
    with pytest.raises(SuppliedError, match="cannot be spread"):
        supplied.spread(["What"], (HEARD[0], HEARD[2]), 0.6)
    with pytest.raises(SuppliedError, match="cannot be spread"):
        supplied.spread([], (), 0.0)


# -- the file ---------------------------------------------------------------------------------------------------------
def test_the_file_is_checked_by_its_digest_and_decoded_bit_exact(tmp_path):
    src = wav(tmp_path / "in" / "trend.wav", 0.5)
    digest = supplied._sha256(src)
    with pytest.raises(SuppliedError, match="not a file"):
        supplied.decode(tmp_path / "missing.m4a", digest, tmp_path / "p")
    with pytest.raises(SuppliedError, match="the recording this reel is cut to"):
        supplied.decode(src, "0" * 64, tmp_path / "p")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:  # pragma: no cover - the workstation has it
        pytest.skip("no ffmpeg")
    one = supplied.decode(src, digest, tmp_path / "p", ffmpeg)
    first = one.read_bytes()
    assert supplied.decode(src, digest, tmp_path / "p", ffmpeg).read_bytes() == first
    assert supplied.duration_of(one) == pytest.approx(0.5)
    with pytest.raises(SuppliedError, match="could not decode"):
        broken = tmp_path / "in" / "broken.m4a"
        broken.write_bytes(b"not audio")
        supplied.decode(broken, supplied._sha256(broken), tmp_path / "p", ffmpeg)


def test_a_file_that_is_not_pcm_with_samples_is_refused(tmp_path):
    with pytest.raises(SuppliedError, match="not a readable WAV"):
        bad = tmp_path / "bad.wav"
        bad.write_bytes(b"RIFF")
        supplied.duration_of(bad)
    with pytest.raises(SuppliedError, match="16-bit PCM with samples"):
        supplied.duration_of(wav(tmp_path / "empty.wav", 0.0))


# -- the voiced project -----------------------------------------------------------------------------------------------
def test_each_take_is_cut_from_the_file_for_head_motion_keeping_its_channels(tmp_path):
    wav(tmp_path / supplied.SOURCE, 3.5)
    supplied.voice(SK, tmp_path, READING, credit="Original audio, by someone else")
    takes, _ = sketch.load_speech(tmp_path / "voiced" / "speech.json")
    with wave.open(str(tmp_path / supplied.SOURCE), "rb") as source:
        channels, rate = source.getnchannels(), source.getframerate()
    for take in takes:  # each take's stretch, which head motion reads for its loudness; never mixed
        cut = tmp_path / "audio" / f"vo-{take.id}.wav"
        assert supplied.duration_of(cut) == pytest.approx(take.kept, abs=1e-4)
        with wave.open(str(cut), "rb") as w:
            assert (w.getnchannels(), w.getframerate()) == (channels, rate)
    manifest = json.loads((tmp_path / "narration.json").read_text())
    assert all("vo-" not in json.dumps(item) for item in manifest["items"])


def test_the_voiced_project_is_what_the_narrated_build_reads(tmp_path):
    audio = wav(tmp_path / supplied.SOURCE, 3.5)
    manifest = supplied.voice(SK, tmp_path, READING, credit="Original audio, by someone else")
    assert manifest["tts_engine"] == "supplied" and manifest["voice"]["phone"]["credit"].startswith("Original")
    cues = narration.narration_cues(tmp_path / "narration.json", tmp_path)
    assert [(c.start, c.duration, c.audio) for c in cues] == [(0.0, 3.5, supplied.SOURCE)]
    assert narration.effect_cues(tmp_path / "narration.json", tmp_path) == []
    assert cues[0].sha256 == narration.sha256_of(audio)
    beats, end = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    assert end == manifest["duration"] == max(3.5, round(beats[-1].start + SK.tail, 6))  # the file, or the tail
    assert [b.start for b in beats if b.spoken] == [0.6, 2.1]  # on the heard words
    takes, _ = sketch.load_speech(tmp_path / "voiced" / "speech.json")
    assert [(t.id, t.who, t.at) for t in takes] == [("01", None, 0.6), ("02", "dog", 2.1)]
    mouths, mouths_end = sketch.load_mouths(tmp_path / "voiced" / "mouths.json")
    assert mouths_end == end and set(mouths) == {"dog"}
    assert mouths["dog"][0] == (2.1, "closed") or mouths["dog"][0][0] >= 2.1
    assert mouths["dog"][-1][1] == "closed"
    phone = supplied.mouth_track(takes)
    assert phone and 0.6 <= phone[0][0] and phone[-1][1] == "closed" and abs(phone[-1][0] - 1.7) <= 1 / 24
    assert any(v != "closed" for _, v in phone)
    heard = json.loads((tmp_path / "voice-transcript.json").read_text())
    assert heard["passed"] and [line["heard"] for line in heard["lines"]] == [
        "What a silly question.",
        "You ask a lot.",
    ]


def test_a_longer_end_holds_and_a_short_one_is_refused_before_anything_is_written(tmp_path):
    wav(tmp_path / supplied.SOURCE, 3.5)
    assert supplied.voice(SK, tmp_path, READING, credit="x", end=6.5)["duration"] == 6.5
    other = tmp_path / "other"
    wav(other / supplied.SOURCE, 3.5)
    with pytest.raises(SuppliedError, match="before the file and the last beat"):
        supplied.voice(SK, other, READING, credit="x", end=3.4)
    with pytest.raises(SuppliedError, match="credit"):
        supplied.voice(SK, other, READING, credit=" ")
    with pytest.raises(SuppliedError, match="ran out"):
        supplied.voice(SK, other, replace(READING, words=HEARD[:3]), credit="x")
    assert not (other / "narration.json").exists() and not (other / "voiced").exists()


def test_the_recorder_decodes_hears_once_and_writes_the_project(tmp_path, capsys):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:  # pragma: no cover - the workstation has it
        pytest.skip("no ffmpeg")
    src = tmp_path / "in" / "trend.wav"
    src.parent.mkdir()
    music.write_wav(src, [0.0] * int(3.5 * 48000), 48000)
    asked = []

    def hear(root, env):
        asked.append(root)
        return READING

    main = supplied.recorder(SK, supplied._sha256(src), "Original audio", __doc__, hear=hear, validate=sketch.check)
    assert main([str(tmp_path / "p"), "--supplied", str(src), "--ffmpeg", ffmpeg], env={}) == 0
    assert asked == [(tmp_path / "p").resolve()]
    assert (tmp_path / "p" / "narration.json").is_file()
    assert "2 lines heard" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main([str(tmp_path / "p")], env={})  # --supplied is required
    with pytest.raises(SuppliedError, match="64 lower-case hex"):
        supplied.recorder(SK, "abc", "x", None)


def test_the_default_hearing_reads_the_cache_and_asks_consent_only_for_a_request(tmp_path):
    from srstudio.narration import ConsentError
    from srstudio.voice import MissingKeyError

    wav(tmp_path / supplied.SOURCE, 1.0)
    body = {"language_code": "en", "language_probability": 1.0, "text": "Hi.", "words": []}
    sent = []

    def transport(*args):
        sent.append(args[0])
        return body, "req-1"

    with pytest.raises(ConsentError):
        supplied._hear(tmp_path, {}, transport)
    with pytest.raises(MissingKeyError):
        supplied._hear(tmp_path, {"SRSTUDIO_ALLOW_CLOUD": "1"}, transport)
    assert sent == []
    allowed = {"SRSTUDIO_ALLOW_CLOUD": "1", "ELEVENLABS_API_KEY": "test-key"}
    assert supplied._hear(tmp_path, allowed, transport).text == "Hi." and len(sent) == 1  # the one paid reading
    assert supplied._hear(tmp_path, {}, transport).text == "Hi." and len(sent) == 1  # read back: no key, no request
