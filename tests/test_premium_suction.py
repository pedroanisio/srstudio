"""Premium Suction (Ink 06) as data: the script checks, the voices, a chat for the phone take, the vacuum's moves
and displays on vacuum takes, the map's trace and relabel on map takes, the hold before the reveal and the button."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_phone, ink_vacuum, shared_counter
from srstudio.canvas import Signature
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import premium_suction_audio

        return premium_suction_audio
    finally:
        sys.path.pop(0)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=5.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def test_the_script_checks_and_opens_on_a_question_with_two_distinct_voices(data):
    script = data.script()
    script.check()
    assert script.takes[0].text.endswith("?")
    assert len({v.id for v in script.voices.values()}) == 2


def test_every_phone_take_has_a_chat_and_every_chat_draws(data):
    phones = {take.id for take in data.TAKES if take.shot == "phone"}
    assert phones == data.SCREENS.keys()
    for state in data.SCREENS.values():
        cv = canvas()
        ink_phone.phone_shot(cv, cv.comp, data.CONTACT, **state)


def test_the_vacuum_and_map_beats_fall_on_their_takes_and_draw(data):
    by_id = {take.id: take for take in data.TAKES}
    assert all(by_id[k].shot.startswith("vacuum") for k in data.VACUUM)
    assert {k for k, t in by_id.items() if t.shot == "map"} == data.MAPS.keys()
    for k, kw in data.VACUUM.items():
        cv = canvas()
        t = Take(k, by_id[k].actor, by_id[k].shot, by_id[k].text, 0.0, 2.0)
        ink_vacuum.vacuum_shot(cv, cv.comp, t, close=t.shot == "vacuum-close", **kw)
    for k, kw in data.MAPS.items():
        cv = canvas()
        t = Take(k, by_id[k].actor, "map", by_id[k].text, 0.0, 2.5)
        kw = dict(kw)
        if kw.get("trace") == "take":
            kw["trace"] = (0.2, 2.2)
        ink_vacuum.floor_map(cv, cv.comp, t, **kw)


def test_the_reveal_holds_and_the_button_rolls_away(data):
    reveal = next(k for k, take in enumerate(data.TAKES) if take.shot == "phone")
    assert data.TAKES[reveal].hold >= 1.2 and data.TAKES[reveal].is_effect
    assert "map" in data.RENT.text and not data.RENT.mine
    after = data.TAKES[reveal + 1]
    assert after.shot == "map" and data.MAPS[after.id]["relabel"][:2] == ("CLOSET", "BEDROOM 2")
    last = data.TAKES[-1]
    assert last.actor == "vacuum" and "premium" in last.text and data.VACUUM[last.id]["state"] == "roll"
