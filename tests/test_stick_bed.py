"""The bed at night: sitting up, the mound that breathes and sinks, the sleep mask, the phone's traces and the low
light, each refusing what it cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_bed
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature())


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animated(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_parts_are_registered_and_tagged():
    for kind, name in (("prop", "stick-duvet"), ("prop", "stick-eye-mask"), ("prop", "stick-recorder")):
        assert registry.get(kind, name)


def test_every_sitting_pose_keeps_its_hips_under_the_duvet_of_a_scaled_figure():
    scale, top = 0.8, 450.0
    for pose in stick_bed.BED.values():
        assert top + scale * pose.hip[1] > 1510 + 26


def test_a_figure_can_sit_up_in_each_pose():
    cv = canvas()
    keys = [stick.RigKey(float(k), name) for k, name in enumerate(stick_bed.BED)]
    stick.rig(cv, cv.comp, keys, 4.0, poses=stick_bed.BED)


def test_only_the_mound_rises_and_what_lies_on_it_rises_with_it():
    cv = canvas()
    mound = stick_bed.duvet(cv, cv.comp, 2.0, lift=[(0.0, 0.0), (1.0, -30.0)])
    stick_bed.recorder(cv, mound, 540.0, 1400.0, 2.0)
    assert animated(cv, "y") == [[(0.0, 0.0), (1.0, -30.0)]]
    assert mound.id in {g.get("id") for g in xml(cv).iter("group")}


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        (dict(end=0), "lasts some seconds"),
        (dict(end=2.0, near=100.0), "runs from its top edge"),
        (dict(end=2.0, width=0), "runs from its top edge"),
        (dict(end=2.0, lift=[(1.0, 0.0), (0.5, 1.0)]), "rising within the shot"),
        (dict(end=2.0, lift=[(3.0, 0.0)]), "rising within the shot"),
    ],
)
def test_a_duvet_it_cannot_draw_is_refused(kwargs, match):
    end = kwargs.pop("end")
    with pytest.raises(StickDataError, match=match):
        stick_bed.duvet(canvas(), None, end, **kwargs)


@pytest.mark.parametrize("scale", [0, -1, float("nan")])
def test_a_mask_with_no_size_is_refused(scale):
    with pytest.raises(StickDataError, match="positive scale"):
        stick_bed.eye_mask(canvas(), None, 0.0, 0.0, scale=scale)


def test_the_phone_draws_a_trace_for_each_sound_and_the_last_one_shakes_while_live():
    still, live = canvas(), canvas()
    stick_bed.recorder(still, still.comp, 540.0, 960.0, 1.0, lines=2)
    stick_bed.recorder(live, live.comp, 540.0, 960.0, 1.0, lines=2, live=True)
    assert animated(still, "opacity") == []
    assert animated(live, "opacity")


@pytest.mark.parametrize(("lines", "end"), [(4, 1.0), (-1, 1.0), ("2", 1.0), (1, 0)])
def test_a_phone_it_cannot_draw_is_refused(lines, end):
    with pytest.raises(StickDataError):
        stick_bed.recorder(canvas(), None, 0.0, 0.0, end, lines=lines)


def test_low_light_multiplies_so_the_ink_stays_black():
    cv = canvas()
    node = stick_bed.lights_low(cv, cv.comp, pool=(540.0, 800.0, 500.0))
    found = [g for g in xml(cv).iter("group") if g.get("id") == node.id]
    assert found[0].get("blend") == "multiply"


def test_a_stronger_light_leaves_less_of_the_picture():
    assert stick_bed._towards("#30406e", 1.0) == "#30406e"
    assert stick_bed._towards("#30406e", 0.0) == "#ffffff"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(tint="navy"),
        dict(tint="#30406e80"),
        dict(strength=0),
        dict(strength=1.5),
        dict(pool=(0.0, 0.0, 0.0)),
        dict(area=(0.0, 0.0, 0.0, 10.0)),
    ],
)
def test_a_light_it_cannot_set_is_refused(kwargs):
    with pytest.raises(StickDataError):
        stick_bed.lights_low(canvas(), None, **kwargs)
