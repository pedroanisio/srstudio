import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, OFFICE, Canvas, registry
from srstudio.native import NativeError
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
    assert first == "url(#test-grad)" and cv.grad("test-grad", [(0, "#000000"), (1, "#FFFFFF")], (0, 0, 0, 1)) == first
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

    @register("prop", "unit_test_prop", summary="a test")
    def prop(cv, parent):
        return cv.group(parent, "unit-test-prop")

    assert registry.get("prop", "unit_test_prop").summary == "a test"
    assert prop(fresh(), fresh().comp).id == "unit-test-prop"
    with pytest.raises(KeyError):
        registry.get("prop", "missing")
    with pytest.raises(ValueError):
        register("gadget", "x")


def test_the_registry_holds_no_episodes_the_usage_report_measures_them():
    with pytest.raises(TypeError):
        register("prop", "unit_test_episodes", episodes=("t",))  # type: ignore[call-arg]
    assert all("episodes" not in row for row in registry.catalog())


def test_an_effect_is_defined_once_and_named_by_its_id():
    cv = fresh()
    first = cv.effect("soft", "blur", radius=6)
    assert first == "soft" and cv.effect("soft", "blur", radius=6) == first
    with pytest.raises(NativeError, match="already declared"):
        cv.effect("soft", "blur", radius=99)  # one name, one effect: other settings are refused
    cv.effect("lift", "drop-shadow", radius=10, offsetY=6, intensity=0.4)
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    effects = root.findall(".//effects/effect")
    assert [(e.get("id"), e.get("type"), e.get("radius")) for e in effects] == [
        ("soft", "blur", "6"),
        ("lift", "drop-shadow", "10"),
    ]
    with pytest.raises(ValueError, match="effect"):
        cv.effect(" ", "blur")


def test_a_radial_gradient_is_defined_once():
    cv = fresh()
    first = cv.rgrad("glow", [(0, "#FFFFFF"), (1, "#FFFFFF00")], (0.5, 0.3, 0.6))
    assert first == "url(#glow)" and cv.rgrad("glow", [(0, "#FFFFFF"), (1, "#FFFFFF00")], (0.5, 0.3, 0.6)) == first
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    (g,) = root.findall(".//radialGradient")
    assert (g.get("cx"), g.get("cy"), g.get("r"), len(g.findall("stop"))) == ("0.5", "0.3", "0.6", 2)


@pytest.mark.parametrize("spans", [[(1, 3), (2, 4)], [(2, 4), (1, 3)], [(1, 4), (2, 3)], [(1, 2), (2, 4)]])
def test_visibility_is_the_union_of_overlapping_nested_and_touching_spans(spans):
    cv = fresh()
    g = cv.group(cv.comp, "g")
    cv.gate(g, iter(spans))
    root = ET.fromstring(cv.scene.to_bytes())
    keys = [(float(k.get("time")), float(k.get("value"))) for k in root.findall(".//animate/key")]
    assert keys == [(0, 0), (1, 1), (4, 0)]


@pytest.mark.parametrize("spans", [[(2, 1)], [(-1, 1)], [(float("nan"), 1)], [(0, float("inf"))]])
def test_invalid_visibility_spans_are_rejected_without_adding_animation(spans):
    cv = fresh()
    g = cv.group(cv.comp, "g")
    with pytest.raises(ValueError, match="span"):
        cv.gate(g, spans)
    assert not any(n.xml_name == "animate" for n in g.iter())


@pytest.mark.parametrize("first,second", [("grad", "grad"), ("rgrad", "rgrad"), ("grad", "rgrad"), ("rgrad", "grad")])
def test_gradient_name_conflicts_are_rejected_without_changing_the_original(first, second):
    cv = fresh()
    stops = [(0, "#000000"), (1, "#FFFFFF")]
    getattr(cv, first)("paint", stops)
    original = cv.scene.to_bytes()
    with pytest.raises(NativeError, match="already declared"):
        getattr(cv, second)("paint", [(0, "#FF0000"), (1, "#FFFFFF")])
    assert cv.scene.to_bytes() == original


@pytest.mark.parametrize("kind,geometry", [("grad", (0, 0, 0, 1)), ("rgrad", (0.2, 0.3, 0.4))])
def test_gradient_geometry_conflicts_are_rejected(kind, geometry):
    cv = fresh()
    stops = [(0, "#000000"), (1, "#FFFFFF")]
    getattr(cv, kind)("paint", stops)
    with pytest.raises(NativeError, match="already declared"):
        getattr(cv, kind)("paint", stops, geometry)


@pytest.mark.parametrize("stick_first", [True, False])
def test_style_gradients_share_conflict_detection_with_canvas_gradients(stick_first):
    from srstudio import stick

    cv = fresh()
    gradient = stick.Gradient("paint", ((0, "#000000"), (1, "#FFFFFF")), 0, 0, 1, 1)
    declarations = [lambda: stick.paint(cv, gradient), lambda: cv.grad("paint", gradient.stops)]
    if not stick_first:
        declarations.reverse()
    declarations[0]()
    with pytest.raises(NativeError, match="already declared"):
        declarations[1]()
