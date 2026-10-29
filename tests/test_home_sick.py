"""Home Sick (Ink 07) as data: the script checks, the voices, a chat for every phone take, the doorbell's verdicts
on doorbell takes, the face box's tags on lens takes, the hold before the reveal and the button."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_doorbell, ink_phone, shared_counter
from srstudio.canvas import Signature
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import home_sick_audio

        return home_sick_audio
    finally:
        sys.path.pop(0)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=5.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def by_id(data):
    return {take.id: take for take in data.TAKES}


def test_the_script_checks_and_opens_on_a_question_with_two_distinct_voices(data):
    script = data.script()
    script.check()
    assert script.takes[0].text.endswith("?") and script.takes[0].shot == "lens"
    assert len({v.id for v in script.voices.values()}) == 2


def test_every_phone_take_has_a_chat_and_every_chat_draws(data):
    phones = {take.id for take in data.TAKES if take.shot == "phone"}
    assert phones == data.SCREENS.keys()
    for state in data.SCREENS.values():
        cv = canvas()
        ink_phone.phone_shot(cv, cv.comp, **state)


def test_every_lens_take_tags_the_face_and_every_doorbell_beat_draws(data):
    takes = by_id(data)
    assert {k for k, t in takes.items() if t.shot == "lens"} == data.LENS.keys()
    assert all(takes[k].shot.startswith("doorbell") for k in data.DOORBELL)
    for k, tags in data.LENS.items():
        cv = canvas()
        t = Take(k, takes[k].actor, "lens", takes[k].text, 0.0, 1.5)
        ink_doorbell.doorbell_view(cv, cv.comp, t, tags=tags, clock=data.CLOCK, shades=True)
    for k, kw in data.DOORBELL.items():
        cv = canvas()
        t = Take(k, takes[k].actor, takes[k].shot, takes[k].text, 0.0, 1.5)
        ink_doorbell.doorstep(cv, cv.comp, t, close=t.shot == "doorbell-close", number=data.NUMBER, **kw)


def test_the_reveal_holds_and_the_face_is_retagged(data):
    takes = list(data.TAKES)
    reveal = next(k for k, take in enumerate(takes) if take.shot == "phone" and take.is_effect)
    assert takes[reveal].hold >= 1.2
    boss = data.SCREENS[takes[reveal + 1].id]["bubbles"][-1]
    assert "employee" in boss.text and not boss.mine
    reaction = takes[reveal + 2]
    assert reaction.shot == "lens" and data.LENS[reaction.id][-1][1] == "EMPLOYEE"


def test_the_door_opens_then_the_boss_has_the_last_word(data):
    takes = list(data.TAKES)
    welcome = takes[-2]
    assert welcome.actor == "doorbell" and data.DOORBELL[welcome.id]["mark"][0] == "allow"
    last = data.SCREENS[takes[-1].id]
    assert takes[-1].hold >= 1.2 and last["contact"] != data.NEIGHBORS
    assert [b.mine for b in last["bubbles"]] == [False, False]
