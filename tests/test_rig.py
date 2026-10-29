import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Actor, Canvas, cast


def fresh():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3)
    return Canvas(scene, OFFICE)


def test_actor_without_drawing_hooks_fails_at_construction():
    class Faceless(Actor):
        def draw_body(self, g, perf):
            pass

    with pytest.raises(TypeError, match="draw_blink|draw_eyes|draw_head"):
        Faceless(fresh())
    with pytest.raises(TypeError):
        Actor(fresh())


def test_partial_bases_stay_abstract_and_every_cast_rig_is_concrete():
    with pytest.raises(TypeError, match="draw_eyes"):
        cast.OfficeActor(fresh())
    with pytest.raises(TypeError, match="draw_body"):
        cast.CafeActor(fresh())
    for rig in (cast.Manager, cast.Candidate, cast.Barista, cast.Customer):
        actor = rig(fresh())
        actor.build(actor.cv.comp, 0, 0)
        assert actor.mouths.keys() == {"rest", "round", "open", "small", "smile"}


def test_the_barista_tag_letters_her_name_unless_it_is_none():
    from srstudio.rig import Performance

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3)
    lettered = cast.Barista(Canvas(scene, OFFICE, font_asset="font"))
    lettered.build(lettered.cv.comp, 0, 0)
    blank_scene = Scene(version="auto")
    blank_scene.add_project(width=1080, height=1920, fps="30", duration=3)
    blank = cast.Barista(Canvas(blank_scene, OFFICE, font_asset="font"))
    blank.build(blank.cv.comp, 0, 0, 1, Performance(extras={"name": None}))
    assert b"<text" not in blank_scene.to_bytes() and b'text="AVA"' in scene.to_bytes()
