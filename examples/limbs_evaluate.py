"""Build matched legacy/spatial tasks, engineering measurements and a blinded review packet.

Run with --engine /path/to/scene-render to encode the six clips. Supply real reviews with --ratings FILE.
The review key comes from --seed or SRSTUDIO_LIMBS_REVIEW_SEED and must stay private; there is no default.
Supply observed human authoring attempts with --authoring FILE.
The implementation key and engineering report stay outside the public review directory.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas, gloss, stick, toon_cast
from srstudio.limbs import HUMAN, MITTEN, ArmProfile, Camera, HandControl, LimbError, Vec3
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.compile import BakeOptions, Occlusion
from srstudio.limbs.evaluation import (
    Pair,
    compare_sources,
    measure,
    parse_authoring,
    parse_ratings,
    plan_trials,
    summarize,
    summarize_authoring,
)
from srstudio.limbs.integration import LimbTrack
from srstudio.limbs.motion import Action, Motion, Target
from srstudio.limbs.serialization import read_document
from srstudio.toon import Pose


def _canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=640, height=800, fps="24", duration=2, background="#f4f0e9")
    scene.add_metadata(generator="srstudio.limbs; evaluation example authored with Codex")
    return Canvas(scene, width=640, height=800, font_asset=None)


def _track(
    style: str,
    side: str,
    action: str,
    target: Vec3,
    origin: tuple[float, float],
    scale: float,
    *,
    pole: Vec3 | None = None,
) -> LimbTrack:
    skin = {"stick": stick.SKIN, "toon": toon_cast.DOG.coat, "gloss": gloss.SKIN["tan"]}[style]
    sleeve = {"stick": "#15151b", "toon": toon_cast.DOG.coat, "gloss": "#2fb3a6"}[style]
    arm = ArmProfile(side=side, width={"stick": 0.10, "toon": 0.40, "gloss": 0.37}[style])
    hand, control = HUMAN, None
    if style == "toon":
        arm = replace(arm, upper=0.6, forearm=0.75)
        hand = replace(
            MITTEN,
            palm_length=MITTEN.palm_length * 0.7,
            digits=tuple(
                replace(d, base=d.base * 0.7, lengths=tuple(v * 0.7 for v in d.lengths)) for d in MITTEN.digits
            ),
        )
        control = HandControl(curl=1, opposition=0.8, cup=0.3)
    motion = Motion(arm, hand, (Action(action, duration=2, target=Target(target), pole=pole, control=control),))
    return LimbTrack(
        motion,
        style=style,
        camera=Camera(origin=origin, scale=scale),
        appearance=Appearance(skin=skin, sleeve=sleeve, line_width=3),
        options=BakeOptions(fps=24),
        occlusion=(Occlusion("palm", 0, 2, "front"), Occlusion("digit:*", 0, 2, "front")) if style == "toon" else (),
    )


def legacy_stick() -> Scene:
    cv = _canvas()
    stick.rig(
        cv,
        cv.comp,
        (stick.RigKey(0, "stand"), stick.RigKey(0.8, "point"), stick.RigKey(1.5, "stand")),
        2,
        poses=stick.STANDING,
        at=(55, -55),
        scale=0.48,
    )
    return cv.scene


def spatial_stick() -> Scene:
    cv = _canvas()
    track = _track(
        "stick", "right", "point", Vec3(276 / 285, 5 / 285, 0), (536, 891), 150, pole=Vec3(144 / 150, 29 / 150, 0)
    )
    stick.rig(
        cv, cv.comp, (stick.RigKey(0, "stand"),), 2, poses=stick.STANDING, at=(55, -55), scale=0.48, limbs=(track,)
    )
    return cv.scene


def legacy_toon() -> Scene:
    cv = _canvas()
    placed = cv.group(cv.comp, "placement", x=130, y=-140, scaleX=0.6, scaleY=0.6)
    toon_cast.dog(
        cv,
        placed,
        (Pose(0, "wide", "flat", "desk"), Pose(0.8, "wide", "flat", "face"), Pose(1.5, "wide", "flat", "desk")),
        2,
    )
    return cv.scene


def spatial_toon() -> Scene:
    cv = _canvas()
    placed = cv.group(cv.comp, "placement", x=130, y=-140, scaleX=0.6, scaleY=0.6)
    tracks = tuple(
        _track("toon", side, "facepalm", Vec3(-79 / 135, -48 / 135, 0), (x, 712), 100, pole=Vec3(pole, 1, 0))
        for side, x, pole in (("right", 308, 1), ("left", 62, -1))
    )
    toon_cast.dog(cv, placed, (Pose(0, "wide", "flat", "desk"),), 2, limbs=tracks)
    return cv.scene


def legacy_gloss() -> Scene:
    cv = _canvas()
    gloss.nadia(cv, cv.comp, at=(320, 750), scale=0.9, end=2, pose=((0, "down"), (0.8, "shrug"), (1.5, "down")))
    return cv.scene


def spatial_gloss() -> Scene:
    cv = _canvas()
    tracks = tuple(
        _track("gloss", side, "shrug", Vec3(94 / 190, -55 / 190, 0), (sign * 92, -345), 100, pole=Vec3(sign, 0.3, 0))
        for side, sign in (("right", 1), ("left", -1))
    )
    gloss.nadia(cv, cv.comp, at=(320, 750), scale=0.9, end=2, limbs=tracks)
    return cv.scene


BUILDERS = {
    "legacy-stick": legacy_stick,
    "spatial-stick": spatial_stick,
    "legacy-toon": legacy_toon,
    "spatial-toon": spatial_toon,
    "legacy-gloss": legacy_gloss,
    "spatial-gloss": spatial_gloss,
}
PAIRS = (
    Pair("point", "Point to the right", "legacy-stick", "spatial-stick"),
    Pair("face", "Raise both hands over the face", "legacy-toon", "spatial-toon"),
    Pair("shrug", "Shrug with both hands raised", "legacy-gloss", "spatial-gloss"),
)


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    path.chmod(0o600)


def build(
    out: Path,
    *,
    seed: str,
    repeats: int = 3,
    engine: str | None = None,
    ratings: Path | None = None,
    authoring: Path | None = None,
) -> Path:
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    public, scenes = out / "review", out / "scenes"
    for directory in (public, scenes):
        directory.mkdir(exist_ok=True, mode=0o700)
    trials = plan_trials(PAIRS, seed=seed)
    observed = ()
    if ratings is not None:
        observed = parse_ratings(read_document(ratings, "rating"))
    summary = summarize(trials, observed)
    authoring_records = ()
    if authoring is not None:
        authoring_records = parse_authoring(read_document(authoring, "authoring"))
    authoring_summary = summarize_authoring(PAIRS, authoring_records)
    measured = {name: measure(name, builder, repeats=repeats) for name, builder in BUILDERS.items()}
    measurements = [item.to_dict() for item in measured.values()]
    sources = {pair.id: compare_sources(measured[pair.baseline], measured[pair.candidate]).to_dict() for pair in PAIRS}
    for trial in trials:
        for side in ("a", "b"):
            name = getattr(trial, side)
            scene = BUILDERS[name]()
            scene.add_output(
                id="main",
                path=f"../review/{trial.id}-{side.upper()}.mp4",
                codec="h264",
                width=640,
                height=800,
                fps="24",
                preset="fast",
                crf="18",
                faststart=True,
            )
            findings = scene.check(schema=True)
            if findings:
                raise LimbError("evaluation output failed schema validation: " + str(findings[0]))
            path = scenes / f"{name}.scene.xml"
            path.write_bytes(scene.to_bytes(layout="pretty"))
            path.chmod(0o600)
            if engine:
                subprocess.run([engine, "encode", str(path.resolve())], check=True)
    _write(
        public / "trials.json", {"schema": "srstudio.limbs.review/1.0.0", "trials": [t.public_dict() for t in trials]}
    )
    if not (public / "ratings-template.json").exists():
        _write(public / "ratings-template.json", {"schema": "srstudio.limbs.ratings/1.0.0", "ratings": []})
    (public / "instructions.txt").write_text(
        "Watch each pair without consulting the private implementation key. Rate each clip from 1 (poor) to 5 "
        "(excellent) for clarity of the task, naturalness of movement, and fit with the drawing style. "
        "Record one preference (a, b, or tie) per trial. Use a stable anonymous reviewer ID.\n"
        'Each ratings entry: {"trial":"trial-001","reviewer":"your-ID","preference":"tie",'
        '"a":{"clarity":3,"naturalness":3,"style_fit":3},'
        '"b":{"clarity":3,"naturalness":3,"style_fit":3},"notes":"optional"}. '
        "Replace illustrative scores with your own observations.\n"
    )
    if not (out / "authoring-template.json").exists():
        _write(out / "authoring-template.json", {"schema": "srstudio.limbs.authoring/1.0.0", "records": []})
    _write(out / "private-key.json", {"trials": [asdict(t) for t in trials]})
    report = out / "evaluation.json"
    _write(
        report,
        {
            "schema": "srstudio.limbs.evaluation/1.2.0",
            "measurements": measurements,
            "source_comparison": sources,
            "review": summary,
            "authoring": authoring_summary,
            "limitations": [
                "Build times exclude schema validation, serialization and video rendering.",
                "Source lines count each entry function and the example functions it reaches; a pair's "
                "source_comparison excludes helpers both sides reach. Library code is excluded from both.",
                "Authoring time, completion and author identity are caller-supplied and not independently verified.",
                "Tasks match intent and framing, not exact pose geometry or hand silhouettes.",
                "Legacy holds switch at 0.8 and 1.5 seconds; spatial gestures use continuous phases.",
                "Ratings are descriptive observations, not evidence of statistical significance.",
            ],
            "clips_encoded": bool(engine),
        },
    )
    for path in public.iterdir():
        if path.is_file():
            path.chmod(0o600)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--engine")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--ratings", type=Path)
    parser.add_argument("--authoring", type=Path)
    parser.add_argument("--seed", help="private review key; defaults to $SRSTUDIO_LIMBS_REVIEW_SEED")
    args = parser.parse_args()
    seed = args.seed or os.environ.get("SRSTUDIO_LIMBS_REVIEW_SEED")
    if not seed:
        parser.error("a private review key is required: pass --seed or set SRSTUDIO_LIMBS_REVIEW_SEED")
    print(
        build(
            args.out,
            seed=seed,
            repeats=args.repeats,
            engine=args.engine,
            ratings=args.ratings,
            authoring=args.authoring,
        )
    )


if __name__ == "__main__":
    main()
