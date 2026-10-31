"""The beat helpers every sketch script shares (:mod:`srstudio.scripting`): a beat that says a line, the parts of a long
line in two pills, a silent hold, the props that change through a sketch, and the checks a script's ``validate``
makes of its events."""

import pytest

from srstudio import scripting
from srstudio.sketch import Beat, Line, SketchError

LINES = (Line("bear", "Why does my password expire every month?"), Line("rabbit", "Security. It's a policy."))


def test_say_captions_the_whole_line():
    assert scripting.say(LINES, 1.0, "rabbit", 1, "half", "flat", "lean", "toast:0") == Beat(
        1.0, "rabbit", "Security. It's a policy.", "half", "flat", "lean", 1, 0, "toast:0"
    )


def test_first_and_part_split_a_long_line_on_its_words():
    assert scripting.first(LINES, 0.0, "bear", 0, "Why does my password", "e", "m", "a") == Beat(
        0.0, "bear", "Why does my password", "e", "m", "a", 0, 0, ""
    )
    assert scripting.part(LINES, 1.2, "bear", 0, 4, "expire every month?", "e", "m", "a", "x") == Beat(
        1.2, "bear", "expire every month?", "e", "m", "a", 0, 4, "x"
    )


def test_a_part_may_sit_in_the_middle_of_a_line():
    assert scripting.part(LINES, 1.0, "bear", 0, 2, "my password", "e", "m", "a").word == 2


@pytest.mark.parametrize(
    ("word", "caption"),
    [(3, "expire every month?"), (4, "expire every month"), (4, "xpire every month?"), (4, "expire every month? Now")],
)
def test_a_part_must_be_the_words_of_the_line_from_its_word(word, caption):
    with pytest.raises(SketchError, match="is not line 0 from word"):
        scripting.part(LINES, 0.0, "bear", 0, word, caption, "e", "m", "a")


@pytest.mark.parametrize(
    "caption", ["Why does my pass", "does my password", "Why does my password expire every month? Now"]
)
def test_first_must_be_the_opening_words_of_the_line(caption):
    with pytest.raises(SketchError, match="does not start line 0"):
        scripting.first(LINES, 0.0, "bear", 0, caption, "e", "m", "a")


def test_hold_is_a_silent_beat():
    assert scripting.hold(2.0, "bear", "", "e", "m", "a", "hangup") == Beat(
        2.0, "bear", "", "e", "m", "a", None, None, "hangup"
    )


def test_a_script_binds_its_lines():
    s = scripting.Script(LINES)
    assert s.say(0.0, "bear", 0, "e", "m", "a") == scripting.say(LINES, 0.0, "bear", 0, "e", "m", "a")
    assert s.first(0.0, "bear", 0, "Why", "e", "m", "a").caption == "Why"
    assert s.part(0.0, "bear", 0, 1, "does my password expire every month?", "e", "m", "a").word == 1
    assert s.hold(1.0, "bear", "x", "e", "m", "a") == scripting.hold(1.0, "bear", "x", "e", "m", "a")


BEATS = (
    Beat(0.0, "bear", "a", "e", "m", "a", 0, 0, "board:Hello"),
    Beat(1.0, "rabbit", "b", "e", "m", "a", 1, 0, "toast:0"),
    Beat(2.0, "bear", "c", "e", "m", "a", None, None, "board:Bye"),
    Beat(3.0, "rabbit", "", "e", "m", "a", None, None, "hangup"),
)


def test_changes_start_from_the_first_value_and_follow_the_events():
    assert scripting.changes(BEATS, "board", "Start") == [(0.0, "Start"), (0.0, "Hello"), (2.0, "Bye")]


def test_spans_clip_each_change_until_the_next():
    changes = [(0.0, "A"), (2.0, "B"), (5.0, "C")]
    assert scripting.spans(changes, 1.0, 4.0) == [(1.0, 2.0, "A"), (2.0, 4.0, "B")]
    assert scripting.spans(changes, 5.0, 6.0) == [(5.0, 6.0, "C")]


def test_off_screen_lists_the_events_outside_their_owner_shots():
    assert scripting.off_screen(BEATS, "board", "bear") == []
    assert scripting.off_screen(BEATS, "toast", "bear") == [(1.0, "0")]


def test_exactly_once_refuses_none_or_two():
    scripting.exactly_once(BEATS, "hangup", "the call ends exactly once")
    with pytest.raises(SketchError, match="the board changes exactly once"):
        scripting.exactly_once(BEATS, "board", "the board changes exactly once")
    with pytest.raises(SketchError, match="no zoom"):
        scripting.exactly_once(BEATS, "zoom", "no zoom")


def test_only_events_refuses_an_unknown_kind():
    scripting.only_events(BEATS, {"board", "toast", "hangup"})
    with pytest.raises(SketchError, match=r"unknown events \['hangup', 'toast'\]"):
        scripting.only_events(BEATS, {"board"})


def test_a_script_is_timed_from_its_words_and_its_turns():
    lines = (Line("a", "one two three four"), Line("b", "five six"))
    assert scripting.spoken_seconds(lines) == pytest.approx(0.27 * 6 + 0.1 * 2 + 0.3)


def test_no_lines_take_no_time_and_one_line_has_no_gap():
    assert scripting.spoken_seconds(()) == 0.0
    assert scripting.spoken_seconds((Line("a", "one"),)) == pytest.approx(0.37)


def _beats(*events):
    return [Beat(float(i), "bear", "", "h", "f", "d", event=e) for i, e in enumerate(events)]


def test_at_is_when_an_event_comes_and_refuses_one_that_never_does():
    beats = _beats("door", "", "door")
    assert scripting.at(beats, "door") == 0.0
    with pytest.raises(SketchError, match="no gulp event"):
        scripting.at(beats, "gulp")


def test_times_are_the_moments_foley_lands_on():
    assert scripting.times(_beats("step", "door", "step:left"), "step") == [0.0, 2.0]


def test_every_spaces_a_bed_of_sounds_and_stops_before_the_end():
    assert scripting.every(1.0, 2.0, 0.4) == [1.0, 1.4, 1.8]
    assert scripting.every(2.0, 2.0, 0.4) == []


@pytest.mark.parametrize("step", [0.0, -1.0])
def test_every_refuses_a_step_that_never_ends(step):
    with pytest.raises(SketchError, match="positive"):
        scripting.every(0.0, 1.0, step)


def test_speaks_by_holds_the_first_line_to_the_opening():
    spoken = [Beat(0.4, "bear", "Hi.", "h", "f", "d", line=0), Beat(1.0, "bear", "Yes.", "h", "f", "d", line=1)]
    scripting.speaks_by(spoken, 0.5)
    with pytest.raises(SketchError, match=r"first line starts at 0\.40 s, after 0\.30 s"):
        scripting.speaks_by(spoken, 0.3)
    with pytest.raises(SketchError, match="no line is spoken"):
        scripting.speaks_by(_beats("door"), 0.5)
