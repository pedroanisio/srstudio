"""Build a twelve-second comparison of one spatial performance in Stick, Toon and Gloss.

Run ``python examples/limbs_gallery.py OUTPUT`` then ``scene-render encode OUTPUT/limbs-gallery.scene.xml``.
The original vector geometry, strict motion.json and numeric QA report travel together. No provider calls.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.math3d import Vec3
from srstudio.limbs.model import HANDS, ArmProfile, LimbError
from srstudio.limbs.motion import Action, Motion, Target
from srstudio.limbs.projection import Camera
from srstudio.limbs.serialization import save_motion
from srstudio.sample import SYSTEM_FONTS


def build(
    out: Path,
    *,
    fps: int = 24,
    font: Path | None = None,
    license_file: Path | None = None,
    deformation: str = "contour",
    hand: str = "human",
) -> Path:
    if deformation not in ("contour", "skin"):
        raise LimbError("gallery deformation must be contour or skin")
    if hand not in HANDS:
        raise LimbError(f"gallery hand must be one of {tuple(HANDS)}")
    if font is not None and license_file is None:
        raise LimbError("a custom font requires its own explicit --font-license")
    os.umask(0o077)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets = out / "assets"
    assets.mkdir(mode=0o700, exist_ok=True)
    font = font or next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        raise LimbError("the gallery needs --font and --font-license when DejaVu Sans is not installed")
    license_file = license_file or Path("/usr/share/doc/fonts-dejavu-core/copyright")
    if not license_file.is_file():
        raise LimbError("the gallery needs an existing --font-license file")
    shutil.copyfile(font, assets / "font.ttf")
    shutil.copyfile(license_file, assets / "FONT-LICENSE.txt")
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version="auto")
    scene.add_project(width=1920, height=1080, fps="24", duration=12, background="#f5f0e9", fontPolicy="pinned")
    scene.add_metadata(
        title="Shared limb performance",
        description=(
            "Original procedural arm and hand geometry in three styles. "
            "Motion source and numeric quality evidence are included."
        ),
        generator="srstudio.limbs; example authored with Codex",
        language="en",
    )
    scene.add_output(
        id="main",
        path="renders/limbs-gallery.mp4",
        codec="h264",
        width=1920,
        height=1080,
        fps="24",
        preset="fast",
        crf="18",
        faststart=True,
    )
    cv = Canvas(scene, width=1920, height=1080, font_asset="font")
    cv.assets.add_font(
        id="font",
        src="assets/font.ttf",
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / "font.ttf"),
        license="assets/FONT-LICENSE.txt",
    )
    cv.text(cv.comp, "title", "ONE PERFORMANCE   THREE DRAWING STYLES", 90, 30, 1740, 80, 42, color="#282333")
    names = ("point", "present", "shrug", "facepalm", "grasp", "press")
    actions = tuple(Action(name, i * 2, 2) for i, name in enumerate(names))
    actions = (Action("point", 0, 2, target=Target(Vec3(0.5, 0.22, 0.55))), *actions[1:])
    if deformation == "skin":
        # Native skin is planar; articulated fingers retain their spatial controls and baked representation.
        targets = ((0.65, 0.3), (0.55, 0.3), (0.48, -0.1), (0.08, -0.28), (0.5, 0.32), (0.6, 0.4))
        actions = tuple(
            Action(name, i * 2, 2, target=Target(Vec3(x, y, 0)))
            for i, (name, (x, y)) in enumerate(zip(names, targets, strict=True))
        )
    motion = Motion(ArmProfile(), HANDS[hand], actions)
    save_motion(motion, out / "motion.json")
    report = {
        "schema": "srstudio.limbs.gallery/1.0.0",
        "generatedBy": "srstudio.limbs",
        "styles": {},
        "deformation": deformation,
        "backends": {},
        "hand": hand,
    }
    for i, (style, background) in enumerate((("stick", "#e7dcc7"), ("toon", "#f8e5d5"), ("gloss", "#e8dcf0"))):
        left = i * 640
        panel = cv.group(cv.comp, f"panel-{style}")
        cv.rect(panel, left + 25, 140, 590, 710, background, radius=24)
        cv.text(panel, f"label-{style}", style.upper(), left + 50, 155, 540, 65, 32, color="#382b44")
        camera = Camera(
            projection="orthographic" if deformation == "skin" else "perspective",
            distance=5,
            focal=5,
            scale=220,
            origin=(left + 170, 370),
        )
        compiled = compile_motion(
            cv,
            panel,
            motion,
            id=f"arm-{style}",
            backend="auto" if deformation == "skin" else "baked",
            deformation=deformation,
            style=style,
            camera=camera,
            appearance=Appearance(skin="#cbd5e1" if hand == "gripper" else None),
            options=BakeOptions(fps=fps),
        )
        report["styles"][style] = compiled.report.to_dict()
        report["backends"][style] = compiled.backend
        cv.ellipse(panel, left + 158, 358, 24, 24, "#7a647c")
    for i, name in enumerate(names):
        label = cv.text(cv.comp, f"action-{i}", name.upper(), 100, 885, 1720, 70, 38, color="#32283d")
        cv.gate(label, [(i * 2, (i + 1) * 2)])
    cv.text(
        cv.comp,
        "caption",
        (
            "Native skin connects the sleeves. Articulated finger contours retain the shared spatial hand controls."
            if deformation == "skin"
            else (
                "Spatial pose, finger controls and perspective are shared. Ink, fills and shading belong to each style."
            )
        ),
        100,
        970,
        1720,
        50,
        23,
        color="#62586c",
    )
    findings = scene.check(schema=True)
    if findings:
        raise LimbError("gallery scene validation failed: " + "; ".join(str(f) for f in findings[:5]))
    path = out / "limbs-gallery.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    (out / "limbs-qa.json").write_text(json.dumps(report, indent=2) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--fps", type=int, default=24, help="limb sampling rate; output remains 24 fps")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-license", type=Path)
    parser.add_argument("--deformation", choices=("contour", "skin"), default="contour")
    parser.add_argument("--hand", choices=tuple(HANDS), default="human")
    args = parser.parse_args()
    print(
        build(
            args.out,
            fps=args.fps,
            font=args.font,
            license_file=args.font_license,
            deformation=args.deformation,
            hand=args.hand,
        )
    )


if __name__ == "__main__":
    main()
