"""Build the same pointing gesture on complete Stick, Toon and Gloss characters.

Run ``PYTHONPATH=src python examples/limbs_cast.py OUTPUT`` then ``scene-render encode OUTPUT/cast.scene.xml``.
The source motions retarget the arm width and hand topology to each character; no provider calls.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, gloss, stick, toon_cast
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import HUMAN, MITTEN, ArmProfile, Camera, LimbError, Vec3
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.integration import LimbTrack
from srstudio.limbs.motion import Action, Motion, Target
from srstudio.limbs.serialization import save_motion
from srstudio.sample import SYSTEM_FONTS
from srstudio.toon import Pose


def build(out: Path, *, fps: int = 24, font: Path | None = None, license_file: Path | None = None) -> Path:
    if font is not None and license_file is None:
        raise LimbError("a custom font requires its own explicit --font-license")
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets = out / "assets"
    assets.mkdir(exist_ok=True, mode=0o700)
    font = font or next((p for p in SYSTEM_FONTS if p.is_file()), None)
    license_file = license_file or Path("/usr/share/doc/fonts-dejavu-core/copyright")
    if font is None or not font.is_file() or not license_file.is_file():
        raise LimbError("the cast showcase needs an existing --font and --font-license")
    shutil.copyfile(font, assets / "font.ttf")
    shutil.copyfile(license_file, assets / "FONT-LICENSE.txt")
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version="auto")
    scene.add_project(width=1920, height=1080, fps="24", duration=2, background="#f4f0e9", fontPolicy="pinned")
    scene.add_metadata(
        title="One gesture, three characters",
        generator="srstudio.limbs; example authored with Codex",
        description="One pointing action on a Stick person, a mitten-handed Toon dog and Gloss Nadia.",
        language="en",
    )
    scene.add_output(
        id="main",
        path="renders/cast.mp4",
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
    cv.text(cv.comp, "title", "ONE GESTURE, THREE CHARACTERS", 80, 30, 1760, 80, 42, color="#322c3c")
    action = Action("point", duration=2, target=Target(Vec3(0.62, 0.10, 0.16)))
    for i, style in enumerate(("stick", "toon", "gloss")):
        left = i * 640
        panel = cv.group(cv.comp, f"panel-{style}")
        cv.rect(panel, left + 25, 140, 590, 710, ("#e7dcc7", "#f8e5d5", "#e8dcf0")[i], radius=24)
        cv.text(panel, f"label-{style}", style.upper(), left + 50, 155, 540, 65, 32, color="#382b44")
        width = {"stick": 0.1, "toon": 0.4, "gloss": 0.37}[style]
        motion = Motion(ArmProfile(width=width), MITTEN if style == "toon" else HUMAN, (action,))
        save_motion(motion, out / f"{style}.motion.json")
        origin, size = {"stick": ((536, 891), 150), "toon": ((308, 712), 70), "gloss": ((92, -345), 100)}[style]
        skin = {"stick": stick.SKIN, "toon": toon_cast.DOG.coat, "gloss": gloss.SKIN["tan"]}[style]
        sleeve = {"stick": "#15151b", "toon": toon_cast.DOG.coat, "gloss": "#2fb3a6"}[style]
        track = LimbTrack(
            motion,
            style=style,
            camera=Camera(origin=origin, scale=size),
            appearance=Appearance(skin=skin, sleeve=sleeve, line_width=3),
            options=BakeOptions(fps=fps),
        )
        if style == "stick":
            stick.rig(
                cv,
                panel,
                (stick.RigKey(0, "stand"),),
                2,
                poses=stick.STANDING,
                at=(left + 60, -75),
                scale=0.48,
                limbs=(track,),
            )
        elif style == "toon":
            local = cv.group(panel, "toon-placement", x=left + 130, y=-140, scaleX=0.6, scaleY=0.6)
            toon_cast.dog(cv, local, (Pose(0, "wide", "flat", "desk"),), 2, limbs=(track,))
        else:
            gloss.nadia(cv, panel, at=(left + 310, 760), scale=0.68, end=2, limbs=(track,))
    cv.text(
        cv.comp,
        "caption",
        "One action. Different proportions, hand topology, drawing style and character placement.",
        90,
        915,
        1740,
        70,
        27,
        color="#62586c",
    )
    findings = scene.check(schema=True)
    if findings:
        raise LimbError("cast scene failed validation: " + "; ".join(str(f) for f in findings[:5]))
    path = out / "cast.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-license", type=Path)
    args = parser.parse_args()
    print(build(args.out, fps=args.fps, font=args.font, license_file=args.font_license))


if __name__ == "__main__":
    main()
