"""Third Snore as data: the third voice is the man the frame hides, the cameras keep the couple in frame and hide him
until the pull back, the reel opens on a move (arm B), no music, and nothing follows his line but his snort."""

import importlib.util
import sys
from pathlib import Path

import pytest

from srstudio import stick_bed

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
HEAD_R = 92


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import third_snore_audio

        return third_snore_audio
    finally:
        sys.path.pop(0)


def framed(camera, point):
    (fx, fy), zoom, (tx, ty) = camera
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


def heads(data):
    dev = data.AT["dev"][0] + data.SCALE * 540, data.AT["dev"][1] + data.SCALE * 1000
    noor = data.AT["noor"][0] - data.SCALE * 540, data.AT["noor"][1] + data.SCALE * 1000
    return dev, noor


def test_no_music_and_the_opening_line_comes_at_once(data):
    assert data.SCRIPT.bed is None and data.SCRIPT.still == 0
    assert data.SCRIPT.takes[0].actor == "noor"


def test_the_last_line_is_his_and_only_his_snort_follows(data):
    last, snort = data.SCRIPT.takes[-2:]
    assert last.actor == "gary" and last.text == "You both snore." and snort.is_effect


def test_gary_speaks_once_and_only_after_the_pull_back(data):
    spoken = [t for t in data.SCRIPT.takes if t.actor == "gary"]
    assert len(spoken) == 1 and spoken[0].shot == "wide"


def test_every_voice_is_a_distinct_premade_one(data):
    assert len(set(data.SCRIPT.voices.values())) == 3


@pytest.mark.parametrize("name", ["CLOSE_FROM", "CLOSE_TO", "WIDE"])
def test_every_framing_keeps_both_faces_in_frame(data, name):
    camera = getattr(data, name)
    for head in heads(data):
        x, y = framed(camera, head)
        reach = data.SCALE * HEAD_R * camera[1]
        assert reach < x < 1080 - reach and 530 < y - reach and y + reach < 1500


def test_the_push_moves_in_and_the_pull_comes_back_out(data):
    assert data.CLOSE_FROM[1] < data.CLOSE_TO[1] and data.WIDE[1] < data.CLOSE_TO[1]


def test_the_mound_hides_his_hair_until_it_sinks_and_clears_his_mouth_after(data):
    top = 1510 - stick_bed.MOUND[1]
    hair = data.GARY_HEAD[1] - 132 * 0.8
    mouth = data.GARY_HEAD[1] + 44 * 0.8
    assert top < hair and top + data.SINK > mouth


def test_the_release_opens_arm_b_on_the_floor_with_five_tags():
    spec = importlib.util.spec_from_file_location("third_snore_post", EPISODES / "posts" / "third_snore.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    release = module.RELEASE
    assert release.tags.test == "sp-hook_motion" and release.tags.arm == "b"
    assert len(release.post.hashtags) == 5 and "#okayville" in release.post.hashtags
    assert release.post.title.endswith("?") and release.comedy.author == 16 and release.comedy.reviewer == 19
