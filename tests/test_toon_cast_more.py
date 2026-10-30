"""The fox, the raccoon and the hedgehog: three more brush-drawn Toon characters, each with a silhouette and a coat of
its own, taking the whole Toon vocabulary, the visemes and blinks, and playing in a sketch by name."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, sketch, toon, toon_cast
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings
from support.toon_thumbnail import apart, lab, silhouette_rest

NEW = {"fox": "FOX", "raccoon": "RACCOON", "hedgehog": "HEDGEHOG"}


def canvas(duration: float = 3.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in root.find("composition").iter("group") if g.get("start") is not None]


def test_the_three_join_the_cast_by_name():
    for name, const in NEW.items():
        look = getattr(toon_cast, const)
        assert toon_cast.LOOKS[name] is look and look.name == name
        assert sketch.drawer(name, {sketch.part_of(name): 1}) is getattr(toon_cast, name)
        assert name in sketch.CHARACTERS and name in sketch.LIP_SYNCED and name in sketch.TOON_CAST.characters
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    for name in NEW:
        assert names[f"toon-{name}"]["kind"] == "character"


@pytest.mark.parametrize("name", list(NEW))
def test_each_new_head_reads_apart_from_every_other_character_at_thumbnail_size(name):
    """Every new head and its ears differ from each other character's at least as much as the two closest of the
    cast before them (the cat and the frog) differ from each other."""
    older = ("cat", "dog", "frog", "bear", "rabbit")
    heads = {n: silhouette_rest(n) for n in (*older, *NEW)}
    floor = min(apart(heads[a], heads[b]) for i, a in enumerate(older) for b in older[i + 1 :])
    assert floor > 0.2
    for other, theirs in heads.items():
        if other != name:
            assert apart(heads[name], theirs) >= floor, f"{name} reads too close to {other}"


def test_the_new_coats_tell_the_three_apart_and_from_the_older_cast():
    coats = {name: look.coat for name, look in toon_cast.LOOKS.items()}
    coats["cat"] = PEACH.shade
    for name in NEW:
        for other, colour in coats.items():
            if other != name:
                assert math.dist(lab(coats[name]), lab(colour)) > 20, f"{name}'s coat is too near {other}'s"


def test_the_builds_differ_small_slender_and_stout():
    def width(look, top, bottom):
        xs = [x for x, y in look.silhouette if top <= y <= bottom]
        return max(xs) - min(xs)

    def torso(look):  # the shoulders down to the desk
        return width(look, 700.0, 800.0)

    fox, raccoon, hedgehog = toon_cast.FOX, toon_cast.RACCOON, toon_cast.HEDGEHOG
    assert torso(raccoon) > max(torso(fox), torso(hedgehog)) + 30  # stout
    assert width(hedgehog, 0.0, hedgehog.mouth[1]) < min(width(n, 0.0, n.mouth[1]) for n in (fox, raccoon)) - 50

    def head(look):
        return min(y for _, y in look.silhouette)

    def ears(look):  # how far the ears rise over the head
        return head(look) - min(y for ear in look.ears for _, y in ear)

    assert ears(fox) > ears(raccoon) + 20  # the fox's ears stand tall
    assert head(hedgehog) > max(head(fox), head(raccoon)) + 25  # a small head, low on its shoulders
    assert hedgehog.limb < fox.limb < raccoon.limb


def test_a_mantle_is_drawn_behind_the_ears_and_the_body_and_paws_take_their_own_colour():
    layers = toon_cast.figure_shapes(toon_cast.HEDGEHOG, "wide", "flat", "desk")
    assert [c for _, c in layers[:2]] == ["ink", toon_cast.HEDGEHOG.dark]  # the spines first, under everything
    tips = toon_cast.HEDGEHOG.mantle
    assert min(y for _, y in tips) < min(y for _, y in toon_cast.HEDGEHOG.silhouette) - 25  # spines over the crown
    plain = toon_cast.figure_shapes(toon_cast.DOG, "wide", "flat", "desk")
    assert toon_cast.DOG.mantle == () and plain[0][1] == "ink"
    gloved = [c for _, c in toon_cast.figure_shapes(toon_cast.RACCOON, "wide", "flat", "desk")]
    assert gloved.count(toon_cast.RACCOON.paw) == 2 and toon_cast.RACCOON.paw != toon_cast.RACCOON.coat
    assert toon_cast.DOG.paw == ""  # the older cast keeps coat-coloured paws


@pytest.mark.parametrize("name", list(NEW))
def test_a_new_character_types_speaks_and_blinks(name):
    look = toon_cast.LOOKS[name]
    assert look.brows or name == "raccoon"  # the raccoon's eyes sit in its mask: no brows to see there
    assert look.shine and look.blink > 0
    cv = canvas(8.0)
    poses = toon.parse_poses(
        [
            {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
            {"start": 4.0, "eyes": "half", "mouth": "smirk", "arms": "type"},
        ]
    )
    track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    getattr(toon_cast, name)(cv, cv.comp, poses, 8.0, taps=(4.5, 4.7), mouths=track)
    first, second = runs_of(cv)
    lips, shut = first.findall("group")
    assert len(lips.findall("group")) == 4  # closed, open, round, teeth
    assert shut.find("animate").get("property") == "opacity"
    assert len(second.findall("group")) == 3  # the two typing frames and the blink lids


def test_a_sketch_plays_the_new_three_by_name():
    lines = (Line("a", "New phone who dis."), Line("b", "Your bank."), Line("c", "Oh no."))

    def speaker(name, who):
        return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)

    beats = (
        Beat(0.0, "fox", lines[0].text, "half", "smirk", "type", 0, 0),
        Beat(2.0, "raccoon", lines[1].text, "narrow", "flat", "crossed", 1, 0),
        Beat(4.0, "hedgehog", lines[2].text, "shock", "o", "face", 2, 0),
    )
    sk = Sketch(
        "new-three",
        "New three",
        (speaker("a", "fox"), speaker("b", "raccoon"), speaker("c", "hedgehog")),
        lines,
        beats,
        6.0,
    )
    sketch.check(sk)
    cv = canvas(6.0)
    mouths = {"fox": [(0.2, "open"), (0.5, "closed")]}
    groups = sketch.draw_cast(cv, cv.comp, sk.beats, sk.end, mouths=mouths, versions={"toon-fox": 1})
    assert len(groups) == 3
    assert [(g.get("start"), g.get("end")) for g in runs_of(cv)] == [("0", "2"), ("2", "4"), ("4", "6")]


@pytest.mark.parametrize("name", list(NEW))
def test_a_headset_fits_the_new_heads(name):
    look = toon_cast.LOOKS[name]
    layers = toon_cast.headset(look)
    band = brush.bounds(layers[0][0])
    top = min(y for _, y in look.silhouette)
    assert top - 16 < band[1] < top
