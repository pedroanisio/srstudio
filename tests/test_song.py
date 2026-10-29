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


def test_a_near_silent_take_stops_the_build_instead_of_being_boosted(tmp_path):
    song = make_song()
    pins = pins_for(tmp_path, song, {0: 0.5, 1: 0.4})
    quiet = tone(tmp_path / "quiet-scratch.wav", 0.8, lead=0.02, amplitude=0.004)  # a take the model left silent
    pins["scratch"] = Resolved(pins["scratch"].generated, quiet, sha256_of(quiet))
    with pytest.raises(S.SongError, match="effect scratch is near-silent"):
        S.place(song, pins)
    pins = pins_for(tmp_path, song, {0: 0.5, 1: 0.4})
    for item in S.declarations(song)[0]:
        whisper = tone(tmp_path / f"quiet-{item.id}.wav", 0.4, amplitude=0.02)  # +32 dB to level
        pins[item.id] = Resolved(item, whisper, sha256_of(whisper))
    with pytest.raises(S.SongError, match="lines are near-silent"):
        S.place(song, pins)


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


# -- a composed song: the music sings the lines of one role, the rest is spoken over it -----------------------------
from srstudio import compose as C  # noqa: E402

STYLES = ("120 BPM", "office pop", "male vocal")
PLAN = C.Plan(
    (
        C.Chunk("Hook", 4.0, STYLES, ("Sit down.",)),
        C.Chunk("Break", 4.0, ("120 BPM", "instrumental")),
        C.Chunk("Out", 4.0, STYLES, ("Work, work.",)),
    )
)
BOSS = S.Singer("cjVigY5qzO86Huf0OWal", "Eric", {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15})


def composed_song(**changes) -> S.Song:
    kw: dict = dict(
        voices={"boss": BOSS},
        lines=[
            S.Line("pip", "Sit down.", "SIT DOWN.", None),
            S.Line("boss", "Slides.", "BOSS: Slides.", (2, 0.5)),
            S.Line("pip", "Work, work.", "WORK!", None),
        ],
        sections=[],
        composition=S.Composition(PLAN, seed=82043, role="pip"),
        lines_end=12.0,
    )
    kw.update(changes)
    return make_song(**kw)


def sung_transcript(*timed) -> Transcript:
    return Transcript("en", 0.99, " ".join(w for w, *_ in timed), tuple(Word(w, a, b, "word") for w, a, b in timed))


HEARD = sung_transcript(("Sit", 0.2, 0.5), ("down.", 0.55, 1.1), ("Work,", 8.3, 8.7), ("work.", 8.8, 9.4))


def fake_composer(tmp_path, calls=None, seconds=12.0):
    def compose_song(plan, seed, bpm):
        if calls is not None:
            calls.append((plan, seed, bpm))
        wav = tone(tmp_path / "music-x.wav", seconds - 0.2)
        return C.Song(
            plan, seed, tmp_path / "music-x.mp3", wav, tmp_path / "music-x.json", seconds, C.Tempo(120.0, 0.02, 0.3)
        )

    return compose_song


@pytest.mark.parametrize(
    "changes, match",
    [
        (dict(lines=[S.Line("pip", "Stand up.", "x", None), S.Line("pip", "Work, work.", "x", None)]), "lyrics"),
        (dict(lines=[S.Line("pip", "Sit down.", "x", None)]), "lyrics"),
        (dict(lines=[S.Line("pip", "Sit down.", "x", (0, 0)), S.Line("pip", "Work, work.", "x", None)]), "sung"),
        (dict(lines=[S.Line("boss", "Hi.", "x", None)]), "beat"),
        (dict(composition=S.Composition(PLAN, seed=-1, role="pip")), "seed"),
    ],
)
def test_a_composed_song_must_sing_exactly_its_plan_lyrics(changes, match):
    with pytest.raises(S.SongError, match=match):
        composed_song(**changes)


def test_only_spoken_lines_are_synthesised_and_heard_line_by_line(tmp_path):
    song = composed_song()
    lines, _ = S.declarations(song)
    assert [g.id for g in lines] == ["line-2"] and lines[0].license.endswith("Eric")
    pins = {"line-2": Resolved(lines[0], tone(tmp_path / "line-2.wav", 0.8), "0" * 64)}
    report, failures = S.hear(song, pins, lambda p: heard("Slides."))
    assert [r["expected"] for r in report["lines"]] == ["Slides."] and not failures


def test_sing_composes_once_and_finds_every_sung_line_with_its_words(tmp_path):
    calls = []
    sung = S.sing(composed_song(), fake_composer(tmp_path, calls), lambda wav: HEARD)
    assert calls == [(PLAN, 82043, 120)]
    assert sung.spans == [(0.2, 1.1), (8.3, 9.4)]
    assert sung.words == [[["Sit", 0.2, 0.5], ["down.", 0.55, 1.1]], [["Work,", 8.3, 8.7], ["work.", 8.8, 9.4]]]
    assert sung.report == {"heard": HEARD.text, "passed": True}


def test_a_song_that_drops_a_lyric_stops_the_build(tmp_path):
    with pytest.raises(S.SongError, match="'Work, work.' not sung"):
        S.sing(
            composed_song(), fake_composer(tmp_path), lambda wav: sung_transcript(("Sit", 0.2, 0.5), ("down.", 0.5, 1))
        )


def test_a_song_that_fails_its_checks_stops_the_build(tmp_path):
    def off_tempo(plan, seed, bpm):
        raise C.MusicOutputError("tempo: the beat runs at about 100.0 bpm, not 120 bpm")

    with pytest.raises(S.SongError, match="song: tempo"):
        S.sing(composed_song(), off_tempo, lambda wav: HEARD)


def test_place_puts_sung_lines_where_they_were_heard_and_spoken_lines_on_their_beat(tmp_path):
    song = composed_song()
    lines, _ = S.declarations(song)
    pins = {"line-2": Resolved(lines[0], tone(tmp_path / "line-2.wav", 1.0), sha256_of(tmp_path / "line-2.wav"))}
    pins.update(
        {e.id: Resolved(e, tone(tmp_path / f"{e.id}.wav", 0.8, lead=0.02), "0" * 64) for e in S.declarations(song)[1]}
    )
    sung = S.sing(song, fake_composer(tmp_path), lambda wav: HEARD)
    placed = S.place(song, pins, sung)
    assert [(p["role"], p["start"]) for p in placed.phrases] == [
        ("pip", 0.2),
        ("boss", GROOVE.at(2, 0.5)),
        ("pip", 8.3),
    ]
    assert placed.phrases[0]["sung"] is True and placed.phrases[0]["words"] == sung.words[0]
    assert placed.phrases[0]["end"] == 1.1 and "sung" not in placed.phrases[1]
    assert [c.generated.id for c in placed.clips] == ["line-2", "scratch"]


def test_a_spoken_line_over_a_sung_one_stops_the_build(tmp_path):
    song = composed_song(
        lines=[
            S.Line("pip", "Sit down.", "x", None),
            S.Line("boss", "Slides.", "x", (0, 1)),  # 0.5 s: inside "Sit down." (0.2-1.1)
            S.Line("pip", "Work, work.", "x", None),
        ]
    )
    lines, _ = S.declarations(song)
    pins = {"line-2": Resolved(lines[0], tone(tmp_path / "line-2.wav", 1.0), "0" * 64)}
    pins.update({e.id: Resolved(e, tone(tmp_path / f"{e.id}.wav", 0.8), "0" * 64) for e in S.declarations(song)[1]})
    with pytest.raises(S.SongError, match="line 1 'Sit down.' runs to 1.100s"):
        S.place(song, pins, S.sing(song, fake_composer(tmp_path), lambda wav: HEARD))


def test_place_needs_the_sung_lines_for_a_composed_song(tmp_path):
    with pytest.raises(S.SongError, match="sing"):
        S.place(composed_song(), {})


@ffmpeg_required
def test_build_of_a_composed_song_writes_the_music_and_its_record(tmp_path, fake_env):
    song = composed_song()
    root = tmp_path / "project"
    out = S.build(
        song,
        root,
        engine=engine(),
        key="sk-test",
        env={**fake_env, "FAKE_HEARD": "Slides."},
        install_font=lambda font, folder: FakeFont(),
        compose_song=fake_composer(tmp_path),
        transcribe_song=lambda wav: HEARD,
    )
    data = json.loads(out.read_text())
    assert [p["text"] for p in data["phrases"]] == ["Sit down.", "Slides.", "Work, work."]
    assert (root / "assets" / "music.wav").read_bytes() == (tmp_path / "music-x.wav").read_bytes()
    assert not (root / "assets" / "groove.wav").exists()
    assert data["music"]["file"] == "assets/music.wav" and data["music"]["seed"] == 82043
    assert data["music"]["plan"] == PLAN.to_dict() and data["music"]["tempo"]["bpm"] == 120.0
    assert data["music"]["sha256"] == sha256_of(root / "assets" / "music.wav")
    assert data["duration"] == pytest.approx(math.ceil((12.0 + S.TAIL) * 30) / 30)
    report = json.loads((root / "voice-transcript.json").read_text())
    assert report["passed"] and report["song"]["passed"] and report["song"]["heard"] == HEARD.text


def test_sing_needs_a_composition(tmp_path):
    with pytest.raises(S.SongError, match="no composition"):
        S.sing(make_song(), fake_composer(tmp_path), lambda wav: HEARD)


# -- an instrumental composition: no role is sung, every line is spoken over it ------------------------------------
GROOVE_PLAN = C.Plan((C.Chunk("Groove", 4.0, ("120 BPM", "instrumental")), C.Chunk("Out", 4.0, ("120 BPM",))))


def instrumental_song(**changes) -> S.Song:
    kw: dict = dict(
        voices={"boss": BOSS},
        lines=[S.Line("boss", "Slides.", "BOSS: Slides.", (1, 0))],
        sections=[],
        composition=S.Composition(GROOVE_PLAN, seed=7, role=None),
        lines_end=8.0,
    )
    kw.update(changes)
    return make_song(**kw)


def test_an_instrumental_composition_sings_no_line_and_its_plan_has_no_lyrics():
    song = instrumental_song()
    assert not any(song.sung(line) for line in song.lines)
    assert [g.id for g in S.declarations(song)[0]] == ["line-1"]
    with pytest.raises(S.SongError, match="lyrics"):
        instrumental_song(composition=S.Composition(PLAN, seed=7, role=None))


def test_an_instrumental_take_with_no_words_passes(tmp_path):
    events = Transcript("en", 0.99, "(upbeat music)", (Word("(upbeat music)", 0.0, 8.0, "audio_event"),))
    sung = S.sing(instrumental_song(), fake_composer(tmp_path, seconds=8.0), lambda wav: events)
    assert sung.spans == [] and sung.words == [] and sung.report["passed"]


@pytest.mark.parametrize("words", [(("Yeah", 1.0, 1.3),), (("la", 0.1, 0.2), ("la", 5.0, 5.2))])
def test_an_instrumental_take_with_heard_words_stops_the_build(tmp_path, words):
    with pytest.raises(S.SongError, match="instrumental"):
        S.sing(instrumental_song(), fake_composer(tmp_path, seconds=8.0), lambda wav: sung_transcript(*words))
