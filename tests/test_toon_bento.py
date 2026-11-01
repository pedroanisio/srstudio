"""Bento, the operator's character: one module, typed moods, its own gestures and eyes, an approved rig (ADR 0062)."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    brush,
    head_motion,
    parts,
    registry,
    sketch,
    specimens,
    toon,
    toon_bento,
    toon_cast,
    toon_head,
    toon_rigs,
)
from srstudio.canvas import PEACH, Canvas
from srstudio.head_motion import limit
from srstudio.toon import Pose, ToonDataError
from srstudio.toon_torso import depth_in

ROOT = Path(__file__).resolve().parents[1]
RIG = toon_bento.BENTO_RIG
LOOK = toon_bento.BENTO
DRAWING = LOOK.drawing
NAMES = (
    "neutral welcoming happy delighted laughing proud relieved grateful affectionate hopeful excited confident "
    "curious thinking confused skeptical surprised astonished concerned empathetic sad grieving disappointed "
    "embarrassed irritated angry furious disgusted contemptuous sarcastic deadpan bored tired anxious frightened "
    "panicked"
).split()
EYE_STATES = "camera left right up down up-left up-right near half-blink closed left-wink right-wink".split()
GESTURES = "ready present empathy shrug folded firm panic facepalm tablet".split()


def stage(seconds: float = 8.0) -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return scene, Canvas(scene, PEACH, font_asset=None)


def face(eyes: str, inner: float = 1.0) -> list[toon_cast.Layer]:
    return toon_cast._eye(LOOK, LOOK.eyes[0 if inner > 0 else 1], eyes, inner)


def spots(layers) -> set[str]:
    return {colour for _, colour in layers}


# -- the moods are data ------------------------------------------------------------------------------------------------
def test_the_thirty_six_moods_are_named_in_english_in_the_pack_s_order():
    assert tuple(toon_bento.MOODS) == tuple(NAMES)
    assert all(re.fullmatch(r"[a-z]+", name) for name in toon_bento.MOODS)
    assert all(mood.use.isascii() and mood.use for mood in toon_bento.MOODS.values())


def test_a_mood_carries_its_channels_as_typed_fields():
    skeptical = toon_bento.MOODS["skeptical"]
    assert isinstance(skeptical, toon_bento.Mood)
    assert skeptical.gaze == (0.8, 0.0)
    assert skeptical.lids == (0.42, 0.08)
    assert skeptical.brows == (7.0, -21.0)
    assert skeptical.angles == (8.0, 0.0)
    assert skeptical.mouth == "side-flat"
    assert skeptical.tilt == -4.0
    assert skeptical.pupil == 1.0
    assert skeptical.gesture == "folded"
    grieving = toon_bento.MOODS["grieving"]
    assert grieving.marks == frozenset({"tears"})
    assert toon_bento.MOODS["panicked"].marks == frozenset({"sweat"})


def test_every_mood_differs_from_every_other_in_its_data_and_its_drawing():
    moods = list(toon_bento.MOODS.values())
    fields = {replace(m, name="", use="", gesture="ready") for m in moods}
    assert len(fields) == 36
    drawn = {repr(face(m.name) + face(m.name, -1.0) + toon_cast._mouth(LOOK, m.mouth)) for m in moods}
    assert len(drawn) == 36


@pytest.mark.parametrize("call", [toon_bento.mood, lambda name: toon_bento.pose_of(0.0, name)], ids=["mood", "pose_of"])
def test_an_unknown_mood_is_refused_by_name(call):
    with pytest.raises(ToonDataError, match="hangry"):
        call("hangry")


def test_a_portuguese_label_is_not_a_mood():
    with pytest.raises(ToonDataError, match="FELIZ"):
        toon_bento.mood("FELIZ")


@pytest.mark.parametrize(
    "change, word",
    [
        ({"lids": (1.2, 0.0)}, "lids"),
        ({"bottom": -0.1}, "bottom"),
        ({"gaze": (1.5, 0.0)}, "gaze"),
        ({"pupil": 0.0}, "pupil"),
        ({"mouth": "smirking"}, "mouth"),
        ({"gesture": "wave"}, "gesture"),
        ({"marks": frozenset({"glitter"})}, "mark"),
        ({"shut": "hard"}, "shut"),
        ({"tilt": 40.0}, "tilt"),
    ],
)
def test_a_mood_out_of_range_is_refused(change, word):
    with pytest.raises(ToonDataError, match=word):
        replace(toon_bento.MOODS["neutral"], **change)


@pytest.mark.parametrize("kind", ["hangry", "hangry/left", "neutral/sideways", "neutral/left/up", ""])
def test_an_unknown_eye_kind_is_refused_when_drawn(kind):
    with pytest.raises(ToonDataError):
        face(kind)


def test_an_unknown_mouth_or_arm_is_refused_when_drawn():
    with pytest.raises(ToonDataError, match="pout"):
        toon_cast._mouth(LOOK, "pout")
    with pytest.raises(ToonDataError, match="jazz"):
        toon_cast._arms(LOOK, "jazz", 0)
    with pytest.raises(ToonDataError, match="jazz"):
        _drawn([Pose(0.0, "neutral", "neutral", "jazz")])


def test_a_shared_arm_starts_on_his_own_shoulder_and_keeps_inside_the_blazer():
    under, _over = toon_cast._arms(LOOK, "desk", 0)
    blazer = toon_bento._samples(toon_bento._BLAZER, toon_bento._at)
    outline = [layer[0] for layer in under if layer[1] == toon_bento.SLEEVE_LINE]
    assert len(outline) == 2
    for shape in outline:
        points = list(zip(shape[0::2], shape[1::2], strict=True))
        for x, y in (p for p in points if p[1] < 760.0):
            span = toon_bento._span(blazer, x)
            assert span is not None, (x, y)
            assert y >= span[0] - 4.0, (x, y)


def test_pose_of_gives_the_mood_s_mouth_and_its_gesture_and_takes_another():
    assert toon_bento.pose_of(1.0, "angry") == Pose(1.0, "angry", "scowl", "firm")
    assert toon_bento.pose_of(1.0, "angry", "shrug", "left") == Pose(1.0, "angry/left", "scowl", "shrug")
    assert toon_bento.pose_of(1.0, "angry", "desk") == Pose(1.0, "angry", "scowl", "desk")
    with pytest.raises(ToonDataError, match="jazz"):
        toon_bento.pose_of(0.0, "angry", "jazz")
    with pytest.raises(ToonDataError, match="sideways"):
        toon_bento.pose_of(0.0, "angry", eyes="sideways")


# -- the eye states and the gestures -----------------------------------------------------------------------------------
def test_the_twelve_eye_states_carry_over_and_each_draws_differently():
    assert tuple(toon_bento.EYE_STATES) == tuple(EYE_STATES)
    drawn = {repr(face(f"neutral/{s}") + face(f"neutral/{s}", -1.0)) for s in EYE_STATES}
    assert len(drawn) == 12


def test_a_wink_shuts_one_eye_on_the_side_it_names():
    open_eye = toon_bento.SCLERA
    assert open_eye not in spots(face("left-wink", 1.0)) and open_eye in spots(face("left-wink", -1.0))
    assert open_eye in spots(face("right-wink", 1.0)) and open_eye not in spots(face("right-wink", -1.0))


def test_near_focus_turns_the_eyes_in_and_a_glance_adds_to_a_mood_s_gaze():
    def iris(drawing, side: int) -> float:
        shape = next(s for s, c in drawing.eye(LOOK, LOOK.eyes[side], "neutral", 1.0 - 2.0 * side) if c == "#66513C")
        return (brush.bounds(shape)[0] + brush.bounds(shape)[2]) / 2

    assert iris(DRAWING.looking(0.42, 0.0), 0) > iris(DRAWING, 0)
    near = [next(s for s, c in face("neutral/near", k) if c == "#66513C") for k in (1.0, -1.0)]
    assert brush.bounds(near[0])[0] > brush.bounds(next(s for s, c in face("neutral") if c == "#66513C"))[0]
    assert brush.bounds(near[1])[0] < brush.bounds(next(s for s, c in face("neutral", -1.0) if c == "#66513C"))[0]


@pytest.mark.parametrize("name", toon_bento.MOODS)
def test_the_iris_never_leaves_the_eye_or_the_lids(name):
    mood = toon_bento.mood(name)
    centre = LOOK.eyes[0]
    for dx, dy in ((0.42, 0.04), (-0.42, 0.04), (0.0, -0.3)):
        drawing = DRAWING.looking(dx, dy)
        eye = [s for s, c in drawing.eye(LOOK, centre, name, 1.0) if c == toon_bento.SCLERA]
        for shape, colour in drawing.eye(LOOK, centre, name, 1.0):
            if colour == "#66513C" and eye:
                x0, y0, x1, y1 = brush.bounds(shape)
                ex0, ey0, ex1, ey1 = brush.bounds(eye[0])
                assert x0 >= ex0 - 0.6 and x1 <= ex1 + 0.6 and y0 >= ey0 - 0.6 and y1 <= ey1 + 0.6, mood.name


def test_the_nine_gestures_carry_over_and_each_draws_differently():
    assert tuple(toon_bento.GESTURES) == tuple(GESTURES)
    drawn = {repr(toon_cast._arms(LOOK, g, 0)) for g in GESTURES}
    assert len(drawn) == 9


def test_every_mood_keeps_the_gesture_the_pack_pairs_it_with():
    assert [toon_bento.MOODS[n].gesture for n in NAMES] == (
        "tablet present present shrug present folded empathy empathy empathy ready panic present "
        "present ready shrug folded shrug panic empathy empathy ready empathy ready facepalm "
        "folded firm firm present folded folded tablet ready ready ready shrug panic"
    ).split()


def test_ready_keeps_its_sleeves_behind_the_blazer_and_its_paws_in_front():
    under, over = toon_cast._arms(LOOK, "ready", 0)
    blazer = [i for i, (_, c) in enumerate(under) if c == toon_bento.SHIRT]
    sleeves = [i for i, (_, c) in enumerate(under) if isinstance(c, toon_cast.Ramp) and "sleeve" in c.name]
    assert sleeves and blazer and max(sleeves) < min(blazer)
    assert over


@pytest.mark.parametrize("gesture", [g for g in GESTURES if g != "ready"])
def test_a_gesture_goes_over_the_head_the_way_the_pack_stacks_it(gesture):
    under, over = toon_cast._arms(LOOK, gesture, 0)
    assert under == [] and over


def test_the_tablet_has_no_lettering_and_no_label():
    root = _drawn([Pose(0.0, "neutral", "neutral", "tablet")])
    assert root.findall(".//text") == []


def test_a_gesture_stays_in_frame_when_framed_on_him():
    for gesture in GESTURES:
        under, over = toon_cast._arms(LOOK, gesture, 0)
        boxes = [brush.bounds(shape) for shape, _ in under + over]
        assert min(b[0] for b in boxes) + toon_bento.CENTRED > 0.0, gesture
        assert max(b[2] for b in boxes) + toon_bento.CENTRED < 592.0, gesture


# -- what he is known by -----------------------------------------------------------------------------------------------
def test_the_port_keeps_the_marks_he_is_known_by():
    x0, y0, x1, y1 = brush.bounds(toon_bento._shape(toon_bento.HEAD))
    mx0, my0, mx1, my1 = brush.bounds(toon_bento._shape(toon_bento.MUZZLE))
    assert (mx1 - mx0) / (x1 - x0) > 0.85  # a broad muzzle
    assert (my1 - my0) / (y1 - y0) > 0.5
    ears = toon_bento.skull_layers()
    assert toon_bento.EAR in spots(ears)
    ear = brush.bounds(next(s for s, c in ears if c == toon_bento.EAR))
    assert (ear[2] - ear[0]) < 0.3 * (x1 - x0)  # small, rounded ears
    assert toon_cast.Ramp in {type(c) for _, c in toon_bento.trunk_layers()}  # a tailored blazer in its gradient
    paw = brush.bounds(next(s for s, c in toon_cast._arms(LOOK, "ready", 0)[1] if isinstance(c, toon_cast.Ramp)))
    assert (paw[2] - paw[0]) < 0.25 * (x1 - x0)  # tiny paws


@pytest.mark.parametrize("kind", ["smile", "grin", "beam", "laugh"])
def test_his_smiles_show_the_two_front_teeth(kind):
    teeth = [s for s, c in toon_cast._mouth(LOOK, kind) if c == toon_bento.TOOTH]
    assert len(teeth) == 2


def test_every_mouth_stays_on_the_muzzle():
    muzzle = toon_bento._outline(toon_bento.MUZZLE)
    for kind in (*toon_bento.MOUTH_KINDS, *toon.MOUTHS):
        for shape, _ in toon_cast._mouth(LOOK, kind):
            for x, y in zip(shape[0::2], shape[1::2], strict=True):
                assert depth_in(muzzle, (x, y))[0] > 0.0, kind


@pytest.mark.parametrize("kind", sorted(toon_bento._TOOTH_ROW))
def test_the_lines_between_his_teeth_stay_inside_the_mouth(kind):
    mouth = toon_bento._samples(toon_bento._BIG_MOUTHS[kind], toon_bento._at)
    lines = [shape for shape, colour in toon_cast._mouth(LOOK, kind) if colour == toon_bento._TOOTH_LINE]
    assert lines
    for shape in lines:
        for x, y in zip(shape[0::2], shape[1::2], strict=True):
            top, bottom = toon_bento._span(mouth, x)
            assert top - 1.5 <= y <= bottom + 1.5, (kind, x, y)


def test_a_blink_lays_back_the_whole_of_the_muzzle_s_line_over_the_eye():
    """The white of the left eye sits over this line, so a blink has to draw all of it back."""
    ring = toon_bento._ring(toon_bento._EYE_X[0], toon_bento._EYE_Y, toon_bento._EYE_RX + 1.5, 37.5)
    under = []
    for x, y in toon_bento._samples(toon_bento.MUZZLE, per_piece=24):
        span = toon_bento._span(ring, x)
        if span is not None and span[0] <= y <= span[1]:
            under.append(toon_bento._at(x, y))
    drawn = [
        point
        for shape, colour in toon_bento._lid_layers()
        if colour == toon_bento.MUZZLE_LINE
        for point in zip(shape[0::2], shape[1::2], strict=True)
    ]
    assert under
    for point in under:
        assert min(math.dist(point, seen) for seen in drawn) < 2.0, point


def test_every_shared_kind_draws_on_him():
    for eyes in toon.EYES:
        assert face(eyes)
    for mouth in toon.MOUTHS:
        assert isinstance(toon_cast._mouth(LOOK, mouth), list)
    for arms in toon.ARMS:
        assert toon_cast._arms(LOOK, arms, 0)
    for viseme in toon_cast.VISEMES:
        assert toon_cast._viseme(LOOK, viseme)


def test_the_visemes_are_his_own_and_differ():
    drawn = [repr(toon_cast._viseme(LOOK, v)) for v in toon_cast.VISEMES]
    assert len(set(drawn)) == len(toon_cast.VISEMES)
    assert toon_bento.TOOTH in spots(toon_cast._viseme(LOOK, "open"))
    assert toon_bento.TOOTH in spots(toon_cast._viseme(LOOK, "teeth"))


def test_a_shut_mood_has_nothing_to_blink():
    for kind in ("laughing", "relieved", "neutral/closed", "closed", "hearts"):
        root = _drawn([Pose(0.0, kind, "neutral", "ready")])
        assert not _opacity_keys(root), kind
    assert _opacity_keys(_drawn([Pose(0.0, "neutral", "neutral", "ready")]))


def _opacity_keys(root: ET.Element) -> list[ET.Element]:
    return [a for a in root.iter("animate") if a.get("property") == "opacity"]


def _drawn(poses, plan=None, rig=RIG, **kw) -> ET.Element:
    scene, cv = stage()
    toon_head.figure(cv, cv.comp, rig, poses, 8.0, plan or head_motion.HeadPlan.still(), **kw)
    return ET.fromstring(scene.to_bytes(layout="pretty"))


# -- lip sync ----------------------------------------------------------------------------------------------------------
def test_lip_sync_draws_one_layer_per_viseme_with_hold_keys():
    mouths = [(0.4, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    root = _drawn([toon_bento.pose_of(0.0, "welcoming")], mouths=mouths)
    assert len(_opacity_keys(root)) >= len(toon_cast.VISEMES)


def test_he_is_lip_synced_in_a_sketch_and_a_sketch_can_draw_him():
    assert "bento" in sketch.CHARACTERS and "bento" in sketch.LIP_SYNCED
    assert callable(sketch.drawer("bento"))


# -- the rig -----------------------------------------------------------------------------------------------------------
def test_his_head_lies_over_the_body_with_his_own_chin():
    assert RIG.head_over is True
    assert RIG.neck == pytest.approx(toon_bento._at(298.0, 424.0))


def test_the_seam_stays_shut_at_every_bound_with_a_mood_s_tilt_on_top():
    assert toon_head.open_seam(RIG) == []
    for mood in toon_bento.MOODS.values():
        assert toon_head.open_seam(replace(RIG, tilt=mood.tilt, tilt_reach=(0.0, 0.0))) == [], mood.name


def test_the_rig_s_bounds_hold_the_widest_mood_tilt():
    tilts = [m.tilt for m in toon_bento.MOODS.values()]
    assert RIG.tilt_reach == (min(tilts), max(tilts))
    turns = [turn for turn, _ in toon_head._bounds(RIG)]
    swing = limit(RIG.style, "turn") + limit(RIG.style, "roll") + limit(RIG.style, "idle_roll")
    assert min(turns) == pytest.approx(min(tilts) - swing)
    assert max(turns) == pytest.approx(max(tilts) + swing)


def test_a_rig_whose_head_is_lifted_off_its_blazer_is_found_out():
    lifted = replace(RIG, head=tuple((x, y - 90.0) for x, y in RIG.head))
    assert toon_head.open_seam(lifted)


def test_the_body_top_is_behind_the_head_at_rest():
    for point in RIG.cover:
        assert depth_in(RIG.head, point)[0] > 0.0


def test_the_muzzle_and_the_face_stay_on_the_head_at_the_slide_bounds():
    side = limit(RIG.style, "face_x")
    drop = limit(RIG.style, "nod") * RIG.face_slide
    muzzle = toon_bento._outline(toon_bento.MUZZLE)
    for dx in (-side, side):
        for dy in (0.0, drop):
            for x, y in muzzle:
                assert depth_in(RIG.head, (x + dx, y + dy))[0] >= -toon_bento.MUZZLE_LAP, (dx, dy, x, y)


def test_a_nod_slides_his_face_less_than_the_others_so_the_muzzle_stays_on():
    assert RIG.face_slide < toon_head.FACE_SLIDE
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    root = _drawn([toon_bento.pose_of(0.0, "neutral")], head_motion.plan(RIG.style, [speech], 8.0))
    face_group = next(g for g in root.iter("group") if g.get("id", "").startswith("face-"))
    face_y = next(a for a in face_group.findall("animate") if a.get("property") == "y")
    nod = max(abs(v) for _, v in head_motion.plan(RIG.style, [speech], 8.0).nod.keys)
    assert max(abs(float(k.get("value"))) for k in face_y.findall("key")) == pytest.approx(
        toon.fh(RIG.face_slide) * nod, abs=0.01
    )


def _take() -> head_motion.Alignment:
    text = "Everyone knows I rested"
    return head_motion.Alignment(
        tuple(text), *zip(*((i * 0.08, (i + 1) * 0.08) for i in range(len(text))), strict=True)
    )


def test_a_lid_line_stops_at_the_eye():
    centre = LOOK.eyes[0]
    x0, _, x1, _ = brush.bounds(next(s for s, c in face("skeptical") if c == toon_bento.SCLERA))
    lids = [brush.bounds(s) for s, c in face("skeptical") if c == toon_bento.DARK_FUR]
    lid = min(lids, key=lambda b: abs((b[1] + b[3]) / 2 - centre[1]))
    assert lid[0] >= x0 - 2.0 and lid[2] <= x1 + 2.0


def test_the_head_turns_about_the_pack_s_pivot_with_each_mood_s_tilt_eased_in():
    poses = [toon_bento.pose_of(0.0, "neutral"), toon_bento.pose_of(2.0, "laughing"), toon_bento.pose_of(4.0, "bored")]
    root = _drawn(poses)
    tilt = next(g for g in root.iter("group") if g.get("id", "").startswith("tilt-"))
    keys = tilt.find("animate").findall("key")
    ease = toon_head.TILT_EASE
    assert [float(k.get("value")) for k in keys] == [0.0, 0.0, -6.0, -6.0, 7.0]
    assert [float(k.get("time")) for k in keys] == [0.0, 2.0, 2.0 + ease, 4.0, 4.0 + ease]


def test_the_style_is_a_calm_anchor_of_its_own():
    style = RIG.style
    others = [r.style for name, r in toon_rigs.RIGS.items() if not name.startswith("toon-bento")]
    assert style.seed not in {s.seed for s in others}
    assert style.nod_px < 9.0 and style.glance_face < 3.0


def test_the_plan_moves_him_when_he_speaks():
    text = "Good evening and welcome"
    alignment = head_motion.Alignment(
        tuple(text), *zip(*((i * 0.08, (i + 1) * 0.08) for i in range(len(text))), strict=True)
    )
    speech = head_motion.Speech(1.0, head_motion.words_of(alignment, 1.0), (-20.0,) * 300)
    plan = head_motion.plan(RIG.style, [speech], 8.0)
    assert plan.nod.keys
    assert max(abs(v) for _, v in plan.nod.keys) <= limit(RIG.style, "nod")


# -- the registry and the record ---------------------------------------------------------------------------------------
def test_he_is_registered_in_the_toon_style_with_the_operators_approval():
    entry = registry.get("character", "toon-bento")
    assert entry.name == "toon-bento"
    part = parts.get("toon-bento")
    assert part.kind == "character" and part.style == "toon" and part.refused is None
    assert part.latest().number == 1
    version = part.version(1)
    assert version.status == "approved" and version.approval.words == "bento is approved"
    assert version.rig is not None and version.rig.status == "approved"
    assert version.rig.approval.date == "2026-10-31" and version.rig.approval.words == "bento is approved"


def test_the_recorded_digests_are_what_he_draws():
    version = parts.get("toon-bento").version(1)
    assert specimens.digest("toon-bento", 1) == version.drawing
    assert specimens.rig_digest("toon-bento", 1) == version.rig.drawing


def test_the_digest_moves_when_the_drawing_moves(monkeypatch):
    before = specimens.digest("toon-bento", 1)
    monkeypatch.setattr(
        toon_bento, "HEAD", ((180.0, 189.0), *toon_bento.HEAD[1:-1], (143.0, 277.0, 150.0, 225.0, 180.0, 189.0))
    )
    toon_bento.skull_layers.cache_clear()
    try:
        assert specimens.digest("toon-bento", 1) != before
    finally:
        monkeypatch.undo()
        toon_bento.skull_layers.cache_clear()


def test_a_reel_can_draw_and_move_him_now_the_operator_has_approved():
    assert parts.resolved("toon-bento") == 1
    assert toon_rigs.rig_of("toon-bento") is RIG


def test_a_limb_track_is_refused_by_name():
    scene, cv = stage()
    with pytest.raises(ToonDataError, match="limb"):
        registry.get("character", "toon-bento")(
            cv, cv.comp, [Pose(0.0, "wide", "flat", "desk")], 8.0, limbs=(object(),)
        )


def test_the_registered_drawing_draws_the_rig_standing_still():
    scene, cv = stage()
    registry.get("character", "toon-bento")(cv, cv.comp, [toon_bento.pose_of(0.0, "happy")], 8.0)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    assert [a.get("property") for a in root.iter("animate") if a.get("property") != "opacity"] == ["rotation"]


def test_the_port_reads_nothing_from_outside_and_keeps_no_branding():
    source = (ROOT / "src/srstudio/toon_bento.py").read_text(encoding="utf-8")
    assert source.isascii()
    for word in ("_tmp", "bento-pack", "PAUTA", "Pauta", "Bicho", "BEP", "DejaVu", "open(", "read_text", "<svg"):
        assert word not in source
    for kind in (*toon_bento.MOUTH_KINDS, *toon_bento.MOODS, *toon_bento.GESTURES, *toon_bento.EYE_STATES):
        assert kind.isascii()


def test_the_adr_records_the_author_and_is_accepted():
    text = (ROOT / "docs/decisions/0062-bento.md").read_text(encoding="utf-8")
    assert re.search(r"^- Status: accepted\b", text, re.M)
    assert "operator" in text and "authored" in text


def test_the_catalog_titles_him():
    notes = json.loads((ROOT / "docs/catalog/notes.json").read_text(encoding="utf-8"))
    assert notes["parts"]["toon-bento"]["title"]


def test_the_module_is_reachable_from_the_package():
    import srstudio

    assert srstudio.toon_bento is toon_bento


def test_the_tilt_reach_is_what_the_table_says():
    assert math.isclose(max(abs(m.tilt) for m in toon_bento.MOODS.values()), toon_bento.TILT_REACH)
