#!/usr/bin/env python3
"""The Instagram post of every episode and the publish gate of the rendered videos.

Each episode declares its release in ``posts/<slug with underscores>.py`` (:mod:`srstudio.releases`): its post, the
rendered video's name when it is not the slug, and whether its cover is drawn from the scene's cover variant; a new
episode adds its own file and edits nothing here. Each episode script calls ``ep.instagram(POSTS[slug])`` so a
build leaves ``ig.txt`` next to its scene. Each post also designs its cover: a
:class:`~srstudio.thumbnail.Thumbnail` drawn over a frame of the video. ``deliver`` writes one ``<out>/<video name>/``
folder per rendered video, holding ``ig.txt`` and ``cover.jpg``, for every video that drifted, and records
``<out>/delivery.json``; ``check`` exits 1 and lists every drift (a video re-rendered after its cover, a changed post,
an edited or missing file, a post without a render) and writes nothing. ``check`` runs no engine, ffmpeg or ffprobe.
``migrate`` moves a 1.0.0 ``delivery.json`` to 1.1.0 once (ADR 0037): it rewrites the post fingerprint of each
entry delivered from the post it has now, keeps every other entry, and draws or delivers nothing; ``--dry-run``
prints the same plan and writes nothing:

    python3 instagram_posts.py deliver OUT RENDERS --fonts DIR [--engine BIN] [--only NAME ...]
    python3 instagram_posts.py check OUT RENDERS --fonts DIR
    python3 instagram_posts.py migrate OUT RENDERS --fonts DIR [--dry-run]

A release declared ``frozen`` (ADR 0040) is a published video whose post now draws another cover than the one
delivered: the gate takes its delivery as current at the drawing the operator accepted, ``deliver`` leaves it as
published, and ``check`` lists it.

``--only`` delivers the named videos alone (one ready to publish while another post waits for its render); the
rest of the delivery is left as it was, and ``check`` still reports what drifted there.

The headline font (:data:`THUMBNAIL_FONT`) is installed into ``--fonts`` and pinned there; once it is in place
nothing is downloaded. ``--engine`` defaults to ``$SRSTUDIO_ENGINE``, then ``scene-render`` on the ``PATH``.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from srstudio import auto_enhance, caption_gate, comedy_floor, fonts, outbox, overlay_gate, releases
from srstudio.social import (
    MANIFEST,
    MANIFEST_VERSION,
    DeliveryError,
    Drift,
    InstagramPost,
    Item,
    Migration,
    check_delivery,
    hashtag_excess,
    migrate_manifest,
    publish,
    read_manifest,
    refuse_hashtags,
)

THUMBNAIL_FONT = fonts.GoogleFont("Anton", 400)  # a condensed display face: two big lines fit a portrait cover

REPO = Path(__file__).resolve().parent.parent  # its history holds the enhancements, its settings the mode (ADR 0056)
RELEASES = releases.load(Path(__file__).resolve().parent / "posts")  # one file per episode: posts/<slug>.py
GRANDFATHERED = releases.grandfathered(Path(__file__).resolve().parent / "posts")  # published before the caption gate
POSTS: dict[str, InstagramPost] = {slug: r.post for slug, r in RELEASES.items()}
VIDEOS = {slug: r.video_name for slug, r in RELEASES.items()}  # project slug -> its rendered video's file name
COVER_SCENES = {slug: r.scene_file for slug, r in RELEASES.items() if r.cover}  # scenes with a cover variant
FROZEN = {r.video_name: r.frozen for r in RELEASES.values() if r.frozen}  # video name -> accepted drawing
AB = {
    r.video_name: outbox.Arm(r.tags.test, r.tags.arm, r.tags.recipient, r.tags.to)
    for r in RELEASES.values()
    if r.tags and r.tags.test
}  # A/B arms
PINS = {slug: r.parts or {} for slug, r in RELEASES.items()}  # project slug -> the character versions it draws


def _beside(renders: Path) -> Path:
    return Path(renders).resolve().parent / "episodes"


def items(renders: Path, episodes: Path | None = None) -> dict[str, Item]:
    """Every post with its rendered video (and the scene its cover is drawn from, for a release with ``cover``),
    keyed by the video's name; ``episodes`` defaults to the ``episodes`` folder beside ``renders``. A release whose
    cover disagrees with its built scene raises :class:`~srstudio.releases.ReleaseError`."""
    return releases.items(RELEASES, Path(renders), Path(episodes) if episodes is not None else _beside(renders))


def font_file(folder: Path) -> Path:
    """The headline font, installed into ``folder`` (and pinned by its lock) the first time."""
    return fonts.install(THUMBNAIL_FONT, folder).path


def caption_drift(renders: Path, *, episodes: Path | None = None, only: list[str] | None = None) -> list[Drift]:
    """What the caption gate (ADR 0048) finds on every release not grandfathered, or on the ``only`` videos."""
    episodes = Path(episodes) if episodes is not None else Path(renders).resolve().parent / "episodes"
    return caption_gate.check_releases(RELEASES, Path(renders), episodes, grandfathered=GRANDFATHERED, only=only)


def _delivering(out: Path, renders: Path, font: Path, only: list[str] | None) -> set[str]:
    """The videos a delivery would write: those named, else those that drifted, or all if the manifest is unreadable."""
    if only:
        return set(only)
    stale = {d.name for d in check_delivery(items(renders), out, font=font, frozen=FROZEN)}
    return {r.video_name for r in RELEASES.values()} if "*" in stale else stale


def write_all(
    out: Path, renders: Path, *, fonts_dir: Path, engine: str | Path, only: list[str] | None = None
) -> list[Path]:
    """Deliver every post whose video drifted (or only the ``only`` ones) and record the delivery; returns the
    folders written. A video the caption gate refuses, a release that does not pin what it draws, or captions that
    print over each other, or a first delivery with no enhancement behind it (ADR 0056), under the comedy floor
    (ADR 0064) or over the hashtag limit (ADR 0065), is a :class:`DeliveryError` before anything is written. A video in
    the manifest is past all three: what was published stays as it went out."""
    refused = caption_drift(renders, only=only)
    if refused:
        raise DeliveryError("the caption gate refuses: " + "; ".join(str(d) for d in refused))
    chosen = {slug: r for slug, r in RELEASES.items() if not only or r.video_name in only}
    delivering = _delivering(out, renders, font_file(fonts_dir), only)
    refused = [
        *releases.unpinned(chosen, _beside(renders), delivering),
        *releases.doubled_captions(chosen, _beside(renders), delivering),
        *releases.caption_on_cover(chosen, _beside(renders), delivering),
    ]
    if refused:
        raise DeliveryError("; ".join(map(str, refused)))
    done = read_manifest(out)
    first = {r.slug: r.video_name for r in chosen.values() if r.video_name in delivering and r.video_name not in done}
    refuse_hashtags({slug: hashtag_excess(chosen[slug].post.text()) for slug in first})
    comedy_floor.refuse({slug: comedy_floor.shortfall(chosen[slug].comedy) for slug in first})
    refused = [
        *overlay_gate.repeated_lines(chosen, _beside(renders), first.values()),
        *auto_enhance.refused(first, REPO),
    ]
    if refused:
        raise DeliveryError("; ".join(map(str, refused)))
    return publish(items(renders), out, font=font_file(fonts_dir), engine=engine, only=only, frozen=FROZEN)


def check_all(out: Path, renders: Path, *, fonts_dir: Path) -> list[Drift]:
    """Every drift between ``out`` and delivering every post from ``renders`` now, with every missing pin."""
    drift = check_delivery(items(renders), out, font=font_file(fonts_dir), frozen=FROZEN)
    return [*releases.unpinned(RELEASES, _beside(renders)), *drift, *caption_drift(renders)]


def migrate_all(out: Path, renders: Path, *, fonts_dir: Path, dry_run: bool = False) -> Migration:
    """Migrate ``out``'s 1.0.0 manifest against every post from ``renders`` (or only plan it, with ``dry_run``)."""
    return migrate_manifest(items(renders), out, font=font_file(fonts_dir), dry_run=dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("deliver", "check", "migrate"))
    parser.add_argument("out", type=Path, help="the delivery folder: one folder per video and delivery.json")
    parser.add_argument("renders", type=Path, help="the folder of rendered <video name>.mp4 files")
    parser.add_argument("--fonts", type=Path, required=True, help="where the headline font is installed")
    parser.add_argument("--engine", default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    parser.add_argument("--only", action="append", metavar="NAME", help="deliver this video alone (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="migrate: print the plan and write nothing")
    args = parser.parse_args(argv)
    if args.command == "migrate":
        try:
            result = migrate_all(args.out, args.renders, fonts_dir=args.fonts, dry_run=args.dry_run)
        except DeliveryError as exc:
            raise SystemExit(f"migrate: {exc}") from None
        for name in result.migrated:
            print(f"migrate {name}")
        for name, why in result.kept:
            print(f"keep {name}: {why}")
        counts = f"{len(result.migrated)} migrated, {len(result.kept)} kept"
        done = f"{args.out / MANIFEST} is now version {MANIFEST_VERSION}"
        print(f"{counts} (dry run: nothing written)" if args.dry_run else f"{counts}; {done}")
        return 0
    if args.command == "check":
        drift = check_all(args.out, args.renders, fonts_dir=args.fonts)
        for d in drift:
            print(d)
        if FROZEN:
            print(f"frozen at an accepted drawing (ADR 0040): {', '.join(sorted(FROZEN))}")
        drifted = len({d.name for d in drift})  # a video can drift in more than one way
        print(f"{len(POSTS)} videos, {drifted} drifted" if drift else f"{len(POSTS)} videos, delivery current")
        return 1 if drift else 0
    if not args.engine:
        parser.error("no engine: pass --engine or set SRSTUDIO_ENGINE")
    try:
        written = write_all(args.out, args.renders, fonts_dir=args.fonts, engine=args.engine, only=args.only)
    except DeliveryError as exc:
        raise SystemExit(f"deliver: {exc}") from None
    for folder in written:
        print(folder / "ig.txt", folder / "cover.jpg")
    if written and not auto_enhance.enabled(REPO):
        print("auto-enhance off: nothing asked of these videos")
    if args.only:
        left = [d for d in check_all(args.out, args.renders, fonts_dir=args.fonts) if d.name not in args.only]
        print(f"delivered {', '.join(args.only)}; {len(left)} drift(s) left elsewhere, see check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
