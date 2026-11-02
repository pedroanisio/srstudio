"""Saga authoring failures must leave the scene and its ID allocation unchanged."""

import pytest

from srstudio import saga
from srstudio import saga_sets as sets
from srstudio.saga import SagaError
from support.gloss import font
from support.saga import canvas

WIDE = 'W' * 100
CASES = [
    (sets.holo, {'panels': (sets.Panel(0, WIDE),)}, 'wider'),
    (sets.holo, {'panels': (sets.Panel(0, 'OK'), sets.Panel(1, WIDE))}, 'wider'),
    (sets.holo, {'panels': (sets.Panel(0, 'OK', body=WIDE),)}, 'wider'),
    (sets.holo, {'panels': (sets.Panel(0, 'OK'), sets.Panel(1, 'NEXT', body=WIDE))}, 'wider'),
    (sets.holo, {'panels': (sets.Panel(0, 'OK', 'A body'),), 'box': (100, 300, 800, 150)}, 'needs'),
    (sets.hook, {'text': WIDE}, 'wider'),
    (sets.entry, {'title': WIDE, 'body': 'OK'}, 'wider'),
    (sets.entry, {'title': 'OK', 'body': WIDE}, 'wider'),
    (saga.handbook, {'at': (100, 300), 'talk': ((0, 'unknown'),)}, 'viseme'),
    (saga.handbook, {'at': (100, 300), 'talk': ((0, 'open'), (0, 'closed'))}, 'second'),
    (saga.handbook, {'at': (100, 300), 'talk': ((-1, 'open'),)}, 'second'),
    (sets.hook, {'text': 'OK', 'talk': ((0, 'unknown'),)}, 'viseme'),
    (sets.entry, {'title': 'OK', 'body': 'A body', 'talk': ((0, 'unknown'),)}, 'viseme'),
    (sets.entry, {'title': 'OK', 'body': 'A body', 'talk': ((1, 'open'), (0.5, 'closed'))}, 'second'),
]


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('builder,options,message', CASES)
def test_copy_and_speech_preflight_is_atomic(local, builder, options, message):
    cv, control = canvas(), canvas()
    cv.local_time = local
    before = cv.scene.to_bytes()
    kwargs = dict(options, end=4)
    if builder is not saga.handbook:
        kwargs['font'] = font()
    with pytest.raises(SagaError, match=message):
        builder(cv, cv.comp, **kwargs)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')
    assert cv.local_time is local


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'builder,options',
    [
        (sets.holo, {'panels': (sets.Panel(0, 'OK'),)}),
        (sets.hook, {'text': 'OK'}),
        (sets.entry, {'title': 'OK', 'body': 'A body'}),
    ],
)
def test_text_builders_require_a_bound_font_before_emission(local, builder, options):
    cv, control = canvas(), canvas()
    cv.font_asset = None
    cv.local_time = local
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match='font'):
        builder(cv, cv.comp, **options, end=4, font=font())
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')
