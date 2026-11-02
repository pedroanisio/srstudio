"""Target tracking moves declared pupil layers without moving lids or changing legacy drawings."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, gaze, toon, toon_critters, toon_head, toon_inked
from srstudio.character_clips import Interval, ToonClip, place_character
from srstudio.head_motion import Channel, HeadPlan

RIGS = (toon_critters.SLOTH_RIG, toon_inked.FOX_RIG)


def plan():
    return gaze.GazePlan(
        gaze.GazeSpec(gaze.TargetTrack((gaze.TargetKey(0, (0, 0, 2)), gaze.TargetKey(0.5, (0.6, 0.2, 2)))), 1, fps=24)
    )


def scene():
    result = Scene(version='auto')
    result.add_project(width=1080, height=1920, fps='24', duration=2)
    return result, Canvas(result, font_asset=None)


@pytest.mark.parametrize('rig', RIGS, ids=('sloth', 'inked-fox'))
@pytest.mark.parametrize('kind', toon.EYES)
def test_declared_eye_layers_preserve_the_authored_geometry_and_order(rig, kind):
    drawing = rig.look.drawing
    for centre, side in zip(rig.look.eyes, (1, -1), strict=True):
        tracked = drawing.tracked_eye(rig.look, centre, kind, side)
        assert tracked.layers == tuple(drawing.eye(rig.look, centre, kind, side))
        assert len(set(tracked.moving)) == len(tracked.moving)
        assert all(0 <= i < len(tracked.layers) for i in tracked.moving)
        assert bool(tracked.moving) == (kind not in ('hearts', 'closed', 'wince'))
        assert tracked.radius > 0


@pytest.mark.parametrize('rig', RIGS, ids=('sloth', 'inked-fox'))
def test_target_gaze_emits_linear_pupil_transforms_and_delayed_head_follow(rig):
    result, cv = scene()
    toon_head.figure(cv, cv.comp, rig, (toon.Pose(0, 'wide', 'flat', 'desk'),), 1, HeadPlan.still(), target_gaze=plan())
    assert result.check() == []
    root = ET.fromstring(result.to_bytes())
    pupils = [n for n in root.iter('group') if n.get('id', '').startswith('gaze-pupil-')]
    assert len(pupils) == 2
    assert all({a.get('property') for a in n.findall('animate')} == {'x', 'y'} for n in pupils)
    assert all(a.get('defaultInterpolation') == 'linear' for n in pupils for a in n.findall('animate'))
    assert all(float(n.find("animate[@property='x']/key").get('value')) == 0 for n in pupils)
    face = next(n for n in root.iter('group') if n.get('id', '').startswith('face-'))
    assert face.find("animate[@property='x']") is not None


def test_capability_refusal_happens_before_any_scene_mutation():
    result, cv = scene()
    rig = replace(RIGS[0], look=replace(RIGS[0].look, drawing=None))
    before = result.to_bytes()
    with pytest.raises(gaze.GazeError) as caught:
        toon_head.figure(
            cv, cv.comp, rig, (toon.Pose(0, 'wide', 'flat', 'desk'),), 1, HeadPlan.still(), target_gaze=plan()
        )
    assert caught.value.to_dict()['code'] == 'gaze.unsupported'
    assert result.to_bytes() == before


def test_target_and_named_gaze_cannot_silently_own_the_same_eyes():
    result, cv = scene()
    before = result.to_bytes()
    with pytest.raises(gaze.GazeError):
        toon_head.figure(
            cv,
            cv.comp,
            RIGS[0],
            (toon.Pose(0, 'wide', 'flat', 'desk'),),
            1,
            HeadPlan(gaze=((0, 'left'),)),
            target_gaze=plan(),
        )
    assert result.to_bytes() == before


def test_added_head_follow_is_checked_against_the_actual_rig_envelope():
    result, cv = scene()
    before = result.to_bytes()
    from srstudio.head_motion import HeadMotionError, limit

    base = HeadPlan(face_x=Channel(((0, limit(RIGS[0].style, 'face_x')), (1, limit(RIGS[0].style, 'face_x')))))
    with pytest.raises(HeadMotionError):
        toon_head.figure(cv, cv.comp, RIGS[0], (toon.Pose(0, 'wide', 'flat', 'desk'),), 1, base, target_gaze=plan())
    assert result.to_bytes() == before


def test_character_clip_carries_target_gaze_on_its_local_source_clock():
    result, cv = scene()
    clip = ToonClip(RIGS[0], (toon.Pose(0, 'wide', 'flat', 'desk'),), target_gaze=plan())
    node = place_character(cv, cv.comp, clip, interval=Interval(1, 2))
    assert node.timeOffset == 1 and result.check() == []
    pupils = [n for n in node.iter('group') if n.id.startswith('gaze-pupil-')]
    assert len(pupils) == 2
    assert all(a.timeBase == 'local' for n in pupils for a in n.iter('animate'))


def test_target_gaze_failure_rolls_back_scene_and_canvas_ids():
    result, cv = scene()
    before = result.to_bytes()

    def fail(parent):
        cv.group(parent, 'partial')
        raise RuntimeError('after eyes')

    with pytest.raises(RuntimeError, match='after eyes'):
        toon_head.figure(
            cv,
            cv.comp,
            RIGS[0],
            (toon.Pose(0, 'wide', 'flat', 'desk'),),
            1,
            HeadPlan.still(),
            on_face=fail,
            target_gaze=plan(),
        )
    assert result.to_bytes() == before
