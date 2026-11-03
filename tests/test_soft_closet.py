"""Soft closets: two plain doors in a wall, a mop, and the dark behind them with its one line of light."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, registry, soft_closet
from srstudio.soft_closet import Door, SoftClosetError
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def keyed(group, prop: str) -> list[tuple[float, float]]:
    animate = next(a for a in group if a.tag.endswith("animate") and a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in animate]


def test_the_module_is_a_part_of_the_soft_style():
    assert "soft_closet" in SOFT.parts
    entries = {e.name: e for e in registry.entries()}
    assert {e.style for n, e in entries.items() if n in ("soft-door", "soft-mop", "soft-closet")} == {"soft"}


def test_what_stands_in_a_doorway_goes_between_the_dark_and_the_door():
    cv = canvas()
    order = []
    soft_closet.doors(cv, cv.comp, [Door(150, 340, 640, ((0.0, 3.0),))], between=lambda g: order.append(g))
    assert len(order) == 1
    names = list(groups(cv))
    assert names.index("soft-door-dark-0") < names.index("soft-door-between") < names.index("soft-door-shut-0")


def test_a_door_is_shut_only_when_it_says_and_open_the_rest_of_the_reel():
    cv = canvas()
    soft_closet.doors(cv, cv.comp, [Door(150, 340, 640, ((0.0, 3.0), (5.0, 9.0)))], end=10.0)
    made = groups(cv)
    assert "soft-door-shut-0" in made and "soft-door-open-0" in made


def test_a_door_hinges_on_the_side_it_says():
    left, right = canvas(), canvas()
    soft_closet.doors(left, left.comp, [Door(150, 340, 640, ((0.0, 1.0),), hinge="left")], end=4.0)
    soft_closet.doors(right, right.comp, [Door(150, 340, 640, ((0.0, 1.0),), hinge="right")], end=4.0)
    assert left.scene.to_bytes() != right.scene.to_bytes()


@pytest.mark.parametrize(
    "door",
    [
        Door(340, 150, 640, ()),
        Door(150, 150, 640, ()),
        Door(150, 340, 0, ()),
        Door(150, float("nan"), 640, ()),
        Door(150, 340, 640, ((3.0, 1.0),)),
        Door(150, 340, 640, ((-1.0, 1.0),)),
        Door(150, 340, 640, (), hinge="top"),
    ],
)
def test_a_door_refuses_what_it_cannot_draw(door):
    cv = canvas()
    with pytest.raises(SoftClosetError):
        soft_closet.doors(cv, cv.comp, [door])


def test_two_doors_may_not_stand_in_each_others_way():
    cv = canvas()
    with pytest.raises(SoftClosetError):
        soft_closet.doors(cv, cv.comp, [Door(150, 340, 640, ()), Door(300, 500, 640, ())])


def test_doors_need_a_door_and_a_callable_between():
    cv = canvas()
    with pytest.raises(SoftClosetError):
        soft_closet.doors(cv, cv.comp, [])
    with pytest.raises(SoftClosetError):
        soft_closet.doors(cv, cv.comp, [Door(150, 340, 640, ())], between="pip")


def test_a_mop_stands_still_until_it_is_told_to_tip():
    still, tipping = canvas(), canvas()
    soft_closet.mop(still, still.comp, 200, 1500)
    soft_closet.mop(tipping, tipping.comp, 200, 1500, tips=(1.0, 2.0))
    assert not [a for a in groups(still)["soft-mop"] if a.tag.endswith("animate")]
    assert keyed(groups(tipping)["soft-mop"], "rotation")[0] == (0.0, 6.0)


@pytest.mark.parametrize("options", [dict(scale=0), dict(scale=float("nan")), dict(tips=(2.0, 1.0)), dict(lean=99.0)])
def test_a_mop_refuses_what_it_cannot_draw(options):
    cv = canvas()
    with pytest.raises(SoftClosetError):
        soft_closet.mop(cv, cv.comp, 200, 1500, **options)


def test_the_closet_shows_only_in_its_span_and_keeps_a_line_of_light():
    cv = canvas()
    soft_closet.closet(cv, cv.comp, 2.0, 5.0, slit=(640.0, 684.0))
    made = groups(cv)
    assert "soft-closet-light" in made
    assert made["soft-closet"].get("id") == "soft-closet"


def test_what_is_behind_the_veil_is_drawn_before_it():
    cv = canvas()
    soft_closet.closet(cv, cv.comp, 2.0, 5.0, behind=lambda g: cv.group(g, "pip-in-the-dark"))
    names = list(groups(cv))
    assert names.index("pip-in-the-dark") < names.index("soft-closet-light")


@pytest.mark.parametrize(
    "options",
    [
        dict(start=5.0, end=2.0),
        dict(start=-1.0, end=2.0),
        dict(slit=(700.0, 640.0)),
        dict(slit=(-10.0, 40.0)),
        dict(slit=(1000.0, 1100.0)),
        dict(veil=1.5),
        dict(behind="pip"),
    ],
)
def test_a_closet_refuses_what_it_cannot_draw(options):
    cv = canvas()
    arguments = dict(start=2.0, end=5.0) | options
    with pytest.raises(SoftClosetError):
        soft_closet.closet(cv, cv.comp, **arguments)


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('spans', [((1, 5), (2, 3)), ((2, 3), (1, 5)), ((1, 3), (2, 5)), ((1, 3), (3, 5))])
def test_shut_spans_and_open_door_are_complements_even_when_spans_overlap(local, spans):
    cv = canvas()
    cv.local_time = local
    soft_closet.doors(cv, cv.comp, [Door(150, 340, 640, spans)], end=8)
    nodes = groups(cv)
    closed = keyed(nodes['soft-door-shut-0'], 'opacity')
    opened = keyed(nodes['soft-door-open-0'], 'opacity')
    assert closed == [(0, 0), (1, 1), (5, 0)]
    assert opened == [(0, 1), (1, 0), (5, 1), (8, 0)]
    for name in ('soft-door-shut-0', 'soft-door-open-0'):
        a = next(nodes[name].iter('animate'))
        assert a.get('timeBase', 'composition') == ('local' if local else 'composition')
