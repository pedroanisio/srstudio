"""Recorded prosody evidence at delivery (ADR 0246).

Missing prosody is a refusal. Historical recording labels grant no release exemption.
Final-master C7 measurement and authority belong to master_gate.evaluate_release."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import prosody
from .prosody import Finding, ProsodyError
from .releases import Release
from .social import Drift

__all__ = ["UNMEASURED", "Reading", "judge", "lines", "read", "reading", "refusals"]

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
        return not self.measured or bool(self.error or self.failing)

    def lines(self) -> list[str]:
        """The report's lines for this reel: one when it is unmeasured, clean or unreadable, else one per finding,
        waived findings with their reasons."""
        head = f"prosody {self.video}"
        if not self.measured:
            return [f"{head}: {UNMEASURED} ({self.why}), REFUSED: missing C7 evidence"]
        if self.error:
            return [f"{head}: REFUSED, {self.error}"]
        if not self.findings:
            return [f"{head}: clean"]
        verdict = "REFUSED" if self.failing else "passes on its waivers"
        return [f"{head}: {verdict}", *(f"  {f.line()}" for f in self.findings)]


def judge(video: str, document: str | bytes | None, where: str = TIMELINE) -> Reading:
    """The gate's reading of a reel's timeline ``document`` (None: there is none), named ``where`` in the report: a
    project's ``timeline.json``, or the one a pilot's package carries."""
    if document is None:
        return Reading(video, False, why=f"no {where}")
    try:
        timeline = json.loads(document)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return Reading(video, True, error=f"{where} cannot be read: {exc}")
    if not isinstance(timeline, Mapping):
        return Reading(video, True, error=f"{where} is not an object")
    if "prosody" not in timeline:
        return Reading(video, False, why=f"{where} has no prosody section: recorded before the gate")
    try:
        return Reading(video, True, tuple(prosody.gate(timeline)))
    except ProsodyError as exc:
        return Reading(video, True, error=str(exc))


def reading(video: str, project: Path) -> Reading:
    """The gate's reading of the reel recorded in ``project``."""
    path = Path(project) / TIMELINE
    if not path.is_file():
        return judge(video, None)
    try:
        return judge(video, path.read_bytes())
    except OSError as exc:
        return Reading(video, True, error=f"{TIMELINE} cannot be read: {exc}")


def read(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> dict[str, Reading]:
    """Each reel on its ``first`` delivery (slug to video name), read from ``episodes/<slug>/timeline.json``."""
    return {slug: reading(video, Path(episodes) / releases[slug].slug) for slug, video in sorted(first.items())}


def refusals(readings: Mapping[str, Reading]) -> list[Drift]:
    """A :class:`~srstudio.social.Drift` for each reel recorded to the gate that it refuses."""
    out = []
    for r in readings.values():
        if r.refused:
            why = r.error or "; ".join(f.line() for f in r.failing)
            out.append(Drift(r.video, f"prosody: {why} (requires a final-master/check-specific authority disposition)"))
    return out


def lines(readings: Mapping[str, Reading]) -> list[str]:
    """The advisory report for every reel read, in slug order."""
    return [line for r in readings.values() for line in r.lines()]
