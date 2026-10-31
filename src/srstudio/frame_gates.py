"""What a human eye caught in full-size frames, held by code where code can hold it.

Reduced-size passes by the authors missed every defect these gates take, and four frames are a sample, so the
funny-reels skill keeps a full-size review by someone who is not the author. These gates take the classes that can be
measured off that review's desk. Each runs on a reel's first delivery only: a video in the manifest is published and
frozen, and no gate here may ask it to change.

- :func:`run_together` reads the scene: a burned caption window must not run across a sentence end unmarked.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from .releases import Release
from .social import DeliveryError, Drift

__all__ = ["FrameGateError", "RunTogether", "captions_run_together", "refuse", "run_together", "sentences_of"]

_WORD = re.compile(r"[a-z0-9$%']+")
_SENTENCE_END = re.compile(r"(?<![.…])(?:\.|[?!]+)[\"'”’)\]]*\Z")  # an ellipsis trails off, inside its sentence
_MARKED = re.compile(r"[.?!,:;…—–-]+[\"'”’)\]]*\Z")
_ABBREVIATION = re.compile(r"(?:[a-z]\.){2,}|(?:mr|mrs|ms|dr|st|vs|jr|sr)\.", re.IGNORECASE)
_SRT_TIMES = re.compile(r"\d\d:\d\d:\d\d,\d{3} --> ")


class FrameGateError(DeliveryError):
    """A new reel a frame gate refuses, or a project a gate cannot read. ``problems`` names each reel and why."""

    def __init__(self, message: str, problems: Iterable[Drift] = ()) -> None:
        super().__init__(message)
        self.problems = tuple(problems)


def refuse(problems: Sequence[Drift]) -> None:
    """Raise :class:`FrameGateError` naming every reel in ``problems``, before anything is written."""
    if problems:
        said = "; ".join(map(str, problems))
        raise FrameGateError(f"the frame gates refuse: {said}", problems)


def _root(document: bytes) -> ET.Element:
    try:
        return ET.fromstring(document)
    except ET.ParseError as e:
        raise FrameGateError(f"not a scene document: {e}") from None


# -- run-together captions -----------------------------------------------------------------------------------------
class RunTogether(NamedTuple):
    """A burned ``window`` that runs ``before``, a sentence's last word, straight into ``after``, the next's first."""

    window: str
    before: str
    after: str


def _plain(word: str) -> str:
    return "".join(_WORD.findall(word.lower().replace("’", "'")))


def _ends_sentence(word: str) -> bool:
    return bool(_SENTENCE_END.search(word)) and not _ABBREVIATION.fullmatch(word)


def _boundaries(sentences: Sequence[str]) -> set[tuple[str, str]]:
    """Each pair of words that a sentence end separates in the reel's lines, read as one run of words. A pair the
    lines also say inside a sentence is left out: ``Flush flush`` after ``brought to you by Flush.`` is the jingle."""
    words = " ".join(sentences).split()
    pairs = list(zip(words, words[1:], strict=False))
    inside = {(_plain(a), _plain(b)) for a, b in pairs if not _ends_sentence(a)}
    return {(_plain(a), _plain(b)) for a, b in pairs if _ends_sentence(a)} - inside


def _windows(root: ET.Element) -> Iterator[str]:
    """The text of every window the scene burns: each text asset a layer shows, then each cue of a caption track."""
    shown = {layer.get("asset") for layer in root.iter("layer")}
    for text in root.iter("text"):
        if text.get("id") in shown and text.get("text"):
            yield " ".join(text.get("text", "").split())
    for cue in root.iter("cue"):
        said = cue.get("text") or " ".join(word.get("text", "") for word in cue.iter("word"))
        yield " ".join(said.split())


def run_together(document: bytes, sentences: Sequence[str]) -> list[RunTogether]:
    """Every place a burned window of the scene ``document`` carries one of ``sentences`` into the next with nothing
    between them: ``Take it Whatever`` for ``Take it. Whatever``. A window that keeps the stop reads as two sentences
    and passes. The windows are matched to the sentences by their words, so a title or a sign burned in the picture
    is read too, and passes unless it repeats that pair of words."""
    boundaries = _boundaries(sentences)
    found: list[RunTogether] = []
    for window in dict.fromkeys(_windows(_root(document))):
        words = window.split()
        for a, b in zip(words, words[1:], strict=False):
            if (_plain(a), _plain(b)) in boundaries and not _MARKED.search(a):
                found.append(RunTogether(window, a, b))
    return found


def _srt_lines(path: Path) -> list[str]:
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    return [
        " ".join(block.splitlines()[2:])
        for block in blocks
        if len(block.splitlines()) > 2 and _SRT_TIMES.match(block.splitlines()[1])
    ]


def _script_lines(path: Path) -> list[str]:
    try:
        return [line["expected"] for line in json.loads(path.read_text(encoding="utf-8"))["lines"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise FrameGateError(f"{path}: no sentences to read: {e!r}") from None


def sentences_of(project: Path) -> list[str]:
    """The lines a reel says, with their punctuation: its script as ``voice-transcript.json`` records it, then its
    subtitles (a burned caption is stripped of its stops, so these are where its sentences end). None for a silent
    reel."""
    project = Path(project)
    lines = _script_lines(project / "voice-transcript.json") if (project / "voice-transcript.json").is_file() else []
    for srt in sorted(project.glob("*.srt")):
        lines += _srt_lines(srt)
    return lines


def captions_run_together(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> list[Drift]:
    """Each run-together caption of the reels on their ``first`` delivery (slug to video name); a project with no
    scene has nothing to read."""
    drift: list[Drift] = []
    for slug, video in first.items():
        project = Path(episodes) / slug
        scene = project / releases[slug].scene_file
        if not scene.is_file():
            continue
        drift += [
            Drift(video, f"the caption {r.window!r} runs {r.before!r} into {r.after!r} across a sentence end")
            for r in run_together(scene.read_bytes(), sentences_of(project))
        ]
    return drift
