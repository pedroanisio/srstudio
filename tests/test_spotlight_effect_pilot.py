"""The pilot's script is checked, its figures are the sources', and it stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import mind_kit, sketch
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import spotlight_effect_data as pilot  # noqa: E402


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_figures_are_the_ones_the_paper_printed():
    assert pilot.GUESSED[1:] == (0.46, "46%")
    assert pilot.COULD[1:] == (0.23, "23%")
    assert pilot.GUESSED[1] == pytest.approx(2 * pilot.COULD[1])  # "exactly twice as high", which the card says
    assert "double" in pilot.STUDY.result


def test_the_figures_in_the_post_are_the_ones_on_the_card():
    for figure in (pilot.GUESSED[2], pilot.COULD[2]):
        assert figure in pilot.POST.description
    assert "Gilovich, Medvec & Savitsky (2000)" in pilot.POST.description


@pytest.mark.parametrize(
    "claim", ["Nobody noticed", "Nobody is looking", "far less", "a whole day", "stain", "haircut"]
)
def test_a_reel_never_says_what_the_sources_contradict(claim):
    words = " ".join((*(q.text for q in pilot.LINES), pilot.POST.title, pilot.POST.description)).lower()
    assert claim.lower() not in words


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((15, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "real" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "split" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"guess": "real", "real": "guess"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_opens_on_the_behaviour_with_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_end_cuts_back_to_the_first_words():
    assert pilot.LINES[0].text == pilot.LINES[-1].text == "One embarrassing shirt."


def test_the_name_is_spoken_once_and_the_card_holds_it():
    assert sum(pilot.NAME.lower() in q.text.lower() for q in pilot.LINES) == 1


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert (
        not list((ROOT / "episodes" / "releases").rglob(f"*{pilot.SLUG}*"))
        if (ROOT / "episodes" / "releases").is_dir()
        else True
    )
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)
