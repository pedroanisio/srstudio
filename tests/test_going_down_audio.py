"""The timeline of Going Down: every effect in a gap between lines, Kevin walking in at floor 4 between the
euphemisms and "Kevin?", the slip dropped before the boss asks about his own role, the hold before the coo that
answers him, the lobby before the park, and the cuts."""

import sys
from pathlib import Path

import pytest

from srstudio.interview import Timing, declarations

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import going_down_audio
    finally:
        sys.path.pop(0)
    return going_down_audio


SPEECH = [1.2, 2.0, 1.0, 3.2, 1.6, 2.6, 2.0, 1.1, 0.9]
EFFECT = {"ding-4": 0.9, "coo-1": 0.7, "drop": 0.5, "coo-2": 0.9, "ding-1": 0.9, "flutter": 1.1, "coo-3": 0.8}


def spans(audio):
    plan = audio.schedule(SPEECH, EFFECT)
    return [(s, s + d) for s, d in zip(plan.lines, SPEECH, strict=True)], plan.effects


def test_lines_follow_each_other_without_overlap(audio):
    lines, _ = spans(audio)
    assert len(lines) == len(audio.SCRIPT) == len(SPEECH)
    assert all(a[1] < b[0] for a, b in zip(lines, lines[1:], strict=False))


def test_each_effect_plays_alone_in_its_gap(audio):
    lines, fx = spans(audio)
    gaps = {"ding-4": 3, "coo-1": 3, "drop": 5, "coo-2": 6, "ding-1": 6, "flutter": 6}  # after line i (0-based)
    for name, i in gaps.items():
        assert lines[i][1] < fx[name] and fx[name] + EFFECT[name] < lines[i + 1][0], name
    assert fx["ding-4"] + EFFECT["ding-4"] < fx["coo-1"]  # the doors open before Kevin coos in
    assert fx["coo-2"] + EFFECT["coo-2"] < fx["ding-1"] and fx["ding-1"] + EFFECT["ding-1"] < fx["flutter"]
    assert fx["coo-3"] > lines[-1][1]  # the last coo answers the last line


def test_the_question_holds_before_the_coo_that_answers_it(audio):
    lines, fx = spans(audio)
    assert fx["coo-2"] - lines[6][1] >= 1.2
    assert "sunset" in audio.SCRIPT[1].text and "my role" in audio.SCRIPT[6].text  # the callback
    assert audio.SCRIPT[0].text.endswith("?") and audio.SCRIPT[0].role == "candidate"  # the hook is a question


def test_the_cuts_run_forward_end_on_the_card_and_change_rooms_at_the_lobby(audio):
    lines, fx = spans(audio)
    phrases = [{"start": s, "end": e} for s, e in lines]
    end = lines[-1][1]
    t = Timing(phrases, dict(fx), end, end + audio.INTERVIEW.reaction_after, end + 2.4, end + 5.0)
    extra = audio.extra(t)
    cuts = extra["camera_cuts"]
    times = [c["time"] for c in cuts]
    assert times == sorted(times) and times[0] == 0
    assert cuts[-1] == {"time": t.ending, "angle": "end"}
    assert extra["park_start"] == next(c["time"] for c in cuts if c["angle"].startswith("park"))
    assert fx["ding-1"] < extra["park_start"] < fx["flutter"]
    slip = next(c["time"] for c in cuts if c["angle"] == "slip")
    assert fx["drop"] < slip < lines[6][0]  # the name on the slip reads before the boss asks


def test_the_script_has_a_voice_for_every_role_and_pinned_effects(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES)
    lines, effects = declarations(audio.INTERVIEW)
    assert [g.id for g in lines] == [f"line-{i + 1}" for i in range(len(audio.SCRIPT))]
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers
