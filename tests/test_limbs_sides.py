"""Left and right name the character's own arms: one right-hand track lands on the anatomical right in every style.

A Stick figure is drawn in profile facing screen-right, so its near arm is its right; ``flip`` turns it to face left
and its far arm becomes its right. Gloss, Toon and Cutout characters face the viewer, so their right arm is on
screen-left, flipped or not.
"""

import xml.etree.ElementTree as ET
from collections import Counter

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, flat_counter, gloss, stick, toon_cast
from srstudio.cast import Manager
from srstudio.layout import path_bounds
from srstudio.limbs import HUMAN, ArmProfile, Camera
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.integration import LimbTrack
from srstudio.limbs.motion import Action, Motion
from srstudio.rig import Performance
from srstudio.toon import SCALE, Pose

# Each style's camera origin at the character's anatomical right shoulder, in its track coordinates (before flip).
SHOULDER = {"stick": (536, 891), "gloss": (-92, -345), "toon": (62, 712), "cutout": (-66, 148)}
CASES = [("stick", False), ("stick", True), ("gloss", False), ("gloss", True), ("toon", False), ("cutout", False)]


def track(style, side):
    return LimbTrack(
        Motion(ArmProfile(side=side, width=0.12), HUMAN, (Action("point", duration=2),)),
        style=style,
        camera=Camera(origin=SHOULDER[style], scale=90),
        options=BakeOptions(fps=2),
        backend="baked",
    )


def build(style, flip, side):
    """The character with one replacement track, as parsed XML, and its centre line on screen."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2)
    cv = Canvas(scene, font_asset=None, namer=flat_counter())
    limbs = (track(style, side),)
    if style == "stick":
        stick.rig(
            cv, cv.comp, (stick.RigKey(0, "stand"),), 2, poses=stick.STANDING, at=(540, 0), flip=flip, limbs=limbs
        )
        centre = None
    elif style == "gloss":
        gloss.nadia(cv, cv.comp, at=(540, 1500), flip=flip, end=2, limbs=limbs)
        centre = 540
    elif style == "toon":
        toon_cast.dog(cv, cv.comp, (Pose(0, "wide", "flat", "desk"),), 2, limbs=limbs)
        centre = 185 * SCALE  # the dog's centre line in reference pixels, drawn at SCALE with no x offset
    else:
        Manager(cv).build(cv.comp, 540, 900, perf=Performance(limbs=limbs))
        centre = 540
    assert scene.check(schema=True) == []
    return ET.fromstring(scene.to_bytes()), centre


def _parents(root):
    return {child: parent for parent in root.iter() for child in parent}


def screen(root, element, point):
    """``point`` in ``element``'s coordinates, through every ancestor's translation and scale (no rotations)."""
    parents = _parents(root)
    x, y = point
    node = element
    while node is not None:
        if node.tag == "group":
            assert float(node.get("rotation", "0")) == 0, "this check composes translation and scale only"
            ax, ay = float(node.get("anchorX", "0")), float(node.get("anchorY", "0"))
            sx, sy = float(node.get("scaleX", "1")), float(node.get("scaleY", "1"))
            x = float(node.get("x", "0")) + sx * (x - ax)
            y = float(node.get("y", "0")) + sy * (y - ay)
        node = parents.get(node)
    return x, y


def _track_roots(root):
    """Compiled tracks: a group named for its side whose children are its baked ``-frame-`` groups."""
    return [
        g
        for g in root.iter("group")
        if g.get("id", "").endswith(("-left", "-right"))
        and any(c.get("id", "").startswith(g.get("id") + "-frame-") for c in g)
    ]


def _centre(root, parents, element):
    box = path_bounds(element.get("path"))
    return screen(root, parents[element], ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2))


def legacy(root):
    """Every drawn path outside the replacement tracks, with its centre on screen."""
    inside = {e for r in _track_roots(root) for e in r.iter()}
    parents = _parents(root)
    return [
        (e.get("path"), e, _centre(root, parents, e))
        for e in root.iter("shape")
        if e.get("shape") == "path" and e not in inside
    ]


def replaced_by_right(style, flip):
    """The legacy shapes a right track removes: drawn beside a left track, absent beside a right one."""
    left_root, centre = build(style, flip, "left")
    right_root, _ = build(style, flip, "right")
    missing = Counter(d for d, _, _ in legacy(left_root)) - Counter(d for d, _, _ in legacy(right_root))
    return [(d, e, c) for d, e, c in legacy(left_root) if missing[d] > 0], centre


@pytest.mark.parametrize(("style", "flip"), CASES)
def test_a_right_track_replaces_the_characters_anatomical_right_arm(style, flip):
    replaced, centre = replaced_by_right(style, flip)
    assert replaced
    if style == "stick":
        # The figure's own near arm is drawn wider; it is the right arm when it faces right, the left when flipped.
        width = stick.LIMB_FAR if flip else stick.LIMB
        assert {float(e.get("strokeWidth")) for _, e, _ in replaced} == {width}
        assert all(d.startswith("M 536 891") for d, _, _ in replaced)
    else:
        assert all(x < centre for _, _, (x, _) in replaced), "a front-facing character's right arm is on screen-left"


@pytest.mark.parametrize(("style", "flip"), CASES)
def test_a_right_track_is_drawn_from_the_right_shoulder_outward(style, flip):
    root, centre = build(style, flip, "right")
    (limb,) = _track_roots(root)
    shoulder = screen(root, _parents(root)[limb], SHOULDER[style])
    parents = _parents(root)
    xs = [_centre(root, parents, e)[0] for e in limb.iter("shape") if e.get("shape") == "path"]
    reach = sum(xs) / len(xs) - shoulder[0]
    if style == "stick":
        # A profile figure points the way it faces: screen-right, or screen-left when flipped.
        assert reach < 0 if flip else reach > 0
    else:
        assert shoulder[0] < centre, "the track starts at the screen-left shoulder"
        assert reach < 0, "the right arm points outward, to screen-left"


@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("side", ["left", "right"])
def test_a_stick_far_arm_track_is_drawn_behind_the_torso_and_a_near_one_over_it(side, flip):
    root, _ = build("stick", flip, side)
    order = {e: i for i, e in enumerate(root.iter())}
    neck, hip = stick.STANDING["stand"].neck, stick.STANDING["stand"].hip
    (torso,) = [e for e in order if e.get("path") == f"M {neck[0]} {neck[1]} L {hip[0]} {hip[1]}"]
    (limb,) = _track_roots(root)
    shapes = [order[e] for e in limb.iter("shape")]
    assert shapes
    # Like the legacy far arm, drawn before the torso; the near arm after it. The far arm is the left one facing
    # right, the right one when flipped to face left.
    if (side == "left") != flip:
        assert max(shapes) < order[torso]
    else:
        assert min(shapes) > order[torso]


@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("side", ["left", "right"])
def test_a_stick_track_on_either_side_reaches_the_way_the_figure_faces(side, flip):
    root, _ = build("stick", flip, side)
    (limb,) = _track_roots(root)
    parents = _parents(root)
    shoulder = screen(root, parents[limb], SHOULDER["stick"])
    xs = [_centre(root, parents, e)[0] for e in limb.iter("shape") if e.get("shape") == "path"]
    reach = sum(xs) / len(xs) - shoulder[0]
    # In profile both arms point forward: screen-right facing right, screen-left flipped to face left.
    assert reach < 0 if flip else reach > 0
