#!/usr/bin/env python3
"""Copy finished pilots to their own folder on Google Drive. A pilot is not published and can never reach Okayville.

    python3 publish_pilots.py FOLDER                # stage generated/pilots/mind, push to gdrive:srstudio/pilots/mind
    python3 publish_pilots.py FOLDER --series maps  # the same for generated/pilots/maps and gdrive:srstudio/pilots/maps
    python3 publish_pilots.py FOLDER --dry-run      # stage, then only preview what rclone would upload
    python3 publish_pilots.py FOLDER --stage-only   # stage, push nothing

FOLDER holds one folder per slug, each with ``<slug>.mp4``, ``cover.jpg``, ``ig.txt``, ``sources.md``, ``notes.md`` and
a package, ``vpkg.zip`` or ``<slug>-<version>.vpkg.zip`` (the highest version wins), delivered as ``vpkg.zip``. Anything
else in a slug's folder is listed and left behind. ``manifest.json`` goes beside the folders, shaped like
``outbox.json``. Staging replaces the last stage whole, so FOLDER is the whole set; the upload is ``rclone copy`` then
``rclone check`` (:func:`srstudio.outbox.push`), which never deletes on Drive.

Anything in ``gdrive:srstudio/ready-to-publish`` can be posted to @okayville.tv, and a write to
``generated/renders/ig`` pushes to it through the ``srstudio-drive`` unit. So this tool only uploads under
``gdrive:srstudio/pilots/``, judged on the normalised remote it hands to rclone; only stages in
``generated/pilots/<series>``; and refuses a slug released on Okayville. A series never crosses another: its stage and
remote are the only ones it accepts, and a slug with a folder under another series' ``pilots/`` in this repository is
refused. A new pilot of a comedy series needs ``comedy-author`` and ``comedy-reviewer`` in the frontmatter of its
``notes.md``, the lower at the floor or above (ADR 0064); a series in :data:`NOT_COMEDY` owes none. A new pilot of any
series carries at most five hashtags in its ``ig.txt`` (ADR 0065). A refused run stages and uploads nothing and exits
2, as does a failed upload.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path

from srstudio import auto_enhance, comedy_floor, outbox, social

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_posts as posts  # noqa: E402

REPO = Path(__file__).resolve().parents[1]  # its history holds the enhancements, its settings the mode (ADR 0056)
WORKSPACE = Path(__file__).resolve().parents[2]
REMOTE = "gdrive:srstudio/pilots/mind"
REMOTE_NAME = "gdrive"
ROOT = ("srstudio", "pilots")
NEVER = "ready-to-publish"
STAGE = Path("generated/pilots/mind")
SERIES = ("mind", "maps", "news", "host", "smallprint")  # the first is the default
NOT_COMEDY = frozenset({"mind", "maps", "smallprint"})  # ADR 0064; Small Print is an explainer (ADR 0195)
MANIFEST = "manifest.json"
PACKAGE = "vpkg.zip"
NOTES = "notes.md"
CAPTION = social.FILE_NAME
ALSO = ("cover.jpg", CAPTION, PACKAGE, "sources.md", NOTES)  # what follows <slug>.mp4 in a pilot's folder
WRITTEN = ("sources.md", NOTES)  # blank is empty for these: a file of spaces says nothing
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
_WATCHED = (("generated", "renders", "ig"), ("generated", "outbox"))


class PilotError(outbox.OutboxError):
    """A remote, a staging folder or a pilot that this tool will not touch."""


def _known(series: str) -> str:
    if series not in SERIES:
        raise PilotError(f"{series!r} is not a series; there are {', '.join(SERIES)}")
    return series


def stage_of(series: str) -> Path:
    """The only staging folder of ``series``."""
    return STAGE.parent / _known(series)


def remote_of(series: str) -> str:
    """The default remote of ``series``."""
    return f"{REMOTE_NAME}:{'/'.join(ROOT)}/{_known(series)}"


def pilots_remote(remote: str, series: str = SERIES[0]) -> str:
    """``remote`` in normal form, the only form rclone is given, if it is on ``gdrive:`` under
    ``srstudio/pilots/<series>``."""
    if any(c.isspace() or c == "\\" for c in remote):
        raise PilotError(f"{remote!r}: a pilots remote has no spaces or backslashes")
    name, colon, path = remote.partition(":")
    parts = [part for part in posixpath.normpath("/" + path).split("/") if part]
    if NEVER in (part.casefold() for part in parts):
        raise PilotError(f"{remote!r} is {NEVER}, which posts to @okayville.tv: a pilot never goes there")
    home = (*ROOT, _known(series))
    if not colon or name != REMOTE_NAME or tuple(parts[: len(home)]) != home:
        raise PilotError(f"{remote!r} is not under {REMOTE_NAME}:{'/'.join(home)}")
    return f"{name}:{'/'.join(parts)}"


def staging_folder(folder: Path, series: str = SERIES[0]) -> Path:
    """``folder``, links resolved, if it is ``generated/pilots/<series>`` outside the folders that reach Okayville."""
    resolved = Path(folder).resolve()
    parts = resolved.parts
    home = stage_of(series)
    watched = any(parts[i : i + len(w)] == w for w in _WATCHED for i in range(len(parts)))
    if watched or parts[-len(home.parts) :] != home.parts:
        raise PilotError(f"the staging folder must be {home} and outside the delivery folders, got {folder}")
    return resolved


def foreign(ready: list[outbox.Bundle], series: str) -> None:
    """Refuse a pilot that this repository keeps under another series."""
    for pilot in ready:
        for other in SERIES:
            if other != series and (REPO / "pilots" / other / pilot.name).exists():
                raise PilotError(f"{pilot.name} belongs to the {other} series, not {series}")


def released(deliveries: Path) -> set[str]:
    """Every name Okayville has used, in lower case: release slugs, video names and folders in ``deliveries``."""
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
        raise PilotError(f"{slug} is a released Okayville video")
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


def delivered(remote: str, rclone: str) -> set[str]:
    """The pilots already on ``remote``, from its manifest; none before the first delivery."""
    text = outbox.fetch(remote, MANIFEST, rclone=rclone)
    if text is None:
        return set()
    try:
        videos = json.loads(text)["videos"]
    except (ValueError, KeyError, TypeError) as e:
        raise PilotError(f"the {MANIFEST} on {remote} cannot be read: {e!r}") from e
    if not isinstance(videos, dict):
        raise PilotError(f"the {MANIFEST} on {remote} cannot be read: videos is no table")
    return set(videos)


def unenhanced(ready: list[outbox.Bundle], remote: str, rclone: str) -> None:
    """Refuse a new pilot whose builder landed no enhancement (ADR 0056); a pilot already on Drive owes none."""
    try:
        if not auto_enhance.enabled(REPO):
            print("auto-enhance off: nothing asked of these videos")
            return
        on_drive = delivered(remote, rclone)
        refused = auto_enhance.refused({p.name: p.name for p in ready if p.name not in on_drive}, REPO)
    except auto_enhance.EnhanceError as e:
        raise PilotError(str(e)) from e
    if refused:
        raise PilotError("; ".join(map(str, refused)))


def unfunny(ready: list[outbox.Bundle], series: str, remote: str, rclone: str) -> None:
    """Refuse a new pilot of a comedy series short of the floor (ADR 0064). A series in :data:`NOT_COMEDY` owes
    nothing, nor does a pilot already on Drive. Drive is read only for a pilot that falls short, so a scored set needs
    no rclone."""
    if series in NOT_COMEDY:
        return
    notes = {p.name: dict(zip(p.names, p.files, strict=True))[NOTES] for p in ready}
    short = {slug: why for slug, path in notes.items() if (why := comedy_floor.notes_shortfall(path.read_bytes()))}
    if short:
        on_drive = delivered(remote, rclone)
        try:
            comedy_floor.refuse({slug: why for slug, why in short.items() if slug not in on_drive})
        except comedy_floor.ComedyError as e:
            raise PilotError(str(e)) from e


def _excess(caption: Path) -> str:
    try:
        return social.hashtag_excess(caption.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return f"{CAPTION} is not UTF-8 text"


def overtagged(ready: list[outbox.Bundle], remote: str, rclone: str) -> None:
    """Refuse a new pilot of any series whose caption is over the hashtag limit (ADR 0065); a pilot already on Drive
    stays as it went out. Drive is read only for a pilot over the limit, so a clean set needs no rclone."""
    captions = {p.name: dict(zip(p.names, p.files, strict=True))[CAPTION] for p in ready}
    excess = {slug: why for slug, path in captions.items() if (why := _excess(path))}
    if excess:
        on_drive = delivered(remote, rclone)
        try:
            social.refuse_hashtags({slug: why for slug, why in excess.items() if slug not in on_drive})
        except social.HashtagError as e:
            raise PilotError(str(e)) from e


def left_behind(pilot: outbox.Bundle, root: Path) -> list[str]:
    """What is in the pilot's folder and not delivered, as ``slug/name``."""
    chosen = {f.name for f in pilot.files}
    return [f"{pilot.name}/{p.name}" for p in sorted((Path(root) / pilot.name).iterdir()) if p.name not in chosen]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="one folder per slug")
    parser.add_argument("--series", choices=SERIES, default=SERIES[0], help=f"default {SERIES[0]}")
    parser.add_argument("--stage", type=Path, help="default generated/pilots/<series>, the only name allowed")
    parser.add_argument(
        "--deliveries", type=Path, default=WORKSPACE / "generated/renders/ig", help="read for the slugs already used"
    )
    parser.add_argument("--remote", help="rclone destination under pilots/<series>, which is the default")
    parser.add_argument("--rclone", default="rclone")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="stage, then only preview the upload")
    mode.add_argument("--stage-only", action="store_true", help="stage, upload nothing")
    args = parser.parse_args(argv)

    try:
        remote = pilots_remote(args.remote or remote_of(args.series), args.series)
        stage = staging_folder(args.stage or WORKSPACE / stage_of(args.series), args.series)
        source = args.folder.resolve()
        if source.is_relative_to(stage) or stage.is_relative_to(source):
            raise PilotError(f"the input {source} and the staging folder {stage} overlap")
        ready = bundles(source, released(args.deliveries))
        foreign(ready, args.series)
        for pilot in ready:
            for name in left_behind(pilot, source):
                print(f"left behind: {name}")
        overtagged(ready, remote, args.rclone)
        unfunny(ready, args.series, remote, args.rclone)
        unenhanced(ready, remote, args.rclone)
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
