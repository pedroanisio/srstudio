"""An invalid nod plan leaves actors and scenes reusable by an authoring agent."""

import math
from contextlib import nullcontext

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, cast
from srstudio.rig import Performance


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    return Canvas(scene, font_asset=None)


@pytest.mark.parametrize('frozen', [False, True])
@pytest.mark.parametrize('bad', [((0, 0), (1, math.nan)), ((0, 0), (math.inf, 1))])
@pytest.mark.parametrize('built', [False, True])
def test_invalid_nods_preserve_scene_actor_and_retry_ids(frozen, bad, built):
    cv = canvas()
    actor = cast.Manager(cv)
    if built:
        actor.build(cv.comp, 0, 0)
    before = cv.scene.to_bytes()
    state = vars(actor).copy()
    with cv.frozen() if frozen else nullcontext():
        with pytest.raises(ValueError):
            actor.build(cv.comp, 0, 0, perf=Performance(nods=bad))
    assert cv.scene.to_bytes() == before
    assert vars(actor) == state

    # A retry must produce exactly the IDs and geometry of the same build with no failed attempt.
    fresh = canvas()
    other = cast.Manager(fresh)
    if built:
        other.build(fresh.comp, 0, 0)
    repaired = Performance(nods=((0, 0), (1, 3)))
    actor.build(cv.comp, 0, 0, perf=repaired)
    other.build(fresh.comp, 0, 0, perf=repaired)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


def test_frozen_nods_crossing_zero_fail_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with cv.frozen(), pytest.raises(ValueError, match='across 0 s'):
        cast.Manager(cv).build(cv.comp, 0, 0, perf=Performance(nods=((-1, 0), (1, 3))))
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('frozen', [False, True])
@pytest.mark.parametrize('local', [False, True])
def test_valid_nods_retain_canvas_interpolation_clock_and_freeze_policy(frozen, local):
    cv = canvas()
    cv.local_time = local
    keys = ((0, 2), (1, 3))
    with cv.frozen() if frozen else nullcontext():
        expected = cv.group(cv.comp, 'reference')
        reference = cv.keys(expected, 'rotation', keys, hold=False)
        actor = cast.Manager(cv)
        actor.build(cv.comp, 0, 0, perf=Performance(nods=keys))
    actual = next(a for a in actor.head.iter('animate') if a.property == 'rotation')
    assert actual.attributes() == reference.attributes()
    assert [k.attributes() for k in actual.iter('key')] == [k.attributes() for k in reference.iter('key')]
