"""The batch's three real roasts: the facts are the sources', the joke comes after them, the source stays on screen, and
a script fits its reel before a take is paid for."""

from __future__ import annotations

import importlib
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, craft, facts, news_inked, news_kit, scripting
from srstudio.news_kit import NewsKitError
from srstudio.sketch import Line, SketchError

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import news_story  # noqa: E402
import safe_from_you_data  # noqa: E402
import seabird_jet_lag_data  # noqa: E402
import space_haiku_data  # noqa: E402
import they_voted_no_data  # noqa: E402

REELS = (seabird_jet_lag_data, space_haiku_data, safe_from_you_data, they_voted_no_data)
TAGGED = (safe_from_you_data, they_voted_no_data)  # reels older than the rule keep the picture they were approved with
RUNS_LONG = {they_voted_no_data: 34.0}  # the reviewer kept every line: 79 words, and the master runs 30.4 s
PHONES = (  # what fills the frame
    "news-phone",
    "news-veer",
    "news-lost",
    "news-money-app",
    "news-money-app-again",
    "news-oven-clock",
)
reel = pytest.mark.parametrize("pilot", REELS, ids=lambda m: m.SLUG)


def folder(pilot) -> Path:
    return ROOT / "pilots" / "news" / pilot.SLUG


def sources(pilot) -> str:
    return (folder(pilot) / "sources.md").read_text(encoding="utf-8")


def shown(pilot) -> tuple[str, ...]:
    return (*pilot.TICKER, *(w for row in pilot.LOWERS for w in row[1:]))


def overlay(pilot) -> dict[str, ET.Element]:
    """The groups the reel draws over its picture, by id."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
    pilot.overlay(cv, cv.comp, sk.beats, sk.end, lambda text, size: 0.42 * size * len(text))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def frontmatter(pilot, name: str = "notes.md") -> dict[str, str]:
    head = (folder(pilot) / name).read_text(encoding="utf-8").split("---")[1]
    return {k.strip(): v.strip() for k, v in (row.split(":", 1) for row in head.strip().splitlines())}


def pilot_inserts(pilot) -> tuple[tuple[float, float], ...]:
    """When the reel's phone or stove is up, read off what it draws."""
    groups = overlay(pilot)
    return tuple(
        (float(groups[name].get("start", "0")), float(groups[name].get("end", "0")))
        for name in PHONES
        if name in groups
    )


def groups_of(pilot, prefix: str) -> list[ET.Element]:
    return [g for name, g in overlay(pilot).items() if name.startswith(prefix)]


@reel
def test_the_reel_as_written_is_valid(pilot):
    pilot.validate()


@reel
def test_the_script_fits_a_thirty_second_reel(pilot):
    assert scripting.over_budget(pilot.LINES, RUNS_LONG.get(pilot, 30.0)) == 0
    assert pilot.SKETCH.end <= 35.0


def test_seabird_was_cut_to_the_length_the_review_asked_for():
    assert scripting.word_count(seabird_jet_lag_data.LINES) <= 68


@reel
def test_the_story_is_from_the_last_48_hours_of_the_day_it_was_picked(pilot):
    picked = date.fromisoformat(frontmatter(pilot)["date"])
    assert picked - timedelta(days=2) <= date.fromisoformat(pilot.STORY_DATE) <= picked
    assert frontmatter(pilot)["story-date"] == pilot.STORY_DATE


@reel
def test_the_card_shows_the_outlets_own_headline_word_for_word(pilot):
    text = sources(pilot)
    assert f'"{pilot.SOURCE.headline}"' in text and pilot.SOURCE.outlet in text


@reel
def test_at_least_two_independent_hosts_are_linked(pilot):
    assert len(set(re.findall(r"<https://([^/]+)/", sources(pilot)))) >= 2


@reel
def test_every_number_spoken_or_shown_is_in_the_sources(pilot):
    assert facts.unsourced((*(q.text for q in pilot.LINES), *shown(pilot)), sources(pilot)) == []


def test_seabird_keeps_the_maximum_and_records_what_the_seven_measures():
    text = sources(seabird_jet_lag_data)
    assert "approximately 15°" in text and "average compass error of 7°" in text
    assert "up to fifteen degrees" in seabird_jet_lag_data.LINES[2].text


def test_seabird_has_the_callback_and_the_wife_payoff():
    lines = [q.text for q in seabird_jet_lag_data.LINES]
    assert lines[5].startswith("Never ask") and lines[7] == "See? Never ask!"
    assert "your wife called" in lines[8] and lines[-1] == "Which way is that?"


def test_seabird_opens_on_a_statement_and_not_a_question():
    assert seabird_jet_lag_data.LINES[0].text == "Seabirds get jet lag."


def test_the_haiku_is_the_satellites_word_for_word():
    assert space_haiku_data.LINES[2].text == (
        "Blue marble below. Data streams in silent grace. Starlight feeds my core."
    )
    text = sources(space_haiku_data)
    assert all(row in text for row in ("Blue marble below", "Data streams in silent grace", "Starlight feeds my core"))


def test_the_twenty_minutes_is_credited_to_techcrunch_alone():
    assert "comes from TechCrunch alone" in sources(space_haiku_data)


def test_gus_is_in_tears_from_the_first_frame():
    assert space_haiku_data.ACTS[0].gus.eyes == "weep"


def test_the_haiku_gets_one_chime_a_line_both_times():
    assert len(space_haiku_data.chimes(space_haiku_data.BEATS)) == 6


def test_the_sign_off_ends_on_the_anchor_credited_for_it():
    assert space_haiku_data.LOWERS[-1][1:] == ("HAIKU BY", "VERA STILLMAN, ANCHOR")
    assert space_haiku_data.BEATS[-1].who == "vera"


def test_binance_is_quoted_in_the_words_read_and_its_position_stays_on_screen():
    assert '"Your assets are safe."' in safe_from_you_data.LINES[3].text
    assert "Your assets are safe." in sources(safe_from_you_data)
    assert any("WILL NOT BE PASSED ON TO USERS" in item for item in safe_from_you_data.TICKER)


def test_safe_from_you_ends_on_one_word_after_the_longest_held_stare():
    pilot = safe_from_you_data
    assert pilot.LINES[-1].text == "You." and pilot.BEATS[-1].who == "vera"
    stare = pilot.BEATS[-2]
    assert stare.line is None and pilot.BEATS[-1].start - stare.start >= 1.2


def test_the_vote_is_read_before_the_oven_and_the_reel_ends_on_it():
    lines = [q.text for q in they_voted_no_data.LINES]
    assert "fifty point two to forty-nine point eight" in lines[3]
    assert lines[-1] == "They voted no." and they_voted_no_data.BEATS[-1].who == "vera"


def test_the_digits_stay_while_the_tag_turns_on_the_word_right():
    pilot = they_voted_no_data
    right = next(b for b in pilot.BEATS if b.event == "right")
    assert right.word == 6 and right.caption == "right."
    groups = overlay(pilot)
    assert float(groups["news-oven-clock-right"].get("start", "0")) == right.start


def test_the_phone_shows_what_opened_first_and_not_all_of_phase_one():
    assert safe_from_you_data.NOTES[0] == "PHASE ONE: BITCOIN FIRST"


@reel
def test_the_opening_is_the_card_the_line_and_a_reaction_by_five_seconds(pilot):
    sk = pilot.SKETCH
    assert sk.beats[0].event == "card" and sk.beats[0].line == 0
    reaction = next(b for b in sk.beats if b.line is not None and sk.lines[b.line].speaker == "gus")
    assert reaction.start < 5.0


@reel
def test_no_banner_because_the_kinds_never_mix(pilot):
    assert not [name for name in overlay(pilot) if name.startswith("news-banner")]


@reel
def test_the_parody_tag_runs_from_the_first_frame_to_the_last_on_a_tagged_reel(pilot):
    assert pilot.STORY.parody is (pilot in TAGGED)
    tag = overlay(pilot).get("news-parody-tag")
    if pilot not in TAGGED:
        assert tag is None
        return
    assert float(tag.get("start", "0")) == 0.0
    assert float(tag.get("end", "0")) == pilot.SKETCH.end


@pytest.mark.parametrize("pilot", TAGGED, ids=lambda m: m.SLUG)
def test_the_credit_stands_on_the_top_row_between_the_show_and_the_tag(pilot):
    groups = overlay(pilot)

    def span(name: str) -> tuple[float, float]:
        chip = next(n for n in groups[name] if n.get("shape") == "rect" and n.get("fill") != news_inked.SHADOW)
        return float(chip.get("x")), float(chip.get("x")) + float(chip.get("width"))

    assert span("news-bug")[1] < span("news-source-card-small")[0]
    assert span("news-source-card-small")[1] < span("news-parody-tag")[0]


def test_a_credit_too_long_for_the_top_row_is_refused():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4.0, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
    long = news_kit.Source("The Outlet With A Rather Long Name Indeed", "Oct 30, 2026", "A headline")
    with pytest.raises(NewsKitError, match="top row"):
        news_inked.source_card(cv, cv.comp, long, 0.0, 1.0, 2.0, lambda t, s: 0.42 * s * len(t), beside_tag=True)


@reel
def test_the_source_stays_on_screen_from_the_first_frame_to_the_last(pilot):
    groups = overlay(pilot)
    large, small = groups["news-source-card"], groups["news-source-card-small"]
    assert float(large.get("start", "0")) == 0.0
    assert float(large.get("end", "0")) == float(small.get("start", "0"))
    assert float(small.get("end", "0")) == pilot.SKETCH.end


@reel
def test_the_show_and_the_source_are_drawn_over_the_phone_so_they_are_not_dimmed(pilot):
    names = list(overlay(pilot))
    phones = [i for i, name in enumerate(names) if name in PHONES]
    assert not phones or max(phones) < names.index("news-bug") < names.index("news-source-card")


@reel
def test_the_ticker_waits_for_the_card_to_leave_its_place(pilot):
    assert float(overlay(pilot)["news-ticker"].get("start", "0")) >= news_kit.SLIDE


@reel
def test_a_lower_third_never_sits_behind_a_phone(pilot):
    groups = overlay(pilot)
    phones = [g for name, g in groups.items() if name in PHONES]
    for name, lower in groups.items():
        if not re.fullmatch(r"news-lower-\d+", name):
            continue
        for phone in phones:
            assert float(lower.get("end", "0")) <= float(phone.get("start", "0")) or (
                float(lower.get("start", "0")) >= float(phone.get("end", "0"))
            )


@reel
def test_a_lower_third_never_names_the_other_anchor_for_as_long_as_it_stays(pilot):
    names = {"VERA STILLMAN, ANCHOR": "vera", "GUS BELLOWS, CO-HOST": "gus"}
    sk = pilot.SKETCH
    for a, b, kicker, _ in pilot.STORY.spans(sk.beats, sk.end):
        for beat in sk.beats:
            if kicker in names and a <= beat.start < b and beat.who in names.values():
                assert beat.who == names[kicker], f"{kicker} over {beat.who} at {beat.start}"


@pytest.mark.parametrize("pilot", [safe_from_you_data, they_voted_no_data], ids=lambda m: m.SLUG)
def test_a_lower_third_stays_long_enough_to_be_read_after_it_slides_in(pilot):
    sk = pilot.SKETCH
    spans = pilot.STORY.spans(sk.beats, sk.end, pilot_inserts(pilot))
    assert all(b - a >= 1.2 for a, b, _, _ in spans), [(a, b) for a, b, _, _ in spans if b - a < 1.2]


@reel
def test_a_lower_third_names_only_who_speaks_or_fills_the_shot(pilot):
    names = {"VERA STILLMAN, ANCHOR": "vera", "GUS BELLOWS, CO-HOST": "gus"}
    for index, kicker, line in pilot.LOWERS:
        for name, who in names.items():
            if name in (kicker, line):
                beat = pilot.BEATS[index]
                speaker = pilot.LINES[beat.line].speaker if beat.line is not None else None
                assert who in (speaker, beat.who)


@reel
def test_the_caption_opens_on_a_question_and_carries_the_source(pilot):
    post = pilot.POST
    assert post.title.endswith("?")
    assert all(part in post.description for part in (pilot.SOURCE.outlet, pilot.SOURCE.date, pilot.SOURCE.headline))
    assert 3 <= len(post.hashtags) <= 5
    assert "Matilda" in post.credit and "Charlie" in post.credit


@reel
def test_ig_txt_is_the_posts_own_text(pilot):
    assert (folder(pilot) / "ig.txt").read_text(encoding="utf-8").strip() == pilot.POST.text().strip()


@reel
def test_the_cover_comes_before_the_payoff(pilot):
    assert pilot.POST.thumbnail.at < pilot.BEATS[-3].start


@reel
@pytest.mark.parametrize("bad", ["Send this to a friend.", "Follow for more!", "Comment below."])
def test_bait_in_a_line_stops_the_build(pilot, bad):
    lines = list(pilot.LINES)
    lines[1] = Line("gus", bad)
    with pytest.raises((NewsKitError, SketchError)):
        pilot.validate(replace(pilot.SKETCH, lines=tuple(lines)))


@reel
def test_an_unknown_event_stops_the_build(pilot):
    beats = (*pilot.BEATS[:-1], replace(pilot.BEATS[-1], event="confetti"))
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


@reel
def test_a_lost_event_stops_the_build(pilot):
    beats = (replace(pilot.BEATS[0], event=""), *pilot.BEATS[1:])
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


@reel
def test_acts_that_do_not_match_the_beats_stop_the_build(pilot):
    story = replace(pilot.STORY, acts=pilot.ACTS[:-1])
    with pytest.raises(SketchError, match="acts for"):
        story.validate(pilot.SKETCH)


@reel
def test_a_lower_third_past_the_last_beat_stops_the_build(pilot):
    story = replace(pilot.STORY, lowers=((99, "A", "B"),))
    with pytest.raises(SketchError, match="past the last beat"):
        story.validate(pilot.SKETCH)


@reel
def test_a_lower_third_never_sits_behind_the_large_card(pilot):
    story = replace(pilot.STORY, small=2, lowers=((1, "A", "B"),))
    with pytest.raises(SketchError, match="behind the large card"):
        story.validate(pilot.SKETCH)


def test_a_reel_that_does_not_open_on_the_card_is_refused():
    pilot = seabird_jet_lag_data
    story = replace(pilot.STORY, events=tuple(e for e in pilot.STORY.events if e != "card") + ("late",))
    beats = (replace(pilot.BEATS[0], event="late"), *pilot.BEATS[1:])
    with pytest.raises(SketchError, match="with the card up"):
        story.validate(replace(pilot.SKETCH, beats=beats))


@pytest.mark.parametrize(
    ("start", "end", "inserts", "left"),
    [
        (0.0, 10.0, (), [(0.0, 10.0)]),
        (0.0, 10.0, ((2.0, 3.0),), [(0.0, 2.0), (3.0, 10.0)]),
        (2.5, 10.0, ((2.0, 3.0),), [(3.0, 10.0)]),
        (0.0, 2.5, ((2.0, 3.0),), [(0.0, 2.0)]),
        (2.2, 2.8, ((2.0, 3.0),), []),
        (0.0, 5.0, ((3.0, 4.0), (1.0, 2.0)), [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)]),
    ],
)
def test_a_lower_third_is_cut_around_the_phone(start, end, inserts, left):
    assert news_story.clipped(start, end, inserts) == left


@reel
def test_it_has_no_release_and_renders_outside_the_instagram_folder(pilot):
    assert pilot.OUTPUT == f"renders/pilots/{pilot.SLUG}.mp4"
    assert not (ROOT / "episodes" / "releases" / f"{pilot.SLUG}.py").exists()


@reel
def test_notes_carry_the_frontmatter_the_review_needs(pilot):
    head = frontmatter(pilot)
    assert {"pilot", "main-trigger", "generated-by", "date", "type", "story-date"} <= set(head)
    assert head["type"] == "real" and head["pilot"] == pilot.SLUG
    assert int(head["comedy-reviewer"]) >= 14 and int(head["comedy-author"]) >= 14


def test_notes_name_the_new_fact_about_gus_for_the_cast_bible():
    assert "wife" in (folder(seabird_jet_lag_data) / "notes.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "module", ["seabird_jet_lag_audio", "space_haiku_audio", "safe_from_you_audio", "they_voted_no_audio"]
)
def test_the_recording_carries_the_banner(module):
    text = (PILOTS / f"{module}.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text


@reel
def test_the_recorded_statement_is_finished_by_three_seconds(pilot):
    episodes = os.environ.get("SRSTUDIO_EPISODES")
    project = Path(episodes or "") / "pilots" / "news" / pilot.SLUG
    if not episodes or not (project / "voiced" / "speech.json").is_file():
        pytest.skip("no recording in this checkout")
    assert craft.statement(project, pilot.FIRST_STATEMENT).end <= craft.STATEMENT_BY


def test_importing_every_reel_module_leaves_no_clash_of_seeds():
    seeds = {importlib.import_module(m.__name__).SEED for m in REELS}
    assert len(seeds) == len(REELS)
