"""The Unwritten Rules, how are you: Rafa's script keeps the show's rules, can be staged and is ready to record, with
no voice chosen for him and nothing recorded."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import comedy_floor, rafa, rafa_host

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import unwritten_rules_how_are_you_data as pilot  # noqa: E402

FOLDER = ROOT / "pilots" / "host" / pilot.SLUG


def test_the_script_as_written_is_valid():
    pilot.validate()


def test_it_runs_twenty_to_thirty_seconds_at_the_estimated_pace():
    assert 20.0 <= pilot.estimated_seconds() <= 30.0


def test_the_host_is_rafa_and_no_voice_has_been_picked_for_him():
    assert pilot.HOST == "rafa"
    assert pilot.VOICE is None
    assert len(pilot.VOICE_CANDIDATES) == 3
    assert all(name and len(id) == 20 and reason for name, id, reason in pilot.VOICE_CANDIDATES)


def test_every_rule_he_says_is_fine_a_prop_under_his_hand_contradicts():
    rules = {beat.label: beat.prop for beat in pilot.BEATS if beat.label.startswith("RULE")}
    assert len(set(rules.values())) == 3, "each rule puts a different thing under his hand"


def test_he_breaks_rule_one_after_the_longest_hold_and_the_smile_comes_back():
    ids = [beat.id for beat in pilot.BEATS]
    assert ids.index("walking") < ids.index("bread") < ids.index("good")
    assert max(pilot.BEATS, key=lambda beat: beat.hold).id == "walking"
    assert pilot.BEATS[ids.index("good")].mood == "public-smile"
    assert pilot.BEATS[ids.index("where")].mood == "internal-meltdown"


def test_the_moods_are_a_track_his_faces_accept():
    rows = rafa_host.faces(2.0, moods=pilot.moods()[:1])
    assert rows[0].mood == "public-smile"
    assert [mood for _, mood in pilot.moods()] == [
        "public-smile",
        "social-battery",
        "internal-meltdown",
        "public-smile",
    ]


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("mood", "calm", "moods"),
        ("prop", "rafa-toaster", "props"),
        ("insert", "rafa-toaster", "props"),
        ("framing", "wide", "framing"),
        ("hold", -1.0, "hold"),
        ("label", "ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT", "seven"),
    ],
)
def test_a_beat_the_show_cannot_stage_is_refused(field, value, match):
    beats = (replace(pilot.BEATS[0], **{field: value}), *pilot.BEATS[1:])
    with pytest.raises(pilot.ScriptError, match=match):
        pilot.validate(beats)


def test_engagement_bait_is_refused():
    with pytest.raises(pilot.host_kit.HostKitError):
        pilot.validate((replace(pilot.BEATS[0], line="Nobody tells you to follow for more."), *pilot.BEATS[1:]))


@pytest.mark.parametrize(
    ("beats", "match"),
    [
        (pilot.BEATS[1:], "opens"),
        (pilot.BEATS[:-1], "sign-off"),
        (tuple(replace(beat, hold=0.0) for beat in pilot.BEATS), "1.2"),
        (tuple(replace(beat, label="") for beat in pilot.BEATS), "three rules"),
    ],
)
def test_a_script_that_drops_a_show_rule_is_refused(beats, match):
    with pytest.raises(pilot.ScriptError, match=match):
        pilot.validate(beats)


def test_a_script_too_long_is_refused():
    with pytest.raises(pilot.ScriptError, match="30"):
        pilot.validate(tuple(replace(beat, hold=beat.hold + 3.0) for beat in pilot.BEATS))


def test_the_notes_hold_an_estimate_at_the_floor_and_every_candidate():
    text = (FOLDER / "notes.md").read_text(encoding="utf-8")
    head = text.split("---")[1]
    facts = {k.strip(): v.strip() for k, v in (row.split(":", 1) for row in head.strip().splitlines())}
    assert int(facts["comedy-author"]) >= comedy_floor.FLOOR
    assert facts["comedy-reviewer"] == "pending"
    assert all(name in text for name, _, _ in pilot.VOICE_CANDIDATES)
    assert "../../../README.md" in text


def test_every_word_is_in_english_and_the_tote_carries_the_price_he_says():
    assert any("187.40" in line.text for line in rafa.PRINTS["tote-label"].lines)
    assert any("hundred and eighty-seven" in beat.line for beat in pilot.BEATS)


def test_nothing_has_been_recorded():
    assert not list(FOLDER.glob("*.wav")) and not list(FOLDER.glob("*.mp4"))
