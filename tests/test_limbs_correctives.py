"""Artist contours blend continuously across camera views without changing anatomy."""

import math
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, Affine, ArmProfile, Camera, Frame, LimbError, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions, bake, compile_motion
from srstudio.limbs.correctives import ContourCorrection, ContourKey
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.motion import Motion

BOX = ((-0.2, 0), (0.2, 0), (0.2, 0.5), (-0.2, 0.5))
WIDE = ((-0.4, 0), (0.4, 0), (0.4, 0.5), (-0.4, 0.5))


def correction():
    return ContourCorrection("palm", (ContourKey(-1, BOX), ContourKey(1, WIDE)))


def test_view_keys_interpolate_corresponding_vertices_and_clamp_at_endpoints():
    c = correction()
    assert c.points(-1) == BOX and c.points(1) == WIDE
    assert c.points(0)[0] == pytest.approx((-0.3, 0))
    assert c.points(-0.000001)[0][0] == pytest.approx(c.points(0.000001)[0][0], abs=1e-6)


def test_artist_contour_is_projected_in_camera_space_and_parent_inverse_once():
    sample = Motion(ArmProfile(), HUMAN).sample(0)
    camera = Camera(scale=100)
    base = project_pose(sample, camera, width=0.18, correctives=(correction(),))
    palm = next(p for p in base.parts if p.name == "palm")
    assert palm.authored
    parent = Affine(a=2, d=3, e=100, f=-20)
    local = project_pose(sample, camera, width=0.18, parent=parent, correctives=(correction(),))
    local_palm = next(p for p in local.parts if p.name == "palm")
    for point, transformed in zip(palm.polygon, local_palm.polygon, strict=True):
        assert parent.point(transformed) == pytest.approx(point)
    assert sample == Motion(ArmProfile(), HUMAN).sample(0)


def test_view_turns_have_no_discrete_palm_back_silhouette_switch():
    sample = Motion(ArmProfile(), HUMAN).sample(0)
    parts = []
    for angle in (math.pi / 2 - 1e-6, math.pi / 2 + 1e-6):
        camera = Camera(view=Frame(rotation=Quaternion.axis_angle(Vec3(0, 1, 0), angle)))
        pose = project_pose(sample, camera, width=0.18, correctives=(correction(),))
        parts.append(next(p for p in pose.parts if p.name == "palm"))
    assert max(math.dist(a, b) for a, b in zip(parts[0].polygon, parts[1].polygon, strict=True)) < 0.01


def test_compiler_preserves_authored_contours_in_brush_style_and_rejects_missing_parts_before_mutation():
    scene = Scene()
    cv = Canvas(scene)
    parent = cv.comp
    motion = Motion(ArmProfile(), HUMAN)
    bake(cv, parent, motion, id="custom", style="toon", options=BakeOptions(fps=1), correctives=(correction(),))
    assert any(n.attributes().get("path", "").count(" L") == 3 for n in scene.iter())
    before = len(list(scene.iter()))
    with pytest.raises(LimbError, match="part"):
        bake(
            cv,
            parent,
            motion,
            id="bad",
            options=BakeOptions(fps=1),
            correctives=(replace(correction(), part="absent"),),
        )
    assert len(list(scene.iter())) == before


@pytest.mark.parametrize(
    "keys", [(), (ContourKey(0, BOX), ContourKey(0, BOX)), (ContourKey(-1, BOX), ContourKey(1, BOX[:3]))]
)
def test_invalid_correspondence_is_rejected(keys):
    with pytest.raises(LimbError):
        ContourCorrection("palm", keys)


def test_bad_vertices_and_strength_are_rejected():
    for value in (float("nan"), 2):
        with pytest.raises(LimbError):
            ContourKey(value, BOX)
    with pytest.raises(LimbError):
        ContourKey(0, ((0, 0), (1, 0), (2, 0)))
    with pytest.raises(LimbError):
        ContourCorrection("palm", (ContourKey(0, BOX),), strength=2)


def test_partial_strength_and_mirrored_artwork_keep_contours_finite():
    sample = Motion(ArmProfile(), HUMAN).sample(0)
    c = replace(correction(), strength=0.5, mirror=True)
    pose = project_pose(sample, Camera(), width=0.18, correctives=(c,))
    palm = next(p for p in pose.parts if p.name == "palm")
    assert len(palm.polygon) == 4
    assert all(math.isfinite(v) for p in palm.polygon for v in p)
    unchanged = project_pose(sample, Camera(), width=0.18, correctives=(replace(c, strength=0),))
    assert unchanged == project_pose(sample, Camera(), width=0.18)


def test_compiler_auto_bakes_corrections_and_native_refuses_them():
    cv = Canvas(Scene())
    motion = Motion(ArmProfile(), HUMAN)
    result = compile_motion(cv, cv.comp, motion, id="auto", options=BakeOptions(fps=1), correctives=(correction(),))
    assert result.backend == "baked" and result.diagnostics
    with pytest.raises(LimbError, match="corrections"):
        compile_motion(
            cv, cv.comp, motion, id="native", backend="native", options=BakeOptions(fps=1), correctives=(correction(),)
        )


def test_opposite_winding_keys_are_rejected_instead_of_collapsing_mid_turn():
    with pytest.raises(LimbError, match="winding"):
        ContourCorrection("palm", (ContourKey(-1, BOX), ContourKey(1, tuple(reversed(BOX)))))


def test_brush_draws_an_end_on_segment_as_a_finite_disc():
    from srstudio.limbs.adapters import Appearance, adapter_for
    from srstudio.limbs.geometry import Part, ProjectedPose, ribbon

    cv = Canvas(Scene())
    line = ((100, 100), (100, 100))
    part = Part("upper", ribbon(line, (20, 20)), line, 0, 20, "sleeve")
    pose = ProjectedPose((part,), (100, 100), (100, 100), (100, 100), (), "side", 0)
    adapter_for("toon").draw(cv, cv.comp, pose, Appearance(), id="end-on")
    contours = [n.attributes().get("path", "") for n in cv.scene.iter()]
    assert any(p.count(" L") == 15 for p in contours)


def test_correctives_are_available_from_public_package_api():
    from srstudio import limbs

    assert limbs.ContourCorrection is ContourCorrection
    assert limbs.ContourKey is ContourKey
