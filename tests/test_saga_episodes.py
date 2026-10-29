"""The seven Saga reels (ADR 0025): each script is well formed and speakable, and each staging fits a recording
of it before any request is made (the drawing itself is tested in test_saga.py)."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

from srstudio import saga_reel
from srstudio.saga import SagaError
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
REELS = (
    "known_issue",
    "annual_review",
    "group_chat",
    "card_reader",
    "update",
    "free_tier",
    "open_plan",
    "icebreaker",
    "exit_interview",
    "moving_day",
    "expense_report",
    "on_hold",
)
SECONDS_A_WORD = 0.35  # a calm speaking rate for the synthetic recording


@pytest.fixture(scope="module", params=REELS)
def reel(request):
    sys.path.insert(0, str(EPISODES))
    try:
        return importlib.import_module(f"saga_{request.param}_audio").REEL
    finally:
        sys.path.pop(0)


def recorded(reel, rate: float = SECONDS_A_WORD) -> list[Take]:
    """A synthetic recording of ``reel``: every word at ``rate``, the hold after the last, effects at their kept
    length; letters stand in for phones."""
    out, start = [], 0.0
    for t in reel.takes:
        if t.is_effect:
            words, length = (), t.longest
        else:
            words = tuple(
                {"text": w, "start": round(0.05 + i * rate, 3), "end": round(0.05 + (i + 1) * rate, 3)}
                for i, w in enumerate(t.text.split())
            )
            length = words[-1]["end"] + 0.05
        phones = tuple({"c": c, "start": 0.05 + i * 0.06, "end": 0.11 + i * 0.06} for i, c in enumerate(t.text.lower()))
        duration = round(length + t.hold, 3)
        out.append(Take(t.id, t.actor, "", t.text, round(start, 3), duration, words=words, phones=phones))
        start += duration
    return out


def test_the_reels_are_numbered_in_order_with_distinct_saga_slugs():
    sys.path.insert(0, str(EPISODES))
    try:
        reels = [importlib.import_module(f"saga_{n}_audio").REEL for n in REELS]
    finally:
        sys.path.pop(0)
    assert [r.number for r in reels] == [f"S{i}" for i in range(1, len(REELS) + 1)]
    assert len({r.slug for r in reels}) == len(REELS) and all(r.slug.startswith("saga-") for r in reels)
    for n in REELS:
        assert (EPISODES / f"saga_{n}.py").read_text().count(f"from saga_{n}_audio import REEL") == 1


def test_the_script_is_well_formed_before_anything_is_requested(reel):
    reel.script().check()


def test_every_line_is_plain_words_speech_to_text_can_hear(reel):
    for t in reel.takes:
        if not t.is_effect:
            assert not re.search(r"[-—#%/0-9]", t.text), f"take {t.id}: {t.text!r} is not plain spoken words"


def test_the_reel_opens_on_its_narrated_hook_question_and_ends_on_a_narrated_handbook_entry(reel):
    first, last = reel.takes[0], reel.takes[-1]
    assert first.actor == last.actor == saga_reel.NARRATOR
    assert reel.hook.endswith("?") and first.text.endswith("?")
    stages = reel.stages(recorded(reel))
    assert stages[last.id].entry is not None
    assert all(s.entry is None for k, s in stages.items() if k != last.id)


def test_the_punchline_is_held_at_least_a_beat_and_a_bit(reel):
    assert max(t.hold for t in reel.takes[:-1]) >= 1.2


@pytest.mark.parametrize("rate", [SECONDS_A_WORD, 0.25, 0.5])
def test_the_staging_fits_the_recording_at_any_reasonable_pace(reel, rate):
    takes = recorded(reel, rate)
    saga_reel.check(takes, reel.stages(takes))


def test_a_recording_that_lost_a_take_is_refused_before_drawing(reel):
    takes = recorded(reel)
    stages = reel.stages(takes)
    with pytest.raises(SagaError, match="takes without a stage|stages without a take"):
        saga_reel.check(takes[:-1], stages)
