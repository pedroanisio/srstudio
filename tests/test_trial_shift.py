"""Trial Shift as data: the lines as decided, the real holds, the voices, and the holdout's post."""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "episodes"))

import pytest  # noqa: E402

from srstudio import cutout_arm  # noqa: E402
from srstudio.releases import load  # noqa: E402
from trial_shift_audio import (  # noqa: E402
    ARM,
    AT_DOOR,
    AVA_APART,
    AVA_HAND,
    AVA_REACH,
    AVA_SHOULDER,
    AVA_SIZE,
    BEHIND_HIM,
    CAPTION_LEAD,
    CAPTION_MIN,
    CAPTION_TAIL,
    CODE_LEFT,
    CUE,
    DOOR_RIGHT,
    GONE,
    HAND_RADIUS,
    HEAD_AT_CODE,
    HELD_OUT,
    HOOK,
    KEY_LEFT,
    LEAVES,
    MILO_JAW,
    MILO_RIGHT_HAND,
    MILO_RIGHT_SHOULDER,
    MILO_SIZE,
    MILO_X,
    MILO_Y,
    ON_AVA,
    OUT_OF_SIGHT,
    PASTRY_RIGHT,
    REST,
    SCRIPT,
    SHOULDER,
    THE_TAG,
    TRAY_HAND,
    TRAY_SIZE,
    TURNS,
    TURNS_FRAME,
    TWO,
    VOICES,
    WALKS_ON,
    cue_off,
    extra,
    schedule,
)


class Timing:
    def __init__(self, phrases):
        self.phrases = phrases


SECONDS = [1.2, 2.0, 1.0, 0.5, 0.9, 0.8, 1.4, 0.7, 1.4, 0.7, 0.4, 1.6]


def phrases() -> list[dict]:
    starts = schedule(SECONDS, {}).lines
    return [{"start": at, "end": at + seconds} for at, seconds in zip(starts, SECONDS, strict=True)]


def test_the_lines_are_the_script_in_order():
    assert [(s.role, s.text) for s in SCRIPT] == [
        ("milo", "How long have you worked here?"),
        ("ava", "I don't. It's just a quick trial shift."),
        ("milo", "When did it start?"),
        ("ava", "April."),
        ("milo", "That's not so bad."),
        ("ava", "2019."),
        ("candidate", "They'll let us know Friday."),
        ("milo", "Which Friday?"),
        ("milo", "Has anyone ever been hired?"),
        ("ava", "Of course!"),
        ("milo", "Who?"),
        ("milo", "It's just a quick trial shift."),
    ]


def test_the_callback_is_avas_own_words_in_his_mouth():
    assert SCRIPT[-1].text in SCRIPT[1].text


def test_three_published_voices():
    assert {role: v.name for role, v in VOICES.items()} == {"milo": "Liam", "ava": "Jessica", "candidate": "Will"}


def test_the_first_word_comes_by_half_a_second():
    assert phrases()[0]["start"] <= 0.5


def test_every_line_starts_late_enough_for_the_last_cue_to_hold():
    starts = [p["start"] for p in phrases()]
    assert all(b - a >= CUE - 1e-9 for a, b in zip(starts, starts[1:], strict=False))


def test_the_holds_are_real_holds_with_no_speech():
    p = phrases()
    assert p[6]["start"] - p[5]["end"] >= CAPTION_TAIL + BEHIND_HIM + THE_TAG + CAPTION_LEAD - 1e-9
    assert p[8]["start"] - p[7]["end"] >= TURNS - 1e-9
    assert p[11]["start"] - p[10]["end"] >= ON_AVA + 1.5


def test_each_shot_of_the_hold_outlasts_a_text_layers_shortest_span():
    assert BEHIND_HIM >= 0.84 and THE_TAG >= 0.84


def test_the_shots_of_the_hold_last_as_long_as_they_say():
    timing = extra(Timing(phrases()))
    by_angle = {c["angle"]: c["time"] for c in timing["camera_cuts"]}
    assert by_angle["tag"] - by_angle["behind"] == pytest.approx(BEHIND_HIM)
    assert by_angle["friday"] - by_angle["tag"] == pytest.approx(THE_TAG)


def test_no_caption_is_up_across_a_cut():
    p = phrases()
    cuts = [c["time"] for c in extra(Timing(p))["camera_cuts"]]
    for i, line in enumerate(p):
        on = line["start"] - CAPTION_LEAD
        off = cue_off(line)
        if i + 1 < len(p):
            off = min(off, p[i + 1]["start"] - CAPTION_LEAD)
        assert not [c for c in cuts if on + 1e-9 < c < off - 1e-9], f"line {i + 1} crosses a cut"


def test_a_short_word_keeps_its_cue_for_the_caption_minimum():
    assert cue_off({"start": 5.0, "end": 5.2}) == pytest.approx(5.0 - CAPTION_LEAD + CAPTION_MIN)


def _units(x, y):
    return (x - AT_DOOR) / MILO_SIZE, (y - MILO_Y) / MILO_SIZE


def test_the_hand_stays_clear_of_a_folded_elbow_on_its_way_to_the_hook_and_out():
    hook, held = _units(HOOK[0], HOOK[1] - 8), _units(*HELD_OUT)
    track = [(0.0, *REST), (0.16, *hook), (0.4, *held)]
    for k in range(41):
        hand = cutout_arm.hand_at(track, k / 100)
        _, elbow = cutout_arm.angles(SHOULDER, ARM, ARM, hand, -1)
        assert 180 - abs(elbow) >= 80, f"the elbow closes to {180 - abs(elbow):.0f} degrees at {k / 100} s"


def test_the_hook_line_leaves_the_prices_on_the_board():
    scale, x, _ = TWO
    assert scale * PASTRY_RIGHT + x < KEY_LEFT


def test_the_tray_clears_milos_jaw_while_the_candidate_walks_on():
    assert all(x + TRAY_SIZE * TRAY_HAND + HAND_RADIUS < MILO_X - MILO_JAW for x in WALKS_ON)


def test_the_candidate_walks_on_clear_of_the_boards_code_and_in_the_frame():
    scale, x, _ = TURNS_FRAME
    assert all(room + HEAD_AT_CODE <= CODE_LEFT and scale * room + x >= 60 for room in WALKS_ON)
    assert WALKS_ON[0] > WALKS_ON[1]  # he does not stop, and he goes the way he was going


def test_ava_stays_in_the_frame_of_the_turn():
    scale, x, _ = TURNS_FRAME
    assert scale * (AVA_APART + AVA_REACH + HAND_RADIUS) + x <= 1080


def test_the_candidate_has_gone_behind_the_door_before_milo_leaves_his_mark():
    beats = extra(Timing(phrases()))
    assert OUT_OF_SIGHT + TRAY_SIZE * TRAY_HAND + HAND_RADIUS <= DOOR_RIGHT
    assert beats["wide"] < beats["down"] - LEAVES < beats["crosses"] + GONE < beats["arrives"]


def _hanging(x, size, shoulder, hand, bend):
    """The room's x of an arm hanging at a figure's side: the elbow and the hand, the two that can touch."""
    aim, _ = cutout_arm.angles(shoulder, ARM, ARM, hand, bend)
    elbow = shoulder[0] + ARM * math.cos(math.radians(aim))
    return x + size * elbow, x + size * hand[0]


def test_the_arms_between_ava_and_milo_do_not_stack_once_he_turns_to_her():
    his = _hanging(MILO_X, MILO_SIZE, MILO_RIGHT_SHOULDER, MILO_RIGHT_HAND, 1)
    hers = _hanging(AVA_APART, AVA_SIZE, AVA_SHOULDER, AVA_HAND, -1)
    elbows, hands = hers[0] - his[0], hers[1] - his[1]
    assert elbows >= 16 and hands >= 2 * HAND_RADIUS


def test_the_cuts_rise_and_end_at_the_door():
    cuts = extra(Timing(phrases()))["camera_cuts"]
    times = [c["time"] for c in cuts]
    assert times == sorted(times) and len(set(times)) == len(times)
    assert [cuts[0]["angle"], cuts[-1]["angle"]] == ["open", "door"]


def test_the_tag_shot_comes_after_every_close_on_her_before_it():
    cuts = extra(Timing(phrases()))["camera_cuts"]
    angles = [c["angle"] for c in cuts]
    assert angles.index("tag") > angles.index("ava")


def test_the_holdout_has_no_recipient_no_send_line_and_no_length_arm():
    tags = _release().tags
    assert (tags.test, tags.arm) == ("sp-speakers", "b")
    assert not tags.also and not tags.send_to and not tags.send_line


def test_the_post_is_the_scripts_and_within_the_hashtag_cap():
    post = _release().post
    assert post.title == "Has anyone you know been hired after a trial shift?"
    assert len(post.hashtags) <= 5 and "#okayville" in post.hashtags


def test_both_scores_are_on_the_comedy_floor():
    comedy = _release().comedy
    assert (comedy.author, comedy.reviewer) == (17, 16)


def _release():
    return load(ROOT / "episodes" / "posts")["trial-shift"]
