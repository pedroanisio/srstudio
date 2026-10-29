"""One spoken take cut at its word boundaries and placed phrase by phrase on the captions it was written for.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A take of a whole sentence has its own pace; captions timed from a reference have another. Played as one clip, the
words drift off their captions. :func:`place_phrases` uses the provider's word alignment (already parsed and
checked by :mod:`srstudio.voice`) to cut the take into the captions' phrases and put each phrase's first word on
its caption. A phrase that is too long for its window plays up to :data:`TEMPO_MAX` faster (pitch kept), and only
what that leaves over starts early, by at most :data:`LEAD_MAX`; the last phrase of a run may spill :data:`SPILL`
past its caption. What still does not fit raises :class:`PhrasingError`: a phrase is never cut. The captions must
spell the take word for word, or the alignment belongs to some other line.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .voice import Alignment, normalize_words

PRE, POST = 0.03, 0.06  # breath kept before a phrase's first word and after its last
LEAD_MAX = 0.20
TEMPO_MAX = 1.15
SPILL = 0.20
GUARD = 0.02  # silence kept between a phrase and the one before it
JOIN = 0.05  # captions closer than this are one run of speech


class PhrasingError(ValueError):
    """The take cannot be placed on the captions without cutting or mis-attributing a word."""


@dataclass(frozen=True)
class Cue:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Phrase:
    """``clip_in..clip_out`` of the take, played ``tempo`` times faster from ``start``; its first word is heard
    ``lead_in / tempo`` after ``start``, which is ``lead`` before its caption."""

    text: str
    clip_in: float
    clip_out: float
    lead_in: float
    start: float
    tempo: float
    lead: float

    @property
    def end(self) -> float:
        return self.start + (self.clip_out - self.clip_in) / self.tempo


Word = tuple[str, float, float]


def words_of(alignment: Alignment) -> list[Word]:
    """The take's words with the start of their first character and the end of their last."""
    out: list[Word] = []
    text, start, end = "", 0.0, 0.0
    for ch, a, b in zip(alignment.characters, alignment.starts, alignment.ends, strict=True):
        if ch.isspace():
            if text:
                out.append((text, start, end))
            text = ""
            continue
        if not text:
            start = a
        text += ch
        end = b
    if text:
        out.append((text, start, end))
    return out


def _split(words: Sequence[Word], cues: Sequence[Cue]) -> list[tuple[Word, Word]]:
    """The first and last take word of each cue; the cues must spell the take exactly."""
    tokens = [(tok, i) for i, w in enumerate(words) for tok in normalize_words(w[0])]
    spans, at = [], 0
    for cue in cues:
        want = normalize_words(cue.text)
        got = [t for t, _ in tokens[at : at + len(want)]]
        if not want or got != want:
            raise PhrasingError(f"caption {cue.text!r} does not match the take there ({' '.join(got)!r})")
        spans.append((words[tokens[at][1]], words[tokens[at + len(want) - 1][1]]))
        at += len(want)
    if at != len(tokens):
        rest = " ".join(t for t, _ in tokens[at:])
        raise PhrasingError(f"the take says {rest!r} after the last caption")
    return spans


def place_phrases(
    words: Sequence[Word],
    cues: Sequence[Cue],
    *,
    lead_max: float = LEAD_MAX,
    tempo_max: float = TEMPO_MAX,
    spill: float = SPILL,
) -> list[Phrase]:
    """Each cue's phrase of the take, its first word on the cue; quickened, then led by at most ``lead_max``."""
    spans = _split(words, cues)
    out: list[Phrase] = []
    prev_end = -1.0
    for i, (cue, (first, last)) in enumerate(zip(cues, spans, strict=True)):
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        joined = nxt is not None and nxt.start - cue.end <= JOIN
        window_end = nxt.start if joined and nxt is not None else cue.end + spill
        clip_in = max(0.0, first[1] - PRE, spans[i - 1][1][2] + 0.005 if i else 0.0)
        clip_out = last[2] + POST
        if i + 1 < len(spans):
            clip_out = min(clip_out, spans[i + 1][0][1] - 0.005)
        length, lead_in = clip_out - clip_in, first[1] - clip_in
        start = cue.start - lead_in
        lead, tempo = 0.0, 1.0
        if start + length > window_end + 1e-9:  # quickened first: a lead moves the first word off its caption
            body = length - lead_in
            tempo = max(1.0, min(tempo_max, body / (window_end - cue.start)))
            lead = max(0.0, cue.start + body / tempo - window_end)
            room = min(lead_max, max(0.0, cue.start - prev_end - GUARD))
            if lead > room + 1e-9:
                raise PhrasingError(
                    f"{cue.text!r}: {body:.2f} s of speech at x{tempo:.2f} starts {lead:.2f} s early"
                    f" to end by {window_end:.2f} s (at most {room:.2f} s allowed)"
                )
            start = cue.start - lead - lead_in / tempo
        overlap = prev_end - start
        if overlap > 1e-9:  # the breath before the first word goes first; the word itself never does
            if overlap * tempo > lead_in + 1e-9:
                raise PhrasingError(f"{cue.text!r} would start {overlap:.3f} s before the phrase before it ends")
            clip_in, lead_in, start = clip_in + overlap * tempo, lead_in - overlap * tempo, prev_end
        phrase = Phrase(cue.text, round(clip_in, 6), round(clip_out, 6), round(lead_in, 6), start, tempo, lead)
        out.append(phrase)
        prev_end = phrase.end
    return out
