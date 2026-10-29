"""The voiced-take pipeline: the script's checks, the recorded timeline, the speech check and the music bed.

Fakes stand in for the provider (speech, effects, recognition, music); ffmpeg is real, as in test_narration.py."""

import json
import math
import struct
import wave
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from srstudio import takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import RATE, Alignment, EffectClip, SpokenLine, Transcript, Voice, VoiceSettings, Word

DEV = Voice(role="dev", id="dev123", name="Will")
SETTINGS = {"dev": VoiceSettings(0.45, 0.75, 0.3)}
BED_PLAN = Plan((Chunk("Bed", 6.0, ("instrumental", "light ukulele")),))


def tone(path: Path, seconds: float, amplitude: float = 0.5, channels: int = 1) -> Path:
    n = round(seconds * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frame = lambda i: struct.pack("<h", round(amplitude * 32767 * math.sin(i * 0.05)))  # noqa: E731
        w.writeframes(b"".join(frame(i) * channels for i in range(n)))
    return path


def script(**changes) -> takes.Script:
    base = dict(
        title="Test — Stick 99",
        seed=7,
        voices={"dev": DEV},
        settings=SETTINGS,
        takes=(
            takes.Take("01", "dev", "Repeat after me.", 0.2, shot="drive", mood="calm", extra={"beat": "vow"}),
            takes.Take("02", "dev", "Repeat after me.", 0.1, shot="push", speed=1.1),
            takes.Take("03", "sfx", "[BUZZ]", 0.1, shot="seat", prompt="a phone buzzing", seconds=1.0, longest=0.5),
        ),
        voice_note="premade voice Will",
        shots=("drive", "push", "seat"),
    )
    return takes.Script(**{**base, **changes})


@dataclass
class Composed:
    wav: Path
    duration: float


class Provider:
    """Speech is a tone whose alignment spells the line; recognition hears what ``heard`` says."""

    def __init__(self, root: Path, heard=None, music_words=()):
        self.root, self.heard, self.music_words = root, heard or {}, music_words
        self.spoken: list[tuple[str, VoiceSettings]] = []
        self.composed: list[tuple[Plan, int, float]] = []

    def synthesize(self, text, voice, settings):
        self.spoken.append((text, settings))
        wav = tone(self.root / f"speech-{len(self.spoken)}.wav", 1.2)
        n, step = len(text), 0.8 / len(text)
        alignment = Alignment(
            tuple(text), tuple(0.2 + i * step for i in range(n)), tuple(0.2 + (i + 1) * step for i in range(n))
        )
        return SpokenLine(text, voice, settings, alignment, wav, self.root / "timing.json", 1.2)

    def transcribe(self, path):
        path = Path(path)
        if path.name.startswith("music"):
            words = tuple(Word(w, 1.0, 1.2, "word") for w in self.music_words)
            return Transcript("en", 1.0, " ".join(self.music_words), words)
        text = self.heard.get(path.name, None)
        if text is None:
            text = self.spoken[int(path.stem.split("-")[1]) - 1][0]
        return Transcript("en", 1.0, text, tuple(Word(w, 0, 0, "word") for w in text.split()))

    def sound_effect(self, prompt, seconds):
        wav = tone(self.root / "effect.wav", seconds, 0.3)
        return EffectClip(prompt, seconds, wav, self.root / "effect.json", seconds)

    def compose(self, plan, seed, bpm):
        self.composed.append((plan, seed, bpm))
        return Composed(tone(self.root / "music.wav", plan.seconds, 0.4, channels=2), plan.seconds)


def confirm(voice):
    return {"voice_id": voice.id, "name": voice.name, "category": "premade"}


def run(tmp_path, s=None, provider=None, **kw):
    provider = provider or Provider(tmp_path)
    root = tmp_path / "project"
    timeline = takes.record(s or script(), root, client=provider, confirm=confirm, compose=provider.compose, **kw)
    return root, timeline, provider


def test_record_writes_the_takes_their_words_and_a_frame_rounded_timeline(tmp_path):
    root, timeline, provider = run(tmp_path)
    items = timeline["items"]
    assert [q["id"] for q in items] == ["01", "02", "03"] and items[0]["beat"] == "vow" and "beat" not in items[1]
    assert [w["text"] for w in items[0]["words"]] == ["Repeat", "after", "me."] and items[0]["phones"]
    assert items[0]["start"] == 0 and items[1]["start"] == pytest.approx(items[0]["duration"])
    assert items[2]["speech_duration"] == 0 and items[2]["generator"] == "ElevenLabs sound generation"
    assert timeline["duration"] * 24 == pytest.approx(round(timeline["duration"] * 24))
    assert timeline["voices"] == {"dev": confirm(DEV)} and "music" not in timeline
    assert provider.spoken[1][1].speed == 1.1 and provider.spoken[0][1].speed == 1.0  # a take's own pace
    on_disk = json.loads((root / "timeline.json").read_text())
    assert on_disk == timeline and (root / items[0]["audio"]).exists()
    assert json.loads((root / "voice-transcript.json").read_text())["passed"] is True


def test_a_misheard_take_stops_the_recording_and_says_what_was_heard(tmp_path):
    provider = Provider(tmp_path, heard={"speech-2.wav": "Repeat after you."})
    with pytest.raises(takes.TakesError, match="take 02: heard 'Repeat after you.'"):
        run(tmp_path, provider=provider)
    report = json.loads((tmp_path / "project" / "voice-transcript.json").read_text())
    assert report["passed"] is False and not (tmp_path / "project" / "timeline.json").exists()


def test_the_bed_is_instrumental_conformed_to_the_episode_and_recorded(tmp_path):
    bed = takes.Bed(BED_PLAN, seed=11, bpm=96, gain_db=-12.0, fade=0.5)
    root, timeline, provider = run(tmp_path, script(bed=bed))
    music = timeline["music"]
    assert provider.composed == [(BED_PLAN, 11, 96)]
    assert music["file"] == "audio/music.wav" and music["gain_db"] == -12.0 and music["seed"] == 11
    with wave.open(str(root / music["file"]), "rb") as w:
        assert w.getnchannels() == 2 and w.getnframes() / w.getframerate() == pytest.approx(
            timeline["duration"], abs=1 / RATE
        )
    assert music["sha256"] == takes.sha256_of(root / music["file"]) and music["plan"] == BED_PLAN.to_dict()


@pytest.mark.parametrize(
    "plan, words, match",
    [
        (BED_PLAN, ("hello", "there"), "instrumental, but 'hello there' was heard"),
        (Plan((Chunk("Bed", 3.0, ("instrumental",)),)), (), "shorter than the episode"),
    ],
)
def test_a_bed_with_words_or_too_short_is_refused(tmp_path, plan, words, match):
    provider = Provider(tmp_path, music_words=words)
    with pytest.raises(takes.TakesError, match=match):
        run(tmp_path, script(bed=takes.Bed(plan, seed=11, bpm=96)), provider=provider)
    assert not (tmp_path / "project" / "timeline.json").exists()


def test_a_bed_the_composer_refuses_is_a_takes_error(tmp_path):
    from srstudio.compose import MusicOutputError

    provider = Provider(tmp_path)

    def off_tempo(plan, seed, bpm):
        raise MusicOutputError("tempo: the beat runs at about 230.8 bpm, not 96 bpm")

    with pytest.raises(takes.TakesError, match="bed: tempo"):
        takes.record(script(bed=takes.Bed(BED_PLAN, 11, 96)), tmp_path / "p", client=provider, confirm=confirm,
                     compose=off_tempo)  # fmt: skip


def test_a_bed_needs_a_composer(tmp_path):
    provider = Provider(tmp_path)
    with pytest.raises(takes.TakesError, match="no composer"):
        takes.record(script(bed=takes.Bed(BED_PLAN, 11, 96)), tmp_path / "p", client=provider, confirm=confirm)


@pytest.mark.parametrize(
    "take, match",
    [
        (dict(actor="printer"), "unknown actor"),
        (dict(shot="roof"), "unknown shot"),
        (dict(text="  "), "needs text"),
        (dict(hold=-1), "hold"),
        (dict(hold=math.nan), "hold"),
        (dict(speed=2.0), "speed"),
        (dict(actor="sfx", text="beep", prompt="x", seconds=1, longest=1), "bracketed"),
        (dict(actor="sfx", text="[X]", prompt="x", seconds=60, longest=1), "seconds"),
        (dict(actor="sfx", text="[X]", prompt="", seconds=1, longest=1), "prompt"),
    ],
)
def test_a_malformed_take_is_refused_before_anything_is_requested(take, match):
    base = takes.Take("99", "dev", "Hi.", 0.1, shot="drive")
    with pytest.raises(takes.TakesError, match=match):
        script(takes=(replace(base, **take),)).check()


@pytest.mark.parametrize(
    "changes, match",
    [
        (dict(takes=()), "at least one take"),
        (dict(takes=(takes.Take("02", "dev", "A.", 0), takes.Take("01", "dev", "B.", 0))), "unique and in order"),
        (dict(takes=(takes.Take("01", "dev", "A.", 0), takes.Take("01", "dev", "B.", 0))), "unique and in order"),
        (dict(settings={}), "no settings for dev"),
        (dict(voices={"sfx": Voice("sfx", "x", "X")}), "reserved"),
        (dict(fps=0), "fps"),
        (dict(bed=takes.Bed(BED_PLAN, seed=-1, bpm=96)), "seed"),
        (dict(bed=takes.Bed(BED_PLAN, seed=1, bpm=0)), "bpm"),
        (dict(bed=takes.Bed(BED_PLAN, seed=1, bpm=96, gain_db=3)), "gain"),
        (dict(bed=takes.Bed(BED_PLAN, seed=1, bpm=96, fade=-1)), "fade"),
    ],
)
def test_a_malformed_script_is_refused(changes, match):
    with pytest.raises(takes.TakesError, match=match):
        script(**changes).check()


def test_main_needs_consent_a_font_and_reports_a_failure_as_an_exit(tmp_path, monkeypatch):
    project = tmp_path / "p"
    with pytest.raises(SystemExit, match="SRSTUDIO_ALLOW_CLOUD"):
        takes.main(script(), [str(project)], env={})
    with pytest.raises(SystemExit, match="Inter-Bold.ttf is missing"):
        takes.main(script(), [str(project)], env={"SRSTUDIO_ALLOW_CLOUD": "1"})
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    for name in takes.FONT:
        (fonts / name).write_text("x")
    provider = Provider(tmp_path, heard={"speech-1.wav": "nope"})
    seen, original = {}, takes.record

    def fake_record(s, root, *, client, confirm, compose, ffmpeg):
        seen.update(root=root, ffmpeg=ffmpeg)
        return original(s, root, client=provider, confirm=globals()["confirm"], compose=provider.compose)

    monkeypatch.setattr(takes, "record", fake_record)
    with pytest.raises(SystemExit, match="take 01: heard 'nope'"):
        takes.main(
            script(), [str(project), "--font", str(fonts), "--ffmpeg", "ffmpeg"], env={"SRSTUDIO_ALLOW_CLOUD": "1"}
        )
    assert (project / "assets" / "Inter-Bold.ttf").exists() and seen["root"] == project.resolve()
    provider.heard = {}
    provider.spoken.clear()
    assert takes.main(script(), [str(project)], env={"SRSTUDIO_ALLOW_CLOUD": "1"}) == 0
    assert (project / "timeline.json").exists()
