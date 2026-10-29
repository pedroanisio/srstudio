"""Anonymous Employee Survey — the reel as data: what is said, what is captioned, how the cat looks, and when.

The reference is a 63 s portrait reel (the.nope.cat): a blue cat at a laptop answers an "anonymous" survey out
loud while its captions appear one phrase at a time in a white pill. ``SEGMENTS`` lists every change of caption
or expression at its reference time; ``SENTENCES`` is what the narrator records, one request each, and each
segment that is spoken names the sentence and the word it starts on, so the narrated build can move the
caption and the expression to where the narrator actually says that word (:func:`place_segments`).

Everything here is plain data with typed derivations; ``employee_survey.py`` draws it and
``employee_survey_audio.py`` records it. Nothing is read from the reference recording at build time.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from srstudio import fonts
from srstudio.fonts import GoogleFont

END = 63.125  # where the reference loops, seconds
MIN_STEP = 0.15  # the least a segment may be held, seconds
BLANK_GAP = 0.25  # a silent beat starts this long after the line before it ends
BLANK_MARGIN = 0.30  # and this long before the next spoken segment at the latest
CAPTION_MIN = 0.85  # a caption is held at least this long when the next change can wait for it
CAPTION_LAG = 0.45  # the most a change is held back from its word to give the caption before it that time
FLASH = 0.125  # the camera flash, seconds
# sentences the survey interrupts: cut after these many letters of this word
CUTS: dict[int, tuple[str, int]] = {8: ("feedback", 4), 14: ("sit", 1)}

SENTENCES: tuple[str, ...] = (
    "Anonymous employee survey.",
    "Let's get into it.",
    "Would you recommend working for this company?",
    "Not a chance in hell.",
    "What do you love most about working here?",
    "Payday.",
    "Are you happy here?",
    "I'm here.",
    "Do you have any feedback?",
    "Do I?",
    "Everyone is stupid.",
    "Including those who have hired the stupids.",
    "Write a brief description of your department... job title... age... start date... employee number?",
    "That's... I don't think that's how that works.",
    "On the office layout below, mark an X where you sit.",
    "What?",
    "This number below is your IP address. Is that correct?",
    "How... first of all, how do I know? I don't...",
    "Hey... what?",
    "Thank you for submitting your 100% anonymous...",
    "Well, my days here are certainly numbered.",
)


@dataclass(frozen=True)
class Segment:
    """One held picture: the caption (empty for none) and the cat's pose from ``start`` until the next segment.
    ``sentence``/``word`` name the spoken word the segment starts on; ``flash`` is the laptop's camera firing."""

    start: float
    caption: str
    eyes: str
    mouth: str
    arms: str
    sentence: int | None = None
    word: int | None = None
    flash: bool = False

    @property
    def spoken(self) -> bool:
        return self.sentence is not None


def _s(start, caption, eyes, mouth, arms, sentence=None, word=None, flash=False) -> Segment:
    return Segment(start, caption, eyes, mouth, arms, sentence, word, flash)


SEGMENTS: tuple[Segment, ...] = (
    _s(0.000, "Anonymous Employee Survey", "wide", "open", "desk", 0, 0),
    _s(1.750, "Let's get into it", "half", "flat", "desk", 1, 0),
    _s(3.250, "Would you recommend", "half", "round", "desk", 2, 0),
    _s(4.250, "working for this company?", "half", "flat", "desk", 2, 3),
    _s(5.000, "working for this company?", "half", "flat", "type"),
    _s(6.375, "Not a chance", "half", "round", "type", 3, 0),
    _s(7.875, "in hell", "closed", "flat", "desk", 3, 3),
    _s(8.750, "What do you love most", "half", "flat", "desk", 4, 0),
    _s(9.750, "about working here?", "half", "flat", "desk", 4, 5),
    _s(10.800, "about working here?", "side", "smirk", "lean"),
    _s(11.750, "about working here?", "half", "grin", "desk"),
    _s(12.625, "Payday", "half", "grin", "crossed", 5, 0),
    _s(14.000, "Are you happy here?", "wide", "open", "desk", 6, 0),
    _s(15.500, "Are you happy here?", "half", "flat", "desk"),
    _s(17.375, "I'm here", "left", "flat", "desk", 7, 0),
    _s(19.125, "Do you have any feed...", "half", "flat", "desk", 8, 0),
    _s(20.750, "", "closed", "drop", "sigh"),
    _s(21.750, "Do I?", "half", "flat", "crossed", 9, 0),
    _s(22.875, "Everyone is stupid", "half", "flat", "type", 10, 0),
    _s(25.875, "including those who have", "half", "flat", "type", 11, 0),
    _s(28.250, "hired the stupids", "half", "o", "desk", 11, 4),
    _s(30.750, "Write a brief description of", "half", "flat", "desk", 12, 0),
    _s(32.125, "your department", "half", "flat", "desk", 12, 5),
    _s(32.750, "job title", "half", "flat", "desk", 12, 7),
    _s(34.000, "age", "wide", "o", "desk", 12, 9),
    _s(35.000, "start date", "wide", "o", "desk", 12, 10),
    _s(36.625, "employee number?", "shock", "o", "desk", 12, 12),
    _s(37.625, "That's", "half", "flat", "desk", 13, 0),
    _s(38.625, "I don't think that's", "half", "open", "desk", 13, 1),
    _s(39.500, "how that works", "half", "flat", "desk", 13, 5),
    _s(40.500, "On the office layout below", "half", "flat", "desk", 14, 0),
    _s(42.125, "mark an x where you s...", "half", "o", "desk", 14, 5),
    _s(43.600, "mark an x where you s...", "left", "o", "desk"),
    _s(44.625, "", "up", "round", "desk"),
    _s(45.400, "", "up", "round", "desk", 15, 0),
    _s(46.625, "This number below", "half", "wave", "desk", 16, 0),
    _s(47.750, "is your ip address", "half", "flat", "desk", 16, 3),
    _s(49.125, "is that correct?", "half", "flat", "desk", 16, 7),
    _s(50.250, "", "narrow", "o", "desk", 17, 0),
    _s(51.125, "First of all", "half", "o", "desk", 17, 1),
    _s(51.750, "i don't...", "half", "o", "desk", 17, 8),
    _s(52.375, "", "half", "o", "desk"),
    _s(53.000, "", "shock", "wave", "desk", None, None, True),
    _s(53.750, "Hey!", "closed", "none", "face", 18, 0),
    _s(54.500, "what...", "closed", "none", "face2", 18, 1),
    _s(55.625, "", "half", "flat", "desk"),
    _s(56.500, "Thank you for submitting", "half", "flat", "desk", 19, 0),
    _s(57.250, "your 100% anonymous", "half", "flat", "desk", 19, 4),
    _s(59.625, "", "half", "open", "desk"),
    _s(61.125, "Well my days here", "down", "wave", "desk", 20, 0),
    _s(61.875, "are certainly numbered", "down", "wave", "desk", 20, 4),
)


class SurveyDataError(ValueError):
    """The data above (or a placement of it) is inconsistent."""


def check(segments: Sequence[Segment] = SEGMENTS, end: float = END) -> None:
    """Segments start at 0, rise, end before ``end``, and name real words of real sentences, in order."""
    if not segments or segments[0].start != 0:
        raise SurveyDataError("the first segment starts at 0")
    last_spoken = (-1, -1)
    for i, seg in enumerate(segments):
        if i and seg.start < segments[i - 1].start + MIN_STEP - 1e-9:
            raise SurveyDataError(f"segment {i} at {seg.start} s is held less than {MIN_STEP} s after the one before")
        if (seg.sentence is None) != (seg.word is None):
            raise SurveyDataError(f"segment {i}: sentence and word go together")
        if seg.sentence is not None and seg.word is not None:
            if not 0 <= seg.sentence < len(SENTENCES):
                raise SurveyDataError(f"segment {i}: no sentence {seg.sentence}")
            if not 0 <= seg.word < len(SENTENCES[seg.sentence].split()):
                raise SurveyDataError(f"segment {i}: sentence {seg.sentence} has no word {seg.word}")
            if (seg.sentence, seg.word) <= last_spoken:
                raise SurveyDataError(f"segment {i}: sentence {seg.sentence} word {seg.word} is out of order")
            last_spoken = (seg.sentence, seg.word)
    if segments[-1].start >= end - MIN_STEP:
        raise SurveyDataError(f"the last segment at {segments[-1].start} s needs {MIN_STEP} s before the end {end}")
    for s, (word, letters) in CUTS.items():
        if word not in [w.strip(".,?!") for w in SENTENCES[s].split()] or not 0 < letters < len(word):
            raise SurveyDataError(f"sentence {s} has no word {word!r} to cut at letter {letters}")


def cues(segments: Sequence[Segment], end: float) -> list[dict]:
    """The caption script (``{start, end, text, caption}``): one cue per run of one caption text."""
    check(segments, end)
    out: list[dict] = []
    for seg, nxt in zip(segments, list(segments[1:]) + [None], strict=True):
        stop = end if nxt is None else nxt.start
        if seg.caption and out and out[-1]["text"] == seg.caption and out[-1]["end"] == seg.start:
            out[-1]["end"] = stop
        elif seg.caption:
            out.append({"start": seg.start, "end": stop, "text": seg.caption, "caption": seg.caption})
    return out


def poses(segments: Sequence[Segment]) -> list[dict]:
    """The pose list (``srstudio.toon.parse_poses``): one entry per change of expression."""
    out: list[dict] = []
    for seg in segments:
        pose = {"start": seg.start, "eyes": seg.eyes, "mouth": seg.mouth, "arms": seg.arms}
        if out and all(out[-1][k] == pose[k] for k in ("eyes", "mouth", "arms")):
            continue
        out.append(pose)
    return out


def sentence_spans(segments: Sequence[Segment], end: float) -> list[tuple[float, float]]:
    """Where each sentence is spoken in the reference: from its first segment to the next sentence's first."""
    check(segments, end)
    starts: dict[int, float] = {}
    for seg in segments:
        if seg.sentence is not None and seg.sentence not in starts:
            starts[seg.sentence] = seg.start
    if sorted(starts) != list(range(len(SENTENCES))):
        raise SurveyDataError("every sentence needs a segment that starts it")
    ordered = [starts[s] for s in range(len(SENTENCES))]
    return [(a, b) for a, b in zip(ordered, ordered[1:] + [end], strict=True)]


def flashes(segments: Sequence[Segment]) -> list[float]:
    return [seg.start for seg in segments if seg.flash]


def place_segments(
    segments: Sequence[Segment], word_starts: Sequence[Sequence[float]], speech_ends: Sequence[float]
) -> list[Segment]:
    """The segments moved to a narration: a spoken segment starts where its word is heard (``word_starts[s][w]``,
    project seconds), a silent one a beat after the line before it ends, no earlier than its reference distance
    from the segment before and no later than ``BLANK_MARGIN`` before the next spoken one (the midpoint when that
    window is empty). A change of caption that would cut the caption before it short of ``CAPTION_MIN``
    (measured from when that caption appeared, not from the last change of pose under it) waits for it, up to
    ``CAPTION_LAG`` after its own word. The result is strictly increasing by ``MIN_STEP``."""
    if len(word_starts) != len(SENTENCES) or len(speech_ends) != len(SENTENCES):
        raise SurveyDataError("place_segments needs the word starts and the speech end of every sentence")
    out: list[Segment] = []
    shown = 0.0  # when the caption on screen appeared
    for i, seg in enumerate(segments):
        if seg.sentence is not None and seg.word is not None:
            words = word_starts[seg.sentence]
            if seg.word >= len(words):
                raise SurveyDataError(f"segment {i}: the take of sentence {seg.sentence} has no word {seg.word}")
            at = words[seg.word]
        else:
            before = next((q for q in reversed(out) if q.sentence is not None), None)
            spoken_end = speech_ends[before.sentence] if before and before.sentence is not None else 0.0
            ref_gap = seg.start - segments[i - 1].start if i else 0.0
            at = max(spoken_end + BLANK_GAP, (out[-1].start if out else 0.0) + ref_gap)
            nxt = next((q for q in segments[i + 1 :] if q.sentence is not None and q.word is not None), None)
            if nxt is not None:
                latest = word_starts[nxt.sentence][nxt.word] - BLANK_MARGIN  # type: ignore[index]
                floor = (out[-1].start if out else 0.0) + MIN_STEP
                at = min(at, latest) if latest >= floor else (floor + latest) / 2
        if out:
            at = max(at, out[-1].start + MIN_STEP)
            if out[-1].caption and out[-1].caption != seg.caption:  # let the caption before be read
                at = min(max(at, shown + CAPTION_MIN), at + CAPTION_LAG)
        if not out or out[-1].caption != seg.caption:
            shown = at
        out.append(replace(seg, start=round(at, 6)))
    out[0] = replace(out[0], start=0.0)
    return out


TYPING_ARMS = ("type", "lean")  # poses whose paws are on the keys
SPEECH_MARGIN = 0.15  # keys stay quiet this long around every spoken span, seconds


def typing_bursts(
    segments: Sequence[Segment], end: float, speech: Sequence[tuple[float, float]] = (), step: float = 0.3
) -> list[float]:
    """Burst times (for ``srstudio.foley.taps``) ``step`` apart while a typing pose is held and nothing is said:
    the reference clacks between its lines, never under them. ``speech`` lists the spoken spans (project seconds);
    bursts keep ``SPEECH_MARGIN`` clear of them and ``step`` clear of the end of the run."""
    quiet_from = [(a - SPEECH_MARGIN, b + SPEECH_MARGIN) for a, b in speech]
    if any(b <= a for a, b in speech):
        raise SurveyDataError("speech spans need start < end")
    out = []
    for seg, nxt in zip(segments, list(segments[1:]) + [None], strict=True):
        if seg.arms not in TYPING_ARMS:
            continue
        stop = end if nxt is None else nxt.start
        t = seg.start + 0.1
        while t < stop - step:
            if not any(a <= t <= b for a, b in quiet_from):
                out.append(round(t, 6))
            t += step
    return out


def write_project(root: Path, font: GoogleFont, segments: Sequence[Segment] = SEGMENTS, end: float = END) -> None:
    """``script.json`` and ``assets/poses.json`` on the reference timing, and the style's font pinned under
    ``assets/fonts``."""
    root = Path(root)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "script.json").write_text(json.dumps(cues(segments, end), indent=2) + "\n")
    (root / "assets" / "poses.json").write_text(json.dumps(poses(segments), indent=2) + "\n")
    fonts.install(font, root / "assets" / "fonts")


def write_voiced(root: Path, segments: Sequence[Segment], end: float) -> None:
    """``voiced/script.json`` and ``voiced/poses.json`` for a placed list of segments."""
    folder = Path(root) / "voiced"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "script.json").write_text(json.dumps(cues(segments, end), indent=2) + "\n")
    (folder / "poses.json").write_text(json.dumps(poses(segments), indent=2) + "\n")
