import json
from copy import deepcopy

import pytest

from srstudio import Timeline
from srstudio.timeline import TimelineError


def test_load_phrases_cuts_and_beats(project):
    t = Timeline.load(project / "dialogue.json")
    assert [p.role for p in t.phrases] == ["manager", "candidate", "manager", "candidate"]
    assert t.phrases[0].caption == "What's your greatest\nstrength?"
    assert t.reaction == pytest.approx(t.phrases[-1].end + 0.25)
    assert t.ending == t.end_card_start
    assert t.spans("candidate") == [t.phrases[1].span, t.phrases[3].span]


def test_shots_merge_adjacent_cuts(project):
    t = Timeline.load(project / "dialogue.json")
    wide = t.shots({"wide"})
    close = t.shots(lambda a: a != "wide")
    assert wide[0][0] == 0 and close[-1][1] == t.duration
    # Alternating angles give one interval per cut; the last one runs to the end.
    assert len(wide) == 2 and len(close) == 2
    merged = Timeline.from_dict(
        {
            "duration": 5,
            "phrases": [],
            "camera_cuts": [{"time": 0, "angle": "a"}, {"time": 1, "angle": "a"}, {"time": 3, "angle": "b"}],
        }
    )
    assert merged.shots({"a"}) == [(0.0, 3.0)]


def test_unknown_beat_raises(project):
    t = Timeline.load(project / "dialogue.json")
    with pytest.raises(AttributeError):
        t.park_start  # noqa: B018


def aligned(tmp_path, sentence: str) -> Timeline:
    """A one-phrase timeline from 1.0 s whose timing file gives character i of ``sentence`` at i × 0.05 s."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "p.json").write_text(
        json.dumps(
            {
                "normalized_alignment": {
                    "characters": list(sentence),
                    "character_start_times_seconds": [i * 0.05 for i in range(len(sentence))],
                }
            }
        )
    )
    (tmp_path / "dialogue.json").write_text(
        json.dumps(
            {
                "duration": 4,
                "phrases": [
                    {
                        "role": "candidate",
                        "text": "x",
                        "start": 1.0,
                        "end": 3.0,
                        "timing_file": "assets/p.json",
                        "trim_seconds": 0.1,
                    }
                ],
                "camera_cuts": [{"time": 0, "angle": "wide"}],
                "reaction_start": 3.2,
            }
        )
    )
    return Timeline.load(tmp_path / "dialogue.json")


def test_word_time_from_character_alignment(tmp_path):
    t = aligned(tmp_path, "I can disappoint several people")
    index = "I can disappoint several people".index("several")
    assert t.word_time(0, "several") == pytest.approx(1.0 + index * 0.05 - 0.1)
    with pytest.raises(TimelineError, match="no word 'absent'"):
        t.word_time(0, "absent")


@pytest.mark.parametrize(
    "sentence, word, at",
    [
        ("This is it.", "is", 5),  # not the "is" inside "This"
        ("Is this it?", "is", 0),  # case-blind, at the start
        ("Nope, no spaces here.", "no spaces", 6),  # a run of words, not "no" inside "Nope"
        ("It's here.", "it's", 0),  # an apostrophe belongs to the word
    ],
)
def test_word_time_matches_whole_words_only(tmp_path, sentence, word, at):
    assert aligned(tmp_path, sentence).word_time(0, word) == pytest.approx(1.0 + at * 0.05 - 0.1)


def test_word_time_refuses_a_word_only_found_inside_another(tmp_path):
    with pytest.raises(TimelineError, match="no word 'is'"):
        aligned(tmp_path, "This was it.").word_time(0, "is")


def dialogue():
    return {
        "duration": 3,
        "phrases": [{"role": "actor", "text": "Hello", "start": 0.2, "end": 1}],
        "camera_cuts": [{"time": 0, "angle": "wide"}, {"time": 1, "angle": "close"}],
    }


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_invalid_project_duration_is_rejected(duration):
    data = dialogue()
    data["duration"] = duration
    with pytest.raises(ValueError, match="duration"):
        Timeline.from_dict(data)


@pytest.mark.parametrize("start,end", [(-0.1, 1), (1, 1), (2, 1), (1, 4), (float("nan"), 1), (0, float("inf"))])
def test_phrase_ranges_must_be_finite_positive_and_inside_the_project(start, end):
    data = dialogue()
    data["phrases"][0].update(start=start, end=end)
    with pytest.raises(ValueError, match="phrase"):
        Timeline.from_dict(data)


@pytest.mark.parametrize("times", [[1, 0], [0, 0], [-1, 1], [0, 3], [0, float("nan")]])
def test_cuts_must_be_strictly_ordered_and_inside_the_project(times):
    data = dialogue()
    data["camera_cuts"] = [{"time": time, "angle": "wide"} for time in times]
    with pytest.raises(ValueError, match="cut"):
        Timeline.from_dict(data)


def sequence_data():
    return {
        "duration": 2.1,
        "items": [
            {"id": "01", "actor": "a", "shot": "wide", "text": "Hello", "start": 0, "duration": 1},
            {"id": "02", "actor": "b", "shot": "close", "text": "Hi", "start": 1, "duration": 1},
        ],
    }


@pytest.mark.parametrize("index,start", [(0, 0.1), (0, -0.1), (1, 1.05), (1, 0.95), (1, float("nan"))])
def test_sequence_gaps_and_overlaps_are_rejected_before_picture_and_audio_can_drift(index, start):
    data = sequence_data()
    data["items"][index]["start"] = start
    with pytest.raises(ValueError, match="take"):
        Timeline.from_takes(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"duration": 0},
        {"duration": -1},
        {"duration": float("inf")},
        {"duration": 5},
        {"speech_duration": -0.1},
        {"speech_duration": 2},
        {"id": "01"},
        {"words": [{"text": "Hi", "start": 0.1, "end": 2}]},
        {"phones": [{"c": "h", "start": -0.1, "end": 0.2}]},
    ],
)
def test_take_ranges_ids_and_local_alignment_must_be_valid(changes):
    data = sequence_data()
    data["items"][1].update(changes)
    with pytest.raises(ValueError, match="take"):
        Timeline.from_takes(data)


def test_sequence_allows_recording_roundoff_and_frame_rounded_trailing_silence():
    data = sequence_data()
    data["items"][1]["start"] += 0.0000004
    saved = deepcopy(data)
    timeline = Timeline.from_takes(data)
    assert timeline.duration == 2.1 and timeline.takes[1].start == data["items"][1]["start"]
    assert data == saved  # validation must not retime the source


@pytest.mark.parametrize("start,end", [(-1, 1), (float("nan"), 1), (0, float("inf"))])
def test_caption_timeline_also_rejects_negative_and_nonfinite_times(start, end):
    with pytest.raises(ValueError):
        Timeline.from_captions([{"start": start, "end": end, "text": "Hello"}])
