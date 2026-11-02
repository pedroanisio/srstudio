"""The look primitives every style shares (srstudio.look): measured text, a shot grade, a far plane out of focus,
pools of light and fades."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import VOID, Canvas, flat_counter, fonts, look, shared_counter
from srstudio.sample import SYSTEM_FONTS

FONT_FILE = next((f for f in SYSTEM_FONTS if f.exists()), None)
needs_font = pytest.mark.skipif(FONT_FILE is None, reason="DejaVu Sans Bold is required")


def font() -> bytes:
    assert FONT_FILE is not None
    return FONT_FILE.read_bytes()


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2.0, background=VOID.background)
    cv = Canvas(scene, VOID, font_asset="f", namer=flat_counter("s"))
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def effects_of(root: ET.Element, node_id: str) -> dict[str, ET.Element]:
    declared = {e.get("id"): e for e in root.iter("effect")}
    node = next(n for n in root.iter() if n.get("id") == node_id)
    return {i: declared[i] for i in (node.get("effects") or "").split()}


def stops(root: ET.Element, paint_id: str) -> list[str]:
    grad = next(g for g in root.iter() if g.get("id") == paint_id)
    return [s.get("color") for s in grad.iter("stop")]


# -- wrap -------------------------------------------------------------------------------------------------------------
@needs_font
def test_wrap_breaks_text_into_lines_the_font_draws_within_the_width():
    text = "the reactor is fine and so is the coffee machine on deck four"
    lines = look.wrap(font(), text, 40, 400, 6)
    assert len(lines) > 1
    assert " ".join(lines) == text
    assert all(fonts.text_width(font(), line, 40) <= 400 for line in lines)


@needs_font
def test_wrap_keeps_phrases_together_on_request_and_greedy_by_default():
    text = "Leave him and open a candle shop today"
    width = fonts.text_width(font(), "Leave him and open a", 40) + 1
    assert look.wrap(font(), text, 40, width, 3) == ["Leave him and open a", "candle shop today"]
    kept = look.wrap(font(), text, 40, width, 3, keep_together=True)
    assert kept == ["Leave him and open", "a candle shop today"]
    assert all(fonts.text_width(font(), line, 40) <= width for line in kept)
    assert look.wrap(font(), "Leave him and\nopen a", 40, width, 3, keep_together=True) == ["Leave him and", "open a"]


@needs_font
def test_wrap_keeps_explicit_newlines():
    assert look.wrap(font(), "one\ntwo", 40, 900, 3) == ["one", "two"]


@needs_font
@pytest.mark.parametrize(
    "text, max_lines, message",
    [
        ("supercalifragilisticexpialidocious", 3, "wider than"),
        ("a supercalifragilisticexpialidocious", 3, "wider than"),
        ("one\ntwo\nthree", 2, "needs 3 lines"),
    ],
)
def test_wrap_refuses_a_word_too_wide_or_more_lines_than_the_box_holds(text, max_lines, message):
    with pytest.raises(look.FitError, match=message):
        look.wrap(font(), text, 60, 200, max_lines)


def test_a_fit_error_is_a_value_error_so_a_style_can_rename_it():
    assert issubclass(look.FitError, ValueError)


def test_label_is_a_text_layer_in_the_box():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    node = look.label(cv, g, "Hello", 10, 20, 300, 60, 40, "#ffffff", align="start")
    assert node.xml_name == "layer"
    assert node.asset is not None


# -- grade and depth --------------------------------------------------------------------------------------------------
def test_grade_applies_each_effect_under_the_styles_prefix():
    cv = canvas()
    g = cv.group(cv.comp, "shot")
    grade = {"bloom": dict(threshold=0.9, radius=28, intensity=0.5), "film-grain": dict(amount=0.05, size=1.2)}
    assert look.grade(cv, g, "demo", grade) is g
    applied = effects_of(tree(cv), "shot")
    assert {i: e.get("type") for i, e in applied.items()} == {"demo-bloom": "bloom", "demo-film-grain": "film-grain"}
    assert applied["demo-bloom"].get("threshold") == "0.9"


def test_grade_refuses_an_empty_grade():
    cv = canvas()
    with pytest.raises(ValueError, match="at least one effect"):
        look.grade(cv, cv.group(cv.comp, "shot"), "demo", {})


def test_depth_is_a_blurred_group_inside_the_parent():
    cv = canvas()
    g = cv.group(cv.comp, "set")
    far = look.depth(cv, g, "demo-depth", 3.0)
    root = tree(cv)
    applied = effects_of(root, far.id)
    assert [e.get("type") for e in applied.values()] == ["blur"]
    assert applied["demo-depth"].get("radius") == "3"
    parent = next(n for n in root.iter() if n.get("id") == "set")
    assert any(c.get("id") == far.id for c in parent)


@pytest.mark.parametrize("radius", [0.0, -1.0, float("nan")])
def test_depth_refuses_a_radius_that_is_not_positive(radius):
    cv = canvas()
    with pytest.raises(ValueError, match="positive"):
        look.depth(cv, cv.group(cv.comp, "set"), "demo-depth", radius)


# -- light ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("colour", ["#ffc870", "#ffc870cc"])
def test_a_pool_of_light_fades_from_its_colour_to_nothing(colour):
    cv = canvas()
    node = look.pool(cv, cv.group(cv.comp, "g"), "demo-pool", colour, 40, 1000, 1000, 260, opacity=0.3)
    root = tree(cv)
    assert stops(root, "demo-pool") == [colour, "#ffc87000"]
    assert node.opacity == pytest.approx(0.3)


def test_a_fade_runs_from_its_colour_at_y0_to_nothing_at_y1_either_way_up():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    down = look.fade(cv, g, "demo-haze", "#3a1f5c80", 100, 400, width=1080)
    up = look.fade(cv, g, "demo-shade", "#3a1f5c", 1900, 1500, width=1080)
    root = tree(cv)
    assert stops(root, "demo-haze") == ["#3a1f5c80", "#3a1f5c00"]
    assert stops(root, "demo-shade") == ["#3a1f5c00", "#3a1f5c"]
    assert (down.y, down.height) == (100, 300)
    assert (up.y, up.height) == (1500, 400)


# -- a text set in its own asset ---------------------------------------------------------------------------------------
def counted() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2.0, background=VOID.background)
    cv = Canvas(scene, VOID, font_asset="f", namer=shared_counter())
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv


def text_asset(cv: Canvas, name: str) -> dict[str, str]:
    return dict(next(t for t in tree(cv).iter("text") if t.get("id") == name).attrib)


def test_text_sets_one_line_in_its_box_and_shows_it_in_a_layer_of_its_own():
    cv = counted()
    layer = look.text(cv, cv.comp, "BAGGING AREA", 10, 20, 300, 44, 24, "#ffffff")
    assert text_asset(cv, "text1") == dict(
        id="text1", text="BAGGING AREA", width="300", height="44", size="24", color="#ffffff", align="center",
        verticalAlign="middle", wrap="none", fontAsset="f",
    )  # fmt: skip
    shown = next(e for e in tree(cv).iter("layer") if e.get("asset") == "text1")
    assert (shown.get("id"), shown.get("x"), shown.get("y")) == ("layer2", "10", "20") and layer is not None


def test_text_lines_balance_a_text_over_at_most_that_many_lines():
    cv = counted()
    look.text(cv, cv.comp, "a", 0, 0, 10, 10, 12, "#000000", lines=1)
    look.text(cv, cv.comp, "a b", 0, 0, 10, 10, 12, "#000000", lines=2)
    assert (text_asset(cv, "text1")["wrap"], text_asset(cv, "text1")["maxLines"]) == ("none", "1")
    assert (text_asset(cv, "text3")["wrap"], text_asset(cv, "text3")["maxLines"]) == ("balance", "2")


def test_text_passes_weight_alignment_line_height_overflow_wrap_and_its_id_prefixes():
    cv = counted()
    look.text(
        cv, cv.comp, "Mon", 0, 0, 10, 10, 12, "#000000", weight=700, align="start", line_height="1.15",
        overflow="ellipsis", wrap="word", asset="txt", layer="label",
    )  # fmt: skip
    attrs = text_asset(cv, "txt1")
    assert {k: attrs[k] for k in ("weight", "align", "lineHeight", "overflow", "wrap")} == dict(
        weight="700", align="start", lineHeight="1.15", overflow="ellipsis", wrap="word"
    )
    assert next(e for e in tree(cv).iter("layer") if e.get("asset") == "txt1").get("id") == "label2"
