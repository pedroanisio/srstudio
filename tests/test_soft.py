"""The Soft style: its palette and frame, top captions, and the pose-sheet blob character."""

import json
import math
import os
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
