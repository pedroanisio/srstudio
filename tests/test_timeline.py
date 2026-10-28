import json

import pytest

from srstudio import Timeline


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


def test_word_time_from_character_alignment(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "p.json").write_text(
        json.dumps(
            {
                "normalized_alignment": {
                    "characters": list("I can disappoint several people"),
                    "character_start_times_seconds": [i * 0.05 for i in range(len("I can disappoint several people"))],
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
    t = Timeline.load(tmp_path / "dialogue.json")
    index = "I can disappoint several people".index("several")
    assert t.word_time(0, "several") == pytest.approx(1.0 + index * 0.05 - 0.1)
    with pytest.raises(ValueError):
        t.word_time(0, "absent")
