"""Gesture accents stop with zero acceleration, including their added arcs."""

from dataclasses import replace

import pytest

from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion, MotionStyle


@pytest.mark.parametrize('style', [MotionStyle(), MotionStyle(overshoot=0.15), MotionStyle(asymmetry=0.3)])
@pytest.mark.parametrize('boundary', ['start', 'stroke_start', 'stroke_end', 'end'])
def test_wrist_acceleration_agrees_on_both_sides_of_phase_boundaries(style, boundary):
    action = Action('present', start=1, style=style)
    motion = Motion(ArmProfile(), HUMAN, (action,))
    edge = {
        'start': action.start,
        'stroke_start': action.start + action.preparation * action.duration,
        'stroke_end': action.stroke_at,
        'end': action.end,
    }[boundary]
    h = 1e-6
    points = [motion.sample(edge + i * h).arm.wrist for i in (-2, -1, 0, 1, 2)]
    left = (points[0] - points[1] * 2 + points[2]) / h**2
    right = (points[4] - points[3] * 2 + points[2]) / h**2
    assert left.distance(right) < 0.03


def test_legacy_envelope_is_explicit_and_persists_without_changing_old_documents():
    from srstudio.limbs.serialization import motion_dict, parse_motion

    modern = Motion(ArmProfile(), HUMAN, (Action('present'),))
    legacy = replace(modern, actions=(replace(modern.actions[0], style=MotionStyle(envelope='legacy')),))
    old = motion_dict(legacy)
    assert old['schema'] == 'srstudio.limbs/1.3.0'
    assert 'envelope' not in old['motion']['actions'][0]['style']
    assert parse_motion(old).sample(0.3) == legacy.sample(0.3)
    new = motion_dict(modern)
    assert new['schema'] == 'srstudio.limbs/1.4.0'
    assert parse_motion(new).sample(0.3) == modern.sample(0.3)
    assert modern.sample(0.3) != legacy.sample(0.3)


def test_legacy_document_with_an_omitted_style_keeps_original_defaults():
    from srstudio.limbs.serialization import motion_dict, parse_motion

    original = Motion(ArmProfile(), HUMAN, (Action('present', style=MotionStyle(envelope='legacy')),))
    data = motion_dict(original)
    del data['motion']['actions'][0]['style']
    restored = parse_motion(data)
    assert restored.sample(0.3) == original.sample(0.3)
