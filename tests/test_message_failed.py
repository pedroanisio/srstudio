"""Message Failed (Ink 04) as data: the script checks, the voices, a chat for every phone take that the phone can
draw, and the router beats on router takes."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_phone, shared_counter
from srstudio.canvas import Signature

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import message_failed_audio

        return message_failed_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_and_opens_on_a_question_with_two_distinct_voices(data):
    script = data.script()
    script.check()
    assert script.takes[0].text.endswith("?")
    assert len({v.id for v in script.voices.values()}) == 2


def test_every_phone_take_has_a_chat_and_every_chat_draws(data):
    phones = {take.id: take for take in data.TAKES if take.shot == "phone"}
    assert phones.keys() == data.SCREENS.keys()
    for state in data.SCREENS.values():
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1080, fps="24", duration=5.0, background=MONO.background)
        cv = Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())
        state = dict(state)
        if state.get("typing") == "take":
            state["typing"] = (0.0, 2.0)
        ink_phone.phone_shot(cv, cv.comp, data.CONTACT, **state)


def test_the_router_beats_fall_on_router_takes(data):
    router = {take.id for take in data.TAKES if take.shot.startswith("router")}
    assert set(data.ROUTER_BEATS) <= router


def test_the_button_is_the_reply_the_human_refused(data):
    last = data.SCREENS[data.TAKES[-1].id]["bubbles"][-1]
    assert last.mine and last.text == "lol" and data.TAKES[-2].text == "No!"
