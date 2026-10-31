"""The fictional story: visibly parody from the first frame to the last, the banner comes back one time worse, the
phone proves it, and the pilot stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, news_kit, sketch
from srstudio.news_kit import NewsKitError
from srstudio.sketch import Line, SketchError
from srstudio.thumbnail import Thumbnail

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import everyday_breaking_data as pilot  # noqa: E402

FOLDER = ROOT / "pilots" / "news" / pilot.SLUG


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


def test_the_parody_tag_is_on_every_frame():
    tag = overlay()["news-parody-tag"]
    assert float(tag.get("start", "0")) == 0.0 and float(tag.get("end", "0")) == pilot.SKETCH.end


def test_no_source_card_because_the_kinds_never_mix():
    assert not [name for name in overlay() if name.startswith("news-source-card")]


def test_the_reel_opens_on_the_banner_and_ends_back_on_it():
    groups = overlay()
    first, last = groups["news-banner"], groups["news-banner-last"]
    assert float(first.get("start", "0")) == 0.0
    assert float(last.get("end", "0")) == pilot.SKETCH.end


def test_the_end_is_the_opening_one_time_worse():
    assert pilot.FOURTH == pilot.THIRD.replace("THIRD", "FOURTH")
    assert pilot.LOWERS[0][2] == pilot.THIRD


def test_the_first_line_is_the_headline_and_the_co_host_reacts_by_five_seconds():
    assert "five minutes away" in pilot.LINES[0].text and "third time" in pilot.LINES[0].text
    reaction = next(b for b in pilot.SKETCH.beats if b.line == 1)
    assert reaction.start < 5.0 and pilot.LINES[1].speaker == "gus"


def test_the_live_update_comes_before_the_phone():
    update = next(b for b in pilot.BEATS if b.line == 4)
    assert update.start < sketch.events(pilot.BEATS, "buzz")[0][0]


def test_the_hold_before_the_question_is_long_enough_to_read():
    stare = sketch.events(pilot.BEATS, "stare")[0][0]
    asked = next(b for b in pilot.BEATS if b.line == 6)
    assert asked.start - stare >= 1.2


def test_the_phone_proves_it_was_gus_all_along():
    said = [m.text for m in pilot.MESSAGES if m.out]
    assert said.count("five minutes away") == 3 and "just parking" in said
    assert [m.text for m in pilot.MESSAGES if not m.out] == ["you take the bus"]


def test_the_phone_is_gone_before_the_banner_comes_back():
    groups = overlay()
    assert float(groups["news-phone"].get("end", "0")) == float(groups["news-banner-last"].get("start", "0"))


@pytest.mark.parametrize("brand", ["uber", "whatsapp", "instagram", "imessage", "google", "nyc", "london"])
def test_no_real_place_person_or_brand_is_the_subject(brand):
    words = " ".join(
        (
            *(q.text for q in pilot.LINES),
            *pilot.TICKER,
            *(w for row in pilot.LOWERS for w in row[1:]),
            *(m.text for m in pilot.MESSAGES),
            pilot.CHAT,
        )
    )
    assert brand not in words.lower()


def test_the_cover_does_not_show_the_payoff():
    assert cover().at < sketch.events(pilot.BEATS, "buzz")[0][0]
    assert "fourth" not in cover().headline.lower() and "gus" not in cover().headline.lower()


def test_the_caption_opens_on_a_question_and_says_parody():
    post = pilot.POST
    assert post.title.endswith("?") and post.description == "Parody."
    assert 3 <= len(post.hashtags) <= 5
    assert "Matilda" in post.credit and "Charlie" in post.credit


@pytest.mark.parametrize("bad", ["Tag a friend.", "Follow us!", "Link in bio."])
def test_bait_in_a_line_stops_the_build(bad):
    lines = list(pilot.LINES)
    lines[1] = Line("gus", bad)
    with pytest.raises((NewsKitError, SketchError)):
        pilot.validate(replace(pilot.SKETCH, lines=tuple(lines)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "buzz" else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="explosion") if b.event == "buzz" else b for b in pilot.BEATS)
    with pytest.raises(SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_pilot_has_no_release_and_no_post():
    assert pilot.SLUG not in (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_the_notes_say_what_the_brief_asks():
    notes = frontmatter()
    assert notes["pilot"] == pilot.SLUG and notes["type"] == "fictional"
    assert notes["generated-by"] == "claude-opus-5-5 in Claude Code" and notes["main-trigger"]
    assert int(notes["comedy-author"]) >= 14


def test_it_says_it_has_no_sources():
    assert "fictional, no sources" in (FOLDER / "sources.md").read_text(encoding="utf-8")


def test_the_recording_script_carries_the_banner():
    text = (PILOTS / "everyday_breaking_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "Absence of output verification is a design defect, not a runtime bug." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text
