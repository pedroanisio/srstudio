"""Body compilation validates all source geometry before any scene mutation."""

from dataclasses import replace

import pytest

from srstudio import body
from srstudio.limbs import Camera, Frame, Vec3
from support.body import canvas, plan


@pytest.mark.parametrize('style', ['solid', 'wire'])
def test_body_window_keeps_source_clock_and_draws_valid_geometry(style):
    cv = canvas()
    group = (
        plan()
        .window(0.75, 1.75)
        .place(cv, cv.comp, at=4, camera=Camera(origin=(540, 1600), scale=700), fps=12, style=style)
    )
    assert float(group.timeOffset) == 3.25
    assert float(group.start) == 4
    assert float(group.end) == 5
    frames = [g for g in group.iter('group') if g.id.startswith('body-frame')]
    assert len(frames) == 24
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize(
    'options',
    [
        {'style': 'unknown'},
        {'fps': True},
        {'fps': 0},
        {'fps': 121},
        {'camera': 'camera'},
        {'at': -1},
        {'id': 'bad id'},
        {'camera': Camera(projection='perspective', distance=0.01)},
    ],
)
def test_rejected_drawing_leaves_scene_and_allocator_untouched(options):
    cv = canvas()
    before = cv.scene.to_bytes()
    calls = []
    uid = cv.uid

    def count(prefix):
        calls.append(prefix)
        return uid(prefix)

    cv.uid = count
    kwargs = {'camera': Camera(), **options}
    with pytest.raises(body.BodyError):
        plan().window(0, 2).place(cv, cv.comp, **kwargs)
    assert before == cv.scene.to_bytes()
    assert calls == []


def test_forged_plan_does_not_bypass_support_preflight():
    original = plan()
    invalid = replace(original, score=replace(original.score, roots=(body.BodyKey(0, Frame(Vec3(2, -0.88, 0))),)))
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(body.BodyError):
        invalid.window(0, 2).place(cv, cv.comp, camera=Camera())
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('budget', ['frames', 'nodes'])
def test_emission_budgets_fail_before_scene_mutation(budget, monkeypatch):
    import srstudio._body_draw as drawing

    authored = plan()
    if budget == 'frames':
        authored = body.compile_body(replace(authored.score, duration=50, validation_hz=1))
    else:
        monkeypatch.setattr(drawing, 'MAX_NODES', 1)
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(body.BodyError) as caught:
        authored.window(0, 2).place(cv, cv.comp, camera=Camera())
    assert caught.value.to_dict()['code'] == 'body.budget'
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('budget', ['frames', 'nodes'])
@pytest.mark.parametrize('at,scale', [(0, 1), (1, 2)])
def test_late_windows_count_the_entire_source_budget(budget, at, scale, monkeypatch):
    import srstudio._body_draw as drawing

    authored = plan()
    if budget == 'frames':
        authored = body.compile_body(replace(authored.score, duration=50, validation_hz=1))
    else:
        # One second fits; the entire two-second source does not.
        monkeypatch.setattr(drawing, 'MAX_NODES', 1500)
    cv = canvas()
    parent = cv.group(cv.comp, 'parent', timeScale=scale)
    before, serial = cv.scene.to_bytes(), cv._serial
    with pytest.raises(body.BodyError) as caught:
        authored.window(authored.duration - 1, authored.duration).place(cv, parent, at=at, camera=Camera())
    assert caught.value.to_dict()['code'] == 'body.budget'
    assert caught.value.to_dict()['path'] == budget
    assert cv.scene.to_bytes() == before and cv._serial == serial


def test_late_window_projects_hidden_source_before_scene_mutation(monkeypatch):
    import srstudio._body_draw as drawing
    from srstudio.limbs.errors import LimbError

    project = drawing.geometry

    def behind_camera(pose, *args):
        if 0.1 < pose.time < 0.5:
            raise LimbError('source starts behind the near plane')
        return project(pose, *args)

    monkeypatch.setattr(drawing, 'geometry', behind_camera)
    cv = canvas()
    before, serial = cv.scene.to_bytes(), cv._serial
    with pytest.raises(body.BodyError) as caught:
        plan().window(1, 2).place(cv, cv.comp, camera=Camera())
    assert caught.value.to_dict()['code'] == 'body.projection'
    assert cv.scene.to_bytes() == before and cv._serial == serial


def test_foreign_parent_and_duplicate_id_are_refused():
    cv, other = canvas(), canvas()
    existing = cv.group(cv.comp, 'occupied')
    before = cv.scene.to_bytes()
    for parent, kwargs in ((other.comp, {}), (cv.comp, {'id': existing.id})):
        with pytest.raises(body.BodyError):
            plan().window(0, 2).place(cv, parent, camera=Camera(), **kwargs)
    assert cv.scene.to_bytes() == before


def test_unexpected_emission_failure_rolls_back_scene_and_builtin_ids(monkeypatch):
    cv = canvas()
    before = cv.scene.to_bytes()
    count = cv._serial

    def broken(*args, **kwargs):
        raise RuntimeError('injected emission failure')

    monkeypatch.setattr(cv, 'path', broken)
    with pytest.raises(RuntimeError, match='injected'):
        plan().window(0, 2).place(cv, cv.comp, camera=Camera())
    assert cv.scene.to_bytes() == before
    assert cv._serial == count
