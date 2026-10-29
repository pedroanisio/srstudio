"""Anonymous Employee Survey: the reel as data, its derivations, and what the narration script asks for (the
shared fitting steps are tested in test_narration.py, the Toon parts in test_toon.py)."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import narration as library
from srstudio import toon
from srstudio.fonts import GoogleFont
from srstudio.voice import Alignment

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import employee_survey_data

        return employee_survey_data
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module")
def script(data):
    sys.path.insert(0, str(EPISODES))
    try:
        import employee_survey_audio

        return employee_survey_audio
    finally:
        sys.path.pop(0)


# -- the data -----------------------------------------------------------------------------------------------
def test_the_segments_are_consistent_and_feed_the_toon_parsers(data):
    data.check()
    poses = toon.parse_poses(data.poses(data.SEGMENTS))
    lines = toon.parse_script(data.cues(data.SEGMENTS, data.END))
    assert poses[0].start == 0 and lines[-1].end == data.END
    assert toon.runs(poses, data.END)[-1][2] == data.END
    # consecutive identical captions are one cue (the typing beats keep their caption); a blank ends the cue
    assert [q.text for q in lines[:4]] == [
        "Anonymous Employee Survey",
        "Let's get into it",
        "Would you recommend",
        "working for this company?",
    ]
    assert lines[3].end == 6.375
    assert "Do you have any feed..." in [q.text for q in lines] and "mark an x where you s..." in [
        q.text for q in lines
    ]
    assert data.flashes(data.SEGMENTS) == [53.0]


def test_every_sentence_is_started_by_a_segment_in_order(data):
    spans = data.sentence_spans(data.SEGMENTS, data.END)
    assert len(spans) == len(data.SENTENCES) and spans[0] == (0.0, 1.75) and spans[-1][1] == data.END
    assert all(b > a for a, b in spans) and all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1))


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda s: [replace(s[0], start=0.5)] + list(s[1:]), "starts at 0"),
        (lambda s: list(s[:5]) + [replace(s[5], start=s[4].start + 0.05)] + list(s[6:]), "held less than"),
        (lambda s: list(s[:1]) + [replace(s[1], word=None)] + list(s[2:]), "go together"),
        (lambda s: list(s[:1]) + [replace(s[1], sentence=99)] + list(s[2:]), "no sentence 99"),
        (lambda s: list(s[:1]) + [replace(s[1], word=40)] + list(s[2:]), "has no word 40"),
        (lambda s: list(s[:2]) + [replace(s[2], sentence=0, word=0)] + list(s[3:]), "out of order"),
        (lambda s: list(s[:-1]) + [replace(s[-1], start=63.1)], "before the end"),
    ],
)
def test_inconsistent_segments_are_refused(data, change, match):
    with pytest.raises(data.SurveyDataError, match=match):
        data.check(change(list(data.SEGMENTS)), data.END)


def test_a_sentence_no_segment_starts_is_refused(data):
    segments = [q if q.sentence != 15 else replace(q, sentence=None, word=None) for q in data.SEGMENTS]
    with pytest.raises(data.SurveyDataError, match="every sentence needs a segment"):
        data.sentence_spans(segments, data.END)


def test_typing_bursts_sit_inside_the_typing_segments(data):
    bursts = data.typing_bursts(data.SEGMENTS, data.END)
    pairs = zip(data.SEGMENTS, data.SEGMENTS[1:], strict=False)
    typing = [(q.start, n.start) for q, n in pairs if q.arms in data.TYPING_ARMS]
    assert bursts and all(any(a < t < b - 0.3 for a, b in typing) for t in bursts)
    assert bursts == sorted(bursts) and all(round(b - a, 6) >= 0.3 for a, b in zip(bursts, bursts[1:], strict=False))
    assert any(10.8 < t < 11.75 for t in bursts)  # the lean on the keys clacks too


def test_typing_bursts_keep_clear_of_the_lines(data):
    quiet = data.typing_bursts(data.SEGMENTS, data.END)
    speech = [(5.0, 5.5), (6.375, 8.5)]  # the first typing run (5.0-7.875) is spoken over except 5.5-6.375
    bursts = data.typing_bursts(data.SEGMENTS, data.END, speech)
    first = [t for t in bursts if t < 8.75]
    assert first and all(5.5 + data.SPEECH_MARGIN <= t <= 6.375 - data.SPEECH_MARGIN for t in first)
    assert [t for t in bursts if t > 8.75] == [t for t in quiet if t > 8.75]
    assert data.typing_bursts(data.SEGMENTS, data.END, [(0.0, data.END)]) == []
    with pytest.raises(data.SurveyDataError, match="start < end"):
        data.typing_bursts(data.SEGMENTS, data.END, [(2.0, 1.0)])


# -- placing the picture on a narration ----------------------------------------------------------------------
def fake_words(data, scale: float, offset: float = 0.0):
    """Every word of every sentence evenly spread over a take ``scale`` times the reference span, in order."""
    spans = data.sentence_spans(data.SEGMENTS, data.END)
    starts, ends = [], []
    for (a, b), text in zip(spans, data.SENTENCES, strict=True):
        n = len(text.split())
        start = a * scale + offset
        length = (b - a) * scale * 0.8
        starts.append([round(start + k * length / n, 6) for k in range(n)])
        ends.append(round(start + length, 6))
    return starts, ends


def test_placed_segments_follow_the_words_and_keep_the_silent_beats(data):
    starts, ends = fake_words(data, 1.3)
    placed = data.place_segments(data.SEGMENTS, starts, ends)
    assert len(placed) == len(data.SEGMENTS) and placed[0].start == 0
    for before, after in zip(data.SEGMENTS, placed, strict=True):
        assert (after.caption, after.eyes, after.mouth, after.arms, after.flash) == (
            before.caption,
            before.eyes,
            before.mouth,
            before.arms,
            before.flash,
        )
        if before.sentence is not None and before.start > 0:
            word = starts[before.sentence][before.word]
            assert word - 1e-9 <= after.start <= word + data.CAPTION_LAG + 1e-9
    assert all(b.start - a.start >= data.MIN_STEP - 1e-9 for a, b in zip(placed, placed[1:], strict=False))
    # the sigh (a silent beat after "Do you have any feed...") waits for that line to end
    sigh = next(i for i, q in enumerate(data.SEGMENTS) if q.start == 20.75)
    assert placed[sigh].start >= ends[8] + data.BLANK_GAP - 1e-9
    assert placed[sigh].start <= starts[9][0] - data.BLANK_MARGIN + 1e-9
    # the camera flash keeps its place between "i don't..." and "Hey!"
    (flash,) = data.flashes(placed)
    assert starts[17][8] < flash < starts[18][0]
    data.check(placed, placed[-1].start + 2)


def test_a_short_caption_holds_back_the_next_change_but_only_so_far(data):
    starts, ends = fake_words(data, 1.3)
    age = next(i for i, q in enumerate(data.SEGMENTS) if q.caption == "age")
    # "start date" is spoken 0.5 s after "age": its caption waits for the minimum hold
    starts[12][10] = starts[12][9] + 0.5
    starts[12][11] = starts[12][10] + 0.2
    placed = data.place_segments(data.SEGMENTS, starts, ends)
    assert placed[age + 1].start == pytest.approx(placed[age].start + data.CAPTION_MIN)
    # spoken only 0.2 s after: the wait is capped, the caption stays short
    starts[12][10] = starts[12][9] + 0.2
    placed = data.place_segments(data.SEGMENTS, starts, ends)
    assert placed[age + 1].start == pytest.approx(starts[12][10] + data.CAPTION_LAG)


def test_the_hold_is_measured_from_the_caption_not_from_a_pose_change_under_it(data):
    # "Are you happy here?" (14.0) changes pose at 15.5 under the same caption; "I'm here" follows at 17.375
    starts, ends = fake_words(data, 1.0)
    happy = next(i for i, q in enumerate(data.SEGMENTS) if q.caption == "Are you happy here?")
    ends[6] = starts[6][0] + 0.5
    starts[7] = [starts[6][0] + 1.2]
    starts[8] = [starts[7][0] + 2.0 + 0.3 * k for k in range(len(starts[8]))]
    placed = data.place_segments(data.SEGMENTS, starts, ends)
    assert placed[happy + 1].start < starts[7][0] and placed[happy + 1].caption == "Are you happy here?"
    assert placed[happy + 2].start == pytest.approx(starts[7][0])  # on its word: the caption had its 0.85 s


def test_placing_refuses_takes_that_lack_the_words_or_sentences(data):
    starts, ends = fake_words(data, 1.0)
    with pytest.raises(data.SurveyDataError, match="every sentence"):
        data.place_segments(data.SEGMENTS, starts[:-1], ends)
    starts[12] = starts[12][:5]
    with pytest.raises(data.SurveyDataError, match="has no word"):
        data.place_segments(data.SEGMENTS, starts, ends)


def test_a_crowded_silent_beat_lands_halfway(data):
    # the beat after sentence 17 has no room before sentence 18: it is placed between its neighbours
    starts, ends = fake_words(data, 1.0)
    i = next(i for i, q in enumerate(data.SEGMENTS) if q.flash)
    starts[18] = [starts[17][8] + 0.2 + k * 0.1 for k in range(len(starts[18]))]
    ends[17] = starts[17][8] + 0.1
    placed = data.place_segments(data.SEGMENTS, starts, ends)
    assert placed[i - 1].start < placed[i].start < placed[i + 1].start


def test_write_project_and_write_voiced_lay_out_the_files(data, tmp_path, monkeypatch):
    installed = []
    monkeypatch.setattr(data.fonts, "install", lambda font, folder: installed.append((font, Path(folder))))
    data.write_project(tmp_path, GoogleFont("Comic Neue", 700, italic=True))
    assert installed == [(GoogleFont("Comic Neue", 700, italic=True), tmp_path / "assets" / "fonts")]
    assert toon.load_script(tmp_path / "script.json") and toon.load_poses(tmp_path / "assets" / "poses.json")
    placed = data.place_segments(data.SEGMENTS, *fake_words(data, 1.1))
    data.write_voiced(tmp_path, placed, 80.0)
    voiced = json.loads((tmp_path / "voiced" / "script.json").read_text())
    assert voiced[-1]["end"] == 80.0 and toon.load_poses(tmp_path / "voiced" / "poses.json")[0].start == 0


# -- the narration script -----------------------------------------------------------------------------------
def test_the_script_uses_the_library_steps_not_a_copy(script):
    for name in ("plan_relaxed", "conform", "confirm_voice", "require_consent"):
        assert getattr(script, name) is getattr(library, name), name
    assert script.SETTINGS.speed == 1.0 and script.NARRATOR.name == "Brian"
    assert script.TYPING_GAIN_DB <= 0 and script.CLICK_GAIN_DB <= 0 and 0 < script.TYPING_PEAK <= script.VOICE_PEAK


def test_the_cut_point_comes_from_the_character_alignment(script, data):
    text = data.SENTENCES[8]
    chars = tuple(text)
    starts = tuple(0.1 * i for i in range(len(chars)))
    ends = tuple(0.1 * i + 0.1 for i in range(len(chars)))
    at = script.cut_at(Alignment(chars, starts, ends), text, *data.CUTS[8])
    assert at == pytest.approx(ends[text.index("feedback") + 3] + script.CUT_TAIL)
    with pytest.raises(data.SurveyDataError, match="spells"):
        script.cut_at(Alignment(chars[:-1], starts[:-1], ends[:-1]), text, "feedback", 4)
    with pytest.raises(data.SurveyDataError, match="no word"):
        script.cut_at(Alignment(chars, starts, ends), text, "payday", 1)
