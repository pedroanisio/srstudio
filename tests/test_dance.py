"""Dance moves on canonical joints: the typed model, its semantic checks, and pure sampling on a beat grid."""

import math
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import dance
from srstudio.dance import (
    Contact,
    DanceError,
    DanceFrame,
    Entry,
    Move,
    MoveError,
    Pattern,
    Routine,
    RoutineError,
    frames,
    sample,
    wave,
)
from srstudio.errors import SrstudioError
from srstudio.music import Groove
from support.authoring_docs import fences

GRID = Groove(120)  # half a second a beat: beat positions read as plain numbers


def bob(**changes):
    move = Move("test-bob", "either", (Pattern("chest.front_back", 0.2, snap=0.25),), contacts=())
    return replace(move, **changes)


def standing(**changes):
    move = Move(
        "test-step",
        "feet",
        (Pattern("root.right", 0.3, cycles=0.5), Pattern("left_lower_leg.stretch", -0.2, cycles=0.5)),
        loop_beats=2,
        contacts=(Contact("left_foot", 0, 2), Contact("right_foot", 0, 1)),
    )
    return replace(move, **changes)


# --- the canonical skeleton ------------------------------------------------------------------------------------------


def test_the_canonical_skeleton_has_the_mannequins_55_joints():
    assert len(dance.JOINTS) == 55
    assert dance.JOINTS["hips"] == ("front_back", "left_right", "twist_left_right")
    assert dance.JOINTS["left_index_proximal"] == ("stretched", "spread")
    assert dance.JOINTS["right_little_distal"] == ("stretched",)
    assert dance.JOINTS["jaw"] == ("close", "left_right")
    assert {"root.right", "root.up", "root.forward"} <= dance.TARGETS
    assert "hips.up" not in dance.TARGETS  # hips translation is the root's, in head radii


def test_every_joint_belongs_to_one_chain():
    chains = [dance.chain(f"{joint}.{dofs[0]}") for joint, dofs in dance.JOINTS.items()]
    assert set(chains) == set(dance.CHAINS) - {"root"}
    assert dance.chain("root.up") == "root"
    assert dance.chain("left_thumb_distal.stretched") == "left_arm"
    assert dance.chain("right_toes.up_down") == "right_leg"
    assert dance.chain("jaw.close") == "head"
    with pytest.raises(MoveError):
        dance.chain("tail.wag")


def test_mirroring_swaps_sides_and_negates_lateral_dofs():
    assert dance.mirrored("left_upper_arm.down_up", 0.5) == ("right_upper_arm.down_up", 0.5)
    assert dance.mirrored("right_foot.roll_in_out", 0.1) == ("left_foot.roll_in_out", 0.1)
    assert dance.mirrored("root.right", 0.3) == ("root.right", -0.3)
    assert dance.mirrored("head.turn_left_right", 0.2) == ("head.turn_left_right", -0.2)
    assert dance.mirrored("spine.twist_left_right", 0.2) == ("spine.twist_left_right", -0.2)
    assert dance.mirrored("neck.tilt_left_right", 0.2) == ("neck.tilt_left_right", -0.2)
    assert dance.mirrored("jaw.left_right", 0.2) == ("jaw.left_right", -0.2)
    assert dance.mirrored("chest.front_back", 0.2) == ("chest.front_back", 0.2)


# --- the waveform -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["sine", "hold"])
def test_a_wave_hits_at_zero_and_reaches_the_far_extreme_after_the_slow_stroke(kind):
    assert wave(kind, 0.25, 0.0) == pytest.approx(1)
    assert wave(kind, 0.25, 0.9999999) == pytest.approx(1)
    assert min(wave(kind, 0.25, k / 400) for k in range(400)) == pytest.approx(-1)


def test_the_sine_snaps_onto_the_hit_in_its_snap_fraction():
    # the far extreme sits one snap before the hit: the stroke onto the hit takes the snap fraction
    assert wave("sine", 0.27, 0.73) == pytest.approx(-1)
    assert wave("sine", 0.5, 0.25) == pytest.approx(math.cos(math.pi / 2))
    assert wave("sine", 0.5, 0.5) == pytest.approx(-1)


def test_the_hold_rests_at_each_extreme_between_its_strokes():
    assert wave("hold", 0.125, 0.2) == 1
    assert wave("hold", 0.125, 0.5) == pytest.approx(-1)
    assert wave("hold", 0.125, 0.7) == -1
    assert wave("hold", 0.125, 0.4375) == pytest.approx(0)


def test_a_snap_of_one_half_makes_the_hold_a_sine():
    for k in range(20):
        assert wave("hold", 0.5, k / 20) == pytest.approx(wave("sine", 0.5, k / 20))


@pytest.mark.parametrize(("kind", "snap", "u"), [("saw", 0.3, 0.1), ("sine", 0.0, 0.1), ("hold", 0.6, 0.1)])
def test_an_unknown_waveform_or_snap_is_refused(kind, snap, u):
    with pytest.raises(MoveError):
        wave(kind, snap, u)


# --- patterns and moves -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"target": "tail.wag"},
        {"target": "hips.up"},
        {"amplitude": math.nan},
        {"amplitude": True},
        {"amplitude": 4.0},  # a rotation of more than half a turn
        {"amplitude": 0.0},  # moves nothing and holds nothing
        {"cycles": 0},
        {"cycles": 17},
        {"per": "phrase"},
        {"phase": 65},
        {"phase": "1"},
        {"waveform": "square"},
        {"snap": 0.01},
        {"snap": 0.99},
        {"swing": 0.4},
        {"swing": 0.8},
        {"intensity": -0.1},
        {"intensity": 2.5},
        {"bias": math.inf},
        {"bias": 3.5},
    ],
)
def test_a_pattern_outside_its_bounds_is_refused(changes):
    with pytest.raises(MoveError) as caught:
        replace(Pattern("chest.front_back", 0.2), **changes)
    assert isinstance(caught.value, (DanceError, SrstudioError, ValueError))


def test_root_amplitudes_are_head_radii_with_their_own_bound():
    assert Pattern("root.up", 3.9).amplitude == 3.9
    with pytest.raises(MoveError):
        Pattern("root.up", 4.5)
    assert Pattern("chest.front_back", 0.0, bias=0.4).bias == 0.4


def test_a_hold_waveform_takes_at_most_half_a_cycle_per_stroke():
    assert Pattern("root.right", 0.2, waveform="hold", snap=0.5).snap == 0.5
    with pytest.raises(MoveError):
        Pattern("root.right", 0.2, waveform="hold", snap=0.6)


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "Bad Name"},
        {"name": "x" * 65},
        {"support": "wall"},
        {"patterns": ()},
        {"patterns": [Pattern("chest.front_back", 0.2)]},
        {"patterns": ("chest.front_back",)},
        {"patterns": (Pattern("chest.front_back", 0.2), Pattern("chest.front_back", 0.1))},
        {"patterns": (Pattern("root.up", 0.2),)},  # an either-support move leaves the root to the body
        {"patterns": (Pattern("left_foot.up_down", 0.2),)},
        {"loop_beats": 0},
        {"loop_beats": 65},
        {"patterns": (Pattern("chest.front_back", 0.2, cycles=0.75),)},  # three quarters of a cycle in the loop
        {"lags": (("tail", 0.1),)},
        {"lags": (("head", 1.5),)},
        {"lags": (("head", 0.1), ("head", 0.2))},
        {"lags": [("head", 0.1)]},
        {"contacts": (Contact("left_foot", 0, 1),)},  # only a standing move plants feet
        {"description": 7},
    ],
)
def test_a_move_that_breaks_its_contract_is_refused(changes):
    with pytest.raises(MoveError):
        bob(**changes)


def test_a_seated_move_has_no_legs():
    seated = Move("test-seat", "seat", (Pattern("root.up", -0.2),))
    assert seated.support == "seat"
    with pytest.raises(MoveError):
        Move("test-seat", "seat", (Pattern("right_upper_leg.front_back", 0.2),))
    with pytest.raises(MoveError):
        Move("test-seat", "seat", (Pattern("root.up", -0.2),), contacts=(Contact("left_foot", 0, 1),))


@pytest.mark.parametrize(
    "contacts",
    [
        (),
        (Contact("left_foot", 0, 1),),  # nothing holds the body for the second beat
        (Contact("left_foot", 0, 0.5), Contact("right_foot", 1, 2)),  # a gap in the middle of the loop
        (Contact("left_foot", 0, 2), Contact("left_foot", 1, 2)),  # one foot planted twice at once
        (Contact("left_foot", 0, 3), Contact("right_foot", 0, 1)),  # past the loop
        ("left_foot",),
    ],
)
def test_a_standing_move_keeps_a_foot_planted_at_every_moment(contacts):
    with pytest.raises(MoveError):
        standing(contacts=contacts)


@pytest.mark.parametrize(
    ("foot", "start", "end"),
    [("left_hand", 0, 1), ("left_foot", -1, 1), ("left_foot", 0, True), ("left_foot", 1, 1), ("left_foot", 2, 1)],
)
def test_a_contact_names_a_foot_and_a_span(foot, start, end):
    with pytest.raises(MoveError):
        Contact(foot, start, end)


def test_a_move_reads_its_lag_by_chain():
    move = bob(lags=(("head", 0.25),))
    assert move.lag("head") == 0.25
    assert move.lag("torso") == 0
    with pytest.raises(MoveError):
        move.lag("tail")


def test_a_move_mirrors_targets_lags_and_contacts():
    move = standing(lags=(("left_leg", 0.1),))
    flipped = move.mirror()
    assert [p.target for p in flipped.patterns] == ["root.right", "right_lower_leg.stretch"]
    assert flipped.patterns[0].amplitude == -0.3
    assert flipped.lag("right_leg") == 0.1 and flipped.lag("left_leg") == 0
    assert {(c.foot, c.end) for c in flipped.contacts} == {("right_foot", 2), ("left_foot", 1)}
    assert flipped.mirror() == move


# --- sampling a move --------------------------------------------------------------------------------------------------


def test_a_move_hits_on_the_beat_at_its_phase():
    move = bob()
    assert sample(move, GRID, 0.0).value("chest.front_back") == pytest.approx(0.2)
    assert sample(move, GRID, 1.0).value("chest.front_back") == pytest.approx(0.2)
    # the far extreme comes one snap (a quarter beat) before the next hit
    assert sample(move, GRID, 0.375).value("chest.front_back") == pytest.approx(-0.2)
    late = bob(patterns=(Pattern("chest.front_back", 0.2, snap=0.25, phase=0.5),))
    assert sample(late, GRID, 0.25).value("chest.front_back") == pytest.approx(0.2)


def test_the_groove_offset_moves_the_beat():
    shifted = Groove(120, offset=0.1)
    assert sample(bob(), shifted, 0.1).value("chest.front_back") == pytest.approx(0.2)
    early = sample(bob(), shifted, 0.05).value("chest.front_back")
    assert early == pytest.approx(sample(bob(), GRID, 0.45).value("chest.front_back"))


def test_a_lag_delays_its_chain_only():
    move = Move(
        "test-lag",
        "either",
        (Pattern("chest.front_back", 0.2), Pattern("head.nod_down_up", 0.1)),
        lags=(("head", 0.25),),
    )
    on = sample(move, GRID, 0.0)
    late = sample(move, GRID, 0.125)
    assert on.value("chest.front_back") == pytest.approx(0.2)
    assert late.value("head.nod_down_up") == pytest.approx(0.1)


def test_cycles_per_bar_count_bars_of_the_groove():
    move = bob(patterns=(Pattern("chest.front_back", 0.2, cycles=1, per="bar"),), loop_beats=4)
    assert sample(move, GRID, 0.0).value("chest.front_back") == pytest.approx(0.2)
    assert sample(move, GRID, 1.0).value("chest.front_back") == pytest.approx(-0.2)
    assert sample(move, GRID, 2.0).value("chest.front_back") == pytest.approx(0.2)
    waltz = Groove(120, beats_per_bar=3)
    assert sample(move, waltz, 1.5).value("chest.front_back") == pytest.approx(0.2)


def test_swing_lands_the_off_beat_late():
    straight = bob(patterns=(Pattern("chest.front_back", 0.2, cycles=2),))
    swung = bob(patterns=(Pattern("chest.front_back", 0.2, cycles=2, swing=2 / 3),))
    assert sample(straight, GRID, 0.25).value("chest.front_back") == pytest.approx(0.2)
    assert sample(swung, GRID, 0.25).value("chest.front_back") != pytest.approx(0.2)
    assert sample(swung, GRID, 1 / 3).value("chest.front_back") == pytest.approx(0.2)
    assert sample(swung, GRID, 0.5).value("chest.front_back") == pytest.approx(0.2)


def test_bias_holds_and_intensity_scales_the_swing_only():
    move = bob(patterns=(Pattern("right_upper_arm.down_up", 0.2, bias=1.0, intensity=0.5),))
    assert sample(move, GRID, 0.0).value("right_upper_arm.down_up") == pytest.approx(1.1)
    still = bob(patterns=(Pattern("right_upper_arm.down_up", 0.0, bias=1.0),))
    assert sample(still, GRID, 0.3).value("right_upper_arm.down_up") == 1.0


def test_a_frame_carries_root_planted_feet_and_support():
    frame = sample(standing(), GRID, 0.0)
    assert isinstance(frame, DanceFrame)
    assert frame.root == pytest.approx((0.3, 0.0, 0.0))
    assert frame.value("root.right") == pytest.approx(0.3)
    assert frame.planted == frozenset({"left_foot", "right_foot"})
    assert sample(standing(), GRID, 0.75).planted == frozenset({"left_foot"})
    assert frame.support == "feet" and frame.move == "test-step" and frame.expression is None
    assert frame.value("left_hand.in_out") == 0.0
    with pytest.raises(MoveError):
        frame.value("tail.wag")
    with pytest.raises(TypeError):
        frame.joints["chest.front_back"] = 1.0  # type: ignore[index]


def test_an_either_move_plants_both_feet_and_a_seated_one_none():
    assert sample(bob(), GRID, 0.2).planted == frozenset({"left_foot", "right_foot"})
    seated = Move("test-seat", "seat", (Pattern("root.up", -0.2),))
    assert sample(seated, GRID, 0.2).planted == frozenset()


def test_sampling_is_pure_and_deterministic():
    move = dance.moves()["seat-groove"]
    assert sample(move, GRID, 1.234) == sample(move, GRID, 1.234)


@pytest.mark.parametrize("t", [math.nan, math.inf, "1", True])
def test_a_time_that_is_not_a_finite_second_is_refused(t):
    with pytest.raises(DanceError):
        sample(bob(), GRID, t)


def test_only_moves_and_routines_are_sampled():
    with pytest.raises(DanceError):
        sample("seat-groove", GRID, 0.0)  # type: ignore[arg-type]
    with pytest.raises(DanceError):
        sample(bob(), 120, 0.0)  # type: ignore[arg-type]


# --- the frame generator ----------------------------------------------------------------------------------------------


def test_frames_are_sampled_at_fps_over_a_half_open_span():
    out = list(frames(bob(), GRID, 0.0, 1.0, 25))
    assert len(out) == 25
    assert out[1].time == pytest.approx(0.04)
    assert out[-1].time == pytest.approx(0.96)
    assert out[3] == sample(bob(), GRID, 3 / 25)


def test_frames_refuse_unbounded_work_before_sampling():
    with pytest.raises(DanceError):
        frames(bob(), GRID, 0.0, 100.0, 25, max_frames=100)
    with pytest.raises(DanceError):
        frames(bob(), GRID, 0.0, 1.0, 25, max_frames=dance.MAX_FRAMES + 1)
    with pytest.raises(DanceError):
        frames(bob(), GRID, 0.0, 1.0, 25, max_frames=True)


@pytest.mark.parametrize(
    ("start", "end", "fps"), [(1.0, 1.0, 25), (-1.0, 1.0, 25), (0, math.inf, 25), (0, 1, 0), (0, 1, 2.5)]
)
def test_frames_refuse_a_bad_span_or_rate(start, end, fps):
    with pytest.raises(DanceError):
        frames(bob(), GRID, start, end, fps)


# --- routines ---------------------------------------------------------------------------------------------------------


def routine(*entries, bars=16):
    return Routine(bars, entries)


def test_a_routine_plays_its_entries_with_expression_and_rest_between():
    groove_move = dance.moves()["seat-groove"]
    nod = dance.moves()["head-nod"]
    r = routine(Entry(0, 4, groove_move, expression="grin"), Entry(8, 12, nod, expression="eyes-closed"))
    first = sample(r, GRID, 0.0)
    assert first.move == "seat-groove" and first.expression == "grin"
    assert first.value("root.up") == pytest.approx(sample(groove_move, GRID, 0.0).value("root.up"))
    rest = sample(r, GRID, GRID.at(5))
    assert rest.move is None and rest.expression is None and rest.joints == {} and rest.root == (0.0, 0.0, 0.0)
    assert rest.support == "seat" and rest.planted == frozenset()
    assert sample(r, GRID, GRID.at(8, 1)).expression == "eyes-closed"
    assert sample(r, GRID, GRID.at(20)).move is None


def test_a_standing_routine_rests_on_both_feet():
    r = routine(Entry(0, 4, dance.moves()["step-touch"]))
    rest = sample(r, GRID, GRID.at(6))
    assert rest.support == "feet" and rest.planted == frozenset({"left_foot", "right_foot"})


def test_entry_intensity_scales_and_hold_adds_a_held_pose():
    move = bob()
    r = routine(Entry(0, 4, move, intensity=0.5, hold=(("head.turn_left_right", 0.3),)))
    frame = sample(r, GRID, 0.0)
    assert frame.value("chest.front_back") == pytest.approx(0.1)
    assert frame.value("head.turn_left_right") == pytest.approx(0.3)


def test_a_mirrored_entry_plays_the_move_mirrored():
    move = standing()
    r = routine(Entry(0, 4, move, mirror=True))
    frame = sample(r, GRID, 0.0)
    assert frame.value("root.right") == pytest.approx(-0.3)
    assert frame.value("right_lower_leg.stretch") == pytest.approx(-0.2)
    assert sample(r, GRID, 0.75).planted == frozenset({"right_foot"})


def test_a_transition_crossfades_move_parameters_from_the_entry_before():
    soft = bob(name="soft", patterns=(Pattern("chest.front_back", 0.1, snap=0.25),))
    hard = bob(name="hard", patterns=(Pattern("chest.front_back", 0.3, snap=0.25),))
    r = routine(Entry(0, 4, soft), Entry(4, 8, hard, transition_beats=4))
    at = GRID.at(4)
    assert sample(r, GRID, at).value("chest.front_back") == pytest.approx(0.1)
    assert sample(r, GRID, GRID.at(4, 2)).value("chest.front_back") == pytest.approx(0.2)
    assert sample(r, GRID, GRID.at(5)).value("chest.front_back") == pytest.approx(0.3)
    assert sample(r, GRID, GRID.at(4, 2)).move == "hard"


def test_a_transition_with_other_timing_blends_the_two_motions():
    on = bob(name="on", patterns=(Pattern("chest.front_back", 0.2, snap=0.25),))
    off = bob(
        name="off", patterns=(Pattern("chest.front_back", 0.2, snap=0.25, phase=0.5), Pattern("neck.nod_down_up", 0.1))
    )
    r = routine(Entry(0, 4, on), Entry(4, 8, off, transition_beats=4))
    t = GRID.at(4, 2)
    expected = 0.5 * sample(on, GRID, t).value("chest.front_back") + 0.5 * sample(off, GRID, t).value(
        "chest.front_back"
    )
    frame = sample(r, GRID, t)
    assert frame.value("chest.front_back") == pytest.approx(expected)
    assert frame.value("neck.nod_down_up") == pytest.approx(0.5 * sample(off, GRID, t).value("neck.nod_down_up"))


def test_a_pattern_only_the_outgoing_move_has_fades_out():
    both = bob(name="both", patterns=(Pattern("chest.front_back", 0.2), Pattern("neck.nod_down_up", 0.1)))
    one = bob(name="one", patterns=(Pattern("chest.front_back", 0.2),))
    r = routine(Entry(0, 4, both), Entry(4, 8, one, transition_beats=4))
    t = GRID.at(4, 2)
    assert sample(r, GRID, t).value("neck.nod_down_up") == pytest.approx(
        0.5 * sample(both, GRID, t).value("neck.nod_down_up")
    )
    assert "neck.nod_down_up" not in sample(r, GRID, GRID.at(5)).joints


def test_a_mirrored_entry_leaves_its_held_pose_as_written():
    r = routine(Entry(0, 4, bob(), mirror=True, hold=(("head.turn_left_right", 0.3),)))
    assert sample(r, GRID, 0.0).value("head.turn_left_right") == pytest.approx(0.3)


def test_a_transition_from_rest_fades_in_and_switches_feet_halfway():
    move = standing()
    r = routine(Entry(2, 6, move, transition_beats=2))
    assert sample(r, GRID, GRID.at(2)).value("root.right") == pytest.approx(0.0)
    assert sample(r, GRID, GRID.at(2, 0.75)).planted == frozenset({"left_foot", "right_foot"})
    assert sample(r, GRID, GRID.at(2, 1.25)).planted == frozenset({"left_foot"})
    assert sample(r, GRID, GRID.at(2, 2)).value("root.right") == pytest.approx(0.3)


def test_held_poses_crossfade_too():
    r = routine(
        Entry(0, 4, bob(), hold=(("head.turn_left_right", 0.4),)),
        Entry(4, 8, bob(), hold=(("head.turn_left_right", -0.4),), transition_beats=2),
    )
    assert sample(r, GRID, GRID.at(4, 1)).value("head.turn_left_right") == pytest.approx(0.0)


@pytest.mark.parametrize(
    "build",
    [
        lambda m: routine(Entry(0, 8, m), Entry(4, 12, m)),  # overlapping
        lambda m: routine(Entry(4, 8, m), Entry(0, 4, m)),  # out of order
        lambda m: routine(Entry(0, 20, m)),  # past the track
        lambda m: routine(Entry(4, 4, m)),
        lambda m: routine(Entry(-1, 4, m)),
        lambda m: routine(Entry(0, 1, m, transition_beats=5)),  # longer than the entry
        lambda m: routine(Entry(0, 4, m, transition_beats=-1)),
        lambda m: routine(Entry(0, 4, m, intensity=3)),
        lambda m: routine(Entry(0, 4, m, mirror=1)),
        lambda m: routine(Entry(0, 4, m, expression="Big Grin")),
        lambda m: routine(Entry(0, 4, m, hold=(("tail.wag", 0.1),))),
        lambda m: routine(Entry(0, 4, m, hold=[("head.turn_left_right", 0.1)])),
        lambda m: routine(Entry(0, 4, m, hold=("head.turn_left_right",))),
        lambda m: routine(Entry(0, 4, m, hold=(("head.turn_left_right", 9.0),))),
        lambda m: routine(Entry(0, 4, m, hold=(("head.turn_left_right", 0.1), ("head.turn_left_right", 0.2)))),
        lambda m: routine(Entry(0, 4, "seat-groove")),
        lambda m: routine(Entry(0.5, 4, m)),
        lambda m: routine(Entry(0, 4, m), bars=0),
        lambda m: Routine(16, [Entry(0, 4, m)]),
        lambda m: Routine(16, ()),
        lambda m: Routine(16, ("entry",)),
        lambda m: Routine(16, (Entry(0, 4, m),), beats_per_bar=0),
        lambda m: routine(Entry(0, 4, dance.moves()["seat-groove"]), Entry(4, 8, dance.moves()["step-touch"])),
    ],
)
def test_a_routine_that_does_not_fit_its_track_is_refused(build):
    with pytest.raises(RoutineError):
        build(bob())


def test_a_routine_samples_only_on_its_own_metre():
    r = routine(Entry(0, 4, bob()))
    with pytest.raises(RoutineError):
        sample(r, Groove(120, beats_per_bar=3), 0.0)


def test_a_routine_reports_its_support():
    assert routine(Entry(0, 4, bob())).support == "either"
    assert routine(Entry(0, 4, bob()), Entry(4, 8, standing())).support == "feet"
    assert routine(Entry(0, 4, dance.moves()["seat-groove"])).support == "seat"


def test_the_errors_share_one_base():
    assert issubclass(MoveError, DanceError) and issubclass(RoutineError, DanceError)
    assert issubclass(DanceError, SrstudioError) and issubclass(DanceError, ValueError)


def test_the_guides_recipes_run():
    guide = (Path(__file__).resolve().parents[1] / "docs" / "authoring-dance.md").read_text()
    recipes = [code for language, code in fences(guide) if language == "python"]
    assert len(recipes) == 2
    for code in recipes:
        exec(compile(code, "authoring-dance.md", "exec"), {})


def test_the_guides_move_parses():
    guide = (Path(__file__).resolve().parents[1] / "docs" / "authoring-dance.md").read_text()
    documents = [code for language, code in fences(guide) if language == "json"]
    assert list(dance.parse_moves(documents[0])) == ["chest-pop"]
