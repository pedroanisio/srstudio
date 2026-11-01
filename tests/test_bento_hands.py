"""Bento's hands are a pair from version 2 (ADR 0104): each hand knows its arm, and the other arm's is its mirror.

Which way a thumb points is read off the drawn layers, never off the flag that chose them.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import anatomy, parts, registry, specimens, toon, toon_bento, toon_rigs
from srstudio.canvas import PEACH, Canvas
from srstudio.toon import ToonDataError
from srstudio.toon_bento import GESTURES, Arm, Bento, Facing, Gesture, Paw
from srstudio.toon_cast import SHOULDERS

ROOT = Path(__file__).resolve().parents[1]
LEFT, RIGHT = Arm.LEFT, Arm.RIGHT
PALM, BACK = Facing.PALM, Facing.BACK
V1_DRAWING = "b9ad7b402809bee1c2b7365b25bebab6aaf7fa932946fa05a81bea4185e903cf"
V1_RIG = "e82a0f54d4f6caa1de25ca9866e3e6f4922f3bfe4c3969203ed3be34edd26517"
# The sha256 of version 1's nine gestures as they stood before hands had arms. Its specimen draws the shared arms and
# none of these, so the recorded digest alone cannot hold them still.
V1_GESTURES = "f266fac9044a8654ec6d8d00b9c8df6bc2a68741b8111b8b771eaca3dab533d4"
HANDS = (  # gesture, arm, what the camera sees, where the thumb points
    ("present", RIGHT, PALM, "in"),
    ("present", LEFT, BACK, "in"),
    ("empathy", RIGHT, BACK, "out"),
    ("empathy", LEFT, BACK, "in"),
    ("shrug", LEFT, PALM, "in"),
    ("shrug", RIGHT, PALM, "in"),
    ("firm", RIGHT, PALM, "in"),
    ("firm", LEFT, BACK, "in"),
    ("panic", LEFT, PALM, "in"),
    ("panic", RIGHT, PALM, "in"),
    ("facepalm", RIGHT, BACK, "out"),
    ("facepalm", LEFT, BACK, "in"),
)


def stage(seconds: float = 8.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None)


def paw_of(gesture: str, arm: Arm) -> Paw:
    return next(paw for paw in GESTURES[gesture].hands if paw.arm is arm)


def points(shape) -> list[tuple[float, float]]:
    return list(zip(shape[0::2], shape[1::2], strict=True))


def thumb_way(paw: Paw, number: int = 2) -> tuple[float, float]:
    """Where the thumb of ``paw`` goes in the picture, unit length. An open paw reaches further across the hand on its
    thumb's side; a fist's thumb is the last line drawn, lying on that side."""
    layers = toon_bento._paw_layers(paw, number)
    wrist = toon_bento._at(*toon_bento._placing(paw, number)(toon_bento._WRIST_X, 0.0))
    a = math.radians(paw.angle)
    across = (math.cos(a), math.sin(a))
    if paw.fist:
        line = points(layers[-1][0])
        reach = sum((x - wrist[0]) * across[0] + (y - wrist[1]) * across[1] for x, y in line) / len(line)
    else:
        spans = [(x - wrist[0]) * across[0] + (y - wrist[1]) * across[1] for x, y in points(layers[0][0])]
        reach = max(spans) + min(spans)
    side = 1.0 if reach > 0 else -1.0
    return across[0] * side, across[1] * side


def side_of(paw: Paw, number: int = 2) -> str:
    x = thumb_way(paw, number)[0]
    return "in" if (x > 0) == (paw.arm is LEFT) else "out"


def inked(shape, point: tuple[float, float]) -> bool:
    """Whether ``point`` lies inside the closed cubic ``shape``, its pieces cut into short lines."""
    line = [(shape[0], shape[1])]
    for k in range(2, len(shape), 6):
        (x0, y0), (x1, y1, x2, y2, x3, y3) = line[-1], shape[k : k + 6]
        for n in range(1, 9):
            t, m = n / 8, 1 - n / 8
            line.append(
                (
                    m**3 * x0 + 3 * m * m * t * x1 + 3 * m * t * t * x2 + t**3 * x3,
                    m**3 * y0 + 3 * m * m * t * y1 + 3 * m * t * t * y2 + t**3 * y3,
                )
            )
    px, py = point
    crossings = sum(
        (y0 > py) != (y1 > py) and px < x0 + (py - y0) * (x1 - x0) / (y1 - y0)
        for (x0, y0), (x1, y1) in zip(line, [*line[1:], line[0]], strict=True)
    )
    return crossings % 2 == 1


def assert_mirror(left, right) -> None:
    """The two shapes are one drawing, reflected left to right and moved: every point differs by the same step."""
    a, b = points(left), points(right)
    assert len(a) == len(b)
    dx, dy = b[0][0] + a[0][0], b[0][1] - a[0][1]
    for (x, y), (u, v) in zip(a, b, strict=True):
        assert u == pytest.approx(dx - x, abs=0.05)
        assert v == pytest.approx(y + dy, abs=0.05)


# -- every hand is on an arm -------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("gesture", "arm", "facing", "way"), HANDS)
def test_each_hand_is_on_its_arm_and_faces_as_it_should(gesture, arm, facing, way):
    assert paw_of(gesture, arm).facing is facing


def test_every_hand_of_every_gesture_is_listed():
    drawn = {(g.name, paw.arm) for g in GESTURES.values() for paw in g.hands}
    assert drawn == {(gesture, arm) for gesture, arm, _, _ in HANDS}


@pytest.mark.parametrize("name", ["ready", "folded", "tablet"])
def test_the_gestures_with_whole_paws_have_no_hand_to_pair(name):
    assert GESTURES[name].hands == () and len(GESTURES[name].paws) == 2


def test_a_bare_tuple_is_not_a_hand():
    with pytest.raises(ToonDataError, match="Paw"):
        replace(GESTURES["panic"], hands=((45.0, 346.0, -14.0, False, 1.05),))


@pytest.mark.parametrize(("arm", "facing"), [("left", PALM), (LEFT, "palm")])
def test_a_hand_names_a_real_arm_and_a_real_face(arm, facing):
    with pytest.raises(ToonDataError):
        Paw(arm, 45.0, 346.0, facing=facing)


def test_a_hand_on_the_other_arm_is_refused():
    panic = GESTURES["panic"]
    left, right = panic.hands
    with pytest.raises(ToonDataError, match="arm"):
        replace(panic, hands=(replace(left, arm=RIGHT), replace(right, arm=LEFT)))


def test_two_hands_on_one_arm_are_refused():
    panic = GESTURES["panic"]
    left, _ = panic.hands
    with pytest.raises(ToonDataError, match="two hands"):
        replace(panic, hands=(left, left))


def test_the_tucked_paw_cannot_be_given_to_the_working_arm():
    firm = GESTURES["firm"]
    fist, tucked = firm.hands
    with pytest.raises(ToonDataError, match="arm"):
        replace(firm, hands=(fist, replace(tucked, x=536.0, y=700.0, arm=RIGHT)))


def test_a_gestures_sleeves_are_frame_left_then_frame_right():
    panic = GESTURES["panic"]
    with pytest.raises(ToonDataError, match="sleeves"):
        replace(panic, sleeves=panic.sleeves[::-1])


def test_a_fist_is_drawn_from_its_fingers_only():
    with pytest.raises(ToonDataError, match="fist"):
        Paw(RIGHT, 536.0, 423.0, fist=True, facing=BACK)


def test_the_mirroring_cannot_be_chosen_by_a_caller():
    paw = paw_of("panic", RIGHT)
    assert paw.mirrored is True
    assert "mirrored" not in Paw.__dataclass_fields__


# -- which way the thumbs go -------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("gesture", "arm", "facing", "way"), HANDS)
def test_each_thumb_points_where_the_hand_says(gesture, arm, facing, way):
    assert side_of(paw_of(gesture, arm)) == way


@pytest.mark.parametrize(("gesture", "arm", "facing", "way"), HANDS)
def test_with_the_fingers_up_palms_turn_thumbs_in_and_backs_turn_them_out(gesture, arm, facing, way):
    if abs(paw_of(gesture, arm).angle) < 90.0:
        assert way == ("in" if facing is PALM else "out")


@pytest.mark.parametrize("gesture", ["present", "empathy", "firm", "facepalm"])
def test_a_hanging_hand_shows_its_back_with_the_thumb_to_his_leg(gesture):
    paw = paw_of(gesture, LEFT)
    assert abs(paw.angle) > 90.0 and paw.facing is BACK and side_of(paw) == "in"


def test_turning_a_raised_hand_over_moves_its_thumb_across():
    palm = paw_of("panic", RIGHT)
    assert side_of(palm) == "in" and side_of(replace(palm, facing=BACK)) == "out"


def test_the_same_hand_on_the_other_arm_is_mirrored():
    left = Paw(LEFT, 100.0, 300.0)
    right = Paw(RIGHT, 500.0, 300.0)
    assert left.mirrored is False and right.mirrored is True
    assert Paw(RIGHT, 500.0, 300.0, fist=True).mirrored is False
    assert Paw(LEFT, 100.0, 300.0, fist=True).mirrored is True


def test_a_back_has_no_palm_crease():
    palm = toon_bento._paw_layers(Paw(LEFT, 100.0, 300.0), 2)
    back = toon_bento._paw_layers(Paw(LEFT, 100.0, 300.0, facing=BACK), 2)
    assert len(palm) == len(back) + 1


@pytest.mark.parametrize("name", ["panic", "shrug"])
def test_the_frame_right_hand_is_the_mirror_of_the_frame_left(name):
    left, right = (toon_bento._paw_layers(paw_of(name, arm), 2) for arm in (LEFT, RIGHT))
    assert len(left) == len(right)
    assert_mirror(left[0][0], right[0][0])


def test_mirroring_a_paw_leaves_its_wrist_on_the_cuff():
    paw = Paw(RIGHT, 558.0, 347.0, 14.0, scale=1.05)
    plain = toon_bento._moved(paw.x, paw.y, paw.angle, paw.scale)
    assert toon_bento._placing(paw, 2)(toon_bento._WRIST_X, 18.0) == pytest.approx(plain(toon_bento._WRIST_X, 18.0))


def test_the_fist_keeps_its_fill_and_its_lines_and_its_thumb_inward():
    paw = paw_of("firm", RIGHT)
    new, old = toon_bento._paw_layers(paw, 2), toon_bento._paw_layers(paw, 1)
    assert new[0] == old[0] and new[2:] == old[2:]
    assert side_of(paw) == "in"


@pytest.mark.parametrize(("number", "closed"), [(1, False), (2, True)])
def test_a_paws_ink_goes_all_the_way_round_from_version_2(number, closed):
    """A stroke drops a last point that repeats its first, so version 1's line stops short of where it began."""
    paw = Paw(LEFT, 45.0, 346.0, -14.0, scale=1.05)
    place = toon_bento._mapped(toon_bento._placing(paw, number))
    (ax, ay), (bx, by) = place(*toon_bento._OPEN[-1][-2:]), place(*toon_bento._OPEN[0])
    seam = ax + (bx - ax) * 0.75, ay + (by - ay) * 0.75
    assert inked(toon_bento._paw_layers(paw, number)[1][0], seam) is closed


# -- the shared poses --------------------------------------------------------------------------------------------------
def limb_hand(side: int, drawing: Bento):
    if side == 0:
        return drawing.limb([SHOULDERS[0], (82.0, 760.0), (124.0, 792.0)], toon_bento.BENTO, (132.0, 794.0), True)[3:]
    return drawing.limb([SHOULDERS[1], (288.0, 760.0), (246.0, 792.0)], toon_bento.BENTO, (238.0, 794.0), True)[3:]


def test_a_shared_pose_gives_each_arm_its_own_hand():
    left, right = limb_hand(0, Bento(number=2)), limb_hand(1, Bento(number=2))
    assert_mirror(left[0][0], right[0][0])


def test_version_1_still_gives_both_shared_arms_one_hand():
    with pytest.raises(AssertionError):
        assert_mirror(limb_hand(0, Bento())[0][0], limb_hand(1, Bento())[0][0])


def test_a_shared_arm_from_no_shoulder_is_refused():
    with pytest.raises(ToonDataError, match="shoulder"):
        Bento(number=2).limb([(1.0, 2.0), (3.0, 4.0)], toon_bento.BENTO, (5.0, 6.0), True)


def test_a_version_he_does_not_have_is_refused():
    with pytest.raises(ToonDataError, match="version"):
        Bento(number=3)


# -- version 1 is untouched --------------------------------------------------------------------------------------------
def test_version_1_keeps_its_recorded_digests():
    version = parts.get("toon-bento").version(1)
    assert version.status == "approved" and version.drawing == V1_DRAWING and version.rig.drawing == V1_RIG
    assert specimens.digest("toon-bento", 1) == V1_DRAWING
    assert specimens.rig_digest("toon-bento", 1) == V1_RIG
    specimens.check("toon-bento", 1)
    specimens.check_rig("toon-bento", 1)


def test_version_1_keeps_all_nine_gestures():
    rows = []
    for name in GESTURES:
        under, over = Bento().gesture(name)
        rows.append((name, [(s, repr(c)) for s, c in under], [(s, repr(c)) for s, c in over]))
    assert hashlib.sha256(repr(rows).encode()).hexdigest() == V1_GESTURES


def test_version_1_still_draws_one_hand_on_both_arms():
    assert thumb_way(paw_of("panic", LEFT), 1)[0] > 0 and thumb_way(paw_of("panic", RIGHT), 1)[0] > 0


# -- version 2 is approved ---------------------------------------------------------------------------------------------
def test_version_2_is_approved_in_the_operators_words():
    version = parts.get("toon-bento").version(2)
    assert version.status == "approved" and version.approval.words == "approved"
    assert version.approval.date == "2026-11-01"
    assert version.rig is not None and version.rig.status == "approved" and version.rig.approval.words == "approved"
    assert version.proof == "generated/character-proofs/bento-hands/index.html"


def test_a_new_reel_gets_version_2_and_a_pin_keeps_version_1():
    assert parts.resolved("toon-bento") == 2
    assert toon_rigs.rig_of("toon-bento") is toon_bento.BENTO_RIG_2
    assert toon_rigs.rig_of("toon-bento", {"toon-bento": 1}) is toon_bento.BENTO_RIG


def test_the_record_is_what_version_2_draws():
    version = parts.get("toon-bento").version(2)
    assert specimens.digest("toon-bento", 2) == version.drawing != V1_DRAWING
    assert specimens.rig_digest("toon-bento", 2) == version.rig.drawing != V1_RIG


def test_version_2_is_a_drawing_with_the_same_contract():
    entry = parts.drawing("toon-bento", 2)
    assert entry.name == "toon-bento@2"
    assert (
        registry.describe("character", "toon-bento@2")["contract"]
        == registry.describe("character", "toon-bento")["contract"]
    )
    assert toon_rigs.RIGS["toon-bento@2"] is toon_bento.BENTO_RIG_2


def test_the_registered_drawing_draws_the_paired_hands():
    assert toon_bento.BENTO_RIG_2.look.drawing == Bento(number=2)
    cv = stage()
    entry = parts.drawing("toon-bento", 2)
    entry(cv, cv.comp, [toon_bento.pose_of(0.0, "happy", "panic")], 8.0)
    assert b"<shape" in cv.scene.to_bytes(layout="pretty")


def test_the_digest_of_version_2_holds_his_gestures(monkeypatch):
    before = specimens.digest("toon-bento", 2)
    panic = GESTURES["panic"]
    left, right = panic.hands
    monkeypatch.setitem(GESTURES, "panic", replace(panic, hands=(replace(left, angle=-20.0), right)))
    assert specimens.digest("toon-bento", 2) != before


def test_the_catalog_titles_version_2():
    notes = json.loads((ROOT / "docs/catalog/notes.json").read_text(encoding="utf-8"))
    assert notes["parts"]["toon-bento@2"]["title"]


def test_the_adr_records_the_rule_and_that_it_is_accepted():
    text = (ROOT / "docs/decisions/0104-bento-hands-are-a-pair.md").read_text(encoding="utf-8")
    assert "- Status: accepted" in text
    assert "toon-bento" in text and "generated-by:" in text


def test_module_exports():
    for name in ("Arm", "Facing", "Paw", "BENTO_2", "BENTO_RIG_2"):
        assert name in toon_bento.__all__
    assert isinstance(GESTURES["panic"], Gesture)


@pytest.mark.parametrize("name", ["ready", "folded", "tablet"])
def test_a_hand_drawn_whole_says_why_it_has_no_thumb_side(name):
    gesture = toon_bento.GESTURES[name]
    hands = gesture.whole()
    assert len(hands) == 2 and [hand.arm.side for hand in hands] == [anatomy.Side.LEFT, anatomy.Side.RIGHT]
    assert all(hand.thumb is None and hand.why == gesture.no_thumb for hand in hands)


def test_a_gesture_with_whole_paws_and_no_reason_is_refused():
    ready = toon_bento.GESTURES["ready"]
    with pytest.raises(toon.ToonDataError, match="no_thumb|thumb"):
        toon_bento.Gesture("x", "X", ready.sleeves, paws=ready.paws)


def test_a_gesture_with_no_whole_paws_has_nothing_to_say():
    plain = next(g for g in toon_bento.GESTURES.values() if not g.paws)
    assert plain.whole() == ()
