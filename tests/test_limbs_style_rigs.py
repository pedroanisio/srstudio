"""Style characters accept the same typed limb tracks without retaining replaced arms."""

from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, flat_counter, gloss, stick, toon_cast
from srstudio.limbs import HUMAN, ArmProfile, Camera, LimbError
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.integration import LimbTrack
from srstudio.limbs.motion import Action, Motion
from srstudio.toon import Pose


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2)
    return Canvas(scene, font_asset=None, namer=flat_counter())


def track(style):
    return LimbTrack(
        Motion(ArmProfile(), HUMAN, (Action("point", duration=2),)),
        style=style,
        camera=Camera(origin=(62, 712), scale=100),
        options=BakeOptions(fps=2),
    )


@pytest.mark.parametrize("name", ["nadia", "gus", "tamsin"])
def test_gloss_people_accept_single_side_tracks_and_keep_the_other_legacy_arm(name):
    cv = canvas()
    result = getattr(gloss, name)(cv, cv.comp, at=(540, 1500), end=2, limbs=(track("gloss"),))
    assert result.parts["pose"]
    paths = [n.attributes().get("path", "") for n in cv.scene.iter("shape")]
    # A doll faces the viewer: its own right arm, which the track replaces, is the one drawn on screen-left.
    assert "M-92 -345 Q-128 -290 -126 -222" not in paths
    assert "M92 -345 Q128 -290 126 -222" in paths
    assert any(n.attributes().get("id", "").endswith("-right") for n in cv.scene.iter("group"))
    assert cv.scene.check(schema=True) == []


def test_stick_accepts_single_side_tracks_and_omits_only_that_legacy_arm():
    cv = canvas()
    pose = stick.SEATED["type-a"]
    stick.rig(cv, cv.comp, (stick.RigKey(0, "type-a"),), 2, limbs=(track("stick"),))
    paths = [n.attributes().get("path", "") for n in cv.scene.iter("shape")]
    # The non-replaced arm is still represented by its authored joint path.
    assert any(f"{pose.hands[0][0]}" in p and f"{pose.hands[0][1]}" in p for p in paths)
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize("drawer", [toon_cast.dog, toon_cast.frog, toon_cast.bear, toon_cast.rabbit])
def test_toon_cast_routes_reference_space_tracks_and_removes_selected_paw(drawer):
    cv = canvas()
    groups = drawer(cv, cv.comp, (Pose(0, "wide", "flat", "desk"),), 2, limbs=(track("toon"),))
    assert len(groups) == 1
    assert any(n.attributes().get("id", "").endswith("-right") for n in cv.scene.iter("group"))
    assert cv.scene.check(schema=True) == []


def test_toon_layer_data_can_omit_each_arm_independently():
    look = toon_cast.DOG
    default = toon_cast.figure_shapes(look, "wide", "flat", "desk")
    left = toon_cast.figure_shapes(look, "wide", "flat", "desk", omit_arms=frozenset({"left"}))
    both = toon_cast.figure_shapes(look, "wide", "flat", "desk", omit_arms=frozenset({"left", "right"}))
    assert len(default) > len(left) > len(both)
    assert len(default) - len(left) == len(left) - len(both)


@pytest.mark.parametrize("style", ["stick", "gloss", "toon"])
def test_default_output_is_byte_identical_when_empty_tracks_are_explicit(style):
    def build(explicit):
        cv = canvas()
        options = {"limbs": ()} if explicit else {}
        if style == "stick":
            stick.rig(cv, cv.comp, (stick.RigKey(0, "type-a"),), 2, **options)
        elif style == "gloss":
            gloss.nadia(cv, cv.comp, at=(540, 1500), end=2, **options)
        else:
            toon_cast.dog(cv, cv.comp, (Pose(0, "wide", "flat", "desk"),), 2, **options)
        return cv.scene.to_bytes()

    assert build(False) == build(True)


def test_bad_tracks_and_durations_fail_before_drawing_character_geometry():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError):
        gloss.nadia(cv, cv.comp, at=(540, 1500), end=2, limbs=(track("gloss"), track("gloss")))
    assert cv.scene.to_bytes() == before
    with pytest.raises(LimbError):
        stick.rig(
            cv,
            cv.comp,
            (stick.RigKey(0, "type-a"),),
            2,
            limbs=(replace(track("stick"), options=BakeOptions(fps=2, duration=3)),),
        )
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize("pose", toon_cast.ARMS)
def test_each_toon_pose_can_suppress_both_arms_including_face_paws(pose):
    full = toon_cast.figure_shapes(toon_cast.DOG, "wide", "flat", pose)
    clean = toon_cast.figure_shapes(toon_cast.DOG, "wide", "flat", pose, omit_arms=frozenset({"left", "right"}))
    assert len(clean) < len(full)


@pytest.mark.parametrize("pose", ["desk", "sigh", "lean"])
def test_toon_track_parent_matches_the_body_reference_transform_in_the_renderer(tmp_path, pose):
    import json
    import math
    import os
    import subprocess

    from srstudio.toon import fx, fy

    engine = os.environ.get("SRSTUDIO_ENGINE")
    if not engine:
        pytest.skip("set SRSTUDIO_ENGINE to verify the character reference transform")
    cv = canvas()
    toon_cast.dog(cv, cv.comp, (Pose(0, "wide", "flat", pose),), 2, limbs=(track("toon"),))
    path = tmp_path / "reference.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    result = subprocess.run([engine, "eval", str(path), "--time", "1", "--json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    nodes = json.loads(result.stdout)["result"]["nodes"]
    node = next(n for n in nodes if n["id"].endswith("-right"))
    a, b, c, d, e, f = node["world"]
    x, y = track("toon").camera.origin
    actual = (a * x + c * y + e, b * x + d * y + f)
    if pose == "sigh":
        y += toon_cast.SIGH_DROP
    elif pose == "lean":
        angle = math.radians(toon_cast.LEAN_DEGREES)
        dx, dy = x - toon_cast.PIVOT[0], y - toon_cast.PIVOT[1]
        x, y = (
            toon_cast.PIVOT[0] + dx * math.cos(angle) - dy * math.sin(angle),
            toon_cast.PIVOT[1] + dx * math.sin(angle) + dy * math.cos(angle),
        )
    assert actual == pytest.approx((fx(x), fy(y)), abs=0.02)


def test_toon_pose_changes_do_not_restart_limb_animation_on_a_local_clock(tmp_path):
    import json
    import os
    import subprocess

    engine = os.environ.get("SRSTUDIO_ENGINE")
    if not engine:
        pytest.skip("set SRSTUDIO_ENGINE to verify pose changes on a local clock")
    cv = canvas()
    cv.local_time = True
    toon_cast.dog(
        cv, cv.comp, (Pose(0, "wide", "flat", "desk"), Pose(0.5, "wide", "flat", "sigh")), 2, limbs=(track("toon"),)
    )
    path = tmp_path / "local-clock.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    for time, expected in ((0.6, 1), (1, 2), (1.8, 3)):
        result = subprocess.run(
            [engine, "eval", str(path), "--time", str(time), "--json"], capture_output=True, text=True, check=True
        )
        nodes = json.loads(result.stdout)["result"]["nodes"]
        visible = [n["id"] for n in nodes if "-frame-" in n["id"] and n.get("opacity", 0) > 0.5]
        assert len(visible) == 1 and f"-frame-{expected:06d}-" in visible[0]
