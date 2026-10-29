"""Not a Robot (Ink 03) as data: the script checks, the voices, and a screen state for every screen take that the
captcha parts can draw."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_captcha, shared_counter
from srstudio.canvas import Signature

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import not_a_robot_audio

        return not_a_robot_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_and_opens_on_a_question_with_three_distinct_voices(data):
    script = data.script()
    script.check()
    assert script.font == ("PatrickHand-Regular.ttf", "font-license.txt")
    assert script.takes[0].text.endswith("?")
    assert len({v.id for v in script.voices.values()}) == 3


def test_every_screen_take_has_a_screen_and_every_screen_draws(data):
    screens = {take.id for take in data.TAKES if take.shot == "screen"}
    assert screens == set(data.SCREENS)
    for state in data.SCREENS.values():
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1080, fps="24", duration=5.0, background=MONO.background)
        cv = Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())
        state = dict(state)
        if "label" in state:
            ink_captcha.checkbox(cv, cv.comp, state["label"], tick_at=1.0 if state.get("tick") else None)
        else:
            ink_captcha.captcha(cv, cv.comp, **state)


def test_the_button_calls_back_the_first_checkbox(data):
    assert data.SCREENS["02"]["label"] == "I'm not a robot" and data.SCREENS["14"]["label"] == "I'm not a router"
    assert data.TAKES[-1].id == "14"
