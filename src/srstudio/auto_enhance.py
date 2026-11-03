"""Auto-enhance: every video leaves the process better for the next one (ADR 0056, ADR 0226).

The rule is on by default. An agent that builds a video finishes it with one real change to the process before the
video's first delivery. The commit names the video and what kind of change it is, as trailers:

    Enhances: <slug>
    Enhancement-Kind: <one of KINDS>

Since the split (ADR 0220) the process lives in two repositories, and a change counts in either: on ``develop`` of
srstudio-episodes (its tools, its reel process, the skill), or in this library at the commit the episodes pin (its
``src/srstudio/`` and tools). Each is a :class:`History` read by its own :class:`Layout`; the callers name both
checkouts, and :func:`pin` reads which library commit the episodes build on from their ``pyproject.toml``.

:func:`refused` is the gate ``deliver`` and ``publish_pilots.py`` run. It reads the histories, so nothing can be claimed
without the commit that does it, and a rebase or a cherry-pick keeps the claim. It proves a change landed and has a
test or a versioned skill rule; it cannot prove the next video is funnier (ADR 0015). With the mode off the gate clears
every video. Only the operator turns it off: ``srstudio enhance off`` writes :data:`SETTINGS` in the episodes
repository, and nowhere else.

Commit messages are model output, so they are parsed into :class:`Enhancement`, checked against the diff, and refused
with a reason. Whatever cannot be read fails closed: a broken setting never reads as off, and a missing pin or library
checkout is an :class:`EnhanceError`, never an empty ledger.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from .social import DeliveryError, Drift

__all__ = ["BRANCH", "EPISODES_REPO", "KINDS", "SDK_REPO", "SETTINGS", "SKILL", "VERSION", "EnhanceError"]
__all__ += ["Enhancement", "History", "Layout", "Setting", "checkout", "enabled", "histories", "ledger", "ledgers"]
__all__ += ["pin", "refused", "set_mode", "setting", "unsound"]

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
PYPROJECT = "pyproject.toml"
GIT_SECONDS = 60
_ON, _OFF = "on", "off"
_FIELD, _RECORD = "\x1f", "\x1e"
_FORMAT = _FIELD.join(
    (
        "%H",
        "%ct",
        "%(trailers:key=Enhances,valueonly,separator=%x2C)",
        "%(trailers:key=Enhancement-Kind,valueonly,separator=%x2C)",
        "%s",
        f"%b{_RECORD}",
    )
).replace(_FIELD, "%x1f").replace(_RECORD, "%x1e")  # fmt: skip
_NEW_TEST = re.compile(r"^\+\s*(?:async\s+)?def test_\w+", re.MULTILINE)
_BUMP = re.compile(r"^\+schema_version: ", re.MULTILINE)
_TRAILER = re.compile(r"^([A-Za-z][\w-]*):\s*(\S.*)$")
_PIN = re.compile(r'"srstudio\s*@\s*git\+[^"\s]+@([0-9a-f]{40})"')  # a quoted dependency, read as tools/gate.sh does
_SHA = re.compile(r"[0-9a-f]{40}")
STRANDED = "its trailers sit in a middle paragraph, and git reads only the last one as trailers"


class EnhanceError(DeliveryError):
    """The mode, the pin or a history cannot be read, so no video can be cleared."""


@dataclass(frozen=True)
class Enhancement:
    """A commit that claims to enhance a video, with every reason its claim does not count."""

    commit: str
    slugs: tuple[str, ...]
    kinds: tuple[str, ...]
    subject: str
    problems: tuple[str, ...]
    source: str  # the name of the History it was read from
    committed: int  # the commit time, in seconds since the epoch: the newest claim of two repositories speaks


@dataclass(frozen=True)
class Layout:
    """Which paths of one repository are the process, and which belong to one video."""

    library: tuple[str, ...]  # code and tools: a change here counts with a new test under tests/
    skill: str = SKILL  # the skill: a change here counts with its schema_version bumped
    episodes: str = "episodes/"  # a file here named after the slug is the video's own script or release
    pilots: str = "pilots/"  # a folder here named by the slug is the video's own


EPISODES_REPO = Layout(library=("tools/",))  # srstudio-episodes: its tools hold the reel process (ADR 0220)
SDK_REPO = Layout(library=("src/srstudio/", "tools/"))  # this library; its history up to the split holds the reels
# and the skill too, so a claim made there before the split reads as it did


@dataclass(frozen=True)
class History:
    """The commits of one repository that can enhance a video: ``revisions`` of ``repo``, read by ``layout``."""

    name: str
    repo: Path
    revisions: str
    layout: Layout

    def __str__(self) -> str:
        return f"{self.name} {self.revisions[:12] if _SHA.fullmatch(self.revisions) else self.revisions}"


@dataclass(frozen=True)
class Setting:
    """The mode and where it came from: ``read`` is false when :data:`SETTINGS` is absent and ``on`` is the default."""

    on: bool
    path: Path
    read: bool

    def __str__(self) -> str:
        mode = _ON if self.on else _OFF
        return f"{mode} (read from {self.path})" if self.read else f"{mode} (the default: {self.path} does not exist)"


def setting(repo: Path) -> Setting:
    """The mode in ``repo``'s :data:`SETTINGS`: on when the file is absent, and said so; anything unreadable raises."""
    path = Path(repo) / SETTINGS
    if not path.exists():
        return Setting(True, path, read=False)
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
    return Setting(data["mode"] == _ON, path, read=True)


def enabled(repo: Path) -> bool:
    """Whether the rule binds: true when :data:`SETTINGS` is absent, or says ``on``; anything unreadable raises."""
    return setting(repo).on


def set_mode(repo: Path, *, on: bool) -> None:
    """Record the mode in :data:`SETTINGS`. The operator's decision alone."""
    path = Path(repo) / SETTINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"version": VERSION, "mode": _ON if on else _OFF}, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def pin(repo: Path) -> str:
    """The srstudio commit ``repo``'s ``pyproject.toml`` depends on. Pinning exactly one is what makes ``repo`` an
    episodes repository (ADR 0220); anything else raises."""
    path = Path(repo) / PYPROJECT
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise EnhanceError(f"{repo} is no episodes repository: {path} cannot be read: {exc}") from exc
    found = _PIN.findall(text)
    if len(found) != 1:
        raise EnhanceError(f"{repo} is no episodes repository: {path} pins no single srstudio commit (ADR 0220)")
    return found[0]


def checkout(named: Path | None) -> Path:
    """The srstudio checkout at ``named``, or the one this package was imported from; refused unless it is a git
    checkout of the library, since a ledger read from anything else would be empty, not wrong."""
    root = Path(named) if named else Path(__file__).resolve().parents[2]
    if not (root / "src" / "srstudio" / "__init__.py").is_file() or not (root / ".git").exists():
        raise EnhanceError(f"no srstudio checkout at {root}: name one with SRSTUDIO_SDK")
    return root


def histories(repo: Path, sdk: Path) -> tuple[History, History]:
    """Where an enhancement of a reel built in the episodes repository ``repo`` can land: its ``develop``, and the
    library checkout ``sdk`` at the commit ``repo`` pins."""
    return (
        History("srstudio-episodes", Path(repo), BRANCH, EPISODES_REPO),
        History("srstudio", Path(sdk), pin(repo), SDK_REPO),
    )


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


def _own(path: str, slug: str, layout: Layout) -> bool:
    """Whether ``path`` belongs to the video ``slug``: its scripts, its release or its pilot folder."""
    if path.startswith(layout.episodes):
        return Path(path).name.startswith(slug.replace("-", "_"))
    return path.startswith(layout.pilots) and slug in Path(path).parts


def _problems(history: History, commit: str, slugs: tuple[str, ...], kinds: tuple[str, ...]) -> tuple[str, ...]:
    repo, layout = history.repo, history.layout
    found = []
    if len(slugs) != 1:
        found.append(f"names {len(slugs)} videos: one commit enhances one video")
    if len(kinds) != 1 or kinds[0] not in KINDS:
        found.append(f"kind {', '.join(kinds) or 'missing'}: Enhancement-Kind must be one of {', '.join(KINDS)}")
    paths = _git(repo, "show", "--format=", "--name-only", "--no-renames", commit).split("\n")
    if any(_own(path, slug, layout) for path in paths for slug in slugs):
        found.append("touches the video's own files: an enhancement is for the next video")
    if any(path.startswith(layout.library) for path in paths):
        if not _NEW_TEST.search(_git(repo, "show", "--format=", "-U0", commit, "--", "tests")):
            found.append("adds no test to prove the change")
    elif layout.skill in paths:
        if not _BUMP.search(_git(repo, "show", "--format=", "-U0", commit, "--", layout.skill)):
            found.append("bumps no schema_version in the skill")
    else:
        found.append("changes no library, tool or skill")
    return tuple(found)


def ledger(history: History) -> list[Enhancement]:
    """Every commit of ``history`` that carries the trailers, newest first, each with what is wrong with it."""
    log = _git(history.repo, "log", history.revisions, "--no-merges", "--grep=^Enhances:", f"--format={_FORMAT}")
    rows = []
    for record in filter(str.strip, log.split(_RECORD)):
        commit, when, named, kind, subject, body = record.strip().split(_FIELD)
        slugs = tuple(filter(None, (s.strip() for s in named.split(","))))
        problems: tuple[str, ...] = ()
        if slugs:
            kinds = tuple(filter(None, (k.strip() for k in kind.split(","))))
        elif stranded := _stranded(body):  # a mention in prose claims nothing; a trailer block in the wrong place does
            slugs, kinds = stranded
            problems = (STRANDED,)
        else:
            continue
        problems += _problems(history, commit, slugs, kinds)
        rows.append(Enhancement(commit, slugs, kinds, subject, problems, history.name, int(when)))
    return rows


def ledgers(sources: Iterable[History]) -> list[Enhancement]:
    """The ledgers of every history in ``sources`` as one, newest commit first."""
    return sorted((row for history in sources for row in ledger(history)), key=lambda row: -row.committed)


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


def unsound(history: History) -> list[Enhancement]:
    """The claims the branch checked out in ``history.repo`` would land that could not count: history cannot be
    rewritten after the merge."""
    return [row for row in ledger(replace(history, revisions=f"{BRANCH}..HEAD")) if row.problems]


def refused(videos: Mapping[str, str], repo: Path, sdk: Path | None) -> list[Drift]:
    """Why each of ``videos`` (slug to video name) cannot have its first delivery from the episodes repository
    ``repo``, reading the library checkout ``sdk`` (None: the one this package came from) at ``repo``'s pin. A slug
    with one good commit in either history is clear; with only bad ones, the newest speaks. Empty when the mode is off
    or no video is new, and then neither the pin nor the library is read."""
    if not videos or not enabled(repo):
        return []
    sources = histories(repo, checkout(sdk))
    rows = ledgers(sources)
    where = " or ".join(map(str, sources))
    drift = []
    for slug, name in videos.items():
        claims = [row for row in rows if slug in row.slugs]
        if not claims:
            reason = f"no commit on {where} carries the trailer Enhances: {slug} (auto-enhance, ADR 0056)"
            drift.append(Drift(name, reason))
        elif all(row.problems for row in claims):
            why = "; ".join(claims[0].problems)
            drift.append(Drift(name, f"enhancement {claims[0].commit[:7]} does not count: {why}"))
    return drift
