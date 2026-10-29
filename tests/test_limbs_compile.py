"""Baked emission is bounded, validated before mutation, and retains temporal visibility and depth controls."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs.compile import BakeOptions, LayerTargets, Occlusion, bake
from srstudio.limbs.math3d import Vec3
from srstudio.limbs.model import HUMAN, ArmProfile, LimbError
from srstudio.limbs.motion import Action, Motion, Target
from srstudio.limbs.projection import Camera


def canvas():
    s = Scene(version="auto")
    s.add_project(width=1080, height=1920, fps="24", duration=2)
    return Canvas(s, font_asset=None)


def test_bake_emits_every_sample_on_its_interval_and_no_duplicate_ids():
    cv = canvas()
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    compiled = bake(cv, cv.comp, motion, id="right-hand", camera=Camera(origin=(400, 400)), options=BakeOptions(fps=12))
    assert compiled.frames == 24
    assert compiled.report.max_bone_error < 1e-8
    assert cv.scene.check() == []
    root = ET.fromstring(cv.scene.to_bytes())
    ids = [n.get("id") for n in root.iter() if n.get("id")]
    assert len(ids) == len(set(ids))
    frames = root.findall(".//group[@id='right-hand']/group")
    assert len(frames) == 24
    for i, frame in enumerate(frames):
        keys = frame.findall("animate/key")
        enabled = [float(k.get("time")) for k in keys if k.get("value") == "1"]
        assert enabled == [pytest.approx(i / 12, abs=1e-6)]
    for i in range(24):
        visible = []
        for j, frame in enumerate(frames):
            value = 0.0
            for key in frame.findall("animate/key"):
                if float(key.get("time")) <= i / 12:
                    value = float(key.get("value"))
            if value:
                visible.append(j)
        assert visible == [i], "rounding must not leave a stale frame visible at a sampling boundary"


@pytest.mark.parametrize("options", [BakeOptions(fps=24, max_frames=2), BakeOptions(max_nodes=1)])
def test_bake_limits_refuse_work_before_scene_mutation(options):
    cv = canvas()
    original = cv.scene.to_bytes()
    with pytest.raises(LimbError, match="budget"):
        bake(cv, cv.comp, Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),)), id="arm", options=options)
    assert cv.scene.to_bytes() == original


def test_unreachable_action_is_checked_before_emitting_any_frame():
    cv = canvas()
    original = cv.scene.to_bytes()
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2, target=Target(Vec3(5, 0, 0), "world")),))
    with pytest.raises(LimbError, match="reach"):
        bake(cv, cv.comp, motion, id="arm")
    assert cv.scene.to_bytes() == original


def test_explicit_layers_can_put_a_facepalm_in_front_of_the_head_and_hide_fingers():
    cv = canvas()
    behind, body, front = [cv.group(cv.comp, name) for name in ("behind", "body", "front")]
    options = BakeOptions(fps=2)
    result = bake(
        cv,
        body,
        Motion(ArmProfile(), HUMAN, (Action("facepalm", 0, 2),)),
        id="facepalm",
        options=options,
        layers=LayerTargets(behind, body, front),
        occlusion=(Occlusion("palm", 0, 2, layer="front"), Occlusion("digit:*", 0, 2, visible=False)),
    )
    root = ET.fromstring(cv.scene.to_bytes())
    assert root.find(".//group[@id='front']/group") is not None
    assert result.report.hidden_parts > 0
    assert cv.scene.check() == []


def test_bad_style_or_visibility_rule_is_not_silently_ignored():
    cv = canvas()
    m = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    original = cv.scene.to_bytes()
    with pytest.raises(LimbError):
        bake(cv, cv.comp, m, id="bad", style="missing")
    with pytest.raises(LimbError, match="part"):
        bake(cv, cv.comp, m, id="bad", occlusion=(Occlusion("sixth-finger", 0, 2),))
    assert cv.scene.to_bytes() == original


def test_bake_honors_local_clock_and_rejects_unsupported_adapter_modes():
    cv = canvas()
    cv.local_time = True
    m = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    bake(cv, cv.comp, m, id="arm", options=BakeOptions(fps=2, offset=0.5))
    root = ET.fromstring(cv.scene.to_bytes())
    assert all(a.get("timeBase") == "local" for a in root.iter("animate"))
    from srstudio.limbs.adapters import Capabilities, VectorAdapter, register_adapter

    register_adapter(
        "unit-planar", VectorAdapter("unit-planar", "#ffffff", "#ffffff", capabilities=Capabilities(perspective=False))
    )
    with pytest.raises(LimbError, match="perspective"):
        bake(cv, cv.comp, m, id="unsupported", style="unit-planar", camera=Camera(projection="perspective"))
