#!/usr/bin/env python3
"""The clay look study: Mae and Bruno as clay figures seated in the sofa room, against the flat cards.

    python clay_sofa_study.py perform PROJECT           # → PROJECT/clay/performance.json, from the reel's own staging
    python clay_sofa_study.py render PROJECT [--push]   # → PROJECT/clay/room/ and room-ink/ (or push/, push-ink/):
                                                        # every frame's composite, plain and with the room's line
    python clay_sofa_study.py scene PROJECT [--push] [--ink]  # → PROJECT/clay-room[-ink].scene.xml, clay-push[-ink]

PROJECT is the recorded project of it-autoplayed with the room's plates (examples/paintover_proof/lounge_plates.py and
plate_fronts.py) under plates/, and under clean-plates/ the same room drawn without the soft shadows lounge_plates lays
under each card (lounge_plates.py and plate_fronts.py as of a0892384, the commit before sitting() came in): the clay
casts its own shadows, so its back plates come from there. Only the seat strips differ between the two sets. The
reel's own staging draws every shot, its captions, its glow and the marks; this script takes the cards out and puts
in their place, frame by frame, the room's back plate with the clay figures on it (:mod:`clay_room`). Both figures
stay on the sofa for every camera, so a close-up shows the other one's edge. The front plate is not laid over the
clay: a card needs the seat's edge to hide its base, the clay sits on the seat and the K pass already says where the
sofa stands in front of it.

Known differences from the flat, for the operator's eye: Bruno sits on his card's column, over the sofa's drawn arm as
the flat lays him, so the sofa's arm takes no bounce or shadow from him (:data:`KNOWN_DIFFERENCES`).

A look study for the operator's decision on Mae and Bruno, never a release: it declares no post and no part, and stays
out of episodes/ so nothing ships it.
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "paintover_proof"), str(HERE.parent.parent / "episodes")]

import _lounge_set as lounge  # noqa: E402
import clay_anatomy as ca  # noqa: E402
import clay_figure as cf  # noqa: E402
import clay_ink as ci  # noqa: E402
import clay_room as cr  # noqa: E402
import numpy as np  # noqa: E402
import performance as pf  # noqa: E402
import sofa_room_study as study  # noqa: E402

import it_autoplayed_data as reel  # noqa: E402
from instagram_posts import PINS, POSTS  # noqa: E402
from srstudio import look, show, toon, toon_bed, toon_pair, toon_redrawn, toon_world  # noqa: E402
from srstudio.plates import Material  # noqa: E402
from srstudio.styles import TOON  # noqa: E402
from srstudio.thumbnail import ShowCover  # noqa: E402
from srstudio.toon_sketch import Staging, build  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "clay-sofa"
CLEAN = "clean-plates"  # the room's plates drawn without the cards' seat shadows: the clay casts its own
ROOM_FRAMES = 191  # 0 to 7.917 s, as the room's encode renders them: the two-shot, her close-up and his
PUSH_FRAMES = lounge.PUSH_FRAMES + 1  # the push's 110 cameras, and the two-shot's last frame on the last of them
TAKES = {"two": (0, 110), "mae": (111, 159), "bruno": (160, 190)}
RIGS = {"mae": toon_redrawn.RABBIT_RIG, "bruno": toon_redrawn.BEAR_RIG}
PALETTE = TOON.palettes[0]  # the reel's canvas: its ink and white paint the clay's faces
OWNERS = {"mae": "rabbit", "bruno": "bear"}  # the characters' parts, as the anatomy ledger names them


def frames_of(start: float, end: float) -> tuple[int, int]:
    """The first and last frame a shot from ``start`` to ``end`` seconds shows: those whose time falls inside it."""
    fps = lounge.PUSH_FPS
    return math.ceil(start * fps - 1e-9), min(math.ceil(end * fps - 1e-9) - 1, ROOM_FRAMES - 1)


def take_of(frame: int) -> str:
    return next(name for name, (first, last) in TAKES.items() if first <= frame <= last)


def lens_of(room: study.Room, take: str, frame: int | None = None) -> cr.Camera:
    """The camera of ``take``; with ``frame``, the push's camera on that frame (it holds its last one)."""
    if frame is None:
        row = room.takes[take]
        return cr.camera_of(row["eye"], row["look_at"], row["lens"])
    eye = room.pushed()["eye"][min(frame, lounge.PUSH_FRAMES - 1)]
    ahead = np.array(eye) - np.array(lounge.EYE)
    return cr.camera_of(eye, tuple(np.array(lounge.LOOK_AT) + ahead), lounge.LENS)


KNOWN_DIFFERENCES = ("no sofa-arm bounce or shadow on Bruno's right side; he sits over the drawn arm as the flat does",)

GAP = 0.006  # metres the clay keeps from the other figure: touching, not passing through


def seats(room: study.Room, performance: pf.Performance) -> dict[str, cr.Seat]:
    """Where each figure sits, on the column of its card's seat on the two-shot and as tall as the card there. Mae
    sits back against the sofa; the drawing lays Bruno over her, so he sits as far forward as it takes for none of him
    to pass through her (at rest, on frame 0). Bruno's column runs over the sofa's drawn arm, and the flat lays him over
    it: so does this study (the arm has no stand-in in the passes)."""
    two = lens_of(room, "two")
    per = toon.SCALE * reel.PAIR_SCALE
    back = cr.SOFA_BACK_FRONT - cr.BACK_CLEARANCE
    mae = cr.seat_of(cf.figure(RIGS["mae"]), lounge.SEAT_MAE, two, per, True, back)
    resting = cr.posed("mae", RIGS["mae"], cf.figure(RIGS["mae"]), performance.at("mae", 0), mae)
    bruno_back = back
    for _ in range(8):
        bruno = cr.seat_of(cf.figure(RIGS["bruno"]), lounge.SEAT_BRUNO, two, per, False, bruno_back)
        his = cr.posed("bruno", RIGS["bruno"], cf.figure(RIGS["bruno"]), performance.at("bruno", 0), bruno)
        short = GAP - cr.clearance(his, resting)
        if short <= 0.0005:
            break
        bruno_back -= short
    else:
        raise cr.RenderError(f"Bruno does not settle in front of Mae: {short:.4f} m short")
    return {"mae": mae, "bruno": bruno}


def figures_at(performance: pf.Performance, frame: int, places: dict[str, cr.Seat]):
    """Both figures at ``frame``: each one's posed parts, and the materials they use."""
    parts: dict[str, tuple[cr.Part, ...]] = {}
    materials: list[Material] = []
    for who in ("mae", "bruno"):
        rig = RIGS[who]
        parts[who] = cr.posed_parts(who, rig, cf.figure(rig), performance.at(who, frame), places[who])
        materials += cr.materials(who, rig, [mesh for part in parts[who] for mesh in part.meshes])
    return parts, tuple(materials)


def clay_root(root: Path) -> Path:
    return root / "clay"


def render(root: Path, push: bool, frames: range | None = None) -> dict:
    """Every frame's four passes and its composite, plain and inked with the room's line; and on every frame the hands
    each figure draws, counted by the anatomy rule (ADR 0174). Returns what the engine spent and, per frame, where its
    passes are and what was counted."""
    cf.use_palette(PALETTE.ink, PALETTE.white)
    room = study.Room.load(root / "plates" / "room.json")
    performance = pf.Performance.load(clay_root(root) / "performance.json")
    places = seats(room, performance)
    kind = "push" if push else "room"
    count = PUSH_FRAMES if push else ROOM_FRAMES
    cache = clay_root(root) / "cache"
    spent = cr.Spent.new()
    index = {}
    for n in frames if frames is not None else range(count):
        if push:
            lens, back = lens_of(room, "two", n), lounge.push_plate(min(n, lounge.PUSH_FRAMES - 1), "back")
        else:
            take = take_of(n)
            lens, back = lens_of(room, take), lounge.plate(take, "back")
        parts, materials = figures_at(performance, n, places)
        p, k, b, i = cr.passes(parts, materials, lens, cache, spent)
        picture, _ = cr.composite(cr.rgba(root / CLEAN / back), cr.rgba(p), cr.rgba(k), cr.rgba(b))
        cr.write(clay_root(root) / kind / f"{n:04d}.png", picture)
        cr.write(clay_root(root) / f"{kind}-ink" / f"{n:04d}.png", ci.ink(picture, cr.rgba(i), ci.ROOM_LINE))
        counted = ca.count({OWNERS[who]: parts[who] for who in parts}, lens)
        if counted.notes:
            raise cr.RenderError(f"{kind} frame {n}: " + "; ".join(str(note) for note in counted.notes))
        meshes = [mesh for who in parts for part in parts[who] for mesh in part.meshes]
        index[n] = dict(P=p.name, K=k.name, B=b.name, I=i.name, back=back, low=_lowest(meshes), hands=counted.hands)
        print(f"{kind} {n}: {spent.runs} {spent.seconds}", flush=True)
    record = dict(spent=dict(seconds=spent.seconds, runs=spent.runs, cached=spent.cached), frames=index)
    out = clay_root(root) / f"render-{kind}-{min(index)}-{max(index)}.json"
    out.write_text(json.dumps(record, indent=1) + "\n")
    return record


def _lowest(meshes) -> dict[str, float]:
    """Each figure's lowest point, in metres above the cushion's top: its seat contact (below 0 it presses in)."""
    out = {}
    for who in ("mae", "bruno"):
        lows = [-m.vertices[:, 1].max() / 100.0 for m in meshes if m.material.startswith(who)]
        out[who] = round(min(lows) - cr.CUSHION_TOP, 5)
    return out


# --- the staging ------------------------------------------------------------------------------------------------------


class ClaySets(study.Sets):
    """The room's sets with the clay composites where the back plate was, and no front plate over them."""

    def __init__(self, room: study.Room, moving: bool, root: Path, ink: bool = False):
        super().__init__(room, moving)
        self.root = root
        self.ink = ink

    def composites(self, cv, parent, kind: str, first: int, last: int, start: float, end: float) -> None:
        folder = f"{kind}-ink" if self.ink else kind
        for n in range(first, last + 1):
            asset = f"clay-{folder}-{n:04d}"
            if asset not in self.added:
                self.added.add(asset)
                cv.assets.add_image(
                    id=asset, src=f"clay/{folder}/{n:04d}.png", width=lounge.WIDTH, height=lounge.HEIGHT
                )
            span = study.frame_span(n, last + 1, lounge.PUSH_FPS, end)
            if n == first:  # the shot's first frame holds from the cut
                span["start"] = start
            holder = cv.group(parent, cv.uid("g"), **span)
            holder.add_layer(id=cv.uid("clay"), asset=asset, x=0, y=0)

    def backdrop(self, shot) -> None:
        cv, app = shot.cv, shot.app
        self.stage(shot)
        far = look.depth(cv, shot.back, "sofa-room-far", reel.FAR_BLUR, overscan=True)
        first, last = frames_of(app.start, app.end)
        if self.push_shot:
            self.frames(cv, far, "far", app.end)
            self.composites(cv, shot.back, "push", first, min(last, PUSH_FRAMES - 1), app.start, app.end)
        else:
            self.plate(cv, far, lounge.plate(self.take, "far"))
            self.composites(cv, shot.back, "room", first, last, app.start, app.end)

    def sofa(self, cv, parent, ground) -> None:
        """The marks on the room's floor and table, and no front plate: the clay sits on the seat."""
        marks = cv.group(parent, cv.uid("g"))
        if self.push_shot:
            rows = self.room.pushed()["spots"]
            self.mark(cv, marks, "cactus", rows[0]["cactus"], rows)
            self.mark(cv, marks, "code", rows[0]["code"], rows)
            return
        spots = self.room.takes[self.take]["spots"]
        self.mark(cv, marks, "cactus", spots["cactus"])
        self.mark(cv, marks, "code", spots["code"])


def _nothing(shot, parent, *args, **kwargs):
    return shot.cv.group(parent, shot.cv.uid("g"))


def _no_arm(cv, parent, *args, **kwargs):
    return cv.group(parent, cv.uid("g"))


def staging_of(root: Path, push: bool, ink: bool = False) -> tuple[Staging, str]:
    room = study.Room.load(root / "plates" / "room.json")
    sets = ClaySets(room, push, root, ink)
    reel._room = sets.backdrop
    # the reel's modules stood in for by just what its staging calls of them
    reel.toon_world = SimpleNamespace(sofa=sets.sofa)  # type: ignore[assignment]
    reel.toon_pair = SimpleNamespace(figure=_nothing, aim=toon_pair.aim)  # type: ignore[assignment]  # the cards out
    reel.toon_bed = SimpleNamespace(swung_arm=_no_arm, ARM_WIDTH=toon_bed.ARM_WIDTH)  # type: ignore[assignment]
    name = ("clay-push" if push else "clay-room") + ("-ink" if ink else "")
    staging = Staging(
        sketch=replace(reel.SKETCH, slug=SLUG, title="Clay Sofa"),
        seed=reel.SEED,
        description="A study: Mae and Bruno as clay in the 3D lounge, never a release.",
        accessibility=reel.ACCESSIBILITY,
        narration=reel.NARRATION,
        tints=reel.TINTS,
        dress=reel.dress,
        versions=PINS[reel.SLUG],
        desk=toon_world.no_desk,
        bare=reel.BARE,
        overlay=reel.overlay,
        captions=None,
        camera=None,
        output=f"study/{name}.mp4",
        loudness="-14",
        bleed=True,
    )
    return staging, name


def scene(root: Path, push: bool, ink: bool = False) -> Path:
    reel.validate(reel.SKETCH)
    staging, name = staging_of(root, push, ink)
    ep = build(root, staging, {"--voice"})
    if ep is None:
        raise cr.RenderError(f"the staging of {name} built no episode")
    cover = POSTS[reel.SLUG].thumbnail
    if not isinstance(cover, ShowCover):
        raise cr.RenderError(f"{reel.SLUG} carries no show cover to stamp its number from")
    out = root / f"{name}.scene.xml"
    with show.stamping(cover.number):
        ep.finish(out, root / "qa" / f"{name}-validation.json")
    return out


def main(argv: list[str]) -> None:
    if len(argv) < 3 or argv[1] not in ("perform", "render", "scene"):
        raise SystemExit(__doc__)
    command, root, flags = argv[1], Path(argv[2]).resolve(), set(argv[3:])
    if flags - {"--push", "--ink"} or ("--ink" in flags and command != "scene"):
        raise SystemExit("the flags are --push, and --ink for a scene")
    clay_root(root).mkdir(exist_ok=True)
    if command == "perform":
        performance = pf.capture(root, ROOM_FRAMES)
        performance.dump(clay_root(root) / "performance.json")
        pf.Performance.load(clay_root(root) / "performance.json")
    elif command == "render":
        render(root, "--push" in flags)
    else:
        print(scene(root, "--push" in flags, "--ink" in flags))


if __name__ == "__main__":
    main(sys.argv)
