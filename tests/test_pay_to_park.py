"""Pay to Park (Ink 08) as data: the script checks with two distinct voices, the taped slot is held before anyone
speaks, the app escalates from a download to a rating, the childhood memory is refused after he gives it, location
is asked of a man standing at the meter, every screen and reading draws on its cues, and the tow lifts the car in the
tight shot and carries on across the cut to the wide one, held before the doodle thanks the meter."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_meter, shared_counter
from srstudio.canvas import Signature
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
INK_HUMAN = "iP95p4xoKVk53GoZ742B"  # Chris, the doodle's voice in the earlier Ink episodes
PER_WORD = 0.32  # a stand-in for the recorded pace, seconds per word


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import pay_to_park_audio

        return pay_to_park_audio
    finally:
        sys.path.pop(0)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def by_id(data):
    return {take.id: take for take in data.TAKES}


def voiced(take) -> Take:
    """The scripted take as a recorded one: its words said one after another, then its hold."""
    said = [] if take.is_effect else take.text.split()
    words = tuple(dict(text=w, start=k * PER_WORD, end=(k + 1) * PER_WORD) for k, w in enumerate(said))
    speech = len(said) * PER_WORD
    return Take(take.id, take.actor, take.shot, take.text, 0.0, speech + take.hold, speech_duration=speech, words=words)


def test_the_script_checks_with_two_voices_and_the_doodle_keeps_his(data):
    script = data.script()
    script.check()
    assert set(script.voices) == {"human", "meter"} and script.voices["human"].id == INK_HUMAN
    assert len({v.id for v in script.voices.values()}) == 2
    assert {take.shot for take in data.TAKES} == set(data.SHOTS)


def test_it_opens_on_the_taped_slot_held_before_anyone_speaks(data):
    first, second = data.TAKES[:2]
    assert first.is_effect and first.shot == "kerb" and data.DISPLAYS["01"][0][1] == ink_meter.TAPE_TEXT
    assert (second.actor, second.shot, second.text) == ("meter", "meter", "Coins? How retro.")


def test_the_opening_pushes_in_on_the_taped_slot_and_keeps_it_in_frame(data):
    sx, sy = data.taped_slot()
    assert data.PUSH_IN == pytest.approx(1.15)
    assert 200 <= sx <= 1080 - 200 and 200 <= sy <= 1080 - 200  # the fixed point stays put, well inside the frame
    head_left = ink_meter.KERB_VIEW[1] + (ink_meter.METER_X - 124) * ink_meter.KERB_VIEW[0]
    assert sx - (sx - head_left) * data.PUSH_IN >= 0  # the meter's head is still whole at the end of the push


def test_the_app_escalates_and_refuses_the_memory_he_gives(data):
    takes = list(data.TAKES)
    apps = [take for take in takes if take.shot == "app"]
    assert [take.id for take in apps] == list(data.SCREENS)
    assert [data.SCREENS[take.id]["title"] for take in apps][0] == data.APP and "stars" in data.SCREENS[apps[-1].id]
    ask, answer, refusal = (next(k for k, t in enumerate(takes) if t.id == i) for i in ("05", "06", "07"))
    assert "childhood memory" in takes[ask].text and ask < answer < refusal
    assert (takes[answer].actor, takes[answer].shot) == ("human", "doodle")
    (memory,) = [r for r in data.SCREENS["07"]["rows"] if r.taken is not None]
    assert memory.text == data.SCREENS["05"]["rows"][-1].text and takes[refusal].text.startswith("That memory")


def test_location_is_asked_of_a_man_standing_at_the_meter(data):
    takes = list(data.TAKES)
    k = next(k for k, t in enumerate(takes) if "location" in t.text.lower())
    reply = takes[k + 1]
    assert (reply.actor, reply.shot, reply.text) == ("human", "kerb", "I'm right in front of you.")


def test_every_cue_is_a_word_of_its_line(data):
    takes = by_id(data)

    def cues(k):
        screen = data.SCREENS.get(k, {})
        for r in screen.get("rows", ()):
            yield from (r.at, r.tick, r.taken)
        yield screen.get("stars")
        yield from (at for at, _ in data.DISPLAYS.get(k, ()))

    for k in takes:
        said = {data.word(w) for w in takes[k].text.split()}
        for at in cues(k):
            assert not isinstance(at, str) or at in said, (k, at)


def test_a_cue_resolves_to_its_word_or_refuses_one_that_was_not_said(data):
    words = voiced(by_id(data)["05"]).words
    assert data.cue(words, "symbol") == pytest.approx(6 * PER_WORD) and data.cue(words, 0.4) == 0.4
    with pytest.raises(ValueError, match="not a word"):
        data.cue(words, "biscuit")


def test_every_screen_and_every_reading_draws_on_its_cues(data):
    takes = by_id(data)
    for k in data.SCREENS:
        cv = canvas()
        ink_meter.app_screen(cv, cv.comp, voiced(takes[k]), **data.screen(voiced(takes[k])))
    assert {k for k, t in takes.items() if t.shot in ("kerb", "meter", "tow-tight", "tow-wide")} == data.DISPLAYS.keys()
    for k in data.DISPLAYS:
        cv = canvas()
        ink_meter.meter(cv, cv.comp, voiced(takes[k]), 500, 200, display=data.readings(voiced(takes[k])))


def test_the_tow_lifts_in_the_tight_shot_and_carries_on_across_the_cut_into_a_held_wide(data):
    takes = list(data.TAKES)
    k = next(k for k, t in enumerate(takes) if t.shot == "tow-tight")
    tight, wide = takes[k], takes[k + 1]
    assert tight.text == "Session started!" and wide.shot == "tow-wide" and wide.is_effect
    assert data.TOW_AFTER + ink_meter.LIFT_SECONDS + 0.2 <= tight.hold  # the nose is up before the cut
    recorded = voiced(tight)
    tow, carried = data.tows(recorded.speech_duration, recorded.duration)
    assert 0 < tow < recorded.duration and carried < 0 and carried == pytest.approx(tow - recorded.duration)
    assert wide.hold >= 1.2  # the empty kerb, held before he speaks


def test_the_hold_music_plays_through_the_ordeal_and_stops_dead_when_the_car_goes(data):
    bed = data.script().bed
    assert bed is not None and bed.bpm == 120 and bed.gain_db == -20.0
    takes = list(data.TAKES)
    (k,) = [k for k, t in enumerate(takes) if t.id == data.CUT_AT]
    assert takes[k].shot == "tow-wide" and takes[k - 1].shot == "tow-tight"  # the cut is where the car goes
    assert [t.actor for t in takes[k + 1 :]] == ["human"]  # in the silence, only his line


def test_it_ends_on_the_doodle_thanking_the_meter(data):
    last = data.TAKES[-1]
    assert (last.actor, last.shot, last.text) == ("human", "doodle", "Thank you.") and last.hold >= 1.2


def test_the_release_declares_the_cover_and_the_doodle_recurs():
    sys.path.insert(0, str(EPISODES))
    try:
        from posts.pay_to_park import RELEASE
    finally:
        sys.path.pop(0)
    assert "ep.hide_on_cover(" in (EPISODES / "pay_to_park.py").read_text()
    assert RELEASE.cover and RELEASE.tags.recurring == ("doodle",)
    assert (RELEASE.tags.territory, RELEASE.post.thumbnail.kicker) == ("everyday-tech", "Ink 08")
