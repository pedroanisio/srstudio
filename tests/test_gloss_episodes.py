"""The Gloss reels (ADR 0030): each script is well formed and speakable, and each staging fits a recording
of it before any request is made (the drawing itself is tested in test_gloss.py)."""

from __future__ import annotations

import importlib
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import gloss_reel
from srstudio.gloss import GlossError
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
REELS = tuple(
    sorted(p.name.removeprefix("gloss_").removesuffix("_audio.py") for p in EPISODES.glob("gloss_*_audio.py"))
)
# G1-G6 were published with the native caption look and G7 with gloss_reel.LOOK, and they keep them; every later reel
# reads with gloss_reel.LOOK_INK, solid dark letters
PUBLISHED_WITH_NATIVE_LOOK = {"orientation", "joy_points", "trust_fall", "feedback", "exit", "wellness"}
PUBLISHED_WITH_GLOSS_LOOK = {"terms"}
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
        extra = {}
        if reel.still and not out:  # the recording puts a still opening inside the first take, as silence
            words = tuple({**w, "start": w["start"] + reel.still, "end": w["end"] + reel.still} for w in words)
            phones = tuple({**q, "start": q["start"] + reel.still, "end": q["end"] + reel.still} for q in phones)
            duration, extra = round(duration + reel.still, 3), {"still": reel.still}
        out.append(Take(t.id, t.actor, "", t.text, round(start, 3), duration, words=words, phones=phones, extra=extra))
        start += duration
    return out


def test_the_reels_are_numbered_from_g1_without_gaps_with_distinct_gloss_slugs():
    reels = [load(n) for n in REELS]
    assert len(REELS) >= 7  # the reels are found, not listed
    assert sorted(int(r.number.removeprefix("G")) for r in reels) == list(range(1, len(REELS) + 1))
    assert len({r.slug for r in reels}) == len(REELS) and all(r.slug.startswith("gloss-") for r in reels)
    for n in REELS:
        assert (EPISODES / f"gloss_{n}.py").read_text().count(f"from gloss_{n}_audio import REEL") == 1


def test_published_reels_keep_the_caption_look_they_shipped_with_and_new_reels_read_without_lone_words():
    from srstudio import native

    looks = {n: load(n).look() for n in REELS}
    assert {n for n, look in looks.items() if look is native.CAPTION_LOOK} == PUBLISHED_WITH_NATIVE_LOOK
    assert {n for n, look in looks.items() if look is gloss_reel.LOOK} == PUBLISHED_WITH_GLOSS_LOOK
    published = PUBLISHED_WITH_NATIVE_LOOK | PUBLISHED_WITH_GLOSS_LOOK
    assert all(looks[n] is gloss_reel.LOOK_INK for n in set(REELS) - published)
    ink, house = gloss_reel.LOOK_INK, gloss_reel.LOOK  # the lines wrap and hold as in LOOK; only the letters change
    plain = dict(color=house.color, active=house.active, stroke=house.stroke, stroke_width=house.stroke_width)
    assert replace(ink, **plain) == house
    assert ink.color == ink.active == ink.stroke == house.stroke  # one dark tone, the sung word too
    assert 0 < ink.stroke_width < house.stroke_width  # outlined in its own color, thinly


def test_every_reel_is_a_gloss_series_reel_staged_by_the_gloss_reel_builder(reel):
    from srstudio import GLOSS, series

    assert isinstance(reel, series.Reel)
    assert reel.series is not None and reel.series.style is GLOSS and reel.series.stage is gloss_reel.build


def test_only_the_operator_approved_hearing_is_accepted():
    heard = {(n, t.id): t.heard for n in REELS for t in load(n).takes if t.heard}
    assert heard == {("terms", "09"): ("Reel is also premium.",)}


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
    stages = reel.stages(takes)
    gloss_reel.check(takes, stages)
    assert gloss_reel.still_opening(takes[0], stages[takes[0].id]) == reel.still  # held still until the first word


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
