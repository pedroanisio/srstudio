"""The Unwritten Rules, how are you: Rafa's script keeps the show's rules, his voice is the one the operator chose, the
reel is staged from the takes and it stays off the release path."""

from __future__ import annotations

import re
import sys
import wave
from array import array
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import comedy_floor, host_kit, narration, native, rafa, rafa_host, rafa_reel, toon
from srstudio.social import InstagramPost

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


def test_the_host_is_rafa_in_the_voice_the_operator_chose():
    assert pilot.HOST == "rafa"
    assert pilot.VOICE == "Will"
    assert pilot.SEED == 52026
    assert pilot.SPEAKER.voice.id == "bIHbv24MWmeRgasZH58o"
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
    assert int(facts["comedy-reviewer"]) >= comedy_floor.FLOOR
    assert comedy_floor.notes_shortfall((FOLDER / "notes.md").read_bytes()) == ""
    assert '"will is the voice"' in text
    assert all(name in text for name, _, _ in pilot.VOICE_CANDIDATES)
    assert "../../../README.md" in text


def test_every_word_is_in_english_and_the_tote_carries_the_price_he_says():
    assert any("187.40" in line.text for line in rafa.PRINTS["tote-label"].lines)
    assert any("hundred and eighty-seven" in beat.line for beat in pilot.BEATS)


def test_the_recording_stays_out_of_the_repository():
    assert not list(FOLDER.glob("*.wav")) and not list(FOLDER.glob("*.mp4"))


def test_the_sketch_as_timed_from_the_takes_is_valid():
    pilot.validate_sketch()
    with pytest.raises(pilot.ScriptError, match="beats"):
        pilot.validate_sketch(replace(pilot.SKETCH, beats=pilot.SKETCH.beats[:-1], lines=pilot.SKETCH.lines[:-1]))


def test_the_first_statement_is_over_by_three_seconds_and_the_reel_runs_twenty_to_thirty():
    assert pilot.KEPT[0] <= 3.0
    assert 20.0 <= pilot.SKETCH.end <= 30.0
    assert len(pilot.KEPT) == len(pilot.BEATS)


def test_each_hold_is_the_beats_hold_and_every_other_gap_is_the_breath():
    gaps = [
        after - (start + kept)
        for start, kept, after in zip(pilot.starts(), pilot.KEPT, pilot.starts()[1:], strict=False)
    ]
    assert gaps == pytest.approx([beat.hold or pilot.GAP for beat in pilot.BEATS[:-1]])


def test_the_labels_stop_where_he_breaks_the_rule():
    beats = pilot.SKETCH.beats
    rows = pilot.labels(beats, pilot.SKETCH.end)
    assert [text for _, _, text in rows] == [pilot.HOOK_LABEL, "RULE 1", "RULE 2", "RULE 3"]
    assert rows[-1][1] == pilot.beat(pilot.LABEL_STOP).start
    assert all(start < stop for start, stop, _ in rows)


def test_the_sign_off_stays_in_the_framing_that_leaves_his_mouth_above_the_label():
    assert rafa_reel.FRAMES[pilot.BEATS[-1].framing] == 1.0


def test_every_cue_fits_its_band_once_the_long_line_breaks_at_its_sentence():
    lines = [toon.Line(str(i), beat.line, 0.0, 2.0) for i, beat in enumerate(pilot.BEATS)]
    cues = host_kit.caption_cues(lines, skip=(pilot.SIGN_OFF,))
    assert len(cues) == len(pilot.BEATS)  # one out for the sign-off, one in for the walking line
    look = host_kit.CAPTION_LOOK
    assert all(len(native.wrap(c.text, look.max_chars, look.max_words)) <= look.max_lines for c in cues)


def test_the_foley_lands_a_sound_on_each_beat_and_the_bed_is_music(tmp_path):
    beats, end = pilot.SKETCH.beats, pilot.SKETCH.end
    speech = [(b.start, b.start + kept) for b, kept in zip(beats, pilot.KEPT, strict=True)]
    rows = pilot.foley(beats, end, speech, tmp_path, pilot.SEED)
    assert [row["id"] for row in rows][:2] == ["bed", "mug"]
    assert {row.get("role", "effects") for row in rows} == set(narration.EFFECT_ROLES)
    assert all((tmp_path / row["audio"]).is_file() for row in rows)


def test_the_bed_is_silent_from_the_bread_to_the_good(tmp_path):
    beats, end = pilot.SKETCH.beats, pilot.SKETCH.end
    with wave.open(str(pilot.bed(tmp_path / "bed.wav", beats, end, pilot.SEED))) as clip:
        assert clip.getsampwidth() == 2
        step = clip.getnchannels()
        samples = array("h", clip.readframes(clip.getnframes()))[::step]
    fall, rise = (round(pilot.beat(name, beats).start * pilot.synth.RATE) for name in ("bread", "good"))
    assert any(samples[:fall]) and any(samples[rise:])
    assert not any(samples[fall:rise])


def test_the_post_asks_a_question_names_his_voice_and_stops_at_five_hashtags():
    assert isinstance(pilot.POST, InstagramPost) and pilot.POST.title.endswith("?")
    assert len(pilot.POST.hashtags) <= 5
    text = (FOLDER / "ig.txt").read_text(encoding="utf-8")
    assert text == pilot.POST.text()
    assert "An animated character; synthetic voice." in text.splitlines()
    assert "Voice: ElevenLabs premade Will." in text.splitlines()
    assert text.splitlines()[0].endswith("?") and len(re.findall(r"#\w+", text)) <= 5
    assert (FOLDER / "cover.jpg").stat().st_size > 0


def test_the_audio_script_carries_the_banner_and_the_pilot_stays_off_the_release_path():
    audio = (PILOTS / "unwritten_rules_how_are_you_audio.py").read_text(encoding="utf-8")
    for line in (
        "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.",
        "Absence of output verification is a design defect, not a runtime bug.",
        "All LLM output must be treated as untrusted and validated explicitly.",
    ):
        assert line in audio
    assert pilot.OUTPUT.startswith("renders/pilots/")
    assert not (ROOT / "episodes" / "releases" / f"{pilot.SLUG}.py").exists()
