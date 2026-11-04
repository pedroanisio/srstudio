"""An agent can require sampled motion evidence without mistaking warnings or missing audits for a pass."""

import json

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, build_report, cli
from srstudio.errors import SrstudioError
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.compile import BakeOptions, _Preparation, bake, compile_motion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.interaction import Participant, bake_interaction
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.validation import QualityProfile, QualityScope


def compile_with(profile, *, prepared=None):
    cv = Canvas(Scene(version='auto'), font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=1),))
    return bake(cv, cv.comp, motion, id='arm', options=BakeOptions(fps=4, quality=profile), _prepared=prepared)


@pytest.mark.parametrize(
    'profile,status',
    [
        (None, 'skipped'),
        (QualityProfile('empty'), 'skipped'),
        (QualityProfile('measured', max_speed=100), 'passed'),
        (QualityProfile('slow', max_speed=0, policy='warn'), 'failed'),
    ],
)
def test_report_records_profile_policy_scope_and_actual_evidence(profile, status):
    with build_report.capture() as report:
        result = compile_with(profile)
    check = report.to_dict()['checks']['motion-quality']
    assert check['status'] == status
    row = check['results'][0]
    if profile is None:
        assert row['reason']
    else:
        evidence = row['evidence']
        assert evidence['profile']['name'] == profile.name
        assert evidence['profile']['policy'] == profile.policy
        assert evidence['sampling'] == {
            'clock': 'motion seconds',
            'samples': 4,
            'start': 0,
            'end': 0.75,
            'min_interval': 0.25,
            'max_interval': 0.25,
            'track': 'arm',
            'style': 'toon',
            'fps': 4,
            'offset': 0,
            'duration': 1,
        }
        assert evidence['report']['max_speed'] == result.report.max_speed
        assert evidence['report']['quality_findings'] == result.report.to_dict()['quality_findings']
    json.dumps(report.to_dict(), allow_nan=False)
    if status != 'passed':
        with pytest.raises(SrstudioError):
            report.require(['motion-quality'])


def test_refusal_retains_failed_quality_findings():
    with build_report.capture() as report, pytest.raises(LimbError, match='max_speed'):
        compile_with(QualityProfile('slow', max_speed=0))
    check = report.to_dict()['checks']['motion-quality']
    assert check['status'] == 'failed'
    finding = check['results'][0]['evidence']['report']['quality_findings'][0]
    assert finding['actual'] > finding['limit'] == 0
    assert finding['time'] is not None and finding['remedy']


def test_cached_preflight_report_remains_available_in_a_new_build():
    profile = QualityProfile('measured', max_speed=100)
    prepared = _Preparation()
    compile_with(profile, prepared=prepared)
    with build_report.capture() as report:
        compile_with(profile, prepared=prepared)
    check = report.to_dict()['checks']['motion-quality']
    assert check['status'] == 'passed'
    assert check['results'][0]['evidence']['cached'] is True


def test_calibration_scope_refusal_is_failed_evidence():
    profile = QualityProfile('calibrated', max_speed=100, scope=QualityScope('gloss', 24))
    with build_report.capture() as report, pytest.raises(LimbError) as caught:
        compile_with(profile)
    assert caught.value.code == 'quality.scope'
    check = report.to_dict()['checks']['motion-quality']
    assert check['status'] == 'failed'
    assert check['results'][0]['evidence']['error']['code'] == 'quality.scope'


@pytest.mark.parametrize(
    'limit,policy,required,expected',
    [(100, 'error', True, 0), (0, 'warn', False, 0), (0, 'warn', True, 1), (0, 'error', False, 1)],
)
def test_cli_exposes_quality_evidence_and_enforces_required_check(tmp_path, capsys, limit, policy, required, expected):
    script = tmp_path / 'build.py'
    script.write_text(
        'from sr_core.scene import Scene\n'
        'from srstudio import Canvas\n'
        'from srstudio.limbs import HUMAN, ArmProfile\n'
        'from srstudio.limbs.motion import Motion, Action\n'
        'from srstudio.limbs.compile import bake, BakeOptions\n'
        'from srstudio.limbs.validation import QualityProfile\n'
        'cv = Canvas(Scene(version="auto"), font_asset=None)\n'
        'motion = Motion(ArmProfile(), HUMAN, (Action("point", duration=1),))\n'
        f'quality = QualityProfile("test", max_speed={limit}, policy={policy!r})\n'
        'bake(cv, cv.comp, motion, id="arm", options=BakeOptions(fps=4, quality=quality))\n'
    )
    args = ['build', '--json', *(['--require-check', 'motion-quality'] if required else []), str(script)]
    assert cli.main(args) == expected
    output = capsys.readouterr()
    data = json.loads(output.out) if expected == 0 else json.loads(output.err)['context']['build']
    assert data['checks']['motion-quality']['status'] == ('passed' if limit else 'failed')


def test_noop_cannot_satisfy_required_motion_quality(tmp_path, capsys):
    script = tmp_path / 'build.py'
    script.write_text('pass\n')
    assert cli.main(['build', '--json', '--require-check', 'motion-quality', str(script)]) == 1
    result = json.loads(capsys.readouterr().err)
    assert result['context']['build']['checks']['motion-quality']['status'] == 'skipped'


@pytest.mark.parametrize('backend', ['native', 'interaction'])
def test_all_compiler_backends_retain_quality_evidence(backend):
    cv = Canvas(Scene(version='auto'), font_asset=None)
    motion = Motion(ArmProfile(), HUMAN)
    options = BakeOptions(fps=4, duration=1, quality=QualityProfile('measured', max_speed=100))
    with build_report.capture() as report:
        if backend == 'native':
            compile_motion(cv, cv.comp, motion, id='arm', backend='native', options=options)
        else:
            bake_interaction(cv, cv.comp, (Participant('arm', motion),), (), id='interaction', options=options)
    check = report.to_dict()['checks']['motion-quality']
    assert check['status'] == 'passed'
    assert all(row['evidence']['sampling']['fps'] == 4 for row in check['results'])


def test_a_later_pass_does_not_hide_an_unprofiled_or_failing_audit():
    with build_report.capture() as report:
        compile_with(None)
        compile_with(QualityProfile('passing', max_speed=100))
        assert report.to_dict()['checks']['motion-quality']['status'] == 'skipped'
        compile_with(QualityProfile('failing', max_speed=0, policy='warn'))
        compile_with(QualityProfile('passing', max_speed=100))
    assert report.to_dict()['checks']['motion-quality']['status'] == 'failed'


def test_insufficient_derivative_samples_do_not_claim_a_zero_measurement_pass():
    cv = Canvas(Scene(version='auto'), font_asset=None)
    motion = Motion(ArmProfile(), HUMAN)
    with build_report.capture() as report, pytest.raises(LimbError):
        bake(
            cv,
            cv.comp,
            motion,
            id='arm',
            options=BakeOptions(fps=1, duration=1, quality=QualityProfile('jerk', max_jerk=100)),
        )
    row = report.to_dict()['checks']['motion-quality']['results'][0]
    assert row['status'] == 'failed'
    assert row['evidence']['report']['quality_findings'][0]['code'] == 'quality.evidence'
