"""The review list comes from the reel's own beats, so no caption goes unlooked at."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import cli, frames
from srstudio.frames import FrameError
from srstudio.sketch import Beat


def beat(start: float, caption: str = "", event: str = "", line: int | None = 0) -> Beat:
    return Beat(start, "vera", caption, "side", "flat", "desk", line, 0 if line is not None else None, event)


BEATS = (beat(0.0, "One.", "card"), beat(4.0, "Two words."), beat(8.0, "", "stare", None), beat(9.0, "Last.", line=1))


def test_the_list_holds_the_first_last_two_second_and_payoff_frames():
    listed = {f.why: f.at for f in frames.frame_list(BEATS, 12.0)}
    assert listed["first"] == 0.0 and listed["two-seconds"] == 2.0
    assert listed["payoff"] == 8.0 and listed["last"] == pytest.approx(11.967)


def test_every_caption_gets_a_frame_in_its_middle():
    listed = {f.why: f.at for f in frames.frame_list(BEATS, 12.0)}
    assert listed["caption-two-words"] == 6.0 and listed["caption-last"] == 10.5


def test_a_caption_that_falls_on_another_frame_is_seen_once():
    assert [f.why for f in frames.frame_list(BEATS, 12.0)].count("two-seconds") == 1
    assert not [f for f in frames.frame_list(BEATS, 12.0) if f.why == "caption-one"]  # its middle is the 2 s frame


def test_a_named_payoff_replaces_the_last_event():
    assert {f.why: f.at for f in frames.frame_list(BEATS, 12.0, payoff=5.0)}["payoff"] == 5.0


def test_the_frames_are_in_time_order():
    times = [f.at for f in frames.frame_list(BEATS, 12.0)]
    assert times == sorted(times)


@pytest.mark.parametrize(("beats", "end", "payoff"), [((), 10.0, None), (BEATS, 0.0, None), (BEATS, 12.0, 20.0)])
def test_a_reel_that_cannot_be_listed_is_refused(beats, end, payoff):
    with pytest.raises(FrameError):
        frames.frame_list(beats, end, payoff)


def fake_engine(path: Path, fail: bool = False) -> Path:
    body = "exit 3" if fail else 'while [ $# -gt 0 ]; do [ "$1" = -o ] && touch "$2"; shift; done'
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


def test_each_frame_is_rendered_under_its_time_and_reason(tmp_path):
    made = frames.at_size(
        tmp_path / "x.scene.xml", [frames.Frame(1.5, "first")], tmp_path / "out", fake_engine(tmp_path / "e")
    )
    assert [p.name for p in made] == ["001.50-first.png"]


def test_a_frame_that_does_not_render_stops_the_list(tmp_path):
    with pytest.raises(FrameError, match="did not render"):
        frames.at_size(
            tmp_path / "x.scene.xml", [frames.Frame(0.0, "first")], tmp_path / "o", fake_engine(tmp_path / "e", True)
        )


def test_the_command_lists_a_voiced_project(tmp_path, capsys):
    voiced = tmp_path / "voiced"
    voiced.mkdir()
    rows = [
        {"start": 0.0, "who": "vera", "caption": "One.", "eyes": "side", "mouth": "flat", "arms": "desk",
         "line": 0, "word": 0, "event": "card"},
    ]  # fmt: skip
    (voiced / "beats.json").write_text(json.dumps({"end": 6.0, "beats": rows}))
    assert cli.main(["frames", str(tmp_path)]) == 0
    assert "0.00  first" in capsys.readouterr().out


def test_the_command_says_why_it_could_not_list(tmp_path, capsys):
    assert cli.main(["frames", str(tmp_path)]) == 2
    assert "srstudio frames" in capsys.readouterr().err
