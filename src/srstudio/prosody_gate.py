"""The prosody gate at first delivery (ADR 0234 d): advisory for every reel, refusing only a reel recorded to it.

arc4d3's ruling of 4 Nov 2026: the prosody findings are listed in every first-delivery report from today, and they
refuse only scripts started after the gate landed. The marker for "started after" is the ``prosody`` section of the
reel's ``timeline.json``: :func:`srstudio.takes.record` writes it since slice (c), and nothing before it did, so every
recording made before the gate reads :data:`UNMEASURED` and is listed, never refused.

The gate does not trust the section's ``passed`` field: it runs :func:`srstudio.prosody.gate` on the timeline again,
with today's targets, and refuses on any finding no stated reason waives. A recorded verdict could be stale (made on
targets that have since moved) or edited by hand; the recorded words and timings are what was heard. A section the
gate cannot read refuses the reel, since a check that passes because its input is broken cannot fail.

Every waived finding is listed with its reason, so the reason reaches the delivery report (``deliver``'s output) that
the delivery post to the reviewer quotes. The Instagram caption is public and never carries it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import prosody
from .prosody import Finding, ProsodyError
from .releases import Release
from .social import Drift

__all__ = ["UNMEASURED", "Reading", "lines", "read", "reading", "refusals"]

UNMEASURED = "unmeasured"
TIMELINE = "timeline.json"


@dataclass(frozen=True)
class Reading:
    """What the gate reads of one reel on its first delivery: ``measured`` when its timeline has a ``prosody`` section,
    the findings of the gate run again, and ``error`` when the section or the timeline cannot be read."""

    video: str
    measured: bool
    findings: tuple[Finding, ...] = ()
    error: str = ""
    why: str = ""  # an unmeasured reel: why

    @property
    def failing(self) -> tuple[Finding, ...]:
        return tuple(prosody.failing(self.findings))

    @property
    def refused(self) -> bool:
        return self.measured and bool(self.error or self.failing)

    def lines(self) -> list[str]:
        """The report's lines for this reel: one when it is unmeasured, clean or unreadable, else one per finding,
        waived findings with their reasons."""
        head = f"prosody {self.video}"
        if not self.measured:
            return [f"{head}: {UNMEASURED} ({self.why}), advisory"]
        if self.error:
            return [f"{head}: REFUSED, {self.error}"]
        if not self.findings:
            return [f"{head}: clean"]
        verdict = "REFUSED" if self.failing else "passes on its waivers"
        return [f"{head}: {verdict}", *(f"  {f.line()}" for f in self.findings)]


def reading(video: str, project: Path) -> Reading:
    """The gate's reading of the reel recorded in ``project``."""
    path = Path(project) / TIMELINE
    if not path.is_file():
        return Reading(video, False, why=f"no {TIMELINE}")
    try:
        timeline = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return Reading(video, True, error=f"{TIMELINE} cannot be read: {exc}")
    if not isinstance(timeline, Mapping):
        return Reading(video, True, error=f"{TIMELINE} is not an object")
    if "prosody" not in timeline:
        return Reading(video, False, why=f"{TIMELINE} has no prosody section: recorded before the gate")
    try:
        return Reading(video, True, tuple(prosody.gate(timeline)))
    except ProsodyError as exc:
        return Reading(video, True, error=str(exc))


def read(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> dict[str, Reading]:
    """Each reel on its ``first`` delivery (slug to video name), read from ``episodes/<slug>/timeline.json``."""
    return {slug: reading(video, Path(episodes) / releases[slug].slug) for slug, video in sorted(first.items())}


def refusals(readings: Mapping[str, Reading]) -> list[Drift]:
    """A :class:`~srstudio.social.Drift` for each reel recorded to the gate that it refuses."""
    out = []
    for r in readings.values():
        if r.refused:
            why = r.error or "; ".join(f.line() for f in r.failing)
            out.append(Drift(r.video, f"prosody: {why} (waive a target with its reason in the line's direction)"))
    return out


def lines(readings: Mapping[str, Reading]) -> list[str]:
    """The advisory report for every reel read, in slug order."""
    return [line for r in readings.values() for line in r.lines()]
