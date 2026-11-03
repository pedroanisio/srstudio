"""srstudio.skeleton's visual model (ADR 0202): limb volume, near and far contours, a centreline and orientation
markers in any orthographic view, so a twist or a turn that leaves every joint origin in place still shows.

Every threshold here is derived from the geometry or measured on the model, never chosen to pass: the derivation is
written beside each one."""

import math

import pytest

from srstudio import skeleton as sk
from srstudio.limbs import Camera
from srstudio.limbs.math3d import Frame, Quaternion, Vec3

REAL = sk.preset("realistic")
SAMPLES = sk.RING_SAMPLES
# A ring of SAMPLES points inscribes its ellipse: a width read off it falls short by at most 1 - cos(pi / SAMPLES).
INSCRIBED = 1 - math.cos(math.pi / SAMPLES)


def posed(profile=REAL, **values):
    return sk.add(profile, sk.pose(profile), {k.replace("__", "."): v for k, v in values.items()})


def piece(figure, name):
    return next(p for p in figure.pieces if p.name == name)


def width(points):
    xs = [x for x, _ in points]
    return max(xs) - min(xs)


def middle_stripe(found):
    """The stripe's projected point at mid-bone: the middle of its samples."""
    points = [point for stroke in found.stripe for point in stroke.points]
    return points[len(points) // 2]


# --- the twist the line drawing cannot show -------------------------------------------------------------------------


def test_a_forearm_twist_rolls_the_stripe_by_the_forearm_radius_while_the_joints_stay():
    plain, twisted = posed(), posed(right_lower_arm__twist_in_out=math.pi / 2)
    for name in ("right_lower_arm", "right_hand"):
        assert sk.world(REAL, plain)[name].origin.distance(sk.world(REAL, twisted)[name].origin) < 1e-12
    before = piece(sk.figure(REAL, plain, sk.FRONT), "right_lower_arm")
    after = piece(sk.figure(REAL, twisted, sk.FRONT), "right_lower_arm")
    assert [*before.centreline[0], *before.centreline[1]] == pytest.approx(
        [*after.centreline[0], *after.centreline[1]], abs=1e-12
    )
    # At rest the stripe runs along the front of the forearm (+z, at the viewer): it projects onto the centreline.
    # A quarter turn about the bone carries it to the forearm's upper edge: it moves by the forearm's radius at
    # mid-bone, the mean of its two end radii, straight up the screen (y down).
    radius = sum(before.radii[0]) / 4 + sum(before.radii[1]) / 4
    (x0, y0), (x1, y1) = middle_stripe(before), middle_stripe(after)
    assert x1 == pytest.approx(x0, abs=1e-9)
    assert y0 - y1 == pytest.approx(radius, rel=1e-9)
    assert radius == pytest.approx(0.0205 * REAL.stature, rel=1e-9)  # (0.025 + 0.016) / 2 of the stature
    assert before.stripe[0].near and len(before.stripe) == 1


def test_past_a_quarter_turn_the_stripe_rolls_onto_the_hidden_half_and_is_dashed():
    _, high = REAL.limits_of("right_lower_arm.twist_in_out")
    assert high > math.pi / 2
    rolled = piece(sk.figure(REAL, posed(right_lower_arm__twist_in_out=high), sk.FRONT), "right_lower_arm")
    assert [stroke.near for stroke in rolled.stripe] == [False]


def test_a_quarter_turn_of_the_torso_changes_its_silhouette_and_not_its_spine():
    turn = math.pi / 4
    plain, turned = posed(), posed(hips__twist_left_right=turn)
    spine = ("hips", "spine", "chest", "upper_chest", "neck")
    for name in spine:  # the line drawing's torso: these origins lie on the turn's axis
        a, b = sk.world(REAL, plain)[name].origin, sk.world(REAL, turned)[name].origin
        assert a.distance(b) < 1e-12
    before = piece(sk.figure(REAL, plain, sk.FRONT), "upper_chest")
    after = piece(sk.figure(REAL, turned, sk.FRONT), "upper_chest")

    # Each section is an ellipse of half-depth a and half-width b; turned by t about the vertical and seen from the
    # front, its width is 2 sqrt(b^2 cos^2 t + a^2 sin^2 t). The widest section sets the silhouette's width.
    def seen(radii, t):
        return max(2 * math.hypot(b * math.cos(t), a * math.sin(t)) for a, b in radii)

    assert width(before.silhouette) == pytest.approx(seen(before.radii, 0), rel=INSCRIBED)
    assert width(after.silhouette) == pytest.approx(seen(after.radii, turn), rel=INSCRIBED)
    # The change is larger than the sampling error of both widths together.
    assert width(before.silhouette) - width(after.silhouette) > 2 * INSCRIBED * width(before.silhouette)


@pytest.mark.parametrize(("front_back", "facing"), [(-math.pi / 4, "distal"), (math.pi / 4, "proximal")])
def test_the_end_pointing_at_the_viewer_shows_its_whole_cap_and_the_other_hides_its_far_arc(front_back, facing):
    # right_upper_arm.front_back turns the arm about +y: negative swings it forward (+z), toward the front view.
    found = piece(sk.figure(REAL, posed(right_upper_arm__front_back=front_back), sk.FRONT), "right_upper_arm")
    caps = {cap.end: cap for cap in found.caps}
    other = "proximal" if facing == "distal" else "distal"
    assert caps[facing].facing and caps[facing].far == () and caps[facing].near
    assert not caps[other].facing and caps[other].far and caps[other].near


def test_a_limb_across_the_line_of_sight_hides_half_of_both_caps():
    found = piece(sk.figure(REAL, posed(), sk.FRONT), "right_upper_leg")
    assert all(not cap.facing and cap.far and cap.near for cap in found.caps)


# --- sizes ----------------------------------------------------------------------------------------------------------


def test_radii_are_the_stated_shares_of_the_stature_and_scale_with_the_profile():
    half = sk.SkeletonProfile("half", sk.Proportions(REAL.proportions.height_m / 2, REAL.head_radius / 2))
    big, small = sk.figure(REAL, sk.pose(REAL), sk.FRONT), sk.figure(half, sk.pose(half), sk.FRONT)
    assert half.stature / REAL.stature == pytest.approx(0.5, rel=1e-12)
    for name in ("right_upper_arm", "left_lower_leg", "neck", "upper_chest"):
        a, b = piece(big, name).radii, piece(small, name).radii
        assert [x / 2 for pair in a for x in pair] == pytest.approx([x for pair in b for x in pair], rel=1e-9)
    share = sk.RADII["upper_arm"]
    (a0, b0), (a1, b1) = piece(big, "right_upper_arm").radii
    assert [a0, b0, a1, b1] == pytest.approx([share[0] * REAL.stature] * 2 + [share[1] * REAL.stature] * 2, rel=1e-12)
    head = piece(big, "head")
    assert head.radii == ((REAL.head_radius, REAL.head_radius),) * 2


def test_the_torso_widths_follow_the_profile_factors():
    narrow = sk.preset("stick")  # shoulders 0.7, hips 0.5
    chest = piece(sk.figure(narrow, sk.pose(narrow), sk.FRONT), "upper_chest").radii[0]
    pelvis = piece(sk.figure(narrow, sk.pose(narrow), sk.FRONT), "hips").radii[0]
    assert chest[1] == pytest.approx(sk.TORSO["upper_chest"][0][1] * narrow.stature * 0.7, rel=1e-12)
    assert pelvis[1] == pytest.approx(sk.TORSO["hips"][0][1] * narrow.stature * 0.5, rel=1e-12)


# --- depth order and markers ----------------------------------------------------------------------------------------


def _overlap(a, b):
    ax, ay = zip(*a.silhouette, strict=True)
    bx, by = zip(*b.silhouette, strict=True)
    return min(ax) < max(bx) and min(bx) < max(ax) and min(ay) < max(by) and min(by) < max(ay)


def test_from_the_left_the_left_arm_is_drawn_over_the_torso_and_the_right_arm_under_it():
    found = sk.figure(REAL, sk.rest_pose(REAL), sk.LEFT)
    order = [p.name for p in found.pieces]
    torso = [order.index(n) for n in ("hips", "spine", "chest", "upper_chest")]
    near = [order.index(n) for n in ("left_upper_arm", "left_lower_arm")]
    far = [order.index(n) for n in ("right_upper_arm", "right_lower_arm")]
    assert max(far) < min(torso) and max(torso) < min(near)
    assert _overlap(piece(found, "left_upper_arm"), piece(found, "chest"))  # they do overlap on the screen
    depth = [p.depth for p in found.pieces]
    assert depth == sorted(depth)


def test_a_forearm_folded_across_the_chest_is_drawn_over_it_from_the_front():
    folded = sk.add(
        REAL,
        sk.pose(REAL),
        {"right_upper_arm.down_up": -0.8, "right_upper_arm.front_back": -1.2, "right_lower_arm.stretch": -1.8},
    )
    found = sk.figure(REAL, folded, sk.FRONT)
    order = [p.name for p in found.pieces]
    assert _overlap(piece(found, "right_lower_arm"), piece(found, "upper_chest"))
    assert order.index("right_lower_arm") > order.index("upper_chest")
    from_back = sk.figure(REAL, folded, sk.View("back", Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, -1)))
    order = [p.name for p in from_back.pieces]
    assert order.index("right_lower_arm") < order.index("upper_chest")


def test_markers_point_where_their_frames_face():
    found = sk.figure(REAL, sk.rest_pose(REAL), sk.FRONT)
    markers = {m.name: m for p in found.pieces for m in p.markers}
    assert set(markers) == {"chest-normal", "pelvis-front", "palm-left", "palm-right", "head-facing"}
    assert markers["chest-normal"].near and markers["head-facing"].near and markers["pelvis-front"].near
    side = sk.figure(REAL, sk.rest_pose(REAL), sk.LEFT)
    facing = next(m for p in side.pieces for m in p.markers if m.name == "head-facing")
    (x0, _), (x1, _) = facing.points
    assert x1 > x0  # from the left, the face looks along +z, screen right in this mirror view
    turned = sk.figure(REAL, posed(hips__twist_left_right=math.pi), sk.FRONT)
    back = {m.name: m for p in turned.pieces for m in p.markers}
    assert not back["chest-normal"].near and not back["head-facing"].near


def test_a_palm_turned_up_points_its_normal_up():
    # At the T-stance the palm faces down (+y). The upper arm's and the forearm's rolls about the arm's axis add up:
    # near half a turn in all, the palm faces up.
    found = sk.figure(REAL, posed(right_upper_arm__twist_in_out=1.57, right_lower_arm__twist_in_out=1.5), sk.FRONT)
    palm = next(m for p in found.pieces for m in p.markers if m.name == "palm-right")
    (_, y0), (_, y1) = palm.points
    assert y1 < y0  # y is down: the palm's normal points up the screen
    down = next(m for p in sk.figure(REAL, sk.pose(REAL), sk.FRONT).pieces for m in p.markers if m.name == "palm-right")
    assert down.points[1][1] > down.points[0][1]


def test_an_unobserved_twist_drops_the_stripe_and_the_tick():
    found = sk.figure(REAL, sk.pose(REAL), sk.FRONT, unobserved=("right_lower_arm",))
    arm = piece(found, "right_lower_arm")
    assert arm.twist == "unobserved" and arm.stripe == () and arm.tick is None
    assert piece(found, "left_lower_arm").twist == "posed" and piece(found, "left_lower_arm").stripe


def test_every_view_gives_every_piece_and_the_mirror_views_say_so():
    for view in (sk.FRONT, sk.LEFT, sk.TOP):
        assert view.mirrored
        found = sk.figure(REAL, sk.rest_pose(REAL), view)
        names = {p.name for p in found.pieces}
        assert {"head", "neck", "hips", "right_foot", "left_toes", "right_index_distal"} <= names
    back = sk.View("back", Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, -1))
    assert not back.mirrored


def test_an_orthographic_camera_is_a_view_and_matches_its_projection():
    camera = Camera(view=Frame(Vec3(0.3, -1.0, 2.0), Quaternion.axis_angle(Vec3(0, 1, 0), 0.4)))
    view = sk.view_from_camera(camera)
    point = Vec3(0.2, -1.1, 0.4)
    shown = camera.project(point)
    u, v = view.flat(point)
    origin = camera.view.origin
    assert ((u - view.flat(origin)[0]) * camera.scale, (v - view.flat(origin)[1]) * camera.scale) == pytest.approx(
        shown.xy, abs=1e-9
    )
    assert view.depth(point) - view.depth(origin) == pytest.approx(shown.depth, abs=1e-12)


# --- refusals -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("right", "down", "toward", "words"),
    [
        (Vec3(2, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1), "unit"),
        (Vec3(1, 0, 0), Vec3(1, 0, 0), Vec3(0, 0, 1), "perpendicular"),
        ((1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1), "Vec3"),
    ],
)
def test_a_view_that_is_not_an_orthonormal_frame_is_refused(right, down, toward, words):
    with pytest.raises(sk.SkeletonViewError, match=words) as caught:
        sk.View("bad", right, down, toward)
    assert caught.value.code == "skeleton.view"


def test_malformed_inputs_are_refused_with_typed_errors():
    with pytest.raises(sk.SkeletonViewError, match="name"):
        sk.View("Not A Name", Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1))
    with pytest.raises(sk.SkeletonViewError, match="orthographic"):
        sk.view_from_camera(Camera(projection="perspective"))
    with pytest.raises(sk.SkeletonViewError, match="Camera"):
        sk.view_from_camera("front")
    with pytest.raises(sk.SkeletonViewError, match="View"):
        sk.figure(REAL, sk.pose(REAL), "front")
    with pytest.raises(sk.SkeletonSchemaError, match="SkeletonProfile"):
        sk.figure("realistic", sk.pose(REAL), sk.FRONT)
    with pytest.raises(sk.SkeletonSchemaError, match="SkeletonPose"):
        sk.figure(REAL, {"hips.up": 0.1}, sk.FRONT)
    with pytest.raises(sk.SkeletonError) as caught:
        sk.figure(REAL, sk.pose(REAL), sk.FRONT, unobserved=("tail",))
    assert caught.value.code == "skeleton.unknown"
    stick = sk.preset("stick")
    with pytest.raises(sk.SkeletonError) as caught:
        sk.figure(stick, sk.SkeletonPose(values=(("left_toes.up_down", 0.2),)), sk.FRONT)
    assert caught.value.code == "skeleton.absent"
