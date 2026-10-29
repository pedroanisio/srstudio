"""``Episode.audio``: one call plays whatever the project brings, with the style's mix defaults."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import CEL, CUTOUT, INK, SOFT, Episode, EpisodeSpec
from srstudio.generated import PlacedClip, Placement
from srstudio.styles import Mix
from test_cel import silent_project
from test_generated import SPEECH, write_wav
from test_ink_layout import takes_data


def spec(root, **kw) -> EpisodeSpec:
    return EpisodeSpec(slug="t", title="t", description="t", root=root, seed=1, **kw)


def mix_of(ep: Episode) -> ET.Element | None:
    return ET.fromstring(ep.scene.to_bytes(layout="pretty")).find("audioMix")


def same_scene(a: Episode, b: Episode) -> None:
    assert a.scene.to_bytes(layout="pretty") == b.scene.to_bytes(layout="pretty")


def test_every_style_names_its_mix_and_ink_masters_louder_without_a_bit_depth():
    assert CUTOUT.mix == SOFT.mix == CEL.mix == Mix(loudness="-16", true_peak="-1.5", bit_depth="24")
    assert INK.mix == Mix(loudness="-14", true_peak="-1.5", bit_depth=None)
    assert INK.facts()["mix"] == {"loudness": "-14", "true_peak": "-1.5", "bit_depth": None}


def test_one_mixed_file_plays_as_the_dialogue_track(project):
    old, new = Episode(spec(project)), Episode(spec(project))
    old.audio_mix(track_id="voice-and-effects")
    assert new.audio_source == "mixed"
    new.audio(track_id="voice-and-effects")
    same_scene(old, new)
    assert mix_of(new).find("master").get("loudness") == "-16"


def test_takes_each_bring_their_own_audio_at_the_takes_start(tmp_path):
    (tmp_path / "timeline.json").write_text(json.dumps(takes_data()))
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hand.ttf").write_bytes(b"\0")
    kw = dict(style=INK, font="assets/hand.ttf")
    old, new = Episode(spec(tmp_path, **kw)), Episode(spec(tmp_path, **kw))
    old.mix(loudness="-14", true_peak="-1.5", bit_depth=None)
    for take in old.takes:
        old.take_audio(take, pan=-0.08 if take.actor == "human" else 0.08)
    assert new.audio_source == "takes"
    new.audio(take=lambda take: dict(pan=-0.08 if take.actor == "human" else 0.08))
    same_scene(old, new)
    master = mix_of(new).find("master")
    assert master.get("loudness") == "-14" and mix_of(new).get("bitDepth") is None


def test_pinned_clips_play_one_track_each_with_their_extras(project, tmp_path):
    root = tmp_path / "ep"
    shutil.copytree(project, root)
    wav = write_wav(root / "assets" / "generated" / "line-1.wav", [0.3 * math.sin(i / 7) for i in range(4800)])
    clip = PlacedClip(SPEECH, hashlib.sha256(wav.read_bytes()).hexdigest(), Placement(start=0.5, role="dialogue"))
    data = json.loads((root / "dialogue.json").read_text())
    data["clips"] = [clip.to_dict()]
    (root / "dialogue.json").write_text(json.dumps(data))
    write_wav(root / "assets" / "groove.wav", [0.1] * 4800)
    extra = [("groove", "assets/groove.wav", {"role": "music"})]
    old, new = Episode(spec(root, style=SOFT, font=None)), Episode(spec(root, style=SOFT, font=None))
    old.generated_audio(extra=extra)
    assert new.audio_source == "clips"
    new.audio(extra=extra)
    same_scene(old, new)
    assert new.track is not None and new.track.duration == pytest.approx(new.t.duration)


def test_a_silent_episode_has_no_mix_and_a_narrated_one_plays_its_verified_cues(tmp_path):
    root = silent_project(tmp_path)
    ep = Episode(spec(root, style=CEL))
    assert ep.audio_source == "silent" and ep.audio() is None and mix_of(ep) is None
    (root / "audio").mkdir()
    with wave.open(str(root / "audio" / "vo-01.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x10\x00" * 4800)
    item = dict(
        id="01",
        text="One.",
        phase="line",
        caption_start=0.1,
        start=0.1,
        duration=0.1,
        speech_duration=0.1,
        speed=1.0,
        lead=0.0,
        tempo=1.0,
        cut=False,
        audio="audio/vo-01.wav",
        sha256=hashlib.sha256((root / "audio" / "vo-01.wav").read_bytes()).hexdigest(),
    )
    (root / "narration.json").write_text(json.dumps({"items": [item]}))
    voiced = Episode(spec(root, style=CEL, language="en-US"))
    voiced.audio(narration=root / "narration.json")
    m = mix_of(voiced)
    (track,) = m.findall("audioTrack")
    assert (track.get("id"), track.get("asset"), float(track.get("start"))) == ("vo-track-01", "vo-01", 0.1)
    assert track.get("language") == "en-US" and m.find("master").get("loudness") == "-16"
    tampered = Path(root / "audio" / "vo-01.wav")
    tampered.write_bytes(tampered.read_bytes() + b"\0\0")
    from srstudio.narration import NarrationError

    with pytest.raises(NarrationError, match="sha256"):
        Episode(spec(root, style=CEL)).audio(narration=root / "narration.json")


def test_audio_refuses_options_the_projects_source_does_not_take(project, tmp_path):
    ep = Episode(spec(project))
    with pytest.raises(TypeError, match="take="):
        ep.audio(take=lambda take: {})  # one mixed file has no takes
    with pytest.raises(TypeError, match="extra="):
        ep.audio(extra=[("x", "assets/x.wav", {})])
    silent = Episode(spec(silent_project(tmp_path), style=CEL))
    with pytest.raises(TypeError, match="track_id="):
        silent.audio(track_id="x")


def test_an_explicit_level_wins_over_the_style(project):
    ep = Episode(spec(project))
    ep.audio(loudness="-14", true_peak="-1")
    master = mix_of(ep).find("master")
    assert (master.get("loudness"), master.get("truePeak")) == ("-14", "-1")


def clips_project(project, tmp_path, role="dialogue"):
    root = tmp_path / "ep"
    shutil.copytree(project, root)
    wav = write_wav(root / "assets" / "generated" / "line-1.wav", [0.3 * math.sin(i / 7) for i in range(4800)])
    clip = PlacedClip(SPEECH, hashlib.sha256(wav.read_bytes()).hexdigest(), Placement(start=0.5, role=role))
    data = json.loads((root / "dialogue.json").read_text())
    data["clips"] = [clip.to_dict()]
    (root / "dialogue.json").write_text(json.dumps(data))
    write_wav(root / "assets" / "groove.wav", [0.1] * 4800)
    return root


def test_the_music_ducks_under_every_spoken_track_when_asked(project, tmp_path):
    root = clips_project(project, tmp_path)
    ep = Episode(spec(root, style=SOFT, font=None))
    ep.audio(extra=[("groove", "assets/groove.wav", {"role": "music", "gain": -3})], duck=-10)
    tracks = {t.get("id"): t for t in mix_of(ep).findall("audioTrack")}
    music = tracks["track-groove"]
    assert (music.get("duckUnder"), music.get("duckAmount"), music.get("gain")) == ("track-line-1", "-10", "-3")
    assert tracks["track-line-1"].get("duckUnder") is None


@pytest.mark.parametrize("duck", [0, 3, float("nan")])
def test_a_duck_must_lower_the_music(project, tmp_path, duck):
    ep = Episode(spec(clips_project(project, tmp_path), style=SOFT, font=None))
    with pytest.raises(ValueError, match="duck"):
        ep.audio(extra=[("groove", "assets/groove.wav", {"role": "music"})], duck=duck)


def test_a_duck_with_no_music_or_nothing_spoken_is_refused(project, tmp_path):
    ep = Episode(spec(clips_project(project, tmp_path), style=SOFT, font=None))
    with pytest.raises(ValueError, match="no music track"):
        ep.audio(extra=[("groove", "assets/groove.wav", {"role": "effects"})], duck=-12)
    unspoken = Episode(spec(clips_project(project, tmp_path / "fx", role="effects"), style=SOFT, font=None))
    with pytest.raises(ValueError, match="no spoken track"):
        unspoken.audio(extra=[("groove", "assets/groove.wav", {"role": "music"})], duck=-12)
    with pytest.raises(TypeError, match="duck="):
        Episode(spec(project)).audio(duck=-12)  # one mixed file: nothing to duck
