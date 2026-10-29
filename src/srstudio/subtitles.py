"""Caption pages from word timings, and SRT output."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from .errors import SrstudioError

Cue = tuple[float, float, str]


class SubtitleError(SrstudioError, ValueError):
    """Captions asked for with an option they cannot be paged by."""


def chunk_words(
    words: Sequence[dict], duration: float, *, max_chars: int = 31, upper: bool = True, min_seconds: float = 0.0
) -> list[Cue]:
    """Pages of at most ``max_chars``, broken at sentence ends; each page runs until the next starts.

    A page shown for less than ``min_seconds`` joins the next page, else the previous one, when the joined text
    still fits ``max_chars``; a short page with no such neighbour stays (the renderer's legibility check reports it)."""
    if not (min_seconds >= 0):
        raise SubtitleError(f"min_seconds must be non-negative, got {min_seconds}")
    chunks: list[list[dict]] = []
    buf: list[dict] = []
    for w in words:
        if buf and len(" ".join(z["text"] for z in buf + [w])) > max_chars:
            chunks.append(buf)
            buf = []
        buf.append(w)
        if re.search(r"[.!?]$", w["text"]):
            chunks.append(buf)
            buf = []
    if buf:
        chunks.append(buf)
    if min_seconds:
        chunks = _merge_short(chunks, duration, max_chars, min_seconds)
    out: list[Cue] = []
    for i, b in enumerate(chunks):
        start = 0 if i == 0 else b[0]["start"]
        end = chunks[i + 1][0]["start"] if i + 1 < len(chunks) else duration
        text = _page_text(b)
        out.append((start, end, text.upper() if upper else text))
    return out


def _page_text(chunk: Sequence[dict]) -> str:
    return " ".join(w["text"] for w in chunk)


def _merge_short(chunks: list[list[dict]], duration: float, max_chars: int, min_seconds: float) -> list[list[dict]]:
    """Joins pages shorter than ``min_seconds`` with a neighbour while the joined text fits, else moves the tail of
    the previous page onto the short one; at most one step per page, so the loop is bounded by the page count."""
    pages = [list(c) for c in chunks]

    def span(i: int, start: float | None = None) -> float:
        begin = 0.0 if i == 0 else (pages[i][0]["start"] if start is None else start)
        return (pages[i + 1][0]["start"] if i + 1 < len(pages) else duration) - begin

    for _ in range(2 * len(pages)):
        i = next((i for i in range(len(pages)) if span(i) < min_seconds), None)
        if i is None:
            break
        if i + 1 < len(pages) and len(_page_text(pages[i] + pages[i + 1])) <= max_chars:
            pages[i : i + 2] = [pages[i] + pages[i + 1]]
            continue
        if i > 0 and len(_page_text(pages[i - 1] + pages[i])) <= max_chars:
            pages[i - 1 : i + 1] = [pages[i - 1] + pages[i]]
            continue
        moved = False
        for k in range(1, len(pages[i - 1])) if i > 0 else ():
            head, tail = pages[i - 1][:-k], pages[i - 1][-k:]
            prev_start = 0.0 if i - 1 == 0 else head[0]["start"]
            if (
                len(_page_text(tail + pages[i])) <= max_chars
                and tail[0]["start"] - prev_start >= min_seconds
                and span(i, tail[0]["start"]) >= min_seconds
            ):
                pages[i - 1], pages[i], moved = head, tail + pages[i], True
                break
        if not moved:
            break  # nothing fits beside it; the renderer's legibility check reports what is left
    return pages


def srt_stamp(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def write_srt(path: Path, cues: Sequence[Cue]) -> Path:
    path = Path(path)
    body = "\n\n".join(f"{i + 1}\n{srt_stamp(s)} --> {srt_stamp(e)}\n{text}" for i, (s, e, text) in enumerate(cues))
    path.write_text(body + "\n")
    return path
