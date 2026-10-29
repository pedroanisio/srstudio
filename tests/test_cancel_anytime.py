"""Cancel Anytime (Stick 06) as data: the script checks, the voices, the rule of three that he meets, the hold
before the punchline, the sunrise that ends it and the sign that can letter its own fine print."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_gym

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import cancel_anytime_audio

        return cancel_anytime_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_with_two_distinct_voices_and_a_bed(data):
    script = data.SCRIPT
    script.check()
    assert script.takes[0].text.endswith("?") and len({v.id for v in script.voices.values()}) == 2
    assert script.bed is not None and script.bed.bpm == 120
    assert set(t.shot for t in script.takes) == set(data.SHOTS)


def test_he_meets_three_rules_then_the_fourth_breaks_the_pattern(data):
    said = [t.text for t in data.SCRIPT.takes]
    rules = ["Easy! In person.", "On a Tuesday.", "Before sunrise."]
    answers = ["I'm here. In person.", "It's Tuesday.", "It's still dark."]
    assert [said[said.index(r) + 1] for r in rules] == answers
    assert said.index("With a note from your trainer.") == said.index("It's still dark.") + 1


def test_the_punchline_holds_and_the_sun_rises_on_the_button(data):
    takes = data.SCRIPT.takes
    ask = next(t for t in takes if t.text == "Is there any other way?")
    assert ask.hold >= 1.2 and takes[takes.index(ask) + 1].text == "A death certificate."
    sunrise = next(t for t in takes if t.id == data.SUNRISE)
    assert sunrise.shot == "wide" and "Sunrise" in sunrise.text and takes[-1].shot == "sign"


def test_the_sign_letters_its_fine_print_and_the_looks_check(data):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=3.0, background="#d9d2c4")
    cv = Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))
    stick_gym.counter(cv, cv.comp, sign=data.SIGN, fine=data.FINE)
    assert data.FINE.startswith("*") and data.SIGN.endswith("*")
    for look in (data.THEO, data.BROOKE):
        stick.check_look(look)
