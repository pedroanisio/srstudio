"""Caption orphans (srstudio.native): a cue whose last line would hold a lone short word is split, on request, into
balanced cues timed by their words; the house look keeps every shipped caption as it was."""

from __future__ import annotations

import pytest

from srstudio import native
from srstudio.native import CAPTION_LOOK, CaptionLook, NativeError
from srstudio.timeline import Take

ORPHAN = "They are shooting into it!"  # 26 characters: the engine breaks it "They are shooting into" / "it!"


def take(text: str, start: float = 2.0) -> Take:
    words = tuple({"text": w, "start": 0.1 + i * 0.3, "end": 0.35 + i * 0.3} for i, w in enumerate(text.split()))
    return Take("01", "juno", "", text, start, 0.4 + 0.3 * len(words), words=words)


def test_the_house_look_keeps_a_cue_with_a_lone_last_word_whole():
    assert native.wrap(ORPHAN, CAPTION_LOOK.max_chars) == ["They are shooting into", "it!"]
    (cue,) = native.cues_from_takes([take(ORPHAN)], CAPTION_LOOK)
    assert cue.text == ORPHAN


def test_min_last_splits_an_orphaned_cue_into_balanced_one_line_cues_timed_by_their_words():
    look = CaptionLook(min_last=2)
    first, second = native.cues_from_takes([take(ORPHAN)], look)
    assert (first.text, second.text) == ("They are shooting", "into it!")
    assert first.start == pytest.approx(2.1) and first.end == pytest.approx(2.0 + 0.35 + 0.6)
    assert second.start == pytest.approx(2.0 + 0.1 + 0.9) and second.end == pytest.approx(2.0 + 0.35 + 1.2)
    assert [w.text for w in first.words + second.words] == ORPHAN.split()
    for cue in (first, second):
        assert len(native.wrap(cue.text, look.max_chars)) == 1


@pytest.mark.parametrize("text", ["Fine. The biggest one.", "Skip it!", "Is this tonight?"])
def test_min_last_leaves_alone_a_cue_on_one_line_or_with_a_full_last_line(text):
    plain = native.cues_from_takes([take(text)], CAPTION_LOOK)
    assert [c.text for c in native.cues_from_takes([take(text)], CaptionLook(min_last=2))] == [c.text for c in plain]


def test_min_last_applies_to_every_cue_a_long_line_is_split_into():
    text = "The update also removed the jump drive and the coffee machine. For security reasons, it says."
    look = CaptionLook(min_last=2)
    cues = native.cues_from_takes([take(text)], look)
    assert " ".join(c.text for c in cues) == text
    for cue in cues:
        lines = native.wrap(cue.text, look.max_chars)
        assert len(lines) <= look.max_lines
        assert len(lines) == 1 or len(lines[-1].split()) >= 2


def test_an_orphaned_cue_without_word_timings_is_refused_not_guessed():
    bare = Take("01", "juno", "", ORPHAN, 0.0, 2.0)
    with pytest.raises(NativeError, match="word timings"):
        native.cues_from_takes([bare], CaptionLook(min_last=2))


@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_min_last_is_a_whole_number_of_at_least_one(value):
    with pytest.raises(NativeError, match="min_last"):
        CaptionLook(min_last=value)


def test_a_cue_no_split_can_free_of_orphans_is_kept_whole():
    look = CaptionLook(max_chars=9, max_lines=3, min_last=5)  # six words on three lines; halves hold two each
    (cue,) = native.cues_from_takes([take("aaaa bbbb cccc dddd eeee ffff")], look)
    assert cue.text == "aaaa bbbb cccc dddd eeee ffff"


def fast(text: str, step: float, start: float = 2.0, tail: float = 0.1) -> Take:
    words = tuple({"text": w, "start": i * step, "end": (i + 1) * step} for i, w in enumerate(text.split()))
    return Take("01", "juno", "", text, start, step * len(words) + tail, words=words)


def test_a_split_that_would_show_a_half_too_briefly_to_read_is_not_made():
    look = CaptionLook(min_last=2, min_seconds=0.84)
    (cue,) = native.cues_from_takes([fast(ORPHAN, 0.2)], look)  # each half would be up for 0.6 s at most
    assert cue.text == ORPHAN


@pytest.mark.parametrize(
    "text, halves",
    [
        ("Seven. Is the hole fixed?", ("Seven.", "Is the hole fixed?")),
        ("It's on the list, my lord.", ("It's on the list,", "my lord.")),
        ("They are shooting into it!", ("They are shooting", "into it!")),
        ("And I didn't report you, sir!", ("And I didn't", "report you, sir!")),
        ("Your annual review, Seven.", ("Your annual", "review, Seven.")),
    ],
)
def test_an_orphaned_cue_splits_after_punctuation_first_then_where_the_halves_balance_never_ending_on_a_lone_word(
    text, halves
):
    cues = native.cues_from_takes([take(text)], CaptionLook(min_last=2))
    assert tuple(c.text for c in cues) == halves


# -- holding a cue long enough to read ----------------------------------------------------------------------------
def test_the_house_look_shows_a_cue_only_while_its_words_are_spoken():
    (cue,) = native.cues_from_takes([take("Medium.")], CAPTION_LOOK)
    assert (cue.start, cue.end) == pytest.approx((2.1, 2.35))


def test_min_seconds_holds_a_short_cue_into_the_silence_after_it():
    (cue,) = native.cues_from_takes([fast("Medium.", 0.25, tail=1.0)], CaptionLook(min_seconds=0.84))
    assert (cue.start, cue.end) == pytest.approx((2.0, 2.84))
    assert [w.text for w in cue.words] == ["Medium."]


def test_the_hold_never_reaches_the_next_cue_or_past_its_own_take():
    look = CaptionLook(min_seconds=0.84)
    first, second = native.cues_from_takes([take("Medium."), take("Rare?", start=2.6)], look)
    assert first.end == pytest.approx(second.start)
    (last,) = native.cues_from_takes([fast("Gone.", 0.3, tail=0.2)], look)
    assert last.end == pytest.approx(2.5)  # the take ends at 2.5 s


def test_the_halves_of_a_split_cue_are_each_held_long_enough_to_read():
    look = CaptionLook(min_last=2, min_seconds=0.84)
    first, second = native.cues_from_takes([take(ORPHAN)], look)
    assert first.end <= second.start
    assert min(first.end - first.start, second.end - second.start) >= 0.84 - 1e-9


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf")])
def test_min_seconds_is_a_finite_number_of_seconds_from_zero(value):
    with pytest.raises(NativeError, match="min_seconds"):
        CaptionLook(min_seconds=value)


HOOK = "What is the worst way to find out who your father is?"  # 53 characters: more than two lines


@pytest.mark.parametrize(
    ("text", "tail", "look", "split"),
    [
        (HOOK, "is?", CaptionLook(min_last=2, min_seconds=0.84), ["What is the worst way",
                                                                  "to find out who your father is?"]),
        ("Enforcer of the year, for outstanding restraint.", "restraint.", CaptionLook(min_last=2),
         ["Enforcer of", "the year, for outstanding restraint."]),
    ],
)  # fmt: skip
def test_a_long_line_split_on_request_never_leaves_a_lone_word_as_its_last_cue(text, tail, look, split):
    plain = [c.text for c in native.cues_from_takes([take(text)], CAPTION_LOOK)]
    assert plain[-1] == tail  # the house look fills each cue greedily
    cues = native.cues_from_takes([take(text)], look)
    assert [c.text for c in cues] == split
    for cue in cues:
        lines = native.wrap(cue.text, look.max_chars)
        assert len(lines) <= look.max_lines and len(lines[-1].split()) >= 2 or len(lines) == 1
        assert cue.end - cue.start >= look.min_seconds


def test_the_tail_of_a_long_line_is_not_moved_when_no_better_split_can_be_shown_long_enough():
    look = CaptionLook(min_last=2, min_seconds=5.0)
    assert [c.text for c in native.cues_from_takes([take(HOOK)], look)][-1] == "is?"


def test_a_long_lines_greedy_split_stands_when_its_last_cue_is_already_readable():
    text = "Gary hit the exhaust port of the battle cube. From the inside. By accident."
    look = CaptionLook(min_last=2, min_seconds=0.84)
    slow = Take("01", "juno", "", text, 0.0, 12.0, words=tuple(
        {"text": w, "start": 0.1 + i * 0.6, "end": 0.5 + i * 0.6} for i, w in enumerate(text.split())))  # fmt: skip
    assert [c.text for c in native.cues_from_takes([slow], look)] == [
        "Gary hit the exhaust port of the battle cube.", "From the inside.", "By accident."]  # fmt: skip
