"""It Autoplayed as data: the lines as decided, three real holds, the cut, the light's cues, the overlay, and the arm."""

import sys
from pathlib import Path

import pytest

from srstudio import releases, sketch, toon_rooms
from srstudio.scripting import at

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import it_autoplayed_data

        return it_autoplayed_data
    finally:
        sys.path.pop(0)


LINES = [
    ("mae", "Why did you gasp?"),
    ("bruno", "The door."),
    ("mae", "It's a door."),
    ("bruno", "Wow."),
    ("mae", "You gasped before the door."),
    ("bruno", "It was a tense door."),
    ("mae", "You've never seen this."),
    ("bruno", "I have an instinct for doors."),
    ("bruno", "You okay?"),
    ("mae", "Nothing's happened."),
    ("bruno", "Not yet."),
    ("bruno", "Relax. The dog's fine."),
    ("mae", "What dog?"),
    ("bruno", "There's going to be a dog."),
    ("mae", "We're on episode two, Bruno."),
    ("bruno", "It autoplayed."),
]


def test_the_lines_are_the_script_s(data):
    assert [(n.speaker, n.text) for n in data.LINES] == LINES


def test_the_sketch_is_valid_and_speaks_by_half_a_second(data):
    data.validate()


def test_a_sketch_without_the_sting_is_refused(data):
    beats = tuple(b for b in data.BEATS if b.event != "sting")
    broken = sketch.Sketch(data.SLUG, data.TITLE, data.SKETCH.speakers, data.LINES, beats, data.END, tail=0.15)
    with pytest.raises(sketch.SketchError):
        data.validate(broken)


def test_the_overlay_never_repeats_a_line(data):
    assert data.OVERLAY == "OUR SHOW: EPISODE 2"
    assert data.OVERLAY.lower() not in " ".join(n.text.lower() for n in data.LINES)


def test_the_holds_carry_no_caption(data):
    holds = [b for b in data.BEATS if b.event in ("pause", "hears", "light")]
    assert len(holds) == 3 and all(not b.caption for b in holds)


def test_the_light_plays_as_a_tv_and_stops_changing_when_she_pauses_it(data):
    cues = data.glow(data.BEATS)
    parsed = toon_rooms.parse_lights("lounge", {"tv": cues}, data.END)["tv"]
    pause, light = at(data.BEATS, "pause"), at(data.BEATS, "light")
    assert not [c for c in parsed if pause <= c.at < light]


def test_the_reel_is_lit_by_a_screen_on_our_side_and_the_sofa_keeps_the_marks(data):
    assert data.FAR_BLUR > 0
    assert data.MENU not in (data.TWO, data.MAE_C, data.BRUNO_C)


def test_the_release_is_the_send_test_s():
    release = releases.load(EPISODES / "posts")["it-autoplayed"]
    assert (release.tags.test, release.tags.arm) == ("sp-length", "natural")
    assert release.tags.also == (("sp-speakers", "a"),)
    assert release.tags.send_to == "your partner"
    assert release.tags.send_line == "It autoplayed."
    assert release.post.title.endswith("?")
    assert len(release.post.hashtags) <= 5 and "#okayville" in release.post.hashtags
