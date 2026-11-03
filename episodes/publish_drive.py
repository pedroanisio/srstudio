"""Copy every video that is ready to publish to Google Drive, with its ig.txt, cover.jpg and .vpkg.zip package.

    python3 publish_drive.py                 # stage generated/outbox and push it to gdrive:srstudio/ready-to-publish
    python3 publish_drive.py --dry-run       # stage, then only preview what rclone would upload
    python3 publish_drive.py --stage-only    # stage, push nothing
    python3 publish_drive.py --release text-me   # push, then take text-me out of Drive's .ignore

Ready means the publish gate (``instagram_posts.py check``) finds no drift for the video: its render, post,
caption and cover all match the last delivery, and it has its package. A video whose release is in an A/B test
(``releases.Tags(test=, arm=)``) is staged with an ``ab.json`` naming the test and its arm. A recreation's
package is the one received in ``videos-styles``; an original episode is packed from its project in
``generated/episodes`` into ``generated/vpkg`` (``srstudio.package``: verified, validated by the engine, repacked
only when its scene changed). A drifted video, or one without a package, is held back and listed, and the command
exits 1; a staging or upload failure exits 2. ``tools/systemd/srstudio-drive.{path,service}`` run it on every delivery.
The upload is ``rclone copy``, which never deletes on Drive; a video that is held back stays wherever an earlier
push put it. Drive's ``.ignore`` is the record of the reels held out of the queue: a push never writes it, reads it
before and after, and fails if a line went missing. ``--release <slug>`` (repeatable) is the only way to remove a line,
for a reel this push carries. Needs an rclone remote (``rclone config``; the default is ``gdrive:``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from srstudio import outbox, package, show_numbers

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_posts as posts  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
REMOTE = "gdrive:srstudio/ready-to-publish"

# video name -> the name its package is shipped under, where the two differ
PACKAGE_OF = {"honesty-interview-recreated": "honesty-interview", "Printer_Recreation": "printer-recreation"}


def packages_for(names, folders) -> dict[str, Path]:
    """The latest package of every published video that has one, from the first of ``folders`` that holds it."""
    found = {}
    for name in names:
        for folder in folders:
            path = outbox.latest_package(folder, PACKAGE_OF.get(name, name))
            if path is not None:
                found[name] = path
                break
    return found


def pack_originals(items, received, episodes: Path, out: Path) -> list[str]:
    """Pack into ``out`` every published video that has no received package and whose project is in ``episodes``;
    returns why each one that could not be packed failed."""
    slug_of = {name: slug for slug, name in posts.VIDEOS.items()}
    failures = []
    for name, item in sorted(items.items()):
        if packages_for([name], received):
            continue
        project = Path(episodes) / slug_of.get(name, name)
        if not (project / f"{project.name}.scene.xml").is_file():
            continue
        try:
            package.pack(project, out, item.post)
        except package.PackageError as e:
            failures.append(f"{name}: {e}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deliveries", type=Path, default=WORKSPACE / "generated/renders/ig")
    parser.add_argument("--renders", type=Path, default=WORKSPACE / "generated/renders")
    parser.add_argument("--fonts", type=Path, default=WORKSPACE / "generated/fonts")
    parser.add_argument(
        "--packages", type=Path, action="append", help="folder of received packages (repeatable; default videos-styles)"
    )
    parser.add_argument("--episodes", type=Path, default=WORKSPACE / "generated/episodes", help="original projects")
    parser.add_argument("--vpkg", type=Path, default=WORKSPACE / "generated/vpkg", help="their packages")
    parser.add_argument("--outbox", type=Path, default=WORKSPACE / "generated/outbox")
    parser.add_argument("--remote", default=REMOTE, help=f"rclone destination, name:path (default {REMOTE})")
    parser.add_argument("--rclone", default="rclone")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="stage, then only preview the upload")
    mode.add_argument("--stage-only", action="store_true", help="stage, upload nothing")
    parser.add_argument(
        "--release",
        action="append",
        default=[],
        metavar="SLUG",
        help="take this reel of the push out of Drive's .ignore, after the upload is checked (repeatable)",
    )
    args = parser.parse_args(argv)
    if args.release and args.stage_only:
        parser.error("--release needs a push, and --stage-only pushes nothing")

    items = posts.items(args.renders)
    received = args.packages or [WORKSPACE / "videos-styles"]
    for failure in pack_originals(items, received, args.episodes, args.vpkg):
        print(f"not packed: {failure}")
    try:
        found = packages_for(items, [*received, args.vpkg])
        bundles, drift = outbox.ready(
            items,
            args.deliveries,
            font=posts.font_file(args.fonts),
            packages=found,
            frozen=posts.FROZEN,
            ab=posts.AB,
            numbers=posts.numbers(args.renders),
        )
        for d in drift:
            print(f"held back: {d}")
        manifest = outbox.stage(bundles, args.outbox)
        held = len({d.name for d in drift} & set(items)) if not any(d.name == "*" for d in drift) else len(items)
        print(f"{len(bundles)} ready, {held} held back; staged in {manifest.parent}")
        if not args.stage_only:
            release = tuple(args.release)
            outbox.push(manifest.parent, args.remote, rclone=args.rclone, dry_run=args.dry_run, release=release)
            print(f"{'previewed' if args.dry_run else 'copied and checked'}: {args.remote}")
            if release:
                print(f"{'would release' if args.dry_run else 'released'}: {', '.join(release)}")
    except (outbox.OutboxError, show_numbers.NumberError) as e:
        print(f"publish_drive: {e}", file=sys.stderr)
        return 2
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
