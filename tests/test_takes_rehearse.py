"""A rehearsal of takes: a script's timeline on estimated lengths and silent clips, before any take is paid for."""

from __future__ import annotations

import json
import wave
from dataclasses import replace

import pytest

from srstudio import cli, scripting, stick, takes
from srstudio.timeline import Timeline
from srstudio.voice import RATE
from support.takes import script


def seconds_of(path):
    with wave.open(str(path), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
        return w.getnframes() / RATE


def rehearsal(tmp_path, s=None):
    timeline = takes.rehearse(s or script(), tmp_path)
    return timeline, json.loads((tmp_path / "timeline.json").read_text())


def spoken(timeline):
    return [q for q in timeline["items"] if q["speech_duration"]]


def test_a_rehearsal_is_a_timeline_the_picture_can_load_with_the_real_contract(tmp_path):
    s = script()
    written, read = rehearsal(tmp_path, s)
    assert written == read and read["rehearsal"] is True
    loaded = Timeline.load(tmp_path / "timeline.json")
    assert [t.id for t in loaded.takes] == [t.id for t in s.takes]
    assert [t.shot for t in loaded.takes] == [t.shot for t in s.takes]
    assert loaded.duration == pytest.approx(sum(t.duration for t in loaded.takes), abs=1 / s.fps)


def test_each_line_runs_for_its_estimate_and_keeps_its_hold(tmp_path):
    s = script()
    timeline, _ = rehearsal(tmp_path, s)
    by_id = {q["id"]: q for q in timeline["items"]}
    for take in s.takes:
        if take.is_effect:
            continue
        q = by_id[take.id]
        pace = s.settings_for(take).speed
        assert q["speech_duration"] == pytest.approx(scripting.line_seconds(take.text, pace), abs=1e-6)
        assert q["duration"] == pytest.approx(q["speech_duration"] + take.hold, abs=1e-6)


def test_a_faster_take_is_a_shorter_rehearsal(tmp_path):
    s = script()
    fast = replace(s, takes=[replace(s.takes[0], speed=1.2), *s.takes[1:]])
    assert (
        spoken(rehearsal(tmp_path, fast)[0])[0]["speech_duration"]
        < spoken(takes.rehearse(s, tmp_path))[0]["speech_duration"]
    )


def test_words_and_phones_run_in_order_inside_the_speech_so_rigs_and_captions_can_time_on_them(tmp_path):
    for q in spoken(rehearsal(tmp_path)[0]):
        assert [w["text"] for w in q["words"]] == q["text"].split()
        assert "".join(p["c"] for p in q["phones"]) == q["text"]
        for marks in (q["words"], q["phones"]):
            assert all(0 <= m["start"] < m["end"] <= q["speech_duration"] + 1e-6 for m in marks)
            assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(marks, marks[1:], strict=False))


def test_captions_build_on_a_rehearsal(tmp_path):
    rehearsal(tmp_path)
    loaded = Timeline.load(tmp_path / "timeline.json")
    cues = stick.word_cues(loaded.takes, min_seconds=0.85, linger=0.9, width=lambda text: 40.0 * len(text), size=88)
    assert cues and cues[0].start == pytest.approx(0.0)


def test_an_effect_takes_the_most_of_it_kept_and_says_nothing(tmp_path):
    s = script()
    timeline, _ = rehearsal(tmp_path, s)
    effects = [t for t in s.takes if t.is_effect]
    assert effects
    by_id = {q["id"]: q for q in timeline["items"]}
    for take in effects:
        q = by_id[take.id]
        assert q["speech_duration"] == 0 and "words" not in q
        assert q["duration"] == pytest.approx(take.longest + take.hold, abs=1e-6)


def test_a_still_opening_moves_the_first_line_later_as_the_recording_does(tmp_path):
    plain = spoken(rehearsal(tmp_path)[0])[0]
    still = takes.rehearse(replace(script(), still=1.5), tmp_path)["items"][0]
    assert still["still"] == 1.5
    assert still["duration"] == pytest.approx(plain["duration"] + 1.5, abs=1e-6)
    assert still["words"][0]["start"] == pytest.approx(plain["words"][0]["start"] + 1.5, abs=1e-6)


def test_the_clips_are_silent_and_stay_out_of_the_takes_own_folder(tmp_path):
    timeline, _ = rehearsal(tmp_path)
    assert list((tmp_path / "audio").iterdir()) == []  # there, empty, for the foley a reel writes beside its takes
    for q in timeline["items"]:
        assert q["audio"].startswith("assets/rehearsal/")
        clip = tmp_path / q["audio"]
        assert seconds_of(clip) == pytest.approx(q["duration"], abs=1 / RATE)
        with wave.open(str(clip), "rb") as w:
            assert not any(w.readframes(w.getnframes()))


def test_a_rehearsal_refuses_a_malformed_script_before_it_writes_anything(tmp_path):
    with pytest.raises(takes.TakesError, match="at least one take"):
        takes.rehearse(replace(script(), takes=()), tmp_path)
    assert not (tmp_path / "timeline.json").exists()


def test_a_rehearsal_never_replaces_a_recording(tmp_path):
    recorded = {"tts_engine": "ElevenLabs", "duration": 1.0, "items": []}
    (tmp_path / "timeline.json").write_text(json.dumps(recorded))
    with pytest.raises(takes.TakesError, match="recording"):
        takes.rehearse(script(), tmp_path)
    assert json.loads((tmp_path / "timeline.json").read_text()) == recorded


def test_a_rehearsal_can_be_run_again(tmp_path):
    rehearsal(tmp_path)
    rehearsal(tmp_path)
    assert takes.rehearsed(tmp_path)


def test_a_project_is_a_rehearsal_only_when_its_timeline_says_so(tmp_path):
    assert not takes.rehearsed(tmp_path)
    takes.refuse_rehearsal(tmp_path)
    (tmp_path / "timeline.json").write_text('{"items": []}')
    assert not takes.rehearsed(tmp_path)
    takes.refuse_rehearsal(tmp_path)


@pytest.mark.parametrize("text", ["not json", "[]", '{"rehearsal": "yes"}'])
def test_a_timeline_that_cannot_be_read_as_recorded_or_rehearsed_is_refused(tmp_path, text):
    (tmp_path / "timeline.json").write_text(text)
    with pytest.raises(takes.TakesError, match="timeline.json"):
        takes.rehearsed(tmp_path)


def test_a_rehearsal_cannot_reach_a_voiced_master(tmp_path):
    rehearsal(tmp_path)
    with pytest.raises(takes.TakesError, match="rehearsal"):
        takes.refuse_rehearsal(tmp_path)


def test_the_cli_refuses_a_voiced_build_of_a_rehearsal(tmp_path, capsys):
    rehearsal(tmp_path)
    reel = tmp_path / "reel.py"
    reel.write_text("raise SystemExit('the build ran')\n")
    assert cli.main(["build", str(reel), str(tmp_path), "--voice"]) == 1
    assert "rehearsal" in capsys.readouterr().err


def test_the_cli_still_runs_a_silent_build_of_a_rehearsal(tmp_path):
    rehearsal(tmp_path)
    reel = tmp_path / "reel.py"
    reel.write_text("print('built')\n")
    assert cli.main(["build", str(reel), str(tmp_path)]) == 0


def test_main_rehearses_with_no_consent_and_no_key(tmp_path, capsys):
    s = script()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / s.font[0]).write_bytes(b"font")
    assert takes.main(s, [str(tmp_path), "--rehearse"], env={}) == 0
    assert takes.rehearsed(tmp_path)
    assert "rehearsal" in capsys.readouterr().out


def test_main_says_why_it_will_not_rehearse_over_a_recording(tmp_path):
    s = script()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / s.font[0]).write_bytes(b"font")
    (tmp_path / "timeline.json").write_text('{"items": []}')
    with pytest.raises(SystemExit, match="recording"):
        takes.main(s, [str(tmp_path), "--rehearse"], env={})


def test_main_still_needs_consent_to_record(tmp_path):
    with pytest.raises(SystemExit):
        takes.main(script(), [str(tmp_path)], env={})


def test_line_seconds_is_the_estimate_a_script_is_budgeted_by(tmp_path):
    text = "one two three four"
    assert scripting.line_seconds(text) == pytest.approx(scripting.SECONDS_A_WORD * 4 + scripting.SECONDS_A_LINE)
    assert scripting.line_seconds(text, 2.0) == pytest.approx(scripting.line_seconds(text) / 2)
