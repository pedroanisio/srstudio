"""The pilot's script is checked, its figures are the sources', and it stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, mind_kit, sketch, toon_head, toon_rigs, toon_sketch
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import peak_end_rule_data as pilot  # noqa: E402

BOW_TIE_HALF = 11.0  # the knot's drawn half-height, in its own units
LAST_TAKE = 1.86  # the measured length of the sloth's last line, in seconds


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def spoken() -> str:
    return " ".join(q.text for q in pilot.LINES).lower()


def on_screen() -> str:
    return " ".join(
        (spoken(), *pilot.FILES, pilot.NAME, pilot.STUDY.what, pilot.STUDY.result, pilot.SHORT[0], pilot.LONG[0])
    ).lower()


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_figures_are_the_ones_the_paper_printed():
    assert "22 of 32 (69%)" in pilot.STUDY.result
    assert round(100 * 22 / 32) == 69
    assert "32 male students" in pilot.STUDY.what  # all male: the card may not read as people in general
    assert pilot.SHORT[1:] == (60 / 90, "60 s")
    assert pilot.LONG[1:] == (1.0, "90 s")
    assert "slightly warmer" in pilot.LONG[0].lower()


def test_the_narrator_says_the_figures_the_card_shows():
    assert "thirty-two male students" in spoken()
    assert "twenty-two of them" in spoken()


def test_the_figures_in_the_post_are_the_ones_on_the_card():
    assert "22 of 32 male students" in pilot.POST.description
    assert "Kahneman, Fredrickson, Schreiber & Redelmeier (1993)" in pilot.POST.description


@pytest.mark.parametrize(
    "claim",
    [
        "forget",
        "patient",
        "colonoscop",
        "everyone",
        "always",
        "this will work",
        "came back",
        "proven",
        "memory ignores",
    ],
)
def test_the_reel_and_its_caption_never_say_what_the_sources_contradict(claim):
    assert claim not in on_screen()
    assert claim not in pilot.POST.description.lower()


@pytest.mark.parametrize("setting", ["holiday", "vacation", "meeting", "date", "hospital"])
def test_a_setting_nobody_tested_is_not_on_screen(setting):
    assert setting not in on_screen()


def test_the_dinner_is_said_not_to_be_the_study():
    assert "cold water isn't dinner" in spoken()
    assert "cold water isn't dinner" in pilot.POST.description.lower()
    assert "thing to try" in pilot.POST.description


def test_the_rule_is_hedged_where_it_is_stated():
    assert "you often reach for" in spoken()
    assert "we often judge" in pilot.POST.description.lower()


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((17, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "mint" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "pay" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"worst": "dim", "dim": "worst"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_opens_on_the_behaviour_with_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_last_line_is_his_first_line_again_and_the_opening_comes_next():
    sloth = [q.text for q in pilot.LINES if q.speaker == "sloth"]
    assert sloth[0] == sloth[-1] == pilot.LINES[-1].text
    assert pilot.LINES[0].text == "Five stars."


def test_the_name_is_spoken_once():
    assert sum(pilot.NAME.lower() in q.text.lower() for q in pilot.LINES) == 1


def test_the_reel_fits_the_format():
    assert 25.0 <= pilot.SKETCH.end <= 45.0


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert not list((ROOT / "episodes").glob(f"releases/**/*{pilot.SLUG}*"))
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def test_the_audio_script_carries_the_banner():
    text = (PILOTS / "peak_end_rule_audio.py").read_text(encoding="utf-8")
    for line in (
        "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.",
        "Absence of output verification is a design defect, not a runtime bug.",
        "All LLM output must be treated as untrusted and validated explicitly.",
    ):
        assert line in text


def scene_of(app: sketch.Appearance) -> ET.Element:
    """The shot as the pilot dresses it, the character's own drawing left out."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    back, light, front = (cv.group(cv.comp, name) for name in ("back", "light", "front"))
    measure = lambda text, size: 0.5 * size * len(text)  # noqa: E731
    pilot.dress(toon_sketch.Shot(cv, app, back, front, sk.beats, sk.end, measure, light, pilot.VERSIONS))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


APPEARANCES = sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end)


def appearance(who: str, nth: int = 0) -> sketch.Appearance:
    return [a for a in APPEARANCES if a.who == who][nth]


def at(event: str) -> float:
    return sketch.events(pilot.BEATS, event)[0][0]


def groups(root: ET.Element, wanted: str) -> list[ET.Element]:
    return [g for g in root.iter("group") if g.get("id", "").startswith(wanted)]


def starts_of_layers_saying(root: ET.Element, word: str) -> list[float]:
    """For each layer that shows ``word``: the latest start among the groups around it."""
    parent = {child: node for node in root.iter() for child in node}
    assets = {node.get("id") for node in root.iter("text") if word in node.get("text", "")}
    found = []
    for layer in root.iter("layer"):
        if layer.get("asset") in assets:
            starts, node = [0.0], layer
            while node in parent:
                node = parent[node]
                starts.append(float(node.get("start", 0.0)))
            found.append(max(starts))
    return found


def test_the_board_is_not_lettered_while_the_phone_stands_in_front_of_it():
    """The contrast check measures covered lettering too, and fails the strict encode."""
    starts = starts_of_layers_saying(scene_of(appearance("raccoon", 0)), "LOBSTER")
    assert starts and min(starts) >= at("wait")


def test_the_second_mint_lands_during_the_last_line():
    mints = groups(scene_of(appearance("sloth", -1)), "mint")
    arrivals = [float(key.get("time")) for g in mints for key in g.find("animate") if key.get("value") == "1"]
    assert arrivals == [pytest.approx(at("last") + pilot.LANDS)]
    assert pilot.LANDS < LAST_TAKE


def test_the_mint_comes_after_the_bill_is_paid():
    assert at("pay") + pilot.PAID < at("mint")


def test_the_second_file_slides_after_the_first_and_the_shelf_is_pulled_at_worst_and_last():
    assert pilot.FILES[pilot.WORST] == "Market price"
    assert pilot.FILES[pilot.LAST] == "The mint"
    assert pilot.SECOND_FILE > 0
    assert at("worst") + pilot.SECOND_FILE < at("dim")


def test_the_bow_tie_clears_the_sloths_mouth():
    rig = toon_rigs.rig_of(sketch.part_of("sloth"), pilot.VERSIONS)
    _, chest = toon_head.chest(rig)
    knot = chest - pilot.TIE_UP
    assert knot - pilot.TIE * BOW_TIE_HALF > rig.look.mouth[1]


def test_the_sloth_wears_the_tie_in_every_shot_he_has():
    for app in (a for a in APPEARANCES if a.who == "sloth"):
        assert groups(scene_of(app), "tie")
