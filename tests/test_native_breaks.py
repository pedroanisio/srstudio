"""Cue cuts that keep phrases whole (ADR 0173): with ``CaptionLook(keep_together=True)`` no cue ends after a weak
word, inside a number or inside a name while another cut fits, a moved cut lands on a sentence end when the cue holds
one (rule 7, ADR 0149), and the default look cuts exactly as before."""

from __future__ import annotations

import pytest

from srstudio import breaks, native
from srstudio.native import CaptionLook, NativeError
from srstudio.timeline import Take


def take(text: str) -> Take:
    words = tuple({"text": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(text.split()))
    return Take("01", "narrator", "", text, 0.0, len(words) * 0.3 + 1.0, words=words)


def cut(text: str, **look: object) -> list[str]:
    return [c.text for c in native.cues_from_takes([take(text)], CaptionLook(**look))]  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "look", "before", "after"),
    [
        (
            "We moved the meeting to the big room today.",
            {"max_chars": 12, "max_lines": 1},
            ["We moved the", "meeting to", "the big room", "today."],
            ["We moved", "the meeting", "to the big", "room today."],
        ),
        (
            "It costs twenty thousand dollars a year now.",
            {"max_chars": 16, "max_lines": 1},
            ["It costs twenty", "thousand dollars", "a year now."],
            ["It costs", "twenty thousand", "dollars a year", "now."],
        ),
        (
            "They flew to New York on Monday.",
            {"max_chars": 12, "max_lines": 1},
            ["They flew to", "New York on", "Monday."],
            ["They flew", "to New York", "on Monday."],
        ),
    ],
)
def test_a_cue_never_ends_after_a_weak_word_inside_a_number_or_inside_a_name_while_another_cut_fits(
    text, look, before, after
):
    assert cut(text, **look) == before
    assert cut(text, keep_together=True, **look) == after
    assert " ".join(after) == text


def test_a_moved_cut_lands_on_the_sentence_end_the_cue_holds():
    look = {"max_chars": 24, "max_lines": 1}
    assert cut("Fine. We moved the meeting to Friday.", **look) == ["Fine. We moved the", "meeting to Friday."]
    assert cut("Fine. We moved the meeting to Friday.", keep_together=True, **look) == [
        "Fine.",
        "We moved the meeting",
        "to Friday.",
    ]


def test_the_forbidden_cut_is_kept_when_nothing_else_fits():
    assert cut("the the the", keep_together=True, max_chars=3, max_lines=1) == ["the", "the", "the"]


def test_the_orphan_split_prefers_an_allowed_cut():
    look = {"max_chars": 24, "max_lines": 2, "min_last": 2}
    text = "You said the deadline was Friday at noon and then you left"
    assert cut(text, **look) == ["You said the deadline was Friday at noon and", "then you left"]
    assert cut(text, keep_together=True, **look) == ["You said the deadline was Friday at noon", "and then you left"]


TEXTS = [
    "Why are the walls of this trash compactor closing in on us today?",
    "Okay. Come on. Come on! We are late for the twenty past nine train to New York.",
    "I asked for one in ten. You gave me three times in ten, and a memo about it.",
    "Stop the walls!",
]


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("lines", [1, 2])
def test_every_word_stays_once_in_order_and_each_cue_fits(text, lines):
    look = CaptionLook(max_chars=18, max_lines=lines, keep_together=True)
    cues = native.cues_from_takes([take(text)], look)
    assert " ".join(c.text for c in cues) == text
    assert all(len(native.wrap(c.text, look.max_chars)) <= look.max_lines for c in cues)
    assert all(a.end <= b.start for a, b in zip(cues, cues[1:], strict=False))


def _forbidden_cuts(cues: list[str]) -> int:
    words = " ".join(cues).split()
    places, at, count = breaks.kept_together(words), 0, 0
    for cue in cues[:-1]:
        at += len(cue.split())
        count += at in places
    return count


def _broken_off(cues: list[str]) -> int:
    """Rule 7's second fault, by its one definition: a cue that keeps a sentence end and stops inside the next one."""
    return sum(
        breaks.breaks_off([breaks.ends_sentence(w) for w in c.split()], closed=breaks.closes(c.split()[-1]))
        for c in cues
    )


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("chars", [10, 14, 18, 24])
def test_keeping_phrases_together_adds_no_forbidden_cut_and_no_rule_7_fault(text, chars):
    plain = cut(text, max_chars=chars, max_lines=1)
    kept = cut(text, max_chars=chars, max_lines=1, keep_together=True)
    assert _forbidden_cuts(kept) <= _forbidden_cuts(plain)
    assert _broken_off(kept) <= _broken_off(plain)


def test_the_rule_is_opt_in_so_a_rebuilt_published_reel_cuts_as_it_did():
    """A published reel's rebuild must stay byte-identical, so no shipped look changes: a new reel sets the option."""
    assert CaptionLook().keep_together is False and native.CAPTION_LOOK.keep_together is False


def test_keep_together_is_a_boolean():
    with pytest.raises(NativeError, match="keep_together"):
        CaptionLook(keep_together=1)  # type: ignore[arg-type]
