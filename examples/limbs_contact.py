"""Build a moving button press and a cup pickup/release using the shared spatial interaction compiler.

Run ``PYTHONPATH=src python examples/limbs_contact.py OUTPUT`` and ``scene-render encode OUTPUT/contact.scene.xml``.
Both clips use original vector props, deterministic motion and a pinned local font; no provider calls.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
from dataclasses import replace
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import HUMAN, ArmProfile, Frame, LimbError, Vec3
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import AttachedProp, Face, Participant, PropDrawing, PropMesh, bake_interaction
from srstudio.limbs.motion import Action, Attachment, Contact, Motion, TransformKey, TransformTrack
from srstudio.limbs.projection import Camera
from srstudio.limbs.serialization import save_motion
from srstudio.sample import SYSTEM_FONTS


def press_motion() -> tuple[Motion, TransformTrack]:
    base = Motion(ArmProfile(), HUMAN, (Action("press", duration=3),))
    held = base.sample(1.5)
    point = held.hand.digit("index").points[-1]
    rotation = held.hand.frame.rotation
    target = TransformTrack(
        tuple(
            TransformKey(time, Frame(point + Vec3(0.035 * depth, 0.035 * depth, 0), rotation))
            for time, depth in ((0, 0), (1.1, 0), (1.5, 1), (1.9, 1), (2.15, 0), (3, 0))
        )
    )
    return replace(base, contacts=(Contact("button", 1.1, 2.15, target, digit="index"),)), target


def cup_motion() -> Motion:
    base = Motion(ArmProfile(), HUMAN, (Action("grasp", duration=3, pole=Vec3(0, 1, 0)),))
    grip = base.sample(1.2).hand.frame
    lift = Frame(grip.origin + Vec3(0.12, -0.25, 0.08), grip.rotation)
    path = TransformTrack((TransformKey(1.2, grip), TransformKey(1.8, lift), TransformKey(2.1, lift)))
    base = replace(base, contacts=(Contact("grip-path", 1.2, 2.1, path),))
    # The cup starts upright in world space; thereafter its authored grip offset follows the wrist exactly.
    offset = Frame(Vec3(0, 0.37, 0.19), grip.rotation.inverse())
    initial = grip.compose(offset)
    return replace(base, attachments=(Attachment("cup", 1.2, 2.1, initial, offset),))


def cup_mesh() -> PropMesh:
    faces = []
    count, radius, height = 16, 0.19, 0.39
    for i in range(count):
        a, b = math.tau * i / count, math.tau * (i + 1) / count

        def point(angle, y):
            return Vec3(radius * math.cos(angle), y, radius * math.sin(angle))

        shade = round(175 + 45 * math.cos((a + b) / 2))
        faces.append(
            Face(
                f"side-{i}",
                (point(a, -height / 2), point(b, -height / 2), point(b, height / 2), point(a, height / 2)),
                f"#{shade:02x}{min(255, shade + 14):02x}ef",
                outline="#5c638a",
            )
        )
    faces.append(
        Face(
            "coffee",
            tuple(
                Vec3(
                    radius * 0.92 * math.cos(math.tau * i / count),
                    -height / 2 + 0.025,
                    radius * 0.92 * math.sin(math.tau * i / count),
                )
                for i in range(count)
            ),
            "#54372d",
        )
    )
    # A segmented handle has a real opening; no background-colored patch is needed for compositing.
    for i in range(12):
        a, b = -math.pi / 2 + math.pi * i / 12, -math.pi / 2 + math.pi * (i + 1) / 12

        def handle(angle, r):
            return Vec3(radius + math.cos(angle) * r, math.sin(angle) * r, 0)

        faces.append(
            Face(
                f"handle-{i}",
                (handle(a, 0.17), handle(b, 0.17), handle(b, 0.12), handle(a, 0.12)),
                "#ced7ff",
                outline="#737da3",
            )
        )
    return PropMesh("cup", tuple(faces))


def button_mesh() -> PropMesh:
    # The origin is exactly the touch surface. Its local Y follows the extended index finger.
    return PropMesh(
        "button",
        (
            Face(
                "base",
                (Vec3(-0.2, 0.12, -0.07), Vec3(0.2, 0.12, -0.07), Vec3(0.2, 0.3, -0.07), Vec3(-0.2, 0.3, -0.07)),
                "#8d9b9c",
            ),
            Face(
                "touch",
                (Vec3(-0.13, 0, -0.03), Vec3(0.13, 0, -0.03), Vec3(0.13, 0.12, 0.03), Vec3(-0.13, 0.12, 0.03)),
                "#69c5ac",
            ),
        ),
    )


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
        raise LimbError("the contact showcase needs an existing --font and --font-license")
    shutil.copyfile(font, assets / "font.ttf")
    shutil.copyfile(license_file, assets / "FONT-LICENSE.txt")
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version="auto")
    scene.add_project(width=1600, height=900, fps="24", duration=3, background="#f4f0e9", fontPolicy="pinned")
    scene.add_metadata(
        title="Touch, grip and release",
        generator="srstudio.limbs; example authored with Codex",
        description="Left: fingertip follows a moving button. Right: cup follows wrist until release.",
        language="en",
    )
    scene.add_output(
        id="main",
        path="renders/contact.mp4",
        codec="h264",
        width=1600,
        height=900,
        fps="24",
        preset="fast",
        crf="18",
        faststart=True,
    )
    cv = Canvas(scene, width=1600, height=900, font_asset="font")
    cv.assets.add_font(
        id="font",
        src="assets/font.ttf",
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / "font.ttf"),
        license="assets/FONT-LICENSE.txt",
    )
    cv.text(cv.comp, "title", "TOUCH, GRIP AND RELEASE", 70, 25, 1460, 70, 40, color="#322c3c")
    press, surface = press_motion()
    cup = cup_motion()
    save_motion(press, out / "press.motion.json")
    save_motion(cup, out / "cup.motion.json")
    report = {"schema": "srstudio.limbs.contact/1.0.0", "generatedBy": "srstudio.limbs"}
    for i, (name, motion, prop, label, caption) in enumerate(
        (
            (
                "press",
                press,
                PropDrawing(button_mesh(), surface),
                "FINGERTIP CONTACT",
                "The fingertip follows the button while it moves.",
            ),
            (
                "cup",
                cup,
                PropDrawing(cup_mesh(), AttachedProp(cup, "cup")),
                "PICKUP AND RELEASE",
                "The cup follows the wrist, then stays at its release pose.",
            ),
        )
    ):
        left = 800 * i
        panel = cv.group(cv.comp, f"panel-{name}")
        cv.rect(panel, left + 25, 125, 750, 620, "#e2e8e5" if i == 0 else "#e7e0ed", radius=25)
        cv.text(panel, f"label-{name}", label, left + 55, 145, 690, 60, 27, color="#40364b")
        camera = Camera(projection="perspective", distance=5, focal=5, scale=210, origin=(left + 160, 300))
        result = bake_interaction(
            cv,
            panel,
            (Participant(name + "-hand", motion, "gloss", Appearance()),),
            (prop,),
            id=f"interaction-{name}",
            camera=camera,
            options=BakeOptions(fps=fps),
        )
        report[name] = result.reports[0][1].to_dict()
        cv.ellipse(panel, left + 148, 288, 24, 24, "#746381")
        cv.text(cv.comp, f"caption-{name}", caption, left + 45, 775, 710, 70, 22, color="#5e5269")
    findings = scene.check(schema=True)
    if findings:
        raise LimbError("contact scene failed validation: " + "; ".join(str(f) for f in findings[:5]))
    path = out / "contact.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    (out / "contact-qa.json").write_text(json.dumps(report, indent=2) + "\n")
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
