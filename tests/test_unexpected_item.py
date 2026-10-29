"""Unexpected Item (Stick 04) as data: the script checks, the voices, the screens the kiosk can show for every take,
and the button that calls back the kiosk's first line."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_shop

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import unexpected_item_audio

        return unexpected_item_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_with_three_distinct_voices_and_a_bed(data):
    script = data.SCRIPT
    script.check()
    assert len({v.id for v in script.voices.values()}) == 3
    assert script.bed is not None and script.bed.bpm == 120
    assert sum(t.hold for t in script.takes) < 9  # holds only where a beat lands


def test_every_take_has_screens_the_kiosk_draws(data):
    assert set(data.SCREENS) == {t.id for t in data.SCRIPT.takes}
    assert set(data.ALARM) <= set(data.SCREENS)
    for screens in data.SCREENS.values():
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="24", duration=3.0, background="#d9d2c4")
        cv = Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))
        stick_shop.kiosk(cv, cv.comp, screens, 3.0)


def test_the_award_shows_dev_in_the_apron_and_the_button_calls_back_the_first_line(data):
    award = data.SCREENS["13"][0]
    assert award.tone == "award" and award.face == data.DEV_HIRED and data.DEV_HIRED.apron == data.CLERK.apron
    takes = data.SCRIPT.takes
    assert takes[0].text == takes[-1].text == data.PLACE
    assert (takes[0].actor, takes[-1].actor) == ("kiosk", "dev")
    assert takes[-2].text == data.UNEXPECTED and takes[-3].text == "Do I get paid?"
    for look in (data.DEV, data.DEV_HIRED, data.CLERK, data.CUSTOMER):
        stick.check_look(look)
