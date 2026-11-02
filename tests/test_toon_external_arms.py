"""A candidate can delegate an arm without drawing or recording a duplicate hand."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, toon_head
from srstudio.character_clips import Interval, ToonClip, place_character
from srstudio.head_motion import HeadMotionError, HeadPlan
from srstudio.toon import Pose
from srstudio.toon_bento import BENTO_RIG_2
from srstudio.toon_cast import _arms


def stage():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    return Canvas(scene, font_asset=None)


def draw(cv, sides, route, *, rig=None, poses=None):
    rig = rig or replace(BENTO_RIG_2, drawn_as=None)
    poses = poses or (Pose(0, eyes='neutral', mouth='neutral', arms='desk'),)
    if route == 'direct':
        return toon_head.figure(cv, cv.comp, rig, poses, 2, HeadPlan.still(), external_arms=sides)
    return place_character(cv, cv.comp, ToonClip(rig, poses, external_arms=sides), interval=Interval(0, 2), id='actor')


@pytest.mark.parametrize('route', ['direct', 'clip'])
@pytest.mark.parametrize('sides', [(), ('left',), ('right',), ('left', 'right')])
def test_external_arms_remove_only_the_requested_native_hands(route, sides):
    cv = stage()
    draw(cv, sides, route)
    root = ET.fromstring(cv.scene.to_bytes())
    baseline = stage()
    draw(baseline, (), route)
    original = ET.fromstring(baseline.scene.to_bytes())
    look = BENTO_RIG_2.look
    before = sum(map(len, _arms(look, 'desk', 0)))
    after = sum(map(len, _arms(look, 'desk', 0, frozenset(sides))))
    assert len(list(original.iter('shape'))) - len(list(root.iter('shape'))) == before - after
    assert {hand.side.name.lower() for hand in cv.limbs.values()} == {'left', 'right'} - set(sides)
    assert cv.scene.check(schema=True) == []
    if not sides:
        assert cv.scene.to_bytes() == baseline.scene.to_bytes()


@pytest.mark.parametrize('route', ['direct', 'clip'])
@pytest.mark.parametrize('sides', [None, [], 'right', (True,), ('other',), ('right', 'right'), ('left',) * 3])
def test_malformed_external_ownership_is_typed_and_atomic(route, sides):
    cv = stage()
    before = cv.scene.to_bytes()
    with pytest.raises(HeadMotionError) as caught:
        draw(cv, sides, route)
    assert caught.value.to_dict()['path'] == 'external_arms'
    assert cv.scene.to_bytes() == before and not cv.limbs


@pytest.mark.parametrize('route', ['direct', 'clip'])
@pytest.mark.parametrize('conflict', ['approved', 'named-gesture'])
def test_external_ownership_refuses_approved_identity_and_indivisible_gestures(route, conflict):
    cv = stage()
    before = cv.scene.to_bytes()
    rig = BENTO_RIG_2 if conflict == 'approved' else replace(BENTO_RIG_2, drawn_as=None)
    poses = (Pose(0, eyes='neutral', mouth='neutral', arms='desk'),)
    if conflict == 'named-gesture':
        poses += (Pose(1, eyes='neutral', mouth='neutral', arms='tablet'),)
    with pytest.raises(HeadMotionError):
        draw(cv, ('right',), route, rig=rig, poses=poses)
    assert cv.scene.to_bytes() == before and not cv.limbs


@pytest.mark.parametrize('poses', [(), (object(),), (Pose(0, 'neutral', 'neutral', 'desk'),) * 20001])
def test_external_ownership_bounds_and_validates_the_complete_pose_sequence(poses):
    cv = stage()
    before = cv.scene.to_bytes()
    with pytest.raises(HeadMotionError):
        toon_head.figure(
            cv, cv.comp, replace(BENTO_RIG_2, drawn_as=None), poses, 2, HeadPlan.still(), external_arms=('right',)
        )
    assert cv.scene.to_bytes() == before and not cv.limbs


def test_drawing_specific_override_of_a_shared_pose_cannot_be_partially_omitted():
    from srstudio.toon_bento import Bento

    class OwnDesk(Bento):
        def gesture(self, arms):
            return [], []

    cv = stage()
    rig = replace(BENTO_RIG_2, drawn_as=None, look=replace(BENTO_RIG_2.look, drawing=OwnDesk(number=2)))
    before = cv.scene.to_bytes()
    with pytest.raises(HeadMotionError):
        draw(cv, ('right',), 'direct', rig=rig)
    assert cv.scene.to_bytes() == before and not cv.limbs


@pytest.mark.parametrize('gesture', ['type', 'crossed', 'sigh', 'face', 'face2', 'lean'])
def test_delegation_reaches_alternate_arm_painter_paths(gesture):
    cv = stage()
    draw(cv, ('right',), 'clip', poses=(Pose(0, eyes='neutral', mouth='neutral', arms=gesture),))
    assert {hand.side.name.lower() for hand in cv.limbs.values()} == {'left'}
    assert cv.scene.check(schema=True) == []


def test_documented_external_arm_recipe_executes():
    from pathlib import Path

    text = (Path(__file__).parents[1] / 'docs/authoring-acting.md').read_text()
    section = text.split('## External arms on a candidate Toon figure')[1].split('## Coordinated acting')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'external-arm-recipe', 'exec'), namespace)
    assert namespace['clip'].external_arms == ('right',)
