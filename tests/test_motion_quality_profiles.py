"""Authored quality limits produce bounded, actionable evidence before scene emission."""

import math
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Frame, Quaternion, Vec3
from srstudio.limbs import validation as quality
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack
from srstudio.limbs.projection import Camera


def samples_of(position, times=(0, 0.5, 1, 1.5), angle=lambda t: 0):
    return tuple(
        Motion(
            ArmProfile(),
            HUMAN,
            root=TransformTrack.constant(Frame(position(t), Quaternion.axis_angle(Vec3(0, 0, 1), angle(t)))),
        ).sample(t)
        for t in times
    )


def report(samples, profile=None):
    poses = tuple(project_pose(s, Camera(), width=0.18) for s in samples)
    return quality.audit(samples, poses, ArmProfile(), quality=profile)


def test_measured_jerk_matches_a_cubic_translation():
    measured = report(samples_of(lambda t: Vec3(t**3, 0, 0)))
    assert measured.max_jerk == pytest.approx(6)
    assert measured.to_dict()['metric_definitions']['max_jerk']['unit'] == 'canonical units/second^3'


def test_angular_acceleration_is_a_vector_derivative_on_nonuniform_times():
    measured = report(samples_of(lambda t: Vec3(), times=(0, 0.2, 0.7, 1), angle=lambda t: t * t / 4))
    assert measured.max_hand_angular_acceleration == pytest.approx(0.5, abs=1e-8)


def test_profile_warns_with_metric_limit_and_sample_time():
    profile = quality.QualityProfile('tired-host', max_jerk=5, policy='warn')
    measured = report(samples_of(lambda t: Vec3(t**3, 0, 0)), profile)
    (finding,) = measured.quality_findings
    assert finding.code == 'quality.limit'
    assert finding.metric == 'max_jerk'
    assert finding.actual == pytest.approx(6)
    assert finding.limit == 5
    assert finding.time == pytest.approx(0.75)
    assert finding.remedy
    assert measured.quality_profile == 'tired-host'


def test_too_few_samples_do_not_pass_a_jerk_limit():
    profile = quality.QualityProfile('slow', max_jerk=10)
    with pytest.raises(LimbError, match='samples') as caught:
        report(samples_of(lambda t: Vec3(), times=(0, 1, 2)), profile)
    assert caught.value.code == 'quality.evidence'


@pytest.mark.parametrize('backend', ['baked', 'native'])
def test_quality_failure_is_atomic_in_both_compilers(backend):
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None)
    before = scene.to_bytes()
    motion = Motion(
        ArmProfile(), HUMAN, root=TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    )
    with pytest.raises(LimbError) as caught:
        compile_motion(
            cv,
            cv.comp,
            motion,
            id='moving',
            backend=backend,
            options=BakeOptions(fps=8, quality=quality.QualityProfile('slow', max_speed=0.01)),
        )
    assert caught.value.code == 'quality.limit'
    assert caught.value.context['field'] == 'max_speed'
    assert scene.to_bytes() == before


def test_compiler_surfaces_advisory_quality_findings():
    cv = Canvas(Scene(version='auto'), font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=2),))
    result = compile_motion(
        cv,
        cv.comp,
        motion,
        id='point',
        backend='baked',
        options=BakeOptions(fps=8, quality=quality.QualityProfile('slow', max_speed=0.01, policy='warn')),
    )
    assert result.report.quality_findings
    assert any(d.code == 'quality.limit' for d in result.diagnostics)


def test_sphere_obstacles_measure_world_capsule_penetration():
    samples = samples_of(lambda t: Vec3())
    wrist = samples[0].arm.wrist
    sphere = quality.CollisionSphere('table-edge', wrist, 0.2)
    profile = quality.QualityProfile('table', max_penetration=0, obstacles=(sphere,), policy='warn')
    measured = report(samples, profile)
    assert measured.max_penetration == pytest.approx(0.2 + ArmProfile().width / 2)
    (finding,) = measured.quality_findings
    assert finding.obstacle == 'table-edge'
    assert finding.part == 'forearm'
    far = replace(sphere, center=Vec3(100, 100, 100))
    assert report(samples, replace(profile, obstacles=(far,))).max_penetration == 0


@pytest.mark.parametrize('limit', [-1, math.nan, math.inf, True, '1'])
def test_limits_are_finite_nonnegative_numbers(limit):
    with pytest.raises(LimbError):
        quality.QualityProfile('bad', max_speed=limit)


def test_profiles_reject_typos_and_unbounded_collision_work():
    with pytest.raises(LimbError):
        quality.QualityProfile('bad', policy='ignore')
    sphere = quality.CollisionSphere('table', Vec3(), 1)
    with pytest.raises(LimbError):
        quality.QualityProfile('bad', obstacles=(sphere, sphere))
    with pytest.raises(LimbError):
        quality.CollisionSphere('bad', Vec3(), -1)
    with pytest.raises(LimbError):
        quality.CollisionSphere('bad', Vec3(), 1, parts=('typo',))


def test_collision_work_budget_applies_even_to_warning_profiles():
    profile = quality.QualityProfile(
        'bounded', obstacles=(quality.CollisionSphere('table', Vec3(), 1),), max_collision_checks=1, policy='warn'
    )
    with pytest.raises(LimbError) as caught:
        report(samples_of(lambda t: Vec3()), profile)
    assert caught.value.code == 'budget'


def test_prepared_track_rechecks_a_changed_quality_profile():
    from srstudio.limbs.compile import LayerTargets
    from srstudio.limbs.integration import LimbTrack, prepare_tracks

    cv = Canvas(Scene(version='auto'), font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=2),))
    profile = quality.QualityProfile('fast', max_speed=1000)
    (track,) = prepare_tracks(cv, (LimbTrack(motion, options=BakeOptions(fps=8, quality=profile)),), 2)
    changed = replace(track, options=replace(track.options, quality=replace(profile, max_speed=0.01)))
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError, match='max_speed'):
        changed.draw(cv, LayerTargets(cv.comp, cv.comp, cv.comp), id='changed')
    assert cv.scene.to_bytes() == before


def test_interaction_quality_failure_leaves_scene_unchanged():
    from srstudio.limbs.interaction import Participant, bake_interaction

    cv = Canvas(Scene(version='auto'), font_asset=None)
    before = cv.scene.to_bytes()
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=2),))
    with pytest.raises(LimbError, match='max_speed'):
        bake_interaction(
            cv,
            cv.comp,
            (Participant('actor', motion),),
            (),
            id='interaction',
            options=BakeOptions(fps=8, quality=quality.QualityProfile('slow', max_speed=0.01)),
        )
    assert cv.scene.to_bytes() == before


def test_quality_recipe_builds_and_returns_structured_evidence():
    text = (Path(__file__).resolve().parents[1] / 'docs/catalog/limbs.md').read_text()
    section = text.split('<!-- quality-profile:start -->')[1].split('<!-- quality-profile:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {'cv': Canvas(Scene(version='auto'), font_asset=None)}
    exec(compile(code, 'quality-profile-recipe', 'exec'), namespace)
    assert namespace['compiled'].report.quality_profile == 'presenter'
    assert namespace['compiled'].report.to_dict()['metric_definitions']['max_jerk']['space'] == 'world'
