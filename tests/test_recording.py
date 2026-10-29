"""The shared command line of an episode's recording script: ``PROJECT [--ffmpeg PATH]``, the environment passed
through, and the project resolved before the recording runs."""

import shutil
from pathlib import Path

import pytest

from srstudio import recording


def test_main_hands_the_project_the_environment_and_ffmpeg_to_the_recording(tmp_path):
    got = []
    code = recording.main(lambda *a: got.append(a), "Doc line\n\nmore", ["proj", "--ffmpeg", "/x/ffmpeg"], {"A": "1"})
    assert code == 0
    assert got == [(Path("proj").resolve(), {"A": "1"}, "/x/ffmpeg")]


def test_main_defaults_to_the_ffmpeg_on_the_path_and_the_process_environment(monkeypatch):
    got = []
    monkeypatch.setenv("SRSTUDIO_RECORDING_TEST", "yes")
    recording.main(lambda *a: got.append(a), None, ["proj"])
    project, env, ffmpeg = got[0]
    assert env["SRSTUDIO_RECORDING_TEST"] == "yes"
    assert ffmpeg == (shutil.which("ffmpeg") or "ffmpeg")


def test_main_refuses_a_missing_project_before_recording_anything():
    got = []
    with pytest.raises(SystemExit) as stop:
        recording.main(lambda *a: got.append(a), "Doc line", [])
    assert stop.value.code == 2 and got == []


def test_the_help_shows_the_first_line_of_the_script_doc(capsys):
    with pytest.raises(SystemExit):
        recording.main(lambda *a: None, "Book Report — the recording\n\nusage notes", ["--help"])
    assert "Book Report — the recording" in capsys.readouterr().out


def test_a_script_adds_its_own_options_and_receives_them_as_keywords():
    got = []

    def options(parser):
        parser.add_argument("--font", type=Path)
        parser.add_argument("--key-stdin", action="store_true")

    recording.main(
        lambda *a, **kw: got.append((a, kw)), "Doc", ["proj", "--font", "f", "--key-stdin"], {}, options=options
    )
    assert got == [((Path("proj").resolve(), {}, recording_ffmpeg()), {"font": Path("f"), "key_stdin": True})]


def test_without_options_the_recording_gets_no_keywords():
    got = []
    recording.main(lambda *a, **kw: got.append(kw), "Doc", ["proj"], {})
    assert got == [{}]


def test_an_option_cannot_shadow_the_shared_arguments():
    with pytest.raises(ValueError, match="project"):
        recording.main(lambda *a, **kw: None, "Doc", ["proj"], {}, options=lambda p: p.add_argument("--project"))


def recording_ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"
