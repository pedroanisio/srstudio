"""The outbox: every video that passed the publish gate, bundled with what is posted with it, ready to upload.

:func:`ready` asks the publish gate (:func:`srstudio.social.check_delivery`) which videos are current and bundles
each one with its ``ig.txt``, its ``cover.jpg`` and its ``.vpkg.zip`` package (received with a recreation, packed by
:mod:`srstudio.package` for an original episode); a video that drifted, or that has no package, is held back and
reported. :func:`stage` copies the bundles into one private folder per video, with an ``ab.json`` naming the
A/B test and arm of a video in one, next to an ``outbox.json`` of SHA-256s (a pilot's folder uses the same stage and
push under another manifest name: ``episodes/publish_pilots.py``), replacing the previous outbox whole,
so the folder holds exactly what is ready now; the operator's own top-level dot-files are carried over.
:func:`push` uploads that folder with rclone (``copy``, which never deletes on the remote) and then has rclone
check that every staged file arrived with the same hash.

The remote's ``.ignore`` is the record of the reels held out of the queue, one name per line. The publishing side edits
it on Drive, so that copy is the source of truth: a local ``.ignore`` is never uploaded, and :func:`push` reads the
remote's before and after and fails if a line went missing. The only way to take a line out is ``release=``, in the push
that carries the re-delivered reel.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import digest, master_gate
from .authority import Disposition
from .errors import SrstudioError
from .releases import ARMS, arms_of
from .show_numbers import Claim, episode_document
from .social import COVER_NAME, FILE_NAME, Drift, Items, check_delivery, read_manifest

__all__ = [
    "AB_NAME",
    "EPISODE_NAME",
    "IGNORE_NAME",
    "Arm",
    "MANIFEST",
    "MANIFEST_VERSION",
    "NO_PACKAGE",
    "Bundle",
    "OutboxError",
    "delivered_names",
    "latest_package",
    "push",
    "ready",
    "stage",
]

MANIFEST = "outbox.json"
AB_NAME = "ab.json"  # beside a video in an A/B test: an :class:`Arm`'s document, read by the posting job
EPISODE_NAME = "episode.json"  # beside a numbered video: its place on the show (ADR 0074), for the posting job's order
IGNORE_NAME = ".ignore"  # on the remote: the reels held out of the queue, a record this code never overwrites
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
    ``recipient`` arm and who arm ``b`` is written ``to``; ``also`` holds the ``(test, arm)`` of any further test."""

    test: str
    arm: str
    recipient: str = ""
    to: str = ""
    also: tuple[tuple[str, str], ...] = ()

    def document(self) -> dict[str, str | list[dict[str, str]]]:
        extra = {"recipient": self.recipient, "to": self.to}
        document: dict[str, str | list[dict[str, str]]] = {"test": self.test, "arm": self.arm}
        document |= {key: value for key, value in extra.items() if value}
        if self.also:
            document["also"] = [{"test": test, "arm": arm} for test, arm in self.also]
        return document


@dataclass(frozen=True)
class Bundle:
    """One video ready to publish: its folder name in the outbox, the files that go in it, video first, and the
    :class:`Arm` of the A/B tests it is in, if any. ``names`` gives what each of ``files`` is staged as, in order; left
    empty, each keeps its own name. ``episode`` is its number on the show, if it has one."""

    name: str
    files: tuple[Path, ...]
    ab: Arm | None = None
    names: tuple[str, ...] = ()
    episode: Claim | None = None

    @property
    def staged_names(self) -> tuple[str, ...]:
        return self.names or tuple(f.name for f in self.files)


def delivered_names(deliveries: Path, folder: Path) -> set[str]:
    """Every video the delivery folder ``deliveries`` or the outbox ``folder`` shows, by a folder or a manifest entry.
    A folder that is not there is an :class:`OutboxError`: it says nothing about what went out."""
    names = set(read_manifest(deliveries))
    for place in (Path(deliveries), Path(folder)):
        if not place.is_dir():
            raise OutboxError(f"{place} is not a folder, so what was delivered cannot be read from it")
        names |= {p.name for p in place.iterdir() if p.is_dir()}
    return names


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
    numbers: Mapping[str, Claim] | None = None,
    projects: Mapping[str, Path] | None = None,
    release_reports: list[str] | None = None,
    release_approvals: Mapping[str, master_gate.ReleaseApproval] | None = None,
    published: Collection[str] = (),
    scopes: Mapping[str, str] | None = None,
    dispositions: Mapping[str, tuple[Disposition, ...]] | None = None,
) -> tuple[list[Bundle], list[Drift]]:
    """The bundles of every video whose delivery in ``deliveries`` is current, and the drift that held others back.

    ``packages`` maps a video name to its package file; a current video without one is held back
    (:data:`NO_PACKAGE`). A package for a video that is not published, or one that does not exist, raises
    :class:`OutboxError`. An untrustworthy delivery manifest makes nothing ready. ``frozen`` is passed to the gate
    (:func:`~srstudio.social.check_delivery`). ``ab`` maps a video name to the ``(test, arm)`` it is staged with; a
    name that is not published, an empty test or an arm other than ``a`` or ``b`` raises :class:`OutboxError`.
    ``numbers`` maps a video name to its number on the show. ``projects`` supplies
    the cached recording project for every candidate; absence refuses C7. Every
    candidate is checked, including delivered but unpublished files, unless named
    in ``published``. Callers may collect complete results in ``release_reports``,
    and pass trusted ``scopes`` and exact master/check ``dispositions``.
    ``release_approvals`` maps names to ADR 0248 whole-master approvals, passed to
    the gate and valid only for the approved master hash. ``published`` excludes
    names from master evaluation on caller-verified platform publication evidence
    (ADR 0246), never Drive presence. Excluded videos still need current delivery
    and a package; their Bundles remain in the staged manifest (ADR 0249), with an
    exclusion line in ``release_reports``. Unknown names in either argument, or
    names in both, raise :class:`OutboxError`."""
    release_approvals = dict(release_approvals or {})
    published = set(published)
    unknown = sorted((set(release_approvals) | published) - set(items))
    if unknown:
        raise OutboxError(f"release approval or publication names an unknown video: {', '.join(unknown)}")
    overlap = sorted(set(release_approvals) & published)
    if overlap:
        raise OutboxError(f"videos have both release approval and publication exclusion: {', '.join(overlap)}")
    ab = _arms(items, ab)
    numbers = dict(numbers or {})
    strays = sorted(set(numbers) - set(items))
    if strays:
        raise OutboxError(f"a number is named for a video that is not published: {', '.join(strays)}")
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
        if name in published:
            if release_reports is not None:
                release_reports.append(f"excluded: {name}: published on platform (caller evidence)")
        else:
            project = (projects or {}).get(name)
            reading = master_gate.evaluate_release(
                Path(item.video),
                project,
                scope=(scopes or {}).get(name, "reserved"),
                dispositions=(dispositions or {}).get(name, ()),
                release_approval=release_approvals.get(name),
            )
            if release_reports is not None:
                release_reports.extend(reading.lines())
            if reading.refused:
                drift.append(Drift(name, "\n".join(reading.lines())))
                continue
        folder = Path(deliveries) / name
        files = (Path(item.video), folder / FILE_NAME, folder / COVER_NAME, Path(packages[name]))
        bundles.append(Bundle(name, files, ab.get(name), episode=numbers.get(name)))
    return bundles, drift


def _arms(items: Items, ab: Mapping[str, Arm] | None) -> dict[str, Arm]:
    ab = dict(ab or {})
    unknown = sorted(set(ab) - set(items))
    if unknown:
        raise OutboxError(f"an A/B arm is named for a video that is not published: {', '.join(unknown)}")
    for name, chosen in sorted(ab.items()):
        if not chosen.test:
            raise OutboxError(f"{name}: an A/B arm needs its test")
        tests = [(chosen.test, chosen.arm), *chosen.also]
        if not all(test for test, _ in tests):
            raise OutboxError(f"{name}: a further A/B arm needs its test")
        for test, arm in tests:
            if arm not in arms_of(test):
                raise OutboxError(f"{name}: {test} arm {arm!r} is not one of {', '.join(arms_of(test))}")
        if len({test for test, _ in tests}) != len(tests):
            raise OutboxError(f"{name}: one test is named twice in {tests!r}")
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
        if b.episode is not None and EPISODE_NAME in files:
            raise OutboxError(f"{b.name}: a staged file is named {EPISODE_NAME}, which its number is written to")


def _dot_files(folder: Path) -> list[Path]:
    """The operator's regular top-level dot-files in ``folder``: kept across restages."""
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
            if b.episode is not None:
                place = target / EPISODE_NAME
                place.write_text(json.dumps(episode_document(b.episode)) + "\n")
                place.chmod(0o600)
                hashes[EPISODE_NAME] = digest.sha256(place)
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


def _held(text: str) -> list[str]:
    """The records of a ``.ignore``: its lines without their surrounding space, blank ones left out."""
    return [record for line in text.splitlines() if (record := line.strip())]


def _lost(before: str, after: str) -> list[str]:
    """The records of ``before`` that ``after`` no longer has."""
    now = set(_held(after))
    return [record for record in _held(before) if record not in now]


def _step(cmd: list[str], run: Callable[..., subprocess.CompletedProcess], **kw: str) -> None:
    try:
        done = run(cmd, capture_output=True, text=True, check=False, **kw)
    except FileNotFoundError as e:
        raise OutboxError(f"rclone was not found at {cmd[0]!r}") from e
    if done.returncode != 0:
        reason = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no output"]
        raise OutboxError(f"rclone {cmd[1]} failed ({done.returncode}): {reason[0]}")


def _refuse_release(folder: Path, release: Sequence[str], held: str) -> None:
    """A release is a slug Drive holds and this push carries; anything else leaves the push untouched."""
    records = set(_held(held))
    unheld = sorted(slug for slug in release if slug not in records)
    if unheld:
        raise OutboxError(f"release: {', '.join(unheld)} is not held in {IGNORE_NAME}")
    carried = {p.name for p in folder.iterdir() if p.is_dir()} if folder.is_dir() else set()
    absent = sorted(slug for slug in release if slug not in carried)
    if absent:
        raise OutboxError(f"release: {', '.join(absent)} is not in this push's outbox, so it was not re-delivered")


def _release(
    remote: str, release: Sequence[str], held: str, *, rclone: str, run: Callable[..., subprocess.CompletedProcess]
) -> None:
    """Write ``held`` back to ``remote`` without the lines of ``release``, the rest in order, and read it back."""
    kept = "".join(line for line in held.splitlines(keepends=True) if line.strip() not in release)
    _step([rclone, "rcat", f"{remote}/{IGNORE_NAME}"], run, input=kept)
    back = fetch(remote, IGNORE_NAME, rclone=rclone, run=run) or ""
    lost = _lost(kept, back)
    if lost:
        raise OutboxError(f"{IGNORE_NAME} on {remote} lost {', '.join(lost)} in the release: restore them there")
    stuck = sorted(set(release) & set(_held(back)))
    if stuck:
        raise OutboxError(f"{IGNORE_NAME} on {remote} still holds {', '.join(stuck)} after the release")


def push(
    folder: Path,
    remote: str,
    *,
    rclone: str = "rclone",
    dry_run: bool = False,
    run: Callable[..., subprocess.CompletedProcess] | None = None,
    release: Sequence[str] = (),
) -> None:
    """Upload ``folder`` to ``remote`` (``name:path``) with ``rclone copy --checksum``, then ``rclone check
    --one-way`` that every file arrived; both leave the remote's ``.ignore`` out. It is read before and after, and a
    line gone from it is an error. ``release`` names the reels of this push to take out of it, after the check, written
    back and read back; a reel it does not hold, or that this push does not carry, stops the push before the upload. A
    dry run reads ``.ignore``, refuses the same releases and only previews the copy. Raises :class:`OutboxError`."""
    if not _REMOTE.fullmatch(remote) or " " in remote.split(":", 1)[0]:
        raise OutboxError(f"{remote!r} is not an rclone remote (name:path)")
    run = run or _run
    folder = Path(folder)
    keep_off = ["--exclude", f"/{IGNORE_NAME}"]
    before = fetch(remote, IGNORE_NAME, rclone=rclone, run=run) or ""
    _refuse_release(folder, release, before)
    _step([rclone, "copy", str(folder), remote, "--checksum", *keep_off, *(["--dry-run"] if dry_run else [])], run)
    if dry_run:
        return
    _step([rclone, "check", str(folder), remote, "--one-way", *keep_off], run)
    after = fetch(remote, IGNORE_NAME, rclone=rclone, run=run) or ""
    lost = _lost(before, after)
    if lost:
        raise OutboxError(f"{IGNORE_NAME} on {remote} lost {', '.join(lost)} during the push: restore them there")
    if release:
        _release(remote, release, after, rclone=rclone, run=run)
