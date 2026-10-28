"""The ElevenLabs music client: plan validation, the beat and lyric checks, failure path, no retries, cache.

No network: the transport is injected. Test songs are click tracks made here (and MP3-encoded by ffmpeg for
the client), so the tempo measurement and the decode run for real.
"""

import io
import json
import math
import random
import shutil
import subprocess
import wave
from array import array

import pytest

from srstudio import compose
from srstudio.compose import Chunk, LyricMismatch, MusicClient, MusicOutputError, Plan, locate_lyrics, measure_tempo
from srstudio.voice import VoiceOutputError, parse_transcript

RATE = 48000
ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required to decode music")


def clicks(bpm=120.0, seconds=8.0, offset=0.0, rate=RATE, accent_every=4):
    """A click on every beat from ``offset``: a 30 ms decaying 1 kHz burst over a quiet 110 Hz drone."""
    n = round(seconds * rate)
    out = [0.08 * math.sin(2 * math.pi * 110 * k / rate) for k in range(n)]
    period, beat = 60 / bpm, 0
    while offset + beat * period < seconds:
        at = round((offset + beat * period) * rate)
        level = 0.8 if beat % accent_every == 0 else 0.55
        for k in range(min(round(0.03 * rate), n - at)):
            out[at + k] += level * math.exp(-k / (0.006 * rate)) * math.sin(2 * math.pi * 1000 * k / rate)
        beat += 1
    return out


def scatter(seconds=12.0, per_second=12, seed=3, rate=RATE):
    """Hits at random times, like the busy off-beat texture of a real arrangement."""
    rnd = random.Random(seed)
    n = round(seconds * rate)
    out = [0.0] * n
    for _ in range(round(seconds * per_second)):
        at, level, f = rnd.randrange(n), rnd.uniform(0.3, 0.8), rnd.choice((300, 2000, 5000))
        for k in range(min(round(0.03 * rate), n - at)):
            out[at + k] += level * math.exp(-k / (0.006 * rate)) * math.sin(2 * math.pi * f * k / rate)
    return out


def noise(seconds=8.0, rate=RATE, seed=7):
    rnd = random.Random(seed)
    return [rnd.uniform(-0.3, 0.3) for _ in range(round(seconds * rate))]


def wav_bytes(samples, rate=RATE, channels=1):
    pcm = array("h", (max(-32767, min(32767, round(v * 32767))) for v in samples))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def mp3_of(samples, tmp_path, name="song"):
    src, out = tmp_path / f"{name}.wav", tmp_path / f"{name}.mp3"
    src.write_bytes(wav_bytes(samples))
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "192k", str(out)], check=True
    )
    return out.read_bytes()


STYLES = ("120 BPM", "office pop", "male vocal")


def plan(*sections):
    return Plan(sections or (Chunk("Verse", 4.0, STYLES, ("Camera on.",)), Chunk("Break", 4.0, STYLES)))


# -- the plan we send: checked before any paid request -----------------------------------------------
def test_plan_serialises_to_the_v2_chunk_schema():
    body = Plan(
        (
            Chunk("Verse", 4.0, STYLES, ("Camera on.", "Nod, nod, nod.")),
            Chunk("Break", 3.5, ("instrumental",), negative=("vocals",), context="medium"),
        )
    ).to_dict()
    assert body == {
        "chunks": [
            {
                "text": "[Verse]\nCamera on.\nNod, nod, nod.",
                "duration_ms": 4000,
                "positive_styles": list(STYLES),
                "negative_styles": [],
                "context_adherence": "high",
            },
            {
                "text": "[Break]",
                "duration_ms": 3500,
                "positive_styles": ["instrumental"],
                "negative_styles": ["vocals"],
                "context_adherence": "medium",
            },
        ]
    }


def test_plan_windows_follow_the_chunk_durations():
    p = plan(Chunk("A", 4.0, STYLES, ("one",)), Chunk("B", 3.0, STYLES), Chunk("C", 8.0, STYLES, ("two",)))
    assert p.seconds == 15.0
    assert p.windows() == [(0.0, 4.0), (4.0, 7.0), (7.0, 15.0)]
    assert p.sung() == [("one", (0.0, 4.0)), ("two", (7.0, 15.0))]


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (dict(seconds=2.99), "duration"),
        (dict(seconds=120.01), "duration"),
        (dict(seconds=float("nan")), "duration"),
        (dict(styles=()), "styles"),
        (dict(styles=("",)), "styles"),
        (dict(lines=("la",) * 31), "30 lines"),
        (dict(lines=("x" * 201,)), "200 characters"),
        (dict(lines=("two\nlines",)), "one line"),
        (dict(name=""), "name"),
        (dict(name="x" * 101), "name"),
        (dict(name="Hook]"), "name"),
        (dict(context="maximum"), "context"),
    ],
)
def test_invalid_chunks_are_refused_before_any_request(kwargs, match):
    fields = dict(name="Verse", seconds=4.0, styles=STYLES, lines=())
    fields.update(kwargs)
    with pytest.raises(ValueError, match=match):
        Chunk(**fields)


def test_an_empty_plan_is_refused():
    with pytest.raises(ValueError, match="at least one chunk"):
        Plan(())


# -- the beat check -------------------------------------------------------------------------------------
@pytest.mark.parametrize("offset", [0.0, 0.1, 0.37])
def test_tempo_and_phase_of_a_steady_beat(offset):
    tempo = measure_tempo(clicks(120, offset=offset), RATE, expected=120)
    assert abs(tempo.bpm - 120) < 0.6
    assert abs(tempo.phase - offset % 0.5) < 0.015
    assert tempo.strength > 0.5


def test_a_double_time_beat_still_lands_on_the_grid():
    tempo = measure_tempo(clicks(240), RATE, expected=120)
    assert abs(tempo.bpm - 120) < 0.6 and tempo.phase < 0.015


@pytest.mark.parametrize("bpm", [100, 112, 128, 60])
def test_a_song_off_the_requested_tempo_is_rejected(bpm):
    with pytest.raises(MusicOutputError, match="tempo"):
        measure_tempo(clicks(bpm), RATE, expected=120)


def test_a_song_without_a_steady_beat_is_rejected():
    with pytest.raises(MusicOutputError, match="steady beat"):
        measure_tempo(noise(), RATE, expected=120)


def test_silence_has_no_beat():
    with pytest.raises(MusicOutputError, match="steady beat"):
        measure_tempo([0.0] * RATE * 4, RATE, expected=120)


# -- the lyric check -----------------------------------------------------------------------------------
def heard(*timed):
    """A transcript body whose words are ``(text, start, end)``."""
    words = [{"text": w, "start": a, "end": b, "type": "word"} for w, a, b in timed]
    return parse_transcript(
        {"language_code": "eng", "language_probability": 0.98, "text": " ".join(w for w, *_ in timed), "words": words}
    )


def test_each_sung_line_is_found_in_order_inside_its_window():
    t = heard(
        ("Camera", 0.4, 0.8),
        ("on.", 0.8, 1.1),
        ("yeah", 1.3, 1.5),  # an ad-lib between lines is allowed
        ("Nod,", 2.0, 2.2),
        ("nod,", 2.3, 2.5),
        ("nod.", 2.6, 2.9),
        ("Pajamas", 8.2, 8.9),
        ("on", 9.0, 9.1),
        ("the", 9.1, 9.2),
        ("beat!", 9.2, 9.6),
    )
    spans = locate_lyrics(t, [("Camera on.", (0, 4)), ("Nod, nod, nod.", (0, 4)), ("Pajamas on the beat!", (8, 16))])
    assert spans == [(0.4, 1.1), (2.0, 2.9), (8.2, 9.6)]


def test_a_line_sung_outside_its_window_is_a_mismatch():
    t = heard(("Camera", 4.5, 4.9), ("on.", 4.9, 5.2))
    with pytest.raises(LyricMismatch, match="Camera on"):
        locate_lyrics(t, [("Camera on.", (0, 4))], slack=0.25)


def test_a_missing_or_changed_word_is_a_mismatch():
    t = heard(("Camera", 0.4, 0.8), ("off.", 0.8, 1.1))
    with pytest.raises(LyricMismatch, match="heard"):
        locate_lyrics(t, [("Camera on.", (0, 4))])


def test_lines_must_come_in_order():
    t = heard(("Nod.", 0.2, 0.5), ("Camera", 1.0, 1.4), ("on.", 1.4, 1.7))
    with pytest.raises(LyricMismatch, match="Nod"):
        locate_lyrics(t, [("Camera on.", (0, 4)), ("Nod.", (0, 4))])


def test_lyric_mismatch_is_a_verification_failure():
    assert issubclass(LyricMismatch, MusicOutputError) and issubclass(MusicOutputError, VoiceOutputError)


# -- the client: one request, verified output, cache ------------------------------------------------------
class Binary:
    def __init__(self, audio=b"", exc=None):
        self.audio, self.exc, self.calls = audio, exc, []

    def __call__(self, url, payload, headers):
        self.calls.append((url, payload, headers))
        if self.exc:
            raise self.exc
        return self.audio, "req-1"


@pytest.fixture(scope="module")
def song_mp3(tmp_path_factory):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    return mp3_of(clicks(120, seconds=8.0), tmp_path_factory.mktemp("song"))


@ffmpeg
def test_compose_sends_one_request_verifies_and_caches(tmp_path, song_mp3):
    binary = Binary(song_mp3)
    client = MusicClient(tmp_path / "cache", key="sk-secret", binary_transport=binary)
    song = client.compose(plan(), seed=82026, bpm=120)
    ((url, payload, headers),) = binary.calls
    assert url.startswith("https://api.elevenlabs.io/v1/music?") and "output_format=mp3_48000_192" in url
    assert payload == {"composition_plan": plan().to_dict(), "model_id": "music_v2", "seed": 82026}
    assert headers["xi-api-key"] == "sk-secret"
    assert abs(song.duration - 8.0) < 0.1 and abs(song.tempo.bpm - 120) < 0.6
    with wave.open(str(song.wav)) as w:  # the mix copy keeps the stereo image at the mix rate
        assert w.getframerate() == 48000 and w.getnchannels() == 2
    record = json.loads(song.record.read_text())
    assert record["request_id"] == "req-1" and record["seed"] == 82026 and "sk-secret" not in song.record.read_text()
    again = MusicClient(tmp_path / "cache", key="", binary_transport=binary).compose(plan(), seed=82026, bpm=120)
    assert len(binary.calls) == 1 and again.wav == song.wav and again.tempo == song.tempo


@ffmpeg
def test_another_seed_or_plan_is_another_request(tmp_path, song_mp3):
    binary = Binary(song_mp3)
    client = MusicClient(tmp_path, key="k", binary_transport=binary)
    client.compose(plan(), seed=1, bpm=120)
    client.compose(plan(), seed=2, bpm=120)
    client.compose(plan(Chunk("Verse", 8.0, STYLES, ("Camera on.",))), seed=1, bpm=120)
    assert len(binary.calls) == 3


@ffmpeg
def test_cached_song_is_reverified_on_read(tmp_path, song_mp3):
    song = MusicClient(tmp_path, key="k", binary_transport=Binary(song_mp3)).compose(plan(), seed=1, bpm=120)
    song.mp3.write_bytes(b"ID3 tampered")
    song.wav.unlink()
    with pytest.raises(MusicOutputError, match="decode"):
        MusicClient(tmp_path, key="").compose(plan(), seed=1, bpm=120)


def test_missing_key_for_an_uncached_song_is_a_clear_error(tmp_path):
    binary = Binary(b"ID3")
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        MusicClient(tmp_path, key="", binary_transport=binary).compose(plan(), seed=1, bpm=120)
    assert binary.calls == []


@pytest.mark.parametrize("audio,match", [(b"", "empty"), (b"<html>busy</html>", "decode")])
def test_empty_or_undecodable_song_is_rejected_and_not_cached(tmp_path, audio, match):
    with pytest.raises(MusicOutputError, match=match):
        MusicClient(tmp_path / "c", key="k", binary_transport=Binary(audio)).compose(plan(), seed=1, bpm=120)
    assert not (tmp_path / "c").exists()


@ffmpeg
def test_a_song_of_the_wrong_length_is_rejected(tmp_path, song_mp3):
    """Asked for 16 s, got 8 s: the model ignored the plan's durations."""
    long_plan = plan(Chunk("Verse", 8.0, STYLES, ("Camera on.",)), Chunk("Break", 8.0, STYLES))
    with pytest.raises(MusicOutputError, match="duration"):
        MusicClient(tmp_path / "c", key="k", binary_transport=Binary(song_mp3)).compose(long_plan, seed=1, bpm=120)
    assert not (tmp_path / "c").exists()


@ffmpeg
def test_a_silent_song_is_rejected(tmp_path):
    silent = mp3_of([0.0] * RATE * 8, tmp_path)
    with pytest.raises(MusicOutputError, match="silent"):
        MusicClient(tmp_path / "c", key="k", binary_transport=Binary(silent)).compose(plan(), seed=1, bpm=120)


@ffmpeg
def test_a_song_off_tempo_is_rejected_and_not_cached(tmp_path):
    slow = mp3_of(clicks(100, seconds=8.0), tmp_path)
    with pytest.raises(MusicOutputError, match="tempo"):
        MusicClient(tmp_path / "c", key="k", binary_transport=Binary(slow)).compose(plan(), seed=1, bpm=120)
    assert not (tmp_path / "c").exists()


def test_transport_failure_is_not_retried(tmp_path):
    binary = Binary(exc=RuntimeError("ElevenLabs HTTP 429: busy"))
    with pytest.raises(RuntimeError, match="429"):
        MusicClient(tmp_path, key="k", binary_transport=binary).compose(plan(), seed=1, bpm=120)
    assert len(binary.calls) == 1


@pytest.mark.parametrize("seed", [-1, 2**32, 1.5, True])
def test_seed_must_be_a_32_bit_integer(tmp_path, seed):
    with pytest.raises(ValueError, match="seed"):
        MusicClient(tmp_path, key="k", binary_transport=Binary(b"x")).compose(plan(), seed=seed, bpm=120)


def test_module_carries_the_verification_banner():
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in compose.__doc__


@ffmpeg
def test_a_missing_mix_wav_is_rebuilt_from_the_cached_mp3(tmp_path, song_mp3):
    song = MusicClient(tmp_path, key="k", binary_transport=Binary(song_mp3)).compose(plan(), seed=1, bpm=120)
    original = song.wav.read_bytes()
    song.wav.unlink()
    again = MusicClient(tmp_path, key="").compose(plan(), seed=1, bpm=120)
    assert again.wav.read_bytes() == original


def test_a_transport_answer_that_is_not_bytes_is_rejected(tmp_path):
    with pytest.raises(MusicOutputError, match="not bytes"):
        MusicClient(tmp_path, key="k", binary_transport=Binary({"detail": "x"})).compose(plan(), seed=1, bpm=120)


def test_a_direction_goes_before_the_lyrics_and_is_not_a_sung_line():
    chunk = Chunk("Forty Slides", 4.0, STYLES, ("Camera off.",), direction="instrumental for two bars")
    assert chunk.to_dict()["text"] == "[Forty Slides]\n{instrumental for two bars}\nCamera off."
    assert Plan((chunk,)).sung() == [("Camera off.", (0.0, 4.0))]


@pytest.mark.parametrize("direction", ["{nested}", "two\nlines", "x" * 201])
def test_a_malformed_direction_is_refused(direction):
    with pytest.raises(ValueError, match="direction"):
        Chunk("Verse", 4.0, STYLES, direction=direction)


def test_a_dense_mix_with_a_weak_but_clear_beat_passes():
    """Real songs spread onsets everywhere: the beat's autocorrelation is low in absolute terms, yet it is the
    strongest non-harmonic peak and far above the noise floor."""
    dense = [a + b for a, b in zip(clicks(120, seconds=12.0), scatter(), strict=True)]
    tempo = measure_tempo(dense, RATE, expected=120)
    assert abs(tempo.bpm - 120) < 0.6 and tempo.phase < 0.015 and tempo.strength < 0.3


@pytest.mark.parametrize("seed", [5, 6])
def test_dense_hits_without_a_beat_are_rejected(seed):
    with pytest.raises(MusicOutputError, match="steady beat"):
        measure_tempo(scatter(seed=seed), RATE, expected=120)
