"""The Unwritten Rules as a format: a script keeps the show's rules or is refused, and the shared sounds land."""

from __future__ import annotations

from dataclasses import replace

import pytest

from srstudio import host_kit, rafa_show
from srstudio.rafa_show import Beat, ScriptError, Show
from srstudio.social import InstagramPost

SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
MUG, PHONE, FOLDER = "rafa-mug", "rafa-phone", "rafa-bills"
WORDS = "ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT"
BEATS = (
    Beat("hook", "Nobody tells you a fork has rules.", SMILE, MUG, label="A FORK HAS RULES"),
    Beat("one", "Rule one. You use the fork.", SMILE, MUG, label="RULE 1"),
    Beat("two", "Rule two. You use the other fork.", SMILE, PHONE, label="RULE 2"),
    Beat("three", "Rule three. The one nobody admits.", BATTERY, FOLDER, label="RULE 3"),
    Beat("nobody", "Nobody knows which fork is which.", BATTERY, FOLDER, "close", hold=1.4),
    Beat("break", "I used a spoon.", MELTDOWN, MUG, "tight", hold=0.5),
    Beat("soup", "It was not soup.", MELTDOWN, MUG, hold=4.0),
    Beat("fine", "Fine.", SMILE, MUG, hold=0.7),
    Beat("off", rafa_show.SIGN_OFF, SMILE, MUG),
)
SHOW = Show(
    "fork", 9, "A fork has rules", "Rafa and a fork.", "A man talks about forks.", BEATS,
    (2.0, 2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 0.8, 1.3), InstagramPost(title="Which fork?", description="d"), stop="break",
)  # fmt: skip


def test_a_script_that_keeps_the_format_is_valid_and_its_sketch_is_timed_from_the_takes():
    SHOW.validate()
    SHOW.validate_sketch()
    assert len(SHOW.sketch.beats) == len(BEATS)
    assert SHOW.starts()[0] == 0.0
    assert SHOW.starts()[1] == pytest.approx(2.0 + rafa_show.GAP)


def test_rafa_speaks_in_the_voice_the_operator_chose():
    assert rafa_show.HOST == "rafa"
    assert rafa_show.SPEAKER.voice.id == "bIHbv24MWmeRgasZH58o"
    assert rafa_show.SEED == 52026


def test_the_shared_sounds_are_the_room_and_what_lands_on_each_rule(tmp_path):
    beats, end = SHOW.sketch.beats, SHOW.sketch.end
    speech = [(b.start, b.start + kept) for b, kept in zip(beats, SHOW.kept, strict=True)]
    rows = rafa_show.shared_sounds(SHOW, beats, end, speech, tmp_path, rafa_show.SEED)
    assert [row["id"] for row in rows] == ["room", "mug", "buzz", "folder"]
    assert rows[0]["gain_db"] == rafa_show.ROOM_GAIN
    assert all((tmp_path / row["audio"]).is_file() for row in rows)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("mood", "calm", "moods"),
        ("prop", "rafa-toaster", "props"),
        ("insert", "rafa-toaster", "props"),
        ("framing", "wide", "framing"),
        ("hold", -1.0, "hold"),
        ("label", WORDS, "seven"),
    ],
)
def test_a_beat_the_show_cannot_stage_is_refused(field, value, match):
    show = SHOW
    with pytest.raises(ScriptError, match=match):
        show.validate((replace(show.beats[0], **{field: value}), *show.beats[1:]))


@pytest.mark.parametrize(
    ("drop", "match"),
    [
        (lambda b: b[1:], "opens"),
        (lambda b: b[:-1], "sign-off"),
        (lambda b: tuple(replace(x, hold=0.0) for x in b), "1.2"),
        (lambda b: tuple(replace(x, label="") for x in b), "three rules"),
        (lambda b: tuple(replace(x, hold=x.hold + 3.0) for x in b), "30"),
    ],
)
def test_a_script_that_drops_a_show_rule_is_refused(drop, match):
    show = SHOW
    with pytest.raises(ScriptError, match=match):
        show.validate(drop(show.beats))


def test_engagement_bait_is_refused():
    show = SHOW
    with pytest.raises(host_kit.HostKitError):
        show.validate((replace(show.beats[0], line="Nobody tells you to follow for more."), *show.beats[1:]))


def test_a_sketch_that_does_not_match_the_script_is_refused():
    show = SHOW
    sk = show.sketch
    with pytest.raises(ScriptError, match="beats"):
        show.validate_sketch(replace(sk, beats=sk.beats[:-1], lines=sk.lines[:-1]))
