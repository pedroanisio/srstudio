"""Cast cards: typed data, refusals, layout from measured text, and the safe zone read off real engine renders."""

import os
from pathlib import Path

import pytest

from srstudio import cast_card, fonts, parts
from srstudio.cast_card import (
    CAST,
    HEIGHT,
    SAFE_BOTTOM,
    SAFE_TOP,
    WIDTH,
    Card,
    CastCardError,
    Frame,
    Lettering,
    Pose,
    compose,
    contrast,
    layout,
    render,
)
from srstudio.cli import main
from srstudio.sample import SYSTEM_FONTS

FIXTURE = next(f for f in SYSTEM_FONTS if f.exists()).read_bytes()  # a fixture for measuring, never a card's face
FACES = Lettering(FIXTURE, FIXTURE)
GOOD = Card(
    "Rex", "Has never heard of it.", "toon-dog", Pose("wide", "grin", "desk"), Frame((540, 900), 1.5), "#F2C14E"
)


def lettering() -> Lettering:
    folder = os.environ.get("SRSTUDIO_FONTS")
    if not folder or not (Path(folder) / "fonts.lock.json").exists():
        pytest.skip("needs SRSTUDIO_FONTS with the pinned Google Fonts")
    return Lettering.installed(folder)


def edited(**changes) -> Card:
    fields = dict(name=GOOD.name, line=GOOD.line, drawing=GOOD.drawing, pose=GOOD.pose, frame=GOOD.frame,
                  backdrop=GOOD.backdrop)  # fmt: skip
    return Card(**(fields | changes))


def test_a_good_card_has_no_problems():
    assert GOOD.problems() == []
    assert GOOD.validate() is GOOD
    assert GOOD.slug == "rex"


@pytest.mark.parametrize(
    "card, needle",
    [
        (edited(drawing="toon-nobody"), "toon-nobody"),
        (edited(drawing=""), "no part"),
        (edited(drawing="toon-desk"), "not a character"),
        (edited(drawing="saga-gloom"), "no card pose"),
        (edited(name=""), "name"),
        (edited(name="Rex the\nDog"), "name"),
        (edited(name="@rex"), "name"),
        (edited(line=""), "line"),
        (edited(line="two\nlines"), "line"),
        (edited(backdrop="yellow"), "backdrop"),
        (edited(pose=Pose("nonsense", "grin", "desk")), "eyes"),
        (edited(pose=Pose("wide", "nonsense", "desk")), "mouth"),
        (edited(pose=Pose("wide", "grin", "nonsense")), "arms"),
        (edited(frame=Frame((540, 900), 0)), "zoom"),
        (edited(frame=Frame((float("nan"), 900), 1)), "focus"),
    ],
)
def test_bad_cards_are_refused(card, needle):
    assert any(needle in problem for problem in card.problems())
    with pytest.raises(CastCardError, match=needle):
        card.validate()


@pytest.mark.parametrize(
    "line",
    [
        "Follow for more",
        "follow us",
        "Tag a friend who does this",
        "Comment below",
        "Share this with Rex",
        "Link in bio",
        "Like and subscribe",
        "Double tap if you agree",
        "Swipe up",
        "Save this for later",
        "DM me",
        "Say hi to @okayville.tv",
        "#relatable",
        "Seen on @tuxmeme",
        "tuxmeme forever",
    ],
)
def test_engagement_bait_and_handles_are_refused(line):
    assert any("bait" in problem for problem in edited(line=line).problems())


@pytest.mark.parametrize("line", ["Likes the lid.", "Treats it like family.", "Never shares the fries.", "A followup."])
def test_ordinary_words_are_not_bait(line):
    assert edited(line=line).problems() == []


def test_a_proposed_version_is_never_drawn(monkeypatch):
    real = parts.get("toon-dog")

    def nothing_approved():
        raise parts.NotApprovedError("no approved version")

    monkeypatch.setattr(real.__class__, "latest", lambda self: nothing_approved())
    assert any("approved" in problem for problem in GOOD.problems())


def test_every_cast_member_is_valid_and_named_once():
    assert {"rex", "fern", "ava", "milo"} <= {card.slug for card in CAST}
    assert len({card.slug for card in CAST}) == len(CAST)
    assert len({card.drawing for card in CAST}) == len(CAST)
    for card in CAST:
        card.validate()


@pytest.mark.parametrize("drawing", ["toon-bento", "gloss-sunny", "saga-gloom", "toon-fox"])
def test_the_cast_keeps_out_who_it_should(drawing):
    assert drawing not in {card.drawing for card in CAST}


def test_the_faces_are_google_fonts_and_not_dejavu():
    assert cast_card.DISPLAY_FONT == fonts.GoogleFont("Fredoka", 600)
    assert cast_card.TEXT_FONT == fonts.GoogleFont("DM Sans", 700)


def test_every_box_sits_in_the_safe_zone_for_the_longest_line():
    lay = layout(edited(line="word " * 5 + "end"), FACES)
    for x, y, w, h in (lay.name, *lay.lines, lay.wordmark):
        assert SAFE_TOP <= y and y + h <= SAFE_BOTTOM
        assert cast_card.MARGIN <= x and x + w <= WIDTH - cast_card.MARGIN
    assert lay.name[1] + lay.name[3] <= lay.lines[0][1]
    assert lay.lines[-1][1] + lay.lines[-1][3] <= lay.wordmark[1]


def test_a_line_that_does_not_fit_is_refused_by_measure():
    with pytest.raises(CastCardError, match="does not fit"):
        layout(edited(line="word " * 40), FACES)
    with pytest.raises(CastCardError, match="wider than"):
        layout(edited(line="W" * 60), FACES)
    with pytest.raises(CastCardError, match="name"):
        layout(edited(name="W" * 30), FACES)


def test_a_short_line_stays_on_one_line_and_a_long_one_breaks_evenly():
    assert layout(edited(line="Short."), FACES).text == ("Short.",)
    first, second = layout(edited(line="one two three four five six seven eight"), FACES).text
    assert abs(len(first) - len(second)) < 12


def test_the_lettering_is_legible_on_the_panel():
    assert contrast(cast_card.LETTER, cast_card.PANEL) >= 7
    assert contrast(cast_card.WORDMARK_COLOUR, cast_card.PANEL) >= 7


@pytest.mark.parametrize("a, b, ratio", [("#000000", "#ffffff", 21.0), ("#777777", "#777777", 1.0)])
def test_contrast_is_the_wcag_ratio(a, b, ratio):
    assert contrast(a, b) == pytest.approx(ratio)


def test_the_document_is_a_card_sized_project_with_the_wordmark_and_no_handle():
    xml = compose(GOOD, FACES).to_bytes().decode()
    assert f'width="{WIDTH}"' in xml and f'height="{HEIGHT}"' in xml
    assert 'text="Okayville"' in xml and 'text="Rex"' in xml
    assert "tuxmeme" not in xml


def test_the_wordmark_is_one_look_on_every_card():
    a, b = (layout(card, FACES) for card in (GOOD, edited(name="Fern", line="word " * 5 + "end")))
    assert a.wordmark == b.wordmark


@pytest.fixture(scope="module")
def faces():
    return lettering()


@pytest.mark.parametrize("card", CAST, ids=lambda card: card.slug)
def test_each_card_renders_inside_the_safe_zone_with_a_big_character(card, faces, tmp_path, scene_render):
    measure = cast_card.measure(card, faces, scene_render, tmp_path)
    x0, y0, x1, y1 = measure.letters
    assert SAFE_TOP <= y0 and y1 <= SAFE_BOTTOM, measure
    assert cast_card.MARGIN <= x0 and x1 <= WIDTH - cast_card.MARGIN, measure
    assert measure.figure[1] >= SAFE_TOP, measure
    assert measure.fill >= cast_card.MIN_FILL, measure


def test_render_writes_a_private_png_at_story_size(faces, tmp_path, scene_render):
    out = render(CAST[0], tmp_path / "cards" / "rex.png", faces, scene_render)
    assert out.read_bytes().startswith(b"\x89PNG")
    assert out.stat().st_mode & 0o777 == 0o600
    assert out.parent.stat().st_mode & 0o777 == 0o700
    assert sorted(p.name for p in out.parent.iterdir()) == ["rex.png"]  # the work folder is gone
    width, height = int.from_bytes(out.read_bytes()[16:20], "big"), int.from_bytes(out.read_bytes()[20:24], "big")
    assert (width, height) == (WIDTH, HEIGHT)


def test_a_card_that_breaks_the_safe_zone_writes_nothing(faces, tmp_path, scene_render):
    high = edited(frame=Frame((540, 1400), 1.5))  # the top of the head lands above the safe zone
    with pytest.raises(CastCardError, match="safe zone|small"):
        render(high, tmp_path / "rex.png", faces, scene_render)
    assert not (tmp_path / "rex.png").exists()


def test_render_all_refuses_an_unknown_name_and_writes_only_those_asked(faces, tmp_path, scene_render):
    with pytest.raises(CastCardError, match="no card for nobody"):
        cast_card.render_all(tmp_path, faces, scene_render, frozenset({"nobody"}))
    assert [p.name for p in cast_card.render_all(tmp_path, faces, scene_render, frozenset({"rex"}))] == ["rex.png"]


def test_the_cards_command_writes_a_card_and_reports_a_refusal(tmp_path, scene_render, capsys, faces):
    folder = os.environ["SRSTUDIO_FONTS"]
    common = ["cards", str(tmp_path), "--fonts", folder, "--engine", str(scene_render)]
    assert main([*common, "--only", "kai"]) == 0
    assert (tmp_path / "kai.png").exists() and "kai.png" in capsys.readouterr().out
    assert main([*common, "--only", "nobody"]) == 1
    assert "no card for nobody" in capsys.readouterr().err


def test_the_cards_command_asks_for_what_it_lacks(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SRSTUDIO_FONTS", raising=False)
    assert main(["cards", str(tmp_path)]) == 2
    assert "--fonts" in capsys.readouterr().err


def test_a_failing_engine_raises_and_writes_nothing(faces, tmp_path):
    fake = tmp_path / "engine"
    fake.write_text("#!/bin/sh\nexit 3\n")
    fake.chmod(0o700)
    with pytest.raises(CastCardError, match="engine"):
        render(CAST[0], tmp_path / "rex.png", faces, fake)
    assert not (tmp_path / "rex.png").exists()
