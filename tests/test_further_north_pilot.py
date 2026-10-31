"""The pilot's script is checked, its figures are the sources', its map tells the truth about the lines, and it stays
outside the @tuxmeme publishing path."""

from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import map_kit, sketch
from srstudio.canvas import Canvas
from srstudio.map_kit import Place
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import further_north_data as pilot  # noqa: E402

AT = {name: sketch.events(pilot.BEATS, name)[0][0] for name in pilot.EVENTS}
FIGURES = {
    "Rome": "41.9°N",
    "New York City": "40.7°N",
    "Paris": "48.9°N",
    "Montreal": "45.5°N",
    "London": "51.5°N",
    "Calgary": "51.1°N",
    "Oslo": "59.9°N",
    "Juneau": "58.3°N",
}
WORDS_ON_SCREEN = " ".join(q.text for q in pilot.LINES) + " " + pilot.STAMP + " " + pilot.POST.description


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_reel_keeps_to_the_length_and_opens_on_the_question():
    assert 20.0 <= pilot.END <= 30.0
    assert pilot.BEATS[0].start == 0.0 and pilot.BEATS[0].line == 0
    assert pilot.LINES[0].text == "Which is further north: Rome, or New York City?"


def dressed() -> str:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=pilot.END, background="#ffffff")
    cv = Canvas(scene, map_kit.MAPS.palettes[0], font_asset="lexend", width=1080, height=1920)
    pilot.dress(
        SimpleNamespace(
            cv=cv,
            back=cv.group(cv.comp, "back"),
            front=cv.group(cv.comp, "front"),
            beats=pilot.BEATS,
            end=pilot.END,
            measure=lambda text, size: len(text) * size * 0.6,
        )
    )
    return scene.to_bytes().decode()


def test_the_last_frame_is_the_first():
    last = pilot.BEATS[-1]
    assert last.line is None and last.event == "first" and last.caption == pilot.LINES[0].text
    written = dressed()
    keys = re.findall(r'<animate property="centerLon"[^>]*>(.*?)</animate>', written)
    begins = float(re.findall(r'value="([^"]+)"', keys[0])[0])
    ends = float(re.findall(r'value="([^"]+)"', keys[-1])[-1])
    assert begins == ends == pilot.TURN_FROM
    for place in ("rome", "nyc"):
        assert f'id="ask-{place}"' in written and f'id="asked-{place}"' in written


@pytest.mark.parametrize(("name", "figure"), FIGURES.items())
def test_each_label_is_its_sources_figure_to_one_decimal(name, figure):
    places = {place.name: place for pair in pilot.PAIRS for place in (pair.over, pair.under)}
    assert places[name].latitude == figure


def test_every_pair_is_the_one_in_the_sources_and_the_line_really_passes_above():
    assert [(p.over.name, p.under.name) for p in pilot.PAIRS] == [
        ("Rome", "New York City"),
        ("Paris", "Montreal"),
        ("London", "Calgary"),
        ("Oslo", "Juneau"),
    ]
    assert all(p.over.lat > p.under.lat for p in pilot.PAIRS)


def test_the_stamp_says_how_the_figures_are_rounded_and_where_they_are_from():
    assert pilot.STAMP == "Latitudes rounded to 0.1°. GeoNames, 2026."


def test_the_projections_are_named_in_the_caption():
    assert "Orthographic globe, then equirectangular." in pilot.POST.description


def test_the_climate_line_is_in_the_caption_and_off_the_calgary_beat():
    assert "Why so mild? Winter winds off the Atlantic." in pilot.POST.description
    assert not any("mild" in q.text or "wind" in q.text for q in pilot.LINES)


def test_the_credits_are_in_the_caption():
    assert "GeoNames (geonames.org), CC BY 4.0" in pilot.POST.credit
    assert "Made with Natural Earth." in pilot.POST.credit


@pytest.mark.parametrize(
    "claim", ["Gulf Stream", "Most people", "city centre", "city center", "Seager", "proved", "Follow", "share this"]
)
def test_the_reel_never_says_what_the_sources_rule_out(claim):
    assert claim.lower() not in WORDS_ON_SCREEN.lower()


def test_new_york_is_never_a_label_alone():
    with pytest.raises(map_kit.MapKitError):
        Place("New York", 40.7, -74.0)
    assert all("New York" not in q.text or "New York City" in q.text for q in pilot.LINES)


def test_a_label_stays_up_long_enough_to_read_before_the_tag_takes_over():
    for i in range(1, len(pilot.PAIRS)):
        assert pilot.hands_at(AT, i) - AT[pilot.WHERE[i]] == pytest.approx(pilot.PIN_READ) or (
            pilot.hands_at(AT, i) - AT[pilot.WHERE[i]] > pilot.PIN_READ
        )


def test_a_flight_lands_on_its_word_or_as_soon_as_the_camera_arrives():
    for i in range(len(pilot.PAIRS)):
        assert pilot.lands_at(AT, i) >= pilot.flies_at(AT, i) + pilot.FLY_WEST
        assert pilot.lands_at(AT, i) >= AT[pilot.LAND[i]]


def test_the_next_pair_is_a_cut_and_not_a_flight_back_across_the_ocean():
    moves = pilot.moves(AT)
    assert len(moves) == 2 * len(pilot.PAIRS) - 1
    assert [m.seconds for m in moves[1::2]] == [pilot.CUT] * (len(pilot.PAIRS) - 1)
    assert all(a.begin + a.seconds <= b.begin for a, b in zip(moves, moves[1:], strict=False))


def test_no_more_labels_at_once_than_a_phone_can_read():
    map_kit.check_labels(pilot.labels(pilot.BEATS, pilot.END))


@pytest.mark.parametrize("bad", ["Tag someone who thinks this.", "Follow for more maps."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    lines = (Line("narrator", bad), *pilot.LINES[1:])
    with pytest.raises(map_kit.MapKitError):
        pilot.validate(replace(pilot.SKETCH, lines=lines))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "nyc" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swapped = {"lock": "rome", "rome": "lock"}
    beats = tuple(replace(b, event=swapped.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_pair_the_wrong_way_round_stops_the_build(monkeypatch):
    rome, nyc = pilot.PAIRS[0].over, pilot.PAIRS[0].under
    monkeypatch.setattr(pilot, "PAIRS", (pilot.Pair(nyc, rome, 72.0), *pilot.PAIRS[1:]))
    with pytest.raises(sketch.SketchError):
        pilot.validate()


def test_a_pilot_has_no_release_and_no_post():
    assert not (ROOT / "episodes" / "releases" / f"{pilot.SLUG}.py").exists()
    assert not (ROOT / "episodes" / "posts" / f"{pilot.SLUG}.py").exists()
    assert pilot.OUTPUT == "renders/pilots/further-north.mp4"


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def test_the_recording_script_carries_the_banner():
    text = (PILOTS / "further_north_audio.py").read_text()
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text
