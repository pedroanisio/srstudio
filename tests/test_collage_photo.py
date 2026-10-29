"""The Collage family photo's props: the phone propped on books counting its self-timer down, the same countdown
in the phone's viewfinder over the group shot, the sofa's front that the seated busts sink into, the camera's
flash, and the printed photo: a still of the lineup in its room, a blurred subject among sharp ones; plus the
refusals."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import COLLAGE, Canvas, collage, collage_photo, collage_sets, registry
from srstudio.canvas import Signature
from srstudio.collage_group import Place
from srstudio.collage_photo import PhotoError

PLACES = {"gary": Place(230, 1800, 0.55), "kai": Place(850, 1800, 0.5), "rosa": Place(540, 1800, 0.58)}
LAUGH = {"gary": ("wide", "o", "shrug"), "kai": ("closed", "grin", "face"), "rosa": ("closed", "grin", "hold")}


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=20.0, background="#ffe5d9")
    return Canvas(scene, COLLAGE.palettes[0], font_asset="caption", signature=Signature())


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [t.get("text") for t in tree(cv).iter("text")]


def animated(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_props_are_registered_in_the_collage_style():
    entries = {e.name: e for e in registry.entries()}
    for name in ("collage-phone-timer", "collage-viewfinder", "collage-sofa", "collage-flash", "collage-photo-print"):
        assert entries[name].kind == "prop" and entries[name].style == "collage", name


@pytest.mark.parametrize("draw", [collage_photo.timer, collage_photo.viewfinder])
def test_the_phone_and_its_viewfinder_count_down_one_second_a_digit(draw):
    cv = canvas()
    if draw is collage_photo.timer:
        draw(cv, cv.comp, 800, 1500, start=2.0, seconds=5)
    else:
        draw(cv, cv.comp, start=2.0, seconds=5)
    assert [t for t in texts(cv) if t.isdigit()] == ["5", "4", "3", "2", "1"]
    fades = animated(cv, "opacity")
    assert [(0.0, 1.0), (3.0, 0.0)] in fades  # the full count waits on the screen until its first second is up
    for i in range(1, 5):
        assert [(0.0, 0.0), (2.0 + i, 1.0), (3.0 + i, 0.0)] in fades  # then each digit for its second, in turn


def test_the_viewfinder_frames_what_the_print_shows_clear_of_the_living_room_signature():
    x0, y0, x1, y1 = collage_photo.CORNERS
    assert collage_photo.PHOTO_CROP == (x0, y0, x1 - x0, y1 - y0)  # the print is the frame the viewfinder showed
    sx0, sy0, sx1, sy1 = collage_sets.signature_box("living-room")
    m = collage_photo.BRACKET / 4
    assert y0 >= sy1 + m or x0 + collage_photo.BRACKET <= sx0 - m  # the top-left bracket clears the cactus shelf
    assert y0 > collage.CAPTION_TOP and collage_photo.COUNT_AT[1] + collage_photo.COUNT_R <= y0  # pill, disc, frame


def test_the_flash_whites_out_holds_and_fades():
    cv = canvas()
    collage_photo.flash(cv, cv.comp, 6.0, hold=1.2, fade=0.4)
    gate, white = animated(cv, "opacity")
    assert gate == [(0.0, 0.0), (6.0, 1.0), (7.6, 0.0)]  # on from the shutter until it has faded
    assert white == [(6.0, 1.0), (7.2, 1.0), (7.6, 0.0)]  # full white, held, then fading


def test_the_print_is_a_still_of_the_lineup_with_its_blurred_subjects_and_nothing_moving():
    cv = canvas()
    collage_photo.print_photo(cv, cv.comp, PLACES, LAUGH, x=90, y=600, width=900, tilt=-3, blur=("gary",))
    root = tree(cv)
    ids = [g.get("id") or "" for g in root.iter("group")]
    for name in PLACES:
        assert sum(i.startswith(f"photo-{name}") for i in ids) == 1, name  # each one drawn once, in one pose
    blurred = [g.get("id") for g in root.iter("group") if (g.get("effects") or "").startswith("collage-photo-blur")]
    assert len(blurred) == 1 and blurred[0].startswith("photo-gary")
    assert any(m.get("type") == "rect" for m in root.iter("mask"))  # the print crops the room to the photo
    assert animated(cv, "y") == [] and animated(cv, "opacity") == []  # a photo does not breathe or blink
    assert sum(i.startswith("sig-cactus") for i in ids) == 1  # the room in the photo keeps its signature


def test_the_sofa_front_covers_the_busts_cut_off_bottoms():
    cv = canvas()
    collage_photo.sofa(cv, cv.comp)
    paths = [p for p in tree(cv).iter("shape") if p.get("shape") == "path"]
    assert paths and animated(cv, "y") == []
    assert collage_photo.SOFA_TOP < min(p.base for p in PLACES.values())


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda cv: collage_photo.timer(cv, cv.comp, 0, 0, start=-1.0), "start"),
        (lambda cv: collage_photo.timer(cv, cv.comp, 0, 0, start=0.0, seconds=0), "seconds"),
        (lambda cv: collage_photo.timer(cv, cv.comp, 0, 0, start=0.0, seconds=11), "seconds"),
        (lambda cv: collage_photo.viewfinder(cv, cv.comp, start=0.0, seconds=2.5), "seconds"),
        (lambda cv: collage_photo.flash(cv, cv.comp, -0.5), "flash"),
        (lambda cv: collage_photo.flash(cv, cv.comp, 1.0, fade=0.0), "flash"),
        (lambda cv: collage_photo.flash(cv, cv.comp, 1.0, hold=-1.0), "flash"),
        (
            lambda cv: collage_photo.print_photo(
                cv, cv.comp, PLACES, {**LAUGH, "brent": LAUGH["kai"]}, x=0, y=0, width=900
            ),
            "pose",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(cv, cv.comp, PLACES, {"rosa": LAUGH["rosa"]}, x=0, y=0, width=900),
            "pose",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(
                cv, cv.comp, PLACES, {**LAUGH, "kai": ("closed", "yell", "face")}, x=0, y=0, width=900
            ),
            "mouth",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(
                cv, cv.comp, PLACES, {**LAUGH, "kai": ("asleep", "grin", "face")}, x=0, y=0, width=900
            ),
            "eyes",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(cv, cv.comp, PLACES, LAUGH, x=0, y=0, width=900, blur=("omar",)),
            "blur",
        ),  # fmt: skip
        (lambda cv: collage_photo.print_photo(cv, cv.comp, PLACES, LAUGH, x=0, y=0, width=0), "width"),
        (
            lambda cv: collage_photo.print_photo(
                cv, cv.comp, {**PLACES, "zed": Place(0, 1800, 0.5)}, {**LAUGH, "zed": LAUGH["kai"]}, x=0, y=0, width=900
            ),
            "cast",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(cv, cv.comp, PLACES, LAUGH, x=0, y=0, width=900, room="attic"),
            "room",
        ),  # fmt: skip
        (
            lambda cv: collage_photo.print_photo(
                cv, cv.comp, PLACES, LAUGH, x=0, y=0, width=900, crop=(0, 1000, 1080, 1200)
            ),
            "crop",
        ),  # fmt: skip
    ],
)
def test_the_props_refuse_what_they_cannot_show(call, match):
    with pytest.raises(PhotoError, match=match):
        call(canvas())


def test_the_print_s_poses_use_the_collage_vocabulary():
    for eyes, mouth, arms in LAUGH.values():
        assert eyes in collage.EYES and mouth in collage.MOUTHS and arms in collage.ARMS
