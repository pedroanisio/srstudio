"""A rehearsal: an episode's timeline and mix from tones, so it can be looked at before any take is paid for."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from fakes import ffmpeg_required
from srstudio import cli
from srstudio import interview as I
from srstudio.timeline import Phrase
from support.interview import make


def schedule(speech, effect) -> I.Schedule:
    return I.Schedule([0.5, 0.5 + speech[0] + 0.3], {"squeak": 0.2})


def scene(tmp_path: Path, iv: I.Interview | None = None) -> dict:
    out = I.rehearse(iv or make(), tmp_path, schedule=schedule, extra=lambda t: {"beat": t.phrases[1]["start"]})
    return json.loads(out.read_text())


def phrase(data: dict, i: int) -> Phrase:
    p = data["phrases"][i]
    return Phrase(index=i, role=p["role"], text=p["text"], caption=p["caption"], start=p["start"], end=p["end"])


@ffmpeg_required
def test_a_rehearsal_places_every_line_for_as_long_as_the_estimate_runs(tmp_path):
    data = scene(tmp_path)
    lengths = [p["end"] - p["start"] for p in data["phrases"]]
    assert lengths[0] == pytest.approx(I.spoken_estimate("Why here?", 1.0), abs=0.09)
    assert lengths[1] == pytest.approx(I.spoken_estimate("The chair.", 0.95), abs=0.09)
    assert data["rehearsal"] is True and data["beat"] == data["phrases"][1]["start"]


def test_a_slower_line_is_estimated_longer():
    assert I.spoken_estimate("one two three four", 0.9) > I.spoken_estimate("one two three four", 1.1)


@ffmpeg_required
def test_a_rehearsal_writes_no_take_into_the_takes_own_cache(tmp_path):
    data = scene(tmp_path)
    assert not (tmp_path / "assets" / "generated").exists()
    assert not (tmp_path / "assets" / "elevenlabs").exists()
    caches = [clip["generated"]["cache"] for clip in data["clips"]]
    assert caches and all(c.startswith("assets/rehearsal/") and (tmp_path / c).is_file() for c in caches)


@ffmpeg_required
def test_a_rehearsal_still_refuses_a_schedule_that_overlaps_two_lines(tmp_path):
    def late(speech, effect):
        return I.Schedule([0.5, 0.6], {"squeak": 0.2})

    with pytest.raises(I.InterviewError, match="past the next line"):
        I.rehearse(make(), tmp_path, schedule=late)


@ffmpeg_required
def test_said_spaces_a_rehearsals_words_evenly_through_its_line(tmp_path):
    data = scene(tmp_path)
    second = phrase(data, 1)
    assert I.said(tmp_path, second, "the") == pytest.approx(second.start)
    assert I.said(tmp_path, second, "chair") == pytest.approx((second.start + second.end) / 2)


@ffmpeg_required
def test_said_refuses_a_word_the_rehearsed_line_does_not_have(tmp_path):
    second = phrase(scene(tmp_path), 1)
    with pytest.raises(I.InterviewError, match="is not heard"):
        I.said(tmp_path, second, "desk")


@ffmpeg_required
def test_a_rehearsed_project_cannot_be_built_for_a_voiced_master(tmp_path):
    scene(tmp_path)
    with pytest.raises(I.InterviewError, match="rehearsal"):
        I.refuse_rehearsal(tmp_path)


def test_a_project_with_no_rehearsal_builds(tmp_path):
    (tmp_path / "dialogue.json").write_text(json.dumps({"phrases": []}))
    I.refuse_rehearsal(tmp_path)
    I.refuse_rehearsal(tmp_path / "missing")


@ffmpeg_required
def test_the_cli_refuses_a_voiced_build_of_a_rehearsal(tmp_path, capsys):
    scene(tmp_path)
    script = tmp_path / "reel.py"
    script.write_text("raise SystemExit('the build ran')\n")
    assert cli.main(["build", str(script), str(tmp_path), "--voice"]) == 1
    assert "rehearsal" in capsys.readouterr().err


def test_a_rehearsals_tones_run_at_the_mix_rate_so_a_mix_can_read_them(tmp_path):
    data = scene(tmp_path)
    for clip in data["clips"]:
        with wave.open(str(tmp_path / clip["generated"]["cache"]), "rb") as w:
            assert w.getframerate() == I.RATE
