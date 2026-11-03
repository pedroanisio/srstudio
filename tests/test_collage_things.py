"""The Collage things for tables and corners: each is registered and draws, each refuses what it cannot draw, a
twitch shuts one eye on the caller's clock, and a group held for an opening does not move."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_things, flat_counter, registry, sketch
from srstudio.canvas import Signature
from srstudio.collage_group import GroupError, Lineup, Place
from srstudio.collage_things import ThingError
from support.acting import evaluate


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    cv.font_asset = "font"
    return cv


DRAWS = {
    "collage-handset": lambda cv, g: collage_things.handset(cv, g, 500, 900),
    "collage-desk-phone": lambda cv, g: collage_things.desk_phone(
        cv, g, 540, 1500, 420, "PARIS", off_hook=True, size=40
    ),
    "collage-resume": lambda cv, g: collage_things.resume(cv, g, 540, 900, 500, turn=4.0),
    "collage-fork": lambda cv, g: collage_things.fork(cv, g, 200, 900),
    "collage-gravy-boat": lambda cv, g: collage_things.gravy_boat(cv, g, 540, 1500),
    "collage-tiny-cup": lambda cv, g: collage_things.tiny_cup(cv, g, 540, 1500),
    "collage-wine-glass": lambda cv, g: collage_things.wine_glass(cv, g, 540, 1500),
    "collage-bank-card": lambda cv, g: collage_things.bank_card(cv, g, 540, 900, 330, "GARY"),
    "collage-receipt": lambda cv, g: collage_things.receipt(cv, g, 540, 900, torn=True),
    "collage-wallet": lambda cv, g: collage_things.wallet(cv, g, 540, 900),
    "collage-counter": lambda cv, g: collage_things.counter(cv, g, 1500),
    "collage-till": lambda cv, g: collage_things.till(cv, g, 540, 1300, 320, "PAID", size=40),
    "collage-stool": lambda cv, g: collage_things.stool(cv, g, 540, 1500),
    "collage-towel": lambda cv, g: collage_things.towel(cv, g, 540, 900),
    "collage-ring-corner": lambda cv, g: collage_things.ring_corner(cv, g),
    "collage-eye-twitch": lambda cv, g: collage_things.twitch(cv, g, "brent", (1.0, 2.0)),
}


def group() -> tuple[Canvas, object]:
    cv = canvas()
    return cv, cv.comp


@pytest.mark.parametrize("name", sorted(DRAWS))
def test_a_thing_is_registered_and_draws(name):
    cv, parent = group()
    assert registry.get("prop", name) is not None
    assert DRAWS[name](cv, parent) is not None
    assert cv.scene.to_bytes()


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv, g: collage_things.handset(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.desk_phone(cv, g, 0, 0, -1.0, "x"),
        lambda cv, g: collage_things.resume(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.fork(cv, g, 0, 0, -3.0),
        lambda cv, g: collage_things.gravy_boat(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.tiny_cup(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.wine_glass(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.bank_card(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.receipt(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.receipt(cv, g, 0, 0, 100.0, -1.0),
        lambda cv, g: collage_things.wallet(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.till(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.stool(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.towel(cv, g, 0, 0, 0.0),
        lambda cv, g: collage_things.towel(cv, g, 0, 0, 100.0, 0.0),
        lambda cv, g: collage_things.ring_corner(cv, g, h=0.0),
        lambda cv, g: collage_things.ring_corner(cv, g, reach=0.0),
        lambda cv, g: collage_things.twitch(cv, g, "nobody", (1.0,)),
        lambda cv, g: collage_things.twitch(cv, g, "brent", (1.0,), side=0),
        lambda cv, g: collage_things.twitch(cv, g, "brent", ()),
        lambda cv, g: collage_things.twitch(cv, g, "brent", (2.0, 1.0)),
    ],
)
def test_a_thing_refuses_what_it_cannot_draw(draw):
    cv, parent = group()
    with pytest.raises(ThingError):
        draw(cv, parent)


def test_a_torn_receipt_is_a_different_cut():
    def outline(torn):
        cv, parent = group()
        collage_things.receipt(cv, parent, 500, 900, torn=torn)
        return cv.scene.to_bytes(layout="pretty")

    assert outline(True) != outline(False)


def test_the_twitch_shuts_the_eye_on_the_callers_clock():
    cv, parent = group()
    g = collage_things.twitch(cv, parent, "brent", (1.0, 2.0))
    root = ET.fromstring(cv.scene.to_bytes())
    node = next(e for e in root.iter() if e.get("id") == g.id)
    anim = next(e for e in node if e.tag.endswith("animate"))
    times = [float(k.get("time")) for k in anim]
    assert 1.0 in times and 2.0 in times


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('times,end', [((1, 1.04), 1.13), ((1, 1.09), 1.18), ((1, 1.04, 1.12), 1.21)])
def test_overlapping_twitches_keep_the_eye_shut_until_the_last_cue_ends(local, times, end):
    cv = canvas()
    cv.local_time = local
    g = collage_things.twitch(cv, cv.comp, 'brent', times)
    node = ET.fromstring(cv.scene.to_bytes()).find(f'.//group[@id="{g.id}"]')
    anim = node.find('animate')
    assert anim.get('timeBase', 'composition') == 'composition'
    assert [(float(k.get('time')), float(k.get('value'))) for k in anim] == [(0, 0), (1, 1), (end, 0)]


@pytest.mark.parametrize('local', [False, True])
def test_twitch_overlap_evaluates_on_project_clock_in_a_later_shot(local, scene_render, tmp_path):
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', start=0, end=2)
    shot = sequence.add_group(id='shot', start=0, end=3)
    g = collage_things.twitch(cv, shot, 'brent', (3, 3.04))
    path = tmp_path / 'twitch.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for time, expected in ((3.10, 1), (3.14, 0), (2.99, 0), (3.10, 1)):
        node = next(n for n in evaluate(scene_render, path, time) if n['id'] == g.id)
        assert node['world_opacity'] == expected
        states.append(node)
    assert states[0] == states[-1]


def test_a_held_group_keys_nothing():
    cv, parent = group()
    pose = ({"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "down"},)
    lineup = Lineup(
        {"brent": Place(285.0, 1565.0, 0.72), "deb": Place(800.0, 1565.0, 0.72)},
        {"brent": pose, "deb": pose},
        spans=((0.0, 0.45),),
    )
    beats = [sketch.Beat(0.0, "brent", "", "open", "flat", "down", None, None, "", ())]
    face = lineup.held(cv, parent, sketch.appearances(beats, 0.45)[0], {})
    assert face[0] == pytest.approx(285.0)
    assert b"animate" not in cv.scene.to_bytes()


def test_a_held_group_needs_its_opener_in_the_lineup():
    cv, parent = group()
    pose = ({"start": 0.0, "eyes": "open", "mouth": "flat", "arms": "down"},)
    lineup = Lineup({"deb": Place(800.0, 1565.0, 0.72)}, {"deb": pose}, spans=((0.0, 0.45),))
    beats = [sketch.Beat(0.0, "brent", "", "open", "flat", "down", None, None, "", ())]
    with pytest.raises(GroupError):
        lineup.held(cv, parent, sketch.appearances(beats, 0.45)[0], {})
