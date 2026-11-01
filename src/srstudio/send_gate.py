"""No bait on the send test: a reel earns a send, it never asks for one (ADR 0080).

A reel is on the send test when its tags name who it is sent to and its send line, or when its claim names the brief
``send-v1``, as a holdout's does: the holdout skips the test but not the rule. Every other reel is never read, so what
was delivered stays as it went out. The gate reads what the library can see, the caption, the cover, the scene's text
and the spoken captions, so it needs no engine. It matches the words, so a character's own line with these words is
refused too: the phrase on screen reads as the ask, whoever says it.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from pathlib import Path

from . import craft, subtitles
from .releases import Release
from .social import Drift

__all__ = ["BRIEF", "bait", "bait_drift", "on_test"]

BRIEF = "send-v1"
_PHRASES = ("tag a friend", "tag someone", "send this to", "share this with", "send it to")
_BAIT = re.compile(r"\b(" + "|".join(p.replace(" ", r"\s+") for p in _PHRASES) + r")\b", re.IGNORECASE)


def bait(text: str) -> list[str]:
    """The bait phrases in ``text``, in lower case with single spaces, each once, in the order they appear."""
    return list(dict.fromkeys(" ".join(found.lower().split()) for found in _BAIT.findall(text)))


def on_test(release: Release, brief: str) -> bool:
    """Whether ``release``, whose claim names ``brief`` or nothing, is held to the send test's no-bait rule."""
    tags = release.tags
    return brief == BRIEF or (tags is not None and bool(tags.send_to))


def _cover(release: Release) -> str:
    thumb = release.post.thumbnail
    return "" if thumb is None else f"{thumb.headline}\n{thumb.kicker}"


def _scene_text(scene: Path) -> Iterable[str]:
    try:
        root = ET.fromstring(scene.read_bytes())
    except ET.ParseError as e:
        raise craft.CraftError(f"{scene.name} is not a scene document: {e}") from None
    return [node.get("text", "") for node in root.iterfind("assets/text")]


def _screen(release: Release, project: Path) -> list[str]:
    """What the viewer reads in the video: each text of the scene, and the spoken captions as one run, so that a phrase
    split over two cues still reads as the phrase."""
    srt = project / f"{release.slug}.srt"
    said = " ".join(cue[2] for cue in subtitles.read_srt(srt)) if srt.is_file() else ""
    return [*_scene_text(project / release.scene_file), said]


def bait_drift(releases: Mapping[str, Release], episodes: Path, briefs: Mapping[str, str]) -> list[Drift]:
    """Every bait phrase in the reels of ``releases`` on the send test, by what carries it; ``briefs`` maps a slug to
    the brief its claim names. A reel on the test whose scene cannot be read is refused, not skipped."""
    drift: list[Drift] = []
    for slug, release in releases.items():
        if not on_test(release, briefs.get(slug, "")):
            continue
        name = release.video_name
        drift += [Drift(name, f'its caption says "{p}"') for p in bait(release.post.text())]
        drift += [Drift(name, f'its cover says "{p}"') for p in bait(_cover(release))]
        project = Path(episodes) / release.slug
        if not (project / release.scene_file).is_file():
            drift.append(Drift(name, f"{release.scene_file} is missing: its on-screen text cannot be read"))
            continue
        try:
            found = [p for text in _screen(release, project) for p in bait(text)]
        except craft.CraftError as e:
            drift.append(Drift(name, str(e)))
            continue
        drift += [Drift(name, f'its screen says "{p}"') for p in dict.fromkeys(found)]
    return drift
