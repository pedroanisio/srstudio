"""An overlay that repeats the spoken caption prints the same words twice on one frame (ADR 0079).

A key line and a hook card are added on top of the picture and each reel gives them their words and their window, with
nothing to compare them to the captions. The gate reads a scene for those two overlays, by the drawing that made them
and not by their words: text inside the picture that a character reads or holds up may match the caption, because
that is a caption of a thing being read. It reads the scene, so it needs no engine, and it stands beside
:func:`srstudio.releases.doubled_captions` on the same reels: a video already published is frozen and never read.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from . import craft, stick, subtitles, toon_house
from .releases import Release
from .social import Drift
from .toon import fy

__all__ = ["Overlay", "overlays", "repeated_lines", "repeats"]

_WORD = re.compile(r"[a-z0-9$%']+")
_RUN = 3  # words in a row shared with a cue that make a repeat; a shorter line must be there whole
HOOK_FILL = "#ffffff"

Span = tuple[float, float]


class Overlay(NamedTuple):
    """A line added on top of the picture, and the seconds it shows."""

    kind: str
    text: str
    spans: tuple[Span, ...]


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("’", "'"))


def _runs(words: Sequence[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def _same_line(a: Sequence[str], b: Sequence[str]) -> bool:
    """Whether ``a`` and ``b`` say the same line: equal, one held whole in the other, or :data:`_RUN` words in a row in
    common. One word is a repeat only of itself: a single shared word is what any two lines have."""
    size = min(_RUN, len(a), len(b))
    if size < 2:
        return list(a) == list(b) and size == 1
    return bool(_runs(a, size) & _runs(b, size))


def _rect(node: ET.Element) -> dict[str, str] | None:
    """The attributes of the first rectangle drawn directly in ``node``."""
    for child in node:
        if child.tag == "shape" and child.get("shape") == "rect":
            return dict(child.attrib)
    return None


def _number(attrs: Mapping[str, str | None], name: str) -> float | None:
    value = attrs.get(name)
    return None if value is None else float(value)


def _kind(layer: ET.Element, parent: ET.Element, asset: ET.Element) -> str | None:
    """Which overlay drew ``layer``, read off the bar or the card it stands on; ``None`` for any other text."""
    rect = _rect(parent)
    if rect is None:
        return None
    place = (_number(rect, "x"), _number(rect, "y"), _number(rect, "width"), _number(rect, "height"))
    x, y, width, height, radius = stick.CARD
    if (
        place == (x, y, width, height)
        and _number(rect, "radius") == radius
        and rect.get("fill") == HOOK_FILL
        and (_number(layer.attrib, "x"), _number(layer.attrib, "y")) == (x + 35, y + 8)
    ):
        return "hook card"
    if (
        rect.get("fill") == toon_house.KEY_LINE_BG
        and _number(rect, "y") == fy(toon_house.KEY_LINE_TOP)
        and _number(layer.attrib, "y") == fy(toon_house.KEY_LINE_TOP)
        and _number(asset.attrib, "size") == toon_house.KEY_LINE_SIZE
        and asset.get("color") == toon_house.KEY_LINE_INK
    ):
        return "key line"
    return None


def _shown_by_keys(animate: ET.Element, base: float, last: float) -> list[Span]:
    """The spans an opacity or visibility track leaves on screen, every key held to the next."""
    keys = sorted(
        (base + craft._seconds(key, "time"), key.get("value", "") not in ("0", "0.0", "false"))
        for key in animate.iterfind("key")
    )
    if not keys:
        return [(0.0, last)]
    keys[0] = (0.0, keys[0][1])
    spans: list[Span] = []
    for (at, on), (until, _) in zip(keys, [*keys[1:], (last, False)], strict=True):
        if not on or until <= at:
            continue
        spans[-1:] = [(spans[-1][0], until)] if spans and spans[-1][1] == at else [*spans[-1:], (at, until)]
    return spans


def _both(a: Iterable[Span], b: Iterable[Span]) -> list[Span]:
    shared = [(max(s, t), min(e, u)) for s, e in a for t, u in b]
    return sorted((round(s, 6), round(e, 6)) for s, e in shared if e > s)


def _clock(node: ET.Element, parents: Mapping[ET.Element, ET.Element]) -> float:
    """Where a node's own clock starts: at the start of the nearest window around it."""
    at: ET.Element | None = node
    while at is not None and at.get("start") is None:
        at = parents.get(at)
    return 0.0 if at is None else craft._seconds(at, "start")


def _spans(
    layer: ET.Element, parents: Mapping[ET.Element, ET.Element], shifts: Mapping[ET.Element, float], last: float
) -> list[Span]:
    """The seconds ``layer`` shows: its window, cut by each ancestor's window and by their gates."""
    spans: list[Span] = [(0.0, last)]
    node: ET.Element | None = layer
    while node is not None:
        shift = shifts.get(node, 0.0)
        end = shift + craft._seconds(node, "end") if node.get("end") is not None else last
        spans = _both(spans, [(shift + craft._seconds(node, "start"), end)])
        for animate in node.iterfind("animate"):
            if animate.get("property") in ("opacity", "visible"):
                local = animate.get("timeBase") == "local"
                base = shift + _clock(node, parents) if local else 0.0
                spans = _both(spans, _shown_by_keys(animate, base, last))
        node = parents.get(node)
    return spans


def overlays(document: bytes) -> list[Overlay]:
    """Every key line and hook card in the scene ``document`` that ever shows."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise craft.CraftError(f"not a scene document: {e}") from None
    project = root.find("project")
    last = 0.0 if project is None else craft._seconds(project, "duration")
    assets = {a.get("id"): a for a in root.iterfind("assets/text")}
    parents = {child: node for node in root.iter() for child in node}
    shifts = craft._sequence_shifts(root)
    found = []
    for layer in root.iter("layer"):
        asset = assets.get(layer.get("asset"))
        kind = None if asset is None else _kind(layer, parents[layer], asset)
        if asset is None or kind is None:
            continue
        spans = _spans(layer, parents, shifts, last)
        if spans:
            found.append(Overlay(kind, asset.get("text", ""), tuple(spans)))
    return found


def repeats(document: bytes, cues: Iterable[subtitles.Cue]) -> list[str]:
    """Each overlay in ``document`` that shows while a cue of ``cues`` says the same line. Two windows that meet at a
    rounded time do not overlap: below :data:`srstudio.craft.DOUBLED` no frame carries both."""
    found = []
    listed = list(cues)
    for overlay in overlays(document):
        said = _words(overlay.text)
        for start, end, text in listed:
            if not _same_line(said, _words(text)):
                continue
            shared = [(s, e) for s, e in _both(overlay.spans, [(start, end)]) if e - s > craft.DOUBLED]
            if shared:
                found.append(
                    f'the {overlay.kind} "{overlay.text}" repeats the caption on screen '
                    f"from {shared[0][0]:.2f} to {shared[-1][1]:.2f} s"
                )
    return found


def repeated_lines(releases: Mapping[str, Release], episodes: Path, delivering: Collection[str]) -> list[Drift]:
    """Every overlay that repeats a live caption in a video being delivered, and every overlay with no captions to
    compare it with; a published video is frozen and a project with no scene has nothing to read."""
    drift: list[Drift] = []
    for release in releases.values():
        scene = Path(episodes) / release.slug / release.scene_file
        srt = Path(episodes) / release.slug / f"{release.slug}.srt"
        if release.video_name not in delivering or not scene.is_file():
            continue
        document = scene.read_bytes()
        if srt.is_file():
            why = repeats(document, subtitles.read_srt(srt))
        else:
            why = [f'the {o.kind} "{o.text}" has no captions to compare with' for o in overlays(document)]
        drift.extend(Drift(release.video_name, reason) for reason in why)
    return drift
