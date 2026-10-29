"""Native planar IK must agree with the spatial model at sampled frames, using the actual renderer evaluator."""

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.math3d import Vec3
from srstudio.limbs.model import HUMAN, ArmProfile, LimbError
from srstudio.limbs.motion import Action, Motion, Target
from srstudio.limbs.projection import Camera


def canvas():
    s = Scene(version="auto")
    s.add_project(width=1080, height=1920, fps="24", duration=2)
    return Canvas(s, font_asset=None)


def motion():
    return Motion(ArmProfile(), HUMAN, (Action("point", 0, 2, target=Target(Vec3(0.65, 0.3, 0))),))


def test_native_backend_emits_two_bones_and_preserves_articulated_hand_frames():
    cv = canvas()
    result = compile_motion(cv, cv.comp, motion(), id="arm", backend="native", options=BakeOptions(fps=12))
    assert result.backend == "native" and result.frames == 24
    xml = ET.fromstring(cv.scene.to_bytes())
    assert len(xml.findall(".//skeleton/bone")) == 2
    assert xml.find(".//skeleton/transformConstraint[@type='ik']") is not None
    assert cv.scene.check() == []


def test_native_backend_refuses_nonplanar_requests_without_writing_any_nodes():
    cv = canvas()
    before = cv.scene.to_bytes()
    m = Motion(ArmProfile(), HUMAN, (Action("reach", 0, 2),))
    with pytest.raises(LimbError, match="planar"):
        compile_motion(cv, cv.comp, m, id="arm", backend="native")
    assert cv.scene.to_bytes() == before
    result = compile_motion(cv, cv.comp, m, id="arm", backend="auto", options=BakeOptions(fps=2))
    assert result.backend == "baked" and result.diagnostics


def test_native_arm_and_hand_have_the_same_visibility_interval_with_an_offset():
    cv = canvas()
    compile_motion(cv, cv.comp, motion(), id="arm", backend="native", options=BakeOptions(fps=2, offset=0.5))
    xml = ET.fromstring(cv.scene.to_bytes())
    keys = xml.findall(".//group[@id='arm']/animate[@property='opacity']/key")
    assert [(float(k.get("time")), float(k.get("value"))) for k in keys] == [(0, 0), (0.5, 1), (2.5, 0)]


def test_renderer_native_elbow_and_wrist_match_spatial_solver(tmp_path):
    engine = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not engine:
        pytest.skip("set SRSTUDIO_ENGINE to verify native IK against the renderer")
    cv = canvas()
    camera = Camera(origin=(400, 400), scale=150)
    m = motion()
    compile_motion(cv, cv.comp, m, id="arm", backend="native", camera=camera, options=BakeOptions(fps=24))
    path = tmp_path / "native.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    checked = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    for frame in (0, 10, 24, 40):
        result = subprocess.run(
            [engine, "eval", str(path), "--frame", str(frame), "--json"], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        raw = json.loads(result.stdout)
        data = raw.get("result", raw)
        nodes = data["nodes"]
        for name, expected in (
            ("arm-upper-draw", m.sample(frame / 24).arm.shoulder),
            ("arm-forearm-draw", m.sample(frame / 24).arm.elbow),
        ):
            node = next(n for n in nodes if n["id"] == name)
            assert node["world"][4:6] == pytest.approx(camera.project(expected).xy, abs=1e-3)
        forearm = next(n for n in nodes if n["id"] == "arm-forearm-draw")
        a, b, _, _, x, y = forearm["world"]
        length = m.arm.forearm * camera.scale
        assert (x + a * length, y + b * length) == pytest.approx(
            camera.project(m.sample(frame / 24).arm.wrist).xy, abs=1e-3
        )
