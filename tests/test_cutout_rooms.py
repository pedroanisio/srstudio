"""The two polished Cutout locations: the conference room and the reception, their slots, light and signature."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, Signature, cast, locations, props, registry
from srstudio.cast import OfficeActor

ROOMS = {"conference-room": "conference_room", "reception": "reception"}
PROPS = ("whiteboard", "blinds-window", "speakerphone", "globe-pendant", "reception-counter", "slat-wall")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def signed_canvas(signed: bool = True):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=2, background=OFFICE.background)
    return scene, Canvas(scene, OFFICE, signature=Signature() if signed else None)


def ids_in_order(root) -> list[str]:
    return [el.get("id") for el in root.iter() if el.get("id")]


def by_id(root, name):
    return next(el for el in root.iter() if el.get("id") == name)


def test_the_rooms_and_their_props_are_registered_cutout_parts():
    for name in ROOMS:
        entry = registry.get("location", name)
        assert entry.style == "cutout" and entry.summary, name
    for name in PROPS:
        entry = registry.get("prop", name)
        assert entry.style == "cutout" and entry.summary, name


@pytest.mark.parametrize("name", ROOMS)
def test_each_room_is_gated_lit_with_a_glaze_signed_and_valid(name):
    scene, cv = signed_canvas()
    g = getattr(locations, ROOMS[name])(cv, cv.comp, shots=[(0.5, 1)])
    root = ET.fromstring(scene.to_bytes())
    ids = ids_in_order(root)
    assert g.id == f"location-{name}"
    assert {f"{g.id}-light", "sig-cactus", "sig-code"} <= set(ids)
    room = by_id(root, g.id)
    assert [k.get("value") for k in room.iter() if local(k.tag) == "key"][:2] == ["0", "1"]
    light = [s for s in by_id(root, f"{g.id}-light").iter() if local(s.tag) == "shape"]
    assert light and all(0 < float(s.get("opacity")) < 0.5 for s in light), "light is a glaze, not paint"
    assert [f for f in scene.check() if f.severity == "error"] == []


@pytest.mark.parametrize("name", ROOMS)
def test_an_unsigned_room_draws_no_marks(name):
    scene, cv = signed_canvas(signed=False)
    getattr(locations, ROOMS[name])(cv, cv.comp)
    root = ET.fromstring(scene.to_bytes())
    assert not [i for i in ids_in_order(root) if i.startswith("sig-")]


def marker(cv, label):
    return lambda g: cv.group(g, label)


def test_the_conference_room_seats_its_slot_behind_the_table_and_in_front_of_the_chair():
    scene, cv = signed_canvas()
    locations.conference_room(cv, cv.comp, behind_table=marker(cv, "seated"), on_table=marker(cv, "on-table"))
    ids = ids_in_order(ET.fromstring(scene.to_bytes()))
    assert (
        ids.index("location-conference-room-chair")
        < ids.index("seated")
        < ids.index("location-conference-room-table")
        < ids.index("on-table")
    )


def test_the_reception_puts_the_clerk_behind_the_counter_and_the_visitor_in_front():
    scene, cv = signed_canvas()
    locations.reception(
        cv, cv.comp, behind_desk=marker(cv, "clerk"), on_desk=marker(cv, "on-desk"), at_desk=marker(cv, "visitor")
    )
    ids = ids_in_order(ET.fromstring(scene.to_bytes()))
    assert ids.index("clerk") < ids.index("location-reception-counter") < ids.index("on-desk") < ids.index("visitor")


@pytest.mark.parametrize(
    ("seat", "edge"),
    [(locations.CONFERENCE_SEAT, locations.CONFERENCE_TABLE_Y), (locations.RECEPTION_CLERK, locations.COUNTER_Y)],
)
def test_a_seated_office_actor_shows_the_whole_head_and_hides_the_body_end_behind_the_furniture(seat, edge):
    x, y, scale = seat
    assert y + 100 * scale < edge, "the chin clears the furniture"
    assert y + OfficeActor.bottom * scale > edge + 20, "the body's cut end is hidden"
    assert 100 * scale < x < 1080 - 100 * scale


def test_the_visitor_stands_on_the_floor_in_front_of_the_counter_inside_the_frame():
    x, y, scale = locations.RECEPTION_VISITOR
    feet = y + 489 * scale  # the standing customer's soles
    assert locations.COUNTER_FLOOR < feet < 1920
    assert 130 * scale < x < 1080 - 130 * scale


def test_both_rooms_take_the_series_cast_and_validate():
    scene, cv = signed_canvas()
    x, y, s = locations.CONFERENCE_SEAT
    locations.conference_room(cv, cv.comp, shots=[(0, 1)], behind_table=lambda g: cast.Manager(cv).build(g, x, y, s))
    locations.reception(
        cv,
        cv.comp,
        shots=[(1, 2)],
        behind_desk=lambda g: cast.Candidate(cv).build(g, *locations.RECEPTION_CLERK),
        at_desk=lambda g: cast.Customer(cv).build(g, *locations.RECEPTION_VISITOR),
    )
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_props_draw_alone_and_the_whiteboard_chart_is_typed():
    scene, cv = signed_canvas()
    props.whiteboard(cv, cv.comp, 560, 300, 460, 420, rising=False)
    props.speakerphone(cv, cv.comp, 540, 1300)
    props.globe_pendant(cv, cv.comp, 300, 260)
    with pytest.raises(ValueError, match="whiteboard"):
        props.whiteboard(cv, cv.comp, 0, 0, 40, 40)
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_the_conference_room_can_leave_its_wall_to_a_slot_drawn_behind_the_chair():
    scene, cv = signed_canvas()
    locations.conference_room(
        cv, cv.comp, rising=None, on_wall=marker(cv, "own-board"), behind_table=marker(cv, "seated")
    )
    ids = ids_in_order(ET.fromstring(scene.to_bytes()))
    assert "location-conference-room-whiteboard" not in ids
    order = ["location-conference-room-window", "own-board", "location-conference-room-light", "seated"]
    assert [ids.index(i) for i in order] == sorted(ids.index(i) for i in order)


def opacity_keys(el) -> list[tuple[float, float]]:
    return [
        (float(k.get("time")), float(k.get("value")))
        for a in el.iter()
        if local(a.tag) == "animate" and a.get("property") == "opacity"
        for k in a.iter()
        if local(k.tag) == "key"
    ]


def test_the_speakerphone_lights_its_ring_while_the_far_end_talks():
    scene, cv = signed_canvas()
    props.speakerphone(cv, cv.comp, 540, 1300, id="phone", talk=[(0.4, 1.0), (1.2, 1.8)])
    ring = by_id(ET.fromstring(scene.to_bytes()), "phone-talk")
    assert opacity_keys(ring) == [(0, 0), (0.4, 1), (1.0, 0), (1.2, 1), (1.8, 0)]
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_a_quiet_speakerphone_draws_no_ring_and_bad_spans_are_refused():
    scene, cv = signed_canvas()
    props.speakerphone(cv, cv.comp, 540, 1300, id="phone")
    assert "phone-talk" not in ids_in_order(ET.fromstring(scene.to_bytes()))
    for spans in ([(1.0, 1.0)], [(-0.1, 0.5)], [(0.5, 1.0), (0.8, 1.2)], [(1.2, 1.8), (0.4, 1.0)]):
        with pytest.raises(ValueError, match="talk"):
            props.speakerphone(cv, cv.comp, 540, 1300, id="bad", talk=spans)


def test_the_conference_room_passes_the_calls_talk_to_its_speakerphone():
    scene, cv = signed_canvas()
    locations.conference_room(cv, cv.comp, speaker_talk=[(0.2, 0.9)])
    ring = by_id(ET.fromstring(scene.to_bytes()), "location-conference-room-speakerphone-talk")
    assert opacity_keys(ring) == [(0, 0), (0.2, 1), (0.9, 0)]


def code_at(root) -> tuple[str | None, str | None]:
    mark = next(el for el in root.iter() if el.get("id") == "sig-code")
    return mark.get("x"), mark.get("y")


def test_the_reception_keeps_its_code_where_it_was_unless_a_reel_moves_it():
    scene, cv = signed_canvas()
    locations.reception(cv, cv.comp)
    moved_scene, moved_cv = signed_canvas()
    locations.reception(moved_cv, moved_cv.comp, code_at=(560, 1376))
    assert code_at(ET.fromstring(scene.to_bytes())) != code_at(ET.fromstring(moved_scene.to_bytes()))
    fresh_scene, fresh_cv = signed_canvas()
    locations.reception(fresh_cv, fresh_cv.comp, code_at=locations.RECEPTION_CODE)
    assert scene.to_bytes() == fresh_scene.to_bytes()


def test_a_cup_in_the_air_can_leave_its_contact_shadow_off():
    def shapes(**options):
        scene, cv = signed_canvas()
        props.coffee_cup(cv, cv.group(cv.comp, "held"), 0, 0, **options)
        return [el for el in ET.fromstring(scene.to_bytes()).iter() if local(el.tag) == "shape"]

    assert len(shapes()) == len(shapes(shadow=True))
    assert len(shapes(shadow=False)) == len(shapes()) - 1
