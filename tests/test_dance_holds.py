"""Foot holds (ADR 0219): when each foot was set down and lifted, read off a move's or a routine's contacts."""

from __future__ import annotations

import pytest

from srstudio import dance
from srstudio.music import Groove

GROOVE = Groove(120)  # half a second a beat, no offset
BEAT = GROOVE.beat


def _move(contacts: tuple[dance.Contact, ...], loop: float = 2.0) -> dance.Move:
    return dance.Move(
        "holds",
        "feet",
        (dance.Pattern("root.right", 0.4, 1, "beat", 0.0, "sine"),),
        loop_beats=loop,
        contacts=contacts,
    )


WALK = _move((dance.Contact("left_foot", 0.0, 1.0), dance.Contact("right_foot", 1.0, 2.0)))


def _at(source: dance.Move | dance.Routine, beat: float) -> dance.DanceFrame:
    return dance.sample(source, GROOVE, beat * BEAT)


def test_a_planted_foot_is_held_from_the_moment_its_contact_began() -> None:
    frame = _at(WALK, 4.5)
    hold = frame.holds["left_foot"]
    assert hold.landed.time == pytest.approx(4.0 * BEAT)
    assert hold.lifted is None and hold.weight == 1.0
    assert hold.landed.holds == {}  # a hold's frames carry no holds of their own


def test_a_foot_in_the_air_carries_its_last_contact_with_a_weight_easing_to_its_next_set_down() -> None:
    hold = _at(WALK, 4.5).holds["right_foot"]
    assert hold.landed.time == pytest.approx(3.0 * BEAT)
    assert hold.lifted is not None and hold.lifted.time == pytest.approx(4.0 * BEAT)
    assert hold.weight == pytest.approx(0.5)  # halfway between lift-off at 4 and set-down at 5, smoothstep
    assert _at(WALK, 4.0).holds["right_foot"].weight == pytest.approx(1.0)
    assert _at(WALK, 4.9).holds["right_foot"].weight < 0.05


def test_a_contact_across_the_loop_seam_began_in_the_previous_loop() -> None:
    wrap = _move((dance.Contact("left_foot", 1.5, 2.0), dance.Contact("left_foot", 0.0, 0.5),
                  dance.Contact("right_foot", 0.0, 2.0)))
    assert _at(wrap, 4.25).holds["left_foot"].landed.time == pytest.approx(3.5 * BEAT)


def test_a_foot_planted_through_the_whole_loop_is_held_from_the_loops_start() -> None:
    wrap = _move((dance.Contact("left_foot", 0.0, 1.0), dance.Contact("right_foot", 0.0, 2.0)))
    assert _at(wrap, 5.5).holds["right_foot"].landed.time == pytest.approx(4.0 * BEAT)


def test_only_a_standing_dance_holds_feet() -> None:
    seated = dance.Move("sit", "seat", (dance.Pattern("neck.turn_left_right", 0.1, 1, "beat", 0.0, "sine"),))
    either = dance.Move("nod", "either", (dance.Pattern("neck.turn_left_right", 0.1, 1, "beat", 0.0, "sine"),))
    assert _at(seated, 1.25).holds == {}
    assert _at(either, 1.25).holds == {}


def test_a_routine_holds_a_foot_planted_since_the_rest_before_its_first_entry() -> None:
    routine = dance.Routine(4, (dance.Entry(1, 3, WALK),))
    frame = _at(routine, 4.5)  # bar 1 starts at beat 4; the left foot has been down since the rest
    assert frame.holds["left_foot"].landed.time == pytest.approx(0.0)
    assert frame.holds["right_foot"].lifted is not None
    assert frame.holds["right_foot"].lifted.time == pytest.approx(4.0 * BEAT)


def test_holds_are_pure() -> None:
    assert _at(WALK, 6.3) == _at(WALK, 6.3)
