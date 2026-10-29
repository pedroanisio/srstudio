"""The timeline of Elevator Pitch: every effect in a gap between lines, the doors and the pigeon between the pitch
and "Morning, Kevin.", the hold before the coo that decides, and the cuts."""

import sys
from pathlib import Path

import pytest

from srstudio.interview import Timing, declarations

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import elevator_pitch_audio
    finally:
        sys.path.pop(0)
    return elevator_pitch_audio


SPEECH = [3.4, 3.0, 0.9, 1.5, 2.6, 1.3, 1.9, 1.7, 1.6]
EFFECT = {"ding-4": 0.9, "coo-1": 0.7, "ding-9": 0.9, "coo-2": 0.9}


def spans(audio):
    plan = audio.schedule(SPEECH, EFFECT)
    return [(s, s + d) for s, d in zip(plan.lines, SPEECH, strict=True)], plan.effects


def test_lines_follow_each_other_without_overlap(audio):
    lines, _ = spans(audio)
    assert len(lines) == len(audio.SCRIPT)
    assert all(a[1] < b[0] for a, b in zip(lines, lines[1:], strict=False))


def test_each_effect_plays_alone_in_its_gap(audio):
    lines, fx = spans(audio)
    for name, i in {"ding-4": 1, "coo-1": 1, "ding-9": 6, "coo-2": 7}.items():  # after line i (0-based)
        assert lines[i][1] < fx[name] and fx[name] + EFFECT[name] < lines[i + 1][0], name
    assert fx["ding-4"] + EFFECT["ding-4"] < fx["coo-1"]  # the doors open before the pigeon coos in


def test_the_call_holds_before_the_coo_that_decides(audio):
    lines, fx = spans(audio)
    assert fx["coo-2"] - lines[7][1] >= 1.2  # "Kevin, your call." ... coo
    assert audio.SCRIPT[7].text.endswith("your call.") and "five days" in audio.SCRIPT[8].text


def test_the_cuts_run_forward_and_end_on_the_card(audio):
    lines, fx = spans(audio)
    phrases = [{"start": s, "end": e} for s, e in lines]
    t = Timing(phrases, dict(fx), lines[-1][1], lines[-1][1] + 0.55, lines[-1][1] + 2.65, lines[-1][1] + 5.25)
    extra = audio.extra(t)
    times = [c["time"] for c in extra["camera_cuts"]]
    assert times == sorted(times) and times[0] == 0
    assert extra["camera_cuts"][-1] == {"time": t.ending, "angle": "end"}
    assert {c["angle"] for c in extra["camera_cuts"]} == {"wide", "candidate", "manager", "display", "pigeon", "end"}


def test_the_script_has_a_voice_for_every_role_and_pinned_effects(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES)
    lines, effects = declarations(audio.INTERVIEW)
    assert [g.id for g in lines] == [f"line-{i + 1}" for i in range(len(audio.SCRIPT))]
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers
