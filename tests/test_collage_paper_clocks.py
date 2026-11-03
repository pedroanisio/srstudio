"""Paper face visibility and its turn share project seconds, including in sequence shots."""

from xml.etree import ElementTree as ET

import pytest

from srstudio import collage_everyday, collage_things
from support.acting import evaluate
from support.collage import canvas


@pytest.mark.parametrize('canvas_local', [False, True])
@pytest.mark.parametrize('override', [None, False, True])
def test_gate_accepts_a_clock_override_without_changing_canvas_default(canvas_local, override):
    cv = canvas()
    cv.local_time = canvas_local
    g = cv.group(cv.comp, 'visible')
    cv.gate(g, ((1, 2), (1.5, 3)), local=override)
    anim = ET.fromstring(cv.scene.to_bytes()).find('.//animate')
    expected = canvas_local if override is None else override
    assert anim.get('timeBase', 'composition') == ('local' if expected else 'composition')
    assert [(float(k.get('time')), float(k.get('value'))) for k in anim] == [(0, 0), (1, 1), (3, 0)]
    assert cv.local_time is canvas_local


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('kind', ['resume', 'flip-card'])
def test_paper_turn_and_face_visibility_always_use_project_seconds(kind, local):
    cv = canvas()
    cv.local_time = local
    if kind == 'resume':
        collage_things.resume(cv, cv.comp, 540, 900, turn=3)
    else:
        collage_everyday.flip_card(cv, cv.comp, ((0, 'YES'), (3, 'NO')))
    animations = list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))
    assert len(animations) == 3
    assert {a.get('timeBase', 'composition') for a in animations} == {'composition'}
    assert cv.local_time is local


@pytest.mark.parametrize('local', [False, True])
def test_resume_changes_to_blank_back_at_the_turn_midpoint_in_a_later_shot(local, scene_render, tmp_path):
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', start=0, end=2)
    shot = sequence.add_group(id='shot', start=0, end=3)
    paper = collage_things.resume(cv, shot, 540, 900, turn=3)
    tree = ET.fromstring(cv.scene.to_bytes())
    front, back = tree.find(f'.//group[@id="{paper.id}"]').findall('group')
    path = tmp_path / 'resume.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for time, expected in ((3.225, (0, 1)), (3.075, (1, 0)), (3.225, (0, 1))):
        nodes = {n['id']: n for n in evaluate(scene_render, path, time)}
        state = (nodes[front.get('id')]['world_opacity'], nodes[back.get('id')]['world_opacity'])
        assert state == expected
        states.append(state)
    assert states[0] == states[-1]
