"""Explicit audio settings and invalid input produce predictable authoring behavior."""

import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import Episode, Soundtrack, SrstudioError, sample
from srstudio.soundtrack import SoundtrackError
from support.audio import spec


@pytest.mark.parametrize("precreate", ["track", "pending", "master"])
def test_audio_overrides_apply_even_when_the_mix_already_exists(project, precreate):
    ep = Episode(spec(project))
    if precreate == "track":
        ep.add_track("extra-dialogue", "dialogue")
    else:
        ep.mix(master_first=precreate == "master")
    ep.audio(loudness="-23", true_peak="-3")
    master = ET.fromstring(ep.scene.to_bytes()).find("audioMix/master")
    assert float(master.get("loudness")) == -23
    assert float(master.get("truePeak")) == -3


def test_implicit_mix_access_preserves_settings_and_explicit_changes_update_them(project):
    ep = Episode(spec(project))
    mix = ep.mix(loudness="-23", true_peak="-3", sample_rate=44100, channels=1, bit_depth=None)
    ep.add_track("dialogue", "dialogue")
    assert ep.mix() is mix
    ep.mix(loudness="-20", sample_rate=48000, channels=2, bit_depth="16")
    root = ET.fromstring(ep.scene.to_bytes())
    node = root.find("audioMix")
    assert (node.get("sampleRate"), node.get("channels"), node.get("bitDepth")) == ("48000", "2", "16")
    assert len(node.findall("master")) == 1
    assert float(node.find("master").get("loudness")) == -20
    assert float(node.find("master").get("truePeak")) == -3
    ep.mix(bit_depth=None)
    ep.add_track("another-dialogue", "dialogue")
    assert ET.fromstring(ep.scene.to_bytes()).find("audioMix").get("bitDepth") is None


@pytest.mark.parametrize("content", [b"not a WAV file", b"RIFF", b""])
def test_bad_wav_has_a_typed_error_with_the_path(tmp_path, content):
    path = tmp_path / "broken.wav"
    path.write_bytes(content)
    with pytest.raises(SoundtrackError, match="broken.wav") as caught:
        Soundtrack(path)
    assert isinstance(caught.value, SrstudioError)
    assert caught.value.__cause__ is not None


def test_truncated_pcm_frames_have_a_typed_error(tmp_path):
    path = tmp_path / "truncated.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x10\x00" * 20)
    path.write_bytes(path.read_bytes()[:-2])
    with pytest.raises(SoundtrackError, match="truncated.wav"):
        Soundtrack(path)


def test_missing_wav_has_a_typed_error(tmp_path):
    with pytest.raises(SoundtrackError, match="missing.wav"):
        Soundtrack(tmp_path / "missing.wav")


def test_bad_wav_build_reports_a_diagnostic_without_tracebacks(tmp_path):
    script = tmp_path / "bad_audio.py"
    script.write_text('from srstudio import Soundtrack\nSoundtrack(__file__)\n')
    result = subprocess.run(
        [sys.executable, "-m", "srstudio", "build", str(script)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 1
    assert "bad_audio.py" in result.stderr
    assert "srstudio build:" in result.stderr and "Traceback" not in result.stderr


def test_sample_without_a_font_fails_before_writing_any_project_files(tmp_path, monkeypatch):
    monkeypatch.setattr(sample, "SYSTEM_FONTS", ())
    root = tmp_path / "project"
    with pytest.raises(SrstudioError, match="font="):
        sample.write_sample_project(root, [sample.Line("a", "hi")])
    assert not root.exists()


def test_sample_refuses_an_invalid_explicit_font_before_writing(tmp_path):
    font = tmp_path / "broken.ttf"
    font.write_bytes(b"\0")
    root = tmp_path / "project"
    with pytest.raises(SrstudioError, match="broken.ttf"):
        sample.write_sample_project(root, [sample.Line("a", "hi")], font=font)
    assert not root.exists()


@pytest.mark.parametrize("explicit_font", [False, True])
def test_starter_example_handles_missing_system_fonts(tmp_path, project, explicit_font):
    script = Path(__file__).resolve().parents[1] / "examples" / "new_episode.py"
    root = tmp_path / "project"
    args = [str(script), str(root)]
    if explicit_font:
        args += ["--font", str(project / "assets" / "DejaVuSans-Bold.ttf")]
    code = (
        'import runpy, sys\nfrom srstudio import sample\nsample.SYSTEM_FONTS = ()\n'
        'script = sys.argv[1]\nsys.argv = sys.argv[1:]\nrunpy.run_path(script, run_name="__main__")'
    )
    result = subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, timeout=30)
    if explicit_font:
        assert result.returncode == 0, result.stdout + result.stderr
        assert (root / "coffee-review.scene.xml").is_file()
    else:
        assert result.returncode != 0
        assert "font" in result.stderr.lower() and "Traceback" not in result.stderr
        assert not root.exists()
