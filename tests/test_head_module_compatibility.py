"""Pre-extraction public, numeric and emission contracts for the head-motion modules.

The fixture was captured from fdae9a22 before moving any implementation. Numeric
samples are rounded to nine decimals; XML and protocol-4 record bytes are exact.
"""

import base64
import hashlib
import importlib
import inspect
import json
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import get_type_hints

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio import head_motion as hm
from srstudio.toon_head import _animate
from srstudio.voice import Alignment

FIXTURE = Path(__file__).with_name('data') / 'head-motion-compatibility.json'
CURVES = (
    'linear',
    'hold',
    'step',
    'steps',
    'ease-in',
    'ease-out',
    'ease-in-out',
    'cubic-bezier',
    'catmull-rom',
    'tcb',
    'spring',
    *(
        f'{family}-{direction}'
        for family in ('sine', 'quad', 'cubic', 'quart', 'quint', 'expo', 'circ', 'bounce', 'back', 'elastic')
        for direction in ('in', 'out', 'in-out')
    ),
)
TIMES = (
    -0.1,
    0,
    0.000001,
    0.3,
    0.5,
    0.999999,
    1,
    1.000001,
    1.499999,
    1.5,
    1.500001,
    1.9,
    2.499999,
    2.5,
    2.500001,
    3,
    4,
    5,
    5.499999,
    5.5,
    5.500001,
    6,
    6.999999,
    7,
    7.000001,
    7.6,
    8,
    9,
)


def style():
    return hm.HeadStyle(7, '^', 6, 1, hm.Spring(1.4, 1.0, 0.1), hm.Spring(0.8, 0.9), hm.Spring(1, 1))


def speech(text='We really need better coffee.', at=1.0):
    alignment = Alignment(
        tuple(text), tuple(i * 0.08 for i in range(len(text))), tuple((i + 1) * 0.08 for i in range(len(text)))
    )
    levels = tuple(-12.0 if i % 40 < 12 else -24.0 for i in range(len(text) * 8 + 50))
    return hm.Speech(at, hm.words_of(alignment, at), levels)


def channels():
    keys = ((0.0, 0.0), (1.0, 1.0), (1.7, -0.5), (2.5, 0.25), (4.0, 0.0))
    result = {curve: hm.Channel(keys, curve=curve) for curve in CURVES}
    for damping in (0.2, 1.0, 1.5):
        result[f'carried-{damping}'] = hm.Channel(keys, hm.Spring(1.4, damping))
    result['long-carried'] = hm.Channel(tuple((i * 0.4, (i % 3 - 1) * 0.5) for i in range(12)), hm.Spring(1.4, 0.7))
    result['empty'] = hm.Channel()
    result['held'] = hm.Channel(((0.0, 0.125),))
    return result


def emitted(channel):
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=10)
    cv = Canvas(scene, font_asset=None)
    _animate(cv, cv.group(cv.comp, 'whole'), 'x', channel)
    _animate(cv, cv.group(cv.comp, 'cut'), 'x', channel.during(1.5, 2.5))
    return hashlib.sha256(scene.to_bytes()).hexdigest()


def observe_channel(channel):
    cut = channel.during(1.5, 2.5)
    return {
        'samples': [round(channel.sample(t), 9) for t in TIMES],
        'cut_samples': [round(cut.sample(t), 9) for t in TIMES if 1.5 <= t <= 2.5],
        'xml_sha256': emitted(channel),
    }


def records():
    line = speech()
    return {
        'Spring': style().head,
        'Channel': channels()['long-carried'],
        'HeadStyle': style(),
        'HeadPlan': hm.HeadPlan.still(),
        'Word': line.words[0],
        'Speech': line,
        'Accent': hm.accents(line, style())[0],
        'Nod': hm.nods(line, style())[0],
        'HeadMotionError': hm.HeadMotionError(
            'test failure', code='test', path='style', actual=0, expected=1, remedy='repair'
        ),
    }


def observe_plan():
    line = speech()
    result = hm.plan(style(), [line], 8, heard=(speech('Please listen.', 4.0),), facing=((5.5, 7.0, -1),))
    return {
        'channels': {name: observe_channel(getattr(result, name)) for name in hm.CHANNELS},
        'gaze': result.gaze,
        'accents': [asdict(value) for value in hm.accents(line, style())],
        'nods': [asdict(value) for value in hm.nods(line, style())],
        'listening': [asdict(value) for value in hm.listening(line, style(), 1)],
        'dips': hm.dips(line),
        'stress': [hm.stress(word) for word in ('really', 'coffee', 'unlistedxyz')],
        'noise': [hm.fbm(t, 0.15, 7, 'idle') for t in TIMES],
    }


def capture():
    """Explicit baseline capture helper; normal tests only read the committed fixture."""
    return {
        'schema_version': '1.0.0',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'source_commit': 'fdae9a22',
        'exports': hm.__all__,
        'signatures': {
            name: str(inspect.signature(getattr(hm, name)))
            for name in hm.__all__
            if callable(getattr(hm, name)) and name != 'Facing'
        },
        'channels': {name: observe_channel(channel) for name, channel in channels().items()},
        'plan': observe_plan(),
        'records': {
            name: base64.b64encode(pickle.dumps(value, protocol=4)).decode() for name, value in records().items()
        },
    }


@pytest.fixture(scope='module')
def baseline():
    return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize(
    'name', [*CURVES, 'carried-0.2', 'carried-1.0', 'carried-1.5', 'long-carried', 'empty', 'held']
)
def test_channel_samples_cuts_and_emitted_keys_match_before_extraction(name, baseline):
    assert observe_channel(channels()[name]) == baseline['channels'][name]


def test_speaking_listening_facing_and_noise_match_before_extraction(baseline):
    assert json.loads(json.dumps(observe_plan())) == baseline['plan']


def test_public_exports_and_signatures_remain_compatible(baseline):
    assert hm.__all__ == baseline['exports']
    for name, signature in baseline['signatures'].items():
        assert str(inspect.signature(getattr(hm, name))) == signature


@pytest.mark.parametrize(
    'name', ['Spring', 'Channel', 'HeadStyle', 'HeadPlan', 'Word', 'Speech', 'Accent', 'Nod', 'HeadMotionError']
)
def test_old_and_new_pickles_retain_the_public_record_path(name, baseline):
    expected = base64.b64decode(baseline['records'][name])
    restored = pickle.loads(expected)
    assert type(restored) is getattr(hm, name)
    assert pickle.dumps(records()[name], protocol=4) == expected
    assert pickle.dumps(restored, protocol=4) == expected
    assert getattr(hm, name).__module__ == 'srstudio.head_motion'
    get_type_hints(getattr(hm, name))


@pytest.mark.parametrize(
    'module,names',
    [
        (
            '_head_channels',
            ('Spring', 'Channel', 'HeadMotionError', '_CURVES', '_bake_spring', '_sample_spring', '_channel_bounds'),
        ),
        ('_head_types', ('HeadStyle', 'HeadPlan', 'limit')),
        ('_head_speech', ('Word', 'Speech', 'Accent', 'Nod', 'speech_of', 'nods', 'listening')),
        ('_head_noise', ('hash_unit', 'noise', 'fbm')),
        ('_head_planner', ('plan',)),
    ],
)
def test_public_facade_reexports_one_implementation_per_concern(module, names):
    implementation = importlib.import_module(f'srstudio.{module}')
    for name in names:
        assert getattr(hm, name) is getattr(implementation, name)


def test_channel_mechanics_share_curve_math_and_do_not_import_behavior_planners():
    import ast

    from srstudio import _curves

    channels = importlib.import_module('srstudio._head_channels')
    assert channels.progress is _curves.progress
    assert channels.spring_response is _curves.spring_response
    assert channels.spline_coefficients is _curves.spline_coefficients
    source = ast.parse(inspect.getsource(channels))
    imports = [node.module for node in ast.walk(source) if isinstance(node, ast.ImportFrom)]
    assert not {'head_motion', '_head_planner', '_head_speech', '_head_types'} & set(imports)
