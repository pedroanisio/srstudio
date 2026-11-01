"""There's a Name for That #3 and #4: the scripts are checked, each claim is the one its sources allow, and both stay
outside the publishing path."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import mind_kit, sketch, toon, toon_everyday

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import above_average_data as above  # noqa: E402
import explain_a_zipper_data as zipper  # noqa: E402

BOTH = (above, zipper)
each = pytest.mark.parametrize("pilot", BOTH, ids=[pilot.SLUG for pilot in BOTH])


def sources(pilot) -> str:
    return (ROOT / "pilots" / "mind" / pilot.SLUG / "sources.md").read_text(encoding="utf-8")


def said(pilot) -> str:
    return " ".join(q.text for q in pilot.LINES)


@each
def test_the_pilot_as_written_is_valid(pilot):
    pilot.validate()


@each
def test_the_series_number_is_in_the_title_the_cover_and_the_caption(pilot):
    assert pilot.SERIES in pilot.TITLE
    assert pilot.POST.thumbnail.kicker == pilot.SERIES
    assert pilot.POST.description.startswith(pilot.SERIES)


def test_the_numbers_follow_the_first_two():
    assert above.SERIES.endswith("#3") and zipper.SERIES.endswith("#4")


@each
def test_the_claim_is_spoken_first_and_the_reel_keeps_its_length(pilot):
    assert pilot.BEATS[0].start == 0.0 and pilot.LINES[pilot.BEATS[0].line].text == pilot.HOOK
    assert 20.0 <= pilot.END <= 30.0


@each
def test_the_caption_opens_on_a_question_and_keeps_to_five_hashtags(pilot):
    assert pilot.POST.title.endswith("?")
    assert len(pilot.POST.hashtags) <= 5


@each
def test_a_line_the_channel_keeps_off_screen_stops_the_build(pilot):
    lines = (replace(pilot.LINES[0], text="Science proves it."), *pilot.LINES[1:])
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(replace(pilot.SKETCH, lines=lines))


@each
def test_a_lost_event_and_a_lost_opening_stop_the_build(pilot):
    event = pilot.EVENTS[0]
    beats = tuple(replace(b, event="") if b.event == event else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=pilot.BEATS[1:]))


@each
def test_events_out_of_order_stop_the_build(pilot):
    first, second = pilot.EVENTS[:2]
    swap = {first: second, second: first}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_above_average_says_only_what_the_sources_print():
    text = sources(above)
    assert "34 of the drivers in the accident group were responsible" in text
    assert above.CITE_CRASH == "Preston & Harris, 1965, in Svenson, 1981"
    assert "Svenson" in above.POST.description
    assert " ".join(above.STAMP) == "93% of US students above the median."


def test_above_average_never_says_all_of_them():
    assert "all of them" not in said(above).lower()


def test_the_lines_are_american():
    assert above.LAST == "The tree didn't signal."
    assert "hospitalized by a crash" in said(above)
    assert "in the hospital" not in said(above)  # the sources give the injury, not where they were asked
    assert "indicating" not in said(above)


def test_explain_a_zipper_quotes_the_papers_own_sentence():
    text = sources(zipper)
    assert "Nearly all participants showed drops in estimates of what they knew" in text
    assert "Sixteen graduate students" in text
    assert zipper.DOWN == "Nearly all of them marked themselves down."
    assert " ".join(zipper.STAMP) == "Nearly all of 16 students marked themselves down."


def test_the_caption_says_where_the_effect_stops():
    assert "procedures, stories and facts" in zipper.POST.description


def test_the_scores_on_the_board_are_owned_up_to_as_ours():
    assert "The scores on the board are ours." in zipper.POST.description


@each
def test_a_pilot_has_no_release_and_no_post(pilot):
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert not list((ROOT / "episodes" / "posts").rglob(f"*{pilot.SLUG.replace('-', '_')}*"))
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


@each
def test_no_hearing_was_written(pilot):
    assert all(not q.heard for q in pilot.LINES)


@each
def test_each_foley_lands_and_no_clip_is_missing(pilot, tmp_path):
    rows = pilot.foley(pilot.BEATS, pilot.END, [], tmp_path, pilot.SEED)
    assert rows
    assert all((tmp_path / "audio" / f"{row['id']}.wav").exists() for row in rows)


def test_the_clipboard_stops_below_the_rabbits_open_mouth():
    top = above.BOARD_AT[1] - toon_everyday.CLIP_TOP * above.BOARD_SCALE
    assert toon.fy(top) >= above.MOUTH_FOOT


def test_the_clipboard_stays_blank_until_he_has_answered_and_blank_when_she_asks_again():
    at = {"swerve": 5.7, "ward": 12.9}
    assert above.answer(3.0, at) == ""
    assert above.answer(6.5, at) == "Top 10%"
    assert above.answer(18.0, at) == ""


@each
def test_the_blurred_far_plane_reaches_the_frame_edge(pilot):
    assert pilot.BLEED is True

