"""A rejected camera reframe can be corrected and retried on the same canvas."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, camera
from srstudio.canvas import CanvasError


def canvas(*, local=False, held=False, existing=True):
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=3)
    cv = Canvas(scene, font_asset=None, local_time=local, held_frames=held)
    group = cv.group(cv.comp, 'camera')
    if existing:
        cv.keys(group, 'opacity', [(0, 1), (2, 0)])
    return cv, group


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('held', [False, True])
@pytest.mark.parametrize('column, prop', [(2, 'x'), (3, 'y')])
def test_failed_reframe_preserves_existing_animation_and_allows_clean_retry(local, held, column, prop):
    cv, group = canvas(local=local, held=held)
    before = cv.scene.to_bytes()
    held_before = list(cv._held)
    rate_before = cv._held_rate
    bad = [1, 2, 20, 30]
    bad[column] = float('nan')

    with pytest.raises(CanvasError) as caught:
        camera.reframe(cv, group, [(0, 1, 0, 0), tuple(bad)])

    assert caught.value.to_dict()['path'] == f'keys.{prop}[1][1]'
    assert cv.scene.to_bytes() == before
    assert cv._held == held_before
    assert cv._held_rate == rate_before

    moves = [(0, 1, 0, 0), (1, 2, 20, 30)]
    camera.reframe(cv, group, moves)
    fresh, fresh_group = canvas(local=local, held=held)
    camera.reframe(fresh, fresh_group, moves)
    cv.place_held()
    fresh.place_held()
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()
    animations = list(group.iter('animate'))
    assert [a.property for a in animations] == ['opacity', 'scaleX', 'scaleY', 'x', 'y']
    assert all(a.defaultInterpolation == 'hold' for a in animations)
    assert all((a.attributes().get('timeBase') == 'local') == local for a in animations)


def test_failed_first_reframe_restores_held_frame_bookkeeping():
    cv, group = canvas(held=True, existing=False)
    before = cv.scene.to_bytes()
    assert cv._held_rate is None
    with pytest.raises(CanvasError):
        camera.reframe(cv, group, [(0, 1, 0, 0), (1, 2, 20, float('nan'))])
    assert cv._held == []
    assert cv._held_rate is None
    assert cv.scene.to_bytes() == before


def test_incomplete_reframe_row_does_not_leave_earlier_columns_attached():
    cv, group = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(IndexError):
        camera.reframe(cv, group, [(0, 1, 0, 0), (1, 2, 20)])
    assert cv.scene.to_bytes() == before
