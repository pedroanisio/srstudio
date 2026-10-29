"""The timeline of Culture Fit: every gag in a gap between lines, a hold before the punchline, a sound script."""

import sys
from pathlib import Path

import pytest

from srstudio.interview import Timing, declarations

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import culture_fit_audio
    finally:
        sys.path.pop(0)
    return culture_fit_audio


SPEECH = [2.3, 1.9, 1.8, 1.2, 0.8, 1.25, 1.0, 1.1, 1.05]
EFFECT = {"flutter": 0.6, "coo-1": 0.7, "coo-2": 0.7, "offer-ping": 0.3, "coo-3": 0.7, "connect-ping": 0.35}


def spans(audio):
    plan = audio.schedule(SPEECH, EFFECT)
    starts = list(plan.lines)
    return [(s, s + d) for s, d in zip(starts, SPEECH, strict=True)], plan.effects


def test_lines_follow_each_other_without_overlap(audio):
    lines, _ = spans(audio)
    assert len(lines) == len(audio.SCRIPT)
    assert all(a[1] < b[0] for a, b in zip(lines, lines[1:], strict=False))


def test_each_effect_plays_alone_in_its_gap_and_the_last_ping_after_the_last_line(audio):
    lines, fx = spans(audio)
    gaps = {"flutter": 0, "coo-1": 1, "coo-2": 2, "offer-ping": 2, "coo-3": 6}  # after line i (0-based)
    for name, i in gaps.items():
        assert lines[i][1] < fx[name] and fx[name] + EFFECT[name] < lines[i + 1][0], name
    assert fx["coo-2"] + EFFECT["coo-2"] <= fx["offer-ping"]
    assert fx["connect-ping"] > lines[-1][1]


def test_the_punchline_and_the_counter_offer_each_get_a_hold(audio):
    lines, _ = spans(audio)
    assert lines[6][0] - lines[5][1] >= 1.2  # "I have a master's degree." ... "He works for crumbs."
    assert lines[7][0] - lines[6][1] >= 1.2  # ... "I can do crumbs."


def test_the_cuts_run_forward_and_end_on_the_card(audio):
    lines, fx = spans(audio)
    phrases = [{"start": s, "end": e} for s, e in lines]
    t = Timing(phrases, dict(fx), lines[-1][1], lines[-1][1] + 0.55, lines[-1][1] + 2.45, lines[-1][1] + 5.05)
    extra = audio.extra(t)
    times = [c["time"] for c in extra["camera_cuts"]]
    assert times == sorted(times) and times[0] == 0
    assert extra["camera_cuts"][-1] == {"time": t.ending, "angle": "end"}
    assert lines[5][1] < extra["toss_start"] < lines[6][0]


def test_the_script_has_a_voice_for_every_role_and_pinned_effects(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES)
    lines, effects = declarations(audio.INTERVIEW)
    assert [g.id for g in lines] == [f"line-{i + 1}" for i in range(len(audio.SCRIPT))]
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]
    assert all(0.7 <= line.speed <= 1.2 for line in audio.SCRIPT)
