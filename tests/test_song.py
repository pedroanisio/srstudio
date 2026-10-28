"""A sung Soft episode's audio: the song's checks, its declarations, the speech check, beat placement, the build."""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import wave
from pathlib import Path

import pytest

from fakes import ffmpeg_required, make_mp3
from srstudio import song as S
from srstudio.generated import PLACEHOLDER, Resolved, ResolveError, sha256_of
from srstudio.music import Groove, Section
from srstudio.voice import Transcript, Word

RATE = 48000
GROOVE = Groove(bpm=120)  # one bar = 2 s


def make_song(**changes) -> S.Song:
    kw: dict = dict(
        slug="test-song",
        title="Test Song",
        seed=7,
        groove=GROOVE,
        voices={
            "pip": S.Singer("bIHbv24MWmeRgasZH58o", "Will", {"stability": 0.3, "similarity_boost": 0.75, "style": 0.4})
        },
        lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0)), S.Line("pip", "Work.", "WORK.", (1, 0), 1.08)],
        sections=[Section(0, 2)],
        effects=[S.Effect("scratch", "a record scratch", seconds=1.0, longest=0.5, peak=0.5, at=(1, 2))],
        lines_end=GROOVE.at(2),
        voice_note="test voices",
    )
    kw.update(changes)
    return S.Song(**kw)


def tone(path: Path, seconds: float, lead: float = 0.1, amplitude: float = 0.5) -> Path:
    """``lead`` seconds of silence, then ``seconds`` of tone, then 0.1 s of silence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_lead, n_on, n_tail = round(lead * RATE), round(seconds * RATE), round(0.1 * RATE)
    samples = [0.0] * n_lead + [amplitude * math.sin(i * 0.05) for i in range(n_on)] + [0.0] * n_tail
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(round(s * 32767).to_bytes(2, "little", signed=True) for s in samples))
    return path


def pins_for(tmp_path: Path, song: S.Song, speech: dict[int, float]) -> dict[str, Resolved]:
    lines, effects = S.declarations(song)
    out = {}
    for i, item in enumerate(lines):
        p = tone(tmp_path / f"{item.id}.wav", speech[i])
        out[item.id] = Resolved(item, p, sha256_of(p))
    for item in effects:
        p = tone(tmp_path / f"{item.id}.wav", 0.8, lead=0.02)
        out[item.id] = Resolved(item, p, sha256_of(p))
    return out


# -- the song ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "changes, match",
    [
        (dict(lines=[]), "at least one line"),
        (dict(lines=[S.Line("boss", "Hi.", "Hi.", (0, 0))]), "no voice for role 'boss'"),
        (dict(lines=[S.Line("pip", "B.", "B.", (1, 0)), S.Line("pip", "A.", "A.", (0, 0))]), "in order"),
        (dict(lines=[S.Line("pip", "  ", "x", (0, 0))]), "no text"),
        (dict(lines=[S.Line("pip", "Hi.", "Hi.", (0, 0), 1.5)]), "speed"),
        (dict(effects=[make_song().effects[0], make_song().effects[0]]), "unique"),
        (dict(effects=[S.Effect("line-1", "x", 1.0, 0.5, 0.5, (0, 0))]), "line-"),
        (dict(effects=[S.Effect("fx", "x", 1.0, 1.5, 0.5, (0, 0))]), "longest"),
        (dict(effects=[S.Effect("fx", "x", 1.0, 0.5, 0.0, (0, 0))]), "peak"),
        (dict(lines_end=float("nan")), "lines_end"),
        (dict(voices={"pip": S.Singer("x", "Will", {"stability": 0.3})}), "not voice settings"),
        (dict(voices={"pip": S.Singer("x", "Will", {"stability": 3, "similarity_boost": 0.7, "style": 0})}), "voice"),
    ],
)
def test_a_malformed_song_is_refused_before_anything_is_requested(changes, match):
    with pytest.raises(S.SongError, match=match):
        make_song(**changes)


def test_declarations_name_one_speech_item_per_line_and_one_effect_each():
    lines, effects = S.declarations(make_song())
    assert [g.id for g in lines] == ["line-1", "line-2"] and [g.id for g in effects] == ["scratch"]
    assert lines[1].voice.startswith("bIHbv24MWmeRgasZH58o?") and "speed=1.08" in lines[1].voice
    assert "stability=0.3" in lines[0].voice and lines[0].cache == "assets/generated/line-1.wav"
    assert lines[0].license.endswith("Will") and effects[0].duration == 1.0 and effects[0].kind == "sound-effect"


# -- speech check -----------------------------------------------------------------------------------------------
def heard(text: str) -> Transcript:
    return Transcript("en", 0.99, text, tuple(Word(w, 0.0, 0.1, "word") for w in text.split()))


def test_hear_reports_every_line_and_collects_each_mismatch(tmp_path):
    song = make_song()
    pins = pins_for(tmp_path, song, {0: 0.5, 1: 0.4})
    report, failures = S.hear(song, pins, lambda p: heard("Sit down." if "line-1" in p.name else "Walk."))
    assert [r["heard"] for r in report["lines"]] == ["Sit down.", "Walk."] and report["passed"] is False
    assert len(failures) == 1 and "Work" in failures[0]
    report, failures = S.hear(song, pins, lambda p: heard("Sit down." if "line-1" in p.name else "Work."))
    assert report["passed"] and not failures


# -- placement on the beat ----------------------------------------------------------------------------------------
def test_place_puts_each_line_on_its_beat_and_each_effect_just_before_its_own(tmp_path):
    song = make_song()
    placed = S.place(song, pins_for(tmp_path, song, {0: 0.5, 1: 0.4}))
    starts = [p["start"] for p in placed.phrases]
    assert starts == [GROOVE.at(0, 0), GROOVE.at(1, 0)]
    for phrase in placed.phrases:
        assert phrase["end"] > phrase["start"] and phrase["voice_name"] == "Will"
    assert placed.effect_starts == {"scratch": round(GROOVE.at(1, 2) - 0.04, 6)}
    assert [c.generated.id for c in placed.clips] == ["line-1", "line-2", "scratch"]
    gains = {c.placement.gain_db for c in placed.clips[:2]}
    assert len(gains) == 1, "every line is levelled by the one loudest line, so the lines keep their balance"


def test_a_line_that_runs_into_the_next_stops_the_build_instead_of_overlapping(tmp_path):
    song = make_song()
    with pytest.raises(S.SongError, match="line 1 'Sit down.' runs to"):
        S.place(song, pins_for(tmp_path, song, {0: 2.2, 1: 0.4}))
    with pytest.raises(S.SongError, match="line 2"):  # the last line is bounded by lines_end
        S.place(song, pins_for(tmp_path, song, {0: 0.5, 1: 2.2}))


# -- the build, through the engine and a fake ElevenLabs ---------------------------------------------------------
def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


@pytest.fixture
def fake_env(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    assert make_mp3(tmp_path / "tone.mp3")
    return {
        "SR_PROVIDER_SRSTUDIO_ELEVENLABS": f"{sys.executable} {Path(__file__).parent / 'fake_provider.py'}",
        "FAKE_MP3": str(tmp_path / "tone.mp3"),
        "FAKE_LOG": str(tmp_path / "calls.log"),
    }


class FakeFont:
    family, weight, license, sha256 = "Poppins", 700, "OFL-1.1", "0" * 64


@ffmpeg_required
def test_build_resolves_checks_places_mixes_and_writes_the_dialogue(tmp_path, fake_env):
    song = make_song(lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0))], lines_end=GROOVE.at(2))
    root = tmp_path / "project"
    fonts_asked = []
    out = S.build(
        song,
        root,
        engine=engine(),
        key="sk-test",
        env=fake_env,
        extra=lambda starts: {"scratch_start": starts["scratch"]},
        install_font=lambda font, folder: fonts_asked.append(font.family) or FakeFont(),
    )
    data = json.loads(out.read_text())
    assert out == root / "dialogue.json" and data["bpm"] == 120 and data["scratch_start"] == pytest.approx(2.96)
    assert [p["text"] for p in data["phrases"]] == ["Sit down."] and len(data["clips"]) == 2
    assert all(c["sha256"] != PLACEHOLDER for c in data["clips"])
    assert (root / "assets" / "groove.wav").exists() and fonts_asked == ["Poppins"]
    assert data["duration"] == pytest.approx(math.ceil((GROOVE.at(2) + S.TAIL) * 30) / 30, abs=1 / 30)
    assert json.loads((root / "voice-transcript.json").read_text())["passed"] is True
    assert "sk-test" not in out.read_text() and "sk-test" not in (root / "test-song.audio.scene.xml").read_text()


@ffmpeg_required
def test_build_stops_when_the_engine_rejects_a_misheard_line(tmp_path, fake_env):
    song = make_song(lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0))], effects=[])
    root = tmp_path / "project"
    with pytest.raises(ResolveError, match="heard"):
        S.build(song, root, engine=engine(), key="sk-test", env={**fake_env, "FAKE_HEARD": "Sit town."})
    assert not (root / "dialogue.json").exists()


def test_main_needs_an_engine(tmp_path, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="no scene-render engine"):
        S.main(make_song(), argv=[str(tmp_path)])


@ffmpeg_required
def test_a_font_that_fails_its_checks_stops_the_build_and_main_runs_it_from_the_command_line(
    tmp_path, fake_env, monkeypatch, capsys
):
    from srstudio import fonts

    song = make_song(lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0))], effects=[])
    root = tmp_path / "project"

    def bad_font(font, folder):
        raise fonts.FontError("licence missing")

    with pytest.raises(S.SongError, match="caption font: licence missing"):
        S.build(song, root, engine=engine(), key="sk-test", env=fake_env, install_font=bad_font)
    for k, v in {**fake_env, "ELEVENLABS_API_KEY": ""}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("'sk-test'\n"))
    monkeypatch.setattr(S, "build", _with_font(S.build))
    assert S.main(song, argv=[str(root), "--key-stdin", "--engine", str(engine())]) == 0
    assert json.loads((root / "dialogue.json").read_text())["phrases"][0]["text"] == "Sit down."
    monkeypatch.setattr(S, "build", lambda *a, **k: (_ for _ in ()).throw(S.SongError("speech check failed")))
    with pytest.raises(SystemExit, match="speech check failed"):
        S.main(song, argv=[str(root), "--engine", str(engine())])


def _with_font(build):
    def run(*args, **kw):
        return build(*args, install_font=lambda font, folder: FakeFont(), **kw)

    return run
