"""Every registered part is shown by a gallery item, or declared here with the reason it is not.

The page build stops when a rendered library episode uses a part that no gallery item shows (``catalog_page``), but it
needs the measured usage, which takes minutes, so it cannot run before a merge: a branch that adds a part would pass,
and the catalog site would stop updating after the merge, with nobody told. This test is the cheap part of that check.
It fails on the branch that registers a part, until the part gets a gallery item in ``docs/catalog/notes.json`` or is
listed below. A declared part can start to be used later; the build then still stops and names it (docs/catalog/README).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Collection
from pathlib import Path

from srstudio import (
    pedro,  # noqa: F401 (importing it registers Pedro, which this file declares)
    rafa_host,  # noqa: F401 (importing it registers Rafa's parts, which this file declares)
    registry,
)

NOTES = Path(__file__).resolve().parent.parent / "docs" / "catalog" / "notes.json"

# From `srstudio usage` on 2026-10-31 (145 episodes, the pilots among them); drop a part from here when its gallery item
# is added.
PACKAGE_ONLY = [
    "answer-bubble",
    "connected-card",
    "dashboard",
    "ink-printer-shot",
    "ink-wide",
    "quiz-card",
    "silent-phone",
    "talking-printer",
]
SUPERSEDED = ["toon-fox", "toon-hedgehog", "toon-raccoon"]
REPLACED_ON_SCREEN = ["news-gus@2", "news-vera@2"]
NO_EPISODE = [
    "bo@2",  # proposed: hands, ADR 0239
    "friends-leo",
    "friends-sam",
    "juno@2",  # proposed: hands, ADR 0239
    "news-gus@4",
    "news-gus@5",
    "news-gus@6",
    "news-phone@2",
    "news-vera@4",
    "news-vera@5",
    "news-vera@6",
    "pedro",
    "pip@2",  # proposed: hands, ADR 0239
    "rafa",
    "rafa-bills",
    "rafa-breakroom",
    "rafa-kitchen",
    "rafa-lunchbox",
    "rafa-mug",
    "rafa-phone",
    "rafa-tote",
    "show-bug",
    "smallprint-apple",
    "smallprint-bowl",
    "smallprint-bread",
    "smallprint-can",
    "smallprint-card",
    "smallprint-feather",
    "smallprint-goldfish",
    "smallprint-horse",
    "smallprint-mint",
    "smallprint-onion",
    "smallprint-paper",
    "smallprint-phone",
    "smallprint-roll",
    "smallprint-stamp",
    "smallprint-sunflower",
    "smallprint-mars",
    "smallprint-tears",
    "smallprint-tower",
    "smallprint-wall",
    "toon-bento",
    "toon-bento@2",
    "toon-counter",
    "toon-field-notebook",
    "toon-leo",
    "toon-lyra",
    "toon-moon-globe",
    "toon-pipe",
    "toon-planetarium-salon",
    "toon-receipt",
    "toon-sam",
    "toon-saturn-model",
    "toon-signal-clicker",
    "toon-starlight-terrace",
    "toon-take-a-number",
    "toon-telescope",
    "toon-tv-browse",  # its reel, #213 grown-on-me, is held until its rebuild (ADR 0140)
    "wire-car",
    "wire-jet",
]
NOT_SHOWN: dict[str, str] = {
    **dict.fromkeys(PACKAGE_ONLY, "only a packaged reel uses it; the packages' cards stay under #/pacotes"),
    **dict.fromkeys(SUPERSEDED, "the first drawing, replaced by its @2 version, which the gallery shows"),
    **dict.fromkeys(REPLACED_ON_SCREEN, "every reel showing it moved to @3, renders too: no still of it is left"),
    **dict.fromkeys(NO_EPISODE, "no library episode builds it yet"),
}


def coverage_gaps(
    shown: Collection[str], registered: Collection[str], declared: Collection[str]
) -> tuple[list[str], list[str]]:
    """The registered parts that are neither shown nor declared, and the declared ones that should not be: already
    shown, or no longer registered."""
    missing = sorted(set(registered) - set(shown) - set(declared))
    stale = sorted(set(declared) & set(shown) | set(declared) - set(registered))
    return missing, stale


def test_every_registered_part_is_shown_or_declared_as_not_shown():
    gallery = json.loads(NOTES.read_text())["gallery"]
    shown = {part for item in gallery for part in item["parts"]}
    missing, stale = coverage_gaps(shown, {e.name for e in registry.entries()}, NOT_SHOWN)
    assert not missing, (
        f"no gallery item shows {missing}: add an item to docs/catalog/notes.json (a still of a render where it is on "
        "screen), or declare the part in NOT_SHOWN with the reason there is none"
    )
    assert not stale, f"NOT_SHOWN lists {stale}, which a gallery item shows or the registry no longer has: remove it"


def test_a_part_with_no_item_and_no_declaration_is_a_gap_and_so_is_a_declaration_left_behind():
    missing, stale = coverage_gaps(shown={"a"}, registered={"a", "b", "c"}, declared={"c", "a", "gone"})
    assert missing == ["b"]  # registered, not shown, not declared
    assert stale == ["a", "gone"]  # declared though shown, declared though unregistered
    assert coverage_gaps({"a"}, {"a", "c"}, {"c"}) == ([], [])  # shown or declared: no gap


def test_importing_the_library_registers_every_recorded_part():
    """Run apart from the suite, whose collection imports every module and so hides a part nothing else imports."""
    code = (
        "import srstudio\n"
        "from srstudio import parts, registry\n"
        "known = {e.name for e in registry.entries()}\n"
        "print(sorted(set(parts.load()) - known))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
