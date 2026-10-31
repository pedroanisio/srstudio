"""More Tired as data: the reel pushes in from its first frame (arm B), both fall asleep before anyone goes up, each
keeps one eye on the other, and his eye shutting is the last thing that happens."""

import importlib.util
import sys
from pathlib import Path

import pytest

from srstudio import stick_home

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import more_tired_audio

        return more_tired_audio
    finally:
        sys.path.pop(0)


def test_no_music_and_the_first_frame_holds_under_half_a_second(data):
    assert data.SCRIPT.bed is None and 0.4 <= data.SCRIPT.still < 0.5


def test_she_has_the_last_word_and_it_is_his(data):
    spoken = [t for t in data.SCRIPT.takes if not t.is_effect]
    assert spoken[-1].actor == "noor" and spoken[-1].text == "You're resting loudly."
    assert "resting loudly" in spoken[5].text and spoken[5].actor == "dev"
    assert data.SCRIPT.takes[-1] is spoken[-1]


def test_her_eye_opens_before_his_and_both_look_at_the_other(data):
    noor, dev = data.PARTS["noor"]["12"], data.PARTS["dev"]["12"]
    assert noor[-1][2].eyes == dev[-1][2].eyes == "peek"
    assert noor[-1][0] < dev[-1][0]
    assert noor[-1][2].look == dev[-1][2].look == data.ACROSS


def test_the_fridge_opens_before_the_reach_and_shuts_inside_the_hold(data):
    assert data.FRIDGE_OPENS < data.REACHES < data.TAKES_KEYS < data.FRIDGE_SHUTS
    assert data.FRIDGE_SHUTS < next(t.hold for t in data.SCRIPT.takes if t.id == "06")


def test_his_reach_is_the_hand_without_the_mug(data):
    assert data.POSES["reach"].hands[1] == data.POSES["hold"].hands[1]


def test_the_keys_lie_inside_the_open_fridge(data):
    x, y, w, h = stick_home.FRIDGE
    assert x < data.KEYS_AT[0] < x + w and y < data.KEYS_AT[1] < y + h


def test_the_camera_leaves_the_safe_out_of_frame(data):
    (fx, _fy), zoom, (tx, _ty) = data.CAMERA
    sx, _sy, sw, _sh = stick_home.SAFE
    assert tx + (sx + sw - fx) * zoom < 0


def test_every_voice_is_a_distinct_premade_one(data):
    assert len(set(data.SCRIPT.voices.values())) == 2


def test_the_release_is_arm_b_on_the_floor_with_five_tags():
    spec = importlib.util.spec_from_file_location("tired_post", EPISODES / "posts" / "more_tired.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    release = module.RELEASE
    assert release.tags.test == "sp-hook_motion" and release.tags.arm == "b"
    assert len(release.post.hashtags) == 5 and "#okayville" in release.post.hashtags
    assert release.post.title.endswith("?") and release.comedy.author == 15 and release.comedy.reviewer == 18
