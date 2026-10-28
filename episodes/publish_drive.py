"""Copy every video that is ready to publish to Google Drive, with its ig.txt, cover.jpg and package.

    python3 publish_drive.py                 # stage generated/outbox and push it to gdrive:srstudio/ready-to-publish
    python3 publish_drive.py --dry-run       # stage, then only preview what rclone would upload
    python3 publish_drive.py --stage-only    # stage, push nothing

Ready means the publish gate (``instagram_posts.py check``) finds no drift for the video: its render, post,
caption and cover all match the last delivery. A drifted video is held back and listed, and the command exits 1.
The upload is ``rclone copy``, which never deletes on Drive; a video that is held back stays wherever an earlier
push put it. Needs an rclone remote (``rclone config``; the default is ``gdrive:``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from srstudio import outbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_posts as posts  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
REMOTE = "gdrive:srstudio/ready-to-publish"

# video name -> the name its package is shipped under, where the two differ
PACKAGE_OF = {"honesty-interview-recreated": "honesty-interview", "Printer_Recreation": "printer-recreation"}


def packages_for(names, folder: Path) -> dict[str, Path]:
    """The latest package of every published video that has one in ``folder``."""
    found = {name: outbox.latest_package(folder, PACKAGE_OF.get(name, name)) for name in names}
    return {name: path for name, path in found.items() if path is not None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deliveries", type=Path, default=WORKSPACE / "generated/renders/ig")
    parser.add_argument("--renders", type=Path, default=WORKSPACE / "generated/renders")
    parser.add_argument("--fonts", type=Path, default=WORKSPACE / "generated/fonts")
    parser.add_argument("--packages", type=Path, default=WORKSPACE / "videos-styles")
    parser.add_argument("--outbox", type=Path, default=WORKSPACE / "generated/outbox")
    parser.add_argument("--remote", default=REMOTE, help=f"rclone destination, name:path (default {REMOTE})")
    parser.add_argument("--rclone", default="rclone")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="stage, then only preview the upload")
    mode.add_argument("--stage-only", action="store_true", help="stage, upload nothing")
    args = parser.parse_args(argv)

    items = posts.items(args.renders)
    bundles, drift = outbox.ready(
        items, args.deliveries, font=posts.font_file(args.fonts), packages=packages_for(items, args.packages)
    )
    for d in drift:
        print(f"held back: {d}")
    manifest = outbox.stage(bundles, args.outbox)
    held = len({d.name for d in drift} & set(items)) if not any(d.name == "*" for d in drift) else len(items)
    print(f"{len(bundles)} ready, {held} held back; staged in {manifest.parent}")
    if not args.stage_only:
        outbox.push(manifest.parent, args.remote, rclone=args.rclone, dry_run=args.dry_run)
        print(f"{'previewed' if args.dry_run else 'copied and checked'}: {args.remote}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
