import math
from dataclasses import replace

from srstudio import CAFE_MOUTH, OFFICE_MOUTH, Soundtrack, Timeline, mouth_states
from srstudio.soundtrack import pose_keys


def test_rms_is_loud_inside_phrases_and_silent_outside(project):
    t = Timeline.load(project / "dialogue.json")
    s = Soundtrack(project / "assets" / "dialogue.wav")
    p = t.phrases[0]
    assert s.rms(p.start + 0.2, p.start + 0.4) > 0.1
    assert s.rms(0, 0.2) == 0
    assert s.rms(t.duration + 5, t.duration + 6) == 0


def test_mouth_states_follow_the_speaking_role(project):
    t = Timeline.load(project / "dialogue.json")
    s = Soundtrack(project / "assets" / "dialogue.wav")
    states = mouth_states(s, t, "candidate", 30, smile=[(0, t.phrases[0].start)])
    assert len(states) == math.ceil(t.duration * 30 - 1e-9)
    by_time = dict(states)
    assert by_time[0.0] == "smile"
    manager_line = t.phrases[0]
    assert by_time[round(int((manager_line.start + 0.5) * 30) / 30, 6)] == "rest"
    talking = {st for tm, st in states if t.phrases[1].start + 0.1 <= tm < t.phrases[1].end - 0.1}
    assert talking <= {"open", "small", "round"} and talking
    idle = mouth_states(s, t, "barista", 30, style=replace(CAFE_MOUTH, idle="smile"))
    assert {st for _, st in idle} == {"smile"}


def test_pose_keys_compress_runs():
    states = [(0, "rest"), (1 / 30, "open"), (2 / 30, "open"), (3 / 30, "rest")]
    assert pose_keys(states, "open") == [(0, 0), (1 / 30, 1), (3 / 30, 0)]
    assert pose_keys(states, "smile") == [(0, 0)]
    assert OFFICE_MOUTH.window != CAFE_MOUTH.window
