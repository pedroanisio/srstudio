"""``srstudio.dub``: verified audio tracks added to a scene document that was built without sound."""

import hashlib
import io
import math
import wave
from array import array

import pytest
import sr_core.scene as sc

from srstudio import dub

SILENT = """<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="1080" height="1920" fps="24" duration="4" seed="1" background="#bda77a"/>
  <metadata title="Silent" description="A silent master." language="en-US">
    <accessibility description="A square." flashCheck="error"/>
  </metadata>
  <output id="main" path="silent.mp4" codec="h264" container="mp4" fps="24" pixelFormat="yuv420p"/>
  <composition>
    <group id="bg" start="0" end="4">
      <shape id="box" x="0" y="0" shape="rect" width="100" height="100" fill="#000000"/>
    </group>
  </composition>
</scene>
"""


def tone(seconds: float = 1.0, rate: int = 48000) -> bytes:
    pcm = array("h", (int(8000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(int(seconds * rate))))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


@pytest.fixture
def project(tmp_path):
    (tmp_path / "scene.silent.xml").write_text(SILENT)
    (tmp_path / "audio").mkdir()
    for name in ("vo-a.wav", "music.wav"):
        (tmp_path / "audio" / name).write_bytes(tone())
    return tmp_path


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracks(root) -> list[dub.Track]:
    return [
        dub.Track("vo-a", "audio/vo-a.wav", sha(root / "audio/vo-a.wav"), start=0.5, role="dialogue", language="en-US"),
        dub.Track(
            "music-desk",
            "audio/music.wav",
            sha(root / "audio/music.wav"),
            start=0.0,
            role="music",
            gain=-12.0,
            clip_in=0.1,
            clip_out=0.9,
            fade_out=0.1,
        ),
    ]


def test_dub_adds_assets_tracks_master_and_audio_output(project):
    out = project / "scene.xml"
    dub.dub(project / "scene.silent.xml", out, tracks(project), credit="Voice and music by ElevenLabs.")
    scene = sc.read(out)
    assert scene.check() == []
    audio = {a.attributes()["id"]: a.attributes() for a in scene.find("assets").find_all("audio")}
    assert audio["vo-a"]["src"] == "audio/vo-a.wav" and audio["vo-a"]["language"] == "en-US"
    mix = scene.find("audioMix")
    master = mix.find("master").attributes()
    assert (master["loudness"], master["truePeak"], master["limiter"]) == ("-16", "-1.5", "true")
    music = {t.attributes()["id"]: t.attributes() for t in mix.find_all("audioTrack")}["music-desk-track"]
    assert music["asset"] == "music-desk" and music["role"] == "music" and music["gain"] == "-12"
    assert (music["clipIn"], music["clipOut"], music["fadeOut"]) == ("0.1", "0.9", "0.1")
    output = scene.find("output").attributes()
    assert output["audioCodec"] == "aac" and output["audioBitrate"] == "192000"
    assert scene.find("metadata").attributes()["description"] == "A silent master. Voice and music by ElevenLabs."
    assert "ElevenLabs" in scene.find("metadata").find("accessibility").attributes()["description"]
    assert (project / "scene.silent.xml").read_text() == SILENT  # the source is left as it was


def test_dub_assets_come_after_existing_assets(project):
    (project / "scene.silent.xml").write_text(
        SILENT.replace(
            "  <composition", '  <assets>\n    <font id="f" src="f.ttf" family="F"/>\n  </assets>\n  <composition'
        )
    )
    (project / "f.ttf").write_bytes(b"")
    dub.dub(project / "scene.silent.xml", project / "scene.xml", tracks(project))
    ids = [a.attributes()["id"] for a in sc.read(project / "scene.xml").find("assets").elements()]
    assert ids == ["f", "vo-a", "music-desk"]


@pytest.mark.parametrize(
    "change, match",
    [
        (dict(sha256="0" * 64), "sha256"),
        (dict(audio="audio/missing.wav"), "missing"),
        (dict(audio="../outside.wav"), "inside"),
        (dict(start=4.0), "start"),
        (dict(start=-0.1), "start"),
        (dict(start=float("nan")), "start"),
        (dict(role="laughter"), "role"),
        (dict(clip_in=0.5, clip_out=0.5), "clip"),
        (dict(gain=40.0), "gain"),
        (dict(fade_in=-1.0), "fade"),
        (dict(id="box"), "already"),
        (dict(id="has space"), "id"),
    ],
)
def test_dub_refuses_a_bad_track(project, change, match):
    first = tracks(project)[0]
    bad = dub.Track(**{**first.__dict__, **change})
    with pytest.raises(dub.DubError, match=match):
        dub.dub(project / "scene.silent.xml", project / "scene.xml", [bad])
    assert not (project / "scene.xml").exists()


def test_dub_refuses_duplicate_ids_no_tracks_and_a_scene_with_sound(project):
    one = tracks(project)[0]
    with pytest.raises(dub.DubError, match="twice"):
        dub.dub(project / "scene.silent.xml", project / "scene.xml", [one, one])
    with pytest.raises(dub.DubError, match="no tracks"):
        dub.dub(project / "scene.silent.xml", project / "scene.xml", [])
    dub.dub(project / "scene.silent.xml", project / "voiced.scene.xml", [one])
    with pytest.raises(dub.DubError, match="already has"):
        dub.dub(project / "voiced.scene.xml", project / "scene.xml", [one])


def test_dub_refuses_an_output_outside_the_audio_root(project, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "scene.xml"
    with pytest.raises(dub.DubError, match="inside"):
        dub.dub(project / "scene.silent.xml", elsewhere, tracks(project))


# -- the music bed -----------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phase, at, want", [(0.0, 2.0, 0.0), (0.1, 2.0, 0.1), (0.0, 2.417, 0.083), (0.45, 2.417, 0.033), (0.2, 0.0, 0.2)]
)
def test_beat_offset_puts_a_beat_on_the_cut(phase, at, want):
    offset = dub.beat_offset(phase=phase, bpm=120, at=at)
    assert offset == pytest.approx(want, abs=1e-6) and 0 <= offset < 0.5
    beat = 60 / 120
    assert ((at + offset - phase) / beat) == pytest.approx(round((at + offset - phase) / beat), abs=1e-6)


@pytest.mark.parametrize("phase, bpm", [(-0.1, 120), (0.5, 120), (0.1, 0), (float("nan"), 120)])
def test_beat_offset_refuses_impossible_tempo_or_phase(phase, bpm):
    with pytest.raises(dub.DubError):
        dub.beat_offset(phase=phase, bpm=bpm, at=1.0)


def test_music_bed_is_quiet_outside_the_loud_spans_and_continuous(project):
    bed = dub.music_bed(
        "music",
        "audio/music.wav",
        "abc",
        offset=0.08,
        duration=11.75,
        loud=[(2.417, 9.583)],
        quiet_gain=-18.0,
        loud_gain=-4.0,
        tail=0.15,
    )
    assert [t.id for t in bed] == ["music-1", "music-2", "music-3"]
    assert [(t.start, t.gain) for t in bed] == [(0.0, -18.0), (2.417, -4.0), (9.583, -18.0)]
    for t in bed:  # every piece plays the song where the timeline is: clip_in - start is the offset
        assert t.clip_in - t.start == pytest.approx(0.08) and t.role == "music"
    assert bed[0].clip_out == pytest.approx(0.08 + 2.417 + 0.15) and bed[0].fade_out == 0.15
    assert bed[-1].clip_out == pytest.approx(0.08 + 11.75) and bed[-1].fade_out > 0.15


@pytest.mark.parametrize("loud", [[], [(3.0, 2.0)], [(-1.0, 2.0)], [(1.0, 13.0)], [(1.0, 3.0), (2.0, 4.0)]])
def test_music_bed_refuses_bad_spans(loud):
    with pytest.raises(dub.DubError, match="span"):
        dub.music_bed("m", "a.wav", "x", offset=0.0, duration=11.75, loud=loud, quiet_gain=-18, loud_gain=-4)


def test_beat_offset_near_picks_the_closest_offset_on_the_grid():
    beat = 60 / 152
    offset = dub.beat_offset(phase=0.1, bpm=152, at=2.4224, near=0.7355)
    assert abs(offset - 0.7355) <= beat / 2
    assert ((2.4224 + offset - 0.1) / beat) == pytest.approx(round((2.4224 + offset - 0.1) / beat), abs=1e-6)
    with pytest.raises(dub.DubError, match="near"):
        dub.beat_offset(phase=0.1, bpm=152, at=1.0, near=-1.0)


def test_dub_can_end_the_scene_early_at_a_loop_point(project):
    out = project / "scene.xml"
    dub.dub(project / "scene.silent.xml", out, tracks(project)[:1], duration=2.5)
    assert sc.read(out).find("project").attributes()["duration"] == "2.5"
    with pytest.raises(dub.DubError, match="duration"):
        dub.dub(project / "scene.silent.xml", out, tracks(project)[:1], duration=5.0)
    late = dub.Track(**{**tracks(project)[0].__dict__, "start": 3.0})
    with pytest.raises(dub.DubError, match="start"):
        dub.dub(project / "scene.silent.xml", out, [late], duration=2.5)
