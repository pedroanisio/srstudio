"""The pilot's script is checked, its figures are the sources', its circles are one size, and it stays outside the
@tuxmeme publishing path."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import map_kit, sketch, toon_rigs
from srstudio.canvas import Canvas
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import inside_the_circle_data as pilot  # noqa: E402

AT = {name: sketch.events(pilot.BEATS, name)[0][0] for name in pilot.EVENTS}
SOURCES = ROOT / "pilots" / "maps" / "inside-the-circle" / "sources.md"
SAID = " ".join(q.text for q in pilot.LINES)
WORDS = " ".join((SAID, pilot.LEGEND, pilot.COUNT, pilot.OVER, pilot.POST.title, pilot.POST.description))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_reel_keeps_to_the_length_and_opens_on_the_claim():
    assert 20.0 <= pilot.END <= 30.0
    assert pilot.BEATS[0].start == 0.0 and pilot.BEATS[0].line == 0
    assert pilot.LINES[0].text == "Nearly half of all people live inside this circle."


def test_the_stamps_are_the_ones_the_sources_allow():
    assert pilot.COUNT == "Inside 3.95 bn. Outside 4.24 bn. GHS-POP 2025."
    assert pilot.OVER == "Same circle over Australia: 44 million. GHS-POP 2025."
    assert pilot.LEGEND == "1 dot = 1 million people, rounded. GHS-POP 2025."


def test_the_figures_on_screen_round_the_ones_in_the_sources():
    text = SOURCES.read_text(encoding="utf-8")
    for figure in ("3,954,047,236", "4,237,941,300", "8,191,988,536", "43,750,398"):
        assert figure in text
    inside, outside, adelaide = 3_954_047_236, 4_237_941_300, 43_750_398
    assert round(inside / 1e9, 2) == 3.95 and round(outside / 1e9, 2) == 4.24
    assert inside + outside == 8_191_988_536 and inside / (inside + outside) < 0.5
    assert round(adelaide / 1e6) == 44 and round(inside / adelaide, -1) == 90


def test_the_dots_on_the_map_count_what_the_stamps_say():
    dots = {zone: len(map_kit.dots(zone)) for zone in ("inside", "adelaide")}
    assert dots == {"inside": 3954, "adelaide": 44}


def test_the_said_numbers_agree_with_the_stamp():
    assert "almost four billion inside" in SAID and "over four billion outside" in SAID


@pytest.mark.parametrize(
    "claim",
    (
        "smallest",
        "best circle",
        "half the world lives here",
        "Quah was wrong",
        "Canada",
        "More people live inside",
        "44 million Australians",
        "more than half",
    ),
)
def test_the_reel_never_says_what_the_sources_rule_out(claim):
    assert claim.lower() not in WORDS.lower()


def test_both_circles_are_one_radius_at_one_scale():
    assert map_kit.ring_px(pilot.RADIUS_KM, pilot.ZOOM) == pytest.approx(pilot.RING_PX, abs=0.01)


def test_the_2013_circle_is_wider_and_drawn_where_it_was():
    x, y, radius = pilot.first_drawn()
    assert radius > pilot.RING_PX and radius == pytest.approx(map_kit.ring_px(4000.0, pilot.ZOOM))
    assert x > 540.0 and y > pilot.RING_Y  # south and east of Mong Khet


def test_the_caption_says_how_the_second_circle_was_placed():
    text = pilot.POST.description
    assert "chosen so the circle holds the country and largely misses Java" in text
    assert "Lambert equal-area." in text and "GHS-POP 2025" in text


def test_the_credits_are_in_the_caption():
    credit = pilot.POST.credit
    for owed in ("GHS-POP R2023A, European Commission JRC, CC BY 4.0", "GeoNames", "Made with Natural Earth."):
        assert owed in credit
    assert "recoloured" in credit and "summed inside circles" in credit


def test_the_hamster_reacts_by_five_seconds():
    assert 3.0 <= AT["crowd"] <= 5.0


def test_the_hamster_is_not_the_narrators_voice_and_has_a_rig():
    assert pilot.HAMSTER.voice.id != map_kit.NARRATOR.voice.id
    assert toon_rigs.rig_of(sketch.part_of("hamster"), pilot.VERSIONS)


def dressed(beats=pilot.BEATS, end=pilot.END) -> str:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=end, background="#ffffff")
    cv = Canvas(scene, map_kit.MAPS.palettes[0], font_asset="lexend", width=1080, height=1920)
    for app in sketch.appearances(beats, end):
        pilot.dress(
            SimpleNamespace(
                cv=cv,
                app=app,
                back=cv.group(cv.comp, cv.uid("g")),
                front=cv.group(cv.comp, cv.uid("g")),
                beats=beats,
                end=end,
                measure=lambda text, size: len(text) * size * 0.6,
            )
        )
    return scene.to_bytes().decode()


def test_the_44_are_only_on_the_maps_that_hold_them_in_frame():
    xml = dressed()
    rest = round((AT["slide"] + pilot.SLIDE) * 1000)
    assert xml.count('k=adelaide-0"') == 2
    assert f'world-{rest}-red-adelaide-0"' in xml and f'world-{round(AT["many"] * 1000)}-red-adelaide-0"' in xml


def test_the_ring_spans_the_cuts_between_maps_so_its_tag_stays_long_enough_to_read():
    xml = dressed()
    shots = sum(a.who == map_kit.CARD for a in sketch.appearances(pilot.BEATS, pilot.END))
    assert xml.count('id="ring-') == shots and xml.count('id="home-ring-') == 1


def test_a_map_that_has_not_come_to_rest_before_the_dots_fall_stops_the_build():
    with pytest.raises(sketch.SketchError, match="rests"):
        pilot._rest({**AT, "fall": AT["slide"] + pilot.SLIDE - 0.1})


def test_a_map_that_comes_home_too_late_stops_the_build():
    with pytest.raises(sketch.SketchError, match="comes home"):
        pilot._rest({**AT, "first": AT["many"] + 0.5})


def test_a_count_line_too_short_for_its_ripples_stops_the_build():
    beats = tuple(replace(b, start=AT["count"] + 1.0) if b.event == "origin" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the count needs"):
        pilot._ripples(SimpleNamespace(beats=beats))


def test_no_more_labels_at_once_than_a_phone_can_read():
    map_kit.check_labels(pilot.labels(pilot.BEATS, pilot.END))


@pytest.mark.parametrize("bad", ("Comment below", "Follow for more"))
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    lines = (*pilot.LINES[:-1], Line("narrator", bad))
    with pytest.raises(map_kit.MapKitError):
        pilot.validate(replace(pilot.SKETCH, lines=lines))


def test_a_lost_event_stops_the_build():
    beats = tuple(b for b in pilot.BEATS if b.event != "count")
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swapped = {"dots": "count", "count": "dots"}
    beats = tuple(replace(b, event=swapped.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_last_frame_is_the_first():
    last = pilot.BEATS[-1]
    assert last.line is None and last.event == "first" and last.caption == pilot.LINES[0].text


def test_a_pilot_has_no_release_and_no_post():
    assert not (ROOT / "episodes" / "releases" / f"{pilot.SLUG}.py").exists()
    assert not (ROOT / "episodes" / "posts" / f"{pilot.SLUG}.py").exists()
    assert pilot.OUTPUT == "renders/pilots/inside-the-circle.mp4"


def test_no_hearing_was_written():
    assert not any(q.heard for q in pilot.LINES)


def test_the_recording_script_carries_the_banner():
    text = (PILOTS / "inside_the_circle_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text
