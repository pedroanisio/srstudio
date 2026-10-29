"""Build crossed arms and a two-hand tray lift with shared spatial contact and depth compositing.

Run ``PYTHONPATH=src python examples/limbs_bimanual.py OUTPUT`` then ``scene-render encode OUTPUT/bimanual.scene.xml``.
Original vector geometry, pinned local font, reusable motions and numeric QA; no provider calls.
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
from srstudio.limbs import HUMAN, ArmProfile, Frame, HandControl, LimbError, Quaternion, Vec3
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import Face, Participant, PropDrawing, PropMesh, bake_interaction
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack
from srstudio.limbs.projection import Camera
from srstudio.limbs.props import Anchor, Coordination, Prop, crossed_arms, grip_prop
from srstudio.limbs.serialization import save_motion
from srstudio.sample import SYSTEM_FONTS


def profiles():
    return ArmProfile(shoulder=Vec3(0.58, 0, 0), width=0.2), ArmProfile(
        shoulder=Vec3(-0.58, 0, 0), width=0.2, side="left"
    )


def tray_pair() -> Coordination:
    right_profile, left_profile = profiles()
    support = Action("present", duration=4, control=HandControl(curl=0.1, spread=0.08, cup=0.12, opposition=0.3))
    right = Motion(right_profile, HUMAN, (support,))
    left = Motion(left_profile, HUMAN, (support,))
    rest = Frame(Vec3(0, 1, 0.1))
    lift = Frame(Vec3(0.08, 0.72, 0.18), Quaternion.axis_angle(Vec3(0, 0, 1), 0.06))
    track = TransformTrack((TransformKey(0, rest), TransformKey(1, rest), TransformKey(2, lift), TransformKey(4, lift)))
    # The palms face up, with each hand's longitudinal axis pointing toward the tray's centre.
    right_rotation = Quaternion.axes(Vec3(0, 0, 1), Vec3(-1, 0, 0), Vec3(0, -1, 0))
    left_rotation = Quaternion.axes(Vec3(0, 0, -1), Vec3(1, 0, 0), Vec3(0, -1, 0))
    tray = Prop(
        "tray",
        track,
        (
            Anchor("right", Frame(Vec3(0.85, 0.22, 0), right_rotation)),
            Anchor("left", Frame(Vec3(-0.85, 0.22, 0), left_rotation)),
        ),
    )
    return grip_prop(right, left, tray, right_anchor="right", left_anchor="left", start=1, end=3)


def ellipse(name, x, y, rx, ry, z, fill):
    return Face(
        name,
        tuple(Vec3(x + rx * math.cos(i * math.tau / 32), y + ry * math.sin(i * math.tau / 32), z) for i in range(32)),
        fill,
        outline=fill,
    )


def mannequin() -> PropMesh:
    mesh = PropMesh(
        "body",
        (
            Face(
                "shirt",
                (
                    Vec3(-0.62, -0.04, -0.22),
                    Vec3(0.62, -0.04, -0.22),
                    Vec3(0.52, 1.85, -0.22),
                    Vec3(-0.52, 1.85, -0.22),
                ),
                "#609eb8",
                outline="#3d657d",
            ),
            Face(
                "neck",
                (Vec3(-0.12, -0.3, -0.20), Vec3(0.12, -0.3, -0.20), Vec3(0.12, 0.1, -0.20), Vec3(-0.12, 0.1, -0.20)),
                "#e6b294",
            ),
            ellipse("head", 0, -0.70, 0.40, 0.48, -0.16, "#edbf99"),
            ellipse("eye-left", -0.14, -0.75, 0.065, 0.08, -0.14, "#fff9ee"),
            ellipse("eye-right", 0.14, -0.75, 0.065, 0.08, -0.14, "#fff9ee"),
            ellipse("pupil-left", -0.14, -0.74, 0.028, 0.045, -0.12, "#292330"),
            ellipse("pupil-right", 0.14, -0.74, 0.028, 0.045, -0.12, "#292330"),
            Face(
                "mouth",
                (
                    Vec3(-0.10, -0.48, -0.12),
                    Vec3(0.10, -0.48, -0.12),
                    Vec3(0.06, -0.46, -0.12),
                    Vec3(-0.06, -0.46, -0.12),
                ),
                "#7c4438",
            ),
        ),
    )

    # The illustrated head is a camera-facing card. Its facial details share that plane so a tilted
    # camera cannot place a lower feature behind the average depth of the whole head surface.
    centre = Vec3(0, -0.70, -0.16)
    head = Frame(centre, Quaternion.axis_angle(Vec3(1, 0, 0), 0.35))
    return replace(
        mesh,
        faces=tuple(
            face
            if face.name in ("shirt", "neck")
            else replace(face, vertices=tuple(head.point(v - centre) for v in face.vertices))
            for face in mesh.faces
        ),
    )


def tray_mesh() -> PropMesh:
    return PropMesh(
        "tray",
        (
            Face(
                "deck", (Vec3(-0.9, 0, -0.28), Vec3(0.9, 0, -0.28), Vec3(0.9, 0, 0.28), Vec3(-0.9, 0, 0.28)), "#e4bd7d"
            ),
            Face(
                "front",
                (Vec3(-0.9, 0, 0.28), Vec3(0.9, 0, 0.28), Vec3(0.9, 0.10, 0.28), Vec3(-0.9, 0.10, 0.28)),
                "#b8814b",
            ),
            Face(
                "back",
                (Vec3(-0.9, 0, -0.28), Vec3(0.9, 0, -0.28), Vec3(0.9, 0.10, -0.28), Vec3(-0.9, 0.10, -0.28)),
                "#d09e60",
            ),
            Face(
                "left",
                (Vec3(-0.9, 0, -0.28), Vec3(-0.9, 0, 0.28), Vec3(-0.9, 0.10, 0.28), Vec3(-0.9, 0.10, -0.28)),
                "#bd8f5a",
            ),
            Face(
                "right",
                (Vec3(0.9, 0, -0.28), Vec3(0.9, 0, 0.28), Vec3(0.9, 0.10, 0.28), Vec3(0.9, 0.10, -0.28)),
                "#bd8f5a",
            ),
        ),
    )


def build(out: Path, *, fps: int = 24, font: Path | None = None, license_file: Path | None = None) -> Path:
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets = out / "assets"
    assets.mkdir(exist_ok=True, mode=0o700)
    font = font or next((p for p in SYSTEM_FONTS if p.is_file()), None)
    license_file = license_file or Path("/usr/share/doc/fonts-dejavu-core/copyright")
    if font is None or not font.is_file() or not license_file.is_file():
        raise LimbError("the two-arm showcase needs an existing --font and --font-license")
    shutil.copyfile(font, assets / "font.ttf")
    shutil.copyfile(license_file, assets / "FONT-LICENSE.txt")
    facts = inspect_ttf(font.read_bytes())
    scene = Scene(version="auto")
    scene.add_project(width=1600, height=1000, fps="24", duration=4, background="#f4f0e9", fontPolicy="pinned")
    scene.add_metadata(
        title="Two arms, one performance",
        generator="srstudio.limbs; example authored with Codex",
        description="Crossed arms with explicit depth and two hands following a moving tray.",
        language="en",
    )
    scene.add_output(
        id="main",
        path="renders/bimanual.mp4",
        codec="h264",
        width=1600,
        height=1000,
        fps="24",
        preset="fast",
        crf="18",
        faststart=True,
    )
    cv = Canvas(scene, width=1600, height=1000, font_asset="font")
    cv.assets.add_font(
        id="font",
        src="assets/font.ttf",
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / "font.ttf"),
        license="assets/FONT-LICENSE.txt",
    )
    cv.text(cv.comp, "title", "TWO ARMS, ONE PERFORMANCE", 70, 25, 1460, 70, 40, color="#322c3c")
    crossed = crossed_arms(*profiles(), duration=4)
    tray = tray_pair()
    report = {"schema": "srstudio.limbs.bimanual/1.0.0", "generatedBy": "srstudio.limbs"}
    for i, (name, pair, label, caption) in enumerate(
        (
            ("crossed", crossed, "CROSSED ARMS", "Explicit depth keeps the crossing readable."),
            ("tray", tray, "SHARED MOVING PROP", "Both hands follow their own anchor on one tray."),
        )
    ):
        left = 800 * i
        panel = cv.group(cv.comp, f"panel-{name}")
        cv.rect(panel, left + 25, 125, 750, 735, "#e2e8e5" if i == 0 else "#e7e0ed", radius=25)
        cv.text(panel, f"label-{name}", label, left + 55, 145, 690, 60, 27, color="#40364b")
        camera = Camera(
            projection="perspective",
            distance=6,
            focal=6,
            scale=175,
            origin=(left + 400, 460),
            view=Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.35)),
        )
        props = (PropDrawing(mannequin(), TransformTrack.constant(Frame())),)
        if pair.props:
            props += (PropDrawing(tray_mesh(), pair.props[0].track),)
        result = bake_interaction(
            cv,
            panel,
            tuple(
                Participant(
                    side, getattr(pair, side), "toon", Appearance(sleeve="#6fb2cf", skin="#edbf99", line_width=2.5)
                )
                for side in ("right", "left")
            ),
            props,
            id=f"pair-{name}",
            camera=camera,
            options=BakeOptions(fps=fps),
        )
        report[name] = {side: qa.to_dict() for side, qa in result.reports}
        report[name]["collision_frames"] = sum(bool(pair.sample(j / fps).diagnostics) for j in range(result.frames))
        for side in ("right", "left"):
            save_motion(getattr(pair, side), out / f"{name}-{side}.motion.json")
        cv.text(cv.comp, f"caption-{name}", caption, left + 45, 900, 710, 70, 23, color="#5e5269")
    findings = scene.check(schema=True)
    if findings:
        raise LimbError("two-arm scene failed validation: " + "; ".join(str(f) for f in findings[:5]))
    path = out / "bimanual.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    (out / "bimanual-qa.json").write_text(json.dumps(report, indent=2) + "\n")
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
