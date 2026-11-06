"""Authoring cannot silently lose an action or a contact between output frames."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.validation import QualityProfile


@pytest.mark.parametrize('backend', ['baked', 'native', 'auto'])
@pytest.mark.parametrize('quality', [None, QualityProfile('strict', max_speed=0.001)])
@pytest.mark.parametrize('start', [0, 0.01])
def test_a_missed_action_is_refused_before_emission_with_a_repair_path(backend, quality, start):
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=1)
    cv = Canvas(scene, font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('present', start=start, duration=0.02),))
    before = scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        compile_motion(
            cv, cv.comp, motion, id='short', backend=backend, options=BakeOptions(duration=1, quality=quality)
        )
    error = caught.value.to_dict()
    assert error['code'] == 'motion.sampling'
    assert error['path'] == 'motion.actions[0]'
    assert error['remedy'] and error['context']['fps'] == 24
    assert scene.to_bytes() == before


def test_cropping_before_an_action_is_intentional():
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=1)
    cv = Canvas(scene, font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('point', start=2),))
    assert compile_motion(cv, cv.comp, motion, id='crop', options=BakeOptions(duration=1)).frames == 24


def test_contact_between_frames_is_refused_by_interaction_compilation():
    from dataclasses import replace

    from srstudio.limbs.interaction import Participant, bake_interaction
    from srstudio.limbs.motion import Contact, TransformTrack

    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None)
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=2),))
    motion = replace(base, contacts=(Contact('brief', 1.01, 1.02, TransformTrack.constant(base.sample(1).hand.frame)),))
    before = scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        bake_interaction(cv, cv.comp, (Participant('hand', motion),), (), id='brief')
    assert caught.value.to_dict()['path'] == 'motion.contacts[0]'
    assert scene.to_bytes() == before


def test_interaction_reports_subphases_missed_by_its_grid():
    from srstudio.limbs.interaction import Participant, bake_interaction

    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=1)
    cv = Canvas(scene, font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, (Action('present', duration=0.09),))
    result = bake_interaction(cv, cv.comp, (Participant('hand', motion),), (), id='phases')
    assert any(d.code == 'motion.phase-sampling' for d in result.diagnostics)
