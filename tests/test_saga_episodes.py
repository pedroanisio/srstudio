"""The seven Saga reels (ADR 0025): each script is well formed and speakable, and each staging fits a recording
of it before any request is made (the drawing itself is tested in test_saga.py)."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

from srstudio import releases, saga_reel
from srstudio.saga import SagaError
from support.saga import SECONDS_A_WORD, recorded

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
REELS = tuple(sorted(p.name.removeprefix("saga_").removesuffix("_audio.py") for p in EPISODES.glob("saga_*_audio.py")))


@pytest.fixture(scope="module", params=REELS)
def reel(request):
    sys.path.insert(0, str(EPISODES))
    try:
        return importlib.import_module(f"saga_{request.param}_audio").REEL
    finally:
        sys.path.pop(0)


def test_the_reels_are_numbered_in_order_with_distinct_saga_slugs():
    sys.path.insert(0, str(EPISODES))
    try:
        reels = [importlib.import_module(f"saga_{n}_audio").REEL for n in REELS]
    finally:
        sys.path.pop(0)
    assert len(REELS) >= 12  # the reels are found, not listed
    assert sorted(int(r.number.removeprefix("S")) for r in reels) == list(range(1, len(REELS) + 1))
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
    stages = reel.stages(recorded(reel))
    lead = next(i for i, t in enumerate(reel.takes) if not stages[t.id].still)  # a still opening comes first
    first, last = reel.takes[lead], reel.takes[-1]
    assert all(t.is_effect for t in reel.takes[:lead])
    assert first.actor == last.actor == saga_reel.NARRATOR
    assert reel.hook.endswith("?") and first.text.endswith("?")
    assert stages[last.id].entry is not None
    assert all(s.entry is None for k, s in stages.items() if k != last.id)


def hook_motion_arm(reel) -> str:
    """The reel's arm in the posting job's first-second test (``sp-hook_motion``), or "" outside it."""
    release = releases.load(EPISODES / "posts").get(reel.slug)
    tags = release.tags if release is not None else None
    return tags.arm if tags is not None and tags.test == "sp-hook_motion" else ""


@pytest.mark.parametrize("rate", [SECONDS_A_WORD, 0.25])
def test_a_reel_in_the_first_second_test_opens_still_or_moving_as_its_arm_says(reel, rate):
    takes = recorded(reel, rate)
    stages = reel.stages(takes)
    arm = hook_motion_arm(reel)
    if arm == "a":  # nothing on screen changes before the first second is out: a still effect take, no caption
        still = next(t.start for t in takes if not stages[t.id].still)
        assert still >= 1.0
    elif arm == "b":  # a camera move or a shake under way by a quarter second, running through the first second
        opening = stages[takes[0].id]
        assert not opening.still and takes[0].duration >= 1.0
        moving = opening.move is not None and opening.move.at <= 0.25 and (opening.move.until or 0) >= 1.0
        assert moving or any(a <= 0.25 and b >= 1.0 for a, b in opening.shake)


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
