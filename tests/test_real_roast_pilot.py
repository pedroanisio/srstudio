"""The real story: the facts are the sources', the joke comes after them, the source stays on screen, and the pilot
stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, craft, news_kit, sketch
from srstudio.news_kit import NewsKitError
from srstudio.sketch import Line, SketchError
from srstudio.thumbnail import Thumbnail

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import real_roast_data as pilot  # noqa: E402

FOLDER = ROOT / "pilots" / "news" / pilot.SLUG
SOURCES = (FOLDER / "sources.md").read_text(encoding="utf-8")
SPOKEN = " ".join(q.text for q in pilot.LINES)
SHOWN = " ".join((*pilot.TICKER, *(w for row in pilot.LOWERS for w in row[1:]), *(b.caption for b in pilot.BEATS)))


def cover() -> Thumbnail:
    assert pilot.POST.thumbnail is not None
    return pilot.POST.thumbnail


def overlay() -> dict[str, ET.Element]:
    """The groups the reel draws over its picture, by id."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")
    pilot.overlay(cv, cv.comp, sk.beats, sk.end, lambda text, size: 0.42 * size * len(text))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def frontmatter() -> dict[str, str]:
    head = (FOLDER / "notes.md").read_text(encoding="utf-8").split("---")[1]
    return {k.strip(): v.strip() for k, v in (row.split(":", 1) for row in head.strip().splitlines())}


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_story_is_from_the_last_48_hours_of_the_day_it_was_picked():
    picked = date(2026, 10, 31)
    assert picked - timedelta(days=2) <= date.fromisoformat(pilot.STORY_DATE) <= picked


def test_the_card_shows_the_outlets_own_headline_word_for_word():
    assert f'"{pilot.SOURCE.headline}"' in SOURCES
    assert "October 30, 2026" in SOURCES and pilot.SOURCE.date == "Oct 30, 2026"
    assert pilot.SOURCE.outlet in SOURCES


def test_two_independent_sources_are_listed_with_links():
    hosts = set(re.findall(r"<https://([^/]+)/", SOURCES))
    assert {"techcrunch.com", "finance.yahoo.com"} <= hosts


@pytest.mark.parametrize("fact", ["several hundred", "993 million"])
def test_every_number_on_screen_is_in_the_sources(fact):
    assert fact in SOURCES and fact in SPOKEN.lower() and fact in SHOWN.lower()


def test_the_opening_states_the_fact_before_anyone_jokes():
    assert pilot.LINES[0].speaker == "vera"
    assert pilot.LINES[0].text == "Several hundred outside AI orders. In total."


def test_it_says_outside_agents_because_the_figure_excludes_doordashs_own():
    assert "outside AI" in pilot.LINES[0].text and "OUTSIDE AI AGENTS" in " ".join(pilot.TICKER)


@pytest.mark.parametrize("claim", ["percent", "%", " share", "fraction", "one in ", "per cent", "ratio", "only "])
def test_two_figures_of_different_periods_are_never_made_a_share(claim):
    assert claim not in f"{SPOKEN} {SHOWN}".lower()


def test_the_opening_shape_is_the_card_the_line_and_the_reaction_by_five_seconds():
    sk = pilot.SKETCH
    assert sk.beats[0].event == "card" and sk.beats[0].line == 0
    reaction = next(b for b in sk.beats if b.line == 1)
    assert reaction.start < 5.0 and sk.lines[1].speaker == "gus"


def test_no_banner_and_no_parody_tag_because_the_kinds_never_mix():
    groups = overlay()
    assert not [name for name in groups if name.startswith(("news-banner", "news-parody"))]


def test_the_source_stays_on_screen_from_the_first_frame_to_the_last():
    groups = overlay()
    large, small = groups["news-source-card"], groups["news-source-card-small"]
    assert float(large.get("start", "0")) == 0.0
    assert float(large.get("end", "0")) == float(small.get("start", "0"))
    assert float(small.get("end", "0")) == pilot.SKETCH.end


def test_the_ticker_waits_for_the_card_to_leave_its_place():
    assert float(overlay()["news-ticker"].get("start", "0")) >= news_kit.SLIDE


def test_the_stare_holds_before_the_last_line():
    stare = sketch.events(pilot.BEATS, "stare")[0][0]
    last = next(b for b in pilot.BEATS if b.line == 8)
    assert last.start - stare >= 1.2


def test_the_last_line_is_the_anchors_and_the_last_act_is_the_phone_put_down():
    assert pilot.LINES[-1].speaker == "vera" and "delivery fee" in pilot.LINES[-1].text
    assert pilot.BEATS[-1].event == "face-down" and pilot.ACTS[-1].gus.arms == "rest"


def test_the_cover_does_not_show_the_payoff():
    assert cover().at < sketch.events(pilot.BEATS, "stare")[0][0]
    assert "fee" not in cover().headline.lower()


def test_the_caption_opens_on_a_question_and_carries_the_source():
    post = pilot.POST
    assert post.title.endswith("?")
    assert all(part in post.description for part in (pilot.SOURCE.outlet, pilot.SOURCE.date, pilot.SOURCE.headline))
    assert 3 <= len(post.hashtags) <= 5
    assert "Matilda" in post.credit and "Charlie" in post.credit


@pytest.mark.parametrize("bad", ["Send this to a friend.", "Follow for more!", "Comment below."])
def test_bait_in_a_line_stops_the_build(bad):
    lines = list(pilot.LINES)
    lines[1] = Line("gus", bad)
    with pytest.raises((NewsKitError, SketchError)):
        pilot.validate(replace(pilot.SKETCH, lines=tuple(lines)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "stare" else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="explosion") if b.event == "stare" else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_acts_and_beats_out_of_step_stop_the_build():
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=pilot.BEATS[:-1]))


def test_a_pilot_has_no_release_and_no_post():
    assert pilot.SLUG not in (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_the_notes_say_what_the_brief_asks():
    notes = frontmatter()
    assert notes["pilot"] == pilot.SLUG and notes["type"] == "real" and notes["story-date"] == pilot.STORY_DATE
    assert notes["generated-by"] == "claude-opus-5-5 in Claude Code" and notes["main-trigger"]
    assert int(notes["comedy-author"]) >= 14


def test_the_recording_script_carries_the_banner():
    text = (PILOTS / "real_roast_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "Absence of output verification is a design defect, not a runtime bug." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text


@pytest.mark.parametrize("window", range(len(pilot.LOWERS)))
def test_a_lower_third_names_only_who_is_speaking_or_alone_on_screen(window):
    """A name under the other anchor's face reads as her name."""
    index, kicker, _ = pilot.LOWERS[window]
    name = next((k for k in ("vera", "gus") if kicker.lower().startswith(k)), None)
    if name is None:
        return
    stop = pilot.LOWERS[window + 1][0] if window + 1 < len(pilot.LOWERS) else len(pilot.BEATS)
    for beat in pilot.BEATS[index:stop]:
        speaking = None if beat.line is None else pilot.LINES[beat.line].speaker
        assert speaking == name or beat.who == name, (kicker, beat.start)


def test_the_first_statement_ends_by_second_three_on_the_recorded_take():
    """L4: the trouble is clear by second 3. Read from the take the master was built from, so no constant can agree
    with itself here; the text check refuses a project recorded from an older script."""
    episodes = os.environ.get("SRSTUDIO_EPISODES")
    if not episodes:
        pytest.skip("needs SRSTUDIO_EPISODES and the recorded project")
    said = craft.statement(Path(episodes) / "pilots" / "news" / pilot.SLUG, pilot.FIRST_STATEMENT)
    assert said.text == pilot.LINES[0].text
    assert said.end <= craft.STATEMENT_BY
