"""The narration toolkit: consent, voice checks, word timings, the take schedule, the conform, caption-window
fitting and the manifest an episode plays from."""

import hashlib
import io
import json
import math
import struct
import subprocess
import urllib.error
import wave
from pathlib import Path

import pytest

from srstudio import cel
from srstudio import narration as _narration
from srstudio.errors import ConsentError, ProviderHTTPError, SrstudioError
from srstudio.voice import RATE, Alignment, Voice, VoiceOutputError

BOX = {"x": 1, "y": 1, "w": 1, "h": 1, "glyphs": "M 1 1"}
BASE = 1.08  # a narrator's base speed


@pytest.fixture
def narration():
    return _narration


def alignment(text, step=0.1, offset=0.5):
    n = len(text)
    return Alignment(
        tuple(text), tuple(offset + i * step for i in range(n)), tuple(offset + (i + 1) * step for i in range(n))
    )


def test_words_and_phones_are_relative_to_the_trimmed_clip(narration):
    a = alignment("Fine. Off.")  # 10 characters, 0.5..1.5
    words = narration.words_from_alignment(a, "Fine. Off.", trim_start=0.45, speech_duration=1.0)
    assert words == [{"text": "Fine.", "start": 0.05, "end": 0.55}, {"text": "Off.", "start": 0.65, "end": 1.0}]
    phones = narration.phones_from_alignment(a, 0.45, 1.0)
    assert [p["c"] for p in phones] == list("Fine. Off.") and phones[0]["start"] == 0.05 and phones[-1]["end"] == 1.0
    assert [p["c"] for p in narration.phones_from_alignment(a, 1.0, 0.3)] == [" ", "O", "f"]  # the cut drops the rest


def test_words_refuse_a_wrong_alignment_and_a_word_the_trim_cut(narration):
    with pytest.raises(VoiceOutputError, match="spells"):
        narration.words_from_alignment(alignment("Fine. On."), "Fine. Off.", 0, 2)
    with pytest.raises(VoiceOutputError, match="outside the trimmed clip"):
        narration.words_from_alignment(alignment("Fine. Off."), "Fine. Off.", trim_start=1.1, speech_duration=0.4)


def test_schedule_chains_the_takes_and_rounds_up_to_the_frame(narration):
    items = [{"id": "01", "duration": 1.3}, {"id": "02", "duration": 0.71}]
    assert narration.schedule(items) == pytest.approx(math.ceil(2.01 * 24) / 24)
    assert [q["start"] for q in items] == [0, 1.3]
    with pytest.raises(ValueError, match="positive"):
        narration.schedule([{"id": "01", "duration": 0}])
    with pytest.raises(ValueError, match="positive"):
        narration.schedule([{"id": "01", "duration": float("nan")}])


def test_consent_is_required(narration):
    with pytest.raises(ConsentError, match="SRSTUDIO_ALLOW_CLOUD") as refused:
        narration.require_consent({})
    assert isinstance(refused.value, SrstudioError) and isinstance(refused.value, RuntimeError)
    narration.require_consent({"SRSTUDIO_ALLOW_CLOUD": "1"})


def test_confirm_voice_checks_the_name_and_caches_only_the_name(narration, tmp_path):
    voice = Voice(role="router", id="abcdefgh12345678", name="Daniel")
    seen = []

    def fetch(url, headers):
        seen.append((url, headers.get("xi-api-key")))
        return {"name": "Daniel - Authoritative, British", "category": "premade", "settings": {"x": 1}}

    kept = narration.confirm_voice(tmp_path, "k", voice, fetch)
    assert kept == {"voice_id": voice.id, "name": "Daniel - Authoritative, British", "category": "premade"}
    assert seen[0][0].endswith(voice.id)
    record = json.loads((tmp_path / f"voice-{voice.id}.json").read_text())
    assert record == kept and "k" not in json.dumps(record)
    assert narration.confirm_voice(tmp_path, "", voice, fetch) == kept and len(seen) == 1  # cached: no request, no key
    with pytest.raises(VoiceOutputError, match="wants 'Chris'"):
        narration.confirm_voice(
            tmp_path, "k", Voice(role="h", id="other123", name="Chris"), lambda u, h: {"name": "Dan"}
        )
    with pytest.raises(VoiceOutputError, match="no name"):
        narration.confirm_voice(tmp_path, "k", Voice(role="h", id="other456", name="Chris"), lambda u, h: ["x"])
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        narration.confirm_voice(tmp_path, "", Voice(role="h", id="other789", name="Chris"), fetch)


class _Reply:
    def __init__(self, body: bytes):
        self.body = body

    def read(self, *_):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _serve(monkeypatch, body, status=None):
    """``urlopen`` answers ``body``, or raises HTTP ``status`` with ``body`` as the error document."""
    seen = []

    def urlopen(request, timeout):
        seen.append((request, timeout))
        if status:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(body))
        return _Reply(body)

    monkeypatch.setattr(_narration.urllib.request, "urlopen", urlopen)
    return seen


def test_the_voice_lookup_gets_once_and_decodes_the_record(narration, monkeypatch):
    seen = _serve(monkeypatch, b'{"name": "Chris - Charming"}')
    assert narration._urllib_fetch("https://api/v1/voices/x", {"xi-api-key": "k"}) == {"name": "Chris - Charming"}
    ((request, timeout),) = seen
    assert request.method == "GET" and request.get_header("Xi-api-key") == "k" and timeout == 60


def test_a_refused_voice_lookup_is_a_provider_error_carrying_only_its_message(narration, monkeypatch, tmp_path):
    _serve(monkeypatch, b'{"detail": {"message": "invalid api key"}}', status=401)
    with pytest.raises(ProviderHTTPError, match="^ElevenLabs HTTP 401: invalid api key$"):
        narration.confirm_voice(tmp_path, "k", Voice(role="h", id="other123", name="Chris"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("body", [b"<html>502</html>", b"\x80 not utf-8", b""])
def test_a_voice_lookup_answered_with_something_not_json_is_invalid_output(narration, monkeypatch, tmp_path, body):
    _serve(monkeypatch, body)
    with pytest.raises(VoiceOutputError, match="not JSON"):
        narration.confirm_voice(tmp_path, "k", Voice(role="h", id="other123", name="Chris"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("stored", ["{not json", "\udcff", '["Chris"]', "null"])
def test_a_cached_voice_record_that_is_not_an_object_is_invalid_output(narration, tmp_path, stored):
    voice = Voice(role="h", id="other123", name="Chris")
    (tmp_path / f"voice-{voice.id}.json").write_text(stored, errors="surrogateescape")
    with pytest.raises(VoiceOutputError, match="not a voice record"):
        narration.confirm_voice(tmp_path, "k", voice, lambda u, h: pytest.fail("a cached voice is never fetched"))


def tone(path, seconds=1.0, amplitude=0.5):
    n = round(seconds * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", round(amplitude * 32767 * math.sin(i * 0.05))) for i in range(n)))


def test_conform_cuts_levels_and_pads_to_the_sample(narration, tmp_path):
    src, dst = tmp_path / "src.wav", tmp_path / "dst.wav"
    tone(src)
    got = narration.conform(src, dst, 0.2, 0.7, 0.8, -6.0)
    assert got == pytest.approx(0.8, abs=1 / RATE) and dst.exists()
    with wave.open(str(dst), "rb") as w:
        assert (w.getframerate(), w.getnchannels()) == (RATE, 1)
    with pytest.raises(subprocess.CalledProcessError):  # the encoder failing is a failure, not a silent clip
        narration.conform(src, tmp_path / "x.wav", 0.2, 0.7, 0.8, 0.0, ffmpeg="false")
    with pytest.raises(VoiceOutputError, match="expected 48000 Hz"):
        bad = tmp_path / "bad.wav"
        with wave.open(str(bad), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"\0" * 400)
        narration.wav_seconds(bad)


def captions(*spans, phase="test"):
    return cel.parse_captions(
        [
            {"id": f"{i + 1:02}", "start": s, "end": e, "text": text, "phase": phase, "boxes": [BOX]}
            for i, (s, e, text) in enumerate(spans)
        ]
    )


def test_slots_run_from_a_caption_to_just_before_the_next_and_the_last_to_the_end(narration):
    caps = captions((0.1, 1.0, "One."), (1.1, 2.0, "Two..."), (2.2, 2.5, "Three."))
    got = narration.slots(caps, 3.0)
    assert [(s.id, s.start, round(s.end, 3)) for s in got] == [("01", 0.1, 1.08), ("02", 1.1, 2.18), ("03", 2.2, 3.0)]
    assert [s.text for s in got] == ["One.", "Two...", "Three."] and got[1].montage is False
    assert narration.slots(captions((0.0, 1.0, "x"), phase="montage"), 1.0)[0].montage is True
    with pytest.raises(ValueError, match="ends at 2.5"):
        narration.slots(caps, 2.4)
    with pytest.raises(ValueError, match="no text"):
        narration.slots(captions((0.0, 1.0, "   ")), 1.0)
    with pytest.raises(ValueError, match="no captions"):
        narration.slots([], 1.0)


def test_retry_speed_is_bounded_and_only_asked_for_when_the_line_overflows(narration):
    assert narration.retry_speed(1.0, 1.2, base=1.08) is None  # fits
    assert narration.retry_speed(1.3, 1.0, base=1.0) == 1.2  # would need 1.33: capped
    assert narration.retry_speed(1.1, 1.0, base=1.0) == 1.12  # 1.1 × 1.02 margin
    assert narration.retry_speed(1.3, 1.0, base=1.2) is None  # already at the cap: nothing more to ask


def test_place_fits_leads_quickens_or_cuts_within_bounds(narration):
    long = narration.Slot("01", "x", False, start=10.0, end=12.0)
    p = narration.place(1.5, long, prev_end=9.0)
    assert (p.start, p.kept, p.lead, p.tempo, p.cut) == (10.0, 1.5, 0.0, 1.0, False)
    p = narration.place(2.2, long, prev_end=9.0)  # overflows by 0.2: starts 0.2 early, nothing else
    assert (round(p.start, 3), round(p.kept, 3), round(p.lead, 3), p.tempo, p.cut) == (9.8, 2.2, 0.2, 1.0, False)
    p = narration.place(2.6, long, prev_end=9.0)  # needs 0.6: the lead is capped at 0.5, the rest is tempo
    assert (round(p.start, 3), round(p.kept, 3), round(p.lead, 3), round(p.tempo, 3), p.cut) == (
        9.5,
        2.5,
        0.5,
        1.04,
        False,
    )
    p = narration.place(3.5, long, prev_end=9.0)  # lead and tempo both capped: the tail is cut
    assert (round(p.start, 3), round(p.kept, 3), round(p.tempo, 3), p.cut) == (9.5, 2.5, 1.15, True)
    p = narration.place(2.6, long, prev_end=9.9)  # the previous line ends late: lead limited by it
    assert (round(p.start, 3), round(p.lead, 3), round(p.tempo, 3), round(p.kept, 3), p.cut) == (
        9.94,
        0.06,
        1.15,
        2.06,
        True,
    )
    frag = narration.Slot("02", "He...", True, start=5.0, end=5.3)
    p = narration.place(0.6, frag, prev_end=4.0)  # montage fragments are cut, never led or quickened
    assert (p.start, round(p.kept, 3), p.lead, p.tempo, p.cut) == (5.0, 0.3, 0.0, 1.0, True)
    with pytest.raises(ValueError, match="no room"):
        narration.place(0.6, narration.Slot("03", "x", True, start=5.0, end=5.0), prev_end=4.0)


def test_plan_asks_a_line_to_hurry_when_the_next_one_cannot_fit_otherwise(narration):
    base = BASE
    natural = {0: 1.9, 1: 1.5, 2: 0.4}
    asked = []

    def measure(i, speed):
        asked.append((i, speed))
        return natural[i] * base / speed

    plan = [
        narration.Slot("01", "a", False, start=0.0, end=2.0),
        narration.Slot("02", "b", False, start=2.02, end=3.0),
        narration.Slot("03", "c", True, start=3.02, end=3.5),
    ]
    out = narration.plan_narration(plan, measure, base)
    first, second, third = out
    assert first.speed == narration.MAX_SPEED and round(first.speech, 3) == 1.71 and not first.at.cut
    assert second.speed == narration.MAX_SPEED and not second.at.cut and round(second.at.lead, 3) == 0.27
    assert round(second.at.start + second.at.kept, 3) <= 3.0 and third.at == narration.place(third.speech, plan[2], 0)
    # base for every line, one retry for the second, one hurry for the first: never more than three a line
    assert asked == [(0, base), (1, base), (1, narration.MAX_SPEED), (0, narration.MAX_SPEED), (2, base)]
    # when the next line fits on its own, the line before is left at its natural pace
    natural[1] = 0.9
    asked.clear()
    out = narration.plan_narration(plan, measure, base)
    assert out[0].speed == base and asked == [(0, base), (1, base), (2, base)]


def wav(path: Path, seconds=0.5):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x10\x00" * int(RATE * seconds))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root: Path, **changes):
    (root / "audio").mkdir(exist_ok=True)
    digest = wav(root / "audio" / "vo-01.wav")
    item = {
        "id": "01",
        "text": "One.",
        "phase": "test",
        "caption_start": 0.1,
        "start": 0.1,
        "duration": 0.5,
        "speech_duration": 0.5,
        "speed": 1.08,
        "lead": 0.0,
        "tempo": 1.0,
        "lag": 0.0,
        "cut": False,
        "audio": "audio/vo-01.wav",
        "sha256": digest,
    }
    item.update(changes)
    (root / "narration.json").write_text(json.dumps({"items": [item]}))
    return root / "narration.json"


def test_plan_relaxed_keeps_the_natural_pace_and_lets_full_lines_spill(narration):
    plan = [
        narration.Slot("01", "a", False, start=0.0, end=2.0),
        narration.Slot("02", "b", False, start=2.02, end=3.0),
        narration.Slot("03", "c...", True, start=3.02, end=3.5),
        narration.Slot("04", "d", False, start=3.52, end=4.0),
    ]
    at, needed = narration.plan_relaxed(plan, [2.4, 1.0, 0.9, 1.1], lag_max=0.9, guard=0.04, tail=0.3)
    # 01 spills 0.4 s past its caption and is not cut; 02 starts when it ends plus the guard, 0.42 s late
    assert (at[0].start, at[0].kept, at[0].tempo, at[0].cut, at[0].lag) == (0.0, 2.4, 1.0, False, 0.0)
    assert (round(at[1].start, 3), round(at[1].lag, 3)) == (2.44, 0.42)
    # 03 is a montage fragment: on its caption, cut where the caption ends; the spilling line before it is cut
    # a guard before it (02 would have ended at 3.44)
    assert (at[2].start, round(at[2].kept, 3), at[2].cut, at[2].lag) == (3.02, 0.48, True, 0.0)
    assert (round(at[1].start + at[1].kept, 3), round(at[1].kept, 3), at[1].cut) == (2.98, 0.54, True)
    # 04 runs past the project: the project needs the tail after it
    assert (at[3].start, at[3].kept, at[3].cut) == (3.52, 1.1, False) and round(needed, 3) == 4.92
    # a lag beyond the bound cuts the spilling line instead of delaying the next one further
    at, needed = narration.plan_relaxed(plan[:2], [3.5, 0.5], lag_max=0.5, guard=0.04, tail=0.3)
    assert (round(at[1].start, 3), round(at[1].lag, 3)) == (2.52, 0.5)
    assert (round(at[0].kept, 3), at[0].cut) == (2.48, True) and round(needed, 3) == 3.32
    assert all(a.lead == 0.0 and a.tempo == 1.0 for a in at)
    with pytest.raises(narration.NarrationError, match="one speech"):
        narration.plan_relaxed(plan, [1.0])
    with pytest.raises(narration.NarrationError, match="positive"):
        narration.plan_relaxed(plan[:1], [0.0])
    with pytest.raises(narration.NarrationError, match="lag_max"):
        narration.plan_relaxed(plan[:1], [1.0], lag_max=-1)
    assert narration.plan_relaxed([], []) == ([], 0.0)


def test_conform_plays_faster_within_its_bound(narration, tmp_path):
    wav(tmp_path / "in.wav", seconds=1.0)
    got = narration.conform(tmp_path / "in.wav", tmp_path / "out.wav", 0.0, 1.0, 0.8, 0.0, tempo=1.25)
    assert abs(got - 0.8) < 1.5 / RATE
    with pytest.raises(ValueError, match="tempo"):
        narration.conform(tmp_path / "in.wav", tmp_path / "out.wav", 0.0, 1.0, 0.8, 0.0, tempo=1.6)


def test_the_manifest_lag_is_optional_and_effects_and_duration_are_checked(narration, tmp_path):
    import json

    path = manifest(tmp_path)
    data = json.loads(path.read_text())
    del data["items"][0]["lag"]  # a manifest from the fitted policy has no lag
    path.write_text(json.dumps(data))
    assert len(narration.narration_cues(path, tmp_path)) == 1
    assert narration.effect_cues(path, tmp_path) == []  # no effects key: none
    with pytest.raises(narration.NarrationError, match="lag"):
        narration.narration_cues(manifest(tmp_path, lag="late"), tmp_path)
    with pytest.raises(narration.NarrationError, match="duration"):
        narration.manifest_duration(path)
    digest = wav(tmp_path / "audio" / "typing.wav")
    fx = {"id": "typing", "start": 0.0, "gain_db": -14, "audio": "audio/typing.wav", "sha256": digest}
    data = json.loads(manifest(tmp_path).read_text())
    data["duration"] = 44.5
    data["effects"] = [fx]
    path.write_text(json.dumps(data))
    assert narration.manifest_duration(path) == 44.5
    assert narration.effect_cues(path, tmp_path) == [narration.Effect("typing", 0.0, -14.0, "audio/typing.wav", digest)]
    data["effects"] = [dict(fx, taps=[0.5, 0.52, 1.0])]
    path.write_text(json.dumps(data))
    assert narration.effect_cues(path, tmp_path)[0].taps == (0.5, 0.52, 1.0)
    for bad, match in (
        (dict(fx, taps=[0.5, 0.4]), "order"),
        (dict(fx, taps=[0.5, "soon"]), "taps"),
        (dict(fx, taps=[-1]), "taps"),
        (dict(fx, taps=0.5), "taps"),
        (dict(fx, sha256="0" * 64), "sha256"),
        (dict(fx, audio="audio/none.wav"), "missing"),
        (dict(fx, gain_db=3), "gain_db"),
        (dict(fx, start=-1), "start"),
        (dict(fx, loop=True), "unknown"),
        ({k: v for k, v in fx.items() if k != "id"}, "missing"),
        ("typing", "object"),
    ):
        data["effects"] = [bad]
        path.write_text(json.dumps(data))
        with pytest.raises(narration.NarrationError, match=match):
            narration.effect_cues(path, tmp_path)
    data["effects"] = {"id": "typing"}
    path.write_text(json.dumps(data))
    with pytest.raises(narration.NarrationError, match="list"):
        narration.effect_cues(path, tmp_path)
    for value in (0, -1, True, "44", None):
        data["duration"] = value
        path.write_text(json.dumps(data))
        with pytest.raises(narration.NarrationError, match="duration"):
            narration.manifest_duration(path)
    path.write_text("[]")
    with pytest.raises(narration.NarrationError, match="object"):
        narration.manifest_duration(path)


def test_narration_cues_verify_the_manifest_and_the_files(narration, tmp_path):
    cues = narration.narration_cues(manifest(tmp_path), tmp_path)
    assert [(c.id, c.start, c.duration, c.audio) for c in cues] == [("01", 0.1, 0.5, "audio/vo-01.wav")]
    with pytest.raises(ValueError, match="sha256"):
        narration.narration_cues(manifest(tmp_path, sha256="0" * 64), tmp_path)
    with pytest.raises(ValueError, match="missing"):
        path = manifest(tmp_path)
        data = json.loads(path.read_text())
        del data["items"][0]["start"]
        path.write_text(json.dumps(data))
        narration.narration_cues(path, tmp_path)
    with pytest.raises(ValueError, match="unknown"):
        narration.narration_cues(manifest(tmp_path, extra=1), tmp_path)
    with pytest.raises(ValueError, match="duration"):
        narration.narration_cues(manifest(tmp_path, duration=0), tmp_path)
    with pytest.raises(ValueError, match="audio/vo-01.wav"):
        path = manifest(tmp_path)
        (tmp_path / "audio" / "vo-01.wav").unlink()
        narration.narration_cues(path, tmp_path)
    with pytest.raises(ValueError, match="items"):
        path.write_text(json.dumps({"items": "no"}))
        narration.narration_cues(path, tmp_path)


def test_the_library_raises_its_own_error_type_and_takes_no_episode_defaults(narration, tmp_path):
    assert issubclass(narration.NarrationError, ValueError)
    with pytest.raises(narration.NarrationError, match="no captions"):
        narration.slots([], 1.0)
    with pytest.raises(narration.NarrationError, match="missing"):
        narration.narration_cues(manifest(tmp_path, audio="audio/gone.wav"), tmp_path)
    with pytest.raises(TypeError):  # the base speed is the episode's choice, never a library default
        narration.plan_narration([], lambda i, s: 0.0)  # type: ignore[call-arg]
    assert narration.plan_narration([], lambda i, s: 0.0, BASE) == []
