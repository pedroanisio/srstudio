import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Actor, Canvas, cast
from srstudio.rig import blinks, check_place


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


class StyleError(ValueError):
    pass


def blink_keys(cv: Canvas) -> list[tuple[str, str]]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [(k.get("time"), k.get("value")) for a in root.iter("animate") for k in a.iter("key")]


def eyes(cv: Canvas):
    return cv.group(cv.comp, "eyes")


def test_blinks_close_the_eyes_every_period_from_the_phase():
    cv = fresh()
    blinks(cv, eyes(cv), 4.0, period=3.1, phase=0.7, skip_empty=True)
    assert blink_keys(cv) == [("0", "1"), ("0.7", "1"), ("0.75", "0.1"), ("0.84", "1"), ("3.8", "1"),
                              ("3.85", "0.1"), ("3.94", "1")]  # fmt: skip


def test_a_shot_too_short_to_blink_keys_nothing_or_holds_the_eyes_open():
    skipped, held = fresh(), fresh()
    blinks(skipped, eyes(skipped), 0.8, period=3.1, phase=0.7, skip_empty=True)
    blinks(held, eyes(held), 0.7, period=2.9, phase=0.6, skip_empty=False)
    assert blink_keys(skipped) == [] and blink_keys(held) == [("0", "1")]


def test_a_place_is_a_scale_above_zero_for_a_shot_above_zero():
    check_place(1.0, 2.0, StyleError)


@pytest.mark.parametrize(
    ("scale", "end", "message"),
    [
        (0, 2.0, "a character's scale must be > 0, got 0"),
        (True, 2.0, "a character's scale must be > 0, got True"),
        (float("nan"), 2.0, "a character's scale must be > 0, got nan"),
        (1.0, 0, "a character is drawn for more than 0 s, got 0"),
        (1.0, float("inf"), "a character is drawn for more than 0 s, got inf"),
    ],
)
def test_a_place_refuses_a_bad_scale_or_end_with_the_callers_error(scale, end, message):
    with pytest.raises(StyleError, match=f"^{message}$"):
        check_place(scale, end, StyleError)
