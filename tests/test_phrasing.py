"""``srstudio.phrasing``: one spoken take cut at its word boundaries and placed phrase by phrase on the captions."""

import pytest

from srstudio import phrasing as ph
from srstudio.voice import Alignment

WORDS = [  # (text, start, end) in the take, as ElevenLabs aligns them
    ("Let", 0.00, 0.14),
    ("me", 0.16, 0.21),
    ("just", 0.23, 0.33),
    ("check", 0.35, 0.46),
    ("with", 0.49, 0.58),
    ("my", 0.60, 0.66),
    ("team", 0.72, 0.91),
    ("real", 0.95, 1.06),
    ("quick", 1.10, 1.24),
    ("and", 1.28, 1.42),
    ("get", 1.56, 1.68),
    ("back", 1.73, 1.87),
    ("to", 1.90, 1.95),
    ("you.", 2.02, 2.42),
]
CUES = [
    ph.Cue("let me just", 0.0, 0.5),
    ph.Cue("check with my team", 0.5, 1.0),
    ph.Cue("real quick", 1.0, 1.6667),
    ph.Cue("and get back to you", 1.6667, 2.4167),
]


def test_each_phrase_starts_on_its_caption_and_never_overlaps_the_next():
    phrases = ph.place_phrases(WORDS, CUES)
    assert [p.text for p in phrases] == [c.text for c in CUES]
    for p, cue, nxt in zip(phrases, CUES, CUES[1:] + [None], strict=True):
        onset = p.start + p.lead_in / p.tempo  # where the first word is heard
        assert onset + p.lead == pytest.approx(cue.start, abs=1e-6) and 0 <= p.lead <= ph.LEAD_MAX
        assert p.tempo <= ph.TEMPO_MAX + 1e-9
        if nxt is not None:
            assert p.end <= nxt.start + 1e-6
    for p, q in zip(phrases, phrases[1:], strict=False):
        assert q.start >= p.end - 1e-9  # one phrase at a time
    assert phrases[0].tempo == 1.0 and phrases[0].lead == 0.0  # 'let me just' fits as spoken
    assert phrases[3].tempo > 1.0  # 'and get back to you' is quickened into its window and the spill
    assert phrases[3].end <= CUES[3].end + ph.SPILL + 1e-6


def test_a_phrase_never_contains_the_next_word():
    phrases = ph.place_phrases(WORDS, CUES)
    starts = {"check": 0.35, "real": 0.95, "and": 1.28}
    for p, nxt in zip(phrases, ["check", "real", "and"], strict=False):
        assert p.clip_out < starts[nxt]


def test_a_phrase_that_cannot_fit_is_refused_not_cut():
    with pytest.raises(ph.PhrasingError, match="and get back to you"):
        ph.place_phrases(WORDS, CUES[:3] + [ph.Cue("and get back to you", 1.6667, 1.9)])


@pytest.mark.parametrize(
    "cues",
    [
        [ph.Cue("let me trust", 0.0, 0.5)] + CUES[1:],  # a word the take does not say
        CUES[:3],  # the take says more than the captions
        CUES + [ph.Cue("again", 2.5, 3.0)],  # the captions say more than the take
    ],
)
def test_captions_must_spell_the_take(cues):
    with pytest.raises(ph.PhrasingError, match="take"):
        ph.place_phrases(WORDS, cues)


def test_words_come_from_the_alignment():
    text = "Hi there."
    starts = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    ends = [s + 0.1 for s in starts]
    alignment = Alignment(tuple(text), tuple(starts), tuple(ends))
    assert ph.words_of(alignment) == [("Hi", 0.0, 0.2), ("there.", 0.3, 0.9)]


def test_a_phrase_is_quickened_before_it_is_moved_off_its_caption():
    # 'and get back to you' is 1.20 s of speech in 0.95 s of window: x1.15 alone leaves it 0.09 s long
    phrases = ph.place_phrases(WORDS, CUES)
    assert phrases[3].tempo == pytest.approx(ph.TEMPO_MAX)
    assert 0 < phrases[3].lead < 0.1  # only what the full speed-up leaves over
    # with a wider window the speed-up alone fits, and the first word stays on its caption
    roomy = ph.place_phrases(WORDS, CUES, spill=0.30)
    assert roomy[3].lead == 0.0 and 1.0 < roomy[3].tempo <= ph.TEMPO_MAX
    assert roomy[3].end == pytest.approx(CUES[3].end + 0.30, abs=1e-3)


def test_the_lead_is_bounded_by_the_phrase_before():
    # 'real quick' is heard until about 1.33 s, so 'and get back to you' cannot start 0.44 s before 1.40 s
    tight = CUES[:2] + [ph.Cue("real quick", 1.0, 1.40), ph.Cue("and get back to you", 1.40, 2.0)]
    with pytest.raises(ph.PhrasingError, match="and get back to you.*allowed"):
        ph.place_phrases(WORDS, tight, spill=0.0, lead_max=0.5)
