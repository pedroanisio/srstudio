"""The park bench as a two-hander: an office actor with legs to sit on it, the seat line, a handful of crumbs, and the
park sign that can leave its lettering out."""

import hashlib
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, Canvas, Signature, cast, locations, props, registry, signature
from srstudio.rig import Performance
from test_signature import TODAY, _canvas


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4, background=CAFE.background)
    return scene, Canvas(scene, CAFE, signature=Signature())


def ids(scene) -> list[str]:
    return [el.get("id") for el in ET.fromstring(scene.to_bytes()).iter() if el.get("id")]


def by_id(scene, name):
    return next(el for el in ET.fromstring(scene.to_bytes()).iter() if el.get("id") == name)


def test_an_office_actor_draws_no_legs_unless_asked():
    scene, cv = canvas()
    cast.Manager(cv, tag="manager-desk").build(cv.comp, 540, 800, 1.0, Performance())
    assert not [i for i in ids(scene) if i.endswith("-legs")]


def test_a_seated_office_actor_has_legs_drawn_behind_its_torso():
    scene, cv = canvas()
    boss = cast.Manager(cv, tag="manager-park")
    boss.build(cv.comp, 720, 900, 1.2, Performance(extras={"legs": "seated"}))
    order = ids(scene)
    legs = f"{boss.tag_base}-legs"
    assert legs in order and order.index(legs) < order.index(f"{boss.tag_base}-head")
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_an_unknown_leg_pose_is_refused():
    _, cv = canvas()
    with pytest.raises(ValueError, match="legs"):
        cast.Manager(cv).build(cv.comp, 540, 800, 1.0, Performance(extras={"legs": "kneeling"}))


def test_the_seat_line_puts_a_seated_actors_torso_on_the_bench():
    for bottom in (cast.Manager.bottom, 300):
        y = locations.park_seat_y(bottom, 1.25)
        assert y + bottom * 1.25 == pytest.approx(locations.PARK_SEAT_Y)
    assert 1030 < locations.PARK_SEAT_Y < 1268  # between the backrest's top slat and the seat's front edge


def test_crumbs_are_a_registered_cutout_prop_that_fall_when_tossed():
    entry = registry.get("prop", "crumbs")
    assert entry.style == "cutout" and entry.summary
    scene, cv = canvas()
    g = props.crumbs(cv, cv.comp, 500, 1200, 1500, toss=1.5, count=6, seed=3)
    names = ids(scene)
    assert g.id == "crumbs" and len([i for i in names if i.startswith("crumbs-bit-")]) == 6
    keys = [k for k in by_id(scene, "crumbs").iter() if k.tag.rsplit("}", 1)[-1] == "key"]
    assert keys, "the handful is gated and falls from the toss"
    assert [f for f in scene.check() if f.severity == "error"] == []


@pytest.mark.parametrize("bad", [dict(count=0), dict(toss=-1.0), dict(ground=1100)])
def test_crumbs_refuse_an_empty_a_negative_or_an_upward_toss(bad):
    _, cv = canvas()
    args = dict(toss=1.0, count=5, ground=1500) | bad
    with pytest.raises(ValueError):
        props.crumbs(cv, cv.comp, 500, 1200, args.pop("ground"), **args)


def test_the_park_keeps_todays_bytes_with_its_sign_lettered():
    for kw in ({}, dict(sign_lettering=True)):
        cv = _canvas(CAFE)
        locations.park(cv, cv.comp, **kw)
        assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == TODAY["park"]


def test_the_park_can_leave_its_sign_lettering_out_and_keeps_the_board_and_both_marks():
    lettered, plain = _canvas(CAFE), _canvas(CAFE)
    locations.park(lettered, lettered.comp)
    locations.park(plain, plain.comp, sign_lettering=False)
    gone = set(ids(lettered.scene)) - set(ids(plain.scene))
    assert gone == {"park-sign", "park-sign-layer"}  # the text and its layer, nothing else
    assert signature.missing(plain.scene.to_bytes()) == []
    assert by_id(plain.scene, "sig-code").get("x") == by_id(lettered.scene, "sig-code").get("x")  # still on the board
    assert [f for f in plain.scene.check() if f.severity == "error"] == []


@pytest.mark.parametrize("bad", [0, 1, None, "no"])
def test_the_park_refuses_a_sign_lettering_that_is_not_a_bool(bad):
    cv = _canvas(CAFE)
    with pytest.raises(locations.LocationError, match="sign_lettering"):
        locations.park(cv, cv.comp, sign_lettering=bad)
