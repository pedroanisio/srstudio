"""A second character in a Toon shot: placed, posed from its own timeline, refused when it cannot be drawn."""

import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon_extras
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def shot(cv: Canvas, mouths=None) -> SimpleNamespace:
    app = sketch.Appearance("goat", 1.0, 5.0, [])
    return SimpleNamespace(cv=cv, app=app, versions={}, mouths=mouths or {})


def test_a_figure_enters_with_the_shot_and_draws_its_own_part():
    cv = canvas()
    g = toon_extras.figure(shot(cv), cv.comp, "raccoon", (400, 800), 0.8, ((0.0, "half", "flat", "desk"),))
    assert g is not None
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    assert len(list(root.iter())) > 20


def test_poses_count_from_the_entrance_and_keep_the_pose_it_enters_in():
    poses = ((0.0, "half", "flat", "desk"), (1.5, "wide", "flat", "desk"), (3.0, "side", "grin", "desk"))
    drawn = toon_extras.poses_of(poses, 2.0)
    assert [(p.start, p.eyes) for p in drawn] == [(0.0, "wide"), (1.0, "side")]


def test_a_figure_refuses_what_it_cannot_draw():
    cv = canvas()
    with pytest.raises(ToonDataError, match="lead"):
        toon_extras.figure(shot(cv), cv.comp, "goat", (400, 800))
    with pytest.raises(ToonDataError, match="positive"):
        toon_extras.figure(shot(cv), cv.comp, "raccoon", (400, 800), 0.0)
    with pytest.raises(ToonDataError, match="leave"):
        toon_extras.figure(shot(cv), cv.comp, "raccoon", (400, 800), start=4.0, end=3.0)
    with pytest.raises(ToonDataError, match="rise"):
        toon_extras.poses_of(((2.0, "half", "flat", "desk"), (1.0, "wide", "flat", "desk")), 0.0)
    with pytest.raises(ToonDataError, match="at least one"):
        toon_extras.poses_of((), 0.0)


def test_a_traced_character_takes_no_voice_track():
    cv = canvas()
    with pytest.raises(sketch.SketchError, match="traced"):
        toon_extras.figure(shot(cv, {"cat": [(0.0, "open")]}), cv.comp, "cat", (400, 800))


def test_a_lip_synced_figure_takes_its_track():
    cv = canvas()
    track = [(1.2, "open"), (1.6, "closed")]
    toon_extras.figure(shot(cv, {"raccoon": track}), cv.comp, "raccoon", (400, 800), mirror=True)
    assert cv.scene.to_bytes(layout="pretty")
