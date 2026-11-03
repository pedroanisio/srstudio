#!/usr/bin/env python3
"""Mae and Bruno as clay figures seated in the sofa room: the clay look study on it-autoplayed, and the pipeline of a
clay reel on the same sofa (grown-on-me), which reads that reel's own staging.

    python clay_sofa_study.py perform PROJECT [--reel MODULE]          # → PROJECT/clay/performance.json, from the
                                                                       # reel's own staging, every frame of it
    python clay_sofa_study.py render PROJECT [--push] [--reel MODULE]  # → PROJECT/clay/room/ and room-ink/ (or
                                                                       # push/, push-ink/): every frame a camera on
                                                                       # the room sees, plain and with the room's line
    python clay_sofa_study.py scene PROJECT [--push] [--ink]  # → PROJECT/clay-room[-ink].scene.xml, clay-push[-ink]

MODULE is the reel's data module under episodes/ (it_autoplayed_data unless named): the reel's shot names, its places,
its acts and its moves (:mod:`performance`) all come from it; a reel's own build makes its master from these frames
(:func:`episode_staging`). PROJECT is the recorded project of the reel with the room's plates
(examples/paintover_proof/lounge_plates.py and plate_fronts.py) under plates/, and under clean-plates/ the same room
drawn without the soft shadows lounge_plates lays under each card (lounge_plates.py and plate_fronts.py as of a0892384,
the commit before sitting() came in): the clay casts its own shadows, so its back plates come from there. Only the seat
strips differ between the two sets. The reel's own staging draws every shot, its captions, its glow and the marks; this
script takes the cards out and puts in their place, frame by frame, the room's back plate with the clay figures on it
(:mod:`clay_room`). Both figures stay on the sofa for every camera, so a close-up shows the other one's edge. The front
plate's seat strip is not laid over the clay: a card needs the seat's edge to hide its base, the clay sits on the seat.
Its arm is: the flat has the sofa's arm in front of Bruno's right side.

Known differences from the flat, for the operator's eye, are in :data:`KNOWN_DIFFERENCES`.

On it-autoplayed this is a look study, never a release: it declares no post and no part. A clay reel declares its own
post and parts and ships from its own episode script, which builds through :func:`episode_staging`.
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

import importlib  # noqa: E402

import _lounge_set as lounge  # noqa: E402
import clay_anatomy as ca  # noqa: E402
import clay_figure as cf  # noqa: E402
import clay_ink as ci  # noqa: E402
import clay_room as cr  # noqa: E402
import numpy as np  # noqa: E402
import performance as pf  # noqa: E402
import sofa_room_study as study  # noqa: E402
from shapely import contains_xy  # noqa: E402

import it_autoplayed_data as reel  # noqa: E402
from instagram_posts import PINS, POSTS  # noqa: E402
from srstudio import look, show, toon, toon_bed, toon_everyday, toon_pair, toon_redrawn, toon_world  # noqa: E402
from srstudio.plates import Material  # noqa: E402
from srstudio.styles import TOON  # noqa: E402
from srstudio.thumbnail import ShowCover  # noqa: E402
from srstudio.toon_sketch import Staging, build  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "clay-sofa"
CLEAN = "clean-plates"  # the room's plates drawn without the cards' seat shadows: the clay casts its own
PUSH_FRAMES = lounge.PUSH_FRAMES + 1  # the push's 110 cameras, and the two-shot's last frame on the last of them
real_everyday = toon_everyday  # the library's, which the clay staging stands a reel's flat remote in for
RIGS = {"mae": toon_redrawn.RABBIT_RIG, "bruno": toon_redrawn.BEAR_RIG}
PALETTE = TOON.palettes[0]  # the reel's canvas: its ink and white paint the clay's faces
OWNERS = {"mae": "rabbit", "bruno": "bear"}  # the characters' parts, as the anatomy ledger names them


def bind(module) -> None:
    """Draw ``module``'s reel from here on, here and in the sofa room's staging."""
    global reel
    study.bind(module)
    reel = module


def reel_of(name: str):
    """The reel data module ``name`` under episodes/."""
    try:
        return importlib.import_module(name)
    except ImportError as error:
        raise SystemExit(f"no reel module {name!r} under episodes/: {error}") from error


def frames_of(start: float, end: float, count: int) -> tuple[int, int]:
    """The first and last frame a shot from ``start`` to ``end`` seconds shows, of the ``count`` the performance has:
    those whose time falls inside it."""
    fps = lounge.PUSH_FPS
    return math.ceil(start * fps - 1e-9), min(math.ceil(end * fps - 1e-9) - 1, count - 1)


def lens_of(room: study.Room, take: str, frame: int | None = None) -> cr.Camera:
    """The camera of ``take``; with ``frame``, the push's camera on that frame (it holds its last one)."""
    if frame is None:
        row = room.takes[take]
        return cr.camera_of(row["eye"], row["look_at"], row["lens"])
    eye = room.pushed()["eye"][min(frame, lounge.PUSH_FRAMES - 1)]
    ahead = np.array(eye) - np.array(lounge.EYE)
    return cr.camera_of(eye, tuple(np.array(lounge.LOOK_AT) + ahead), lounge.LENS)


KNOWN_DIFFERENCES = (
    "Bruno's right side runs unseen into the sofa arm's volume, as his flat card does; the arm covers him and takes "
    "no shadow from him",
    "Mae sits further right along the cushion than her card, which the two-shot cuts at the frame's left edge: the "
    "clay sits whole inside it",
    "Bruno's right shoulder sits deeper than his left, so its upper arm stays under the sofa arm and the forearm comes "
    "out from under it as the flat's does; that arm shows shorter beside the cover than the flat's whole arm",
)
# the sofa arm over Bruno's right side, in his drawing's reference pixels: :func:`cover_edge` on the two-shot puts the
# stand-in's edge at 286.4 over the rows his upper arm runs down; the tuck keeps 1.4 pixels inside it, which sets his
# right shoulder back from -27.5 to -20.5
TUCKS = {"bruno": cf.Tuck("right", 285.0)}


def figure_of(who: str) -> cf.Figure:
    """``who`` as clay on this sofa: Bruno's right arm tucked under the sofa's arm."""
    return cf.figure(RIGS[who], TUCKS.get(who))


def cover_edge(seat: cr.Seat, lens: cr.Camera, fig: cf.Figure) -> float:
    """The innermost x (reference pixels) on ``fig``'s skin front, seated at ``seat`` and seen through ``lens``, that
    the sofa arm's stand-in covers, over the rows the resting right upper arm runs down from the shoulder to the
    elbow. A row the stand-in does not reach raises: the tuck would not hold there."""
    if seat.mirror:
        raise cr.RenderError("the cover's edge is read on an unmirrored figure only")
    chain = next(c for c in fig.arms if c.side == "right")
    joints = cf.reach(chain, chain.rest)
    cover = cr.arm_cover(lens)
    depth = cf.front_of(fig.skin)
    xs = np.arange(fig.extent[0], fig.extent[1] + 40.0, 0.5)
    edges = []
    for y in np.linspace(joints.shoulder[1], joints.elbow[1], 9):
        points = np.stack((xs, np.full_like(xs, y), depth(xs, np.full_like(xs, y))), 1)
        seen = cr.project(np.array(seat.at) + seat.per * (points - (cr.SEAT_X, cf.BASE, 0.0)), lens)
        under = contains_xy(cover, seen[:, 0], seen[:, 1])
        if not under.any():
            raise cr.RenderError(f"the sofa arm does not reach row {y:.0f} of the upper arm")
        edges.append(float(xs[under].min()))
    return min(edges)


GAP = 0.006  # metres the clay keeps from the other figure: touching, not passing through
FRAME_MARGIN = 16.0  # frame pixels the two-shot keeps clear between each figure's silhouette and the frame's side


def _across(meshes, lens: cr.Camera) -> tuple[float, float]:
    """The leftmost and the rightmost frame x of ``meshes`` through ``lens``: their silhouette's sides."""
    x = cr.project(np.concatenate([m.vertices for m in meshes]), lens)[:, 0]
    return float(x.min()), float(x.max())


def framed(parts, lens: cr.Camera, frame: int) -> None:
    """Refuse a two-shot ``frame`` on which a figure's silhouette, with half the room's line round it, crosses the
    frame's side."""
    edge = ci.ROOM_LINE.heavy / 2.0
    for who, posed_parts in parts.items():
        lo, hi = _across([m for part in posed_parts for m in part.meshes], lens)
        if lo < edge or hi > cr.WIDTH - edge:
            raise cr.RenderError(f"frame {frame}: {who} crosses the two-shot's side ({lo:.1f} to {hi:.1f} px)")


def seats(room: study.Room, performance: pf.Performance) -> dict[str, cr.Seat]:
    """Where each figure sits, on the column of its card's seat on the two-shot and as tall as the card there. Mae
    sits back against the sofa; the drawing lays Bruno over her, so he sits as far forward as it takes for none of him
    to pass through her (at rest, on frame 0). Bruno's column runs into the sofa's arm as his card does; the drawn arm
    covers him as it covers the card. Her card's column puts her past the two-shot's left side, so Mae moves right
    along the cushion just as far as it takes for her silhouette to keep :data:`FRAME_MARGIN` from it."""
    two = lens_of(room, "two")
    per = toon.SCALE * reel.PAIR_SCALE
    back = cr.SOFA_BACK_FRONT - cr.BACK_CLEARANCE
    card = lounge.SEAT_MAE
    for _ in range(6):
        mae = cr.seat_of(figure_of("mae"), card, two, per, True, back)
        resting = cr.posed("mae", RIGS["mae"], figure_of("mae"), performance.at("mae", 0), mae)
        cut = FRAME_MARGIN - _across(resting, two)[0]
        if cut <= 0.25 and (card == lounge.SEAT_MAE or cut >= -0.25):
            break
        card = (card[0] + cut / cr.pixels_per_metre(card, two), card[1], card[2])
    else:
        raise cr.RenderError(f"Mae does not settle inside the two-shot: {cut:.2f} px past its margin")
    bruno_back = back
    for _ in range(8):
        bruno = cr.seat_of(figure_of("bruno"), lounge.SEAT_BRUNO, two, per, False, bruno_back)
        his = cr.posed("bruno", RIGS["bruno"], figure_of("bruno"), performance.at("bruno", 0), bruno)
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
        parts[who] = cr.posed_parts(who, rig, figure_of(who), performance.at(who, frame), places[who])
        materials += cr.materials(who, rig, [mesh for part in parts[who] for mesh in part.meshes])
    return parts, tuple(materials)


def clay_root(root: Path) -> Path:
    return root / "clay"


def render(root: Path, push: bool, frames: range | list[int] | None = None) -> dict:
    """Every frame's four passes and its composite, plain and inked with the room's line, on every frame a camera on
    the room sees (the menu's are the reel's own drawing); and on every frame the hands each figure draws, counted by
    the anatomy rule (ADR 0174). Returns what the engine spent and, per frame, where its passes are and what was
    counted."""
    cf.use_palette(PALETTE.ink, PALETTE.white)
    room = study.Room.load(root / "plates" / "room.json")
    performance = pf.Performance.load(clay_root(root) / "performance.json")
    places = seats(room, performance)
    kind = "push" if push else "room"
    seen = range(PUSH_FRAMES) if push else performance.rendered()
    cache = clay_root(root) / "cache"
    spent = cr.Spent.new()
    index = {}
    for n in frames if frames is not None else seen:
        if push:
            still = min(n, lounge.PUSH_FRAMES - 1)
            lens = lens_of(room, "two", n)
            back, front = lounge.push_plate(still, "back"), lounge.push_plate(still, "front")
        else:
            take = performance.shot(n)
            if take == "menu":
                raise cr.RenderError(f"frame {n} is the menu's: no camera on the room sees it")
            lens, back, front = lens_of(room, take), lounge.plate(take, "back"), lounge.plate(take, "front")
        parts, materials = figures_at(performance, n, places)
        if not push and take == "two":
            framed(parts, lens, n)
        p, k, b, i = cr.passes(parts, materials, lens, cache, spent)
        picture, _ = cr.composite(cr.rgba(root / CLEAN / back), cr.rgba(p), cr.rgba(k), cr.rgba(b))
        paws = [cr.project(m.vertices, lens) for who in parts for part in parts[who] if part.hand for m in part.meshes]
        arm = cr.drawn_arm(cr.rgba(root / CLEAN / front), lens, cr.rgba(i), paws)
        cr.write(clay_root(root) / kind / f"{n:04d}.png", cr.over(picture, arm))
        inked = ci.ink(picture, cr.rgba(i), ci.ROOM_LINE)
        cr.write(clay_root(root) / f"{kind}-ink" / f"{n:04d}.png", cr.over(inked, arm))
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

    def __init__(self, room: study.Room, moving: bool, root: Path, ink: bool = False, count: int = 0):
        super().__init__(room, moving)
        self.root = root
        self.ink = ink
        self.count = count  # the frames the performance has

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
        first, last = frames_of(app.start, app.end, self.count)
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


class StandIns:
    """What :func:`stand_ins` took out of a reel module, to put back."""

    def __init__(self, module, saved: dict):
        self.module, self.saved = module, saved

    def restore(self) -> None:
        for name, value in self.saved.items():
            setattr(self.module, name, value)


def stand_ins(module, sets: ClaySets | None = None) -> StandIns:
    """The reel's modules stood in for by just what its staging calls of them: the cards out, the flat arms out, the
    flat remote out (the clay holds its own), and the TV's menu kept; with ``sets``, the room's plates and the clay's
    composites in place of its room and its sofa."""
    names = ("_room", "toon_world", "toon_pair", "toon_bed", "toon_everyday")
    saved = {name: getattr(module, name) for name in names if hasattr(module, name)}
    if sets is not None:
        module._room = sets.backdrop
        module.toon_world = SimpleNamespace(sofa=sets.sofa)
    module.toon_pair = SimpleNamespace(figure=_nothing, aim=toon_pair.aim)
    module.toon_bed = SimpleNamespace(swung_arm=_no_arm, ARM_WIDTH=toon_bed.ARM_WIDTH)
    if "toon_everyday" in saved:
        kept = {name: getattr(real_everyday, name) for name in dir(real_everyday) if not name.startswith("__")}
        module.toon_everyday = SimpleNamespace(**{**kept, "remote": _no_arm})
    return StandIns(module, saved)


def _count(root: Path) -> int:
    return pf.Performance.load(clay_root(root) / "performance.json").frames


def staging_of(root: Path, push: bool, ink: bool = False) -> tuple[Staging, str]:
    room = study.Room.load(root / "plates" / "room.json")
    sets = ClaySets(room, push, root, ink, _count(root))
    stand_ins(reel, sets)
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


def episode_staging(root: Path, sketch, **reel_staging) -> Staging:
    """The bound reel's own staging, ``sketch`` (one of its endings) drawn in clay: its cards and flat arms out, the
    room's plates and the clay composites under ``root``/clay/room in their place, no line round the clay.
    ``reel_staging`` is the rest of the reel's own :class:`Staging` (description, captions, overlay, versions...)."""
    room = study.Room.load(root / "plates" / "room.json")
    sets = ClaySets(room, False, root, False, _count(root))
    stand_ins(reel, sets)
    return Staging(sketch=sketch, dress=reel.dress, desk=toon_world.no_desk, bare=reel.BARE, **reel_staging)


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
    command, root, rest = argv[1], Path(argv[2]).resolve(), list(argv[3:])
    if "--reel" in rest:
        at = rest.index("--reel")
        if at + 1 >= len(rest) or command == "scene":
            raise SystemExit("--reel names a reel's data module, for perform and render")
        bind(reel_of(rest[at + 1]))
        del rest[at : at + 2]
    flags = set(rest)
    if flags - {"--push", "--ink"} or ("--ink" in flags and command != "scene"):
        raise SystemExit("the flags are --push, and --ink for a scene")
    clay_root(root).mkdir(exist_ok=True)
    if command == "perform":
        performance = pf.capture(root)
        performance.dump(clay_root(root) / "performance.json")
        pf.Performance.load(clay_root(root) / "performance.json")
    elif command == "render":
        render(root, "--push" in flags)
    else:
        print(scene(root, "--push" in flags, "--ink" in flags))


if __name__ == "__main__":
    main(sys.argv)
