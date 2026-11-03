"""The preset moves on the shared skeleton (ADR 0186, ADR 0192): every preset stays inside the limits of every preset
character without clamping, at a dense set of times and mirrored."""

import pytest

from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

GRID = Groove(120)  # half a second a beat
PROFILES = {name: sk.preset(name) for name in sk.PRESETS}
STEPS = 48  # samples a beat: finer than any stroke of the presets


def posed(profile, source, beat):
    """``source`` danced at ``beat`` on ``profile``, unclamped: a value past a limit raises."""
    return dance_pose(profile, dance.sample(source, GRID, beat * GRID.beat)).pose


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize("name", list(dance.moves()))
def test_every_preset_dances_within_every_characters_limits_unclamped(name, character):
    move = dance.moves()[name]
    for source in (move, move.mirror()):
        for step in range(round(move.loop_beats * STEPS)):
            posed(PROFILES[character], source, step / STEPS)


# --- the dance gestures (ADR 0192), each proved on the skeleton's forward kinematics ---------------------------------

GESTURES = ("clap", "point-up", "raise-the-roof", "hand-wave-side", "shoulder-roll", "hip-sway", "hands-up")
MOVES = dance.moves()
SIDES = ("left", "right")


def radius(profile):
    return profile.proportions.head_radius_m


def hand_tip(profile, pose, side):
    """The middle of the side's fingertips (one tip on a mitten): where the hand reaches."""
    points = [v for k, v in sk.tips(profile, pose).items() if k.startswith(f"{side}_") and not k.endswith("toes")]
    return tuple(sum(getattr(v, axis) for v in points) / len(points) for axis in "xyz")


def shoulder(profile, pose, side):
    point = sk.world(profile, pose)[f"{side}_upper_arm"].origin
    return (point.x, point.y, point.z)


def crown(profile, pose):
    return sk.tips(profile, pose)["head"].y


def above(profile, y, reference):
    """How far ``y`` is above ``reference``, in head radii (y points down)."""
    return (reference - y) / radius(profile)


def palm_up(profile, pose, side):
    """The upward share of the palm's normal: the way the fingertips move when the fingers curl a little."""
    curls = {
        c: -0.2
        for c in profile.controls
        if c.startswith(f"{side}_") and c.endswith("_proximal.stretched") and "thumb" not in c
    }
    before, after = sk.tips(profile, pose), sk.tips(profile, sk.add(profile, pose, curls))
    tips = [k for k in before if k.startswith(f"{side}_") and "thumb" not in k and not k.endswith("toes")]
    move = [sum(getattr(after[k], a) - getattr(before[k], a) for k in tips) for a in "xyz"]
    return -move[1] / sum(c * c for c in move) ** 0.5


def test_the_gestures_ship_as_presets():
    assert set(GESTURES) <= set(MOVES)


@pytest.mark.parametrize("name", GESTURES)
def test_a_gesture_moves_only_canonical_controls(name):
    move = MOVES[name]
    assert all(p.target in dance.ROOT or p.target in sk.CONTROLS for p in move.patterns)
    frame = dance.sample(move, GRID, 0.0)
    assert dance_pose(PROFILES["realistic"], frame).dropped == frozenset()


@pytest.mark.parametrize("name", GESTURES)
def test_a_gestures_arms_ride_the_body_with_no_lag(name):
    move = MOVES[name]
    assert move.lag("left_arm") == move.lag("right_arm") == 0


def _swap(name):
    for a, b in (("left_", "right_"), ("right_", "left_")):
        if name.startswith(a):
            return b + name[len(a) :]
    return name


def test_the_realistic_skeleton_is_its_own_mirror_at_rest():
    profile = PROFILES["realistic"]
    world = sk.world(profile, sk.rest_pose(profile))
    for name, frame in world.items():
        other = world[_swap(name)].origin
        assert (other.x, other.y, other.z) == pytest.approx((-frame.origin.x, frame.origin.y, frame.origin.z), abs=1e-9)


@pytest.mark.parametrize("name", GESTURES)
def test_a_mirrored_gesture_is_the_gesture_seen_in_a_mirror(name):
    profile, move = PROFILES["realistic"], MOVES[name]
    for beat in (0.0, 0.3, 0.77, 1.5, 2.9):
        seen = sk.world(profile, posed(profile, move, beat))
        mirrored = sk.world(profile, posed(profile, move.mirror(), beat))
        for joint, frame in seen.items():
            other = mirrored[_swap(joint)].origin
            assert (other.x, other.y, other.z) == pytest.approx(
                (-frame.origin.x, frame.origin.y, frame.origin.z), abs=1e-9
            ), (name, beat, joint)


# clap: the hands meet in front of the chest on the beat and part between beats. The cartoon's arms are short against
# its shoulders, so at the angles where the realistic and stick hands meet its hands stop short; at intensity 2 they
# meet too.
CLAP_MEET = {"realistic": 0.1, "stick": 0.3, "cartoon": 0.9}


@pytest.mark.parametrize("character", sk.PRESETS)
def test_clap_hands_meet_in_front_on_the_beat_and_part_between(character):
    profile, move = PROFILES[character], MOVES["clap"]
    r = radius(profile)
    for beat in (0, 1, 2):
        pose = posed(profile, move, beat)
        left, right = hand_tip(profile, pose, "left"), hand_tip(profile, pose, "right")
        assert sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) ** 0.5 / r < CLAP_MEET[character]
        assert left[2] / r > 1.0 and right[2] / r > 1.0  # in front of the body
        assert above(profile, left[1], shoulder(profile, pose, "left")[1]) < 0  # below the shoulders: chest height
        apart = posed(profile, move, beat + 0.65)  # the far extreme of a sine with snap 0.35
        gap = hand_tip(profile, apart, "right")[0] - hand_tip(profile, apart, "left")[0]
        assert gap / r > 2.5
    for step in range(STEPS):
        pose = posed(profile, move, step / STEPS)
        assert hand_tip(profile, pose, "left")[0] / r < 0.15  # a hand never passes the middle by more than this


def test_a_cartoon_claps_shut_at_intensity_two():
    profile = PROFILES["cartoon"]
    routine = dance.Routine(1, (dance.Entry(0, 1, MOVES["clap"], intensity=2.0),))
    pose = posed(profile, routine, 0.0)
    left, right = hand_tip(profile, pose, "left"), hand_tip(profile, pose, "right")
    assert abs(right[0] - left[0]) / radius(profile) < 0.15


# point-up: the right arm points up and out on one, the left on two, held between.


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize(("beat", "up", "down"), [(0, "right", "left"), (1, "left", "right")])
def test_point_up_points_above_the_head_and_out_on_its_beat(character, beat, up, down):
    profile = PROFILES[character]
    r = radius(profile)
    for at in (beat, beat + 0.25, beat + 2):  # on the beat, held after it, and a loop later
        pose = posed(profile, MOVES["point-up"], at)
        tip = hand_tip(profile, pose, up)
        assert above(profile, tip[1], crown(profile, pose) + r) > 0.3  # above the middle of the head
        if character != "cartoon":  # its arms are shorter than its head is tall: it cannot reach past its crown
            assert above(profile, tip[1], crown(profile, pose)) > 1.0
        outward = (tip[0] - shoulder(profile, pose, up)[0]) * (1 if up == "right" else -1)
        assert outward / r > 0.5  # a diagonal: out past its own shoulder
        low = hand_tip(profile, pose, down)
        assert above(profile, low[1], shoulder(profile, pose, down)[1]) < -0.5


# raise-the-roof: elbows out, both hands above the shoulders, palms up, pushing up onto the beat.


@pytest.mark.parametrize("character", sk.PRESETS)
def test_raise_the_roof_pushes_both_palms_up_on_the_beat(character):
    profile = PROFILES[character]
    move = MOVES["raise-the-roof"]
    heights = {side: [] for side in SIDES}
    for step in range(STEPS + 1):
        pose = posed(profile, move, step / STEPS)
        for side in SIDES:
            height = above(profile, hand_tip(profile, pose, side)[1], shoulder(profile, pose, side)[1])
            assert height > 0.8, (side, step)
            heights[side].append(height)
    for side in SIDES:
        assert heights[side][0] == pytest.approx(max(heights[side]))  # the top lands on the beat
        assert heights[side][0] > heights[side][-2] > heights[side][-6]  # still rising into it
        assert heights[side][0] - min(heights[side]) > 0.3  # a push, not a hold
        assert palm_up(profile, posed(profile, move, 0), side) > 0.6


# hand-wave-side: both raised hands travel right over the first half of the bar and left over the second.


@pytest.mark.parametrize("character", sk.PRESETS)
def test_hand_wave_side_carries_both_hands_side_to_side_over_a_bar(character):
    profile = PROFILES[character]
    move = MOVES["hand-wave-side"]
    r = radius(profile)
    one, three = posed(profile, move, 0), posed(profile, move, 2)
    for side in SIDES:
        assert (hand_tip(profile, one, side)[0] - hand_tip(profile, three, side)[0]) / r > 1.5
    assert sk.world(profile, posed(profile, move, 4)) == sk.world(profile, one)  # one wave a bar
    for step in range(4 * STEPS // 4):
        pose = posed(profile, move, step / 12)
        for side in SIDES:
            assert above(profile, hand_tip(profile, pose, side)[1], shoulder(profile, pose, side)[1]) > 0.5


# shoulder-roll: each shoulder goes up, back, down and forward over two beats, the left a beat after the right.


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize(("side", "start"), [("right", 0), ("left", 1)])
def test_shoulder_roll_rolls_each_shoulder_backward_in_turn(character, side, start):
    profile = PROFILES[character]
    path = [shoulder(profile, posed(profile, MOVES["shoulder-roll"], start + step / 8), side) for step in range(16)]
    heights = [-y for _, y, _ in path]
    forward = [z for _, _, z in path]
    assert heights.index(max(heights)) == 0  # up on its beat
    assert forward.index(min(forward)) == 4  # back half a beat later
    assert heights.index(min(heights)) == 8  # down a beat later
    assert forward.index(max(forward)) == 12  # forward, then up again
    assert (max(heights) - min(heights)) / radius(profile) > 0.2


# hip-sway: the hips go right on one and left on two; the hands go with them, and further.


@pytest.mark.parametrize("character", sk.PRESETS)
def test_hip_sway_carries_the_hands_with_the_hips(character):
    profile = PROFILES[character]
    move = MOVES["hip-sway"]
    right, left = posed(profile, move, 0), posed(profile, move, 1)
    hips = sk.world(profile, right)["hips"].origin.x - sk.world(profile, left)["hips"].origin.x
    assert hips / radius(profile) > 0.4
    for side in SIDES:
        assert hand_tip(profile, right, side)[0] - hand_tip(profile, left, side)[0] > 2 * hips


# hands-up: a held pose, both hands high, usable as an entry's hold over a move that leaves the arms alone.


@pytest.mark.parametrize("character", sk.PRESETS)
def test_hands_up_holds_both_hands_over_the_head(character):
    profile = PROFILES[character]
    move = MOVES["hands-up"]
    pose = posed(profile, move, 0)
    assert posed(profile, move, 0.37) == pose
    for side in SIDES:
        y = hand_tip(profile, pose, side)[1]
        assert above(profile, y, crown(profile, pose) + radius(profile)) > 0.5
        if character != "cartoon":
            assert above(profile, y, crown(profile, pose)) > 1.5


def test_hands_up_is_held_as_bias_pairs():
    held = MOVES["hands-up"].held()
    assert dict(held) == {p.target: p.bias for p in MOVES["hands-up"].patterns}
    with pytest.raises(dance.MoveError, match="held pose"):
        MOVES["clap"].held()


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize("name", ["seat-groove", "head-nod", "shoulder-roll", "bob", "sway"])
def test_hands_up_holds_over_a_move_that_leaves_the_arms_alone(character, name):
    profile = PROFILES[character]
    entry = dance.Entry(0, 2, MOVES[name], transition_beats=2, hold=MOVES["hands-up"].held())
    routine = dance.Routine(2, (entry,))
    for step in range(8 * 12):  # every twelfth of a beat, through the crossfade in
        pose = posed(profile, routine, step / 12)  # unclamped: within every character's limits
        if step >= 24:  # the hold is in full after the two-beat transition
            for side in SIDES:
                assert above(profile, hand_tip(profile, pose, side)[1], crown(profile, pose) + radius(profile)) > 0.3
