"""Native sleeve skinning must follow planar joints in real rendered pixels, not just valid XML."""

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import STYLES, Canvas
from srstudio.limbs import HUMAN, ArmProfile, Camera, LimbError, Vec3
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.motion import Action, Motion, Target


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=512, height=512, fps="24", duration=2, background="#000000")
    return Canvas(scene, font_asset=None)


def motion():
    return Motion(ArmProfile(), HUMAN, (Action("point", duration=2, target=Target(Vec3(0.65, 0.3, 0))),))


@pytest.mark.parametrize("style", tuple(STYLES))
def test_skin_backend_binds_style_owned_sleeve_surfaces_and_retains_baked_fingers(style):
    cv = canvas()
    result = compile_motion(
        cv,
        cv.comp,
        motion(),
        id="sleeve",
        backend="native",
        deformation="skin",
        style=style,
        camera=Camera(origin=(128, 128), scale=100),
        options=BakeOptions(fps=2),
    )
    assert result.backend == "native-skin"
    xml = ET.fromstring(cv.scene.to_bytes())
    bindings = xml.findall(".//modifier[@type='skin']")
    assert bindings and all(n.get("skeleton") == "sleeve-skeleton" for n in bindings)
    assert xml.find(".//group[@id='sleeve-hand']") is not None
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize(
    "kwargs", [{"backend": "baked"}, {"camera": Camera(projection="perspective")}, {"deformation": "magic"}]
)
def test_unsupported_skin_requests_are_rejected_before_scene_mutation(kwargs):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError):
        compile_motion(cv, cv.comp, motion(), id="bad", **{"deformation": "skin", **kwargs})
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize("mirrored", [False, True])
def test_rendered_skin_covers_the_elbow_and_forearm_near_the_wrist_at_multiple_frames(tmp_path, mirrored):
    engine = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not engine or not shutil.which("ffmpeg"):
        pytest.skip("set SRSTUDIO_ENGINE and install ffmpeg for native skin pixel evidence")
    cv = canvas()
    m = motion()
    camera = Camera(origin=(128, 128), scale=100)
    parent = cv.group(cv.comp, "actor", x=512 if mirrored else 0, scaleX=-1 if mirrored else 1)
    compile_motion(
        cv,
        parent,
        m,
        id="skin",
        deformation="skin",
        camera=camera,
        style="cutout",
        appearance=Appearance(sleeve="#ffffff", skin="#ff0000", detail=0, line_width=0),
        options=BakeOptions(fps=24),
    )
    path = tmp_path / "skin.scene.xml"
    path.write_bytes(cv.scene.to_bytes())
    for time in (0, 0.8, 1.5):
        png = tmp_path / f"skin-{time}.png"
        result = subprocess.run(
            [engine, "render", str(path), "--time", str(time), "--output", str(png)], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True,
            check=True,
        ).stdout
        pose = m.sample(time).arm
        for point in (pose.elbow, pose.wrist + (pose.elbow - pose.wrist).unit() * 0.12):
            x, y = camera.project(point).xy
            if mirrored:
                x = 512 - x
            colors = [
                raw[(yy * 512 + xx) * 3 : (yy * 512 + xx) * 3 + 3]
                for yy in range(round(y) - 2, round(y) + 3)
                for xx in range(round(x) - 2, round(x) + 3)
            ]
            assert any(all(c > 220 for c in color) for color in colors), (time, point)


def test_actor_track_routes_explicit_skin_deformation():
    from srstudio.limbs.compile import LayerTargets
    from srstudio.limbs.integration import LimbTrack

    cv = canvas()
    track = LimbTrack(motion(), deformation="skin", options=BakeOptions(fps=2))
    assert track.draw(cv, LayerTargets(cv.comp, cv.comp, cv.comp), id="track").backend == "native-skin"
    with pytest.raises(LimbError):
        LimbTrack(motion(), backend="baked", deformation="skin")


@pytest.mark.parametrize("backend", ["native", "baked"])
def test_compiled_limb_namespace_collision_fails_before_writing(backend):
    cv = canvas()
    cv.group(cv.comp, "existing-target")
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError, match="ID"):
        compile_motion(cv, cv.comp, motion(), id="existing", backend=backend, options=BakeOptions(fps=2))
    assert cv.scene.to_bytes() == before
