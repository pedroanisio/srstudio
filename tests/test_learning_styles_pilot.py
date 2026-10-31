"""The pilot's script is checked, its wording stays inside its sources, and it stays outside the @tuxmeme publishing
path."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, mind_kit, sketch, toon_sketch
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import learning_styles_data as pilot  # noqa: E402

SHEET_WIDE, SHEET_TALL = 800.0, 960.0  # a quiz sheet's drawn size, in its own units


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def words_on_screen() -> str:
    """Every word the reel shows or says, and its caption."""
    return " ".join(
        (
            *(q.text for q in pilot.LINES),
            pilot.BELIEF,
            pilot.REVIEW.what,
            pilot.REVIEW.result,
            *pilot.CAVEAT,
            pilot.POST.title,
            pilot.POST.description,
        )
    )


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_card_quotes_the_abstract_and_keeps_its_scope():
    assert pilot.REVIEW.who.startswith("Pashler") and pilot.REVIEW.year == "2008"
    assert '"No adequate evidence base"' in pilot.REVIEW.result
    assert "general teaching" in pilot.REVIEW.result  # the abstract's limit: general educational practice


def test_the_caveat_stands_beside_the_verdict():
    caveat = " ".join(pilot.CAVEAT)
    assert caveat.startswith("Not disproved.")
    assert "2024 meta-analysis" in caveat and '"too small and too infrequent"' in caveat
    assert any(q.text.startswith("Not disproved") for q in pilot.LINES)


def test_the_survey_figure_is_always_about_educators():
    assert "89.1% of educators" in pilot.BELIEF
    assert "89.1% is among educators" in pilot.POST.description
    assert not any("89" in q.text for q in pilot.LINES)


def test_the_post_gives_the_meta_analysis_figure_of_its_abstract():
    assert "g = 0.31" in pilot.POST.description
    assert "Clinton-Lisell & Litzinger (2024)" in pilot.POST.description


def test_the_post_names_every_study_the_reel_leans_on():
    for source in ("Pashler et al. (2008)", "Knoll et al. (2017)", "Dunlosky et al. (2013)", "Newton & Salvi (2020)"):
        assert source in pilot.POST.description


@pytest.mark.parametrize(
    "claim",
    [
        "myth",
        "zero effect",
        "no effect",
        "debunk",
        "learners don't exist",
        "89% of people",
        "everyone",
        "proven false",
        "doesn't work",
        "15,000",
    ],
)
def test_a_reel_never_says_what_the_sources_rule_out(claim):
    assert claim.lower() not in words_on_screen().lower()


def test_disproved_appears_only_as_not_disproved():
    words = words_on_screen().lower()
    assert words.count("disproved") == words.count("not disproved") > 0


def test_expert_advice_is_not_shown_as_a_finding():
    assert "match the format" not in words_on_screen().lower()


def test_the_turn_is_the_technique_the_review_rates():
    assert "Test yourself instead of rereading." in (q.text for q in pilot.LINES)
    assert "Dunlosky et al. (2013)" in pilot.POST.description


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((13, bad)))


def test_an_unknown_caption_on_the_card_stops_the_build(monkeypatch):
    monkeypatch.setattr(pilot, "BELIEF", "Science proves everyone believed it.")
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate()


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "verdict" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "shelf" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"felt": "recalled", "recalled": "felt"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_opens_on_the_behaviour_with_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_first_exchange_comes_back_at_the_end_and_means_something_else():
    texts = [q.text for q in pilot.LINES]
    assert texts[2:4] == ["What's it say?", "It's important."] == [texts[-3], texts[-1]]
    assert texts[-2] == " ".join(pilot.ANSWER)  # this time she has the answer, shut book and all


def test_the_name_is_spoken_once_and_the_card_holds_it():
    assert sum(pilot.NAME.lower() in q.text.lower() for q in pilot.LINES) == 1


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    releases = ROOT / "episodes" / "releases"
    assert not releases.is_dir() or not list(releases.rglob(f"*{pilot.SLUG}*"))
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def scene_of(app: sketch.Appearance) -> ET.Element:
    """The shot as the pilot dresses it, the character's own drawing left out."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    back, light, front = (cv.group(cv.comp, name) for name in ("back", "light", "front"))
    measure = lambda text, size: 0.5 * size * len(text)  # noqa: E731
    pilot.dress(toon_sketch.Shot(cv, app, back, front, sk.beats, sk.end, measure, light, pilot.VERSIONS))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def appearance(event: str) -> sketch.Appearance:
    at = sketch.events(pilot.BEATS, event)[0][0]
    return next(a for a in sketch.appearances(pilot.BEATS, pilot.END) if a.start <= at < a.end)


def test_the_push_moves_the_sheet_and_leaves_the_signature_marks_where_they_are(monkeypatch):
    def sign(cv, parent):
        cv.group(parent, "the-marks")

    monkeypatch.setattr(pilot.mind_kit, "sign", sign)
    root = scene_of(appearance("quiz"))
    parents = {child: node for node in root.iter() for child in node}
    pushed = [n for n in root.iter("group") if any(k.tag == "animate" and "scale" in str(k.attrib) for k in n)]
    assert pushed  # the push is there

    marks = next(n for n in root.iter("group") if n.get("id") == "the-marks")
    while marks in parents:
        marks = parents[marks]
        assert marks not in pushed


def rectangle(at: tuple[float, float]) -> tuple[float, float, float, float]:
    half_wide, half_tall = pilot.LAND_SCALE * SHEET_WIDE / 2, pilot.LAND_SCALE * SHEET_TALL / 2
    return at[0] - half_wide, at[1] - half_tall, at[0] + half_wide, at[1] + half_tall


def test_no_sheet_lands_on_another_ones_words():
    sheets = [rectangle(at) for at, _ in pilot.LANDED]
    assert len(sheets) == 4
    for k, (left, top, right, bottom) in enumerate(sheets):
        for other_left, other_top, other_right, other_bottom in sheets[k + 1 :]:
            assert right <= other_left or other_right <= left or bottom <= other_top or other_bottom <= top


def test_the_cover_shows_the_open_book():
    assert pilot.POST.thumbnail.at < sketch.events(pilot.SKETCH.beats, "shut")[0][0]
