"""Numeric, emitted and serialization compatibility across limb-motion boundaries.

The fixture was captured before extraction (83917174) and recaptured with capture()
at bf3724f3, after HUMAN's thumb gained a third segment in b38b6f11: only the cases
drawn with HUMAN changed, each in its thumb. Normal tests only read it; hashes of
numeric records round at twelve decimal places, while scene XML is byte exact.
"""

import base64
import hashlib
import importlib
import inspect
import json
import pickle
from contextlib import ExitStack
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HANDS, HUMAN, ArmProfile, Frame, Quaternion, Vec3
from srstudio.limbs import motion as public
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.motion import (
    Action,
    Attachment,
    Contact,
    Motion,
    MotionStyle,
    Target,
    TransformKey,
    TransformTrack,
    WordRef,
)
from srstudio.limbs.serialization import motion_dict, parse_motion

FIXTURE = Path(__file__).parent / 'data/limb-motion-compatibility.json'
TIMES = (0, 0.2, 0.5, 0.8, 1, 1.3, 1.5, 1.9, 2.2, 2.7, 3)
EMITTED_CASES = (
    'right-point',
    'joined',
    'continuous-root',
    'moving-contact',
    'finger-contact',
    'pole',
    'planar-left',
    'planar-right',
)


def cases():
    result = {
        f'{side}-{name}': Motion(ArmProfile(side=side), HUMAN, (Action(name, start=0.5, duration=2),))
        for side in ('left', 'right')
        for name in public.ACTIONS
    }
    for name, hand in HANDS.items():
        result[f'anatomy-{name}'] = Motion(ArmProfile(), hand, (Action('grasp', duration=3),))
    result['expressive'] = Motion(
        ArmProfile(),
        HUMAN,
        (
            Action(
                'wave',
                duration=3,
                style=MotionStyle(
                    amplitude=0.9, speed=1.2, overshoot=0.1, settling=0.15, tension=0.2, asymmetry=0.2, arc=0.08
                ),
            ),
        ),
    )
    root = TransformTrack(
        tuple(
            TransformKey(t, Frame(Vec3(x, 0, 0), Quaternion.axis_angle(Vec3(0, 0, 1), r)))
            for t, x, r in ((0, 0, 0), (1, 0.1, 0.05), (3, 0.3, -0.03))
        ),
        'continuous',
    )
    result['continuous-root'] = Motion(ArmProfile(), HUMAN, (Action('point', duration=3),), root=root)
    result['joined'] = Motion(
        ArmProfile(), HUMAN, (Action('present', duration=1.5), Action('point', start=1.5))
    ).chain()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=3),))
    grip = base.sample(1).hand.frame
    track = TransformTrack(
        (
            TransformKey(0, grip),
            TransformKey(
                3, Frame(grip.origin + Vec3(0.15, 0, 0), grip.rotation * Quaternion.axis_angle(Vec3(0, 1, 0), 0.1))
            ),
        )
    )
    result['moving-contact'] = replace(base, contacts=(Contact('cup', 1, 2, track),))
    offset = Frame(Vec3(0, 0.3, 0))
    result['attachment'] = replace(base, attachments=(Attachment('cup', 1, 2, grip.compose(offset), offset),))
    press = Motion(ArmProfile(), HUMAN, (Action('press', duration=3),))
    hand = press.sample(1).hand
    surface = TransformTrack.constant(Frame(hand.digit('index').points[-1], hand.frame.rotation))
    result['finger-contact'] = replace(press, contacts=(Contact('button', 1, 2, surface, digit='index'),))
    result['pole'] = Motion(ArmProfile(), HUMAN, (Action('rest', duration=3, pole=Vec3(0, 1, 0)),))
    for side in ('left', 'right'):
        result[f'planar-{side}'] = Motion(
            ArmProfile(side=side), HUMAN, (Action('point', duration=3, target=Target(Vec3(0.65, 0.3, 0))),)
        )
    return result


def normalized(value):
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalized(v) for v in value]
    return value


def numeric_hash(motion):
    payload = {
        'samples': [asdict(motion.sample(t)) for t in TIMES],
        'props': [[asdict(motion.prop_frame(a.name, t)) for t in TIMES] for a in motion.attachments],
    }
    return hashlib.sha256(json.dumps(normalized(payload), sort_keys=True, allow_nan=False).encode()).hexdigest()


def emitted(motion, backend):
    scene = Scene(version='auto')
    scene.add_project(width=640, height=640, fps='8', duration=3)
    cv = Canvas(scene, font_asset=None)
    before = scene.to_bytes()
    try:
        compiled = compile_motion(
            cv, cv.comp, motion, id='arm', backend=backend, options=BakeOptions(fps=8, duration=3)
        )
    except LimbError as error:
        assert backend == 'native' and error.code == 'capability'
        assert scene.to_bytes() == before
        return {'refused': error.code, 'message': error.message}
    assert scene.check(schema=True) == []
    return {
        'sha256': hashlib.sha256(scene.to_bytes()).hexdigest(),
        'frames': compiled.frames,
        'report': normalized(compiled.report.to_dict()),
    }


def records():
    motion = cases()['moving-contact']
    return [
        motion.root.keys[0],
        motion.root,
        Target(Vec3(1, 2, 3)),
        MotionStyle(),
        WordRef('take', 0),
        motion.actions[0],
        motion.contacts[0],
        cases()['attachment'].attachments[0],
        motion.sample(1),
        motion,
    ]


def capture():
    """Manual baseline capture only; never invoked by the regression tests."""
    motions = cases()
    return {
        'schema_version': '1.0.0',
        'generated_by': {'model': 'Claude Opus 5.5', 'tool': 'Claude Code'},
        'source_commit': 'bf3724f3',
        'numeric_rounding_decimal_places': 12,
        'numeric': {name: numeric_hash(m) for name, m in motions.items()},
        'emitted': {
            f'{name}/{backend}': emitted(motions[name], backend)
            for name in EMITTED_CASES
            for backend in ('baked', 'native')
        },
        'records': {
            type(record).__name__: {
                'signature': str(inspect.signature(type(record))),
                'pickle4': base64.b64encode(pickle.dumps(record, protocol=4)).decode(),
            }
            for record in records()
        },
    }


@pytest.fixture(scope='module')
def baseline():
    return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize('name', tuple(cases()))
def test_numeric_samples_match_baseline_and_random_access(name, baseline):
    motion = cases()[name]
    assert numeric_hash(motion) == baseline['numeric'][name]
    expected = {t: motion.sample(t) for t in TIMES}
    for time in reversed(TIMES):
        assert motion.sample(time) == expected[time]
    restored = parse_motion(motion_dict(motion))
    assert numeric_hash(restored) == baseline['numeric'][name]


@pytest.mark.parametrize('name', EMITTED_CASES)
@pytest.mark.parametrize('backend', ['baked', 'native'])
def test_emitted_scene_and_report_match_baseline(name, backend, baseline):
    result = emitted(cases()[name], backend)
    if name.startswith('planar-'):
        assert 'sha256' in result and result['frames'] == 24
    assert result == baseline['emitted'][f'{name}/{backend}']


@pytest.mark.parametrize('record', records(), ids=lambda record: type(record).__name__)
def test_record_identity_signatures_hints_and_old_pickles_are_preserved(record, baseline):
    kind = type(record)
    assert getattr(public, kind.__name__) is kind
    assert kind.__module__ == 'srstudio.limbs.motion'
    assert str(inspect.signature(kind)) == baseline['records'][kind.__name__]['signature']
    assert set(get_type_hints(kind)) == {f.name for f in fields(kind)}
    old = pickle.loads(base64.b64decode(baseline['records'][kind.__name__]['pickle4']))
    assert type(old) is kind and old == record
    assert pickle.loads(pickle.dumps(record, protocol=4)) == record


@pytest.mark.parametrize(
    'module,functions',
    [
        ('_motion_transforms', ('velocities', 'sample')),
        ('_motion_gestures', ('relative', 'request', '_blend', '_recipe')),
        ('_motion_contacts', ('request', 'position', 'resolve', 'diagnostics', 'prop_frame')),
        ('_motion_kinematics', ('pole_geometry', 'pole_path', 'pole', 'pose')),
        ('_motion_interpolation', ('smooth', 'tangent_weights')),
    ],
)
def test_each_implementation_concern_has_one_owner(module, functions):
    owner = importlib.import_module(f'srstudio.limbs.{module}')
    for name in functions:
        assert Path(inspect.getsourcefile(getattr(owner, name))).stem == module
    if module == '_motion_gestures':
        assert public._blend is owner._blend and public._recipe is owner._recipe
    if module == '_motion_interpolation':
        assert public.smooth is owner.smooth
        for consumer in ('_motion_transforms', '_motion_contacts', 'transitions'):
            assert importlib.import_module(f'srstudio.limbs.{consumer}').tangent_weights is owner.tangent_weights


def test_invalid_sampling_keeps_repair_context_after_delegation():
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=3, target=Target(Vec3(99, 0, 0), 'world')),))
    with pytest.raises(LimbError) as caught:
        public.sample_motion(motion, 1.5, track='presenter-right')
    assert caught.value.code == 'unreachable'
    assert caught.value.context == {
        'time': 1.5,
        'side': 'right',
        'action': 'point',
        'action_index': 0,
        'track': 'presenter-right',
    }


def test_shared_easing_preserves_public_function_introspection_and_pickle_identity():
    assert str(inspect.signature(public.smooth)) == "(value: 'float') -> 'float'"
    assert public.smooth.__module__ == 'srstudio.limbs.motion'
    assert pickle.loads(pickle.dumps(public.smooth, protocol=4)) is public.smooth


def test_public_sampling_uses_the_extracted_owners():
    owners = {
        '_motion_transforms': ('velocities', 'sample'),
        '_motion_gestures': ('relative', 'request'),
        '_motion_contacts': ('request', 'position', 'resolve', 'diagnostics', 'prop_frame'),
        '_motion_kinematics': ('pole_geometry', 'pole_path', 'pole', 'pose'),
    }
    with ExitStack() as stack:
        calls = {}
        for module, names in owners.items():
            owner = importlib.import_module(f'srstudio.limbs.{module}')
            for name in names:
                calls[f'{module}.{name}'] = stack.enter_context(patch.object(owner, name, wraps=getattr(owner, name)))
        for motion in cases().values():
            for time in TIMES:
                motion.sample(time)
                for attachment in motion.attachments:
                    motion.prop_frame(attachment.name, time)
        assert all(call.call_count for call in calls.values()), [
            name for name, call in calls.items() if not call.call_count
        ]
