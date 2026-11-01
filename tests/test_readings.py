"""A value on screen that changes on cues, every reading held long enough to read."""

from __future__ import annotations

import pytest

from srstudio.readings import LEAST, Reading, ReadingError, climbing, held, shown_at


def test_each_reading_runs_from_its_cue_to_the_next() -> None:
    assert held(((0.0, "9%"), (2.0, "10%"), (4.0, "11%")), 6.0) == (
        Reading(0.0, 2.0, "9%"),
        Reading(2.0, 4.0, "10%"),
        Reading(4.0, 6.0, "11%"),
    )


def test_a_reading_too_brief_to_read_gives_way_to_the_next() -> None:
    out = held(((0.0, "98%"), (2.0, "99%"), (2.3, "100%")), 5.0)
    assert out == (Reading(0.0, 2.0, "98%"), Reading(2.0, 5.0, "100%"))


def test_a_last_reading_too_brief_keeps_the_one_before_it_up() -> None:
    assert held(((0.0, "$9"), (2.0, "$10"), (4.7, "$11")), 5.0) == (Reading(0.0, 2.0, "$9"), Reading(2.0, 5.0, "$10"))


def test_every_reading_clears_the_least_however_crowded_the_cues() -> None:
    cues = tuple((i * 0.2, str(i)) for i in range(40))
    out = held(cues, 8.0)
    assert all(r.end - r.start >= LEAST for r in out)
    assert out[0].start == 0.0 and out[-1].end == 8.0
    assert all(a.end == b.start for a, b in zip(out, out[1:], strict=False))


def test_the_same_text_twice_runs_as_one_reading() -> None:
    out = held(((0.0, "SENT"), (1.0, "SENT"), (2.0, "OK")), 3.0)
    assert out == (Reading(0.0, 2.0, "SENT"), Reading(2.0, 3.0, "OK"))


def test_the_window_clips_the_readings_to_one_shot() -> None:
    cues = ((0.0, "a"), (2.0, "b"), (4.0, "c"))
    assert held(cues, 6.0, within=(1.0, 3.0)) == (Reading(1.0, 2.0, "a"), Reading(2.0, 3.0, "b"))


def test_a_window_cutting_a_reading_short_never_leaves_it_too_brief() -> None:
    cues = ((0.0, "a"), (2.0, "b"), (4.0, "c"))
    out = held(cues, 6.0, within=(1.7, 3.8))
    assert out == (Reading(1.7, 3.8, "b"),)


def test_held_refuses_what_cannot_be_read() -> None:
    with pytest.raises(ReadingError, match="at least one"):
        held((), 3.0)
    with pytest.raises(ReadingError, match="in order"):
        held(((2.0, "a"), (1.0, "b")), 3.0)
    with pytest.raises(ReadingError, match="before the end"):
        held(((0.0, "a"), (3.0, "b")), 3.0)
    with pytest.raises(ReadingError, match="is blank"):
        held(((0.0, " "),), 3.0)
    with pytest.raises(ReadingError, match="a second"):
        held(((float("nan"), "a"),), 3.0)
    with pytest.raises(ReadingError, match="too short"):
        held(((0.0, "a"),), 0.5)
    with pytest.raises(ReadingError, match="least"):
        held(((0.0, "a"),), 3.0, least=0.0)
    with pytest.raises(ReadingError, match="too short"):
        held(((0.0, "a"),), 3.0, within=(1.0, 1.2))
    with pytest.raises(ReadingError, match="window"):
        held(((0.0, "a"),), 3.0, within=(2.0, 1.0))


def test_shown_at_reads_the_reading_standing_at_a_second() -> None:
    out = held(((0.0, "a"), (2.0, "b")), 4.0)
    assert shown_at(out, 1.9) == "a"
    assert shown_at(out, 2.0) == "b"
    assert shown_at(out, 4.0) is None
    assert shown_at(out, -1.0) is None


def test_climbing_lands_on_the_last_value_at_the_last_second() -> None:
    cues = climbing(9, 21, 0.0, 12.0, every=3.0)
    assert cues == ((0.0, 9), (3.0, 12), (6.0, 15), (9.0, 18), (12.0, 21))


def test_climbing_counts_down_as_well() -> None:
    assert climbing(10, 0, 0.0, 2.0, every=1.0) == ((0.0, 10), (1.0, 5), (2.0, 0))


def test_climbing_holds_a_value_that_would_not_change_a_whole_step() -> None:
    assert climbing(1, 2, 0.0, 4.0, every=1.0) == ((0.0, 1), (4.0, 2))


def test_climbing_refuses_a_step_nobody_could_read() -> None:
    with pytest.raises(ReadingError, match="every"):
        climbing(1, 9, 0.0, 5.0, every=0.5)
    with pytest.raises(ReadingError, match="runs from"):
        climbing(1, 9, 5.0, 2.0, every=1.0)
    with pytest.raises(ReadingError, match="whole"):
        climbing(1.5, 9, 0.0, 5.0, every=1.0)  # type: ignore[arg-type]
