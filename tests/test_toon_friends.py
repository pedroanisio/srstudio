"""Leo and Sam, two best friends drawn the critters' way with head rigs and controller grips (ADR 0230): both
proposed, each with his own face and his own head motion, every pose drawn through the rig, and nothing a reel can
draw until the operator approves them."""

from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import (
    PEACH,
    Canvas,
    anatomy_parts,
    flat_counter,
    parts,
    registry,
    specimens,
    styles,
    toon,
    toon_cast,
    toon_friends,
    toon_head,
    toon_rigs,
)
from srstudio.head_motion import HeadPlan
from srstudio.toon import Pose, ToonDataError
from srstudio.toon_gamepad import GRIPS

NAMES = ("toon-leo", "toon-sam")
RIGS = {"toon-leo": toon_friends.LEO_RIG, "toon-sam": toon_friends.SAM_RIG}
EACH = pytest.mark.parametrize("name", NAMES)


def stage(seconds: float = 8.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("f"))


def builder(name):
    return registry.get("character", name)


# -- the record --------------------------------------------------------------------------------------------------------
@EACH
def test_each_is_a_toon_character_proposed_with_a_proposed_rig_and_no_approval(name):
    specimens.load_parts()
    entry = builder(name)
    assert entry.style == "toon"
    version = parts.get(name).version(1)
    assert version.status == "proposed" and version.approval is None
    assert version.rig is not None and version.rig.status == "proposed" and version.rig.approval is None
    assert version.proof == version.rig.proof == "generated/character-proofs/between-friends/index.html"


@EACH
def test_the_digest_on_record_is_the_one_drawn(name):
    assert specimens.digest(name) == parts.get(name).version(1).drawing


@EACH
def test_the_rig_digest_on_record_is_the_one_drawn(name):
    assert specimens.rig_digest(name) == parts.get(name).version(1).rig.drawing


@EACH
def test_a_reel_cannot_reach_a_rig_the_operator_has_not_approved(name):
    assert toon_rigs.RIGS[name] is RIGS[name]
    with pytest.raises(parts.NotApprovedError, match="no approved version"):
        toon_rigs.rig_of(name)
    with pytest.raises(parts.NotApprovedError):
        toon_rigs.rig_of(name, {name: 1})


@EACH
@pytest.mark.parametrize("grip", GRIPS)
def test_the_rig_digest_shows_every_grip(name, grip, monkeypatch):
    held = specimens.rig_digest(name)
    monkeypatch.setitem(specimens.OWN_RIG_ARMS, name, tuple(g for g in GRIPS if g != grip))
    assert specimens.rig_digest(name) != held


@EACH
def test_the_drawing_digest_shows_the_grips(name, monkeypatch):
    held = specimens.digest(name)
    monkeypatch.setitem(specimens.OWN_ARMS, name, ())
    assert specimens.digest(name) != held


def test_the_style_lists_their_modules():
    assert {"toon_friends", "toon_gamepad"} <= set(styles.STYLES["toon"].parts)


@EACH
def test_each_declares_a_seated_body_and_a_pair_of_paws(name):
    assert anatomy_parts.body(name).framing.name == "BUST"
    assert anatomy_parts.CHARACTERS[name].kind is anatomy_parts.Kind.PAIRED


# -- the drawings ------------------------------------------------------------------------------------------------------
def test_they_look_unlike_each_other_and_move_unlike_each_other():
    leo, sam = toon_friends.LEO_RIG, toon_friends.SAM_RIG
    assert leo.look.coat != sam.look.coat
    assert toon_friends.LEO_CRITTER.sleeve != toon_friends.SAM_CRITTER.sleeve
    assert leo.style.signature != sam.style.signature
    assert leo.style.nod_px != sam.style.nod_px


def test_no_other_rig_shares_their_head_motion_seeds():
    seeds = [rig.style.seed for name, rig in toon_rigs.RIGS.items() if name not in NAMES]
    assert toon_friends.LEO_RIG.style.seed not in seeds
    assert toon_friends.SAM_RIG.style.seed not in seeds
    assert toon_friends.LEO_RIG.style.seed != toon_friends.SAM_RIG.style.seed


@EACH
def test_every_shared_eye_and_mouth_and_every_arm_and_grip_draws_through_the_builder(name):
    kinds = (*toon.ARMS, *GRIPS)
    poses = [Pose(i * 0.25, toon.EYES[i % len(toon.EYES)], toon.MOUTHS[i % len(toon.MOUTHS)], kinds[i % len(kinds)])
             for i in range(max(len(toon.EYES), len(toon.MOUTHS), len(kinds)))]  # fmt: skip
    seconds = len(poses) * 0.25 + 1.0
    cv = stage(seconds)
    groups = builder(name)(cv, cv.comp, poses, seconds, mouths=[(0.5, "open"), (1.0, "closed")])
    assert len(groups) == 1


@EACH
def test_the_builder_has_no_limb_tracks_to_draw(name):
    cv = stage()
    with pytest.raises(ToonDataError, match="limb track"):
        builder(name)(cv, cv.comp, [Pose(0.0, "half", "flat", "pad")], 4.0, limbs=(object(),))


@EACH
def test_the_builder_is_the_rig_held_still(name):
    poses = [Pose(0.0, "half", "flat", "pad"), Pose(1.0, "down", "smirk", "pad-lap")]
    a, b = stage(), stage()
    builder(name)(a, a.comp, poses, 4.0)
    toon_head.figure(b, b.comp, RIGS[name], poses, 4.0, HeadPlan.still())
    assert a.scene.to_bytes(layout="pretty") == b.scene.to_bytes(layout="pretty")


@EACH
def test_an_arm_kind_that_is_neither_shared_nor_a_grip_is_refused(name):
    cv = stage()
    with pytest.raises(ToonDataError, match="no gesture"):
        builder(name)(cv, cv.comp, [Pose(0.0, "half", "flat", "juggle")], 4.0)


def test_the_smirk_is_their_own_and_every_other_mouth_the_shared_one():
    look = toon_friends.LEO_RIG.look
    assert toon_friends._warm_mouths(look, "smirk") is not None
    assert all(toon_friends._warm_mouths(look, kind) is None for kind in toon.MOUTHS if kind != "smirk")


@EACH
def test_the_chin_turns_off_each_neck_join_and_stays_below_both(name):
    rig = RIGS[name]
    torso = {"toon-leo": toon_friends._LEO_TORSO, "toon-sam": toon_friends._SAM_TORSO}[name]
    (_, left), (_, right) = torso.head[0], torso.head[-1]
    chin = rig.head[len(torso.head) :]
    assert all(y > min(left, right) for _, y in chin)
    lowest = max(y for _, y in chin)
    assert lowest - max(left, right) >= 16.0  # a quarter circle of the default radius off each join


def test_a_chin_line_that_rises_past_a_corner_is_still_drawn_but_the_test_above_finds_it():
    line = ((262.0, 690.0), (230.0, 700.0), (185.0, 700.0), (140.0, 700.0), (108.0, 690.0))
    chin = toon_friends._rounded_chin(toon_friends._LEO_TORSO, 3.0, line)
    assert min(y for _, y in chin[3:-3]) < chin[2][1]


@EACH
def test_the_seam_holds_and_stops_holding_when_the_head_is_lifted(name):
    rig = RIGS[name]
    assert toon_head.open_seam(rig) == []
    high = replace(rig, head=tuple((x, y - 120.0) for x, y in rig.head))
    assert toon_head.open_seam(high)


@EACH
def test_the_whole_shared_vocabulary_reaches_the_rig(name):
    look = RIGS[name].look
    for mouth in toon.MOUTHS:
        assert isinstance(toon_cast._mouth(look, mouth), list)
