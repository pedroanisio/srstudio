#!/usr/bin/env python3
"""Copy finished pilots to their own folder on Google Drive. A pilot is not published and can never reach @tuxmeme.

    python3 publish_pilots.py FOLDER               # stage generated/pilots/mind, push it to gdrive:srstudio/pilots/mind
    python3 publish_pilots.py FOLDER --dry-run     # stage, then only preview what rclone would upload
    python3 publish_pilots.py FOLDER --stage-only  # stage, push nothing

FOLDER holds one folder per slug, each with ``<slug>.mp4``, ``cover.jpg``, ``ig.txt``, ``sources.md``, ``notes.md`` and
a package, ``vpkg.zip`` or ``<slug>-<version>.vpkg.zip`` (the highest version wins), delivered as ``vpkg.zip``. Anything
else in a slug's folder is listed and left behind. ``manifest.json`` goes beside the folders, shaped like
``outbox.json``. Staging replaces the last stage whole, so FOLDER is the whole set; the upload is ``rclone copy`` then
``rclone check`` (:func:`srstudio.outbox.push`), which never deletes on Drive.

Anything in ``gdrive:srstudio/ready-to-publish`` can be posted to @tuxmeme, and a write to ``generated/renders/ig``
pushes to it through the ``srstudio-drive`` unit. So this tool only uploads under ``gdrive:srstudio/pilots/``, judged on
the normalised remote it hands to rclone; only stages in ``generated/pilots/mind``; and refuses a slug released on
@tuxmeme. A refused run stages and uploads nothing and exits 2, as does a failed upload.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

from srstudio import outbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_posts as posts  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
REMOTE = "gdrive:srstudio/pilots/mind"
REMOTE_NAME = "gdrive"
ROOT = ("srstudio", "pilots")
NEVER = "ready-to-publish"
STAGE = Path("generated/pilots/mind")
MANIFEST = "manifest.json"
PACKAGE = "vpkg.zip"
ALSO = ("cover.jpg", "ig.txt", PACKAGE, "sources.md", "notes.md")  # what follows <slug>.mp4 in a pilot's folder
WRITTEN = ("sources.md", "notes.md")  # blank is empty for these: a file of spaces says nothing
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
_WATCHED = (("generated", "renders", "ig"), ("generated", "outbox"))


class PilotError(outbox.OutboxError):
    """A remote, a staging folder or a pilot that this tool will not touch."""


def pilots_remote(remote: str) -> str:
    """``remote`` in normal form, the only form rclone is given, if it is on ``gdrive:`` under ``srstudio/pilots/``."""
    if any(c.isspace() or c == "\\" for c in remote):
        raise PilotError(f"{remote!r}: a pilots remote has no spaces or backslashes")
    name, colon, path = remote.partition(":")
    parts = [part for part in posixpath.normpath("/" + path).split("/") if part]
    if NEVER in (part.casefold() for part in parts):
        raise PilotError(f"{remote!r} is {NEVER}, which posts to @tuxmeme: a pilot never goes there")
    if not colon or name != REMOTE_NAME or tuple(parts[: len(ROOT)]) != ROOT or len(parts) <= len(ROOT):
        raise PilotError(f"{remote!r} is not under {REMOTE_NAME}:{'/'.join(ROOT)}/")
    return f"{name}:{'/'.join(parts)}"


def staging_folder(folder: Path) -> Path:
    """``folder``, links resolved, if it is a ``generated/pilots/mind`` outside the folders that reach @tuxmeme."""
    resolved = Path(folder).resolve()
    parts = resolved.parts
    watched = any(parts[i : i + len(w)] == w for w in _WATCHED for i in range(len(parts)))
    if watched or parts[-len(STAGE.parts) :] != STAGE.parts:
        raise PilotError(f"the staging folder must be {STAGE} and outside the delivery folders, got {folder}")
    return resolved


def released(deliveries: Path) -> set[str]:
    """Every name @tuxmeme has used, in lower case: release slugs, video names and folders in ``deliveries``."""
    names = {*posts.VIDEOS, *posts.VIDEOS.values()}
    if not names:
        raise PilotError("the released videos could not be read, so no slug can be cleared")
    if Path(deliveries).is_dir():
        names |= {p.name for p in Path(deliveries).iterdir() if p.is_dir()}
    return {name.casefold() for name in names}


def _package(folder: Path, slug: str) -> Path:
    versioned = outbox.latest_package(folder, slug)
    if versioned is None:
        return folder / PACKAGE
    if (folder / PACKAGE).exists():
        raise PilotError(f"{slug}: both {PACKAGE} and {versioned.name}: which package is the pilot's?")
    return versioned


def bundle(root: Path, slug: str, taken: set[str]) -> outbox.Bundle:
    """The pilot ``slug`` in ``root``, every file present, a real file and not empty."""
    if not _SLUG.fullmatch(slug):
        raise PilotError(f"{slug!r} is not a slug: lower-case letters, digits and hyphens, no path")
    if slug.casefold() in taken:
        raise PilotError(f"{slug} is a released @tuxmeme video")
    folder = Path(root) / slug
    if folder.is_symlink() or not folder.is_dir():
        raise PilotError(f"{slug}: not a folder in {root}")
    names = (f"{slug}.mp4", *ALSO)
    files = tuple(_package(folder, slug) if name == PACKAGE else folder / name for name in names)
    absent = [name for name, f in zip(names, files, strict=True) if f.is_symlink() or not f.is_file()]
    if absent:
        raise PilotError(f"{slug}: missing or not a plain file: {', '.join(absent)}")
    empty = [
        name
        for name, f in zip(names, files, strict=True)
        if not (f.read_bytes().strip() if name in WRITTEN else f.stat().st_size)
    ]
    if empty:
        raise PilotError(f"{slug}: empty: {', '.join(empty)}")
    return outbox.Bundle(slug, files, names=names)


def bundles(root: Path, taken: set[str]) -> list[outbox.Bundle]:
    """Every pilot in ``root``; the operator's dot-files are skipped, anything else that is no pilot is refused."""
    root = Path(root)
    if not root.is_dir():
        raise PilotError(f"{root} is not a folder")
    entries = [p for p in sorted(root.iterdir()) if not (p.name.startswith(".") and p.is_file())]
    if not entries:
        raise PilotError(f"{root} holds no pilots")
    strays = [p.name for p in entries if p.is_file()]
    if strays:
        raise PilotError(f"{root} holds one folder per slug, not {', '.join(strays)}")
    return [bundle(root, p.name, taken) for p in entries]


def left_behind(pilot: outbox.Bundle, root: Path) -> list[str]:
    """What is in the pilot's folder and not delivered, as ``slug/name``."""
    chosen = {f.name for f in pilot.files}
    return [f"{pilot.name}/{p.name}" for p in sorted((Path(root) / pilot.name).iterdir()) if p.name not in chosen]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="one folder per slug")
    parser.add_argument("--stage", type=Path, default=WORKSPACE / STAGE, help=f"default {STAGE}, the only name allowed")
    parser.add_argument(
        "--deliveries", type=Path, default=WORKSPACE / "generated/renders/ig", help="read for the slugs already used"
    )
    parser.add_argument("--remote", default=REMOTE, help=f"rclone destination under pilots/ (default {REMOTE})")
    parser.add_argument("--rclone", default="rclone")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="stage, then only preview the upload")
    mode.add_argument("--stage-only", action="store_true", help="stage, upload nothing")
    args = parser.parse_args(argv)

    try:
        remote = pilots_remote(args.remote)
        stage = staging_folder(args.stage)
        source = args.folder.resolve()
        if source.is_relative_to(stage) or stage.is_relative_to(source):
            raise PilotError(f"the input {source} and the staging folder {stage} overlap")
        ready = bundles(source, released(args.deliveries))
        for pilot in ready:
            for name in left_behind(pilot, source):
                print(f"left behind: {name}")
        stage.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        stage.parent.chmod(0o700)
        manifest = outbox.stage(ready, stage, manifest=MANIFEST)
        print(f"{len(ready)} staged in {manifest.parent}")
        if not args.stage_only:
            outbox.push(manifest.parent, remote, rclone=args.rclone, dry_run=args.dry_run)
            print(f"{'previewed' if args.dry_run else 'copied and checked'}: {remote}")
    except outbox.OutboxError as e:
        print(f"publish_pilots: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
