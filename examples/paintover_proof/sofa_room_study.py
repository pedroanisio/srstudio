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
and its sofa for the plates of each camera and stands both rigs on their seats in the room, so a rig's drawing, a
caption and a cue here are the reel's. Each card stands at the seat's depth with its base on the cushion's top, SUNK
screen pixels under the seat's line on every camera and frame, its base along that line, a soft shadow under it. On
the push one plate of each depth shows per frame, and the rigs ride a group that takes each frame's scale and place
from the room's own projection of the seat. A study for the paintover pilot's look decision, never a release: it
declares no post and no part, and stays out of episodes/ so nothing ships it.

Two staging rules hold if these cameras go into a reel (arc4d3, 2026-11-02). They are notes for that reel, not kit:

- Both on the sofa. Both figures stay placed in the room for every camera, and neither is removed for a close-up:
  Mae's close-up shows Bruno's edge beside her and Bruno's shows hers. An empty seat appears only when the script
  has the character leave, and then we see them go. This study draws it so.
- Signature marks. The cactus and SR-1028 appear in each scene's establishing shot and on the cover; a close-up may
  leave them out, and there is never a second cactus.
"""

import json
import math
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
from srstudio.toon import fx, fy  # noqa: E402
from srstudio.toon_sketch import Staging, build  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "sofa-room"
FLAGS = ("--push", "--control", "--cast", "--marks", "--silent")
CAMERAS = ("two", "mae", "bruno")
TAKE_FIELDS = {"eye", "look_at", "lens", "spots", "rigs"}
PUSH_FIELDS = {"frames", "seconds", "rig", "spots", "eye"}
MARKS = {"cactus", "code"}
DROP = 88.6  # two-shot px from the reel's seat line down to its rigs' base: the reel's sofa hid that much of each bust
SUNK = (
    12.0  # screen px of the base under the seat's line, on every camera and frame: the cut's ink and a bust's corners
)


def rigs_of(module) -> dict[str, tuple]:
    """Each rig of ``module``: who draws it, where the two-shot and the close-up stand it, and whether it is
    mirrored."""
    return {
        "mae": ("rabbit", module.MAE_AT, module.MAE_CLOSE, True),
        "bruno": ("bear", module.BRUNO_AT, module.BRUNO_CLOSE, False),
    }


RIGS = rigs_of(reel)


def bind(module) -> None:
    """Draw ``module``'s reel from here on: a reel of Mae and Bruno on this sofa that names its shots ``TWO``,
    ``MAE_C`` and ``BRUNO_C`` and stands them at it-autoplayed's places, which the room's plates were drawn for."""
    global reel, RIGS
    places = ("MAE_AT", "BRUNO_AT", "PAIR_SCALE", "MAE_CLOSE", "BRUNO_CLOSE")
    moved = [name for name in places if getattr(module, name) != getattr(reel, name)]
    if moved:
        raise PlateError(f"{module.SLUG} moves {moved} off the places the room's plates were drawn for")
    reel, RIGS = module, rigs_of(module)


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
            if set(take["rigs"]) != set(RIGS) or any(len(seat) != 5 for seat in take["rigs"].values()):
                raise PlateError(
                    f"{path}: camera {name} seats {take['rigs']}, not x, y, ppm, depth, slope for {sorted(RIGS)}"
                )
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
        rigs = shot.cv.group(shot.back, shot.cv.uid("room-carrier"))
        carried(shot.cv, rigs, self.room.pushed()["rig"], lounge.PUSH_FPS)
        return replace(shot, back=rigs)


def lift(scale: float) -> float:
    """Two-shot px to raise a card drawn at `scale` so its base sits SUNK screen px under the seat's line."""
    return DROP - SUNK / scale


def lifted(cv, parent, name: str, scale: float = 1.0):
    """A group that sits a card's base on the cushion's top, inside a parent that draws it at `scale`."""
    return cv.group(parent, cv.uid(f"room-rig-{name}"), y=-lift(scale))


def lifted_on_the_push(cv, parent, name: str, rows: list[list[float]], fps: int):
    """`lifted` inside the group that rides the push, keyed on every frame to that frame's scale, so the seat's edge
    covers the same rows of the card on the last frame as on the first."""
    group = lifted(cv, parent, name)
    cv.keys(group, "y", [(n / fps, -lift(row[2] / rows[0][2])) for n, row in enumerate(rows)], hold=False, local=False)
    return group


def seen(cv, parent, name: str, two: list[float], here: list[float]):
    """A group that takes the two-shot's picture of the card on `name`'s seat into another camera's: the seat point
    `two` (x, y, pixels per metre) to `here`, scaled by the ratio of pixels per metre there and sheared so the card's
    base runs along the seat's line as this camera sees it (`here`'s slope). A billboard: the card faces every camera,
    so no camera sees its edge or its back."""
    ratio = here[2] / two[2]
    held = cv.group(parent, cv.uid("g"), anchorX=two[0], anchorY=two[1], x=here[0], y=here[1], scaleX=ratio,
                    scaleY=ratio, skewY=math.degrees(math.atan(here[4])))  # fmt: skip
    return lifted(cv, held, name, ratio)


def in_the_room(sets: Sets) -> None:
    """The reel's three rig drawers, with both rigs standing on their seats in the room for every camera.

    The two-shot draws them as the reel does, lifted so each base rests on the cushion's top; the push carries that
    with the camera. A close-up draws its own character with the reel's close-up drawer, put back where the two-shot
    stands it and then seen through the close-up's camera, and the other character, drawn as in the two-shot, on its
    own seat: the nearer card in front."""
    two, own = reel._two, {"mae": reel._mae, "bruno": reel._bruno}

    def pair(shot) -> None:
        sets.stage(shot)
        sets.shot_end = shot.app.end
        carrier = sets.riding(shot).back
        if sets.push_shot:
            back = lifted_on_the_push(shot.cv, carrier, "pair", sets.room.pushed()["rig"], lounge.PUSH_FPS)
        else:
            back = lifted(shot.cv, carrier, "pair")
        two(replace(shot, back=back))

    def close_up(subject: str):
        def draw(shot) -> None:
            sets.stage(shot)
            sets.shot_end = shot.app.end
            cv, here, there = shot.cv, sets.room.takes[sets.take]["rigs"], sets.room.takes["two"]["rigs"]
            for name in sorted(RIGS, key=lambda n: -here[n][3]):  # the farther card first
                kind, at, close, mirror = RIGS[name]
                g = seen(cv, shot.back, name, there[name], here[name])
                if name == subject:  # the reel's own close-up drawing, at the two-shot's place and size
                    back = cv.group(g, cv.uid("g"), anchorX=fx(close[0]), anchorY=fy(close[1]), x=fx(at[0]),
                                    y=fy(at[1]), scaleX=reel.PAIR_SCALE, scaleY=reel.PAIR_SCALE)  # fmt: skip
                    own[name](replace(shot, back=back))
                else:
                    reel.toon_pair.figure(shot, g, kind, at, reel.ACTS[kind], scale=reel.PAIR_SCALE, mirror=mirror)

        return draw

    reel._two, reel._mae, reel._bruno = pair, close_up("mae"), close_up("bruno")


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


def sketch_of(root: Path):
    """The sketch the project under ``root`` holds: the reel's, or the ending its recording says when it has two."""
    return reel.sketch_for(root) if hasattr(reel, "sketch_for") else reel.SKETCH


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
        in_the_room(sets)
        dress = bare_cast
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
        in_the_room(sets)
        name = "sofa-push" if moving else SLUG
    staging = Staging(
        sketch=replace(sketch_of(root), slug=SLUG, title="Sofa Room"),
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
