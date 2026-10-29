"""Named styles: what they decide for an episode, what an episode may still override, and what they refuse."""

import json
from dataclasses import replace

import pytest

from srstudio import CAFE, CEL, CUTOUT, INK, LINEN, MONO, OFFICE, STYLES, EpisodeSpec, Style, StyleError, registry
from srstudio.cli import main
from srstudio.soundtrack import CAFE_MOUTH, INK_MOUTH, OFFICE_MOUTH


def spec(**kw):
    return EpisodeSpec(slug="t", title="t", description="t", root=kw.pop("root", "."), seed=1, **kw)


def test_cutout_is_the_default_and_decides_frame_font_mouth_and_stage():
    s = spec()
    assert s.style is CUTOUT and s.palette is OFFICE and s.background == OFFICE.background
    assert (s.width, s.height, s.fps, s.local_time) == (1080, 1920, 30, False)
    assert (s.dialogue, s.audio) == ("dialogue.json", "assets/dialogue.wav")
    assert (s.font, s.font_id, s.font_family, s.font_weight, s.font_style) == (
        "assets/DejaVuSans-Bold.ttf",
        "caption-font",
        "DejaVu Sans",
        "700",
        None,
    )
    assert s.mouth_style is OFFICE_MOUTH and s.namer is None and s.accessibility is None


def test_the_palette_picks_the_mouth_model_and_the_stage_colour():
    s = spec(palette=CAFE)
    assert s.mouth_style is CAFE_MOUTH and s.background == CAFE.background
    assert spec(palette="cafe").palette is CAFE


def test_ink_decides_the_square_sequence_and_its_own_id_scheme():
    s = spec(style=INK)
    assert s.palette is MONO and s.background == "#FFFFFF"
    assert (s.width, s.height, s.fps, s.local_time, s.dialogue, s.audio) == (
        1080,
        1080,
        24,
        True,
        "timeline.json",
        None,
    )
    assert (s.font_id, s.font_family, s.font_weight, s.font_style, s.font_policy) == (
        "hand",
        "Patrick Hand",
        "400",
        "normal",
        "pinned",
    )
    assert s.mouth_style is INK_MOUTH
    assert [s.namer("g"), s.namer("p")] == ["g1", "p2"]  # one shared counter per episode
    assert spec(style=INK).namer("g") == "g1"  # a fresh counter for the next episode
    assert s.accessibility == dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn", minTextSize="2%")


def test_an_explicit_field_wins_and_accessibility_merges_over_the_style():
    s = spec(
        style=INK,
        fps=30,
        audio="assets/mix.wav",
        font_credit="Someone",
        namer=None,
        local_time=False,
        accessibility=dict(description="d", minTextSize="3%"),
    )
    assert (s.fps, s.audio, s.font_credit, s.namer, s.local_time) == (30, "assets/mix.wav", "Someone", None, False)
    assert s.accessibility == dict(
        flashCheck="error", contrastCheck="warn", legibilityCheck="warn", minTextSize="3%", description="d"
    )


def test_cel_is_the_silent_style_and_a_silent_style_needs_no_mouth_model():
    s = spec(style=CEL)
    assert s.palette is LINEN and s.font is None and s.mouth_style is None and s.audio is None
    assert (s.width, s.height, s.fps, s.local_time, s.dialogue) == (1080, 1920, 24, False, "script.json")
    assert replace(CEL, palettes=(LINEN, MONO)).mouths == {}  # silent: no model per palette required
    with pytest.raises(StyleError, match="no mouth model"):
        replace(CEL, silent=False)
    assert list(STYLES) == ["cutout", "ink", "soft", "cel", "stick", "toon", "saga", "collage", "gloss"]


def test_a_palette_the_style_is_not_drawn_in_is_refused():
    with pytest.raises(StyleError, match="not drawn in palette 'mono'"):
        spec(palette=MONO)
    with pytest.raises(StyleError, match="not drawn in palette 'office'"):
        spec(style=INK, palette="office")
    with pytest.raises(StyleError, match="no mouth model"):
        replace(INK, palettes=(MONO, OFFICE))
    with pytest.raises(StyleError, match="no palette"):
        replace(INK, palettes=())


def test_a_new_style_is_a_value_built_from_an_existing_one():
    wide = replace(CUTOUT, slug="cutout-wide", name="Cutout wide", width=1920, height=1080)
    s = spec(style=wide, palette=CAFE)
    assert (s.width, s.height, s.mouth_style) == (1920, 1080, CAFE_MOUTH)
    assert isinstance(wide, Style) and wide.frame == "1920×1080 @ 30 fps"


def test_registry_entries_carry_the_style_of_their_module():
    styles = {e.name: e.style for e in registry.entries()}
    assert styles["manager"] == "cutout" and styles["office-wide"] == "cutout"
    assert styles["doodle"] == "ink" and styles["ink-wide"] == "ink"
    assert styles["signature-cactus"] == "" and styles["signature-code"] == ""  # shared by every style
    ink_names = {e.name for e in registry.entries(style="ink")}
    assert {"doodle", "talking-printer", "ink-wide", "signature-cactus"} <= ink_names and "manager" not in ink_names
    assert all(row["style"] in ("", "ink") for row in registry.catalog("ink"))


def test_cli_lists_styles_and_filters_the_catalog(capsys):
    assert main(["styles"]) == 0
    out = capsys.readouterr().out
    assert "Cutout" in out and "Ink" in out and "Cel" in out and "1080×1080 @ 24 fps" in out
    assert main(["styles", "--json"]) == 0
    facts = json.loads(capsys.readouterr().out)
    assert [f["slug"] for f in facts] == list(STYLES) and facts[1]["palettes"][0]["name"] == "mono"
    assert main(["catalog", "--style", "ink", "--kind", "character"]) == 0
    rows = capsys.readouterr().out.splitlines()
    assert rows and all(" ink " in r for r in rows) and not any(" manager " in r for r in rows)
