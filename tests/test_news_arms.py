"""The geometry of the anchors' arms from version 5 (ADR 0071), each rule measured on version 5 and on version 4, whose
drawing broke it, so that every rule is seen to bite."""

from __future__ import annotations

import math

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, news_arms, news_inked, news_kit, parts, specimens
from srstudio.news_arms import BUILDS, ELBOW_LEAST, TORSOS
from srstudio.news_kit import ARMS, Pose

anchors = pytest.mark.parametrize("who", ["vera", "gus"])
SIDES = (-1.0, 1.0)
FRAME = 1 / 30
LENGTH_TOLERANCE = 0.5  # px: what rounding leaves of one length
SHOULDER_ROOM = 1.0  # px a sleeve's root may sit past the jacket's control polygon
STEP_MOST = 60.0  # px a wrist may travel in a frame, in the anchor's own units
OLD_TORSO = {"vera": news_inked.VERA_TORSO, "gus": news_inked.GUS_TORSO}
V4_PHONE_HELD = -82.0


def inside(point, polygon) -> bool:
    x, y = point
    hit = False
    for (ax, ay), (bx, by) in zip(polygon, [*polygon[1:], polygon[0]], strict=True):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def edge_distance(point, polygon) -> float:
    def to_segment(a, b) -> float:
        ax, ay, bx, by = *a, *b
        along = ((point[0] - ax) * (bx - ax) + (point[1] - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)
        k = max(0.0, min(1.0, along))
        return math.dist(point, (ax + k * (bx - ax), ay + k * (by - ay)))

    return min(to_segment(a, b) for a, b in zip(polygon, [*polygon[1:], polygon[0]], strict=True))


def arms_of(who: str, number: int):
    return [arm for state in ARMS for arm in news_inked.skeleton(who, number, state)]


def spread(who: str, number: int, bone: int) -> float:
    lengths = [math.dist(arm[bone], arm[bone + 1]) for arm in arms_of(who, number)]
    return max(lengths) - min(lengths)


def elbow_inside(arm) -> float:
    s, e, w = arm
    a, b = (s[0] - e[0], s[1] - e[1]), (w[0] - e[0], w[1] - e[1])
    return math.degrees(math.acos((a[0] * b[0] + a[1] * b[1]) / (math.hypot(*a) * math.hypot(*b))))


def root_points(who: str, number: int, side: float, state: str) -> list[tuple[float, float]]:
    """What a sleeve puts around its shoulder, in the anchor's units: the root's rim, or, before version 5, its cap."""
    s, e, w = news_inked.skeleton(who, number, state)[0 if side < 0 else 1]
    if number >= 5:
        r = BUILDS[who].root
        return [(s[0] + r * math.cos(a), s[1] + r * math.sin(a)) for a in [i * math.pi / 12 for i in range(24)]]
    contour = news_inked._limb(s, e, w, 78.0, 62.0, 46.0)
    return [contour[0], contour[1], contour[-1]]


def torso_of(who: str, number: int):
    return TORSOS[who] if number >= 5 else OLD_TORSO[who]


def root_outside(who: str, number: int) -> float:
    """How far past the jacket the worst root of any pose reaches."""
    worst = 0.0
    torso = torso_of(who, number)
    for state in ARMS:
        for side in SIDES:
            for point in root_points(who, number, side, state):
                if not inside(point, torso):
                    worst = max(worst, edge_distance(point, torso))
    return worst


def line_gap(who: str, number: int) -> float:
    """How far apart a sleeve's ink ends at the shoulder: nothing where a line runs right round the root."""
    if number < 5:
        return 0.0  # the contour of news_inked._limb is closed: its ink goes across the top of the arm
    points = news_arms.sleeve(BUILDS[who], 6.0)
    return math.dist(points[0], points[-1])


def wrist_steps(who: str, number: int, acts) -> float:
    """The most any wrist moves in one frame through ``acts``."""
    end = acts[-1][0] + 1.0
    frames = [i * FRAME for i in range(int(end / FRAME))]
    worst = 0.0
    for side in SIDES:
        if number >= 5:
            keys = news_arms.keys_of(who, side, acts)
            at = [news_arms.joints_at(who, side, keys, t)[2] for t in frames]
        else:
            at = []
            for t in frames:
                state = next(pose.arms for when, pose in reversed(acts) if when <= t)
                at.append(news_inked.skeleton(who, number, state)[0 if side < 0 else 1][2])
        worst = max(worst, *(math.dist(a, b) for a, b in zip(at, at[1:], strict=False)))
    return worst


def every_change() -> tuple:
    rows = [(a, b) for a in ARMS for b in ARMS if a != b]
    states = [state for pair in rows for state in pair]
    return tuple((float(i), Pose(arms=state)) for i, state in enumerate(states))


@anchors
@pytest.mark.parametrize("bone", [0, 1], ids=["upper", "forearm"])
def test_a_length_of_arm_stays_one_length_in_every_pose(who, bone):
    assert spread(who, 5, bone) <= LENGTH_TOLERANCE
    if who == "gus":
        assert spread(who, 4, bone) > LENGTH_TOLERANCE


@anchors
def test_no_pose_holds_an_elbow_sharper_than_the_limit(who):
    assert min(elbow_inside(arm) for arm in arms_of(who, 5)) >= ELBOW_LEAST
    if who == "gus":
        assert min(elbow_inside(arm) for arm in arms_of(who, 4)) < ELBOW_LEAST


@anchors
def test_a_sleeve_starts_inside_the_jacket(who):
    assert root_outside(who, 5) <= SHOULDER_ROOM
    assert root_outside(who, 4) > SHOULDER_ROOM


@anchors
def test_the_jacket_slopes_from_the_neck_and_comes_in_to_the_desk(who):
    def sides(torso):
        right = [p for p in torso if p[0] > 0]
        return max(right, key=lambda p: p[1])[0], max(p[0] for p in right)

    hem, widest = sides(TORSOS[who])
    assert hem < widest - 6.0
    hem, widest = sides(OLD_TORSO[who])
    assert hem >= widest - 6.0


@anchors
def test_no_ink_crosses_the_arm_at_the_shoulder(who):
    assert line_gap(who, 5) >= BUILDS[who].root
    assert line_gap(who, 4) == 0.0


@pytest.mark.parametrize("who", ["gus"])
def test_a_wrist_travels_between_poses_and_never_jumps(who):
    acts = every_change()
    assert wrist_steps(who, 5, acts) <= STEP_MOST
    assert wrist_steps(who, 4, acts) > STEP_MOST


def test_a_wrist_reaches_every_key_on_its_own_bones():
    acts = every_change()
    build = BUILDS["gus"]
    for side in SIDES:
        keys = news_arms.keys_of("gus", side, acts)
        for t in [i * FRAME for i in range(600)]:
            s, e, w = news_arms.joints_at("gus", side, keys, t)
            assert s == (build.shoulder[0] * side, build.shoulder[1])
            assert math.dist(s, e) == pytest.approx(build.upper)
            assert math.dist(e, w) == pytest.approx(build.fore)
            assert w[1] < 60.0, "an arm between poses stays off the front of the desk"


def test_a_pose_holds_the_joints_it_solved():
    for side in SIDES:
        for at_rest, pose in enumerate(ARMS):
            acts = ((0.0, Pose(arms=pose)),)
            _, _, wrist = news_arms.joints_at("gus", side, news_arms.keys_of("gus", side, acts), 0.0)
            reach = news_arms.REACHES["gus"][pose][0 if side < 0 else 1]
            assert wrist == pytest.approx(reach.wrist), at_rest


def test_an_arm_that_cannot_reach_a_pose_is_refused():
    reach = news_arms.Reach((-900.0, 0.0), "fist", 0.0)
    with pytest.raises(news_kit.NewsKitError, match="cannot reach"):
        news_arms.elbow_of(BUILDS["gus"], -1.0, reach)
    with pytest.raises(news_kit.NewsKitError, match="cannot reach"):
        news_arms.elbow_of(BUILDS["gus"], -1.0, news_arms.Reach((-166.0, -96.0), "fist", 0.0))


@pytest.mark.parametrize("who", ["vera", "gus"])
def test_the_arms_stay_off_the_lower_third_in_the_closest_framing(who):
    scale = news_inked.FRAMING[who][1]
    build = BUILDS[who]
    lowest = max(point[1] + build.elbow for arm in arms_of(who, 5) for point in arm)
    assert news_kit.DESK_Y + lowest * scale < news_inked.LOWER_Y


def test_no_hand_comes_in_front_of_the_face_in_a_held_pose():
    head = 210.0  # half the width of Gus's hair, the widest thing above his neck
    for arm in arms_of("gus", 5):
        wrist = arm[2]
        assert wrist[1] > news_inked.NECK_Y or abs(wrist[0]) > head


def test_the_phone_stops_below_the_collar():
    top_of_the_phone = 84.0
    assert news_inked.PHONE_HELD - top_of_the_phone > news_inked.COLLAR_Y
    assert V4_PHONE_HELD - top_of_the_phone <= news_inked.COLLAR_Y


def test_an_elbow_closes_the_same_way_all_the_way_through_every_change():
    for side in SIDES:
        keys = news_arms.keys_of("gus", side, every_change())
        bends = [news_arms.value_at(keys["bend"], i * FRAME) * side for i in range(600)]
        assert all(bend > 0 for bend in bends) or all(bend < 0 for bend in bends)


def test_the_arms_turn_on_keys_from_version_5_and_cut_between_drawings_before_it():
    def rotations(number: int) -> int:
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="30", duration=4.0, background=news_kit.PLUM_DEEP)
        cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        acts = tuple((float(i), Pose(arms=state)) for i, state in enumerate(("rest", "up", "point", "rest")))
        news_inked.perform(cv, back, "gus", 400.0, acts, 0.0, 4.0, scale=1.0, over=front, number=number)
        return cv.scene.to_bytes(layout="pretty").count(b'property="rotation"')

    assert rotations(5) > rotations(4)


def test_gus_grips_his_phone_with_both_hands():
    left, right = news_inked.skeleton("gus", 5, "phone")
    assert left[2][0] == -right[2][0]
    assert abs(left[2][0]) - 48.0 < 30.0  # the phone's half width, and the reach of a fist from its wrist


@anchors
def test_version_5_changes_only_the_shoulders_and_the_arms(who):
    assert news_inked.inked(who, 5) is news_inked.inked(who, 4)
    assert news_inked.RIGS[f"news-{who}@5"] is news_inked.RIGS[f"news-{who}@4"]


@anchors
def test_version_5_is_approved(who):
    name = f"news-{who}"
    version = parts.get(name).version(5)
    assert version.status == "approved"
    assert version.rig.status == "approved"
    assert "Slack 1793489774.457989" in version.approval.words
    assert version.approval.words == version.rig.approval.words
    assert specimens.digest(name, 5) == version.drawing
    assert specimens.rig_digest(name, 5) == version.rig.drawing
    assert specimens.digest(name, 5) != specimens.digest(name, 4)


def scene_of(who, number):
    """The scene of an anchor in the pose that shows both hands."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=2.0, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    news_inked.perform(cv, back, who, 540.0, ((0.0, Pose(arms="up")),), 0.0, 2.0, scale=1.0, over=front, number=number)
    return cv.scene.to_bytes(layout="pretty")


@pytest.mark.parametrize("side", SIDES)
def test_a_palm_to_the_camera_has_its_thumb_inward_on_either_arm(side):
    thumb = min(news_inked.FINGERS_UP, key=lambda p: p[0] + p[1] * 0.1)  # the far low tip: the thumb, not a finger
    assert thumb[0] < 0
    drawn = -thumb[0] if news_arms.Hand("open", side).mirrored else thumb[0]
    assert drawn * side < 0


def test_the_two_open_hands_are_a_pair_and_not_the_same_hand():
    left, right = news_arms.Hand("open", -1.0), news_arms.Hand("open", 1.0)
    assert left.mirrored != right.mirrored


@pytest.mark.parametrize("kind", sorted(news_arms.DRAWN_FOR))
def test_every_shape_is_mirrored_on_exactly_one_arm(kind):
    assert news_arms.Hand(kind, -1.0).mirrored != news_arms.Hand(kind, 1.0).mirrored


def test_a_level_point_keeps_its_thumb_on_top_on_the_arm_that_points():
    hand = news_arms.Hand("point", -1.0)
    assert not hand.mirrored
    thumb = max(news_inked.POINTING, key=lambda p: p[0])
    turn = math.radians(news_arms.REACHES["gus"]["point"][0].turn)
    assert thumb[0] * math.sin(turn) + thumb[1] * math.cos(turn) < -30.0  # above the wrist on the frame


def test_a_hand_on_the_other_arm_is_refused():
    with pytest.raises(news_kit.NewsKitError, match="was placed on side"):
        news_arms.Hand("open", 1.0).on(-1.0)
    assert news_arms.Hand("open", 1.0).on(1.0).mirrored is False


@pytest.mark.parametrize(("kind", "side"), [("claw", 1.0), ("open", 0.0)])
def test_a_hand_that_is_no_hand_of_the_pair_is_refused(kind, side):
    with pytest.raises(news_kit.NewsKitError):
        news_arms.Hand(kind, side)


@anchors
def test_version_6_mirrors_one_hand_of_the_pair_and_version_5_stays_as_it_went_out(who):
    assert scene_of(who, 6).count(b'scaleX="-') == scene_of(who, 5).count(b'scaleX="-') + 1


@anchors
def test_version_6_changes_only_the_hands(who):
    assert news_inked.inked(who, 6) is news_inked.inked(who, 5)
    assert news_inked.RIGS[f"news-{who}@6"] is news_inked.RIGS[f"news-{who}@5"]


@anchors
def test_version_6_is_approved_and_is_what_new_reels_get(who):
    name = f"news-{who}"
    version = parts.get(name).version(6)
    assert (version.status, version.rig.status) == ("approved", "approved")
    assert "Slack 1793545038.063029" in version.approval.words
    assert parts.latest(name).number == 6
    assert specimens.digest(name, 6) == version.drawing
    assert specimens.rig_digest(name, 6) == version.rig.drawing
    assert specimens.digest(name, 6) != specimens.digest(name, 5)
