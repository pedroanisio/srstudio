"""The Ink video doorbell: a talking doorbell whose ring pulses while it speaks and that can deny or allow, the
doorstep it hangs by, and its camera view, where the face box's tag changes over the take; plus the refusals and
the human's opt-in sunglasses."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink, ink_doorbell, registry, shared_counter
from srstudio.canvas import Signature
from srstudio.ink_doorbell import DoorbellError
from srstudio.timeline import Take


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def take(actor: str = "doorbell", duration: float = 2.0, shot: str = "doorbell") -> Take:
    return Take("01", actor, shot, "Face not recognized.", 0.0, duration)


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def animated(cv: Canvas, prop: str):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_parts_are_registered_in_the_ink_style():
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (
        ("character", "talking-doorbell"),
        ("location", "ink-doorstep"),
        ("graphic", "ink-doorbell-view"),
    ):
        assert entries[name].kind == kind and entries[name].style == "ink"


def test_the_doorbell_pulses_its_ring_and_shows_voice_marks_only_when_it_speaks():
    talking, silent = canvas(), canvas()
    ink_doorbell.doorbell(talking, talking.comp, take(), 300, 500)
    ink_doorbell.doorbell(silent, silent.comp, take("human"), 300, 500)
    assert animated(silent, "opacity") == []
    fades = animated(talking, "opacity")
    assert len(fades) == ink_doorbell.RING_LIGHTS + 1  # each light of the ring, and the voice marks
    assert all(k[0] == (0.0, 1.0) and k[-1][0] < 2.0 for k in fades[: ink_doorbell.RING_LIGHTS])


@pytest.mark.parametrize("mark", ["deny", "allow"])
def test_the_doorbell_shows_its_verdict_from_its_moment(mark):
    cv = canvas()
    ink_doorbell.doorbell(cv, cv.comp, take("human"), 300, 500, mark=(mark, 0.6))
    assert animated(cv, "opacity") == [[(0.0, 0.0), (0.6, 1.0)]]


def test_the_doorbell_refuses_an_unknown_verdict_or_one_outside_the_take():
    cv = canvas()
    with pytest.raises(DoorbellError, match="mark"):
        ink_doorbell.doorbell(cv, cv.comp, take(), 300, 500, mark=("maybe", 0.5))
    with pytest.raises(DoorbellError, match="within the take"):
        ink_doorbell.doorbell(cv, cv.comp, take(), 300, 500, mark=("allow", 2.5))


@pytest.mark.parametrize("close", [False, True])
def test_the_doorstep_hangs_the_doorbell_by_the_numbered_door_and_signs_it(close):
    cv = canvas()
    ink_doorbell.doorstep(cv, cv.comp, take(), close=close, number="14")
    assert "14" in texts(cv)
    assert any("sig-code" in (g.get("id") or "") for g in tree(cv).iter())  # the signature code on the doorbell
    assert len(animated(cv, "opacity")) == ink_doorbell.RING_LIGHTS + 1


def test_the_doorstep_refuses_a_house_number_it_cannot_letter():
    cv = canvas()
    with pytest.raises(DoorbellError, match="number"):
        ink_doorbell.doorstep(cv, cv.comp, take(), number="")
    with pytest.raises(DoorbellError, match="number"):
        ink_doorbell.doorstep(cv, cv.comp, take(), number="12345")


def test_the_camera_view_tags_the_face_in_turn_and_blinks_rec():
    cv = canvas()
    ink_doorbell.doorbell_view(
        cv, cv.comp, take("human", 2.0, "lens"), tags=((0.0, "UNKNOWN"), (0.4, "EMPLOYEE")), clock="2:14 PM"
    )
    shown = texts(cv)
    assert {"UNKNOWN", "EMPLOYEE", "REC"} <= set(shown)
    assert any("2:14 PM" in (t or "") for t in shown)
    fades = animated(cv, "opacity")
    assert [(0.0, 1.0), (0.4, 0.0)] in fades and [(0.0, 0.0), (0.4, 1.0)] in fades  # one tag gives way to the next
    assert any(len(k) > 3 for k in fades)  # the REC dot blinks through the take


def test_a_single_tag_holds_for_the_whole_take():
    cv = canvas()
    ink_doorbell.doorbell_view(cv, cv.comp, take("doorbell", 2.0, "lens"), tags=((0.0, "UNKNOWN"),))
    assert "UNKNOWN" in texts(cv)
    assert [(0.0, 1.0), (0.4, 0.0)] not in animated(cv, "opacity")


@pytest.mark.parametrize(
    ("tags", "match"),
    [
        ((), "at least one tag"),
        (((0.0, ""),), "tag"),
        (((0.0, "A" * (ink_doorbell.TAG_MAX + 1)),), "tag"),
        (((0.5, "UNKNOWN"),), "first tag"),
        (((0.0, "UNKNOWN"), (0.0, "EMPLOYEE")), "rising"),
        (((0.0, "UNKNOWN"), (3.0, "EMPLOYEE")), "within the take"),
    ],
)
def test_the_camera_view_refuses_tags_it_cannot_show(tags, match):
    cv = canvas()
    with pytest.raises(DoorbellError, match=match):
        ink_doorbell.doorbell_view(cv, cv.comp, take("human", 2.0, "lens"), tags=tags)


def test_the_camera_view_refuses_a_clock_too_long_for_its_strip():
    cv = canvas()
    with pytest.raises(DoorbellError, match="clock"):
        ink_doorbell.doorbell_view(cv, cv.comp, take("human"), tags=((0.0, "UNKNOWN"),), clock="X" * 20)


def test_the_human_wears_sunglasses_only_when_asked():
    plain, shades = canvas(), canvas()
    ink.human(plain, plain.comp, take("human"), 100, 100)
    ink.human(shades, shades.comp, take("human"), 100, 100, shades=True)
    extra = len(list(tree(shades).iter("shape"))) - len(list(tree(plain).iter("shape")))
    assert extra == 3  # two lenses and the bridge, on the forehead


def test_the_default_human_is_unchanged_by_the_sunglasses_option():
    a, b = canvas(), canvas()
    ink.human(a, a.comp, take("human"), 100, 100)
    ink.human(b, b.comp, take("human"), 100, 100, shades=False)
    assert a.scene.to_bytes(layout="pretty") == b.scene.to_bytes(layout="pretty")
