"""Turn This Car as data: the reel holds its first frame (arm A), opens and closes on one mirror, ends on the kid's
word, and carries the hats and the rings through every car shot."""

import importlib.util
import sys
from pathlib import Path

import pytest

from srstudio import stick_roadtrip

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import turn_this_car_audio

        return turn_this_car_audio
    finally:
        sys.path.pop(0)


def test_no_music_and_the_first_frame_holds_under_half_a_second(data):
    assert data.SCRIPT.bed is None and 0.4 <= data.SCRIPT.still < 0.5


def test_the_reel_opens_and_closes_on_the_same_mirror(data):
    assert data.SCRIPT.takes[0].shot == "mirror" == data.SCRIPT.takes[-1].shot


def test_nothing_is_said_after_the_second_word(data):
    spoken = [t for t in data.SCRIPT.takes if not t.is_effect]
    assert [t.text for t in spoken if t.actor == "kid"] == ["Word.", "Word."]
    assert spoken[-1].actor == "kid" and data.SCRIPT.takes[-1].is_effect


def test_the_mirror_shows_the_eyes_and_never_the_mouth_that_would_have_to_speak(data):
    x, y, w, h = stick_roadtrip.MIRROR
    head_y = data.MIRROR_AT[1] + data.MIRROR_SCALE * 930
    assert y < head_y - 20 * data.MIRROR_SCALE < y + h  # the eyes
    assert head_y + 44 * data.MIRROR_SCALE > y + h  # the mouth


def test_the_last_frame_shows_the_face_of_the_first(data):
    assert data.IN_MIRROR["14"][-1][1] == data.IN_MIRROR["01"][0][1] == data.GLARE


def test_the_held_opening_keeps_the_first_face_until_the_hold_is_over(data):
    assert data.IN_MIRROR["01"][1][0] > data.SCRIPT.still


def test_every_voice_is_a_distinct_premade_one(data):
    assert len(set(data.SCRIPT.voices.values())) == 3


def test_everyone_keeps_a_hat_on(data):
    assert data.DAD.sunhat and data.MOM.sunhat and data.KID.sunhat


def test_the_three_clicks_stay_inside_their_holds(data):
    held = {t.id: t.hold for t in data.SCRIPT.takes}
    assert data.CLICKS[-1] + stick_roadtrip.CLICK_SHOWS < held["02"]
    assert len(data.CLICKS) == len(data.LAST_CLICKS) == 3


def test_the_engine_ticks_fit_the_pause(data):
    assert data.TICKS[-1] < dict((t.id, t.hold) for t in data.SCRIPT.takes)["12"]
    gaps = [b - a for a, b in zip(data.TICKS, data.TICKS[1:], strict=False)]
    assert gaps == sorted(gaps)


def test_the_release_is_arm_a_on_the_floor_with_five_tags():
    spec = importlib.util.spec_from_file_location("turn_post", EPISODES / "posts" / "turn_this_car.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    release = module.RELEASE
    assert release.tags.test == "sp-hook_motion" and release.tags.arm == "a"
    assert len(release.post.hashtags) == 5 and "#okayville" in release.post.hashtags
    assert release.post.title.endswith("?") and release.comedy.author == 15 and release.comedy.reviewer == 19
