"""Who is named or drawn in which published reel, counted by code, so the cast bible can be recounted (ADR 0069).

A published reel is one in the delivery manifest (``outbox.json``) that has a release. Four sources put a name on a
reel, and each is kept apart so a reader can see why a character was counted:

- ``tag``: the release's ``Tags.recurring``, the names the publishing side compares across reels;
- ``speaker``: the speakers, roles or voice keys the project's data files record (``script.json``,
  ``narration.json``, ``timeline.json``, ``dialogue.json``), a variant like ``rex-off`` folded into ``rex``;
- ``caption``: a name of the vocabulary written with a capital in the post's title, description or credit;
- ``drawn``: a registered character the release pins.

A name recurs when it is on :data:`THRESHOLD` or more reels. What this cannot say is who a name *is*: it counts
appearances and lists the voices and drawings seen with a name, so a name with two of either is flagged, and the
persona is written by someone reading the reels.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import SrstudioError
from .releases import Release

__all__ = [
    "THRESHOLD",
    "Candidate",
    "InventoryError",
    "Reel",
    "candidates",
    "clashes",
    "cite",
    "collect",
    "corpus",
    "mentions",
    "published",
    "speakers",
    "vocabulary",
    "world_of",
]

THRESHOLD = 2  # published reels a character is named or drawn in to recur
SEALED = ("saga", "gloss")  # worlds that share no canon with the everyday one
VARIANT = re.compile(r"-(off|low)$")  # the same speaker heard off screen or quietly
NOT_SPEAKERS = frozenset({"voice_id", "name", "category"})  # a flat voice record, not three speakers
SOURCES = ("script", "narration", "timeline", "dialogue")


class InventoryError(SrstudioError, ValueError):
    """A manifest, a project file or an option cannot be trusted to count from."""


def world_of(slug: str) -> str:
    """The world a published slug belongs to: a sealed series by its slug's first word, else the everyday one."""
    first = slug.split("-", 1)[0]
    return first if first in SEALED and "-" in slug else "okayville"


def published(manifest: Path) -> frozenset[str]:
    """The slugs the delivery manifest holds. A manifest that cannot be read is an error, never an empty set."""
    try:
        document = json.loads(manifest.read_text())
    except (OSError, ValueError) as exc:
        raise InventoryError(f"{manifest}: cannot read the delivery manifest: {exc}") from exc
    videos = document.get("videos") if isinstance(document, dict) else None
    if not isinstance(videos, dict) or not all(isinstance(k, str) and k for k in videos):
        raise InventoryError(f"{manifest}: outbox.json has no 'videos' mapping of named videos")
    return frozenset(videos)


def _load(folder: Path, name: str) -> Any:
    path = folder / f"{name}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise InventoryError(f"{path}: cannot read {name}.json: {exc}") from exc


def _name(raw: object, where: Path) -> str | None:
    if not isinstance(raw, str):
        raise InventoryError(f"{where}: a speaker is {raw!r}, not a name")
    name = VARIANT.sub("", raw.strip().lower())
    return name or None


def _voice(record: object) -> str:
    """The voice's first name from ``Matilda - Knowledgable, Professional``; empty when none is recorded."""
    text = record.get("name") if isinstance(record, dict) else record
    return text.split(" - ", 1)[0].strip() if isinstance(text, str) else ""


def speakers(project: Path) -> dict[str, str]:
    """Each speaker a project records, with the voice's first name (empty when it records none)."""
    found: dict[str, str] = {}

    def add(raw: object, voice: str, where: Path) -> None:
        name = _name(raw, where)
        if name and name not in NOT_SPEAKERS:
            found[name] = found.get(name) or voice

    script = _load(project, "script")
    if script is not None:
        if not isinstance(script, list):
            raise InventoryError(f"{project / 'script.json'}: script.json is not a list of lines")
        for line in script:
            if isinstance(line, dict) and line.get("speaker") is not None:
                add(line["speaker"], _voice(line.get("voice_name")), project / "script.json")

    narration = _load(project, "narration")
    if narration is not None:
        voices = narration.get("voice", {}) if isinstance(narration, dict) else None
        if not isinstance(voices, dict) or not all(isinstance(v, (dict, str)) for v in voices.values()):
            raise InventoryError(f"{project / 'narration.json'}: narration.json has no mapping of voices")
        if not {"voice_id", "name"} <= voices.keys():
            for key, record in voices.items():
                add(key, _voice(record), project / "narration.json")

    timeline = _load(project, "timeline")
    if timeline is not None:
        voices = timeline.get("voices", {}) if isinstance(timeline, dict) else None
        if not isinstance(voices, dict):
            raise InventoryError(f"{project / 'timeline.json'}: timeline.json has no mapping of voices")
        for key, record in voices.items():
            add(key, _voice(record), project / "timeline.json")

    dialogue = _load(project, "dialogue")
    if dialogue is not None:
        phrases = dialogue.get("phrases", []) if isinstance(dialogue, dict) else None
        if not isinstance(phrases, list):
            raise InventoryError(f"{project / 'dialogue.json'}: dialogue.json has no list of phrases")
        for phrase in phrases:
            if isinstance(phrase, dict) and phrase.get("role") is not None:
                add(phrase["role"], _voice(phrase.get("voice_name")), project / "dialogue.json")
    return found


def mentions(text: str, names: Collection[str]) -> set[str]:
    """The names written with a capital as whole words in ``text``; a lowercase word is not a name."""
    return {n for n in names if re.search(rf"(?<![A-Za-z]){re.escape(n.capitalize())}(?![A-Za-z])", text)}


def _said(release: Release) -> str:
    post = release.post
    return "\n".join((post.title, post.description, post.credit))


def vocabulary(releases: Mapping[str, Release], published_slugs: Collection[str], episodes: Path) -> frozenset[str]:
    """Every tagged and spoken name of the published reels: the words a caption is searched for."""
    names: set[str] = set()
    for slug in published_slugs:
        release = releases.get(slug)
        if release is None:
            continue
        names.update(release.tags.recurring if release.tags else ())
        names.update(speakers(episodes / slug) if (episodes / slug).is_dir() else ())
    return frozenset(n for n in names if len(n) > 2)


def _strings(node: object, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("text", "caption") and isinstance(value, str):
                found.append(value)
            else:
                _strings(value, found)
    elif isinstance(node, list):
        for value in node:
            _strings(value, found)


def _plain(text: str) -> str:
    """Lowercase, one space between words, straight quotes: how a line and a quotation of it are compared."""
    table = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-"})
    return " ".join(text.translate(table).lower().split())


def corpus(project: Path, release: Release) -> str:
    """Everything a viewer reads or hears, plain: the lines and captions its project records, and its post."""
    found: list[str] = [release.post.title, release.post.description, release.post.credit]
    for name in (*SOURCES, "voice-transcript"):
        for folder in (project, project / "voiced"):
            document = _load(folder, name) if folder.is_dir() else None
            if document is not None:
                _strings(document, found)
    return "\n".join(_plain(s) for s in found)


def cite(
    slug: str,
    kind: str,
    quote: str,
    *,
    releases: Mapping[str, Release],
    published_slugs: Collection[str],
    episodes: Path,
    characters: Collection[str] = (),
) -> str | None:
    """Why a citation does not hold, or None when it does.

    ``line``: the quotation is part of the reel's lines, captions or post. ``drawn``: the quotation is a registered
    character the release pins. ``voice``: the quotation is a voice the reel's project records. ``seen`` is an
    observation of the render that code cannot confirm: it is reported, never accepted here."""
    if slug not in published_slugs or slug not in releases:
        return f"{slug} is not a published reel"
    release = releases[slug]
    if kind == "line":
        if not quote.strip():
            return f"{slug}: an empty quotation"
        found = _plain(quote) in corpus(episodes / slug, release)
        return None if found else f"{slug}: no line says {quote!r}"
    if kind == "drawn":
        return (
            None
            if quote in (release.parts or {}) and quote in set(characters)
            else f"{slug}: {quote!r} is not a character it draws"
        )
    if kind == "voice":
        heard = set(speakers(episodes / slug).values()) if (episodes / slug).is_dir() else set()
        return None if quote in heard else f"{slug}: no voice {quote!r} (it records {sorted(heard) or 'none'})"
    return f"{slug}: kind {kind!r} cannot be confirmed by code"


@dataclass(frozen=True)
class Reel:
    slug: str
    world: str
    tagged: frozenset[str]
    spoke: frozenset[str]
    named: frozenset[str]
    drawn: frozenset[str]
    voices: Mapping[str, str] = field(default_factory=dict)

    def names(self) -> frozenset[str]:
        return self.tagged | self.spoke | self.named


def collect(
    releases: Mapping[str, Release],
    published_slugs: Collection[str],
    episodes: Path,
    *,
    characters: Collection[str],
    vocabulary: Collection[str],
) -> list[Reel]:
    """One :class:`Reel` per published release, in slug order; a published slug with no release is not counted."""
    reels = []
    for slug in sorted(set(published_slugs) & set(releases)):
        release = releases[slug]
        heard = speakers(episodes / slug) if (episodes / slug).is_dir() else {}
        reels.append(
            Reel(
                slug,
                world_of(slug),
                frozenset(release.tags.recurring if release.tags else ()),
                frozenset(heard),
                frozenset(mentions(_said(release), vocabulary)),
                frozenset(set(release.parts or ()) & set(characters)),
                {n: v for n, v in heard.items() if v},
            )
        )
    return reels


@dataclass(frozen=True)
class Candidate:
    name: str
    world: str
    reels: tuple[str, ...]
    sources: Mapping[str, frozenset[str]]
    voices: Mapping[str, tuple[str, ...]]
    drawn: Mapping[str, tuple[str, ...]]
    recurring: bool
    worlds: tuple[str, ...] = ()


def candidates(reels: Collection[Reel], *, threshold: int = THRESHOLD) -> list[Candidate]:
    """Every name on any reel, with its reels, sources, voices and the characters drawn beside it, most reels first."""
    if threshold < 1:
        raise InventoryError(f"threshold {threshold} must be at least 1: one reel is the least a character is on")
    seen: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    voices: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    drawn: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    worlds: dict[str, set[str]] = defaultdict(set)
    for reel in reels:
        for name in reel.names():
            sources = seen[name][reel.slug]
            for label, group in (("tag", reel.tagged), ("speaker", reel.spoke), ("caption", reel.named)):
                if name in group:
                    sources.add(label)
            worlds[name].add(reel.world)
            if name in reel.voices:
                voices[name][reel.voices[name]].append(reel.slug)
            for part in reel.drawn:
                drawn[name][part].append(reel.slug)
    out = [
        Candidate(
            name,
            sorted(worlds[name])[0] if len(worlds[name]) == 1 else "mixed",
            tuple(sorted(by_reel)),
            {slug: frozenset(s) for slug, s in sorted(by_reel.items())},
            {v: tuple(slugs) for v, slugs in sorted(voices[name].items())},
            {p: tuple(slugs) for p, slugs in sorted(drawn[name].items())},
            len(by_reel) >= threshold,
            tuple(sorted(worlds[name])),
        )
        for name, by_reel in seen.items()
    ]
    return sorted(out, key=lambda c: (-len(c.reels), c.name))


def clashes(candidate: Candidate) -> list[str]:
    """Where one name is heard in two voices, or drawn so that no one character is in every reel that draws any."""
    found = []
    if len(candidate.voices) > 1:
        found.append("voice: " + "; ".join(f"{v} in {', '.join(s)}" for v, s in candidate.voices.items()))
    if candidate.drawn:
        per_reel: dict[str, set[str]] = defaultdict(set)
        for part, slugs in candidate.drawn.items():
            for slug in slugs:
                per_reel[slug].add(part)
        if not set.intersection(*per_reel.values()):
            found.append(
                "drawing: "
                + "; ".join(f"{'+'.join(sorted(parts))} in {slug}" for slug, parts in sorted(per_reel.items()))
            )
    return found
