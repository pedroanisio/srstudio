"""A reel's cover and caption for a look before it is released: into a proof folder, never the publish folder.

:func:`proof` draws what a delivery would draw and lists what the file gates find (parts unpinned or held, doubled
captions, the caption gate), so a reel's cover is seen while the reel can still change. Findings do not stop the
drawing: a part that waits for its version is the normal state of a new reel, and the list says so. It will not write
under ``<renders>/ig``: a write there starts the Drive push.

    python -m srstudio.cover_proof SLUG... --out DIR --renders DIR --episodes DIR --font FILE --engine PATH
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import caption_gate, releases
from .errors import SrstudioError
from .social import Drift

__all__ = ["CoverProofError", "Proof", "main", "proof", "refuse_outbox"]

OUTBOX = "ig"  # the folder under the renders that the Drive unit watches


class CoverProofError(SrstudioError, ValueError):
    """A proof cannot be drawn where it was asked for, or from what is there."""


@dataclass(frozen=True)
class Proof:
    """Where a proof's files went and what the gates found."""

    folder: Path
    drift: tuple[Drift, ...]


def refuse_outbox(out: Path, renders: Path) -> None:
    """Raise if ``out`` is the publish folder or inside it, however the path spells it."""
    outbox = (Path(renders) / OUTBOX).resolve()
    folder = Path(out).resolve()
    if folder == outbox or outbox in folder.parents:
        raise CoverProofError(f"{out} is the publish folder; a proof goes anywhere else")


def proof(release: releases.Release, out: Path, *, renders: Path, episodes: Path, font: Path, engine: Path) -> Proof:
    """Draw ``release``'s ``cover.jpg`` and ``ig.txt`` into ``out/<slug>`` and list what the file gates find."""
    refuse_outbox(out, renders)
    video = Path(renders) / f"{release.video_name}.mp4"
    if not video.is_file():
        raise CoverProofError(f"{video} is not rendered yet")
    chosen = {release.slug: release}
    named = {release.video_name}
    drift = [
        *releases.unpinned(chosen, episodes, named),
        *releases.doubled_captions(chosen, episodes, named),
        *caption_gate.check_releases(chosen, renders, episodes, grandfathered=frozenset(), only=list(named)),
    ]
    folder = Path(out) / release.slug
    scene = Path(episodes) / release.slug / release.scene_file
    release.post.deliver(folder, video, font=font, engine=engine, scene=scene if scene.is_file() else None)
    return Proof(folder, tuple(drift))


def main(argv: Sequence[str] | None = None) -> int:
    """Draw each slug's proof; exit 0 when all were drawn, whatever the gates listed, which are printed."""
    parser = argparse.ArgumentParser(prog="cover_proof", description=__doc__)
    parser.add_argument("slugs", nargs="+")
    parser.add_argument("--posts", type=Path, default=Path("episodes/posts"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--renders", type=Path, required=True)
    parser.add_argument("--episodes", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True, help="the headline's TrueType file")
    parser.add_argument("--engine", type=Path, required=True)
    args = parser.parse_args(argv)
    known = releases.load(args.posts)
    for slug in args.slugs:
        if slug not in known:
            print(f"cover_proof: no release {slug!r}", file=sys.stderr)
            return 2
        result = proof(known[slug], args.out, renders=args.renders, episodes=args.episodes, font=args.font,
                       engine=args.engine)  # fmt: skip
        print(f"{slug}: drawn in {result.folder}")
        for found in result.drift:
            print(f"  {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
