"""Auto-enhance: every video leaves the process better for the next one (ADR 0056).

The rule is on by default. An agent that builds a video finishes it with one real change to the process, merged into
``develop`` before the video's first delivery. The commit names the video and what kind of change it is, as trailers:

    Enhances: <slug>
    Enhancement-Kind: <one of KINDS>

:func:`refused` is the gate ``deliver`` and ``publish_pilots.py`` run. It reads the history, so nothing can be claimed
without the commit that does it, and a rebase or a cherry-pick keeps the claim. It proves a change landed and has a
test or a versioned skill rule; it cannot prove the next video is funnier (ADR 0015). With the mode off the gate clears
every video. Only the operator turns it off: ``srstudio enhance off`` writes :data:`SETTINGS`.

Commit messages are model output, so they are parsed into :class:`Enhancement`, checked against the diff, and refused
with a reason. Whatever cannot be read fails closed: a broken setting never reads as off.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .social import DeliveryError, Drift

__all__ = ["BRANCH", "KINDS", "SETTINGS", "SKILL", "VERSION", "EnhanceError", "Enhancement"]
__all__ += ["enabled", "ledger", "refused", "set_mode", "unsound"]

KINDS = {
    "comedy": "funnier: joke mechanisms, beat timing, hooks, payoffs, rubric rules",
    "story": "stronger shapes: formats, escalation, endings, replay loops, premise selection",
    "picture": "visual quality: grade, light, depth, palette, composition, finish",
    "motion": "livelier movement: gestures, walks, reactions, secondary motion, timing curves",
    "effects": "better fx: transitions, engine effects, particles, text animators",
    "camera": "better shots: moves, framing, cuts, parallax",
    "music": "better music: scores, stings, ducking, the mix",
    "sound": "better foley: ambience, impacts, room tone, sound on the beat",
    "voice": "better voices: casting, delivery settings, pacing, lip sync",
    "character": "better characters: written descriptions, expressions, poses, wardrobe, rigs of the approved cast",
    "props": "new or better props, reusable by the next reel",
    "sets": "new or better locations and rooms",
    "readability": "more readable captions and on-screen text: size, timing, placement, emphasis",
    "covers": "better covers and first frames: headline, crop, contrast",
    "checks": "a new automatic check that catches a defect before delivery",
    "speed": "a cheaper or faster process: build, render, takes, reuse of the catalog",
    "insight": "a lesson from the account's numbers turned into a rule or a default",
}  # the possibilities, closed so that a ledger can be counted; a new kind is added here with its description
SETTINGS = "episodes/auto_enhance.json"
SKILL = ".claude/skills/funny-reels/SKILL.md"
BRANCH = "develop"  # what the next video is built from: an enhancement elsewhere helps no video yet
VERSION = "1.0.0"
LIBRARY = ("src/srstudio/", "tools/")
EPISODES = "episodes/"
PILOTS = "pilots/"
GIT_SECONDS = 60
_ON, _OFF = "on", "off"
_FIELD, _RECORD = "\x1f", "\x1e"
_FORMAT = _FIELD.join(
    (
        "%H",
        "%(trailers:key=Enhances,valueonly,separator=%x2C)",
        "%(trailers:key=Enhancement-Kind,valueonly,separator=%x2C)",
        "%s",
        f"%b{_RECORD}",
    )
).replace(_FIELD, "%x1f").replace(_RECORD, "%x1e")  # fmt: skip
_NEW_TEST = re.compile(r"^\+\s*(?:async\s+)?def test_\w+", re.MULTILINE)
_BUMP = re.compile(r"^\+schema_version: ", re.MULTILINE)
_TRAILER = re.compile(r"^([A-Za-z][\w-]*):\s*(\S.*)$")
STRANDED = "its trailers sit in a middle paragraph, and git reads only the last one as trailers"


class EnhanceError(DeliveryError):
    """The mode or the history cannot be read, so no video can be cleared."""


@dataclass(frozen=True)
class Enhancement:
    """A commit that claims to enhance a video, with every reason its claim does not count."""

    commit: str
    slugs: tuple[str, ...]
    kinds: tuple[str, ...]
    subject: str
    problems: tuple[str, ...]


def enabled(repo: Path) -> bool:
    """Whether the rule binds: true when :data:`SETTINGS` is absent, or says ``on``; anything unreadable raises."""
    path = Path(repo) / SETTINGS
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EnhanceError(f"{path} cannot be read: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"version", "mode"}:
        raise EnhanceError(f"{path} must hold exactly version and mode")
    if data["version"] != VERSION:
        raise EnhanceError(f"{path} is version {data['version']!r}; this srstudio reads {VERSION}")
    if data["mode"] not in (_ON, _OFF):
        raise EnhanceError(f"{path}: mode must be {_ON!r} or {_OFF!r}, got {data['mode']!r}")
    return bool(data["mode"] == _ON)


def set_mode(repo: Path, *, on: bool) -> None:
    """Record the mode in :data:`SETTINGS`. The operator's decision alone."""
    path = Path(repo) / SETTINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"version": VERSION, "mode": _ON if on else _OFF}, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def _git(repo: Path, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, timeout=GIT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnhanceError(f"cannot read the history of {repo}: {exc}") from exc
    if done.returncode != 0:
        raise EnhanceError(f"cannot read the history of {repo}: {done.stderr.strip()}")
    return done.stdout


def _own(path: str, slug: str) -> bool:
    """Whether ``path`` belongs to the video ``slug``: its scripts, its release or its pilot folder."""
    if path.startswith(EPISODES):
        return Path(path).name.startswith(slug.replace("-", "_"))
    return path.startswith(PILOTS) and slug in Path(path).parts


def _problems(repo: Path, commit: str, slugs: tuple[str, ...], kinds: tuple[str, ...]) -> tuple[str, ...]:
    found = []
    if len(slugs) != 1:
        found.append(f"names {len(slugs)} videos: one commit enhances one video")
    if len(kinds) != 1 or kinds[0] not in KINDS:
        found.append(f"kind {', '.join(kinds) or 'missing'}: Enhancement-Kind must be one of {', '.join(KINDS)}")
    paths = _git(repo, "show", "--format=", "--name-only", "--no-renames", commit).split("\n")
    if any(_own(path, slug) for path in paths for slug in slugs):
        found.append("touches the video's own files: an enhancement is for the next video")
    if any(path.startswith(LIBRARY) for path in paths):
        if not _NEW_TEST.search(_git(repo, "show", "--format=", "-U0", commit, "--", "tests")):
            found.append("adds no test to prove the change")
    elif SKILL in paths:
        if not _BUMP.search(_git(repo, "show", "--format=", "-U0", commit, "--", SKILL)):
            found.append("bumps no schema_version in the skill")
    else:
        found.append("changes no library, tool or skill")
    return tuple(found)


def ledger(repo: Path, revisions: str = BRANCH) -> list[Enhancement]:
    """Every commit in ``revisions`` that carries the trailers, newest first, each with what is wrong with it."""
    log = _git(repo, "log", revisions, "--no-merges", "--grep=^Enhances:", f"--format={_FORMAT}")
    rows = []
    for record in filter(str.strip, log.split(_RECORD)):
        commit, named, kind, subject, body = record.strip().split(_FIELD)
        slugs = tuple(filter(None, (s.strip() for s in named.split(","))))
        if slugs:
            kinds = tuple(filter(None, (k.strip() for k in kind.split(","))))
            rows.append(Enhancement(commit, slugs, kinds, subject, _problems(repo, commit, slugs, kinds)))
        elif stranded := _stranded(body):  # a mention in prose claims nothing; a trailer block in the wrong place does
            slugs, kinds = stranded
            problems = (STRANDED, *_problems(repo, commit, slugs, kinds))
            rows.append(Enhancement(commit, slugs, kinds, subject, problems))
    return rows


def _stranded(body: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """The videos and kinds of a block of only trailer lines, naming both, that is not the message's last paragraph."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    for block in paragraphs[:-1]:
        pairs = [_TRAILER.match(line.strip()) for line in block.splitlines()]
        found = [(m.group(1), m.group(2).strip()) for m in pairs if m]
        if len(found) == len(pairs) and {"Enhances", "Enhancement-Kind"} <= {key for key, _ in found}:
            return (
                tuple(value for key, value in found if key == "Enhances"),
                tuple(value for key, value in found if key == "Enhancement-Kind"),
            )
    return None


def unsound(repo: Path) -> list[Enhancement]:
    """The claims this branch would land that could not count: history cannot be rewritten after the merge."""
    return [row for row in ledger(repo, f"{BRANCH}..HEAD") if row.problems]


def refused(videos: Mapping[str, str], repo: Path) -> list[Drift]:
    """Why each of ``videos`` (slug to video name) cannot have its first delivery. A slug with one good commit is
    clear; with several bad ones, the newest speaks. Empty when the mode is off or no video is new."""
    if not videos or not enabled(repo):
        return []
    rows = ledger(repo)
    drift = []
    for slug, name in videos.items():
        claims = [row for row in rows if slug in row.slugs]
        if not claims:
            reason = f"no commit on {BRANCH} carries the trailer Enhances: {slug} (auto-enhance, ADR 0056)"
            drift.append(Drift(name, reason))
        elif all(row.problems for row in claims):
            why = "; ".join(claims[0].problems)
            drift.append(Drift(name, f"enhancement {claims[0].commit[:7]} does not count: {why}"))
    return drift
