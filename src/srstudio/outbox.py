"""The outbox: every video that passed the publish gate, bundled with what is posted with it, ready to upload.

:func:`ready` asks the publish gate (:func:`srstudio.social.check_delivery`) which videos are current and bundles
each one with its ``ig.txt``, its ``cover.jpg`` and its ``.vpkg.zip`` package (received with a recreation, packed by
:mod:`srstudio.package` for an original episode); a video that drifted, or that has no package, is held back and
reported. :func:`stage` copies the bundles into one private folder per video, with an ``ab.json`` naming the
A/B test and arm of a video in one, next to an ``outbox.json`` of SHA-256s (a pilot's folder uses the same stage and
push under another manifest name: ``episodes/publish_pilots.py``), replacing the previous outbox whole,
so the folder holds exactly what is ready now; the operator's own top-level dot-files (``.ignore``) are carried
over and uploaded with it.
:func:`push` uploads that folder with rclone (``copy``, which never deletes on the remote) and then has rclone
check that every staged file arrived with the same hash.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import digest
from .errors import SrstudioError
from .releases import ARMS
from .social import COVER_NAME, FILE_NAME, Drift, Items, check_delivery

__all__ = [
    "AB_NAME",
    "Arm",
    "MANIFEST",
    "MANIFEST_VERSION",
    "NO_PACKAGE",
    "Bundle",
    "OutboxError",
    "latest_package",
    "push",
    "ready",
    "stage",
]

MANIFEST = "outbox.json"
AB_NAME = "ab.json"  # beside a video in an A/B test: an :class:`Arm`'s document, read by the posting job
MANIFEST_VERSION = "1.0.0"
NO_PACKAGE = "no .vpkg.zip package: every published video ships with its package"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_REMOTE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*:.*")
_run: Callable[..., subprocess.CompletedProcess] = subprocess.run
_NOT_FOUND = (3, 4)  # rclone's exit codes for a missing directory and a missing file


class OutboxError(SrstudioError, ValueError):
    """A bundle, the outbox folder or an upload that cannot be trusted or completed."""


@dataclass(frozen=True)
class Arm:
    """What a reel's ``ab.json`` says: the first-second ``test`` and its ``arm``, and, in the recipient test, its
    ``recipient`` arm and who arm ``b`` is written ``to``."""

    test: str
    arm: str
    recipient: str = ""
    to: str = ""

    def document(self) -> dict[str, str]:
        extra = {"recipient": self.recipient, "to": self.to}
        return {"test": self.test, "arm": self.arm} | {key: value for key, value in extra.items() if value}


@dataclass(frozen=True)
class Bundle:
    """One video ready to publish: its folder name in the outbox, the files that go in it, video first, and the
    :class:`Arm` of the A/B tests it is in, if any. ``names`` gives what each of ``files`` is staged as, in order; left
    empty, each keeps its own name."""

    name: str
    files: tuple[Path, ...]
    ab: Arm | None = None
    names: tuple[str, ...] = ()

    @property
    def staged_names(self) -> tuple[str, ...]:
        return self.names or tuple(f.name for f in self.files)


def latest_package(folder: Path, slug: str) -> Path | None:
    """The highest ``<slug>-<major>.<minor>.<patch>.vpkg.zip`` in ``folder`` by version number, or ``None``."""
    pattern = re.compile(re.escape(slug) + r"-(\d+)\.(\d+)\.(\d+)\.vpkg\.zip")
    found = []
    for path in Path(folder).glob(f"{slug}-*.vpkg.zip") if Path(folder).is_dir() else ():
        m = pattern.fullmatch(path.name)
        if m:
            found.append((tuple(int(g) for g in m.groups()), path))
    return max(found)[1] if found else None


def ready(
    items: Items,
    deliveries: Path,
    *,
    font: Path,
    packages: Mapping[str, Path] | None = None,
    frozen: Mapping[str, str] | None = None,
    ab: Mapping[str, Arm] | None = None,
) -> tuple[list[Bundle], list[Drift]]:
    """The bundles of every video whose delivery in ``deliveries`` is current, and the drift that held others back.

    ``packages`` maps a video name to its package file; a current video without one is held back
    (:data:`NO_PACKAGE`). A package for a video that is not published, or one that does not exist, raises
    :class:`OutboxError`. An untrustworthy delivery manifest makes nothing ready. ``frozen`` is passed to the gate
    (:func:`~srstudio.social.check_delivery`). ``ab`` maps a video name to the ``(test, arm)`` it is staged with; a
    name that is not published, an empty test or an arm other than ``a`` or ``b`` raises :class:`OutboxError`."""
    ab = _arms(items, ab)
    packages = dict(packages or {})
    unknown = sorted(set(packages) - set(items))
    if unknown:
        raise OutboxError(f"a package is named for a video that is not published: {', '.join(unknown)}")
    missing = sorted(name for name, path in packages.items() if not Path(path).is_file())
    if missing:
        raise OutboxError(f"the package for {', '.join(missing)} is missing")
    drift = list(check_delivery(items, deliveries, font=font, frozen=frozen))
    held = {d.name for d in drift}
    if "*" in held:
        return [], drift
    bundles = []
    for name, item in sorted(items.items()):
        if name in held:
            continue
        if name not in packages:
            drift.append(Drift(name, NO_PACKAGE))
            continue
        folder = Path(deliveries) / name
        files = (Path(item.video), folder / FILE_NAME, folder / COVER_NAME, Path(packages[name]))
        bundles.append(Bundle(name, files, ab.get(name)))
    return bundles, drift


def _arms(items: Items, ab: Mapping[str, Arm] | None) -> dict[str, Arm]:
    ab = dict(ab or {})
    unknown = sorted(set(ab) - set(items))
    if unknown:
        raise OutboxError(f"an A/B arm is named for a video that is not published: {', '.join(unknown)}")
    for name, chosen in sorted(ab.items()):
        if not chosen.test:
            raise OutboxError(f"{name}: an A/B arm needs its test")
        if chosen.arm not in ARMS:
            raise OutboxError(f"{name}: arm {chosen.arm!r} is not one of {', '.join(ARMS)}")
        if chosen.recipient and chosen.recipient not in ARMS:
            raise OutboxError(f"{name}: recipient {chosen.recipient!r} is not one of {', '.join(ARMS)}")
        if (chosen.recipient == "b") != bool(chosen.to):
            raise OutboxError(
                f"{name}: recipient {chosen.recipient!r}, to {chosen.to!r}: arm b, and only it, names who"
            )
    return ab


def _check(bundles: Sequence[Bundle]) -> None:
    names = [b.name for b in bundles]
    for name in names:
        if not _NAME.fullmatch(name):
            raise OutboxError(f"{name!r} is not a usable folder name")
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise OutboxError(f"two bundles are named {', '.join(twice)}: a name can be staged only once, not twice")
    for b in bundles:
        if b.names and len(b.names) != len(b.files):
            raise OutboxError(f"{b.name}: {len(b.names)} names for {len(b.files)} files")
        unusable = sorted(f for f in b.names if not _NAME.fullmatch(f))
        if unusable:
            raise OutboxError(f"{b.name}: {unusable[0]!r} is not a usable file name")
        files = list(b.staged_names)
        if len(set(files)) != len(files):
            raise OutboxError(f"{b.name}: two files share one name, so one would be staged twice")
        if b.ab is not None and AB_NAME in files:
            raise OutboxError(f"{b.name}: a staged file is named {AB_NAME}, which its A/B arm is written to")


def _dot_files(folder: Path) -> list[Path]:
    """The operator's regular top-level dot-files in ``folder``: kept across restages and uploaded with the rest."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.name.startswith(".") and p.is_file() and not p.is_symlink())


def stage(bundles: Sequence[Bundle], folder: Path, *, manifest: str = MANIFEST) -> Path:
    """Replace ``folder`` with one private folder per bundle and the ``manifest`` of hashes; returns its path.

    The new outbox is built beside ``folder`` and swapped in, so a failure leaves the previous one in place. A
    ``folder`` that holds anything but a previous outbox is refused and left untouched. The operator's top-level
    dot-files in ``folder`` (``.ignore``) are kept as they are, content and mode."""
    _check(bundles)
    folder = Path(folder)
    if folder.exists() and any(folder.iterdir()) and not (folder / manifest).is_file():
        raise OutboxError(f"{folder} is not an outbox (no {manifest}); refusing to replace it")
    folder.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=f".{folder.name}-", dir=folder.parent))  # mode 700
    try:
        videos: dict[str, dict[str, str]] = {}
        for b in bundles:
            target = build / b.name
            target.mkdir(mode=0o700)
            hashes = {}
            for source, staged in zip(b.files, b.staged_names, strict=True):
                before = digest.sha256(source)
                copy = target / staged
                shutil.copyfile(source, copy)
                copy.chmod(0o600)
                hashes[copy.name] = digest.sha256(copy)
                if hashes[copy.name] != before:
                    raise OutboxError(f"{source} changed while it was staged")
            if b.ab is not None:
                arm = target / AB_NAME
                arm.write_text(json.dumps(b.ab.document()) + "\n")
                arm.chmod(0o600)
                hashes[AB_NAME] = digest.sha256(arm)
            videos[b.name] = hashes
        document = build / manifest
        document.write_text(json.dumps({"version": MANIFEST_VERSION, "videos": videos}, indent=2) + "\n")
        document.chmod(0o600)
        for kept in _dot_files(folder):
            shutil.copy2(kept, build / kept.name)
        if folder.exists():
            old = Path(tempfile.mkdtemp(prefix=f".{folder.name}-old-", dir=folder.parent))
            folder.replace(old / folder.name)
            build.replace(folder)
            shutil.rmtree(old)
        else:
            build.replace(folder)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise
    return folder / manifest


def fetch(
    remote: str, name: str, *, rclone: str = "rclone", run: Callable[..., subprocess.CompletedProcess] | None = None
) -> str | None:
    """The text of ``name`` in ``remote``, or None when it is not there. Any other failure is an
    :class:`OutboxError`, so an unreachable remote never reads as an empty one."""
    run = run or _run
    try:
        done = run([rclone, "cat", f"{remote}/{name}"], capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise OutboxError(f"rclone was not found at {rclone!r}") from e
    if done.returncode in _NOT_FOUND:
        return None
    if done.returncode != 0:
        reason = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no output"]
        raise OutboxError(f"reading {name} from {remote} failed: {reason[0]}")
    return str(done.stdout)


def push(
    folder: Path,
    remote: str,
    *,
    rclone: str = "rclone",
    dry_run: bool = False,
    run: Callable[..., subprocess.CompletedProcess] | None = None,
) -> None:
    """Upload ``folder`` to ``remote`` (``name:path``) with ``rclone copy --checksum``, then ``rclone check
    --one-way`` that every file arrived; a dry run only previews the copy. Raises :class:`OutboxError`."""
    if not _REMOTE.fullmatch(remote) or " " in remote.split(":", 1)[0]:
        raise OutboxError(f"{remote!r} is not an rclone remote (name:path)")
    run = run or _run
    steps = [[rclone, "copy", str(folder), remote, "--checksum", *(["--dry-run"] if dry_run else [])]]
    if not dry_run:
        steps.append([rclone, "check", str(folder), remote, "--one-way"])
    for cmd in steps:
        try:
            done = run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as e:
            raise OutboxError(f"rclone was not found at {rclone!r}") from e
        if done.returncode != 0:
            reason = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no output"]
            raise OutboxError(f"rclone {cmd[1]} failed ({done.returncode}): {reason[0]}")
