"""The lip proof picks mid-word instants across a recorded reel, says what the mouth track holds at each one and pulls
that frame from the master, so a person compares mouth to word on the file that ships."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from srstudio import cli, lip_proof
from srstudio.lip_proof import Instant, LipProofError


def take(id: str, at: float, text: str, seconds: float = 0.1, clip_in: float = 0.0) -> dict:
    n = len(text)
    return {
        "id": id,
        "who": "lint",
        "at": at,
        "kept": n * seconds,
        "characters": list(text),
        "starts": [k * seconds for k in range(n)],
        "ends": [(k + 1) * seconds for k in range(n)],
        "clip_in": clip_in,
    }


def project(tmp_path: Path, takes: list[dict], mouths: list | None = None) -> Path:
    voiced = tmp_path / "voiced"
    voiced.mkdir()
    (voiced / "speech.json").write_text(json.dumps({"end": 9.0, "takes": takes}), encoding="utf-8")
    track = [[0.0, "open"]] if mouths is None else mouths
    (voiced / "mouths.json").write_text(json.dumps({"end": 9.0, "mouths": {"lint": track}}), encoding="utf-8")
    return tmp_path


def test_each_instant_is_the_middle_of_a_words_longest_letter_on_the_masters_clock(tmp_path):
    held = take("01", 2.0, "Nobody", clip_in=0.5)
    held["ends"][3] = 0.6  # the second o is the long one
    found = lip_proof.instants(project(tmp_path, [held]), count=1)
    assert found == [Instant("lint", "Nobody", "o", 1.95, "open")]


def test_instants_spread_over_the_reel_and_stop_at_the_words_there_are(tmp_path):
    words = " ".join(f"word{k}" for k in range(20))
    root = project(tmp_path, [take("01", 0.0, words)])
    spread = lip_proof.instants(root, count=4)
    assert [i.word for i in spread] == ["word0", "word5", "word10", "word15"]
    assert len(lip_proof.instants(root, count=99)) == 20


def test_punctuation_never_counts_as_the_letter(tmp_path):
    found = lip_proof.instants(project(tmp_path, [take("01", 0.0, "Hi.", seconds=0.2)]), count=1)
    assert found[0].word == "Hi" and found[0].letter == "H"


def test_a_silent_final_e_is_not_the_letter_to_look_at(tmp_path):
    held = take("01", 0.0, "wardrobe")
    held["ends"][7] = 2.0
    assert lip_proof.instants(project(tmp_path, [held]), count=1)[0].letter != "e"


def test_the_shown_pose_is_the_one_the_track_holds_at_that_second(tmp_path):
    root = project(tmp_path, [take("01", 0.0, "ab")], [[0.0, "closed"], [0.05, "round"], [9.0, "open"]])
    assert lip_proof.instants(root, count=1)[0].shown == "round"


def test_a_shut_vowel_is_called_out_and_a_shut_consonant_is_not():
    assert not Instant("lint", "You", "Y", 1.0, "closed").suspect
    assert Instant("lint", "group", "u", 1.0, "closed").suspect
    assert not Instant("lint", "mute", "m", 1.0, "closed").suspect
    assert not Instant("lint", "mute", "u", 1.0, "round").suspect


def test_a_project_without_a_recording_is_refused_by_name(tmp_path):
    with pytest.raises(LipProofError, match="speech.json"):
        lip_proof.instants(tmp_path)


def test_a_broken_recording_is_refused_and_not_guessed_at(tmp_path):
    bad = take("01", 0.0, "abc")
    bad["starts"] = [0.0]
    with pytest.raises(LipProofError, match="characters"):
        lip_proof.instants(project(tmp_path, [bad]))


def test_a_speaker_with_no_mouth_track_is_refused(tmp_path):
    root = project(tmp_path, [take("01", 0.0, "abc")])
    (root / "voiced/mouths.json").write_text(json.dumps({"end": 9.0, "mouths": {}}), encoding="utf-8")
    with pytest.raises(LipProofError, match="lint"):
        lip_proof.instants(root)


def test_a_count_below_one_is_refused(tmp_path):
    with pytest.raises(LipProofError, match="count"):
        lip_proof.instants(project(tmp_path, [take("01", 0.0, "abc")]), count=0)


def test_frames_are_pulled_one_each_from_the_master_in_order(tmp_path):
    calls: list[list[str]] = []

    def run(cmd: list[str]) -> None:
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"png")

    out = tmp_path / "proof"
    picks = [Instant("lint", "a", "a", 1.5, "open"), Instant("lint", "b", "b", 2.0, "closed")]
    names = lip_proof.frames(picks, tmp_path / "m.mp4", out, crop="600:480:240:520", run=run)
    assert [p.name for p in names] == ["lip00.png", "lip01.png"]
    assert calls[0][calls[0].index("-ss") + 1] == "1.500"
    assert "crop=600:480:240:520" in calls[0]


def test_a_frame_ffmpeg_could_not_write_stops_the_proof(tmp_path):
    def run(cmd: list[str]) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    with pytest.raises(LipProofError, match="ffmpeg"):
        lip_proof.frames([Instant("lint", "a", "a", 1.0, "open")], tmp_path / "m.mp4", tmp_path / "o", run=run)


def test_the_command_prints_the_table_and_counts_the_shut_vowels(tmp_path, capsys):
    root = project(tmp_path, [take("01", 0.0, "Oh")], [[0.0, "closed"]])
    assert cli.main(["lip-proof", str(root), "--count", "1"]) == 0
    printed = capsys.readouterr().out
    assert "Oh" in printed and "closed" in printed and "1 vowel on a shut mouth" in printed


def test_the_command_reports_a_missing_recording(tmp_path, capsys):
    assert cli.main(["lip-proof", str(tmp_path)]) == 2
    assert "speech.json" in capsys.readouterr().err
