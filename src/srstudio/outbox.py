"""The outbox: every video that passed the publish gate, bundled with what is posted with it, ready to upload.

:func:`ready` asks the publish gate (:func:`srstudio.social.check_delivery`) which videos are current and bundles
each one with its ``ig.txt``, its ``cover.jpg`` and, for a recreation, its ``.vpkg.zip`` package; a video that
drifted is held back and reported. :func:`stage` copies the bundles into one private folder per video next to an
``outbox.json`` of SHA-256s, replacing the previous outbox whole, so the folder holds exactly what is ready now;
the operator's own top-level dot-files (``.ignore``) are carried over and uploaded with it.
:func:`push` uploads that folder with rclone (``copy``, which never deletes on the remote) and then has rclone
check that every staged file arrived with the same hash.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .social import COVER_NAME, FILE_NAME, Drift, Items, check_delivery

__all__ = ["MANIFEST", "MANIFEST_VERSION", "Bundle", "OutboxError", "latest_package", "push", "ready", "stage"]

MANIFEST = "outbox.json"
MANIFEST_VERSION = "1.0.0"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_REMOTE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*:.*")
_run: Callable[..., subprocess.CompletedProcess] = subprocess.run


class OutboxError(ValueError):
    """A bundle, the outbox folder or an upload that cannot be trusted or completed."""


@dataclass(frozen=True)
class Bundle:
    """One video ready to publish: its folder name in the outbox and the files that go in it, video first."""

    name: str
    files: tuple[Path, ...]


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
    items: Items, deliveries: Path, *, font: Path, packages: Mapping[str, Path] | None = None
) -> tuple[list[Bundle], list[Drift]]:
    """The bundles of every video whose delivery in ``deliveries`` is current, and the drift that held others back.

    ``packages`` maps a video name to its package file; a package for a video that is not published, or one that
    does not exist, raises :class:`OutboxError`. An untrustworthy delivery manifest makes nothing ready."""
    packages = dict(packages or {})
    unknown = sorted(set(packages) - set(items))
    if unknown:
        raise OutboxError(f"a package is named for a video that is not published: {', '.join(unknown)}")
    missing = sorted(name for name, path in packages.items() if not Path(path).is_file())
    if missing:
        raise OutboxError(f"the package for {', '.join(missing)} is missing")
    drift = check_delivery(items, deliveries, font=font)
    held = {d.name for d in drift}
    if "*" in held:
        return [], drift
    bundles = []
    for name, item in sorted(items.items()):
        if name in held:
            continue
        folder = Path(deliveries) / name
        files = (Path(item.video), folder / FILE_NAME, folder / COVER_NAME)
        bundles.append(Bundle(name, files + ((Path(packages[name]),) if name in packages else ())))
    return bundles, drift


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _check(bundles: Sequence[Bundle]) -> None:
    names = [b.name for b in bundles]
    for name in names:
        if not _NAME.fullmatch(name):
            raise OutboxError(f"{name!r} is not a usable folder name")
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise OutboxError(f"two bundles are named {', '.join(twice)}: a name can be staged only once, not twice")
    for b in bundles:
        files = [f.name for f in b.files]
        if len(set(files)) != len(files):
            raise OutboxError(f"{b.name}: two files share one name, so one would be staged twice")


def _dot_files(folder: Path) -> list[Path]:
    """The operator's regular top-level dot-files in ``folder``: kept across restages and uploaded with the rest."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.name.startswith(".") and p.is_file() and not p.is_symlink())


def stage(bundles: Sequence[Bundle], folder: Path) -> Path:
    """Replace ``folder`` with one private folder per bundle and ``outbox.json``; returns the manifest's path.

    The new outbox is built beside ``folder`` and swapped in, so a failure leaves the previous one in place. A
    ``folder`` that holds anything but a previous outbox is refused and left untouched. The operator's top-level
    dot-files in ``folder`` (``.ignore``) are kept as they are, content and mode."""
    _check(bundles)
    folder = Path(folder)
    if folder.exists() and any(folder.iterdir()) and not (folder / MANIFEST).is_file():
        raise OutboxError(f"{folder} is not an outbox (no {MANIFEST}); refusing to replace it")
    folder.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=f".{folder.name}-", dir=folder.parent))  # mode 700
    try:
        videos: dict[str, dict[str, str]] = {}
        for b in bundles:
            target = build / b.name
            target.mkdir(mode=0o700)
            hashes = {}
            for source in b.files:
                before = _sha(source)
                copy = target / source.name
                shutil.copyfile(source, copy)
                copy.chmod(0o600)
                hashes[copy.name] = _sha(copy)
                if hashes[copy.name] != before:
                    raise OutboxError(f"{source} changed while it was staged")
            videos[b.name] = hashes
        manifest = build / MANIFEST
        manifest.write_text(json.dumps({"version": MANIFEST_VERSION, "videos": videos}, indent=2) + "\n")
        manifest.chmod(0o600)
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
    return folder / MANIFEST


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
