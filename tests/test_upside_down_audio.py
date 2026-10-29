"""The timeline of Upside Down: every gag sits in a gap between lines, nothing overlaps, and the script is sound."""

import sys
from pathlib import Path

import pytest

from srstudio.interview import declarations

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import upside_down_audio
    finally:
        sys.path.pop(0)
    return upside_down_audio


SPEECH = [2.1, 1.9, 2.4, 1.8, 2.2, 1.1, 1.5]
EFFECT = {"speaker-beep": 0.3, "speaker-beep-2": 0.3, "board-flip": 0.55, "board-flip-back": 0.6, "door-chime": 0.8}


def test_lines_follow_each_other_without_overlap(audio):
    starts = list(audio.schedule(SPEECH, EFFECT).lines)
    ends = [s + d for s, d in zip(starts, SPEECH, strict=True)]
    assert len(starts) == len(audio.SCRIPT)
    assert all(e < s for e, s in zip(ends, starts[1:], strict=False))


def test_each_effect_plays_alone_in_its_gap(audio):
    plan = audio.schedule(SPEECH, EFFECT)
    starts, fx = list(plan.lines), plan.effects
    spans = [(s, s + d) for s, d in zip(starts, SPEECH, strict=True)]
    gaps = {"speaker-beep": 2, "board-flip": 3, "speaker-beep-2": 4, "board-flip-back": 5}  # after line i (0-based)
    for name, line in gaps.items():
        assert spans[line][1] < fx[name] and fx[name] + EFFECT[name] < spans[line + 1][0], name
    assert fx["door-chime"] + EFFECT["door-chime"] <= starts[0] + 0.1


def test_the_script_has_a_voice_and_a_style_for_every_role_and_unique_effects(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES)
    lines, effects = declarations(audio.INTERVIEW)
    assert [g.id for g in lines] == [f"line-{i + 1}" for i in range(len(audio.SCRIPT))]
    assert len({g.id for g in effects}) == len(audio.EFFECTS)
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]  # pinned takes
    assert all(0.7 <= line.speed <= 1.2 for line in audio.SCRIPT)
