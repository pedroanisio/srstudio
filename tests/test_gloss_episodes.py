"""The seven Gloss reels (ADR 0030): each script is well formed and speakable, and each staging fits a recording
of it before any request is made (the drawing itself is tested in test_gloss.py)."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

from srstudio import gloss_reel
from srstudio.gloss import GlossError
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
REELS = ("orientation", "joy_points", "trust_fall", "feedback", "exit", "wellness", "terms")
SECONDS_A_WORD = 0.35  # a calm speaking rate for the synthetic recording


def load(name: str):
    sys.path.insert(0, str(EPISODES))
    try:
        return importlib.import_module(f"gloss_{name}_audio").REEL
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="module", params=REELS)
def reel(request):
    return load(request.param)


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


def test_the_seven_reels_are_numbered_g1_to_g7_with_distinct_gloss_slugs():
    reels = [load(n) for n in REELS]
    assert [r.number for r in reels] == [f"G{i}" for i in range(1, 8)]
    assert len({r.slug for r in reels}) == 7 and all(r.slug.startswith("gloss-") for r in reels)
    for n in REELS:
        assert (EPISODES / f"gloss_{n}.py").read_text().count(f"from gloss_{n}_audio import REEL") == 1


def test_the_script_is_well_formed_before_anything_is_requested(reel):
    reel.script().check()


def test_every_line_is_plain_words_speech_to_text_can_hear(reel):
    for t in reel.takes:
        if not t.is_effect:
            assert not re.search(r"[-—#%/0-9]", t.text), f"take {t.id}: {t.text!r} is not plain spoken words"


def test_the_reel_opens_on_sunnys_hook_question_and_ends_on_the_plaza_notice(reel):
    first, last = reel.takes[0], reel.takes[-1]
    assert first.actor == last.actor == gloss_reel.HOST
    assert reel.hook.endswith("?") and first.text == reel.hook
    stages = reel.stages(recorded(reel))
    assert stages[last.id].notice is not None
    assert all(s.notice is None for k, s in stages.items() if k != last.id)


def test_the_punchline_is_held_at_least_a_beat_and_a_bit(reel):
    assert max(t.hold for t in reel.takes[:-1]) >= 1.2


@pytest.mark.parametrize("rate", [SECONDS_A_WORD, 0.25, 0.5])
def test_the_staging_fits_the_recording_at_any_reasonable_pace(reel, rate):
    takes = recorded(reel, rate)
    gloss_reel.check(takes, reel.stages(takes))


def test_a_recording_that_lost_a_take_is_refused_before_drawing(reel):
    takes = recorded(reel)
    stages = reel.stages(takes)
    with pytest.raises(GlossError, match="takes without a stage|stages without a take"):
        gloss_reel.check(takes[:-1], stages)


def test_every_location_and_prop_option_draws_before_anything_is_recorded(reel):
    from sr_core.scene import Scene

    from srstudio import PLASTIC, Canvas, flat_counter, gloss_sets

    for rate in (0.25, SECONDS_A_WORD, 0.5):
        takes = recorded(reel, rate)
        stages = reel.stages(takes)
        for take in takes:
            s = stages[take.id]
            if s.notice is not None:
                continue
            scene = Scene(version="auto")
            scene.add_project(width=1080, height=1920, fps="24", duration=take.duration, background="#ffffff")
            cv = Canvas(scene, PLASTIC, namer=flat_counter("g"))
            gloss_sets.SETS[s.set](cv, cv.comp, end=take.duration, **s.options)
            for prop in s.props:
                gloss_sets.PROPS[prop.name](cv, cv.comp, at=(prop.x, prop.y), end=take.duration, **prop.options)
