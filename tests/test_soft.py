"""The Soft style: its palette and frame, top captions, and the pose-sheet blob character."""

import json
import math
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import SOFT, STYLES, WARM, Canvas, EpisodeSpec, blob, graphics, registry
from srstudio.blob import ARMS, EYES, LIMBS, MOUTHS, POSES, BlobError, Cue, Pose, Stroke
from srstudio.soundtrack import SOFT_MOUTH

NS = "{https://scene-render.dev/schema}"


def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


def canvas(duration=4) -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=duration, background=WARM.background)
    return scene, Canvas(scene, WARM)


def tree(scene) -> ET.Element:
    return ET.fromstring(scene.to_bytes())


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# -- the style ------------------------------------------------------------------------------------
def test_soft_is_a_registered_portrait_style_on_a_warm_stage():
    assert STYLES["soft"] is SOFT
    assert (SOFT.width, SOFT.height, SOFT.fps, SOFT.timing, SOFT.audio) == (1080, 1920, 30, "clock", None)
    assert SOFT.palettes == (WARM,) and WARM.name == "warm" and WARM.background == "#F3DFCF"
    assert WARM.white == "#FFFFFF" and WARM.ink == "#231E19"
    s = EpisodeSpec(slug="t", title="t", description="t", root=".", seed=1, style=SOFT)
    assert s.palette is WARM and s.background == "#F3DFCF" and s.mouth_style is SOFT_MOUTH
    assert (s.font, s.font_family, s.font_license) == ("assets/fonts/poppins-700.ttf", "Poppins", "OFL-1.1")
    assert SOFT.font.google is not None and SOFT.font.google.css_url.endswith("family=Poppins:wght@700")


def test_an_episode_whose_google_font_is_missing_says_how_to_fetch_it(tmp_path):
    from srstudio import Episode

    (tmp_path / "dialogue.json").write_text(json.dumps({"duration": 1, "phrases": []}))
    spec = EpisodeSpec(slug="t", title="t", description="t", root=tmp_path, seed=1, style=SOFT)
    with pytest.raises(FileNotFoundError, match="srstudio fonts add 'Poppins' --weight 700"):
        Episode(spec)


def test_blob_parts_belong_to_the_soft_style():
    styles = {e.name: e.style for e in registry.entries()}
    assert styles["pip"] == "soft" and styles["soft-office"] == "soft"
    assert {"soft-desk", "soft-chair", "soft-laptop"} <= {e.name for e in registry.entries(style="soft")}


# -- captions ---------------------------------------------------------------------------------------
def test_captions_take_a_text_colour_and_may_drop_the_shadow():
    scene, cv = canvas()
    graphics.captions(cv, [(0, 1, "WORK", "line-1")], color="#111111", stroke="#FFFFFF", shadow=None, y=250)
    text = next(e for e in tree(scene).iter() if local(e.tag) == "text" and e.get("id") == "line-1")
    assert (text.get("color"), text.get("strokeColor")) == ("#111111", "#FFFFFF")
    assert text.get("shadowColor") is None and text.get("shadowBlur") is None
    layer = next(e for e in tree(scene).iter() if e.get("id") == "line-1-caption")
    assert layer.get("y") == "250"


def test_captions_keep_white_text_and_a_shadow_by_default():
    scene, cv = canvas()
    graphics.captions(cv, [(0, 1, "hi", "line-1")])
    text = next(e for e in tree(scene).iter() if local(e.tag) == "text")
    assert text.get("color") == "#FFFFFF" and text.get("shadowColor") == "#00000066"


# -- strokes -----------------------------------------------------------------------------------------
def nums(d: str) -> list[float]:
    return [float(v) for v in d.replace("M", " ").replace("L", " ").replace("Z", " ").split()]


def test_a_stroke_outline_is_a_closed_tapered_body_with_round_caps():
    s = Stroke((0, 0), (100, 0), (200, 0), (300, 0), 60, 20)
    d = s.outline()
    assert d.startswith("M") and d.endswith("Z")
    xy = nums(d)
    xs, ys = xy[0::2], xy[1::2]
    # Caps reach half a width beyond each end; the body is 60 wide at the start and 20 at the end.
    assert min(xs) == pytest.approx(-30, abs=0.2) and max(xs) == pytest.approx(310, abs=0.2)
    assert max(ys) == pytest.approx(30, abs=0.2) and min(ys) == pytest.approx(-30, abs=0.2)
    near_end = [abs(y) for x, y in zip(xs, ys, strict=True) if 299 <= x <= 300.5]
    assert near_end and max(near_end) == pytest.approx(10, abs=0.3)


def test_a_stroke_contour_is_open_at_its_root_so_a_limb_grows_out_of_the_body():
    s = Stroke((0, 0), (100, 0), (200, 0), (300, 0), 60, 20)
    d = s.contour()
    assert d.startswith("M") and "Z" not in d
    xy = nums(d)
    xs, ys = xy[0::2], xy[1::2]
    # It starts and ends on the two sides at the root (x = 0, y = +-30), and wraps the tip (x = 310).
    assert (xs[0], abs(ys[0])) == (pytest.approx(0, abs=0.2), pytest.approx(30, abs=0.2))
    assert (xs[-1], abs(ys[-1])) == (pytest.approx(0, abs=0.2), pytest.approx(30, abs=0.2))
    assert ys[0] == pytest.approx(-ys[-1], abs=0.2)
    assert max(xs) == pytest.approx(310, abs=0.2) and min(xs) == pytest.approx(0, abs=0.2)


def test_strokes_interpolate_and_map_their_points():
    a = Stroke((0, 0), (0, 10), (0, 20), (0, 30), 10, 10)
    b = Stroke((100, 0), (100, 10), (100, 20), (100, 30), 30, 50)
    mid = a.lerp(b, 0.5)
    assert mid.p0 == (50, 0) and mid.p3 == (50, 30) and (mid.w0, mid.w1) == (20, 30)
    assert a.mapped(lambda p: (-p[0] + 1, p[1] * 2)).p3 == (1, 60)


@pytest.mark.parametrize(
    "args, match",
    [
        (((0, 0), (1, 1), (2, 2), (3, 3), 0, 5), "width"),
        (((0, 0), (1, 1), (2, 2), (3, 3), 5, -1), "width"),
        (((0, float("nan")), (1, 1), (2, 2), (3, 3), 5, 5), "finite"),
    ],
)
def test_a_bad_stroke_is_refused(args, match):
    with pytest.raises(BlobError, match=match):
        Stroke(*args)


# -- the pose sheet ------------------------------------------------------------------------------------
def test_every_pose_has_the_same_limbs_so_any_two_interpolate():
    assert {"stand", "sit", "type-a", "type-b", "clasp", "lean", "groove-a", "groove-b", "groove-c", "step"} <= set(
        POSES
    )
    for name, pose in POSES.items():
        assert pose.name == name and set(pose.limbs) == set(LIMBS) and pose.front <= set(ARMS) | set(blob.FEET)
    assert {"open", "happy", "squint", "closed", "wide", "look"} <= set(EYES)
    assert {"smile", "grin", "o", "flat", "sing"} <= set(MOUTHS)


def test_a_pose_missing_a_limb_or_fronting_the_torso_is_refused():
    limbs = dict(POSES["stand"].limbs)
    with pytest.raises(BlobError, match="limbs"):
        Pose("broken", (0, -400), {k: v for k, v in limbs.items() if k != "arm_l"})
    with pytest.raises(BlobError, match="front"):
        Pose("broken", (0, -400), limbs, front=frozenset({"torso"}))
    assert Pose("near leg", (0, -400), limbs, front=frozenset({"leg_l"})).front == {"leg_l"}


def arc_length(s: Stroke, n: int = 60) -> float:
    pts = [s.point(i / n) for i in range(n + 1)]
    return sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:], strict=False))


def test_every_arm_and_leg_keeps_its_length_in_every_pose():
    """A rubber-hose limb may bend, not grow: within -20 %..+25 % of its length standing."""
    stand = POSES["stand"]
    for name, pose in POSES.items():
        for limb in (*ARMS, *blob.FEET):
            ratio = arc_length(pose.limbs[limb]) / arc_length(stand.limbs[limb])
            assert 0.8 <= ratio <= 1.25, (name, limb, round(ratio, 2))


def point_in(poly, x, y) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, [*poly[1:], poly[0]], strict=True):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def world(p) -> tuple[float, float]:
    return blob.SEAT[0] + p[0] * blob.SCALE, blob.SEAT[1] + p[1] * blob.SCALE


def test_seated_at_the_soft_office_the_hands_reach_the_keyboard_and_the_feet_the_floor():
    for name in ("sit", "type-a", "type-b", "nod"):
        pose = POSES[name]
        for arm in ARMS:
            assert point_in(blob.keyboard(), *world(pose.limbs[arm].p3)), (name, arm, world(pose.limbs[arm].p3))
        for leg in blob.FEET:
            s = pose.limbs[leg]
            sole = world((s.p3[0], s.p3[1] + s.w1 / 2))[1]
            assert sole == pytest.approx(blob.SEATED_FLOOR, abs=12), (name, leg, sole)
        # 3/4 view: the near arm and leg are outlined in front, the far arm stays behind the body.
        assert pose.front == {"arm_l", "leg_l"}


def test_seated_the_two_shins_stand_apart_so_the_legs_read_as_two():
    """The near shin is in front of (left of) the far one and the soles do not overlap: a gap shows between them."""
    for name in ("sit", "type-a", "type-b", "nod"):
        near, far = POSES[name].limbs["leg_l"], POSES[name].limbs["leg_r"]
        assert near.p3[0] < far.p3[0], name
        gap = (far.p3[0] - far.w1 / 2) - (near.p3[0] + near.w1 / 2)
        assert gap >= 6, (name, round(gap, 1))


def test_cheering_raises_both_hands_above_the_head_and_waving_only_the_right():
    for name in ("cheer-a", "cheer-b"):
        pose = POSES[name]
        for arm in ARMS:
            assert pose.limbs[arm].p3[1] < pose.head[1], (name, arm)  # the hand is higher than the head's centre
            assert abs(pose.limbs[arm].p3[0] - pose.head[0]) > blob.HEAD, (name, arm)  # beside the head, not on it
        assert pose.front == frozenset(), name  # raised arms cross nothing: they merge into the body
    for name in ("wave-a", "wave-b"):
        pose = POSES[name]
        assert pose.limbs["arm_r"].p3[1] < pose.head[1] < pose.limbs["arm_l"].p3[1], name
        assert pose.front == {"arm_l"}, name  # the lowered arm still crosses the body
    assert POSES["wave-a"].limbs["arm_r"].p3 != POSES["wave-b"].limbs["arm_r"].p3


def test_a_seated_nod_drops_the_head_and_keeps_the_hands_on_the_keyboard():
    sit, nod = POSES["sit"], POSES["nod"]
    assert nod.head[1] > sit.head[1] + 10 and nod.face[1] > sit.face[1]
    assert {a: nod.limbs[a].p3 for a in ARMS} == {a: sit.limbs[a].p3 for a in ARMS}


def test_poses_interpolate_and_place():
    stand, sit = POSES["stand"], POSES["sit"]
    assert stand.lerp(sit, 0) == stand.lerp(stand, 0.3)  # u=0 is the first pose
    half = stand.lerp(sit, 0.5)
    assert half.head == pytest.approx(((stand.head[0] + sit.head[0]) / 2, (stand.head[1] + sit.head[1]) / 2))
    placed = stand.placed(100, 50, turn=0, flip=True)
    assert placed.head == (100 - stand.head[0], 50 + stand.head[1])
    assert placed.limbs["arm_l"].p3[0] == pytest.approx(100 - stand.limbs["arm_l"].p3[0])
    turned = stand.placed(0, 0, turn=90, flip=False)
    assert turned.head == pytest.approx((-stand.head[1], stand.head[0]))


def test_the_silhouette_draws_every_outline_before_any_fill():
    scene, cv = canvas()
    strokes = [Stroke((0, 0), (30, 0), (60, 0), (100, 0), 40, 30), Stroke((0, 0), (0, 30), (0, 60), (0, 100), 60, 50)]
    blob.silhouette(cv, cv.comp, strokes, head=(0, -80, 50))
    shapes = [e for e in tree(scene).iter() if local(e.tag) == "shape"]
    assert len(shapes) == 6
    outline, fill = shapes[:3], shapes[3:]
    assert all(s.get("fill") == WARM.ink for s in outline)
    assert [float(s.get("strokeWidth")) for s in outline[:2]] == [2 * blob.OUTLINE] * 2
    assert all(s.get("fill") == WARM.white and float(s.get("strokeWidth", 0)) == 0 for s in fill)


# -- cues and drawings -------------------------------------------------------------------------------------
def test_cues_hold_and_ease_in_with_in_between_drawings():
    cues = [Cue(0, "stand"), Cue(1, "sit", ease=0.2), Cue(2, "stand")]
    out = blob.drawings(cues, end=3, fps=15)
    times = [d.time for d in out]
    assert times == pytest.approx([0, 0.8, 0.8 + 1 / 15, 0.8 + 2 / 15, 1, 2])
    assert [d.cue.pose for d in out] == ["stand", "sit", "sit", "sit", "sit", "stand"]
    us = [d.u for d in out]
    assert us[0] == 1 and us[4] == 1 and us[5] == 1 and 0 < us[1] < us[2] < us[3] < 1
    # An in-between lies between the two poses it joins.
    stand, sit = POSES["stand"].head, POSES["sit"].head
    lo, hi = sorted((stand[1], sit[1]))
    assert lo < out[2].pose.head[1] < hi


def test_in_betweens_keep_the_old_expression_until_the_new_pose_lands():
    cues = [Cue(0, "stand", eyes="open", mouth="smile"), Cue(1, "clasp", eyes="squint", mouth="grin", ease=0.2)]
    out = blob.drawings(cues, end=2, fps=15)
    assert [(d.face.eyes, d.face.mouth) for d in out] == [("open", "smile")] * 4 + [("squint", "grin")]
    assert [m for _, m in blob.mouth_track(out)] == ["smile"] * 4 + ["grin"]


def face_box(pose: Pose) -> tuple[float, float, float, float]:
    """The eyes-and-mouth region of a placed pose: centre x, centre y, half width, half height."""
    return pose.head[0] + pose.face[0], pose.head[1] + pose.face[1] + 12, 62.0, 58.0


def covers_face(pose: Pose) -> list[str]:
    cx, cy, rx, ry = face_box(pose)
    hits = []
    for arm in sorted(pose.front):
        xy = nums(pose.limbs[arm].outline())
        if any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 1 for x, y in zip(xy[0::2], xy[1::2], strict=True)):
            hits.append(arm)
    return hits


def test_no_arm_in_front_ever_covers_the_face_in_a_pose_or_any_in_between():
    for a in POSES:
        for b in POSES:
            for u in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
                pose = POSES[a].lerp(POSES[b], u)
                assert not covers_face(pose), (a, b, u, covers_face(pose))


def test_an_arm_moving_to_or_from_the_front_travels_behind_the_body():
    clasp, behind = POSES["clasp"], POSES["groove-a"]  # hands clasped in front; hands behind the head
    assert clasp.lerp(behind, 0.3).front == frozenset() == behind.lerp(clasp, 0.7).front
    assert clasp.lerp(clasp, 0.5).front == clasp.front
    assert behind.lerp(clasp, 1.0).front == clasp.front and clasp.lerp(behind, 0.0).front == clasp.front


def limb_length(s: Stroke) -> float:
    return ((s.p3[0] - s.p0[0]) ** 2 + (s.p3[1] - s.p0[1]) ** 2) ** 0.5


def test_a_turn_is_interpolated_as_a_rotation_so_limbs_keep_their_length():
    cues = [Cue(0, "stand"), Cue(1, "stand", turn=60, ease=0.2)]
    mid = blob.drawings(cues, end=2, fps=10)[1]
    assert 0 < mid.u < 1
    for limb in LIMBS:
        assert limb_length(mid.pose.limbs[limb]) == pytest.approx(limb_length(POSES["stand"].limbs[limb]), rel=1e-6)


def test_a_lifted_move_rises_on_an_arc_and_lands_where_it_was_cued():
    flat = blob.drawings([Cue(0, "stand"), Cue(1, "stand", x=300, ease=0.3)], end=2, fps=10)
    arced = blob.drawings([Cue(0, "stand"), Cue(1, "stand", x=300, ease=0.3, lift=40)], end=2, fps=10)
    for f, a in zip(flat, arced, strict=True):
        assert a.pose.head[0] == pytest.approx(f.pose.head[0])
        assert f.pose.head[1] - a.pose.head[1] == pytest.approx(40 * math.sin(math.pi * min(f.u, 1)), abs=1e-6)
    assert arced[-1].pose.head == flat[-1].pose.head


def foot(d, limb: str) -> tuple[float, float]:
    return d.pose.limbs[limb].p3


def test_a_pinned_cue_keeps_the_planted_foot_still_and_solves_the_position():
    cues = [
        Cue(0, "stand", x=100),
        Cue(0.5, "walk-a", pin="leg_l", ease=0.2),
        Cue(1.0, "stride", pin="leg_l", ease=0.2),
        Cue(1.5, "walk-b", pin="leg_r", ease=0.2),
        Cue(2.0, "stand", pin="leg_r", ease=0.2),
    ]
    out = blob.drawings(cues, end=3, fps=15)
    for prev, d in zip(out, out[1:], strict=False):
        planted = d.cue.pin
        assert foot(d, planted) == pytest.approx(foot(prev, planted), abs=1e-6), (d.time, planted)
    # A cycle of the side step travels: the body ends to the right of where it started.
    assert out[-1].pose.head[0] > out[0].pose.head[0] + 100


def test_an_overshoot_lands_past_the_pose_then_settles_one_drawing_later():
    cues = [Cue(0, "stand"), Cue(1, "clasp", ease=0.2, overshoot=0.1)]
    out = blob.drawings(cues, end=2, fps=10)
    key, settle = out[-2], out[-1]
    assert (key.time, key.u) == (pytest.approx(1.0), pytest.approx(1.1))
    assert (settle.time, settle.u) == (pytest.approx(1.1), 1.0)
    assert settle.pose == POSES["clasp"]
    beyond = POSES["stand"].lerp(POSES["clasp"], 1.1)
    assert key.pose.head == pytest.approx(beyond.head)


@pytest.mark.parametrize(
    "cues, match",
    [
        ([Cue(0, "stand", pin="leg_l")], "first cue"),
        ([Cue(0, "stand"), Cue(1, "stand", pin="leg_l", x=5)], "planted foot"),
        ([Cue(0, "stand"), Cue(1, "stand", pin="leg_r", lift=20)], "planted foot"),
        ([Cue(0, "stand"), Cue(1, "stand", pin="arm_l")], "pin"),
        ([Cue(0, "stand"), Cue(1, "stand", overshoot=0.6)], "overshoot"),
        ([Cue(0, "stand"), Cue(1, "stand", overshoot=0.1), Cue(1.05, "sit")], "settle"),
        ([Cue(0, "stand"), Cue(1, "stand", overshoot=0.1)], "settle"),
        ([Cue(0, "stand"), Cue(1, "stand", lift=float("nan"))], "finite"),
    ],
)
def test_bad_pins_overshoots_and_lifts_are_refused(cues, match):
    end = 1.08 if cues[-1].overshoot and len(cues) == 2 else 2
    with pytest.raises(BlobError, match=match):
        blob.drawings(cues, end=end, fps=10)


def test_pip_casts_a_shadow_under_its_feet_on_every_drawing():
    scene, cv = canvas()
    cues = [Cue(0, "stand", x=100), Cue(1, "sit", x=300, y=-200, ease=0.2)]
    blob.pip(cv, cv.comp, cues, end=2, shadow=True)
    root = tree(scene)
    shadow = next(e for e in root.iter() if e.get("id") == "pip-shadow")
    keys = {
        a.get("property"): [(float(k.get("time")), float(k.get("value"))) for k in a if local(k.tag) == "key"]
        for a in shadow
        if local(a.tag) == "animate"
    }
    frames = blob.drawings(cues, end=2)
    for (t, x), d in zip(keys["x"], frames, strict=True):
        feet = [d.pose.limbs[leg].p3 for leg in ("leg_l", "leg_r")]
        assert t == pytest.approx(d.time) and x == pytest.approx(sum(f[0] for f in feet) / 2, abs=1e-3)


@pytest.mark.parametrize(
    "cues, match",
    [
        ([], "at least one"),
        ([Cue(0.5, "stand")], "first cue"),
        ([Cue(0, "stand"), Cue(0, "sit")], "increasing"),
        ([Cue(0, "stand"), Cue(1, "sit"), Cue(0.5, "sit")], "increasing"),
        ([Cue(0, "moonwalk")], "moonwalk"),
        ([Cue(0, "stand", eyes="laser")], "laser"),
        ([Cue(0, "stand", mouth="beak")], "beak"),
        ([Cue(0, "stand"), Cue(4, "sit")], "end"),
        ([Cue(0, "stand", x=float("inf"))], "finite"),
        ([Cue(0, "stand"), Cue(1, "sit", ease=1.5)], "ease"),
        ([Cue(0, "stand"), Cue(1, "sit", ease=-0.1)], "ease"),
    ],
)
def test_bad_cues_are_refused(cues, match):
    with pytest.raises(BlobError, match=match):
        blob.drawings(cues, end=4)


@pytest.mark.parametrize("bad", [0, -15, float("nan"), float("inf"), True])
def test_a_performance_needs_a_positive_fps_and_end(bad):
    with pytest.raises(BlobError, match=r"fps must be a positive number"):
        blob.drawings([Cue(0, "stand")], end=4, fps=bad)
    with pytest.raises(BlobError, match=r"end must be a positive number"):
        blob.drawings([Cue(0, "stand")], end=bad)


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf"), True])
def test_a_blob_needs_a_positive_scale(scale):
    _, cv = canvas()
    with pytest.raises(BlobError, match="scale must be a positive number"):
        blob.pip(cv, cv.comp, [Cue(0, "stand")], end=4, scale=scale)


def test_singing_needs_mouth_states_on_the_episode_frames():
    _, cv = canvas()
    with pytest.raises(BlobError, match="mouth states"):
        blob.pip(cv, cv.comp, [Cue(0, "stand", mouth="sing")], end=4)
    with pytest.raises(BlobError, match="unknown mouth state 'yawn'"):
        blob.pip(cv, cv.comp, [Cue(0, "stand", mouth="sing")], end=4, mouth_states=[(0, "yawn")])


def test_mouth_track_follows_the_song_only_while_a_cue_sings():
    cues = [Cue(0, "stand", mouth="grin"), Cue(1, "stand", mouth="sing"), Cue(2, "stand", mouth="o")]
    states = [(f / 10, "open" if f % 2 else "rest") for f in range(30)]
    track = blob.mouth_track(blob.drawings(cues, end=3), states)
    at = dict(track)
    assert at[0.0] == "grin" and at[1.0] == "smile" and at[1.1] == "grin" and at[2.0] == "o"
    assert all(shape == "grin" for t, shape in track if t < 1)


def test_pip_is_one_rig_whose_paths_change_on_every_drawing():
    scene, cv = canvas()
    cues = [Cue(0, "stand"), Cue(1, "sit", ease=0.2, x=50), Cue(2, "clasp", eyes="squint", mouth="grin")]
    blob.pip(cv, cv.comp, cues, end=3, x=540, y=1500)
    root = tree(scene)
    times = [round(d.time, 6) for d in blob.drawings(cues, end=3)]
    rig = next(e for e in root.iter() if e.get("id") == "pip")
    keyed = [a for a in rig.iter() if local(a.tag) == "animate" and a.get("property") == "path"]
    fronted = set().union(*(POSES[c.pose].front for c in cues))
    assert len(keyed) == len(LIMBS) * 2 + len(fronted) * 2  # every limb in both passes, plus each fronted limb
    for a in keyed:
        assert [float(k.get("time")) for k in a] == pytest.approx(times)
    clasp_front = [a for a in rig.iter() if local(a.tag) == "animate" and a.get("property") == "opacity"]
    assert clasp_front, "the clasped arms swap from the back pass to the front pass"


def test_a_front_limb_is_filled_then_traced_with_an_open_root():
    scene, cv = canvas()
    cues = [Cue(0, "sit"), Cue(1, "clasp", ease=0.2)]
    blob.pip(cv, cv.comp, cues, end=2)
    root = tree(scene)
    for limb in ("arm_l", "leg_l"):
        g = next(e for e in root.iter() if e.get("id") == f"pip-front-{limb}")
        shapes = [e for e in g if local(e.tag) == "shape"]
        assert len(shapes) == 2
        fill, trace = shapes
        assert fill.get("fill") == WARM.white and (fill.get("strokeWidth") in (None, "0"))
        assert trace.get("stroke") == WARM.ink and trace.get("fill") == WARM.clear
        assert "Z" not in trace.get("path") and fill.get("path").rstrip().endswith("Z")


def test_standing_arms_are_drawn_over_the_body_so_they_never_melt_into_it():
    for name in ("stand", "step", "clasp", "walk-a", "stride", "walk-b"):
        assert POSES[name].front == set(ARMS), name


def test_pip_shows_one_face_at_a_time_on_the_engine(tmp_path):
    scene, cv = canvas(duration=4)
    states = [(f / 10, "open" if 25 <= f < 30 else "rest") for f in range(40)]
    cues = [
        Cue(0, "stand"),
        Cue(1, "sit", x=100, ease=0.2),
        Cue(2, "clasp", eyes="squint", mouth="sing"),
        Cue(3, "stand"),
    ]
    blob.pip(cv, cv.comp, cues, end=4, x=540, y=1500, mouth_states=states)
    doc = tmp_path / "pip.scene.xml"
    doc.write_bytes(scene.to_bytes())
    for frame, eyes, mouth in [
        (5, "open", "smile"),
        (15, "open", "smile"),
        (22, "squint", "smile"),
        (27, "squint", "grin"),
        (35, "open", "smile"),
    ]:
        out = subprocess.run(
            [str(engine()), "eval", str(doc), "--frame", str(frame), "--json"], capture_output=True, text=True
        )
        assert out.returncode == 0, out.stderr
        nodes = json.loads(out.stdout)["result"]["nodes"]
        shown = {n["id"] for n in nodes if n.get("draw") and n.get("world_opacity", 1) > 0}
        assert {i for i in shown if i.startswith("pip-eyes-")} == {f"pip-eyes-{eyes}"}, frame
        assert {i for i in shown if i.startswith("pip-mouth-")} == {f"pip-mouth-{mouth}"}, frame


def test_squinting_eyes_point_inward_like_a_wince():
    scene, cv = canvas()
    blob.EYES["squint"](cv, cv.comp, 0, 0)
    paths = [e.get("path") for e in tree(scene).iter() if local(e.tag) == "shape"]
    xs = [nums(d)[0::2] for d in paths]
    (lb, ltip, _), (rb, rtip, _) = xs
    assert ltip > lb and rtip < rb  # the left eye reads ">", the right "<"
    assert ltip < 0 < rtip


def test_the_soft_office_holds_chair_desk_laptop_and_the_signature():
    from srstudio import Signature

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=2, background=WARM.background)
    cv = Canvas(scene, WARM, signature=Signature())
    blob.office(cv, cv.comp, shots=[(0, 1)])
    root = tree(scene)
    ids = {e.get("id") for e in root.iter()}
    assert {"soft-office", "soft-chair", "soft-desk", "soft-laptop", "sig-cactus", "sig-code"} <= ids
    office = next(e for e in root.iter() if e.get("id") == "soft-office")
    assert [k.get("value") for k in office.iter() if local(k.tag) == "key"][:2] == ["1", "0"]  # gated to its shot
    for part in ("soft-chair", "soft-desk"):
        group = next(e for e in root.iter() if e.get("id") == part)
        assert all(s.get("stroke") == blob.WOOD_LINE for s in group.iter() if local(s.tag) == "shape")


# -- looks: one rig, several characters ------------------------------------------------------------
def test_pip_is_the_default_look_and_a_look_checks_its_colours():
    assert blob.PIP.name == "pip" and blob.PIP.fill is None and blob.PIP.topper is not None
    with pytest.raises(BlobError, match="colour"):
        blob.Look("x", fill="blue")
    with pytest.raises(BlobError, match="colour"):
        blob.Look("x", blush="#12")
    with pytest.raises(BlobError, match="name"):
        blob.Look("Two Words")


def test_bo_is_a_registered_soft_character_on_the_same_rig_with_his_own_look():
    entry = registry.get("character", "bo")
    assert entry.style == "soft" and entry.builder is blob.bo
    scene, cv = canvas()
    cues = [Cue(0, "stand"), Cue(1, "sit", ease=0.2, x=40), Cue(2, "wave-a", eyes="happy", mouth="grin")]
    blob.bo(cv, cv.comp, cues, end=3, x=540, y=1500)
    root = tree(scene)
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    assert {"bo", "bo-outline", "bo-fill", "bo-hair", "bo-glasses", "bo-face"} <= ids
    assert not any(i.startswith("pip") for i in ids)
    fill_pass = next(e for e in root.iter() if e.get("id") == "bo-fill")
    fills = {s.get("fill") for s in fill_pass.iter() if local(s.tag) == "shape"}
    assert fills == {blob.BO.fill}, "every limb and the head are filled in Bo's body colour"
    face = next(e for e in root.iter() if e.get("id") == "bo-face")
    assert not [s for s in face if local(s.tag) == "shape" and s.get("fill") == blob.BLUSH], "Bo does not blush"
    keyed = [a for a in root.iter() if local(a.tag) == "animate" and a.get("property") == "path"]
    times = [round(d.time, 6) for d in blob.drawings(cues, end=3)]
    assert keyed and all([float(k.get("time")) for k in a] == pytest.approx(times) for a in keyed)


def test_pip_and_bo_share_a_scene_without_an_id_clash_and_it_validates():
    scene, cv = canvas()
    blob.pip(cv, cv.comp, [Cue(0, "stand")], end=3, x=300, y=1500, scale=0.8)
    blob.bo(cv, cv.comp, [Cue(0, "clasp", eyes="look", flip=True)], end=3, x=780, y=1500, scale=0.8, shadow=True)
    ids = [e.get("id") for e in tree(scene).iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_bos_hairline_climbs_from_above_the_ear_on_the_parted_side():
    scene, cv = canvas()
    g = cv.group(cv.comp, "hair")
    blob._side_part(cv, g, blob.HEAD)
    (d,) = [e.get("path") for e in tree(scene).iter() if e.get("shape") == "path"]
    points = [tuple(map(float, p.split())) for p in re.findall(r"-?[\d.]+ -?[\d.]+", d)]
    parted = [(x, y) for x, y in points if x > 0]
    assert parted and max(y for _, y in parted) < -0.15 * blob.HEAD  # no edge dropping down the cheek


# -- polished looks: Juno and Remy ---------------------------------------------------------------------
NEW_LOOKS = {"juno": (blob.juno, blob.JUNO), "remy": (blob.remy, blob.REMY)}
PUPILS = ("open", "look", "wide")


def shapes(element) -> list[ET.Element]:
    return [s for s in element.iter() if local(s.tag) == "shape"]


def by_id(root, id) -> ET.Element:
    return next(e for e in root.iter() if e.get("id") == id)


def test_a_look_checks_its_shade_colour():
    with pytest.raises(BlobError, match="shade"):
        blob.Look("x", shade="grey")


@pytest.mark.parametrize("name", sorted(NEW_LOOKS))
def test_juno_and_remy_are_registered_soft_characters_on_the_rig(name):
    builder, look = NEW_LOOKS[name]
    entry = registry.get("character", name)
    assert entry.style == "soft" and entry.builder is builder
    assert look.shade and look.catchlights and look.fill not in (None, blob.BO.fill)
    scene, cv = canvas()
    cues = [Cue(0, "stand"), Cue(1, "sit", ease=0.2, x=40), Cue(2, "cheer-a", eyes="happy", mouth="sing")]
    builder(cv, cv.comp, cues, end=3, x=540, y=1500, mouth_states=[(0, "rest"), (2.1, "open")], shadow=True)
    root = tree(scene)
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids)) and not any(i.startswith(("pip", "bo")) for i in ids)
    assert {name, f"{name}-outline", f"{name}-fill", f"{name}-hair", f"{name}-face", f"{name}-{look.topper_id}"} <= set(
        ids
    )
    fills = {s.get("fill") for s in shapes(by_id(root, f"{name}-fill"))}
    assert look.fill in fills and look.shade in fills, "the head is shaded in the character's own shade"
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_the_shade_is_a_crescent_inside_the_head_on_the_side_away_from_the_light():
    r, dx, dy = blob.HEAD, -0.16 * blob.HEAD, -0.2 * blob.HEAD
    d = blob._crescent(r, dx, dy)
    assert d.startswith("M ") and d.endswith(" Z")
    points = [tuple(map(float, p.split())) for p in re.findall(r"-?[\d.]+ -?[\d.]+", d)]
    assert len(points) > 20
    for x, y in points:
        assert math.hypot(x, y) <= r + 0.05, (x, y)  # inside the head
        assert math.hypot(x - dx, y - dy) >= r - 0.05, (x, y)  # outside the lit disc
    cx, cy = sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)
    assert cx > 0 and cy > 0, "light from the upper left: the shade sits lower right"


@pytest.mark.parametrize("bad", [(0.0, 0.0), (2.0 * blob.HEAD, 0.0), (math.nan, 0.0)])
def test_a_crescent_needs_the_lit_disc_moved_by_less_than_its_diameter(bad):
    with pytest.raises(BlobError, match="crescent"):
        blob._crescent(blob.HEAD, *bad)


def eye_shapes(look, kind) -> list[ET.Element]:
    scene, cv = canvas()
    blob.blob(cv, cv.comp, [Cue(0, "stand", eyes=kind)], end=1, id="c", look=look)
    return shapes(by_id(tree(scene), f"c-eyes-{kind}"))


@pytest.mark.parametrize("kind", sorted(EYES))
def test_lashes_follow_every_eye_and_catchlights_only_eyes_with_pupils(kind):
    plain, polished = eye_shapes(blob.PIP, kind), eye_shapes(blob.JUNO, kind)
    lashes = [s for s in polished if s.get("shape") == "path"][-4:]
    assert len(polished) > len(plain)
    assert all(s.get("stroke") == WARM.ink for s in lashes)
    lights = [
        s
        for s in polished
        if s.get("fill") == WARM.white and s.get("shape") == "ellipse" and s.get("strokeWidth") == "0"
    ]
    assert len(lights) == (4 if kind in PUPILS else 0)


def test_pip_and_bo_draw_no_polish_so_their_episodes_stay_as_they_were():
    for look in (blob.PIP, blob.BO):
        assert look.shade is None and not look.gloss and not look.catchlights and not look.lashes
        for kind in EYES:
            assert all(s.get("strokeWidth") != "0" or s.get("fill") == WARM.ink for s in eye_shapes(look, kind))


def test_the_whole_cast_shares_one_scene_without_an_id_clash():
    scene, cv = canvas()
    for i, builder in enumerate((blob.pip, blob.bo, blob.juno, blob.remy)):
        builder(cv, cv.comp, [Cue(0, "wave-a", eyes="look", mouth="grin")], end=3, x=150 + 260 * i, y=1500, scale=0.6)
    ids = [e.get("id") for e in tree(scene).iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    assert [f for f in scene.check() if f.severity == "error"] == []


# -- the soft home: a sofa to lounge on ------------------------------------------------------------
def sofa_world(p) -> tuple[float, float]:
    return blob.SOFA_SEAT[0] + p[0] * blob.SCALE, blob.SOFA_SEAT[1] + p[1] * blob.SCALE


def test_the_home_parts_are_registered_soft_and_lounge_is_a_seated_pose():
    styles = {e.name: e.style for e in registry.entries()}
    assert styles["soft-home"] == styles["soft-sofa"] == "soft"
    assert POSES["lounge"].front == POSES["sit"].front == {"arm_l", "leg_l"}


def test_lounging_on_the_sofa_the_hip_is_on_the_cushion_the_soles_on_the_floor_the_hands_on_the_lap():
    for name in ("sit", "lounge"):
        pose = POSES[name]
        assert point_in(blob.sofa_seat(), *blob.SOFA_SEAT)
        for leg in blob.FEET:
            s = pose.limbs[leg]
            sole = sofa_world((s.p3[0], s.p3[1] + s.w1 / 2))[1]
            assert sole == pytest.approx(blob.SOFA_FLOOR, abs=12), (name, leg, sole)
    thigh = POSES["lounge"].limbs["leg_l"]
    for arm in ARMS:
        hand = POSES["lounge"].limbs[arm].p3
        gap = min(math.dist(hand, thigh.point(i / 40)) for i in range(41))
        assert gap < thigh.w0 / 2 + 6, (arm, hand, gap)  # resting on the near thigh, not hovering over a keyboard


def test_the_soft_home_seats_a_character_between_the_sofas_seat_and_its_near_arm():
    from srstudio import Signature

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=2, background=WARM.background)
    cv = Canvas(scene, WARM, signature=Signature())
    blob.home(cv, cv.comp, shots=[(0, 1)], on_sofa=lambda g: blob.pip(cv, g, [Cue(0, "lounge")], end=2))
    root = tree(scene)
    order = [e.get("id") for e in root.iter() if e.get("id")]
    assert {"soft-home", "soft-sofa", "sig-cactus", "sig-code"} <= set(order)
    assert order.index("soft-sofa-seat") < order.index("pip") < order.index("soft-sofa-arm-near")
    home = next(e for e in root.iter() if e.get("id") == "soft-home")
    assert [k.get("value") for k in home.iter() if local(k.tag) == "key"][:2] == ["1", "0"]
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_the_sofa_alone_has_no_slot_and_still_draws_its_near_arm_last():
    scene, cv = canvas()
    blob.sofa(cv, cv.comp)
    order = [e.get("id") for e in tree(scene).iter() if e.get("id")]
    assert order.index("soft-sofa-seat") < order.index("soft-sofa-arm-near")


def test_the_sofas_front_stands_on_the_floor_the_seated_soles_meet():
    """The seat's front face drops to the line under the soles, so a seated character's feet are on the floor."""
    scene, cv = canvas()
    blob.sofa(cv, cv.comp)
    seat = next(e for e in tree(scene).iter() if e.get("id") == "soft-sofa-seat")
    (front,) = [e.get("path") for e in seat.iter() if e.get("shape") == "path" and e.get("fill") == blob.FABRIC_SIDE]
    _, _, near, far = [tuple(map(float, p.split())) for p in re.findall(r"-?[\d.]+ -?[\d.]+", front)][:4]
    x = blob.SOFA_SEAT[0] - 110  # the front edge on the hip's line along the sofa
    bottom = far[1] + (near[1] - far[1]) * (x - far[0]) / (near[0] - far[0])
    assert bottom + 18 == pytest.approx(blob.SOFA_FLOOR, abs=12)  # 18: the sofa's feet


# -- polished rooms: the meeting room and the break room ---------------------------------------------------
ROOMS = {"soft-meeting-room": "meeting_room", "soft-break-room": "break_room"}


def signed_canvas() -> tuple[Scene, Canvas]:
    from srstudio import Signature

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=2, background=WARM.background)
    return scene, Canvas(scene, WARM, signature=Signature())


def test_the_rooms_and_their_furniture_are_registered_soft_parts():
    entries = {(e.kind, e.name): e for e in registry.entries()}
    for name, fn in ROOMS.items():
        assert entries[("location", name)].style == "soft" and entries[("location", name)].builder is getattr(blob, fn)
    for prop in ("soft-swivel-chair", "soft-stool", "soft-coffee-machine", "soft-fridge"):
        assert entries[("prop", prop)].style == "soft", prop


def test_a_room_point_on_either_wall_meets_the_floor_on_the_wall_base():
    for a in range(-330, int(blob.CORNER) + 1, 50):
        x, y = blob.room_point(a)
        assert blob.wall_base(x) == pytest.approx(y)
    for c in range(0, 300, 50):
        x, y = blob.room_point(blob.CORNER, c)
        assert blob.wall_base(x) == pytest.approx(y)
    corner = blob.room_point(blob.CORNER)
    assert blob.wall_base(corner[0] - 1) < corner[1] + 1 and blob.wall_base(corner[0] + 1) > corner[1]


def test_every_place_a_character_stands_or_sits_is_on_the_floor_in_front_of_the_walls():
    for x in range(0, 1081, 40):
        assert blob.wall_base(x) < blob.SEATED_FLOOR < blob.FLOOR
    assert blob.wall_base(blob.BREAK_STAND[0]) < blob.BREAK_STAND[1] == blob.FLOOR


@pytest.mark.parametrize("name", sorted(ROOMS))
def test_a_room_is_walls_floor_light_and_furniture_gated_to_its_shots_and_signed(name):
    scene, cv = signed_canvas()
    getattr(blob, ROOMS[name])(cv, cv.comp, shots=[(0, 1)])
    root = tree(scene)
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    assert {name, f"{name}-walls", f"{name}-floor", f"{name}-light", "sig-cactus", "sig-code"} <= set(ids)
    assert ids.index(f"{name}-walls") < ids.index(f"{name}-floor") < ids.index(f"{name}-light")
    room = by_id(root, name)
    assert [k.get("value") for k in room.iter() if local(k.tag) == "key"][:2] == ["1", "0"]
    light = shapes(by_id(root, f"{name}-light"))
    assert light and all(0 < float(s.get("opacity")) < 0.5 for s in light), "light is a glaze, not paint"
    assert [f for f in scene.check() if f.severity == "error"] == []


@pytest.mark.parametrize("name", ["office", "home", "meeting_room", "break_room"])
def test_a_location_drawn_twice_namespaces_the_second_ones_furniture(name):
    scene, cv = canvas()
    getattr(blob, name)(cv, cv.comp)
    first = [e.get("id") for e in tree(scene).iter() if e.get("id")]
    getattr(blob, name)(cv, cv.comp, id="again")
    ids = [e.get("id") for e in tree(scene).iter() if e.get("id")]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})
    named = [i for i in ids[len(first) :] if not re.fullmatch(r"[a-z]+-\d+", i)]  # cv.uid names are unique already
    assert named and all(i.startswith("again") for i in named), named


def test_wall_decor_stays_below_the_captions_and_on_its_wall():
    for name, (wall, a0, a1, u0, u1) in blob.WALL_DECOR.items():
        corners = blob.wall_quad(wall, a0, a1, u0, u1)
        assert all(y >= blob.CAPTION_FLOOR for _, y in corners), name
        assert all(0 <= x <= 1080 for x, _ in corners), name
        span = (-blob.ROOM[0], blob.CORNER) if wall == "back" else (0, 1080 - blob.ROOM[0] - blob.CORNER)
        assert span[0] <= a0 < a1 <= span[1], name


def test_the_fridge_top_stays_below_the_captions_and_in_frame():
    a0, a1, c0, c1, height = blob.FRIDGE_BOX
    top = [blob.room_point(a, c, height) for a in (a0, a1) for c in (c0, c1)]
    assert all(y >= blob.CAPTION_FLOOR for _, y in top)
    assert all(0 <= x <= 1080 for x, _ in top)


def test_the_meeting_table_takes_the_laptop_and_the_swivel_chair_the_seated_hip():
    top = blob.meeting_table_top()
    assert all(point_in(top, x, y) for x, y in blob.keyboard()), "a seated pose types on the table"
    assert point_in(blob.swivel_seat(), *blob.SEAT)


def test_the_stool_seats_the_hip_at_the_chairs_height_and_its_base_on_the_floor_the_soles_meet():
    cx, cy, rx, ry = blob.STOOL_TOP
    hx, hy = blob.SEAT
    assert ((hx - cx) / rx) ** 2 + ((hy - cy) / ry) ** 2 < 1
    assert blob.STOOL_FLOOR == pytest.approx(blob.SEATED_FLOOR, abs=25)


def test_the_meeting_room_seats_a_character_on_the_swivel_chair_and_validates():
    scene, cv = signed_canvas()
    blob.meeting_room(cv, cv.comp)
    blob.juno(
        cv,
        cv.comp,
        [Cue(0, "type-a", x=blob.SEAT[0] / blob.SCALE, y=blob.SEAT[1] / blob.SCALE)],
        end=2,
        scale=blob.SCALE,
    )
    blob.break_room(cv, cv.comp, id="other-room")
    assert [f for f in scene.check() if f.severity == "error"] == []


def opacity_keys(el) -> list[tuple[float, float]]:
    return [
        (float(k.get("time")), float(k.get("value")))
        for a in el.iter()
        if local(a.tag) == "animate" and a.get("property") == "opacity"
        for k in a.iter()
        if local(k.tag) == "key"
    ]


def test_the_home_lamp_glows_while_it_talks_and_stays_plain_by_default():
    scene, cv = canvas()
    blob.home(cv, cv.comp, lamp_talk=[(0.5, 1.2), (2.0, 2.6)])
    lamp = next(e for e in tree(scene).iter() if e.get("id") == "soft-home-lamp-talk")
    assert opacity_keys(lamp) == [(0, 0), (0.5, 1), (1.2, 0), (2.0, 1), (2.6, 0)]
    plain, cv = canvas()
    blob.home(cv, cv.comp)
    assert "soft-home-lamp-talk" not in {e.get("id") for e in tree(plain).iter()}
    x, y = blob.LAMP_SHADE
    assert 300 < x < 700 and 400 < y < 900  # the shade's centre, for a camera to frame


@pytest.mark.parametrize("spans", [[(1.0, 1.0)], [(-0.2, 0.4)], [(0.5, 1.0), (0.9, 1.4)]])
def test_lamp_talk_spans_out_of_order_or_empty_are_refused(spans):
    _, cv = canvas()
    with pytest.raises(BlobError, match="lamp_talk"):
        blob.home(cv, cv.comp, lamp_talk=spans)
