"""What a character's digest holds: the drawing, not the document around it (ADR 0047, after ADR 0037)."""

import re
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import characters, registry, specimens, toon, toon_cast
from srstudio.canvas import Canvas, flat_counter
from srstudio.specimens import DrawingChangedError, SpecimenError

specimens.load_parts()
APPROVED = [(name, v.number) for name, c in characters.load().items() for v in c.versions if v.status == "approved"]


def drawn() -> bytes:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2.0, background="#ffffff")
    cv = Canvas(scene, font_asset=None, namer=flat_counter("n"))
    toon_cast.fox(cv, cv.comp, [toon.Pose(0, "wide", "flat", "desk"), toon.Pose(1, "roll", "grin", "type")], 2.0)
    return scene.to_bytes(layout="pretty")


BASE = specimens.fingerprint(drawn())


def edited(pattern: str, replacement: str, *, count: int = 0) -> str:
    text, n = re.subn(pattern, replacement, drawn().decode(), count=count)
    assert n, pattern
    return specimens.fingerprint(text.encode())


def test_the_same_document_digests_the_same():
    assert re.fullmatch(r"[0-9a-f]{64}", BASE) and specimens.fingerprint(drawn()) == BASE


@pytest.mark.parametrize(
    ("pattern", "replacement"),
    [
        (r'<scene version="[^"]*"', '<scene version="9.9"'),  # the engine's format version
        (r'<project [^>]*/>', '<project width="1920" height="1080" fps="30" duration="9" background="#000000"/>'),
        (r' id="n(\d+)"', r' id="other-\1"'),  # the ids a namer hands out
        (r'( width="1080")( height="1920")( path=)', r"\2\1\3"),  # attribute order
        (r'start="0"', 'start="0.0"'),  # how a number is written
        (r'end="1"', 'end="1.000"'),
        (r'(path="M )(\d+)\.(\d+)', r"\g<1>\2.\g<3>0"),  # a trailing zero in a path
        (r'<composition>', '<metadata title="x"/><composition>'),
    ],
)
def test_a_change_unrelated_to_the_drawing_does_not_move_the_digest(pattern, replacement):
    assert edited(pattern, replacement, count=1 if "composition" in pattern or "path" in pattern else 0) == BASE


def test_a_group_that_draws_nothing_does_not_move_the_digest():
    root = ET.fromstring(drawn())
    comp = root.find("composition")
    assert comp is not None
    wrapper = ET.Element("group", {"id": "added"})
    wrapper.extend(list(comp))
    for child in list(comp):
        comp.remove(child)
    comp.append(wrapper)
    assert specimens.fingerprint(ET.tostring(root)) == BASE


@pytest.mark.parametrize(
    ("pattern", "replacement"),
    [
        (r'(path="M )(\d+)\.(\d+)', r"\g<1>\g<2>7.\3"),  # one drawn point moved
        (r'fill="#[0-9A-Fa-f]{6}"', 'fill="#123456"'),  # one colour
        (r'strokeWidth="[^"]*"', 'strokeWidth="9"'),  # one line weight
    ],
)
def test_a_change_to_the_drawing_moves_the_digest(pattern, replacement):
    assert edited(pattern, replacement, count=1) != BASE


def test_a_group_moved_or_a_key_changed_moves_the_digest():
    assert edited(r'start="0" end="1"', 'start="0" end="1.5"', count=1) != BASE
    root = ET.fromstring(drawn())
    shapes = list(root.iter("shape"))
    first, second = shapes[0], shapes[1]
    parent = next(p for p in root.iter() if first in list(p))
    parent.remove(first)
    parent.insert(list(parent).index(second) + 1, first)  # one drawn over the other
    assert specimens.fingerprint(ET.tostring(root)) != BASE


def test_an_attribute_nobody_classified_stops_the_digest_rather_than_passing_it_by():
    text = drawn().decode().replace("<shape ", '<shape glow="1" ', 1)
    with pytest.raises(SpecimenError, match=r"shape@glow.*specimens\.DRAWN"):
        specimens.fingerprint(text.encode())


def test_an_element_nobody_classified_stops_the_digest():
    text = drawn().decode().replace("<shape ", "<sparkle/><shape ", 1)
    with pytest.raises(SpecimenError, match="sparkle"):
        specimens.fingerprint(text.encode())


def test_a_definition_is_digested_where_it_is_used():
    def with_effect(radius: str) -> str:
        doc = (
            drawn()
            .decode()
            .replace("<composition>", f'<effects><effect id="e" type="blur" radius="{radius}"/></effects><composition>')
        )
        return specimens.fingerprint(doc.replace("<group ", '<group effects="e" ', 1).encode())

    assert with_effect("4") != with_effect("5")
    renamed = (
        drawn()
        .decode()
        .replace("<composition>", '<effects><effect id="z" type="blur" radius="4"/></effects><composition>')
        .replace("<group ", '<group effects="z" ', 1)
    )
    assert specimens.fingerprint(renamed.encode()) == with_effect("4")


def test_a_gradient_is_digested_where_a_fill_uses_it():
    def painted(stop: str, name: str = "g") -> str:
        paints = f'<paints><linearGradient id="{name}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" color="{stop}"/>'
        doc = drawn().decode().replace("<composition>", f"{paints}</linearGradient></paints><composition>")
        return specimens.fingerprint(re.sub(r'fill="#\w+"', f'fill="url(#{name})"', doc, count=1).encode())

    assert painted("#111111") != painted("#222222") and painted("#111111") == painted("#111111", "renamed")


@pytest.mark.parametrize(("name", "number"), APPROVED, ids=[f"{n}@{v}" for n, v in APPROVED])
def test_an_approved_drawing_never_changes(name, number):
    specimens.check(name, number)


def test_a_changed_approved_drawing_fails_and_says_to_add_a_version(monkeypatch):
    real = specimens.digest
    monkeypatch.setattr(specimens, "digest", lambda name, number=1: "b" * 64)
    with pytest.raises(DrawingChangedError, match=r"toon-bear version 1 .*add a version"):
        specimens.check("toon-bear", 1)
    monkeypatch.setattr(specimens, "digest", real)


def test_moving_a_point_of_a_look_moves_its_digest(monkeypatch):
    before = specimens.digest("toon-bear")
    bear = toon_cast.LOOKS["bear"]
    moved = bear.silhouette[:1] + ((bear.silhouette[1][0] + 3.0, bear.silhouette[1][1]),) + bear.silhouette[2:]
    from dataclasses import replace

    monkeypatch.setattr(toon_cast, "BEAR", replace(bear, silhouette=moved))
    assert specimens.digest("toon-bear") != before


def test_the_specimens_read_a_fixed_vocabulary_so_a_new_kind_moves_no_digest(monkeypatch):
    before = specimens.digest("toon-bear")
    monkeypatch.setattr(toon, "EYES", (*toon.EYES, "sleepy"))
    monkeypatch.setattr(toon, "MOUTHS", (*toon.MOUTHS, "yawn"))
    assert specimens.digest("toon-bear") == before


def test_the_fixed_vocabulary_is_still_the_vocabulary():
    assert set(specimens.EYES) <= set(toon.EYES) and set(specimens.MOUTHS) <= set(toon.MOUTHS)
    assert set(specimens.ARMS) == set(toon.ARMS) and set(specimens.WEAR) == set(toon.WEAR)


def test_every_character_has_a_specimen_and_one_family_each():
    names = {e.name for e in registry.entries("character")}
    assert names == set(specimens.SPECIMENS)
    assert len(set(specimens.SPECIMENS.values())) <= 12
