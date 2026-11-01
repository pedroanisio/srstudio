"""The canon check: does a new reel, or a brief, agree with the cast bible? Plain code, no model (ADR 0069).

A release is checked against what its project recorded, by the name it uses for each character:

- ``unknown-name``: a name the release tags or a project speaker uses that is neither a character of the bible in the
  reel's world nor one of its unnamed roles;
- ``drawing``: a known character named in the reel while none of the parts the bible gives them is drawn in it, and the
  reel draws a character part that no name present accounts for. A character who is only heard (a voice on the phone,
  a voice behind a door) has no drawing to get wrong: when every character part the reel draws belongs to another name
  present, she is checked for her name and her voice alone. A rig that draws any figure (the Stick style's) belongs to
  no one in particular, so it never explains a name's absence. When several characters of the reel's world share a
  name, the one whose voice the reel has (else the one whose drawing it pins) is the one meant;
- ``voice``: a known character heard in a voice that is not the bible's;
- ``world``: a name that only exists in another world's bible (a sealed world shares no canon).

A brief is checked for the ``Cast:`` line that cites the bible: its slugs must be characters of the bible, and an
optional ``World:`` line must be one the bible knows, with no character of another world named in its cast.

What this cannot do is read prose: a brief that makes Rex a cat in its third paragraph, or a fact that contradicts
a canon fact in other words, is beyond what code can prove. Only the names, the drawings, the voices and the cast line
are checked, and a release already delivered is never refused (the caller passes only a first delivery).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import bible_inventory, registry
from .bible import Bible, Character
from .releases import Release
from .social import DeliveryError

__all__ = ["BibleCheckError", "Finding", "check_brief", "check_release", "refuse"]

CAST_LINE = re.compile(r"^\s*cast\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
WORLD_LINE = re.compile(r"^\s*world\s*:\s*([a-z-]+)\s*$", re.IGNORECASE | re.MULTILINE)


class BibleCheckError(DeliveryError):
    """A reel or a brief disagrees with the cast bible; ``findings`` says how, one per fault."""

    def __init__(self, findings: list[Finding]):
        super().__init__("the cast bible refuses: " + "; ".join(str(f) for f in findings))
        self.findings = findings


@dataclass(frozen=True)
class Finding:
    where: str
    kind: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.kind}: {self.message}"


def _voice_matches(heard: str, character: Character) -> bool:
    given = character.voice.voice
    return given.startswith(("open:", "proposal:")) or heard.lower() in given.lower()


def _which(here: list[Character], voice: str, pinned: Collection[str]) -> Character:
    """The character a name means when several of one world share it: the one whose voice the reel has, else the one
    whose drawing it pins, else the first. Two Garys of one world (a Collage dad, a Stick one) are told apart so."""
    if len(here) > 1:
        for test in (
            lambda c: bool(voice) and _voice_matches(voice, c) and not c.voice.voice.startswith(("open:", "proposal:")),
            lambda c: bool({d.part for d in c.look.drawing} & set(pinned)),
        ):
            for c in here:
                if test(c):
                    return c
    return here[0]


def rig_parts() -> frozenset[str]:
    """The registered parts that draw any number of figures: one rig per style, as the Stick style has."""
    return frozenset(e.name for e in registry.entries("character") if e.style == "stick")


def check_release(
    bible: Bible,
    release: Release,
    episodes: Path,
    *,
    characters: Collection[str] = (),
    rigs: Collection[str] | None = None,
) -> list[Finding]:
    """What disagrees with the bible in ``release``, by the names its tags and its project's speakers use."""
    slug = release.slug
    world = bible_inventory.world_of(slug)
    project = episodes / slug
    heard = bible_inventory.speakers(project) if project.is_dir() else {}
    names = sorted({*(release.tags.recurring if release.tags else ()), *heard})
    pinned = set(release.parts or ()) & set(characters)
    many = set(rig_parts() if rigs is None else rigs)  # a rig draws anyone, so it explains no one
    accounted: set[str] = set()  # the drawn parts that a name present in the reel explains
    for name in names:
        accounted |= {d.part for c in bible.named(name) if c.world == world for d in c.look.drawing} & pinned - many
    unexplained = pinned - accounted  # drawn in the reel, and no name present owns them
    found: list[Finding] = []
    unnamed = []
    for name in names:
        if bible.is_role(name):
            continue
        everywhere = bible.named(name)
        here = [c for c in everywhere if c.world == world]
        if not everywhere:
            unnamed.append(name)
            found.append(Finding(slug, "unknown-name", f"{name!r} is not a character of the bible"))
            continue
        if not here:
            where = ", ".join(sorted({c.world for c in everywhere}))
            found.append(Finding(slug, "world", f"{name!r} is a character of {where} only; {world} shares no canon"))
            continue
        character = _which(here, heard.get(name, ""), pinned)
        owned = {d.part for d in character.look.drawing} & set(characters)  # a prop is no character part to compare
        if unexplained and owned and not owned & pinned:
            found.append(
                Finding(
                    slug,
                    "drawing",
                    f"{name!r} is drawn as {', '.join(sorted(owned))} in the bible; "
                    f"the reel draws {', '.join(sorted(pinned))}",
                )
            )
        voice = heard.get(name, "")
        if voice and not _voice_matches(voice, character):
            found.append(
                Finding(slug, "voice", f"{name!r} is {character.voice.voice} in the bible; the reel has {voice}")
            )
    if unnamed:
        belong = {
            d.part: c.slug for c in bible.characters if c.world == world for d in c.look.drawing if d.part not in many
        }  # a rig belongs to no one, so it names no absent owner
        absent = sorted({who for part, who in belong.items() if part in pinned and who not in names})
        if absent:
            found.append(
                Finding(
                    slug,
                    "unknown-name",
                    f"the reel draws what the bible calls {', '.join(absent)}; "
                    f"is {', '.join(unnamed)} a new name for them?",
                )
            )
    return found


def check_brief(bible: Bible, text: str, *, where: str = "brief") -> list[Finding]:
    """The ``Cast:`` line of a brief or script: it must cite the bible, and cite only what the bible holds."""
    cast = CAST_LINE.search(text)
    if cast is None:
        return [
            Finding(where, "cast-line", "cites no cast: add a 'Cast: slug, slug' line naming the bible's characters")
        ]
    slugs = [s.strip().lower() for s in cast.group(1).split(",") if s.strip()]
    world_line = WORLD_LINE.search(text)
    world = world_line.group(1).lower() if world_line else ""
    found: list[Finding] = []
    if world and world not in {c.world for c in bible.characters} | {"okayville"}:
        found.append(Finding(where, "world", f"{world!r} is not a world of the bible"))
    for slug in slugs:
        character = bible.character(slug)
        if character is None:
            found.append(Finding(where, "unknown-name", f"{slug!r} is not a character of the bible"))
        elif world and character.world != world:
            found.append(Finding(where, "world", f"{slug!r} is a {character.world} character; the brief is {world}"))
    if not slugs:
        found.append(Finding(where, "cast-line", "the Cast: line names no one"))
    return found


def refuse(findings: Mapping[str, list[Finding]]) -> None:
    """Raise :class:`BibleCheckError` listing every finding of every slug; nothing is raised when there are none."""
    flat = [f for slug in sorted(findings) for f in findings[slug]]
    if flat:
        raise BibleCheckError(flat)
