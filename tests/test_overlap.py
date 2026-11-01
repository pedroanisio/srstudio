"""Lines that repeat another episode are found from the scripts, and a script that cannot be read stops the search."""

import json

import pytest

from srstudio.cli import main
from srstudio.overlap import Overlap, OverlapError, overlaps, project_script, read_lines, scripts


def script(folder, slug, *lines):
    (folder / slug).mkdir(parents=True)
    rows = [{"start": 0.0, "end": 1.0, "text": line} for line in lines]
    (folder / slug / "script.json").write_text(json.dumps(rows), encoding="utf-8")


def voiced(folder, slug, *lines):
    (folder / slug / "voiced").mkdir(parents=True)
    rows = [{"start": 0.0, "end": 1.0, "text": line} for line in lines]
    (folder / slug / "voiced" / "script.json").write_text(json.dumps(rows), encoding="utf-8")


def test_a_shared_run_of_words_is_found_whatever_the_case_and_punctuation():
    found = overlaps(["Split it evenly, please!"], {"old": ["We split it, evenly, please."]})
    assert found == [
        Overlap("Split it evenly, please!", "old", "We split it, evenly, please.", "split it evenly please")
    ]


def test_a_curly_apostrophe_is_the_same_word():
    assert overlaps(["Don’t go to that place"], {"old": ["Don't go to that place"]})


def test_fewer_words_than_the_least_is_everyday_speech():
    assert overlaps(["What is going on here"], {"old": ["What is it, where is going on"]}) == []


def test_the_least_can_be_raised():
    assert overlaps(["one two three four"], {"old": ["one two three four"]}, least=5) == []


def test_a_run_of_no_words_is_refused():
    with pytest.raises(OverlapError, match="at least one word"):
        overlaps(["a"], {}, least=0)


def test_scripts_reads_every_episode_and_skips_the_one_being_checked(tmp_path):
    script(tmp_path, "a", "first line")
    script(tmp_path / "pilots", "b", "second line")
    assert scripts(tmp_path, skip="a") == {"b": ["second line"]}


def test_a_voiced_episode_is_read_from_what_was_recorded(tmp_path):
    script(tmp_path, "a", "the silent draft")
    voiced(tmp_path, "a", "the recorded line")
    assert scripts(tmp_path) == {"a": ["the recorded line"]}


def test_every_voiced_episode_keeps_its_own_name(tmp_path):
    voiced(tmp_path, "a", "first line")
    voiced(tmp_path, "b", "second line")
    assert scripts(tmp_path) == {"a": ["first line"], "b": ["second line"]}


def test_a_voiced_episode_being_checked_is_skipped(tmp_path):
    script(tmp_path, "a", "the silent draft")
    voiced(tmp_path, "a", "the recorded line")
    voiced(tmp_path, "b", "second line")
    assert scripts(tmp_path, skip="a") == {"b": ["second line"]}


def test_an_episode_that_was_never_voiced_keeps_its_script(tmp_path):
    script(tmp_path, "a", "first line")
    assert project_script(tmp_path / "a") == tmp_path / "a" / "script.json"


def test_a_voiced_episode_is_checked_on_what_was_recorded(tmp_path, capsys):
    script(tmp_path, "a", "a line nobody ever said")
    voiced(tmp_path, "a", "the same four words")
    voiced(tmp_path, "b", "say the same four words")
    assert project_script(tmp_path / "a") == tmp_path / "a" / "voiced" / "script.json"
    assert main(["overlap", str(tmp_path / "a"), "--episodes", str(tmp_path)]) == 0
    assert "the same four words" in capsys.readouterr().out


@pytest.mark.parametrize("text", ["{", '{"text": "x"}', '[{"start": 0}]', "[1]", '[{"text": 3}]'])
def test_a_script_that_is_not_a_list_of_lines_is_refused(tmp_path, text):
    path = tmp_path / "script.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(OverlapError, match="script.json"):
        read_lines(path)


def test_a_missing_script_is_refused(tmp_path):
    with pytest.raises(OverlapError):
        read_lines(tmp_path / "script.json")


def test_the_command_lists_what_it_finds(tmp_path, capsys):
    script(tmp_path, "new", "Nobody comes back from a potluck")
    script(tmp_path, "old", "Nobody comes back from a wedding")
    assert main(["overlap", str(tmp_path / "new"), "--episodes", str(tmp_path)]) == 0
    assert "old: nobody comes back from a" in capsys.readouterr().out


def test_the_command_says_when_nothing_repeats(tmp_path, capsys):
    script(tmp_path, "new", "Something else entirely")
    assert main(["overlap", str(tmp_path / "new"), "--episodes", str(tmp_path)]) == 0
    assert "no overlap" in capsys.readouterr().out


def test_the_command_reports_a_broken_script(tmp_path, capsys):
    script(tmp_path, "new", "Fine")
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "script.json").write_text("{", encoding="utf-8")
    assert main(["overlap", str(tmp_path / "new"), "--episodes", str(tmp_path)]) == 2
    assert "srstudio overlap" in capsys.readouterr().err


def transcript(root, slug, *lines):
    folder = root / slug
    folder.mkdir(parents=True)
    rows = [{"role": "pip", "expected": line, "heard": line.lower()} for line in lines]
    (folder / "voice-transcript.json").write_text(json.dumps({"recognizer": "x", "lines": rows}))


def test_a_reel_with_only_a_transcript_is_read_by_what_it_was_asked_to_say(tmp_path):
    transcript(tmp_path, "takes", "Other door, thank you.", "Yes.")
    assert read_lines(project_script(tmp_path / "takes")) == ["Other door, thank you.", "Yes."]


def test_a_script_outranks_a_transcript_beside_it(tmp_path):
    transcript(tmp_path, "both", "from the transcript")
    (tmp_path / "both" / "script.json").write_text(json.dumps([{"role": "a", "text": "from the script"}]))
    assert read_lines(project_script(tmp_path / "both")) == ["from the script"]
    assert scripts(tmp_path) == {"both": ["from the script"]}


def test_a_reel_with_only_a_transcript_is_compared_with_the_others(tmp_path):
    transcript(tmp_path, "takes", "first in, last out, you got the job")
    transcript(tmp_path, "skipped", "this one is checked and is not in the pile")
    assert scripts(tmp_path, skip="skipped") == {"takes": ["first in, last out, you got the job"]}


def test_a_transcript_line_with_nothing_asked_of_it_is_refused(tmp_path):
    (tmp_path / "voice-transcript.json").write_text(json.dumps({"lines": [{"heard": "hi"}]}))
    with pytest.raises(OverlapError, match="line 0"):
        read_lines(tmp_path / "voice-transcript.json")


def test_a_transcript_with_no_list_of_lines_is_refused(tmp_path):
    (tmp_path / "voice-transcript.json").write_text(json.dumps({"lines": "hi"}))
    with pytest.raises(OverlapError, match="list of lines"):
        read_lines(tmp_path / "voice-transcript.json")
