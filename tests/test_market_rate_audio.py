"""The timeline of Market Rate: every effect in a gap between lines, the holds before the punchlines, the cuts."""

import sys
from pathlib import Path

import pytest

from srstudio.interview import Timing, declarations

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import market_rate_audio
    finally:
        sys.path.pop(0)
    return market_rate_audio


SPEECH = [1.6, 2.4, 0.9, 2.0, 1.2, 0.8, 2.1, 1.4, 1.5, 0.9, 1.1]
EFFECT = {"join": 0.6, "posting-ping": 0.3, "hold-music": 1.9, "endorse-ping": 0.35}


def spans(audio):
    plan = audio.schedule(SPEECH, EFFECT)
    starts = list(plan.lines)
    return [(s, s + d) for s, d in zip(starts, SPEECH, strict=True)], plan.effects


def test_lines_follow_each_other_without_overlap(audio):
    lines, _ = spans(audio)
    assert len(lines) == len(audio.SCRIPT)
    assert all(a[1] < b[0] for a, b in zip(lines, lines[1:], strict=False))


def test_each_effect_plays_alone_in_its_gap(audio):
    lines, fx = spans(audio)
    assert fx["join"] + EFFECT["join"] < lines[0][0]
    for name, i in {"posting-ping": 5, "hold-music": 9}.items():  # after line i (0-based)
        assert lines[i][1] < fx[name] and fx[name] + EFFECT[name] < lines[i + 1][0], name
    assert fx["endorse-ping"] > lines[-1][1]


def test_both_punchlines_get_a_hold(audio):
    lines, _ = spans(audio)
    assert lines[5][0] - lines[4][1] >= 1.2  # "Does Senior pay more?" ... "It's longer."
    assert lines[10][0] - lines[9][1] >= 1.2  # "Hold, please." (hold music) "Your interview is Thursday."


def test_the_cuts_run_forward_and_end_on_the_card(audio):
    lines, fx = spans(audio)
    phrases = [{"start": s, "end": e} for s, e in lines]
    t = Timing(phrases, dict(fx), lines[-1][1], lines[-1][1] + 0.55, lines[-1][1] + 2.65, lines[-1][1] + 5.25)
    extra = audio.extra(t)
    times = [c["time"] for c in extra["camera_cuts"]]
    assert times == sorted(times) and times[0] == 0
    assert extra["camera_cuts"][-1] == {"time": t.ending, "angle": "end"}
    assert {c["angle"] for c in extra["camera_cuts"]} == {"wide", "phone", "board", "candidate", "end"}


def test_the_script_has_a_voice_for_every_role_and_pinned_effects(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES)
    lines, effects = declarations(audio.INTERVIEW)
    assert [g.id for g in lines] == [f"line-{i + 1}" for i in range(len(audio.SCRIPT))]
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers
