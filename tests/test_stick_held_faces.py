"""``stick.rig(held_faces=True)``: a body keyed every picture keeps one face per run of equal faces, and
blinks inside it; without it the rig draws exactly what it always drew."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick

GRIN = stick.Face("happy", "raised", "smile", (0, 0))
COOL = stick.Face("half", "flat", "smirk", (0.4, 0))


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="25", duration=2.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def per_picture(faces: list[stick.Face], step: float = 0.04) -> list[stick.RigKey]:
    names = list(stick.SEATED)
    return [stick.RigKey(round(i * step, 6), names[i % len(names)], face) for i, face in enumerate(faces)]


def face_groups(cv: Canvas, rig) -> list[ET.Element]:
    """The groups that hold a face's features: each carries the brows, drawn as stroked paths, and the eyes' group."""
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(f".//*[@id='{rig.id}']")
    assert root is not None
    head = next(g for g in root.findall("group") if g.find("shape[@shape='ellipse']") is not None)
    return [g for g in head.findall("group") if g.find("group") is not None and g.find("shape") is not None]


def blinks(cv: Canvas, rig) -> list[list[tuple[float, float]]]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(f".//*[@id='{rig.id}']")
    assert root is not None
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.findall("key")]
        for a in root.iter("animate")
        if a.get("property") == "scaleY"
    ]


def test_a_run_of_equal_faces_is_drawn_once_and_each_switch_draws_the_next():
    keys = per_picture([GRIN] * 20 + [COOL] * 20)
    cv = canvas()
    rig = stick.rig(cv, cv.comp, keys, 1.6, held_faces=True)
    faces = face_groups(cv, rig)
    assert len(faces) == 2
    gates = [[(float(k.get("time")), k.get("value")) for k in g.find("animate").findall("key")] for g in faces]
    assert gates == [[(0.0, "1"), (0.8, "0")], [(0.0, "0"), (0.8, "1"), (1.6, "0")]]


def test_without_held_faces_every_key_draws_its_own_face():
    keys = per_picture([GRIN] * 6)
    cv = canvas()
    rig = stick.rig(cv, cv.comp, keys, 0.24)
    assert len(face_groups(cv, rig)) == 6


def test_a_blink_plays_inside_a_held_face_though_every_body_lasts_one_picture():
    keys = per_picture([GRIN] * 25 + [stick.Face("open", "flat", "flat", (0, 0))] * 25)
    held = canvas()
    figure = stick.rig(held, held.comp, keys, 2.0, blinks=(1.3,), held_faces=True)
    assert blinks(held, figure) == [[(0.0, 1.0), (1.3, 1.0), (1.35, 0.1), (1.42, 1.0)]]
    keyed = canvas()
    figure = stick.rig(keyed, keyed.comp, keys, 2.0, blinks=(1.3,))
    assert blinks(keyed, figure) == []  # a span of one picture is too short to blink in


def test_held_faces_change_nothing_when_no_two_neighbouring_keys_share_a_face():
    keys = per_picture([GRIN, COOL, GRIN, COOL])
    plain, held = canvas(), canvas()
    stick.rig(plain, plain.comp, keys, 0.2, blinks=(0.0,))
    stick.rig(held, held.comp, keys, 0.2, blinks=(0.0,), held_faces=True)
    assert plain.scene.to_bytes() == held.scene.to_bytes()


def test_the_mouth_follows_the_held_faces():
    keys = per_picture([GRIN] * 5 + [COOL] * 5)
    cv = canvas()
    rig = stick.rig(cv, cv.comp, keys, 0.4, held_faces=True)
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(f".//*[@id='{rig.id}']")
    lips_x = [
        [float(k.get("value")) for k in a.findall("key")]
        for a in root.iter("animate")
        if a.get("property") == "x" and len(a.findall("key")) == 2
    ]
    assert [0.0, 0.4 * 14] in lips_x  # one key per held face, not one per picture


@pytest.mark.parametrize("value", [1, "yes", None])
def test_held_faces_is_a_boolean(value):
    with pytest.raises(stick.StickDataError, match="held_faces"):
        cv = canvas()
        stick.rig(cv, cv.comp, per_picture([GRIN]), 0.1, held_faces=value)


def test_the_contract_describes_held_faces():
    from srstudio import registry

    described = registry.describe("character", "stick-rig")["contract"]["arguments"]["properties"]["held_faces"]
    assert described["type"] == "boolean" and described["default"] is False
