import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, OFFICE, Canvas, registry
from srstudio.registry import register


def fresh():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=3)
    return Canvas(scene, OFFICE)


def test_gate_and_keys_are_sorted_hold_keys():
    cv = fresh()
    g = cv.group(cv.comp, "g")
    cv.gate(g, [(2.0, 3.0), (0.5, 1.0)])
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    anim = root.find(".//group[@id='g']/animate")
    keys = [(float(k.get("time")), float(k.get("value"))) for k in anim.findall("key")]
    assert keys == [(0, 0), (0.5, 1), (1.0, 0), (2.0, 1), (3.0, 0)]
    assert anim.get("defaultInterpolation") == "hold"


def test_path_defaults_and_gradient_cache():
    cv = fresh()
    p = cv.path(cv.comp, "M0 0 L10 10")
    assert p.stroke == OFFICE.ink and p.fill == OFFICE.clear and p.strokeCap == "round"
    first = cv.grad("test-grad", [(0, "#000000"), (1, "#FFFFFF")], (0, 0, 0, 1))
    assert first == "url(#test-grad)" and cv.grad("test-grad", [], (0, 0, 0, 1)) == first
    assert CAFE.ink != OFFICE.ink


def test_registry_lists_the_shipped_parts_and_new_ones():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {
        ("character", "manager"),
        ("character", "barista"),
        ("location", "cafe"),
        ("prop", "silent-phone"),
        ("graphic", "scorecard"),
    } <= names

    @register("prop", "unit_test_prop", summary="a test", episodes=("t",))
    def prop(cv, parent):
        return cv.group(parent, "unit-test-prop")

    assert registry.get("prop", "unit_test_prop").summary == "a test"
    assert prop(fresh(), fresh().comp).id == "unit-test-prop"
    with pytest.raises(KeyError):
        registry.get("prop", "missing")
    with pytest.raises(ValueError):
        register("gadget", "x")
