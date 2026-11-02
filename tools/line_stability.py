#!/usr/bin/env python3
"""How well lines hold between frames, per folder of rendered frames (srstudio.line_stability, ADR 0160).

    python tools/line_stability.py PLAIN INKED [INKED...] --frames 276 280 [--search 16] [--window 33] [--reach 2]
        [--rows 1500 ...] [--columns 300 ...] [--ink 0.035 0.03 0.07]

PLAIN holds the same frames with no lines. Frames are named f0000.png by frame number, and a pair is each frame in the
range with the one after it. With --rows or --columns it also reads the width of every stroke crossing those lines on
every frame: a slow move should change a width by under a pixel and never turn it back and forth.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from srstudio import line_stability


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plain", type=Path)
    parser.add_argument("inked", type=Path, nargs="+")
    parser.add_argument("--frames", type=int, nargs=2, required=True, metavar=("FIRST", "LAST"))
    parser.add_argument("--search", type=int, default=16)
    parser.add_argument("--window", type=int, default=33)
    parser.add_argument("--reach", type=int, default=2)
    parser.add_argument("--rows", type=int, nargs="*", default=[])
    parser.add_argument("--columns", type=int, nargs="*", default=[])
    parser.add_argument("--ink", type=float, nargs=3, default=(0.035, 0.03, 0.07), metavar=("R", "G", "B"))
    args = parser.parse_args()
    first, last = args.frames
    readings = line_stability.measure(
        args.plain, args.inked, range(first, last + 1), search=args.search, window=args.window, reach=args.reach
    )
    pairs = last - first + 1
    for name, r in readings.items():
        print(
            f"{name}: cover {r.cover:.2%}, popped {r.rate:.2%}, unexplained {r.unexplained_rate:.2%}"
            f" ({r.unexplained / pairs:.0f} px/frame)"
        )
        if args.rows or args.columns:
            folder = next(f for f in args.inked if f.name == name)
            frames = range(first, last + 2)
            got = line_stability.width_chatter(
                args.plain, folder, frames, tuple(args.ink), rows=args.rows, columns=args.columns
            )
            print(f"  width: worst change {got.worst:.2f} px, {got.flips} reversals over {got.pairs} strokes followed")


if __name__ == "__main__":
    main()
