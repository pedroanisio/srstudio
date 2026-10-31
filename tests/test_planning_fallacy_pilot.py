"""The pilot's script is checked, its figures are the sources', and it stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, Signature, mind_kit, signature, sketch, toon, toon_everyday, toon_house, toon_sketch
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import planning_fallacy_data as pilot  # noqa: E402

NOTES = ROOT / "pilots" / "mind" / pilot.SLUG / "notes.md"
SOURCES = (ROOT / "pilots" / "mind" / pilot.SLUG / "sources.md").read_text(encoding="utf-8")
TURN = "Before you say a time, picture how it went the last few times and how this one could go the same way."


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def apps() -> list[sketch.Appearance]:
    return sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end)


def at(name: str) -> float:
    return sketch.events(pilot.BEATS, name)[0][0]


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_figures_are_the_ones_the_table_printed():
    assert pilot.SAID[2] == "33.9 days" and "| 33.9 days |" in SOURCES
    assert pilot.TOOK[2] == "55.5 days" and "| 55.5 days |" in SOURCES
    assert pilot.SAID[1] == pytest.approx(33.9 / pilot.DAYS) and pilot.TOOK[1] == pytest.approx(55.5 / pilot.DAYS)


def test_both_bars_are_to_one_scale_and_fit_the_kit():
    assert 0 < pilot.SAID[1] < pilot.TOOK[1] <= 1


def test_the_card_says_who_was_counted():
    assert "37" in pilot.STUDY.result and "33" in pilot.STUDY.result
    assert "37 surveyed" in SOURCES and "the 33 who had finished" in SOURCES
    assert "37 surveyed" in pilot.POST.description and "the 33 who had finished" in pilot.POST.description


def test_days_are_counted_from_the_call_on_the_card():
    assert all("from that call" in bar[0] for bar in (pilot.SAID, pilot.TOOK))
    assert "from that call" in pilot.POST.description


def test_the_spoken_figures_are_the_rounded_ones_the_sources_give():
    words = " ".join(q.text for q in pilot.LINES)
    assert "about 34 days" in words and "about 56" in words


def test_the_figures_in_the_post_are_the_ones_spoken():
    assert "about 34 days" in pilot.POST.description and "about 56" in pilot.POST.description
    assert "Buehler, Griffin & Ross (1994)" in pilot.POST.description


def test_the_turn_is_the_wording_the_evidence_carries():
    spoken = " ".join(q.text for q in pilot.LINES)
    assert TURN in spoken
    assert TURN in SOURCES
    assert "the optimism went away" in spoken
    assert "In a later study" in spoken  # Study 4, not the thesis study on the card


@pytest.mark.parametrize(
    "claim",
    [
        "accurate",
        "you'll be right",
        "a month",
        "two months",
        "nearly two",
        "always",
        "lazy",
        "worst case",
        "ten minutes",
    ],
)
def test_a_reel_never_says_what_the_sources_contradict(claim):
    words = " ".join((*(q.text for q in pilot.LINES), pilot.POST.title, pilot.POST.description)).lower()
    assert claim.lower() not in words


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((14, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "took" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "past" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"said": "took", "took": "said"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_late_opening_line_stops_the_build():
    beats = tuple(replace(b, start=b.start + 2.0) if b.start < 2.0 else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_a_reel_over_the_format_stops_the_build():
    with pytest.raises(sketch.SketchError, match="45 seconds"):
        pilot.validate(replace(pilot.SKETCH, end=45.5))


def test_the_name_is_spoken_once_and_the_card_holds_it():
    assert sum(pilot.NAME.lower() in q.text.lower() for q in pilot.LINES) == 1


def test_the_bear_says_nothing_until_after_the_turn():
    before = [b for b in pilot.BEATS if b.line is not None and b.start < at("table")]
    assert "bruno" not in {pilot.LINES[b.line].speaker for b in before}


def test_the_hold_before_the_punchline_is_long_enough():
    knows = next(b for b in pilot.BEATS if b.line == len(pilot.LINES) - 1)
    assert knows.start - at("punch") >= 1.2


def test_the_last_shot_is_the_first_frame_again():
    first, last = apps()[0], apps()[-1]
    a, z = pilot.BEATS[0], pilot.BEATS[-1]
    assert (first.who, a.eyes, a.mouth, a.arms) == (last.who, z.eyes, z.mouth, z.arms)
    assert a.line is None and z.line is None


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


def test_the_narrator_is_the_channels_voice():
    assert pilot.DANIEL.id == "onwK4e9ZLuTAKqWW03F9"


def test_the_post_keeps_to_the_format():
    assert 3 <= len(pilot.POST.hashtags) <= 5


def test_the_notes_say_who_it_is_sent_to():
    head = NOTES.read_text(encoding="utf-8").split("---")[1]
    assert re.search(r"^pilot: planning-fallacy$", head, re.M)
    assert re.search(r"^main-trigger: recipient$", head, re.M)
    assert re.search(r"^to: \S", head, re.M)


def scene_of(app: sketch.Appearance) -> ET.Element:
    """The shot as the pilot dresses it, the character's own drawing left out."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces", signature=Signature())
    back, light, front = (cv.group(cv.comp, name) for name in ("back", "light", "front"))
    measure = lambda text, size: 0.5 * size * len(text)  # noqa: E731
    pilot.dress(toon_sketch.Shot(cv, app, back, front, sk.beats, sk.end, measure, light, pilot.VERSIONS))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def water_spans(app: sketch.Appearance) -> list[tuple[float, float]]:
    root = scene_of(app)
    return [
        (float(n.get("start")), float(n.get("end")))
        for n in root.iter()
        if n.tag == "group" and re.fullmatch(r"water-\d+-\d+", n.get("id") or "")
    ]


def test_the_water_stops_for_the_words_and_nothing_else():
    assert water_spans(apps()[0]) == [(0.0, at("off")), (at("on"), apps()[0].end)]


def test_the_water_runs_again_on_the_last_shot():
    assert water_spans(apps()[-1]) == [(apps()[-1].start, apps()[-1].end)]


def test_there_is_water_in_no_other_shot():
    assert not [a for a in apps()[1:-1] if water_spans(a)]


def test_the_water_keeps_off_her_face():
    assert all(not pilot.DRY_FACE[0] <= x <= pilot.DRY_FACE[1] for x in toon_house.streaks(pilot.DRY_FACE))


def test_every_shot_is_signed_once(monkeypatch):
    drawn = []
    monkeypatch.setattr(signature, "cactus", lambda *args, **kwargs: drawn.append(args))
    for app in apps():
        before = len(drawn)
        scene_of(app)
        assert len(drawn) == before + 1, app.who


def test_every_time_the_bear_is_shown_his_phone_says_the_time():
    wanted = {*pilot.CLOCK}
    drawn = " ".join(ET.tostring(scene_of(a), encoding="unicode") for a in apps() if a.who == "bear")
    assert all(clock in drawn for clock in wanted)


def test_the_clock_only_moves_forward():
    minutes = [int(c.split(":")[0]) * 60 + int(c.split(":")[1]) for c in pilot.CLOCK]
    assert minutes == sorted(minutes)


def test_what_his_table_is_booked_for_is_later_than_any_time_on_his_phone():
    assert "8:15" in pilot.LINES[15].text and all(c.startswith("7:") for c in pilot.CLOCK)


def test_the_screens_fit_the_phone():
    def measure(text: str, size: float) -> float:
        return 0.6 * size * len(text)

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4.0, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    screens = (
        toon_everyday.Screen(0.0, "off"),
        toon_everyday.Screen(1.0, "notify", pilot.SENDER, pilot.HEARD, pilot.CLOCK[0]),
    )
    toon_everyday.phone(cv, cv.comp, screens, measure=measure, id="p", **pilot.PROPPED)


def test_the_stage_shot_keeps_the_rabbit_on_the_plinth():
    assert pilot.SMALL_Y + pilot.SMALL * toon.fy(801) == pytest.approx(toon.fy(801), abs=12.0)
