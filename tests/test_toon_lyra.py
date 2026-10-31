"""Lyra, the owl presenter (ADR 0063): her moods and eye poses as typed data, her beak for lip sync, the head rig
measured at its bounds, and all of it held at ``proposed``."""

import math
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import (
    PEACH,
    Canvas,
    brush,
    flat_counter,
    parts,
    registry,
    sketch,
    specimens,
    styles,
    toon,
    toon_cast,
    toon_head,
    toon_lyra,
    toon_orbit,
    toon_rigs,
)
from srstudio.head_motion import limit
from srstudio.toon import Pose, ToonDataError
from srstudio.toon_torso import depth_in

MOODS = ("welcome", "curiosity", "doubt", "delight", "focus", "wonder")
EYE_POSES = ("camera", "left", "right", "up", "down", "near", "half", "closed")


def stage(seconds: float = 8.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("l"))


# -- the data ----------------------------------------------------------------------------------------------------------
def test_there_are_six_moods_and_eight_eye_poses_in_the_order_they_were_drawn():
    assert tuple(toon_lyra.MOODS) == MOODS
    assert tuple(toon_lyra.EYE_POSES) == EYE_POSES


def test_each_mood_holds_the_values_it_was_drawn_with():
    doubt = toon_lyra.mood("doubt")
    assert (doubt.eyes.gaze, doubt.eyes.lids, doubt.eyes.brows, doubt.eyes.angles) == (
        (0.9, 0.0),
        (0.47, 0.12),
        (12.0, -22.0),
        (-7.0, 9.0),
    )
    assert (doubt.beak, doubt.tilt) == ("closed", 5.0)
    assert toon_lyra.mood("delight").eyes.bottom == 0.44
    wonder = toon_lyra.mood("wonder")
    assert (wonder.eyes.pupil, wonder.eyes.tall) == (1.15, 84.0)
    assert toon_lyra.mood("focus").eyes.angles == (16.0, -16.0)


@pytest.mark.parametrize("name", ["", "Welcome", "sulk", "left"])
def test_an_unknown_mood_is_refused_by_name(name):
    with pytest.raises(ToonDataError, match=r"no mood .*welcome"):
        toon_lyra.mood(name)


def test_an_unknown_eye_pose_is_refused_by_name():
    with pytest.raises(ToonDataError, match=r"no eye pose 'wonder'.*camera"):
        toon_lyra.eye_pose("wonder")


def test_a_drawing_asked_for_an_unknown_mood_refuses_it():
    look = toon_lyra.LYRA
    with pytest.raises(ToonDataError, match="no eyes 'sulk'"):
        look.drawing.eye(look, look.eyes[0], "sulk", 1.0)
    with pytest.raises(ToonDataError, match="no beak 'sulk'"):
        look.drawing.mouth(look, "sulk")


@pytest.mark.parametrize(
    "bad",
    [
        {"gaze": (2.0, 0.0)},
        {"gaze": (math.nan, 0.0)},
        {"lids": (1.2, 0.0)},
        {"bottom": -0.1},
        {"pupil": 0.0},
        {"tall": 10.0},
        {"blink": 2.0},
    ],
)
def test_eyes_out_of_range_are_refused(bad):
    with pytest.raises(ToonDataError):
        toon_lyra.Eyes(**bad)


@pytest.mark.parametrize(
    ("kw", "message"),
    [({"beak": "grin"}, "no beak"), ({"tilt": 40.0}, "tilt"), ({"tilt": math.inf}, "tilt"), ({"name": ""}, "name")],
)
def test_a_mood_out_of_range_is_refused(kw, message):
    good = {"name": "x", "eyes": toon_lyra.Eyes(), "beak": "talk", "tilt": 0.0}
    with pytest.raises(ToonDataError, match=message):
        toon_lyra.Mood(**{**good, **kw})


def test_a_beak_with_a_gape_out_of_range_is_refused():
    with pytest.raises(ToonDataError):
        toon_lyra.Beak("x", (0.0, 10.0))


def test_the_near_pose_crosses_her_eyes():
    near = toon_lyra.eye_pose("near").eyes
    assert near.near
    left = toon_lyra.iris_of(near, 0, (0.0, 0.0))
    right = toon_lyra.iris_of(near, 1, (0.0, 0.0))
    assert left[0] > 219.0 and right[0] < 380.0


def test_a_gaze_never_leaves_the_almond():
    for name in toon_lyra.MOODS:
        for side in (0, 1):
            x, y = toon_lyra.iris_of(toon_lyra.mood(name).eyes, side, (0.42, 0.04))
            assert math.hypot(x - (219.0, 380.0)[side], y - 290.0) <= 27.0 + 1e-6


# -- the drawing -------------------------------------------------------------------------------------------------------
def test_every_shared_expression_draws_and_each_of_hers_differs_from_the_rest():
    look = toon_lyra.LYRA
    for kind in (*toon.EYES, *MOODS, *EYE_POSES):
        assert look.drawing.eye(look, look.eyes[0], kind, 1.0)
    for kind in (*toon.MOUTHS, *MOODS):
        assert look.drawing.mouth(look, kind)
    faces = {tuple(look.drawing.eye(look, look.eyes[0], m, 1.0)) for m in MOODS}
    assert len(faces) == len(MOODS)
    poses = {tuple(look.drawing.eye(look, look.eyes[0], e, 1.0)) for e in EYE_POSES}
    assert len(poses) == len(EYE_POSES)


def test_every_shared_arm_pose_draws():
    for arms in toon.ARMS:
        under, over = toon_cast._arms(toon_lyra.LYRA, arms, 0)
        assert under or over


def test_her_shared_contract_holds_outside_her_rig():
    under, mouth, over = toon_cast.figure_layers(toon_lyra.LYRA, "wide", "open", "desk")
    assert under and mouth and not over


@pytest.mark.parametrize("viseme", ["open", "round", "teeth"])
def test_each_viseme_opens_the_beak_and_keeps_the_beak_drawn(viseme):
    look = toon_lyra.LYRA
    drawn = look.drawing.viseme(look, viseme)
    closed = look.drawing.mouth(look, "flat")
    assert len(drawn) > len(closed)
    assert drawn[-2:] == closed[-2:]  # the upper beak stays, over the gape


def test_a_viseme_that_is_not_one_is_refused():
    with pytest.raises(ToonDataError, match="no viseme"):
        toon_lyra.LYRA.drawing.viseme(toon_lyra.LYRA, "grin")


def test_the_visemes_differ_from_each_other():
    look = toon_lyra.LYRA
    assert len({tuple(look.drawing.viseme(look, v)) for v in ("open", "round", "teeth")}) == 3


def test_she_fits_the_frame_from_her_tufts_to_her_feet():
    layers = toon_lyra.LYRA.drawing.foundation(toon_lyra.LYRA)
    edges = [brush.bounds(shape) for shape, _ in layers]
    assert min(e[0] for e in edges) >= 0.0
    assert max(e[2] for e in edges) <= toon.REF_W
    assert min(e[1] for e in edges) >= toon.REF_TOP
    assert max(e[3] for e in edges) <= 1122.0


def test_a_mouth_she_speaks_with_sits_on_the_beak():
    x, y = toon_lyra.LYRA.mouth
    assert depth_in(toon_lyra.LYRA.silhouette, (x, y))[0] > 0.0


def test_her_colours_stay_hers_on_any_palette():
    colours = {c for _, c in toon_lyra.LYRA.drawing.foundation(toon_lyra.LYRA)}
    assert colours <= {*toon_lyra.PALETTE}
    assert "ink" not in colours and "white" not in colours


# -- the rig -----------------------------------------------------------------------------------------------------------
def test_the_seam_holds_with_the_head_at_every_bound_measured_from_the_covers_ends():
    assert toon_lyra.LYRA_RIG.free == 0.0
    assert toon_head.open_seam(toon_lyra.LYRA_RIG) == []


def test_the_seam_stops_holding_if_the_head_is_lifted():
    high = replace(toon_lyra.LYRA_RIG, head=tuple((x, y - 90.0) for x, y in toon_lyra.LYRA_RIG.head))
    assert toon_head.open_seam(high)


def test_the_chin_overlaps_the_scarf_at_the_highest_the_head_reaches():
    rig = toon_lyra.LYRA_RIG
    highest = min(drop for _, drop in toon_head._bounds(rig))
    chin = max(y for _, y in rig.head)
    scarf = toon_lyra.SCARF_TOP
    assert chin + highest > scarf + 10.0


def test_every_mood_turn_lies_inside_what_the_seam_was_measured_for():
    rig = toon_lyra.LYRA_RIG
    style = rig.style
    swing = limit(style, "turn") + limit(style, "roll") + limit(style, "idle_roll")
    for name in MOODS:
        assert abs(toon_lyra.mood(name).tilt - rig.tilt) <= swing


def test_the_rig_turns_nothing_twice():
    assert toon_lyra.LYRA_RIG.look.drawing.tilt == 0.0
    assert toon_lyra.LYRA_RIG.tilt == toon_lyra.mood("welcome").tilt


def test_the_mood_plan_turns_her_head_to_each_mood_and_an_eye_pose_levels_it():
    poses = [toon_lyra.pose(0.0, "welcome"), toon_lyra.pose(2.0, "doubt"), toon_lyra.pose(4.0, "near")]
    plan = toon_lyra.mood_plan(poses, 6.0)
    keys = dict(plan.turn.keys)
    rest = toon_lyra.LYRA_RIG.tilt
    assert keys[0.0] == 0.0
    assert keys[round(2.0 + toon_lyra.TURN_SECONDS, 6)] == 5.0 - rest
    assert keys[round(4.0 + toon_lyra.TURN_SECONDS, 6)] == 0.0 - rest


def test_a_pose_in_an_unknown_mood_is_refused():
    with pytest.raises(ToonDataError, match="no mood or eye pose"):
        toon_lyra.pose(0.0, "sulk")


def test_a_mood_plan_with_no_poses_is_refused():
    with pytest.raises(ToonDataError):
        toon_lyra.mood_plan([], 4.0)


def test_she_glances_with_her_pupils_and_not_past_her_almond():
    drawing = toon_lyra.LYRA_RIG.look.drawing
    assert isinstance(drawing, toon_head.Glancing)
    assert drawing.looking(0.42, 0.04).glance == (0.42, 0.04)


def test_moods_and_eye_poses_draw_in_one_figure_through_the_rig():
    cv = stage()
    poses = [Pose(float(i) / 2, m, m, "desk") for i, m in enumerate(MOODS)]
    poses += [Pose(3.0 + i / 4, e, "talk", "desk") for i, e in enumerate(EYE_POSES)]
    plan = toon_lyra.mood_plan(poses, 8.0)
    assert toon_head.figure(cv, cv.comp, toon_lyra.LYRA_RIG, poses, 8.0, plan) is not None


def test_a_clip_can_reach_the_rig_directly_but_a_reel_is_refused_it():
    assert toon_rigs.RIGS["toon-lyra"] is toon_lyra.LYRA_RIG
    with pytest.raises(parts.NotApprovedError):
        toon_rigs.rig_of("toon-lyra")


def test_she_lip_syncs_through_the_shared_track():
    cv = stage()
    toon_lyra.lyra(cv, cv.comp, [Pose(0.0, "wide", "flat", "desk")], 4.0, mouths=[(0.5, "open"), (1.0, "closed")])
    assert b"opacity" in cv.scene.to_bytes()


def test_the_builder_has_no_limb_tracks_to_draw():
    cv = stage()
    with pytest.raises(ToonDataError, match="limb tracks"):
        toon_lyra.lyra(cv, cv.comp, [Pose(0.0, "wide", "flat", "desk")], 4.0, limbs=(object(),))


# -- the record --------------------------------------------------------------------------------------------------------
def test_she_is_proposed_a_toon_part_with_no_approval():
    specimens.load_parts()
    entry = registry.get("character", "toon-lyra")
    assert entry.builder is toon_lyra.lyra
    assert entry.style == "toon"
    part = parts.get("toon-lyra")
    version = part.version(1)
    assert version.status == "proposed"
    assert version.approval is None
    assert part.default is None
    assert version.rig.status == "proposed"
    assert version.rig.approval is None
    assert version.proof == version.rig.proof == "generated/character-proofs/lyra/index.html"


def test_her_digest_is_the_one_on_record():
    assert specimens.digest("toon-lyra") == parts.get("toon-lyra").version(1).drawing


def test_her_rig_digest_is_the_one_on_record():
    assert specimens.rig_digest("toon-lyra") == parts.get("toon-lyra").version(1).rig.drawing


@pytest.mark.parametrize("name", MOODS)
def test_the_digest_shows_every_mood(name, monkeypatch):
    changed = replace(toon_lyra.mood(name), eyes=replace(toon_lyra.mood(name).eyes, lids=(0.3, 0.2)))
    monkeypatch.setattr(toon_lyra, "MOODS", {**toon_lyra.MOODS, name: changed})
    assert specimens.digest("toon-lyra") != parts.get("toon-lyra").version(1).drawing


@pytest.mark.parametrize("name", EYE_POSES)
def test_the_digest_shows_every_eye_pose(name, monkeypatch):
    changed = replace(toon_lyra.eye_pose(name), eyes=replace(toon_lyra.eye_pose(name).eyes, brows=(3.0, 4.0)))
    monkeypatch.setattr(toon_lyra, "EYE_POSES", {**toon_lyra.EYE_POSES, name: changed})
    assert specimens.digest("toon-lyra") != parts.get("toon-lyra").version(1).drawing


def test_a_sketch_knows_her_and_refuses_her_while_she_is_proposed():
    assert "lyra" in sketch.CHARACTERS
    assert "lyra" in sketch.LIP_SYNCED
    with pytest.raises(parts.NotApprovedError):
        parts.resolved("toon-lyra")


def test_the_style_lists_her_modules():
    assert {"toon_lyra", "toon_orbit"} <= set(styles.STYLES["toon"].parts)


def test_the_salon_keeps_its_window_beside_her_head_so_her_tufts_stand_on_the_wall():
    x0, y0, x1, y1 = toon_orbit.SALON_WINDOW
    tufts = max(x for x, _ in toon_lyra.LYRA_RIG.head)
    assert x0 >= tufts
    assert y1 - y0 > 300.0
