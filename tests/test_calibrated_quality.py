"""Versioned quality presets are tied to anatomy, sampling and measured reference motions."""

import json
from dataclasses import replace
from importlib import resources

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Vec3
from srstudio.limbs.calibration import CALIBRATED_HAND, get_preset, list_presets, measure_reference, reference_cases
from srstudio.limbs.compile import compile_motion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.motion import Action, Motion, Target

IDS = ('toon-human-conversation/1.0.0', 'gloss-human-deliberate/1.0.0')


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=960, height=720, fps='24', duration=8)
    return Canvas(scene, width=960, height=720, font_asset=None)


@pytest.mark.parametrize('name', IDS)
def test_profiles_disclose_scope_calibration_and_missing_subjective_evidence(name):
    profile = get_preset(name)
    data = profile.describe()
    assert data['version'] == '1.0.0'
    assert data['scope']['fps'] == 24
    assert data['scope']['clock'] == 'motion seconds'
    assert data['scope']['upper_arm'] == 1
    assert data['scope']['forearm'] == 0.9
    assert data['scope']['hand'] == 'human'
    assert data['calibration']['headroom'] == 1.25
    assert data['perceptual_validation'] == 'not established by numeric calibration'
    assert json.loads(json.dumps(data, allow_nan=False)) == data
    assert name in {p['id'] for p in list_presets()}


@pytest.mark.parametrize('name', IDS)
def test_every_reference_performance_passes_its_own_frozen_limits(name):
    profile = get_preset(name)
    cases = reference_cases(name)
    assert len(cases) >= 6
    assert {case.motion.arm.side for case in cases} == {'left', 'right'}
    for case in cases:
        cv = canvas()
        result = compile_motion(
            cv,
            cv.comp,
            case.motion,
            id='reference',
            style=profile.style,
            backend='baked',
            options=profile.options_for(case.motion, style=profile.style, fps=24),
        )
        assert not result.report.quality_findings
        assert result.report.quality_profile == name


@pytest.mark.parametrize('name', IDS)
def test_time_compression_trips_all_calibrated_derivative_gates_and_refuses_emission(name):
    profile = get_preset(name)
    source = reference_cases(name)[0].motion
    fast = replace(
        source, actions=tuple(replace(a, start=a.start / 6, duration=a.duration / 6) for a in source.actions)
    )
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        compile_motion(
            cv,
            cv.comp,
            fast,
            id='rejected',
            style=profile.style,
            backend='baked',
            options=profile.options_for(fast, style=profile.style, fps=24),
        )
    assert caught.value.code == 'quality.limit'
    assert cv.scene.to_bytes() == before
    result = compile_motion(
        cv,
        cv.comp,
        fast,
        id='evidence',
        style=profile.style,
        backend='baked',
        options=profile.options_for(fast, style=profile.style, fps=24, policy='warn'),
    )
    failed = {f.metric for f in result.report.quality_findings}
    assert set(profile.describe()['limits']) - {'max_reach_error'} <= failed


@pytest.mark.parametrize('name', IDS)
def test_reach_gate_catches_explicitly_clamped_unreachable_motion(name):
    profile = get_preset(name)
    motion = Motion(
        ArmProfile(),
        CALIBRATED_HAND,
        (Action('reach', duration=4, target=Target(Vec3(4, 0, 0))),),
        reach_policy='clamp',
    )
    cv = canvas()
    result = compile_motion(
        cv,
        cv.comp,
        motion,
        id='clamped',
        style=profile.style,
        backend='baked',
        options=profile.options_for(motion, style=profile.style, fps=24, policy='warn'),
    )
    assert 'max_reach_error' in {f.metric for f in result.report.quality_findings}


@pytest.mark.parametrize('change', ['anatomy', 'hand', 'rate', 'style'])
def test_profiles_refuse_out_of_scope_inputs_instead_of_claiming_calibration(change):
    preset = get_preset(IDS[0])
    motion = reference_cases(IDS[0])[0].motion
    fps, style = 24, preset.style
    if change == 'anatomy':
        motion = replace(motion, arm=replace(motion.arm, upper=2))
    elif change == 'hand':
        motion = replace(motion, hand=replace(motion.hand, palm_width=0.9))
    elif change == 'rate':
        fps = 30
    else:
        style = 'stick'
    with pytest.raises(LimbError) as caught:
        preset.options_for(motion, style=style, fps=fps)
    assert caught.value.code == 'quality.scope'
    assert caught.value.to_dict()['remedy']


def test_unknown_preset_has_a_structured_repair_path():
    with pytest.raises(LimbError) as caught:
        get_preset('invented/99.0.0')
    assert caught.value.code == 'quality.preset'
    assert caught.value.to_dict()['expected'] == list(IDS)


@pytest.mark.parametrize('backend', ['baked', 'native'])
@pytest.mark.parametrize('change', ['rate', 'hand', 'anatomy', 'style'])
def test_compilation_rechecks_scope_when_options_are_reused(backend, change):
    preset = get_preset(IDS[0])
    source = reference_cases(IDS[0])[0].motion
    options = preset.options_for(source, style='toon', fps=24)
    style = 'toon'
    if change == 'rate':
        options = replace(options, fps=12)
    elif change == 'hand':
        source = replace(source, hand=replace(CALIBRATED_HAND, palm_width=0.9))
    elif change == 'anatomy':
        source = replace(source, arm=replace(source.arm, upper=1.5))
    else:
        style = 'gloss'
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        compile_motion(cv, cv.comp, source, id='outside', style=style, backend=backend, options=options)
    assert caught.value.code == 'quality.scope'
    assert cv.scene.to_bytes() == before


def test_interactions_recheck_the_same_calibration_scope():
    from srstudio.limbs.interaction import Participant, bake_interaction

    preset = get_preset(IDS[0])
    source = reference_cases(IDS[0])[0].motion
    options = preset.options_for(source, style='toon', fps=24)
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        bake_interaction(cv, cv.comp, (Participant('hand', source, 'gloss'),), (), id='outside', options=options)
    assert caught.value.code == 'quality.scope'
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('name', IDS)
def test_frozen_measurements_match_source_hashes_and_recomputed_corpus(name):
    asset = resources.files('srstudio').joinpath(get_preset(name).describe()['calibration']['asset'])
    frozen = next(row for row in json.loads(asset.read_text())['profiles'] if row['id'] == name)
    measured = measure_reference(name)
    assert measured['limits'] == frozen['limits']
    assert measured['peaks'] == pytest.approx(frozen['peaks'], rel=1e-10, abs=1e-10)
    for actual, expected in zip(measured['cases'], frozen['cases'], strict=True):
        assert actual['name'] == expected['name']
        assert actual['source_sha256'] == expected['source_sha256']
        assert actual['samples'] == expected['samples']
        assert actual['metrics'] == pytest.approx(expected['metrics'], rel=1e-10, abs=1e-10)


@pytest.mark.parametrize('field,value', [('fps', True), ('fps', 0), ('fps', 121), ('arm', None), ('hand', None)])
def test_scope_requires_typed_anatomy_and_bounded_integer_sampling(field, value):
    from srstudio.limbs.validation import QualityScope

    with pytest.raises(LimbError):
        QualityScope(**{'style': 'toon', 'fps': 24, field: value})


def test_presets_refuse_untyped_motion_and_invalid_policy():
    preset = get_preset(IDS[0])
    with pytest.raises(LimbError) as caught:
        preset.options_for({}, style='toon', fps=24)
    assert caught.value.to_dict()['path'] == 'motion'
    with pytest.raises(LimbError, match='policy'):
        preset.options_for(reference_cases(IDS[0])[0].motion, style='toon', fps=24, policy='ignore')


def test_scope_allows_translation_without_rescaling_anatomy():
    preset = get_preset(IDS[0])
    source = reference_cases(IDS[0])[0].motion
    translated = replace(source, arm=replace(source.arm, shoulder=Vec3(10, 20, 30)))
    options = preset.options_for(translated, style='toon', fps=24)
    assert options.quality.scope is not None


@pytest.mark.parametrize('field', ['arm', 'hand'])
def test_scope_refuses_malformed_python_anatomy_with_a_repairable_error(field):
    preset = get_preset(IDS[0])
    malformed = replace(reference_cases(IDS[0])[0].motion, **{field: None})
    with pytest.raises(LimbError) as caught:
        preset.options_for(malformed, style='toon', fps=24)
    assert caught.value.code == 'quality.scope'
    assert caught.value.to_dict()['path'] == field
    assert caught.value.to_dict()['remedy']


@pytest.mark.parametrize('name', IDS)
def test_presets_keep_the_hand_they_were_measured_with(name):
    # ADR 0089 fixes anatomy per version: HUMAN's later three-segment thumb must not change the 1.0.0 corpus.
    assert CALIBRATED_HAND.name == 'human'
    assert CALIBRATED_HAND.digits[0].lengths == (0.17, 0.13)
    assert {case.motion.hand for case in reference_cases(name)} == {CALIBRATED_HAND}
    preset = get_preset(name)
    preset.options_for(Motion(ArmProfile(), CALIBRATED_HAND), style=preset.style, fps=24)
    with pytest.raises(LimbError) as caught:
        preset.options_for(Motion(ArmProfile(), HUMAN), style=preset.style, fps=24)
    assert caught.value.code == 'quality.scope'
    assert caught.value.to_dict()['path'] == 'hand'
