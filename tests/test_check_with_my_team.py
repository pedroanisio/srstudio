"""Check With My Team: the voiced and scored master of the packaged recreation (the shared steps are tested in
test_dub.py, test_narration.py and test_compose.py)."""

import hashlib
import io
import json
import math
import shutil
import sys
import wave
import xml.etree.ElementTree as ET
from array import array
from pathlib import Path

import pytest

from srstudio import dub, narration, phrasing
from srstudio.voice import Transcript, Word

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


def load(name: str):
    sys.path.insert(0, str(EPISODES))
    try:
        return __import__(name)
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module")
def audio():
    return load("check_with_my_team_audio")


@pytest.fixture(scope="module")
def episode():
    return load("check_with_my_team")


CAPTIONS = [
    {"start": 0.0, "end": 0.5, "text": "let me just", "size": 86},
    {"start": 0.5, "end": 1.0, "text": "check with my team", "size": 83},
    {"start": 1.0, "end": 1.6667, "text": "real quick", "size": 86},
    {"start": 1.6667, "end": 2.4167, "text": "and get back to you", "size": 83},
    {"start": 230 / 24, "end": 10.1667, "text": "let me just", "size": 86},
    {"start": 10.1667, "end": 11.75, "text": "and get back to you", "size": 83},
]


def test_the_script_uses_the_library_steps_not_a_copy(audio):
    for name in ("conform", "confirm_voice", "require_consent"):
        assert getattr(audio, name) is getattr(narration, name), name
    assert audio.place_phrases is phrasing.place_phrases and audio.beat_offset is dub.beat_offset


def test_the_voiced_cut_hides_its_lettering_and_words_on_the_cover_but_the_package_scene_has_no_variant(
    episode, packages, tmp_path
):
    source = packages / "check-with-my-team-1.0.0" / "project"
    if not source.is_dir():
        pytest.skip(f"{source} missing")
    shutil.copy(source / "script.json", tmp_path)
    shutil.copytree(source / "assets", tmp_path / "assets")
    root = ET.parse(episode.build(tmp_path, tmp_path / "scene.silent.xml", voiced=True)).getroot()
    hidden = {o.get("target") for o in root.iterfind("parameters/variant[@id='cover']/override")}
    words = root.find(".//group[@id='spoken-words']")
    assert words is not None and "spoken-words" in hidden and len(words) == 7  # every cue of the voiced cut
    lettered = hidden - {"spoken-words"}
    assert len(lettered) == 2  # the opening's hook card and the garden's headline
    assert ET.parse(source / "scene.xml").getroot().find("parameters") is None


def test_captions_after_the_loop_point_are_the_recording_starting_over(audio):
    shown = audio.cues(CAPTIONS, loop=9.5833)
    assert [c.text for c in shown] == ["let me just", "check with my team", "real quick", "and get back to you"]
    assert audio.sentence(shown) == "Let me just check with my team real quick and get back to you."
    assert audio.LOOP == 230 / 24


def test_the_voiced_cut_turns_on_a_card_and_ends_on_a_spoken_button(audio):
    shown = audio.shown(CAPTIONS)
    assert [c.text for c in shown] == [
        "let me just", "check with my team", "real quick", "and get back to you",
        "3 hours later...", "the team says...", "I'm absolutely right.",
    ]  # fmt: skip
    card, *button = shown[4:]
    assert audio.CUT < card.start < card.end == audio.LOOP  # mid-dance, gone at the cut back to the desk
    assert button[0].start == audio.LOOP and button[0].end == button[1].start
    assert button[1].end + phrasing.SPILL <= audio.END == 282 / 24  # the spill still ends inside the picture
    assert all(a.end <= b.start for a, b in zip(shown, shown[1:], strict=False))


def test_the_spoken_takes_are_the_line_and_the_button_but_not_the_card(audio):
    line, button = audio.takes(CAPTIONS)
    assert audio.sentence(line) == "Let me just check with my team real quick and get back to you."
    assert audio.sentence(button) == "The team says... I'm absolutely right."
    assert audio.LATER not in line + button


@pytest.mark.parametrize(
    "bad", [[], [{"start": 1.0, "end": 0.5, "text": "x", "size": 80}], [{"start": 0, "end": 1}], [CAPTIONS[-1]]]
)
def test_bad_captions_are_refused(audio, bad):
    with pytest.raises(narration.NarrationError):
        audio.cues(bad, loop=9.5833)


def test_the_cut_beat_is_on_the_dance_grid_just_after_the_cut(audio):
    assert 0 <= audio.CUT_BEAT - audio.CUT < 0.02
    assert audio.MUSIC.windows()[1][0] == pytest.approx(audio.INTRO_BEATS * audio.BEAT, abs=1e-3)
    assert audio.INTRO_BEATS * audio.BEAT - audio.CUT_BEAT + audio.END <= audio.MUSIC.seconds  # outlasts the video


def test_the_onset_is_where_the_music_starts(audio):
    assert audio.onset_of(stereo([(0.5, 0.0), (0.5, 0.3)])) == pytest.approx(0.5, abs=0.006)
    with pytest.raises(audio.MusicOutputError, match="never"):
        audio.onset_of(stereo([(0.5, 0.0)]))


def stereo(levels: list[tuple[float, float]], rate: int = 48000) -> bytes:
    """A stereo WAV of 440 Hz at each (seconds, amplitude) in turn."""
    pcm = array("h")
    n = 0
    for seconds, amp in levels:
        for _ in range(int(seconds * rate)):
            v = int(32767 * amp * math.sin(2 * math.pi * 440 * n / rate))
            pcm.extend((v, v))
            n += 1
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def test_a_song_without_a_drop_at_the_cut_is_refused(audio):
    assert audio.require_drop(stereo([(1.0, 0.05), (1.0, 0.5)]), 1.0, before=0.8, after=0.8) > 15
    with pytest.raises(audio.MusicOutputError, match="no drop"):
        audio.require_drop(stereo([(1.0, 0.3), (1.0, 0.35)]), 1.0, before=0.8, after=0.8)
    with pytest.raises(audio.MusicOutputError, match="no audio"):
        audio.require_drop(stereo([(1.0, 0.3)]), 1.0, before=0.5, after=0.5)


def transcript(*words: tuple[str, str]) -> Transcript:
    return Transcript("en", 1.0, " ".join(w for w, _ in words), tuple(Word(w, 0.0, 0.1, t) for w, t in words))


def test_a_song_with_heard_words_is_refused(audio):
    audio.require_instrumental(transcript(("(upbeat music)", "audio_event"), (" ", "spacing")))
    audio.require_instrumental(transcript())
    with pytest.raises(audio.MusicOutputError, match="instrumental"):
        audio.require_instrumental(transcript(("Yeah", "word"), ("(music)", "audio_event")))


def music_doc(root: Path) -> dict:
    (root / "audio").mkdir(exist_ok=True)
    (root / "audio" / "music.wav").write_bytes(b"RIFF")
    return {
        "audio": "audio/music.wav",
        "sha256": hashlib.sha256(b"RIFF").hexdigest(),
        "model": "music_v2",
        "seed": 1336,
        "bpm": 120,
        "measured_bpm": 119.8,
        "phase": 0.21,
        "offset": 0.293,
        "loud": [[2.4167, 9.5833]],
        "quiet_gain": -18.0,
        "loud_gain": -6.0,
        "heard": "(upbeat music)",
    }


def test_music_manifest_becomes_a_ducked_bed(episode, tmp_path):
    (tmp_path / "music.json").write_text(json.dumps(music_doc(tmp_path)))
    bed = episode.music_tracks(tmp_path, duration=11.75)
    assert [t.gain for t in bed] == [-18.0, -6.0, -18.0] and bed[1].start == 2.4167
    assert all(isinstance(t, dub.Track) for t in bed)


@pytest.mark.parametrize(
    "change, match",
    [
        ({"extra": 1}, "unknown"),
        ({"bpm": "120"}, "bpm"),
        ({"loud": [[3.0]]}, "loud"),
        ({"sha256": "0" * 64}, "sha256"),
        ({"audio": "../x.wav"}, "inside"),
    ],
)
def test_bad_music_manifests_are_refused(episode, tmp_path, change, match):
    doc = {**music_doc(tmp_path), **change}
    (tmp_path / "music.json").write_text(json.dumps(doc))
    with pytest.raises(dub.DubError, match=match):
        episode.music_tracks(tmp_path, duration=11.75)


def test_missing_key_in_music_manifest_is_refused(episode, tmp_path):
    doc = music_doc(tmp_path)
    del doc["offset"]
    (tmp_path / "music.json").write_text(json.dumps(doc))
    with pytest.raises(dub.DubError, match="missing"):
        episode.music_tracks(tmp_path, duration=11.75)


def make_package(root: Path) -> Path:
    project = root / "project"
    (project / "assets").mkdir(parents=True)
    files = {"scene.xml": b"<scene/>", "script.json": b"[]", "assets/font.ttf": b"F", "Check_With_My_Team.mp4": b"V"}
    for name, data in files.items():
        (project / name).write_bytes(data)
    manifest = [{"path": n, "sha256": hashlib.sha256(d).hexdigest(), "size": len(d)} for n, d in files.items()]
    (root / "vpkg.json").write_text(json.dumps({"files": manifest}))
    return root


def test_the_package_inputs_are_verified_then_copied_and_its_scene_is_not(episode, tmp_path):
    package = make_package(tmp_path / "pkg")
    target = tmp_path / "ep"
    episode.unpack(package, target)
    assert not (target / "scene.xml").exists() and not (target / "Check_With_My_Team.mp4").exists()  # built here
    assert (target / "assets" / "font.ttf").read_bytes() == b"F" and (target / "script.json").exists()


def test_the_scene_is_drawn_with_the_stick_style(episode):
    from srstudio import STICK, stick

    assert episode.STICK is STICK and episode.stick is stick
    icon = stick.Icon((0.0, 0.0), (stick.Plate("#ffffff", "M 0 0 Z"),))
    badges = episode.badges(dict.fromkeys(("chatgpt", "gemini", "claude"), icon), traced=-5.0)
    assert [(b.radius, b.traced_angle) for b in badges] == [(47, -5.0), (None, -5.0), (42, -5.0)]
    assert badges[1].paint is not None and badges[1].paint.id == "gemini-gradient"
    with pytest.raises(stick.StickDataError, match="claude"):
        episode.badges({"chatgpt": icon, "gemini": icon}, traced=0.0)


def test_a_tampered_package_is_refused(episode, tmp_path):
    package = make_package(tmp_path / "pkg")
    (package / "project" / "script.json").write_bytes(b"[1]")
    with pytest.raises(dub.DubError, match="script.json"):
        episode.unpack(package, tmp_path / "ep")
    assert not (tmp_path / "ep").exists()
