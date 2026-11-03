"""What the published record has that the cast bible does not yet (ADR 0069): the list of work that extends it.

A gap is not a fault of the bible; it is a reel published since the last version. Plain code, no model.

- ``missing``: a name on 2 or more published reels of its world with no sheet.
- ``stale``: a sheet whose reels lack a published reel that names the character. Characters of one world that share
  a name, as the two Garys do, share the reels it is on: the first sheet is listed once if none of them has the reel.
  A reel a recorded clash cites, or names in its subject (the Toon Pip), is a decision waiting for the operator, not
  work for an author.

A fix to either is a new minor version of the bible and a ``CHANGELOG.md`` section, locked with
``srstudio bible lock``.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass

from .bible import Bible
from .bible_inventory import THRESHOLD, Candidate, Reel, candidates, world_of

__all__ = ["Gaps", "find"]

CANON_FAMILY = {"saga": {"saga"}, "gloss": {"gloss"}}
SHARED = {"okayville", "news", "host", "mind", "maps"}  # worlds that share one set of characters, as in the bible


@dataclass(frozen=True)
class Gaps:
    missing: tuple[tuple[str, str, tuple[str, ...]], ...]  # (name, world, its published reels)
    stale: tuple[tuple[str, tuple[str, ...]], ...]  # (character slug, published reels that name it but are not listed)
    waiting: tuple[str, ...]  # placeholder slugs: filled by hand once a published reel establishes them
    bare: tuple[str, ...]  # published reels that name no character of the bible

    def __bool__(self) -> bool:
        return bool(self.missing or self.stale)


def _family(world: str) -> set[str]:
    return CANON_FAMILY.get(world, SHARED)


def find(bible: Bible, reels: Collection[Reel], *, threshold: int = THRESHOLD) -> Gaps:
    """Compare the published reels' names with the bible's characters, world by world."""
    recorded = {f.reel for clash in bible.clashes for f in clash.evidence}  # a clash is on record, not a gap
    subjects = " ".join(clash.subject for clash in bible.clashes)
    recorded |= {s for r in reels for s in [r.slug] if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", subjects)}
    missing: list[tuple[str, str, tuple[str, ...]]] = []
    stale: dict[str, tuple[str, ...]] = {}
    covered: set[str] = set()
    for cand in candidates(reels, threshold=1):
        if bible.is_role(cand.name):
            continue
        for world in cand.worlds or (cand.world,):
            _compare(bible, cand, world, threshold, recorded, missing, stale, covered)
    bare = sorted(r.slug for r in reels if r.slug not in covered)
    waiting = tuple(c.slug for c in bible.characters if c.status == "placeholder")
    return Gaps(tuple(sorted(missing)), tuple(sorted(stale.items())), waiting, tuple(bare))


def _compare(
    bible: Bible,
    cand: Candidate,
    world: str,
    threshold: int,
    recorded: set[str],
    missing: list[tuple[str, str, tuple[str, ...]]],
    stale: dict[str, tuple[str, ...]],
    covered: set[str],
) -> None:
    here = tuple(s for s in cand.reels if world_of(s) == world)
    sheets = [c for c in bible.named(cand.name) if c.world in _family(world) and c.status == "canon"]
    if not sheets:
        if len(here) >= threshold:
            missing.append((cand.name, world, here))
        return
    covered.update(here)
    listed = {s for sheet in sheets for s in sheet.reels}  # characters that share a name share the reels it is on
    absent = tuple(s for s in here if s not in listed and s not in recorded)
    if absent:
        slug = sheets[0].slug
        stale[slug] = tuple(sorted(set(stale.get(slug, ())) | set(absent)))
