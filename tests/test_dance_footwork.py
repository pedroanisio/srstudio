"""Footwork as data (ADR 0205): strokes and a weight schedule on a move, followers in chains, and the floor pass that
solves a lifted foot's leg onto its goal. Every refusal is tested with a move that would otherwise read."""

import cmath
import json
import math
from functools import cache

import pytest

from srstudio import dance, dance_floor
from srstudio import skeleton as sk
from srstudio._dance_footwork import UNLOADED, Footwork, Steps, Stroke, WeightKey, bump, smoother
from srstudio._dance_model import MAX_CHAIN, WEIGHT, Follow, Move, MoveError, Pattern
from srstudio._dance_parse import DanceDataError, parse_moves
from srstudio._dance_sample import _response
from srstudio._floor_body import ball_of, sole
from srstudio.dance import Entry, Routine
from srstudio.dance_floor import FloorLimitError, Performance, perform, stance
from srstudio.music import Groove

GROOVE = Groove(120.0)
PRESETS = ("realistic", "cartoon", "stick")
NEW = ("two-step", "heel-rock", "twist-groove")
LEFT, RIGHT = "left_foot", "right_foot"
FPS = 50


def footwork(**kw):
    """A valid loop of 4 beats: the left foot lifts while the weight stands on the right, then the mirror."""
    return Footwork(
        kw.pop("strokes", (Stroke(LEFT, 0.5, 1.0, "lift", height=0.1), Stroke(RIGHT, 2.5, 1.0, "lift", height=0.1))),
        kw.pop("weight", (WeightKey(0.0, 0.98), WeightKey(1.75, 0.98), WeightKey(2.0, 0.02), WeightKey(3.75, 0.02))),
        **kw,
    )


def moved(**kw):
    kw.setdefault("support", "feet")
    kw.setdefault("patterns", (Pattern("root.up", -0.1, 1.0),))
    kw.setdefault("loop_beats", 4)
    kw.setdefault("footwork", footwork())
    return Move("probe", **kw)


@cache
def danced(name: str, preset: str) -> Performance:
    profile = sk.preset(preset)
    run = perform(Routine(2, (Entry(0, 2, dance.moves()[name]),)), profile, GROOVE, base=stance(profile))
    run.frames(FPS)
    return run


# --- the ease of a stroke --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ease", [smoother, bump])
def test_an_ease_starts_and_ends_at_rest_to_the_acceleration(ease):
    h = 1e-4
    for u in (0.0, 1.0):
        inner = u + h if u == 0.0 else u - h
        assert abs(ease(inner) - ease(u)) / h < 1e-2


def test_a_bump_peaks_at_one_half_way():
    assert bump(0.5) == pytest.approx(1.0)
    assert bump(0.0) == 0.0 and bump(1.0) == 0.0


# --- strokes ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"foot": "left_hand"}, "stroke foot"),
        ({"kind": "moonwalk"}, "stroke kind"),
        ({"kind": "step"}, "says its to"),
        ({"kind": "pivot"}, "says its turn"),
        ({"kind": "heel", "to": (0.1, 0.0)}, "only a step or a touch"),
        ({"kind": "heel", "turn": 0.1}, "does not turn"),
        ({"kind": "heel", "height": 0.1}, "no height"),
        ({"kind": "lift", "height": 0.1, "pitch": 0.1}, "no pitch"),
        ({"kind": "lift"}, "height"),
        ({"kind": "lift", "height": 0.9}, "height"),
        ({"kind": "lift", "height": 0.1, "beats": 0.01}, "beats"),
        ({"kind": "lift", "height": math.inf}, "height"),
        ({"kind": "lift", "height": float("nan")}, "height"),
    ],
)
def test_a_stroke_that_cannot_be_danced_is_refused(kw, match):
    args = {"foot": LEFT, "start": 0.0, "beats": 1.0, "kind": "lift"}
    with pytest.raises(MoveError, match=match):
        Stroke(**(args | kw))


def test_two_strokes_of_one_foot_at_once_are_refused():
    strokes = (Stroke(LEFT, 0.5, 1.0, "lift", height=0.1), Stroke(LEFT, 1.0, 1.0, "lift", height=0.1))
    with pytest.raises(MoveError, match="two strokes at once"):
        footwork(strokes=strokes)


def test_weight_keys_are_shares_of_the_weight_in_order():
    with pytest.raises(MoveError):
        WeightKey(0.0, 1.5)
    with pytest.raises(MoveError):
        footwork(weight=(WeightKey(2.0, 0.5), WeightKey(1.0, 0.5)))
    with pytest.raises(MoveError):
        footwork(weight=())


# --- on a loop -------------------------------------------------------------------------------------------------------


def test_a_foot_off_the_floor_carries_no_weight():
    """A lifted foot under the weight is the mistake that makes a dancer fall: the data refuses it."""
    with pytest.raises(MoveError, match="off the floor") as caught:
        moved(footwork=footwork(weight=(WeightKey(0.0, 0.5),)))
    assert caught.value.to_dict()["code"] == "dance.footwork.weight"


def test_a_stroke_past_the_loop_is_refused():
    with pytest.raises(MoveError, match="runs past the loop"):
        moved(footwork=footwork(strokes=(Stroke(LEFT, 3.5, 1.0, "lift", height=0.1),)))


def test_some_foot_is_flat_at_every_moment():
    """Both feet off the floor at once is a jump: the floor pass has no goal for it, so the data says so first."""
    strokes = (Stroke(LEFT, 0.5, 1.0, "lift", height=0.1), Stroke(RIGHT, 0.5, 1.0, "lift", height=0.1))
    with pytest.raises(MoveError, match="no foot is flat|off the floor"):
        moved(footwork=footwork(strokes=strokes, weight=(WeightKey(0.0, 0.0),)))


def test_footwork_stands_on_feet_and_derives_its_own_contacts():
    with pytest.raises(MoveError):
        moved(support="seat")
    with pytest.raises(MoveError):
        moved(contacts=(dance.Contact(LEFT, 0.0, 1.0),))
    move = moved()
    assert {c.foot for c in move.contacts} == {LEFT, RIGHT}
    left = [(c.start, c.end) for c in move.contacts if c.foot == LEFT]
    assert left == [(0.0, 0.5), (1.5, 4.0)]


def test_a_mirrored_footwork_turns_every_stroke_and_the_weight_round():
    move = moved()
    mirrored = move.mirror()
    assert mirrored.steps(1.0).right.up == pytest.approx(move.steps(1.0).left.up)
    assert mirrored.steps(1.0).left.up == 0.0
    assert mirrored.weight(1.0) == pytest.approx(-move.weight(1.0))
    assert {c.foot for c in mirrored.contacts} == {LEFT, RIGHT}


def test_the_feet_come_home_inward_of_the_base_when_asked():
    work = footwork(inward=0.09)
    at = work.at(0.0, 4)
    assert at.left.right == pytest.approx(0.09) and at.right.right == pytest.approx(-0.09)


# --- what a foot does ------------------------------------------------------------------------------------------------


def test_a_step_ends_where_it_says_and_stays_there_round_the_loop():
    work = Footwork(
        (Stroke(RIGHT, 0.5, 1.0, "step", to=(0.1, 0.05), height=0.1), Stroke(RIGHT, 2.5, 1.0, "return", height=0.1)),
        (WeightKey(0.0, 0.02),),
    )
    assert work.goal(RIGHT, 2.0, 4).right == pytest.approx(0.1)
    assert work.goal(RIGHT, 2.0, 4).forward == pytest.approx(0.05)
    assert work.goal(RIGHT, 3.75, 4).right == pytest.approx(0.0)
    assert work.goal(RIGHT, 1.0, 4).up == pytest.approx(0.1)


def test_a_touch_holds_on_the_ball_until_the_next_stroke():
    work = Footwork(
        (Stroke(LEFT, 0.5, 0.5, "touch", to=(0.1, 0.0), pitch=0.4), Stroke(LEFT, 2.0, 0.5, "return")),
        (WeightKey(0.0, 0.98),),
    )
    held = work.goal(LEFT, 1.5, 4)
    assert held.pitch == pytest.approx(0.4) and not held.planted and held.contacts == (False, True)
    assert work.goal(LEFT, 3.0, 4).planted


@pytest.mark.parametrize(
    "goal, contacts",
    [
        (dance.FootGoal(), (True, True)),
        (dance.FootGoal(pitch=0.3, planted=False), (False, True)),
        (dance.FootGoal(pitch=0.3, pivot="heel", planted=False), (True, False)),
        (dance.FootGoal(up=0.1, planted=False), (False, False)),
        (dance.FootGoal(right=0.1, planted=False), (False, False)),
    ],
)
def test_a_goal_says_which_of_heel_and_toe_hold_still(goal, contacts):
    assert goal.contacts == contacts


def test_the_weight_eases_round_the_loop():
    work = footwork()
    assert work.share(1.0, 4) == pytest.approx(0.98)
    assert work.share(3.0, 4) == pytest.approx(0.02)
    assert work.share(1.875, 4) == pytest.approx(0.5)
    assert work.share(3.875, 4) == pytest.approx(0.5)


def test_the_hips_arrive_a_settle_after_the_plan():
    move = moved(footwork=footwork(settle=0.1))
    plain = moved()
    assert move.steps(1.875).weight == pytest.approx(0.5)
    assert move.steps(1.975).settled == pytest.approx(0.5)
    assert move.weight(1.975) == pytest.approx(plain.weight(1.875))


def test_steps_mix_through_a_transition_with_the_pitch_changing_pivot_at_nothing():
    a = dance.FootGoal(pitch=0.4, planted=False)
    b = dance.FootGoal(pitch=0.4, pivot="heel", planted=False)
    half = a.mix(b, 0.5)
    assert half.pitch == pytest.approx(0.0)
    assert Steps(a, a, 1.0, 1.0, 1.0).mix(None, 1.0) == Steps(
        dance.FootGoal(planted=True), dance.FootGoal(planted=True), 0.5, 0.0, 0.5
    )


# --- followers in chains ---------------------------------------------------------------------------------------------


def chain_move(*follows, **kw):
    return moved(follows=follows, **kw)


def test_a_follower_may_read_the_weight_only_with_footwork():
    chain_move(Follow("hips.left_right", WEIGHT, 0.1))
    with pytest.raises(MoveError, match="weight"):
        Move("bare", "feet", (Pattern("root.up", -0.1, 1.0),), follows=(Follow("hips.left_right", WEIGHT, 0.1),))


def test_a_follower_may_read_another_follower():
    move = chain_move(Follow("hips.left_right", WEIGHT, 0.1), Follow("spine.left_right", "hips.left_right", 0.5))
    a = dance.sample(move, GROOVE, 1.0).joints["spine.left_right"]
    assert a != 0.0


def test_a_chain_that_closes_on_itself_is_refused():
    with pytest.raises(MoveError, match="loop|nothing moves") as caught:
        chain_move(
            Follow("spine.left_right", "chest.left_right", 0.5), Follow("chest.left_right", "spine.left_right", 0.5)
        )
    assert caught.value.to_dict()["code"] in ("dance.chain", "dance.follow", None)


def test_a_chain_past_its_depth_is_refused_by_ordinary_code():
    names = ["hips.left_right", "spine.left_right", "chest.left_right", "upper_chest.left_right",
             "neck.tilt_left_right", "head.tilt_left_right", "hips.twist_left_right", "spine.twist_left_right",
             "chest.twist_left_right", "upper_chest.twist_left_right"]  # fmt: skip
    links = [Follow(names[0], WEIGHT, 0.1)]
    links += [Follow(b, a, 0.5) for a, b in zip(names, names[1:], strict=False)]
    assert len(links) > MAX_CHAIN
    with pytest.raises(MoveError, match="chain") as caught:
        chain_move(*links)
    assert caught.value.to_dict()["code"] == "dance.chain"


def test_a_follower_of_one_link_reads_as_it_did_before_chains():
    from srstudio._dance_model import spring

    gain, lag, taps = _response((Follow("spine.left_right", "root.right", 0.5, 0.1, 3.0, 0.6),))
    assert gain == 0.5 and lag == 0.1
    assert taps == spring(3.0, 0.6)


def test_a_chained_response_is_a_bounded_impulse_that_sums_to_one():
    links = (
        Follow("spine.left_right", "root.right", 0.5, 0.1, 3.0, 0.6),
        Follow("chest.left_right", "spine.left_right", 2.0, 0.2, 2.0, 0.45),
    )
    gain, lag, taps = _response(links)
    assert gain == pytest.approx(1.0) and lag == pytest.approx(0.3)
    assert sum(w for _, w in taps) == pytest.approx(1.0)
    assert len(taps) <= 96


def test_each_link_of_a_chain_runs_later_than_the_one_before():
    """On the loop's first harmonic; a link's gain may turn its sign, so the phases are read modulo half a cycle."""
    move = dance.moves()["two-step"]
    chain = ("hips.left_right", "spine.left_right", "chest.left_right", "upper_chest.left_right")
    turn = 2j * cmath.pi / 400
    phase = []
    for target in chain:
        values = [dance.sample(move, GROOVE, i / 100).joints[target] for i in range(400)]
        phase.append(cmath.phase(sum(v * cmath.exp(-turn * i) for i, v in enumerate(values))))
    late = [(a - b) % math.pi for a, b in zip(phase, phase[1:], strict=False)]
    assert all(0 < v < math.pi / 2 for v in late), late


# --- the document ----------------------------------------------------------------------------------------------------


def document(schema="srstudio.dance-moves/1.2.0", **move):
    entry = {
        "name": "probe",
        "description": "a probe",
        "support": "feet",
        "loop_beats": 4,
        "patterns": [
            {
                "target": "root.up",
                "amplitude": -0.1,
                "cycles": 1,
                "per": "beat",
                "phase": 0,
                "waveform": "sine",
                "snap": 0.5,
            }
        ],
        "footwork": {
            "strokes": [{"foot": LEFT, "from": 0.5, "beats": 1, "kind": "lift", "height": 0.1}],
            "weight": [{"beat": 0, "right": 0.98}],
            "inward": 0.05,
            "settle": 0.1,
        },
    }
    return json.dumps({"schema": schema, "moves": [entry | move]})


def test_a_1_2_document_reads_footwork():
    move = parse_moves(document())["probe"]
    assert move.footwork.inward == 0.05 and move.footwork.settle == 0.1
    assert move.footwork.strokes[0].kind == "lift"


def test_a_1_1_document_cannot_hold_footwork():
    with pytest.raises(DanceDataError, match="footwork"):
        parse_moves(document("srstudio.dance-moves/1.1.0"))


def test_a_1_1_document_cannot_chain_followers():
    move = {
        "footwork": None,
        "follow": [
            {"target": "spine.left_right", "source": "root.up", "gain": 0.1},
            {"target": "chest.left_right", "source": "spine.left_right", "gain": 0.1},
        ],
    }
    doc = json.loads(document("srstudio.dance-moves/1.1.0", **move))
    del doc["moves"][0]["footwork"]
    with pytest.raises(DanceDataError, match="follow"):
        parse_moves(json.dumps(doc))


@pytest.mark.parametrize(
    "broken",
    [
        {"footwork": {"strokes": [], "weight": [{"beat": 0, "right": 0.5}], "colour": "red"}},
        {"footwork": {"weight": [{"beat": 0, "right": 0.5}]}},
        {"footwork": {"strokes": [{"foot": LEFT, "from": 0, "beats": 1, "kind": "lift", "height": 0.1, "x": 1}],
                      "weight": [{"beat": 0, "right": 0.98}]}},
        {"footwork": {"strokes": [{"foot": LEFT, "from": "soon", "beats": 1, "kind": "lift", "height": 0.1}],
                      "weight": [{"beat": 0, "right": 0.98}]}},
        {"footwork": {"strokes": [], "weight": "lots"}},
        {"footwork": {"strokes": [{"foot": LEFT, "from": 0, "beats": 1, "kind": "step", "to": [0.1]}],
                      "weight": [{"beat": 0, "right": 0.98}]}},
        {"footwork": {"strokes": [{"foot": LEFT, "from": 0, "beats": 1, "kind": "lift", "height": 1e9}],
                      "weight": [{"beat": 0, "right": 0.98}]}},
        {"footwork": ["not", "an", "object"]},
    ],
)  # fmt: skip
def test_a_broken_footwork_document_is_refused_never_coerced(broken):
    with pytest.raises(dance.DanceError, match="footwork"):
        parse_moves(document(**broken))


# --- on the floor ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_the_new_presets_stand_on_their_feet(name, preset):
    run = danced(name, preset)
    assert run.balance(FPS) == ()
    slip = run.slip(FPS)
    assert slip.ball_m < 1e-6 and slip.ankle_m < 1e-6


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_the_new_presets_pass_no_joint_limit(name, preset):
    profile = sk.preset(preset)
    run = perform(Routine(2, (Entry(0, 2, dance.moves()[name]),)), profile, GROOVE, base=stance(profile), clamp=False)
    run.frames(25)


def test_a_planted_foot_the_ankle_cannot_lay_flat_is_refused():
    """A stance too deep for the ankle: the foot must not quietly tip while the data says it stands flat."""
    deep = Move("deep", "feet", (Pattern("root.up", -1.2, 1.0, bias=-1.2),), loop_beats=4, footwork=footwork())
    profile = sk.preset("cartoon")
    run = perform(Routine(1, (Entry(0, 1, deep),)), profile, GROOVE, base=stance(profile), clamp=False)
    with pytest.raises(FloorLimitError):
        run.frames(25)


@pytest.mark.parametrize("preset", ("realistic", "cartoon"))
def test_a_heel_lift_keeps_the_ball_on_its_spot(preset):
    profile = sk.preset(preset)
    run = danced("heel-rock", preset)
    side = "left"
    spots = []
    for n in range(int(0.76 / 0.01), int(1.5 / 0.01)):  # the left heel stroke, in beats
        pose = run.pose(n * 0.01 * GROOVE.beat)
        spots.append(ball_of(profile, sk.world(profile, pose), side))
    first = spots[0]
    assert max(math.hypot(p.x - first.x, p.z - first.z) for p in spots) < 1e-4
    assert max(abs(p.y - first.y) for p in spots) < 1e-4


@pytest.mark.parametrize("preset", PRESETS)
def test_a_lifted_foot_leaves_the_floor_and_comes_back(preset):
    profile = sk.preset(preset)
    run = danced("two-step", preset)
    drop = profile.length("ankle")
    heights = [
        (run.floor_y - drop - sk.world(profile, f.pose)["left_foot"].origin.y) / profile.pelvis_height
        for f in run.frames(FPS)[:-1]
    ]
    assert max(heights) > 0.08
    assert min(abs(h) for h in heights) < 1e-6


def test_the_footwork_turns_a_toeless_foot_about_its_ball():
    profile = sk.preset("stick")
    run = danced("twist-groove", "stick")
    spot = []
    toe = sole(profile)[2] * dance_floor.BALL_SHARE
    for n in range(14, 49):  # the left foot's two pivots, in hundredths of a beat over 2
        t = n * 0.02 * GROOVE.beat
        foot = sk.world(profile, run.pose(t))["left_foot"]
        spot.append(foot.point(sk.Vec3(0.0, profile.length("ankle"), toe)))
    first = spot[0]
    assert max(math.hypot(p.x - first.x, p.z - first.z) for p in spot) < 1e-4


def test_a_routine_of_old_and_new_moves_blends_the_feet():
    profile = sk.preset("realistic")
    moves = dance.moves()
    routine = Routine(2, (Entry(0, 1, moves["hip-sway"]), Entry(1, 2, moves["two-step"])))
    run = perform(routine, profile, GROOVE, base=stance(profile))
    assert run.frame(GROOVE.at(1) + 1.0).steps is not None
    assert run.frame(0.5).steps is None or run.frame(0.5).steps.left.planted


def test_old_moves_are_frozen_they_carry_no_footwork():
    moves = dance.moves()
    for name in ("seat-groove", "hip-sway", "step-touch", "bob", "sway", "head-nod"):
        assert moves[name].footwork is None


def test_the_unloaded_share_is_what_the_weight_check_allows():
    with pytest.raises(MoveError):
        moved(footwork=footwork(weight=(WeightKey(0.0, 0.98 - UNLOADED - 0.5),)))
