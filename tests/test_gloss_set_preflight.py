"""Agent repair attempts must not retain a partial Gloss room, card or graphic."""

import pytest

from srstudio import gloss_sets as sets
from srstudio.gloss import GlossError
from support.gloss import canvas, font

TOO_WIDE = 'W' * 100
CASES = [
    ('activity', {'number': 'X'}, 'digits only'),
    ('waiting', {'serving': ((0, ''),)}, 'digits only'),
    ('waiting', {'serving': ((0, '3'), (1, 'X'))}, 'digits only'),
    ('ticket', {'at': (500, 1000), 'number': ''}, 'digits only'),
    ('board', {'cards': (sets.Card(0, TOO_WIDE),)}, 'wider'),
    ('board', {'cards': (sets.Card(0, 'OK'), sets.Card(1, TOO_WIDE))}, 'wider'),
    ('board', {'cards': (sets.Card(0, 'OK', body=TOO_WIDE),)}, 'wider'),
    ('board', {'cards': (sets.Card(0, 'OK'), sets.Card(1, 'NEXT', body=TOO_WIDE))}, 'wider'),
    ('board', {'cards': (sets.Card(0, 'OK', body='A body'),), 'box': (100, 300, 800, 150)}, 'needs'),
    ('hook', {'text': TOO_WIDE}, 'wider'),
    ('notice', {'title': TOO_WIDE, 'body': 'OK'}, 'wider'),
    ('notice', {'title': 'OK', 'body': TOO_WIDE}, 'wider'),
    ('hook', {'text': 'OK', 'talk': ((0, 'unknown-mouth'),)}, 'talk'),
    ('notice', {'title': 'OK', 'body': 'A body', 'talk': ((0, 'unknown-mouth'),)}, 'talk'),
]


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('name,options,message', CASES)
def test_gloss_sets_preflight_all_copy_and_delegated_talk_before_any_scene_or_id_mutation(
    local, name, options, message
):
    cv, control = canvas(), canvas()
    cv.local_time = control.local_time = local
    before = cv.scene.to_bytes()
    kwargs = dict(options, end=4)
    if name in ('board', 'hook', 'notice'):
        kwargs['font'] = font()
    with pytest.raises(GlossError, match=message):
        getattr(sets, name)(cv, cv.comp, **kwargs)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')
    assert cv.local_time is local


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name,options',
    [
        ('board', {'cards': (sets.Card(0, 'OK'),)}),
        ('hook', {'text': 'OK'}),
        ('notice', {'title': 'OK', 'body': 'A body'}),
    ],
)
def test_gloss_text_builders_require_a_bound_font_before_drawing(local, name, options):
    cv, control = canvas(), canvas()
    cv.local_time = local
    cv.font_asset = None
    before = cv.scene.to_bytes()
    with pytest.raises(GlossError, match='font'):
        getattr(sets, name)(cv, cv.comp, **options, end=4, font=font())
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('serving', [((0, '3'), (0, '4')), ((False, '3'),)])
def test_waiting_room_checks_the_first_cue_and_its_order_before_drawing(local, serving):
    cv, control = canvas(), canvas()
    cv.local_time = local
    before = cv.scene.to_bytes()
    with pytest.raises(GlossError, match='NOW SERVING'):
        sets.waiting(cv, cv.comp, end=4, serving=serving)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')
