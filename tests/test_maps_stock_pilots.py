"""Maps #3 and #4: the scripts are checked, each figure is the one its sources give, and both stay outside the
publishing path."""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from srstudio import map_kit, sketch

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import dig_straight_down_data as dig  # noqa: E402
import most_time_zones_data as zones  # noqa: E402

BOTH = (dig, zones)
each = pytest.mark.parametrize("pilot", BOTH, ids=[pilot.SLUG for pilot in BOTH])


def sources(pilot) -> str:
    return (ROOT / "pilots" / "maps" / pilot.SLUG / "sources.md").read_text(encoding="utf-8")


def said(pilot) -> str:
    return " ".join(q.text for q in pilot.LINES)


@each
def test_the_pilot_as_written_is_valid(pilot):
    pilot.validate()


def test_the_numbers_follow_the_first_two():
    assert dig.SERIES == "Maps #3" and zones.SERIES == "Maps #4"


@each
def test_the_series_number_is_in_the_title_the_cover_and_the_caption(pilot):
    assert pilot.SERIES in pilot.TITLE
    assert pilot.POST.thumbnail.kicker == pilot.SERIES
    assert pilot.POST.description.startswith(pilot.SERIES)


@each
def test_the_reel_keeps_its_length_and_speaks_on_the_first_frame(pilot):
    assert 20.0 <= pilot.END <= 30.0
    assert pilot.BEATS[0].start == 0.0 and pilot.BEATS[0].line == 0


@each
def test_the_caption_opens_on_a_question_and_keeps_to_five_hashtags(pilot):
    assert pilot.POST.title.endswith("?")
    assert len(pilot.POST.hashtags) <= 5


@each
def test_a_lost_event_stops_the_build(pilot):
    beats = tuple(replace(b, event="") if b.event == pilot.EVENTS[0] else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


@each
def test_an_unknown_event_stops_the_build(pilot):
    beats = tuple(replace(b, event="bonus") if b.event == pilot.EVENTS[-1] else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


@each
def test_events_out_of_order_stop_the_build(pilot):
    first, second = pilot.EVENTS[:2]
    swap = {first: second, second: first}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


@each
def test_the_labels_stay_within_what_a_phone_can_read(pilot):
    map_kit.check_labels(pilot.labels(pilot.BEATS, pilot.END))
    too_many = [(0.0, pilot.END, str(n)) for n in range(map_kit.MOST_LABELS + 1)]
    with pytest.raises(map_kit.MapKitError):
        map_kit.check_labels(too_many)


@pytest.mark.parametrize(
    ("here", "there"), [(dig.NEW_YORK, dig.INDIAN), (dig.BEIJING, dig.ARGENTINA), (dig.MADRID, dig.NEW_ZEALAND)]
)
def test_each_far_point_is_the_antipode_of_its_city(here, there):
    assert there.lat == pytest.approx(-here.lat)
    assert abs(there.lon - here.lon) == pytest.approx(180.0)


def test_the_antipodes_are_the_ones_the_sources_give():
    text = sources(dig)
    for figure in ("40.714 S, 105.994 E", "39.907 S, 63.603 W", "40.416 S, 176.297 E", "79.82%", "13.10%"):
        assert figure in text


def test_the_figures_on_screen_round_the_ones_in_the_sources():
    assert dig.STAMP == "80% of people. GHS-POP 2025, Natural Earth."
    assert round(79.82) == 80
    assert dig.EIGHTH == "About an eighth of the land has land opposite."
    assert abs(13.10 - 100 / 8) < 1.0


def test_the_reel_says_beijing_and_never_what_all_of_china_gets():
    assert "Beijing comes up in Argentina." in said(dig)
    assert "Beijing is not all of China" in dig.POST.description


def test_the_stamp_says_july_because_january_is_a_tie():
    assert zones.COUNT.startswith("July:")
    assert "In January France and Russia tie at 11." in zones.POST.description
    assert "tie at 11" in sources(zones)


def test_the_twelve_clocks_are_the_offsets_the_sources_give_and_all_differ():
    assert ", ".join(f"{o:g}" for o in zones.OFFSETS) in sources(zones)
    assert len(set(zones.hours())) == 12


def test_the_clocks_read_one_moment():
    paris = zones.hours()[zones.OFFSETS.index(2.0)]
    tahiti = zones.hours()[zones.OFFSETS.index(-10.0)]
    assert paris == 12.0 and tahiti == 0.0


def test_the_seven_towns_are_the_ones_the_figure_was_computed_on():
    names = {town.name for town in zones.TOWNS}
    assert len(names) == 7
    for name in names:
        assert name in sources(zones)


def test_a_town_is_lit_all_through_the_day_the_reel_shows():
    assert zones.darkest(zones.WORST_DAY) >= 1


def test_the_build_stops_if_the_reel_would_show_twelve_clocks_that_are_not(monkeypatch):
    monkeypatch.setattr(zones, "OFFSETS", (1.0,) * 12)
    with pytest.raises(sketch.SketchError, match="twelve"):
        zones.validate()


def test_the_build_stops_if_the_day_shown_goes_all_dark(monkeypatch):
    monkeypatch.setattr(zones, "TOWNS", (zones.TOWNS[4],))
    monkeypatch.setattr(zones, "WORST_DAY", datetime(2026, 12, 21, tzinfo=timezone.utc))
    with pytest.raises(sketch.SketchError, match="sun never sets"):
        zones.validate()


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


@each
def test_the_caption_on_disk_is_the_post(pilot):
    path = ROOT / "pilots" / "maps" / pilot.SLUG / "ig.txt"
    assert path.read_text(encoding="utf-8") == pilot.POST.text()
    assert (path.parent / "cover.jpg").stat().st_size > 0
