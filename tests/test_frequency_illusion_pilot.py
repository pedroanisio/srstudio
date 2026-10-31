"""The pilot's script is checked, every claim is one the sources allow, and it stays outside the publishing path."""

from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import mind_kit, sketch, toon_cars
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import frequency_illusion_data as pilot  # noqa: E402

SCRIPTED = {name: sketch.events(pilot.SKETCH.beats, name)[0][0] for name in pilot.EVENTS}


def words() -> str:
    """Everything the reel says or shows, and its caption."""
    return " ".join(
        (
            *(q.text for q in pilot.LINES),
            pilot.NAME,
            pilot.STORY.who,
            pilot.STORY.year,
            pilot.STORY.what,
            pilot.STORY.result,
            *pilot.STORY_NOTE,
            pilot.ATTENTION,
            pilot.BIAS,
            pilot.POST.title,
            pilot.POST.description,
            pilot.POST.thumbnail.headline,
            pilot.POST.thumbnail.kicker,
        )
    )


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_name_dates_from_2005_and_no_word_says_2006():
    assert pilot.STORY.year == "2005"
    assert "Zwicky (2005)" in pilot.POST.description
    assert not re.search(r"(coined|named)[^.]*2006", words())


@pytest.mark.parametrize("name", ["baader", "meinhof", "red army", "terror"])
def test_the_older_name_is_nowhere_on_screen_or_in_the_voice(name):
    assert name not in words().lower()


def test_the_older_name_is_nowhere_in_the_source_of_the_reel():
    assert "baader" not in (PILOTS / "frequency_illusion_data.py").read_text(encoding="utf-8").lower()


def test_the_line_that_carries_the_point_is_the_sources_wording():
    assert "The name is recent. The attention research behind it isn't." in [q.text for q in pilot.LINES]


def test_the_reel_says_that_no_direct_test_was_found_not_that_none_exists():
    assert "We found no direct test of this one." in [q.text for q in pilot.LINES]


@pytest.mark.parametrize(
    "claim",
    [
        "no one has ever",
        "nobody has ever",
        "proven",
        "experiments show",
        "aren't more common",
        "no more common",
        "always there",
        "gorilla",
        "mullen",
        "forum",
    ],
)
def test_a_reel_never_says_what_the_sources_warn_against(claim):
    assert claim not in words().lower()


def test_the_evidence_card_says_what_it_is():
    assert "story" in pilot.STORY_NOTE[0] and "Not a study" in pilot.STORY_NOTE[1]
    assert "who named it" in pilot.STORY.who


def test_the_evidence_card_prints_no_number_the_post_did_not():
    card = " ".join((pilot.STORY.what, pilot.STORY.result, *pilot.STORY_NOTE))
    assert not re.search(r"\d", card)


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((13, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "ten" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "rare" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"story": "rare", "rare": "story"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_opens_on_the_behaviour_with_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_last_stroke_leaves_the_page_as_the_first_frame_starts():
    assert pilot.LAST_COUNT + 1 == pilot.FIRST_COUNT
    assert pilot.LINES[0].text == "That's eleven."
    assert pilot.LINES[-1].text == "That's ten."


def test_the_last_beat_holds_the_first_frames_pose():
    first, last = pilot.BEATS[0], pilot.BEATS[-1]
    assert (first.who, first.eyes, first.mouth, first.arms) == (last.who, last.eyes, last.mouth, last.arms)


@pytest.mark.parametrize(
    ("start", "end", "page"),
    [
        (0.0, 1.0, (pilot.FIRST_COUNT, (pilot.PEN_DOWN,))),
        (2.3, 4.4, (pilot.FIRST_COUNT + 1, ())),
        (6.3, 10.4, (pilot.FIRST_COUNT + 1, (SCRIPTED["twelve"] + pilot.PEN_DOWN,))),
        (11.8, 12.6, (pilot.FIRST_COUNT + 2, ())),
    ],
)
def test_the_count_on_the_pad_is_the_one_the_dog_says(start, end, page):
    assert pilot._page(sketch.Appearance("dog", start, end, []), SCRIPTED) == page


def test_the_last_shot_adds_the_tenth_stroke_and_the_one_before_it_none():
    before = sketch.Appearance("dog", SCRIPTED["friday"], SCRIPTED["friday"] + 2.0, [])
    last = sketch.Appearance("dog", SCRIPTED["ten"], pilot.END, [])
    assert pilot._page(before, SCRIPTED) == (pilot.LAST_COUNT, ())
    assert pilot._page(last, SCRIPTED) == (pilot.LAST_COUNT, (SCRIPTED["ten"] + pilot.PEN_DOWN,))


def test_every_stroke_the_stage_adds_fits_the_page():
    _, yellow, bus, fruit = pilot._parade(SCRIPTED)
    assert pilot.FIRST_COUNT + 2 + len(yellow) + 2 <= toon_cars.PAD_MOST
    assert fruit > bus


def test_no_two_things_are_under_the_lens_at_once():
    grey, yellow, bus, fruit = pilot._parade(SCRIPTED)
    times = sorted([*grey, *yellow, bus, fruit])
    assert min(b - a for a, b in zip(times, times[1:], strict=False)) >= pilot.PARADE_GAP


def test_the_parade_ends_with_the_shot():
    grey, yellow, bus, fruit = pilot._parade(SCRIPTED)
    assert max(*grey, *yellow, bus, fruit) < SCRIPTED["story"]


def test_nothing_on_the_road_carries_a_badge_or_a_name():
    text = (ROOT / "src" / "srstudio" / "toon_cars.py").read_text(encoding="utf-8")
    assert "cv.text" not in text


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert not list((ROOT / "episodes" / "posts").rglob(f"*{pilot.SLUG.replace('-', '_')}*"))
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def test_the_cast_is_the_approved_two_with_no_head_rig():
    assert set(pilot.VERSIONS) == {"toon-dog", "toon-frog"}
    assert "heads=" not in (PILOTS / "frequency_illusion.py").read_text(encoding="utf-8")


def test_the_recording_carries_the_banner():
    text = (PILOTS / "frequency_illusion_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
