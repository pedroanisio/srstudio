#!/usr/bin/env python3
"""The sofa-room study: one lounge, several cameras, one slow push, the rigs live and unchanged.

    python lounge_plates.py PROJECT --push              # with srlocations' interpreter: PROJECT/plates, room.json
    python plate_fronts.py PROJECT                      # the front plate of every take and every pushed frame
    python sofa_room_study.py PROJECT                   # → sofa-room.scene.xml, two-shot and close-ups on the room
    python sofa_room_study.py PROJECT --push            # → sofa-push.scene.xml, the opening on a camera that moves
    python sofa_room_study.py PROJECT --control         # → sofa-control.scene.xml, the approved set under a 2D push
    python sofa_room_study.py PROJECT --cast [--push]   # the rigs alone on nothing, to measure what the seat must hide
    python sofa_room_study.py PROJECT --marks           # the dots the rigs ride on, to measure how far they drift
    python sofa_room_study.py PROJECT --silent          # any of these on the script's timing: no recording needed

PROJECT is the recorded project of it-autoplayed. The reel's own staging draws every shot: this script swaps its room
and its sofa for the plates of each camera and touches nothing else, so a rig, a caption and a cue here are the reel's.
On the push one plate of each depth shows per frame, and the rigs ride a group that takes each frame's scale and place
from the room's own projection of the seat. A study for the paintover pilot's look decision, never a release: it
declares no post and no part, and stays out of episodes/ so nothing ships it.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent.parent / "episodes")]

import _lounge_set as lounge  # noqa: E402
import numpy as np  # noqa: E402
from paintover_proof_study import PlateError, bare_cast  # noqa: E402
from PIL import Image  # noqa: E402

import it_autoplayed_data as reel  # noqa: E402
from instagram_posts import PINS, POSTS  # noqa: E402
from srstudio import camera, look, show, signature, toon_world  # noqa: E402
from srstudio.toon_sketch import Staging, build  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "sofa-room"
FLAGS = ("--push", "--control", "--cast", "--marks", "--silent")
CAMERAS = ("two", "mae", "bruno")
TAKE_FIELDS = {"eye", "look_at", "lens", "spots"}
PUSH_FIELDS = {"frames", "seconds", "rig", "spots", "eye"}
MARKS = {"cactus", "code"}
CACTUS, CODE = 0.7, 14  # the marks' size on the two-shot; another camera scales them by its own metres


@dataclass(frozen=True)
class Room:
    """What the plate script measured for one room: its cameras, how each frame of the push projects, what it cost."""

    engine: str
    engine_sha256: str
    srlocations_commit: str
    size: list[int]
    seconds: dict[str, float]
    takes: dict[str, dict]
    rig: list[float]
    push: dict

    @classmethod
    def load(cls, path: Path) -> "Room":
        data = json.loads(path.read_text())
        names = {f.name for f in fields(cls)}
        if set(data) != names:
            raise PlateError(f"{path}: expected the fields {sorted(names)}, found {sorted(data)}")
        room = cls(**data)
        if room.srlocations_commit != lounge.SRLOCATIONS_COMMIT:
            raise PlateError(f"{path}: drawn by srlocations {room.srlocations_commit}, not {lounge.SRLOCATIONS_COMMIT}")
        if not re.fullmatch(r"[0-9a-f]{64}", room.engine_sha256):
            raise PlateError(f"{path}: {room.engine_sha256!r} is no sha256 of the engine")
        if room.size != [lounge.WIDTH, lounge.HEIGHT]:
            raise PlateError(f"{path}: the plates are {room.size}, the reel {lounge.WIDTH}x{lounge.HEIGHT}")
        if set(room.takes) != set(CAMERAS):
            raise PlateError(f"{path}: the cameras are {sorted(room.takes)}, not {sorted(CAMERAS)}")
        for name, take in room.takes.items():
            if set(take) != TAKE_FIELDS:
                raise PlateError(f"{path}: camera {name} has {sorted(take)}, not {sorted(TAKE_FIELDS)}")
            if set(take["spots"]) != MARKS:
                raise PlateError(f"{path}: camera {name} places {sorted(take['spots'])}, not {sorted(MARKS)}")
        if room.push:
            room._check_push(path)
        return room

    def _check_push(self, path: Path) -> None:
        if set(self.push) != PUSH_FIELDS:
            raise PlateError(f"{path}: the push has {sorted(self.push)}, not {sorted(PUSH_FIELDS)}")
        frames = self.push["frames"]
        if frames != lounge.PUSH_FRAMES:
            raise PlateError(f"{path}: the push has {frames} frames, not {lounge.PUSH_FRAMES}")
        for name in ("rig", "spots", "eye"):
            if len(self.push[name]) != frames:
                raise PlateError(f"{path}: the push's {name} has {len(self.push[name])} rows for {frames} frames")
        for frame, spots in enumerate(self.push["spots"]):
            if set(spots) != MARKS:
                raise PlateError(f"{path}: frame {frame} of the push places {sorted(spots)}, not {sorted(MARKS)}")

    def pushed(self) -> dict:
        if not self.push:
            raise PlateError("the room was drawn without --push: it has no frames for a moving camera")
        return self.push


def frame_span(frame: int, frames: int, fps: int, end: float) -> dict[str, float]:
    """The times a pushed plate holds: the one frame it is sampled on, the last one to the end of its shot."""
    start = max(0.0, (frame - 0.5) / fps)
    return dict(start=round(start, 5), end=end if frame == frames - 1 else round((frame + 0.5) / fps, 5))


def carried(cv, group, rows: list[list[float]], fps: int) -> None:
    """Hold `group` on a moving point of the room: `rows` are that point's x, y and pixels per metre, frame by frame,
    and the group is drawn as it stands on the first. A key on every frame: nothing is left to an ease between them."""
    x0, y0, ppm0 = rows[0]
    camera.anchor(group, x0, y0, place=True)
    for prop, column in (("x", 0), ("y", 1)):
        cv.keys(group, prop, [(n / fps, row[column]) for n, row in enumerate(rows)], hold=False, local=False)
    scale = [(n / fps, row[2] / ppm0) for n, row in enumerate(rows)]
    cv.keys(group, "scaleX", scale, hold=False, local=False)
    cv.keys(group, "scaleY", scale, hold=False, local=False)


class Sets:
    """The reel's two set drawers on this room's plates, for the camera of the shot being dressed."""

    def __init__(self, room: Room, moving: bool):
        self.room, self.moving = room, moving
        self.added: set[str] = set()
        self.take, self.push_shot, self.shot_end = "two", False, 0.0

    def plate(self, cv, parent, path: str, **span) -> None:
        asset = "plate-" + path.removesuffix(".png").replace("/", "-")
        if asset not in self.added:
            self.added.add(asset)
            cv.assets.add_image(id=asset, src=f"plates/{path}", width=lounge.WIDTH, height=lounge.HEIGHT)
        holder = cv.group(parent, cv.uid("g"), **span) if span else parent
        holder.add_layer(id=cv.uid("plate"), asset=asset, x=0, y=0)

    def frames(self, cv, parent, layer: str, end: float) -> None:
        for frame in range(lounge.PUSH_FRAMES):
            span = frame_span(frame, lounge.PUSH_FRAMES, lounge.PUSH_FPS, end)
            self.plate(cv, parent, lounge.push_plate(frame, layer), **span)

    def stage(self, shot) -> None:
        self.take = {reel.MAE_C: "mae", reel.BRUNO_C: "bruno"}.get(shot.app.who, "two")
        self.push_shot = self.moving and shot.app.who == reel.TWO and shot.app.start == 0.0

    def backdrop(self, shot) -> None:
        """The reel's `_room`: the far plate thrown out of focus, the back plate sharp."""
        cv, end = shot.cv, shot.app.end
        self.stage(shot)
        far = look.depth(cv, shot.back, "sofa-room-far", reel.FAR_BLUR, overscan=True)
        if self.push_shot:
            self.frames(cv, far, "far", end)
            self.frames(cv, shot.back, "back", end)
        else:
            self.plate(cv, far, lounge.plate(self.take, "far"))
            self.plate(cv, shot.back, lounge.plate(self.take, "back"))

    def sofa(self, cv, parent, ground) -> None:
        """The stub the reel's shots call for the sofa: the front plate, and the marks that sit on the room's floor."""
        marks = cv.group(parent, cv.uid("g"))
        if self.push_shot:
            self.frames(cv, marks, "front", self.shot_end)
            rows = self.room.pushed()["spots"]
            self.mark(cv, marks, "cactus", rows[0]["cactus"], rows)
            self.mark(cv, marks, "code", rows[0]["code"], rows)
            return
        self.plate(cv, marks, lounge.plate(self.take, "front"))
        spots = self.room.takes[self.take]["spots"]
        self.mark(cv, marks, "cactus", spots["cactus"])
        self.mark(cv, marks, "code", spots["code"])

    def mark(self, cv, parent, name: str, spot: list[float], rows: list[dict] | None = None) -> None:
        x, y, ppm = spot
        ratio = 1.0 if rows else ppm / self.room.takes["two"]["spots"][name][2]
        holder = cv.group(parent, cv.uid("g"))
        if rows:
            carried(cv, holder, [row[name] for row in rows], lounge.PUSH_FPS)
        if name == "cactus":
            signature.cactus(cv, holder, x, y, CACTUS * ratio)
        else:
            signature.code(cv, holder, x, y, CODE * ratio, color=toon_world.SIGN_CODE, opacity=0.9, align="end")

    def riding(self, shot):
        """`shot` with its back layer on a group that rides the camera, on the shot the camera moves."""
        self.stage(shot)
        self.shot_end = shot.app.end
        if not self.push_shot:
            return shot
        rigs = shot.cv.group(shot.back, shot.cv.uid("g"))
        carried(shot.cv, rigs, self.room.pushed()["rig"], lounge.PUSH_FPS)
        return replace(shot, back=rigs)


def dressed(sets: Sets):
    """The reel's own dress, with its back layer riding the camera once the plates are down."""
    two = reel._two
    reel._two = lambda shot: two(sets.riding(shot))
    return reel.dress


def bare_riding(sets: Sets):
    """The rigs alone with the push, for the base check."""

    def cast(shot) -> None:
        bare_cast(sets.riding(shot) if shot.app.who == reel.TWO else shot)

    return cast


def centroid(path: Path, colour: str) -> tuple[float, float]:
    """Where the dot of `colour` lands on a plate: the mean of its pixels."""
    picture = np.asarray(Image.open(path).convert("RGBA"), dtype=float)
    wanted = np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    weight = np.clip(1.0 - np.abs(picture[..., :3] - wanted).sum(axis=2) / 255.0, 0.0, 1.0) * picture[..., 3] / 255.0
    if weight.sum() == 0:
        raise PlateError(f"{path}: no {colour} dot on the plate")
    rows, columns = np.indices(weight.shape)
    return float((columns * weight).sum() / weight.sum()), float((rows * weight).sum() / weight.sum())


def dots(sets: Sets, first: Path):
    """The tracker's dots as they stand on the first frame of the push, on nothing, riding what the rigs ride."""

    def draw(shot) -> None:
        rigs = sets.riding(shot)
        if not sets.push_shot:
            return
        cv = rigs.cv
        for colour in lounge.TRACK_COLOURS.values():
            x, y = (at + 0.5 for at in centroid(first, colour))  # a pixel's index to the middle of that pixel
            radius = lounge.TRACK_RADIUS * sets.room.pushed()["rig"][0][2]
            cv.ellipse(rigs.back, x - radius, y - radius, 2 * radius, 2 * radius, colour)

    return draw


def staging_of(root: Path, flags: set[str]) -> tuple[Staging, str]:
    moving = "--push" in flags or "--marks" in flags
    room = None if "--control" in flags else Room.load(root / "plates" / "room.json")
    sets = Sets(room, moving) if room else None
    bare = "--cast" in flags or "--marks" in flags
    dress = reel.dress
    move = None
    if "--marks" in flags:
        dress = dots(sets, root / "plates" / lounge.push_plate(0, "track"))
        name = "marks"
    elif "--cast" in flags:
        reel.toon_world = SimpleNamespace(sofa=lambda cv, parent, ground: None)
        dress = bare_riding(sets) if moving else bare_cast
        name = "cast-push" if moving else "cast-room"
    elif "--control" in flags:
        scale = [(n / lounge.PUSH_FPS, lounge.magnification(n)) for n in range(lounge.PUSH_FRAMES)]

        def move(shot, group) -> None:
            if shot.app.start == 0.0:
                camera.anchor(group, lounge.WIDTH / 2, lounge.HEIGHT / 2, place=True)
                camera.push_in(shot.cv, group, scale=scale)

        name = "sofa-control"
    else:
        reel._room = sets.backdrop
        reel.toon_world = SimpleNamespace(sofa=sets.sofa)
        dress = dressed(sets)
        name = "sofa-push" if moving else SLUG
    staging = Staging(
        sketch=replace(reel.SKETCH, slug=SLUG, title="Sofa Room"),
        seed=reel.SEED,
        description="A study: one 3D lounge, several cameras and a moving one, never a release.",
        accessibility=reel.ACCESSIBILITY,
        narration=reel.NARRATION,
        tints=reel.TINTS,
        dress=dress,
        versions=PINS[reel.SLUG],
        desk=toon_world.no_desk,
        bare=reel.BARE,
        overlay=None if bare else reel.overlay,
        captions=(lambda *_: None) if bare else None,
        camera=move,
        output=f"study/{name}.mp4",
        loudness="-14",
        bleed=True,
    )
    return staging, name


def main(argv: list[str]) -> None:
    root = Path(argv[1]).resolve()
    flags = set(argv[2:])
    if flags - set(FLAGS):
        raise SystemExit(f"flags: {' '.join(FLAGS)}")
    reel.validate(reel.SKETCH)
    staging, name = staging_of(root, flags)
    ep = build(root, staging, set() if "--silent" in flags else {"--voice"})
    bare = "--cast" in flags or "--marks" in flags
    if bare:
        ep.scene.find("project").background = "#00000000"
        ep.cv.signature = None  # the measuring picture: it has no set to carry the marks
    with show.stamping(None if bare else POSTS[reel.SLUG].thumbnail.number):
        ep.finish(root / f"{name}.scene.xml", root / "qa" / f"{name}-validation.json")


if __name__ == "__main__":
    main(sys.argv)
