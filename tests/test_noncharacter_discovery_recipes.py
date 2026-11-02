"""The public discovery recipes bind real callbacks and preserve a flat prop's local contact anchor."""

import math
from pathlib import Path

import pytest

from srstudio.head_motion import Channel


def recipe(name):
    document = Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md'
    section = document.read_text().split(f'<!-- {name}:start -->')[1].split(f'<!-- {name}:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, str(document), 'exec'), namespace)
    return namespace


def test_location_discovery_recipe_invokes_a_real_actor_slot_once():
    ns = recipe('location-discovery')
    assert len(ns['seated']) == 1
    assert ns['seated'][0] in list(ns['room'].elements())
    assert ns['scene'].check(schema=True) == []
    assert ns['repair']['code'] == 'location.slot'
    assert ns['repair']['path'] == 'behind_desk'


def test_toon_discovery_recipe_distinguishes_reference_coordinates_and_animation_clocks():
    ns = recipe('toon-drawing-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['plant_result'] is ns['clock_result'] is None
    assert ns['plant_info']['returns']['type'] == 'null'
    assert (
        ns['clock_info']['arguments']['properties']['times']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    )
    animations = list(ns['scene'].iter('animate'))
    assert any(a.timeBase == 'local' for a in animations)
    assert any(a.property == 'rotation' and a.timeBase is None for a in animations)


def test_held_prop_recipe_publishes_a_schema_valid_scene_and_no_contact_shadow():
    ns = recipe('held-prop-discovery')
    assert ns['scene'].check(schema=True) == []
    cup = ns['cups'][0]
    assert cup in list(ns['hand'].elements())
    assert cup.anchorX == 0 and cup.anchorY == 24
    assert not any(n.attributes().get('fill') == '#5C4D3E' for n in cup.iter())
    # The callback places the cup between the palm and closing fingers.
    children = [n for n in ns['hand'].elements() if n.xml_name in ('shape', 'group')]
    at = children.index(cup)
    assert at > 0 and len(children) - at - 1 == 4


@pytest.mark.parametrize('time', [2.9, 0.0, 1.7, 0.5, 3.0])
def test_held_prop_anchor_remains_on_the_hand_through_shared_transforms(time):
    ns = recipe('held-prop-discovery')
    cup, hand = ns['cups'][0], ns['hand']
    anchor = ns['cup_info']['returns']['x-anchors']['body-center']
    # The geometry's published anchor maps to the hand origin before any parent motion.
    x = float(cup.x) + (anchor[0] - float(cup.anchorX)) * float(cup.scaleX)
    y = float(cup.y) + (anchor[1] - float(cup.anchorY)) * float(cup.scaleY)
    animations = {a.property: a for a in hand.find_all('animate')}

    def value(name):
        keys = tuple((float(k.time), float(k.value)) for k in animations[name].find_all('key'))
        return Channel(keys, curve='sine-in-out').sample(time)

    angle, height = math.radians(value('rotation')), value('y')
    world = (
        float(hand.x) + (x * math.cos(angle) - y * math.sin(angle)) * float(hand.scaleX),
        height + (x * math.sin(angle) + y * math.cos(angle)) * float(hand.scaleY),
    )
    assert world == pytest.approx((float(hand.x), height), abs=1e-9)
