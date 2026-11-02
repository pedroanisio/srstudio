#!/usr/bin/env python3
"""The proof's two sides together: the side-by-side clip, the sheet of paired frames at full size, and the measures.

    python compare.py MASTER STUDY PROJECT OUT      # MASTER the delivered reel, STUDY the study's encode, PROJECT its
                                                    # project (plates/ and cast/%04d.png), OUT a private folder

The clip's picture is the approved shot left, the 3D plate right, and its sound is the master's own, cut to the same
frames. Two measures back the eye. The base check runs the rig alone over every frame against the front plate. The sync
measure compares the rigs' pixels left and right, and compares them again one frame apart, which must be worse or it
proves nothing.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from _base_check import clearance, exposed_columns
from _span import FPS, FRAMES, PAIRS
from PIL import Image

os.umask(0o077)  # generated outputs are private: folders 700, files 600

WIDTH, HEIGHT = 1080, 1920
SEAT_TOP = 1290  # rows above this are rig on both sides; below it the two seats differ on purpose
FAST_FRAMES = 60  # the opening, where the rigs move most, so an offset shows


def frames(path: Path, count: int) -> np.ndarray:
    """The first `count` decoded frames as rgb24."""
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", str(count), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
    )
    picture = np.frombuffer(done.stdout, np.uint8)
    if picture.size != count * WIDTH * HEIGHT * 3:
        raise SystemExit(f"{path}: decoded {picture.size} bytes for {count} frames")
    return picture.reshape(count, HEIGHT, WIDTH, 3)


def alpha(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))[..., 3]


def rig_difference(left: np.ndarray, right: np.ndarray, cast: Path, shift: int = 0) -> float:
    """Mean difference per channel over the opaque rig pixels above the seat, `shift` frames apart."""
    total, seen = 0.0, 0
    for index in range(FAST_FRAMES):
        mask = alpha(cast / f"{index:04d}.png") == 255
        mask[SEAT_TOP:] = False
        grown = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
        inner = np.zeros_like(mask)
        inner[1:-1, 1:-1] = grown
        total += np.abs(left[index][inner].astype(float) - right[index + shift][inner].astype(float)).sum()
        seen += int(inner.sum()) * 3
    return round(total / seen, 3)


def main(argv: list[str]) -> None:
    master, study, project, out = (Path(a).resolve() for a in argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    seconds = FRAMES / FPS
    clip = out / "paintover-proof-side-by-side.mp4"
    graph = (
        f"[0:v]trim=end_frame={FRAMES},setpts=PTS-STARTPTS[a];[1:v]trim=end_frame={FRAMES},setpts=PTS-STARTPTS[b];"
        "[a][b]hstack=inputs=2[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(master),
            "-i",
            str(study),
            "-filter_complex",
            graph,
            "-map",
            "[v]",
            "-map",
            "0:a",
            "-t",
            f"{seconds:.5f}",
            "-c:v",
            "libx264",
            "-crf",
            "14",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(clip),
        ],
        check=True,
    )
    left, right = frames(master, FAST_FRAMES + 1), frames(study, FAST_FRAMES + 1)
    near = alpha(project / "plates" / "front.png")
    masks = [alpha(project / "cast" / f"{index:04d}.png") for index in range(FRAMES)]
    measures = dict(
        frames=FRAMES,
        seconds=round(seconds, 4),
        pairs=list(PAIRS),
        base_columns_exposed=sum(exposed_columns(mask, near) for mask in masks),
        least_rows_of_cover=min(clearance(mask, near) for mask in masks),
        rig_difference=rig_difference(left, right, project / "cast"),
        rig_difference_one_frame_apart=rig_difference(left, right, project / "cast", 1),
    )
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")
    sheet = Image.new("RGB", (WIDTH * 6, HEIGHT * 2))
    for number, frame in enumerate(PAIRS):
        pair = Image.new("RGB", (WIDTH * 2, HEIGHT))
        for side, source in enumerate((master, study)):
            picked = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-vf",
                    f"select=eq(n\\,{frame})",
                    "-frames:v",
                    "1",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ],
                capture_output=True,
                check=True,
            )
            pair.paste(Image.frombytes("RGB", (WIDTH, HEIGHT), picked.stdout), (side * WIDTH, 0))
        pair.save(out / f"pair-{number + 1}-frame-{frame:03d}.png")
        sheet.paste(pair, (number % 3 * WIDTH * 2, number // 3 * HEIGHT))
    sheet.save(out / "paintover-proof-sheet.png")
    print(json.dumps(measures))


if __name__ == "__main__":
    main(sys.argv)
