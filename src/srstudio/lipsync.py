"""Lip sync: mouth poses from what is said, when it is said and how loud.

Two drivers share one reading of the letters (:func:`letter_poses`):

- :func:`phoneme_states` samples character timestamps (an aligned take: ``{c, start, end}`` relative to the take)
  at the style's rate, for the drawn styles (Ink, Stick, the Toon sketches). Its improvements are opt-in fields of
  :class:`~srstudio.soundtrack.PhonemeStyle`, all on in :data:`SPEECH_MOUTH`:

  - ``spelling`` reads English spelling, not single letters: *ph* is an f, the *h* of *th*, *sh*, *ch* and *wh* holds
    the consonant, *w* and *qu* round the lips, a silent
    final *e* (*come*, *make*) and a silent *gh* (*light*) hold the pose before them;
  - ``close_bilabials``: every *b*, *m* and *p* closes the mouth on the sample nearest it, so a quick bilabial that
    falls between two samples is never lost (a scream stays open);
  - ``lead``: the mouth shows each sound this many seconds early, as animators lead the track;
  - ``min_rest``: a pause between two letters shorter than this keeps the pose before it instead of snapping shut.

  With the fields at their defaults the samples are the ones the shipped packages were built from
  (:data:`~srstudio.soundtrack.INK_MOUTH` reproduces the Ink package sample for sample).
- :func:`letter_track` guides an amplitude mouth (:class:`~srstudio.soundtrack.MouthStyle` with ``letters=True``)
  that has a line's text but no timestamps: the letters are spread in order over the frames where the line is
  voiced, vowels weighing twice a consonant, and pick round, closed or open; the amplitude still picks how open.

:func:`score` measures a style over aligned takes (closed bilabials, word joins snapped shut, pose changes a
second); ``srstudio lipsync TIMELINE...`` prints it for the shipped and the speech mouth.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .soundtrack import PhonemeStyle

SPEECH_MOUTH = PhonemeStyle(spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VOWELS = "aeiouy"
_HOLD = "hold"  # a silent letter: the pose before it


def _plain(ch: str, style: PhonemeStyle) -> str | None:
    """The pose of one lowercased character (or a multi-character token) as the shipped sampler read it."""
    if not ch.isalpha():
        return None
    if ch in style.round_letters:
        return "round"
    if ch in style.open_letters:
        return "open"
    if ch in style.closed_letters:
        return "closed"
    return "teeth"


def _respell(word: str, poses: list[str | None]) -> None:
    """English spelling over one word's letters, in place."""
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in "wq":
            poses[i] = "round"
        elif ch == "p" and nxt == "h":
            poses[i] = "teeth"
        elif ch == "g" and nxt == "h":
            poses[i] = poses[i + 1] = _HOLD
        elif ch == "h" and i and word[i - 1] not in VOWELS and poses[i] != _HOLD:
            poses[i] = _HOLD  # th, sh, ch, ph, wh: the h is part of the consonant
    if len(word) >= 4 and word[-1] == "e" and word[-2] not in VOWELS and word[-3] in VOWELS:
        poses[-1] = _HOLD
    for i, pose in enumerate(poses):
        if pose == _HOLD:
            poses[i] = poses[i - 1] if i else "teeth"


def letter_poses(text: Sequence[str], style: PhonemeStyle) -> list[str | None]:
    """The pose of each character of ``text`` (a string, or the tokens of a take); None between words."""
    low = [c.lower() for c in text]
    out = [_plain(c, style) for c in low]
    if style.spelling:
        i = 0
        while i < len(low):
            if len(low[i]) == 1 and low[i].isalpha():
                j = i
                while j < len(low) and len(low[j]) == 1 and low[j].isalpha():
                    j += 1
                word = out[i:j]
                _respell("".join(low[i:j]), word)
                out[i:j] = word
                i = j
            else:
                i += 1
    return out


def _moody(pose: str, mood: str, style: PhonemeStyle) -> str:
    if mood in style.scream_moods:
        return "shout"
    if pose == "open" and mood in style.angry_moods:
        return "shout"
    return pose


def phoneme_states(
    phones: Sequence[dict], duration: float, mood: str = "", style: PhonemeStyle | None = None
) -> list[tuple[float, str]]:
    """``(time, pose)`` samples every ``1 / style.rate`` s from 0 to ``duration`` (the last one at ``duration``)
    from character timestamps ``{c, start, end}`` relative to the take; the mouth is closed between words."""
    from .soundtrack import INK_MOUTH

    style = style or INK_MOUTH
    poses = letter_poses([z["c"] for z in phones], style)
    letters = [(z["start"], z["end"], p) for z, p in zip(phones, poses, strict=True) if p is not None]

    def pose_at(u: float) -> str:
        k = next((k for k, z in enumerate(phones) if z["start"] <= u < z["end"]), None)
        here = poses[k] if k is not None else None
        if here is not None:
            return _moody(here, mood, style)
        if style.min_rest > 0:
            before = [x for x in letters if x[1] <= u]
            after = [x for x in letters if x[0] > u]
            if before and after:
                last = max(before, key=lambda x: x[1])
                if min(x[0] for x in after) - last[1] < style.min_rest:
                    return _moody(last[2], mood, style)
        return "closed"

    count = math.ceil(duration * style.rate) + 1
    out = [(t, pose_at(t + style.lead)) for t in (min(duration, j / style.rate) for j in range(count))]
    if style.close_bilabials and mood not in style.scream_moods:
        for z, pose in zip(phones, poses, strict=True):
            if pose == "closed" and z["c"].lower() in style.closed_letters:
                j = round(((z["start"] + z["end"]) / 2 - style.lead) * style.rate)
                j = min(max(j, 0), count - 1)
                out[j] = (out[j][0], "closed")
    return out


def letter_track(text: str, frames: int) -> list[str]:
    """The pose of each of ``frames`` voiced frames of a line: its letters in order, a vowel weighing twice a
    consonant; ``closed`` for a bilabial, ``round``, ``open`` or ``teeth`` otherwise. Empty for a line without
    letters."""
    pairs = [(p, c.lower()) for p, c in zip(letter_poses(text, SPEECH_MOUTH), text, strict=True) if p is not None]
    if not pairs or frames <= 0:
        return []
    poses = [p for p, _ in pairs]
    weights = [2.0 if c in VOWELS else 1.0 for _, c in pairs]
    total = sum(weights)
    out, k, edge = [], 0, weights[0]
    for f in range(frames):
        u = (f + 0.5) / frames * total
        while u > edge and k + 1 < len(poses):
            k += 1
            edge += weights[k]
        out.append(poses[k])
    return out


# -- scoring --------------------------------------------------------------------------------------------------------
JOIN = 0.12  # a pause shorter than this between two letters joins words said in one breath


@dataclass(frozen=True)
class Score:
    """How a mouth style reads a set of takes: bilabials (not in a scream, not the *p* of *ph*) and how many
    show a closed mouth within half a sample of the sound; joins between words and how many snap the mouth shut;
    pose changes over the seconds sampled."""

    seconds: float
    bilabials: int
    closed_bilabials: int
    joins: int
    snapped_joins: int
    changes: int

    @property
    def changes_per_second(self) -> float:
        return self.changes / self.seconds

    def summary(self) -> str:
        return (
            f"{self.closed_bilabials}/{self.bilabials} bilabials closed, "
            f"{self.snapped_joins}/{self.joins} word joins snapped shut, "
            f"{self.changes_per_second:.2f} pose changes/s over {self.seconds:.1f} s"
        )


def score(takes: Iterable[tuple[Sequence[dict], float, str]], style: PhonemeStyle) -> Score:
    """Score ``style`` over ``takes``: ``(phones, duration, mood)`` each, as :func:`phoneme_states` reads them."""
    takes = list(takes)
    if not takes:
        raise ValueError("score needs takes with character timestamps, got none")
    seconds, bilabials, closed, joins, snapped, changes = 0.0, 0, 0, 0, 0, 0
    half = 0.5 / style.rate
    for phones, duration, mood in takes:
        states = phoneme_states(phones, duration, mood, style)
        seconds += duration
        changes += sum(1 for a, b in zip(states, states[1:], strict=False) if a[1] != b[1])
        chars = [z["c"].lower() for z in phones]
        for k, z in enumerate(phones):
            c = chars[k]
            if (
                c in ("b", "m", "p")
                and not (c == "p" and chars[k + 1 : k + 2] == ["h"])
                and mood not in style.scream_moods
            ):
                bilabials += 1
                a, b = z["start"] - style.lead - half, z["end"] - style.lead + half
                closed += any(p == "closed" and a <= t <= b for t, p in states)
        letters = [z for z, c in zip(phones, chars, strict=True) if c.isalpha()]
        for x, y in zip(letters, letters[1:], strict=False):
            if 0 < y["start"] - x["end"] < JOIN:
                joins += 1
                snapped += any(p == "closed" and x["end"] <= t + style.lead < y["start"] for t, p in states)
    return Score(seconds, bilabials, closed, joins, snapped, changes)
