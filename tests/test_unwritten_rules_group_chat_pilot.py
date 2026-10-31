"""The Unwritten Rules, the group chat: the rule he breaks is the first one, the premise lands by three seconds, the
cutaways stay gags, no invented fact reaches the screen, and the pilot stays off the @tuxmeme publishing path."""

from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import comedy_floor, host_kit, sketch
from srstudio.sketch import Line, SketchError
from srstudio.social import InstagramPost

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import unwritten_rules_group_chat_data as pilot  # noqa: E402

FOLDER = ROOT / "pilots" / "host" / pilot.SLUG


def frontmatter() -> dict[str, str]:
    head = (FOLDER / "notes.md").read_text(encoding="utf-8").split("---")[1]
    return {k.strip(): v.strip() for k, v in (row.split(":", 1) for row in head.strip().splitlines())}


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_his_mouth_opens_on_the_first_sound_of_a_take():
    assert pilot.MOUTH.first_sound


def test_he_speaks_on_the_first_frame_and_the_premise_is_on_screen_in_seven_words():
    first = pilot.SKETCH.beats[0]
    assert first.start == 0.0 and first.line == 0
    text = pilot.LABELS[0][2]
    assert len(text.split()) <= 7 and "RULES" in text
    assert pilot.beat("where").start <= 3.0


def test_the_three_rules_arrive_in_order_with_the_phone_between_them():
    order = [pilot.NAMES.index(name) for name in ("one", "buzz-1", "two", "buzz-2", "three", "buzz-3", "press", "sign")]
    assert order == sorted(order)
    assert [row[2] for row in pilot.LABELS[1:]] == ["RULE 1", "RULE 2", "RULE 3"]


def test_he_leaves_you_on_read_which_is_rule_one():
    assert "on read" in pilot.LINES[2].text
    assert pilot.ASKED[0].status == "Read by Lint"
    assert pilot.beat("press").event == "press" and pilot.ACTS[pilot.NAMES.index("press")].arm == "press"
    lit = host_kit.light_spans(pilot.BEATS, pilot.END)
    assert lit[-1][1] == pilot.beat("press").start


def test_the_last_frame_frames_and_lights_as_the_first_so_it_cuts_back():
    assert pilot.BEATS[0].who == pilot.BEATS[-1].who == "lint"
    last = pilot.ACTS[-1]
    assert last.pull == 0 and last.arm == "rest"
    assert all(b <= pilot.beat("press").start for _, b in host_kit.light_spans(pilot.BEATS, pilot.END))


def test_every_episode_closes_on_the_sign_off():
    assert pilot.SKETCH.lines[-1].text == pilot.SIGN_OFF == "You know what you did."
    broken = replace(pilot.SKETCH, lines=(*pilot.LINES[:-1], Line("lint", "Goodbye.")))
    with pytest.raises(SketchError, match="sign-off"):
        pilot.validate(broken)


def test_a_reel_that_opens_on_silence_or_puts_the_phone_out_twice_is_refused():
    beats = (sketch.Beat(0.0, "lint", "", "side", "flat", "desk"), *pilot.BEATS[1:])
    silent = sketch.Sketch(
        pilot.SLUG, pilot.TITLE, pilot.SKETCH.speakers, pilot.LINES, beats, pilot.END, cast=pilot.SKETCH.cast
    )
    with pytest.raises(SketchError):
        pilot.validate(silent)


def test_nothing_on_screen_is_a_number_a_receipt_or_money():
    shown = [*(q.text for q in pilot.LINES), *(row[2] for row in pilot.LABELS), *(b.text for b in pilot.ASKED)]
    digits = [text for text in shown if re.search(r"\d", text) and not text.startswith("RULE ")]
    assert digits == [] and not any("$" in text or "%" in text for text in shown)
    assert (FOLDER / "sources.md").read_text(encoding="utf-8").count("no factual claims") == 1


def test_nobody_real_and_no_group_of_people_is_the_joke():
    words = " ".join(q.text for q in pilot.LINES).lower()
    assert not re.search(r"\b(?:women|men|boomers|millennials|gen z|moms|dads)\b", words)


def test_the_cutaways_are_gags_of_at_most_a_second_and_a_half_as_scripted():
    assert pilot.beat("laugh").start - pilot.beat("haha").start <= 1.5
    assert pilot.beat("chewing").start - pilot.beat("insert").start <= 1.5


def test_the_hold_before_the_sign_off_is_long_enough_to_land():
    assert round(pilot.beat("sign").start - pilot.beat("press").start, 6) >= 1.2  # 28.2 - 27.0 is 1.1999999999999993


def test_the_post_asks_a_question_and_stops_at_five_hashtags():
    assert isinstance(pilot.POST, InstagramPost) and pilot.POST.title.endswith("?")
    assert len(pilot.POST.hashtags) <= 5


def test_the_caption_carries_the_disclosure_word_for_word():
    text = (FOLDER / "ig.txt").read_text(encoding="utf-8")
    assert "An animated character; synthetic voice." in text.splitlines()
    assert text.splitlines()[0].endswith("?") and len(re.findall(r"#\w+", text)) <= 5


def test_the_notes_carry_the_persona_and_the_comedy_score():
    meta = frontmatter()
    assert meta["pilot"] == pilot.SLUG and meta["main-trigger"] and meta["generated-by"] and meta["date"]
    assert comedy_floor.notes_shortfall((FOLDER / "notes.md").read_bytes()) == ""
    notes = (FOLDER / "notes.md").read_text(encoding="utf-8").lower()
    for heading in ("name", "look", "voice", "point of view", "sign-off", "never do", "hook formula", "three rules"):
        assert heading in notes


def test_the_audio_script_carries_the_banner_and_the_kit_the_pilot_stays_off_the_release_path():
    audio = (PILOTS / "unwritten_rules_group_chat_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in audio
    assert "renders/pilots/" in pilot.OUTPUT
    assert not (ROOT / "episodes" / "releases" / f"{pilot.SLUG}.py").exists()
