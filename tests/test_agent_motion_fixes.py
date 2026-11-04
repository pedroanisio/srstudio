"""Agent samples and rendered poses agree through crops and placed clocks."""

import math
from dataclasses import replace

import pytest

from srstudio import _body_draw
from srstudio.acting import ActingScore, Overrides, compile_performance, gloss_actor
from srstudio.limbs import Camera, Frame, Quaternion
from srstudio.limbs.errors import LimbError
from srstudio.limbs.motion import Attachment
from support.acting import contact_track, evaluate
from support.body import canvas, plan


@pytest.mark.parametrize(
    'at,lead,offset,scale,cut',
    [(0.01, 0, 0, 1, 0), (0.01, 0.113, 0, 1, 0.25), (0.01, 0.113, 0.03, 0.7, 0.25), (0.01, 0.113, 0.03, 1.4, 0.25)],
)
def test_body_held_pose_uses_reel_clock(scene_render, tmp_path, monkeypatch, at, lead, offset, scale, cut):
    cv = canvas()
    parent = cv.comp
    if lead:
        seq = cv.comp.add_sequence(id='shots')
        seq.add_group(id='lead', end=lead)
        parent = seq.add_group(id='shot', end=4, timeOffset=offset, timeScale=scale)

    def geometry(pose, *args):
        return (_body_draw.Primitive(0, 'circle', ((pose.time, 0),), '#FFFFFF', 1),)

    def emit(cv, parent, primitives):
        marker = cv.group(parent, f'sample-{round(primitives[0].points[0][0] * 24)}')
        cv.ellipse(marker, 0, 0, 1, 1, '#FFFFFF')

    monkeypatch.setattr(_body_draw, 'geometry', geometry)
    monkeypatch.setattr(_body_draw, 'emit', emit)
    plan().window(cut, 2).place(cv, parent, at=at, camera=Camera(), fps=24)
    path = tmp_path / 'body.xml'
    path.write_bytes(cv.scene.to_bytes())
    for frame in (12, 16, 20):
        t = frame / 24
        source = (t - lead - offset) * scale - at + cut
        nodes = evaluate(scene_render, path, t)
        visible = [n['id'] for n in nodes if n['id'].startswith('sample-') and n['world_opacity'] > 0]
        assert visible == [f'sample-{math.floor(source * 24 + 1e-8)}']


@pytest.mark.parametrize('offset', [0, 0.25])
def test_acting_sample_holds_cropped_terminal_pose_and_contacts(offset):
    track = contact_track()
    track = replace(track, options=replace(track.options, duration=1, offset=offset))
    plan = compile_performance(gloss_actor('nadia'), ActingScore(5, overrides=Overrides(limbs=(track,))))
    terminal = plan.sample(1 + offset).limbs
    assert terminal[0].contacts == ('button',)
    assert plan.sample(3.75).limbs == terminal
    assert plan.window(3, 5).sample(0.75).limbs == terminal
    assert plan.sample(0).limbs[0].pose == track.motion.sample(0)


@pytest.mark.parametrize('view', ['front', None, Frame(origin=(0, 0, 0)), Frame(rotation=(1, 0, 0, 0))])
def test_camera_refuses_invalid_view_with_repair_fields(view):
    with pytest.raises(LimbError) as caught:
        Camera(view=view)
    error = caught.value.to_dict()
    assert error['code'] == 'projection'
    assert error['path'].startswith('camera.view')
    assert error['expected'] and error['remedy']


def test_camera_refuses_forged_nonunit_view_without_normalizing_it():
    rotation = Quaternion()
    object.__setattr__(rotation, 'w', 2)
    with pytest.raises(LimbError):
        Camera(view=Frame(rotation=rotation))
    assert rotation.w == 2


def test_acting_cropped_props_hold_the_same_frame_as_the_hand():
    track = contact_track()
    motion = track.motion
    motion = replace(motion, attachments=(Attachment('button-prop', 0.5, 3.5, motion.sample(0.5).hand.frame),))
    track = replace(track, motion=motion, options=replace(track.options, duration=1))
    performance = compile_performance(gloss_actor('nadia'), ActingScore(5, overrides=Overrides(limbs=(track,))))
    assert performance.sample(4).limbs[0].props == (('button-prop', motion.prop_frame('button-prop', 1)),)


def test_unsupported_body_clock_refuses_without_scene_mutation():
    cv = canvas()
    parent = cv.group(cv.comp, 'marked', startMarker='entry')
    before, serial = cv.scene.to_bytes(), cv._serial
    from srstudio.body import BodyError

    with pytest.raises(BodyError):
        plan().window(0, 2).place(cv, parent, camera=Camera())
    assert cv.scene.to_bytes() == before and cv._serial == serial
