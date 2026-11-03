"""Acting controls fail clearly and preserve smooth, bounded motion."""

import json
import math
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, cast, describe
from srstudio import head_motion as hm
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion, MotionStyle, smooth
from srstudio.rig import Performance, RigError
from srstudio.toon import Pose
from srstudio.toon_critters import GOAT_RIG, HAMSTER_RIG, SLOTH_RIG
from srstudio.toon_head import figure
from support.spring_curve import peak


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=20)
    return Canvas(scene, font_asset=None)


def test_unsafe_spring_tuning_is_rejected_against_the_actual_channel_response():
    style = replace(GOAT_RIG.style, settle=hm.Spring(2, 0.2))
    with pytest.raises(hm.HeadMotionError, match=r'(turn|face_x).*bound'):
        hm.plan(style, [], 20, facing=((0, 18, 1),))


@pytest.mark.parametrize('frequency, damping', [(0.8, 0.5), (2, 0.99999), (2, 1), (2, 1.00001), (2, 1.6)])
def test_safe_spring_tuning_remains_available(frequency, damping):
    style = replace(GOAT_RIG.style, settle=hm.Spring(frequency, damping))
    plan = hm.plan(style, [], 20, facing=((0, 18, 1),))
    for name in ('turn', 'face_x'):
        assert peak(getattr(plan, name)) <= hm.limit(style, name)


@pytest.mark.parametrize('damping', [0.2, 1, 1.6])
def test_continuous_response_bounds_enclose_renderer_samples(scene_render, tmp_path, damping):
    from srstudio.toon_head import _animate

    channel = hm.Channel(((0, 0), (0.3, 1), (0.5, -1), (0.7, 0.5), (1, 0)), hm.Spring(2, damping))
    _, (low, high) = hm._sample_spring(channel)
    cv = canvas()
    group = cv.group(cv.comp, 'spring')
    _animate(cv, group, 'x', channel)
    path = tmp_path / 'spring.xml'
    path.write_bytes(cv.scene.to_bytes())
    for t in (0.05, 0.15, 0.27, 0.31, 0.41, 0.51, 0.63, 0.78, 0.91):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(t), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(result.stdout)['result']['nodes']
        value = next(node['world'][4] for node in nodes if node['id'] == 'spring')
        assert low - 1e-6 <= value <= high + 1e-6


def test_manual_spring_plan_is_validated_before_drawing():
    cv = canvas()
    plan = hm.HeadPlan(face_x=hm.Channel(((0, 0), (0.5, 7), (18, 7), (18.6, 0)), hm.Spring(2, 0.2)))
    before = cv.scene.to_bytes()
    with pytest.raises(hm.HeadMotionError, match='face_x.*bound'):
        figure(cv, cv.comp, GOAT_RIG, [Pose(0, 'wide', 'flat', 'desk')], 20, plan)
    assert cv.scene.to_bytes() == before


def test_a_plan_for_a_larger_motion_envelope_cannot_silently_override_another_rig():
    cv = canvas()
    plan = hm.plan(SLOTH_RIG.style, [], 8)
    before = cv.scene.to_bytes()
    with pytest.raises(hm.HeadMotionError, match='face_x.*bound'):
        figure(cv, cv.comp, HAMSTER_RIG, [Pose(0, 'wide', 'flat', 'desk')], 8, plan)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('actor_type', [cast.Manager, cast.Candidate, cast.Barista, cast.Customer])
def test_unknown_mouth_state_fails_with_allowed_values_before_geometry(actor_type):
    cv = canvas()
    actor = actor_type(cv)
    before = cv.scene.to_bytes()
    with pytest.raises(RigError, match=r'mouth.*closed.*rest.*round.*open.*small.*smile'):
        actor.build(cv.comp, 0, 0, 1, Performance(mouth=((0, 'closed'),)))
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'mouth', [((-0.1, 'open'),), ((float('nan'), 'open'),), ((1, 'open'), (0, 'rest')), (('bad',),)]
)
def test_malformed_mouth_tracks_fail_before_drawing(mouth):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(RigError, match='mouth'):
        cast.Manager(cv).build(cv.comp, 0, 0, 1, Performance(mouth=mouth))
    assert cv.scene.to_bytes() == before


def test_custom_actor_can_declare_an_additional_mouth_pose():
    class LaughingManager(cast.Manager):
        mouth_poses = (*cast.Manager.mouth_poses, 'laugh')

        def draw_mouths(self, head):
            return {**super().draw_mouths(head), 'laugh': self.cv.ellipse(head, -10, 40, 20, 20, '#000000')}

    cv = canvas()
    actor = LaughingManager(cv)
    actor.build(cv.comp, 0, 0, 1, Performance(mouth=((0, 'laugh'),)))
    assert 'laugh' in actor.mouths
    assert cv.scene.check() == []


@pytest.mark.parametrize('side', ['left', 'right'])
@pytest.mark.parametrize('overshoot', [0, 0.4])
def test_finger_blending_has_continuous_velocity_at_anticipation_and_saturation(side, overshoot):
    action = Action('grasp', duration=1, style=MotionStyle(overshoot=overshoot))
    motion = Motion(ArmProfile(side=side), HUMAN, (action,))

    def amount(u):
        return -0.05 + 1.05 * smooth(u) + overshoot * math.sin(math.pi * u) ** 2

    edges = []
    for threshold in (0, 1):
        # Find crossings within the stroke, including both sides of an overshoot.
        for i in range(100):
            lo, hi = i / 100, (i + 1) / 100
            if (amount(lo) - threshold) * (amount(hi) - threshold) >= 0:
                continue
            for _ in range(45):
                mid = (lo + hi) / 2
                if (amount(lo) - threshold) * (amount(mid) - threshold) <= 0:
                    hi = mid
                else:
                    lo = mid
            edges.append(action.preparation + action.stroke * (lo + hi) / 2)
    assert edges
    for at in edges:
        h = 1e-6
        a, b, c = (motion.sample(t).hand.digit('index').points[-1] for t in (at - h, at, at + h))
        assert ((b - a) / h).distance((c - b) / h) < 1e-3


def test_bento_inspection_explains_and_executes_its_mood_accelerator():
    info = describe('character', 'toon-bento')
    for contract in ('pose_of', 'MOODS', 'EYE_STATES', 'GESTURES', 'seconds', 'limbs'):
        assert contract in info['documentation']
    assert info['examples']
    for example in info['examples']:
        cv = canvas()
        exec(example, {'ep': SimpleNamespace(cv=cv, comp=cv.comp)})
        assert list(cv.comp.iter('shape'))
        assert cv.scene.check() == []
