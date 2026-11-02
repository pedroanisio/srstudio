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


def test_household_discovery_recipe_owns_visibility_for_a_validation_only_end():
    ns = recipe('toon-household-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['pile_result'] is None
    assert ns['holder'].end == 3
    assert ns['pipe_result'] in list(ns['holder'].elements())
    assert ns['pipe_result'].end is None
    assert ns['pile_info']['arguments']['properties']['end']['x-role'] == 'validation-limit'


def test_domestic_discovery_recipe_uses_a_returned_group_and_explicit_point_shape():
    ns = recipe('toon-domestic-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['bottle'] in list(ns['holder'].elements())
    assert ns['bottle'].end == 3
    assert ns['point_schema']['type'] == 'array'
    assert len(ns['point_schema']['prefixItems']) == 2


def test_study_discovery_recipe_maps_reference_book_geometry_to_frame_marker_keys():
    ns = recipe('toon-study-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['marker_info']['arguments']['properties']['at']['x-space'] == 'frame'
    assert ns['book_result'] is ns['marker_result'] is None
    group = next(n for n in ns['scene'].iter('group') if n.id == 'marker')
    assert group.x == pytest.approx(ns['left'] + 0.02 * (ns['right'] - ns['left']))
    assert group.y == ns['y']
    animations = list(ns['scene'].iter('animate'))
    assert len(animations) == 2
    assert all(a.defaultInterpolation == 'linear' and a.timeBase is None for a in animations)


def test_care_discovery_recipe_distinguishes_whole_cabinet_from_moving_front():
    ns = recipe('toon-care-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['cabinet'].end == 3
    assert ns['front'] not in ns['cabinet'].elements()
    assert ns['front'].end is None
    assert 'moving drawer front' in ns['drawer_info']['returns']['description']
    assert ns['lamp_result'] is None
    assert ns['lamp_info']['arguments']['properties']['end']['x-role'] == 'animation-limit'
    assert ns['lamp_holder'].end == 3
    assert all(a.timeBase is None for a in ns['scene'].iter('animate'))


def test_care_discovery_recipe_keeps_dim_light_and_smooth_drawer_motion(tmp_path, scene_render):
    from srstudio.toon import fx
    from srstudio.toon_bed import GLOW
    from support.acting import evaluate

    ns = recipe('toon-care-discovery')
    scene, front = ns['scene'], ns['front']
    glow = next(s for s in scene.iter('shape') if s.fill == GLOW)
    path = tmp_path / 'care.scene.xml'
    path.write_bytes(scene.to_bytes())
    for time, opacity in ((0.5, 0), (2, 0.35), (2.225, 0.35), (2.45, 0.35)):
        nodes = {n['id']: n for n in evaluate(scene_render, path, time)}
        assert nodes[glow.id]['world_opacity'] == pytest.approx(opacity)
        if time == 2.225:
            assert nodes[front.id]['local'][0] == pytest.approx(1.025)
            assert nodes[front.id]['local'][3] == pytest.approx(0.93)
    nodes = {n['id']: n for n in evaluate(scene_render, path, 1.02)}
    assert float(nodes[front.id]['props']['x']) == pytest.approx(fx(494) - 3.5)


def test_lit_room_discovery_recipe_places_overlay_after_actor_and_returns_typed_cues():
    from srstudio.toon_rooms import Cue

    ns = recipe('toon-lit-room-discovery')
    assert ns['scene'].check(schema=True) == []
    assert ns['cv'].comp.elements() == [ns['back'], ns['actor'], ns['light'], ns['front']]
    assert ns['cues']['lamp'] == [Cue(0, 'on'), Cue(1, 'dim')]
    assert ns['room_info']['returns']['x-role'] == 'parsed-light-cues'
    assert ns['light'].elements() and ns['back'].elements()


def test_lit_room_discovery_recipe_fades_light_continuously_in_engine(tmp_path, scene_render):
    from support.acting import evaluate

    ns = recipe('toon-lit-room-discovery')
    shade = next(g for g in ns['light'].elements() if g.blend == 'multiply')
    path = tmp_path / 'room.scene.xml'
    path.write_bytes(ns['scene'].to_bytes())
    for time, expected in ((0.5, 0), (1, 0), (1.375, 0.0975), (1.75, 0.195), (2.5, 0.39), (3, 0.39)):
        node = next(n for n in evaluate(scene_render, path, time) if n['id'] == shade.id)
        assert node['world_opacity'] == pytest.approx(expected)


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
