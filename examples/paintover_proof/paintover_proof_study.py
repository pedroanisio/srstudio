#!/usr/bin/env python3
"""Paintover proof: the opening of it-autoplayed re-staged on a 3D lounge, the rigs live and unchanged.

    python lounge_plates.py PROJECT                     # with srlocations' interpreter: PROJECT/plates
    python plate_fronts.py PROJECT                      # the front plates, cut from the back plates
    python paintover_proof_study.py PROJECT             # → PROJECT/paintover-proof.scene.xml, the 3D plates
    python paintover_proof_study.py PROJECT --control   # the approved set, to show the rigs did not change
    python paintover_proof_study.py PROJECT --cast      # the rigs alone on nothing, to measure what the seat must hide
    python paintover_proof_study.py PROJECT --silent    # any of these on the script's timing: no recording needed

PROJECT holds the recorded project of it-autoplayed (script.json, narration.json, voiced/, audio/, assets/). The reel's
own staging draws every shot: this script swaps its room and its sofa for the plates and touches nothing else, so a rig,
a caption and a cue here are the reel's. Far plate blurred as the approved room is; back plate sharp; rigs; front plate.
A study for the paintover pilot's look decision, never a release: it declares no post and no part, and stays out of
episodes/ so nothing ships it.
"""

import json
import os
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent.parent / "episodes")]

import _lounge_set as lounge  # noqa: E402

import it_autoplayed_data as reel  # noqa: E402
from instagram_posts import PINS, POSTS  # noqa: E402
from srstudio import look, show, signature, toon_world  # noqa: E402
from srstudio.toon_sketch import Staging, build  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "paintover-proof"
FLAGS = ("--control", "--cast", "--silent")


class PlateError(ValueError):
    """The plate script's record does not describe the plates this study draws."""


@dataclass(frozen=True)
class Registration:
    """What the plate script measured: where the set's marks land, and how long each layer took."""

    seconds: dict[str, float]
    engine: str
    srlocations_commit: str
    spots: dict[str, list[float]]
    size: list[int]

    @classmethod
    def load(cls, path: Path) -> "Registration":
        data = json.loads(path.read_text())
        names = {f.name for f in fields(cls)}
        if set(data) != names:
            raise PlateError(f"{path}: expected the fields {sorted(names)}, found {sorted(data)}")
        record = cls(**data)
        if record.srlocations_commit != lounge.SRLOCATIONS_COMMIT:
            raise PlateError(
                f"{path}: drawn by srlocations {record.srlocations_commit}, not {lounge.SRLOCATIONS_COMMIT}"
            )
        if record.size != [lounge.WIDTH, lounge.HEIGHT]:
            raise PlateError(f"{path}: the plates are {record.size}, the reel {lounge.WIDTH}x{lounge.HEIGHT}")
        if set(record.seconds) != set(lounge.LAYERS):
            raise PlateError(f"{path}: the layers are {sorted(record.seconds)}, not {sorted(lounge.LAYERS)}")
        if set(record.spots) != {"cactus", "code"}:
            raise PlateError(f"{path}: the spots are {sorted(record.spots)}, not cactus and code")
        return record


def plate(cv, parent, name: str) -> None:
    asset = f"plate-{name}"
    if asset not in _ADDED:
        _ADDED.add(asset)
        cv.assets.add_image(id=asset, src=f"plates/{name}.png", width=lounge.WIDTH, height=lounge.HEIGHT)
    parent.add_layer(id=cv.uid("plate"), asset=asset, x=0, y=0)


_ADDED: set[str] = set()


def staged(registration: Registration):
    """The reel's two set drawers as plates: its `_room` and the `sofa` its shots call."""

    def room(shot) -> None:
        cv = shot.cv
        plate(cv, look.depth(cv, shot.back, "paintover-far", reel.FAR_BLUR, overscan=True), "far")
        plate(cv, shot.back, "back")

    def sofa(cv, parent, ground) -> None:
        plate(cv, parent, "front")
        marks = cv.group(parent, cv.uid("g"))
        signature.cactus(cv, marks, *registration.spots["cactus"], 0.7)
        signature.code(cv, marks, *registration.spots["code"], 14, color=toon_world.SIGN_CODE, opacity=0.9, align="end")

    return room, sofa


def bare_cast(shot) -> None:
    """The rigs and their arms alone, for the base check: no set, no signature, no light."""
    who = shot.app.who
    if who != reel.MENU:
        {reel.TWO: reel._two, reel.MAE_C: reel._mae, reel.BRUNO_C: reel._bruno}[who](shot)


def main(argv: list[str]) -> None:
    root = Path(argv[1]).resolve()
    flags = set(argv[2:])
    if flags - set(FLAGS):
        raise SystemExit(f"flags: {' '.join(FLAGS)}")
    dress = reel.dress
    if "--cast" in flags:
        reel.toon_world = SimpleNamespace(sofa=lambda cv, parent, ground: None)
        dress = bare_cast
    elif "--control" not in flags:
        registration = Registration.load(root / "plates" / "registration.json")
        reel._room, sofa = staged(registration)
        reel.toon_world = SimpleNamespace(sofa=sofa)
    reel.validate(reel.SKETCH)
    staging = Staging(
        sketch=replace(reel.SKETCH, slug=SLUG, title="Paintover Proof"),
        seed=reel.SEED,
        description="A study: the opening of it-autoplayed on a 3D lounge, never a release.",
        accessibility=reel.ACCESSIBILITY,
        narration=reel.NARRATION,
        tints=reel.TINTS,
        dress=dress,
        versions=PINS[reel.SLUG],
        desk=toon_world.no_desk,
        bare=reel.BARE,
        overlay=None if "--cast" in flags else reel.overlay,
        captions=(lambda *_: None) if "--cast" in flags else None,
        output="study/paintover-proof.mp4",
        loudness="-14",
        bleed=True,
    )
    ep = build(root, staging, set() if "--silent" in flags else {"--voice"})
    if "--cast" in flags:
        ep.scene.find("project").background = "#00000000"
        ep.cv.signature = None  # the measuring picture: it has no set to carry the marks
    name = "cast" if "--cast" in flags else "control" if "--control" in flags else SLUG
    with show.stamping(None if "--cast" in flags else POSTS[reel.SLUG].thumbnail.number):
        ep.finish(root / f"{name}.scene.xml", root / "qa" / f"{name}-validation.json")


if __name__ == "__main__":
    main(sys.argv)
