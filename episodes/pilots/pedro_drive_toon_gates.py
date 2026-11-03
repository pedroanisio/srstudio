"""The measurements DRAWING.md asks of the layered Pedro piece, on this build, printed as JSON.

    python pedro_drive_toon_gates.py WORK_DIR

It builds the piece twice (finished and bare), renders single frames with the engine, and reports what it measured: it
passes or fails nothing by itself. A gate it cannot measure is not listed as passed.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pedro_drive as base
import pedro_drive_toon as toon
from PIL import Image

from srstudio import gpu

PALETTE_TOLERANCE = 2  # levels per 8-bit channel (DRAWING.md)
CREAM = tuple(int(base.CREAM[i : i + 2], 16) for i in (1, 3, 5))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(engine: str, scene: Path, t: float, out: Path) -> Path:
    with gpu.held():
        done = subprocess.run(
            [engine, "render", scene.name, "-t", str(t), "-o", out.name],
            cwd=scene.parent,
            capture_output=True,
            text=True,
        )
    if done.returncode:
        raise SystemExit(f"render failed: {done.stdout[-400:]} {done.stderr[-400:]}")
    return scene.parent / out.name


def build(root: Path, **options) -> tuple[Path, float]:
    start = time.time()
    scene = toon.TonePiece(root, **options).build()
    return scene, round(time.time() - start, 1)


def tree_digest(root: Path) -> str:
    """One digest of every file the project holds besides the scene, by path and content."""
    digest = hashlib.sha256()
    for path in sorted((root / "assets").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + sha(path).encode())
    return digest.hexdigest()


def palette_match(frame: Path, ground: tuple[int, int, int]) -> dict:
    """How much of Pedro's picture sits within the tolerance of his palette. ``ground`` is the colour behind him, left
    out; pixels in the one-pixel margin round a change of colour are counted apart, as an edge, from the interior."""
    palette = np.array(
        [[int(c[i : i + 2], 16) for i in (1, 3, 5)] for _, c in toon.PEDRO_BANDS]
        + [[int(toon.INK[i : i + 2], 16) for i in (1, 3, 5)]],
        dtype=int,
    )
    px = np.asarray(Image.open(frame).convert("RGB"), dtype=int)
    figure = np.any(px != np.array(ground), axis=2)
    near = (np.abs(px[:, :, None, :] - palette[None, None]).max(axis=3) <= PALETTE_TOLERANCE).any(axis=2)
    edge = np.zeros_like(figure)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            edge |= np.any(np.roll(np.roll(px, dy, 0), dx, 1) != px, axis=2)
    interior = figure & ~edge
    return {
        "figure_pixels": int(figure.sum()),
        "interior_pixels": int(interior.sum()),
        "interior_within_tolerance": int((interior & near).sum()),
        "interior_fraction": round(float((interior & near).sum()) / max(1, int(interior.sum())), 4),
        "all_figure_fraction": round(float((figure & near).sum()) / max(1, int(figure.sum())), 4),
    }


def pedro_alone(work: Path, engine: str) -> Path:
    """Pedro's toned plate on a clear ground, as TonePiece draws it, for the palette check."""
    piece = toon.TonePiece(work / "alone", finish=False)
    asset, _ = piece.plate("car-calm")
    cv = piece.cv
    group = cv.group(cv.comp, "alone")
    group.add_layer(id="alone-layer", asset=asset, x=0, y=0)
    cv.apply(group, piece.tone)
    scene = work / "alone" / "alone.scene.xml"
    scene.write_bytes(cv.scene.to_bytes())
    return render(engine, scene, 0, Path("alone.png"))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    work = Path(argv[1]).resolve()
    engine = os.environ["SRSTUDIO_ENGINE"]
    report: dict = {}
    first, cold = build(work / "a")
    second, warm = build(work / "b")
    bare, _ = build(work / "bare", finish=False)
    report["rebuild"] = {
        "scene_identical": sha(first) == sha(second),
        "assets_identical": tree_digest(work / "a") == tree_digest(work / "b"),
        "first_build_s": cold,
        "second_build_s": warm,
        "vehicle_plates": len(list((work / "a" / "assets" / "vehicle").glob("*.png"))),
        "pedro_plates": len(list((work / "a" / "assets" / "pedro").glob("*.png"))),
    }
    frames = [(t, render(engine, first, t, Path(f"seq-{t}.png"))) for t in (17.0, 5.0, 24.0)]
    again = render(engine, first, 17.0, Path("again-17.0.png"))
    report["temporal"] = {
        "same_frame_twice_identical": sha(frames[0][1]) == sha(again),
        "out_of_order_identical": all(
            sha(path) == sha(render(engine, second, t, Path(f"ooo-{t}.png"))) for t, path in reversed(frames)
        ),
    }
    finished, plain = (
        render(engine, first, 1.5, Path("info-finished.png")),
        render(engine, bare, 1.5, Path("info-bare.png")),
    )
    box = (base.SAFE_X, 330 - 90, base.SAFE_X + base.SAFE_W, 330 + 90)

    def cream(path: Path) -> int:
        region = Image.open(path).convert("RGB").crop(box)
        return int((np.asarray(region) == np.array(CREAM)).all(axis=2).sum())

    report["information"] = {"cream_pixels_finished": cream(finished), "cream_pixels_bare": cream(plain)}
    report["palette"] = palette_match(pedro_alone(work, engine), (7, 9, 20))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
