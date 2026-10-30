"""Generated media: declarations, placements, the engine's resolve step, pins and mouths from clips."""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from fakes import ffmpeg_required, make_mp3
from srstudio import Episode, EpisodeSpec, cast, generated, locations
from srstudio.generated import PLACEHOLDER, Generated, PlacedClip, Placement, ResolveError
from srstudio.soundtrack import Soundtrack
from support.generated import SQUEAK

SPEECH = Generated(
    id="line-1",
    kind="speech",
    provider="srstudio-elevenlabs",
    model="eleven_multilingual_v2",
    prompt="In your chair.",
    voice="bIHbv24MWmeRgasZH58o?stability=0.42&similarity_boost=0.75&style=0.24&speed=1.0&use_speaker_boost=true",
    language="en",
    seed=52026,
    cache="assets/generated/line-1.wav",
)


def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


def write_wav(path: Path, samples: list[float], rate: int = 48000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(int(max(-1, min(1, s)) * 32767).to_bytes(2, "little", signed=True) for s in samples))
    return path


# -- declarations -----------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "over,match",
    [
        ({"id": "1line"}, "id"),
        ({"cache": "/abs/line.wav"}, "relative"),
        ({"cache": "../out/line.wav"}, "inside"),
        ({"cache": "assets/line.mp3"}, "wav"),
        ({"kind": "image"}, "kind"),
        ({"prompt": ""}, "prompt"),
        ({"duration": 0.0}, "duration"),
    ],
)
def test_invalid_declarations_are_refused(over, match):
    with pytest.raises(ValueError, match=match):
        Generated(**{**SPEECH.__dict__, **over})


def test_a_sound_effect_needs_a_duration():
    with pytest.raises(ValueError, match="duration"):
        Generated(**{**SQUEAK.__dict__, "duration": None})


@pytest.mark.parametrize(
    "over,match",
    [
        ({"start": -0.1}, "start"),
        ({"clip_in": -1}, "clip_in"),
        ({"clip_in": 0.5, "clip_out": 0.5}, "clip_out"),
        ({"clip_out": 0.2, "fade_in": 0.15, "fade_out": 0.1}, "fades"),
        ({"gain_db": math.inf}, "gain"),
        ({"role": "singing"}, "role"),
    ],
)
def test_invalid_placements_are_refused(over, match):
    with pytest.raises(ValueError, match=match):
        Placement(**{"start": 1.0, **over})


def test_placed_clips_round_trip_and_refuse_unknown_fields():
    clip = PlacedClip(SQUEAK, "ab" * 32, Placement(start=1.5, clip_in=0.1, clip_out=0.6, gain_db=-4.5, fade_out=0.06))
    assert PlacedClip.from_dict(clip.to_dict()) == clip
    data = clip.to_dict()
    data["placement"]["loop"] = 3
    with pytest.raises(ValueError, match="unknown"):
        PlacedClip.from_dict(data)
    with pytest.raises(ValueError, match="sha256"):
        PlacedClip.from_dict({**clip.to_dict(), "sha256": "xyz"})


# -- the audio document and pins ----------------------------------------------------------------------------
def test_audio_document_declares_each_item_with_a_placeholder(tmp_path):
    path = generated.audio_document(tmp_path / "a.scene.xml", [SPEECH, SQUEAK])
    root = ET.parse(path).getroot()
    assets = {g.get("id"): g for g in root.iter("generated")}
    assert set(assets) == {"line-1", "squeak"}
    assert assets["line-1"].get("cacheSha256") == PLACEHOLDER and float(assets["squeak"].get("duration")) == 1.0
    assert {t.get("asset") for t in root.iter("audioTrack")} == {"line-1", "squeak"}


def test_pins_are_read_back_and_checked_against_the_file(tmp_path):
    doc = generated.audio_document(tmp_path / "a.scene.xml", [SPEECH])
    with pytest.raises(ResolveError, match="not resolved"):
        generated.pinned(doc, [SPEECH])
    wav = write_wav(tmp_path / SPEECH.cache, [0.1] * 480)
    digest = hashlib.sha256(wav.read_bytes()).hexdigest()
    doc.write_text(doc.read_text().replace(PLACEHOLDER, digest))
    (resolved,) = generated.pinned(doc, [SPEECH]).values()
    assert resolved.sha256 == digest and resolved.path == wav
    wav.write_bytes(wav.read_bytes() + b"\0\0")
    with pytest.raises(ResolveError, match="does not match"):
        generated.pinned(doc, [SPEECH])
    with pytest.raises(ResolveError, match="no generated asset"):
        generated.pinned(doc, [SQUEAK])


# -- the engine ------------------------------------------------------------------------------------------------
@pytest.fixture
def fake_env(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    mp3 = make_mp3(tmp_path / "tone.mp3")
    assert mp3
    return {
        "SR_PROVIDER_SRSTUDIO_ELEVENLABS": f"{sys.executable} {Path(__file__).parent / 'fake_provider.py'}",
        "SRSTUDIO_ALLOW_CLOUD": "1",
        "ELEVENLABS_API_KEY": "sk-test",
        "FAKE_MP3": str(tmp_path / "tone.mp3"),
        "FAKE_LOG": str(tmp_path / "calls.log"),
    }


def calls(env) -> list[str]:
    log = Path(env["FAKE_LOG"])
    return log.read_text().split() if log.exists() else []


@ffmpeg_required
def test_resolve_makes_pins_and_skips_what_is_up_to_date(tmp_path, fake_env):
    project = tmp_path / "project"
    doc = generated.audio_document(project / "audio.scene.xml", [SPEECH, SQUEAK])
    report = generated.resolve(doc, engine=engine(), env=fake_env)
    assert {t.id: t.status for t in report} == {"line-1": "made", "squeak": "made"}
    assert sorted(calls(fake_env)) == ["sfx", "stt", "tts"]
    pins = generated.pinned(doc, [SPEECH, SQUEAK])
    assert pins["line-1"].path.exists() and pins["squeak"].sha256 != PLACEHOLDER
    again = generated.resolve(doc, engine=engine(), env=fake_env)
    assert {t.status for t in again} == {"up-to-date"} and len(calls(fake_env)) == 3


@ffmpeg_required
def test_resolve_fails_loudly_when_the_line_is_misheard(tmp_path, fake_env):
    doc = generated.audio_document(tmp_path / "p" / "audio.scene.xml", [SPEECH])
    with pytest.raises(ResolveError, match="heard") as info:
        generated.resolve(doc, engine=engine(), env={**fake_env, "FAKE_HEARD": "In your chairs."})
    assert [t.id for t in info.value.targets if t.status == "error"] == ["line-1"]
    with pytest.raises(ResolveError, match="not resolved"):
        generated.pinned(doc, [SPEECH])


def test_resolve_reports_a_missing_engine(tmp_path):
    with pytest.raises(ResolveError, match="engine"):
        generated.resolve(tmp_path / "x.scene.xml", engine=tmp_path / "no-such-engine")


def test_the_provider_command_runs_this_interpreter():
    assert generated.provider_command().split()[:3] == [sys.executable, "-m", "srstudio.provider"]


# -- mouths from clips -----------------------------------------------------------------------------------------
def test_soundtrack_from_clips_places_trims_gains_and_fades(tmp_path):
    a = write_wav(tmp_path / "a.wav", [0.5] * 4800)  # 0.1 s at 0.5
    b = write_wav(tmp_path / "b.wav", [0.0] * 2400 + [0.2] * 4800)  # silence then 0.1 s at 0.2
    track = Soundtrack.from_clips(
        [
            (a, Placement(start=1.0, gain_db=-6.0206)),  # half: 0.25
            (b, Placement(start=2.0, clip_in=0.05, clip_out=0.15, fade_in=0.05)),
        ],
        duration=3.0,
    )
    assert track.duration == pytest.approx(3.0)
    assert track.rms(0.5, 0.9) == 0
    assert track.rms(1.01, 1.09) == pytest.approx(0.25, rel=1e-3)
    assert track.rms(2.06, 2.09) == pytest.approx(0.2, rel=1e-3)  # after the fade-in
    assert track.rms(2.0, 2.02) < 0.1  # inside the fade-in
    assert track.rms(2.2, 2.9) == 0


def test_soundtrack_from_clips_refuses_another_sample_rate(tmp_path):
    a = write_wav(tmp_path / "a.wav", [0.5] * 441, rate=44100)
    with pytest.raises(ValueError, match="44100"):
        Soundtrack.from_clips([(a, Placement(start=0))], duration=1.0)


# -- the episode ---------------------------------------------------------------------------------------------------
def test_episode_plays_pinned_clips_and_moves_mouths_from_them(project, tmp_path):
    root = tmp_path / "ep"
    shutil.copytree(project, root)
    loud = write_wav(root / "assets" / "generated" / "line-1.wav", [0.3 * math.sin(i / 7) for i in range(48000)])
    sha = hashlib.sha256(loud.read_bytes()).hexdigest()
    clip = PlacedClip(SPEECH, sha, Placement(start=0.62, clip_in=0.0, clip_out=1.0, role="dialogue", language="en"))
    ep = Episode(
        EpisodeSpec(slug="gen", title="t", description="t", root=root, seed=6, background="#D5DFDF", audio=None)
    )
    ep.generated_audio([clip])
    ep.setup(
        locations.office_wide,
        [(0, ep.t.duration)],
        at_desk=lambda g: ep.perform(cast.Manager(ep.cv), g, 560, 724, 1.45),
    )
    path = ep.finish(tmp_path / "gen.scene.xml")
    root_el = ET.parse(path).getroot()
    (asset,) = list(root_el.iter("generated"))
    assert asset.get("cacheSha256") == sha and asset.get("cache") == SPEECH.cache
    (track,) = [t for t in root_el.iter("audioTrack") if t.get("asset") == "line-1"]
    assert float(track.get("start")) == 0.62 and float(track.get("clipOut")) == 1.0 and track.get("role") == "dialogue"
    assert not [a for a in root_el.iter("audio") if a.get("id") == "dialogue"]
    mouth_keys = [k for k in root_el.iter("key") if k.get("value") == "1"]
    assert mouth_keys  # the manager's mouth opens while the clip plays


def test_episode_refuses_a_clip_whose_file_changed(project, tmp_path):
    root = tmp_path / "ep2"
    shutil.copytree(project, root)
    write_wav(root / SPEECH.cache, [0.1] * 4800)
    clip = PlacedClip(SPEECH, "0" * 63 + "1", Placement(start=0.5))
    ep = Episode(
        EpisodeSpec(slug="gen", title="t", description="t", root=root, seed=6, background="#D5DFDF", audio=None)
    )
    with pytest.raises(ResolveError, match="does not match"):
        ep.generated_audio([clip])


# -- trimming clips to their sound ---------------------------------------------------------------------------------
def test_speech_trim_keeps_a_lead_and_a_tail_around_the_voice(tmp_path):
    # 0.5 s silence, 0.4 s voice at 0.3, 0.5 s silence
    wav = write_wav(tmp_path / "s.wav", [0.0] * 24000 + [0.3] * 19200 + [0.0] * 24000)
    trim = generated.trim_speech(wav)
    assert trim.clip_in == pytest.approx(0.5 - 0.025, abs=1e-4)
    assert trim.clip_out == pytest.approx(0.9 + 0.05, abs=1e-3)
    assert trim.peak == pytest.approx(0.3, abs=1e-3)


def test_effect_trim_starts_at_the_onset_caps_the_length_and_measures_the_faded_peak(tmp_path):
    wav = write_wav(tmp_path / "e.wav", [0.001] * 9600 + [0.6] * 48000)  # quiet hiss, then the effect
    trim = generated.trim_effect(wav, longest=0.5)
    assert trim.clip_in == pytest.approx(0.2 - 0.005, abs=1e-4)
    assert trim.clip_out - trim.clip_in == pytest.approx(0.5, abs=1e-4)
    assert trim.peak == pytest.approx(0.6, abs=0.01)


@pytest.mark.parametrize("samples", [[0.0] * 4800, []])
def test_silent_clips_cannot_be_trimmed(tmp_path, samples):
    wav = write_wav(tmp_path / "z.wav", samples)
    with pytest.raises(ValueError, match="silent"):
        generated.trim_speech(wav)
    with pytest.raises(ValueError, match="silent"):
        generated.trim_effect(wav, longest=0.5)


def test_gain_to_peak_converts_a_level_to_decibels():
    assert generated.gain_to_peak(0.3, 0.6) == pytest.approx(6.0206, abs=1e-3)
    with pytest.raises(ValueError):
        generated.gain_to_peak(0.0, 0.5)
