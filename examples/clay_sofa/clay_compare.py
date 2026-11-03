#!/usr/bin/env python3
"""The clay look study against the flat cards: three side-by-side clips, paired stills at full size, and the measures.

    python clay_compare.py MASTER PROJECT OUT [ROUND1]  # MASTER the delivered reel (its sound); PROJECT the study's
                                                        # project (study/sofa-room.mp4, sofa-push.mp4, clay-room.mp4,
                                                        # clay-push.mp4 and their -ink twins, plates/, cast-room/,
                                                        # cast-push/, marks/, clay/); ROUND1 round 1's project, for the
                                                        # neck's seam against it; OUT is private

Every clip is the flat cards in the room left (examples/paintover_proof/sofa_room_study.py) and the clay right, on the
same frames, with the master's sound cut to them: under OUT/plain/ the clay as it renders, under OUT/ink/ with the
room's line round it. The measures run over every frame of each span, for each figure:

- base cover: on the card side the columns of a card's base in view past the seat's front edge (room_compare's
  check); on the clay side whether any of the base's underside turns to the camera, and how far the base leaves the
  cushion (the reel's gasp and jump lift the figure).
- seat contact: the clay's lowest point against the cushion's top, and the shadow it lays on the sofa, darkest and how
  much of the frame it darkens past the renderer's noise, on each figure's side.
- drift on the push: on the card side the dots the rigs' group carries against the room's own (room_compare's); on
  the clay side the room's seat points through the clay's camera against the same dots of the room.
- arm chains: each figure's two chains, their shoulders and bone lengths, and on every frame the most a bone strays
  from its length and how high each paw goes.
- hands: on every frame the hands each figure draws, as the anatomy rule (ADR 0174) counts them on the render.
- body lift: through the gasp and the jump, each frame's lift of the base off the cushion, and how far the figure's
  move strays from a turn and a shift (0 for no stretch and no shear).
- placement: each clay seat's column on the two-shot against its card's, and its base's depth against the cushion.
- rest arms: how long each arm shows from the front at rest against the flat's arm, its width at the wrist, whether
  the elbow stays inside the outline, and how much longer the clay's line runs laid over the belly than bare.
- chin fall: down each column beside the muzzle, the steepest the skin's front falls back (an undercut is a collar).
- neck seam: on the two-shot's frame 60, the darkest line across each figure's neck on its P pass (the luminance below
  the column's own smooth run), this round against round 1.
- known differences: what the study does not match in the flat, listed for the operator.
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "paintover_proof")]

import _lounge_set as lounge  # noqa: E402
import clay_figure as cf  # noqa: E402
import clay_ink as ci  # noqa: E402
import clay_room as cr  # noqa: E402
import clay_sofa_study as cs  # noqa: E402
import numpy as np  # noqa: E402
import performance as pf  # noqa: E402
import room_compare as rc  # noqa: E402
from compare import alpha  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402
from sofa_room_study import Room, centroid  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOM_FRAMES = 191  # the study's span of it-autoplayed: 0 to 7.917 s, the two-shot, her close-up and his
CLIPS = {"1-two-shot": (0, 111), "2-close-ups": (111, ROOM_FRAMES)}
STILLS = {"gasp": 4, "two-shot": 60, "jump": 92, "wow": 106, "close-up-mae": 130, "close-up-bruno": 170}
PUSH_STILLS = (0, 54, 109)
BASE_LEVEL = 0.05  # engine centimetres: a base vertex lies this close to the figure's lowest point
FLAT_TAKES = {"two": (0, 110), "mae": (111, 159), "bruno": (160, 190)}


def take_of(frame: int) -> str:
    """The camera of ``frame`` in the study's span."""
    return next(name for name, (first, last) in FLAT_TAKES.items() if first <= frame <= last)


def underside_facing(meshes, eye: np.ndarray) -> int:
    """How many vertices of a figure's flat base (at its lowest level, their normals straight down as cf.inflate sets
    them) face the camera at ``eye`` (engine centimetres). An outline's own normals point down at the bottom of an ear
    or a paw too; those are not the base."""
    lowest = max(float(mesh.vertices[:, 1].max()) for mesh in meshes)  # engine y points down
    count = 0
    for mesh in meshes:
        down = (mesh.normals[:, 1] > 0.999) & (mesh.vertices[:, 1] >= lowest - BASE_LEVEL)
        if down.any():
            towards = eye - mesh.vertices[down]
            count += int(((towards * mesh.normals[down]).sum(axis=1) > 0).sum())
    return count


def clay_base(performance: pf.Performance, places: dict, room: Room, push: bool) -> dict:
    """Over every frame: the base's gap above the cushion's top (metres, below 0 pressed in), frames off the cushion,
    and underside vertices turned to the camera."""
    count = cs.PUSH_FRAMES if push else ROOM_FRAMES
    gaps: dict[str, list[float]] = {"mae": [], "bruno": []}
    facing: dict[str, int] = {"mae": 0, "bruno": 0}
    for n in range(count):
        lens = cs.lens_of(room, "two", n) if push else cs.lens_of(room, take_of(n))
        eye = np.array(lens.position, float)
        for who in ("mae", "bruno"):
            rig = cs.RIGS[who]
            meshes = cr.posed(who, rig, cs.figure_of(who), performance.at(who, n), places[who])
            low = max(float(m.vertices[:, 1].max()) for m in meshes) / -100.0
            gaps[who].append(round(low - cr.CUSHION_TOP, 5))
            facing[who] += underside_facing(meshes, eye)
    out = {}
    for who, rows in gaps.items():
        off = [n for n, gap in enumerate(rows) if gap > 0.0]
        out[who] = dict(
            frames=count,
            frames_off_the_cushion=len(off),
            first_frame_off=off[0] if off else None,
            last_frame_off=off[-1] if off else None,
            highest_gap_m=max(rows),
            resting_gap_m=rows[0],
            underside_vertices_facing_the_camera=facing[who],
        )
    return out


def contact_shadow(project: Path, record: dict, splits: list[float]) -> dict:
    """The clay's shadow on the sofa, each frame from its own P, K and B passes, cut at ``splits`` (Mae left)."""
    cache = project / "clay" / "cache"
    rows: dict[str, list[tuple[float, int]]] = {"mae": [], "bruno": []}
    for (_, entry), split in zip(sorted(record["frames"].items(), key=lambda kv: int(kv[0])), splits, strict=True):
        p, k, b = (cr.rgba(cache / kind / entry[kind]) for kind in ("P", "K", "B"))
        dark = cr.shadow(p, b, k)
        dark[cr.coverage(k) > 0.5] = 1.0  # the figures themselves are no shadow
        column = int(round(min(max(split, 0), dark.shape[1])))
        for who, part in (("mae", dark[:, :column]), ("bruno", dark[:, column:])):
            rows[who].append((float(part.min()) if part.size else 1.0, int((part < 0.9).sum())))
    return {
        who: dict(
            darkest_ratio=round(min(r[0] for r in got), 3),
            median_darkest_ratio=round(float(np.median([r[0] for r in got])), 3),
            median_px_below_0_9=int(np.median([r[1] for r in got])),
            frames_with_no_shadow=sum(1 for r in got if r[1] == 0),
        )
        for who, got in rows.items()
    }


def clay_drift(room: Room, track: Path) -> dict:
    """Pixels between the room's own dots on the seat (its track plates) and the same seat points through the clay's
    camera, on every frame of the push: how well the clay's camera matches the room's."""
    result = {}
    for name, colour in lounge.TRACK_COLOURS.items():
        apart = []
        for frame in range(lounge.PUSH_FRAMES):
            x0, y0 = centroid(track / f"{frame:04d}.png", colour)
            x1, y1 = cr.project([cr.engine(lounge.TRACKS[name])], cs.lens_of(room, "two", frame))[0]
            apart.append(float(np.hypot(x1 - (x0 + 0.5), y1 - (y0 + 0.5))))  # a pixel's index to its middle
        result[name] = dict(
            mean_px=round(float(np.mean(apart)), 3), max_px=round(max(apart), 3), worst_frame=int(np.argmax(apart))
        )
    return result


def flat_base(project: Path, room: Room) -> dict:
    """The cards' base check, as room_compare runs it, on the card side's own measuring renders."""
    plates = project / "plates"
    fronts = {take: alpha(plates / lounge.plate(take, "front")) for take in FLAT_TAKES}
    masks = [alpha(project / "cast-room" / f"{frame:04d}.png") for frame in range(ROOM_FRAMES)]
    out = {}
    for take, (first, last) in FLAT_TAKES.items():
        count, seats = last + 1 - first, room.takes[take]["rigs"]
        out[take] = rc.per_rig(masks[first : last + 1], [fronts[take]] * count, [rc.split_of(seats)] * count)
    push_masks = [alpha(project / "cast-push" / f"{frame:04d}.png") for frame in range(lounge.PUSH_FRAMES)]
    push_fronts = [alpha(plates / lounge.push_plate(frame, "front")) for frame in range(lounge.PUSH_FRAMES)]
    out["push"] = rc.per_rig(push_masks, push_fronts, [row[0] for row in room.pushed()["rig"]])
    return out


def splits_of(room: Room, places: dict, push: bool) -> list[float]:
    """Each frame's column halfway between the two clay figures' seats."""
    count = cs.PUSH_FRAMES if push else ROOM_FRAMES
    out = []
    for n in range(count):
        lens = cs.lens_of(room, "two", n) if push else cs.lens_of(room, take_of(n))
        xs = cr.project([places["mae"].at, places["bruno"].at], lens)[:, 0]
        out.append(float(xs.mean()))
    return out


def arm_chains(performance: pf.Performance) -> dict:
    """Each figure's chains, and over every frame the most any bone strays from its length and each paw's highest."""
    out = {}
    for who in ("mae", "bruno"):
        rig = cs.RIGS[who]
        fig = cs.figure_of(who)
        stray, highest = 0.0, {chain.side: np.inf for chain in fig.arms}
        for n in range(ROOM_FRAMES):
            targets = cr.arm_targets(fig, performance.at(who, n))
            for chain in fig.arms:
                joints = cf.reach(chain, targets[chain.side])
                bones = (np.linalg.norm(joints.elbow - joints.shoulder), np.linalg.norm(joints.wrist - joints.elbow))
                stray = max(stray, abs(bones[0] - chain.upper), abs(bones[1] - chain.fore))
                highest[chain.side] = min(highest[chain.side], float(joints.paw[1]))
        out[who] = dict(
            chains=[
                dict(
                    side=c.side,
                    shoulder_ref_px=[round(float(v), 2) for v in c.shoulder],
                    upper_ref_px=c.upper,
                    fore_ref_px=c.fore,
                    rest_paw_ref_px=[round(float(v), 2) for v in c.rest],
                )
                for c in fig.arms
            ],  # fmt: skip
            most_bone_stray_ref_px=round(stray, 6),
            highest_paw_y_ref_px={side: round(y, 2) for side, y in highest.items()},
            neck_y_ref_px=rig.neck[1],
        )
    return out


def rest_arms() -> dict:
    """Each figure's arms at rest against the flat's: how long each shows from the front (from where it leaves the
    body to the wrist) in how many pieces, and the flat's own arm; the width at the elbow against the flat's and the
    wrist's over the elbow's (the forearm narrows); the paw seen from the front against the flat paw's box; how many
    degrees below level the forearm runs from the elbow to the wrist; whether the elbow stays inside the outline; and
    how much longer the clay's line is laid over the belly than the bones run (the bones keep their length; only the
    roll over them bends)."""
    out = {}
    for who in ("mae", "bruno"):
        rig = cs.RIGS[who]
        fig = cs.figure_of(who)
        flat = cf.flat_rest_arms(rig)
        boxes = cf._paws(rig)
        outline = Polygon(fig.parts.body).buffer(0).union(Polygon(fig.parts.head).buffer(0))
        sides = {}
        for chain in fig.arms:
            joints = cf.reach(chain, chain.rest)
            laid, radii = cf.arm_line(chain, joints)
            bare, _ = cf.arm_line(replace(chain, lap=None, skin=None), joints)
            made = cf.arm_meshes(chain, joints, f"{who}-arm", f"{who}-pad")
            paw = made["paw"][0].vertices
            (x0, y0), (x1, y1) = boxes[chain.side][0]
            run = joints.wrist - joints.elbow
            sides[chain.side] = dict(
                shown_ref_px=round(cf.arm_shown(fig, chain, joints), 2),
                shown_pieces=len(cf.arm_pieces(fig, chain, joints)),
                flat_ref_px=round(flat[chain.side].length, 2),
                elbow_width_ref_px=round(2.0 * float(radii[cf.ELBOW_AT]), 2),
                flat_width_ref_px=flat[chain.side].width,
                wrist_over_elbow=round(float(radii[-1] / radii[cf.ELBOW_AT]), 3),
                paw_ref_px=[round(float(np.ptp(paw[:, 0])), 2), round(float(np.ptp(paw[:, 1])), 2)],
                flat_paw_ref_px=[round(x1 - x0, 2), round(y1 - y0, 2)],
                paw_depth_over_height=round(float(np.ptp(paw[:, 2]) / np.ptp(paw[:, 1])), 3),
                toe_marks=len(cf.toe_columns(chain)),
                forearm_fall_degrees=round(math.degrees(math.atan2(run[1], abs(run[0]))), 1),
                elbow_inside=bool(outline.buffer(-chain.radii[0]).contains(Point(joints.elbow[0], joints.elbow[1]))),
                laid_over_bare=round(_length(laid) / _length(bare), 4),
            )
        out[who] = sides
    return out


def _length(path: np.ndarray) -> float:
    return float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())


def chin_fall() -> dict:
    """Down each column beside the muzzle, from above the chin to the base, the steepest the skin's front falls back
    per reference pixel (an undercut under the chin reads as a collar; the tests hold it above -0.5)."""
    out = {}
    for who in ("mae", "bruno"):
        fig = cs.figure_of(who)
        depth = cf.front_of(fig.skin)
        head = Polygon(fig.parts.head)
        ys = np.arange(head.bounds[3] - 80.0, cf.BASE - 10.0, 2.0)
        out[who] = {
            f"{dx:+.0f}": round(float((np.diff(-depth(np.full_like(ys, head.centroid.x + dx), ys)) / 2.0).min()), 3)
            for dx in (-90.0, -70.0, 70.0, 90.0)
        }
    return out


def placement(room: Room, performance: pf.Performance, places: dict) -> dict:
    """Each clay seat's column on the two-shot against its card's seat, and its base's depth on frame 0 against the
    cushion's front and rounded edge (metres; a base behind the edge rests on the flat of the cushion)."""
    two = cs.lens_of(room, "two")
    out = {}
    for who, card in (("mae", lounge.SEAT_MAE), ("bruno", lounge.SEAT_BRUNO)):
        posed = cr.posed(who, cs.RIGS[who], cs.figure_of(who), performance.at(who, 0), places[who])
        v = np.concatenate([m.vertices for m in posed]) / 100.0
        base = v[:, 1] > -(cr.CUSHION_TOP - cr.SINK) - 0.005  # engine y is down: the lowest half centimetre
        out[who] = dict(
            card_column_px=round(float(cr.project([cr.engine(card)], two)[0][0]), 2),
            clay_column_px=round(float(cr.project([places[who].at], two)[0][0]), 2),
            base_nearest_z_m=round(float(v[base, 2].min()), 4),
            cushion_front_z_m=cr.CUSHION_FRONT,
            cushion_edge_m=cr.CUSHION_EDGE,
        )
    return out


def hands(record: dict) -> dict:
    """The hands each figure draws on every frame, as the render counted them with the rule."""
    rows = sorted(record["frames"].items(), key=lambda kv: int(kv[0]))
    owners = sorted({owner for _, entry in rows for owner in entry["hands"]})
    return {
        owner: dict(
            per_frame=[entry["hands"][owner] for _, entry in rows],
            least=min(entry["hands"][owner] for _, entry in rows),
            most=max(entry["hands"][owner] for _, entry in rows),
        )
        for owner in owners
    }


def body_lift(performance: pf.Performance, places: dict, spans: dict[str, tuple[str, int, int]]) -> dict:
    """Through each span (``name: (who, first, last)``): each frame's lift of the base off the cushion (metres) and
    the most the figure's move strays from a turn and a shift (``|M Mᵀ - I|``, 0 when nothing stretches or shears)."""
    out = {}
    for name, (who, first, last) in spans.items():
        rig, lifts, worst = cs.RIGS[who], [], 0.0
        for n in range(first, last + 1):
            frame = performance.at(who, n)
            meshes = cr.posed(who, rig, cs.figure_of(who), frame, places[who])
            low = max(float(m.vertices[:, 1].max()) for m in meshes) / -100.0
            lifts.append(round(low - cr.CUSHION_TOP + cr.SINK, 5))
            m = cr.figure_motion(frame, places[who].mirror)[:2, :2]
            worst = max(worst, float(np.abs(m @ m.T - np.eye(2)).max()))
        top = int(np.argmax(lifts))
        out[name] = dict(
            who=who, frames=[first, last], lift_m=lifts, highest_lift_m=lifts[top], highest_at_frame=first + top,
            back_on_the_cushion_at_frame=next((first + k for k in range(top, len(lifts)) if lifts[k] <= 1e-6), None),
            most_stretch_or_shear=round(worst, 12),
        )  # fmt: skip
    return out


SEAM_BAND = 40  # frame pixels above and below the neck's row searched for a line (round 1 sat a little elsewhere)


def _darkest_line(p: np.ndarray, k: np.ndarray, at: tuple[float, float], half: int) -> float:
    """The darkest horizontal line through ``at`` on a P pass: per column in a band round the neck, the luminance below
    its own 9-pixel median, the 5th percentile over the band's figure pixels (more negative is a darker line)."""
    from scipy import ndimage

    x, y = int(round(at[0])), int(round(at[1]))
    box = (slice(y - SEAM_BAND, y + SEAM_BAND), slice(x - half, x + half))
    lum = cr.luminance(p[..., :3])[box]
    seen = cr.coverage(k)[box] > 0.99
    smooth = ndimage.median_filter(lum, size=(9, 1))
    residual = (lum - smooth)[seen]
    return round(float(np.percentile(residual, 5)), 4) if residual.size else float("nan")


def neck_seam(project: Path, round1: Path | None, room: Room, places: dict, frame: int = 60) -> dict:
    """Each figure's darkest line across the neck on the two-shot's frame ``frame`` (both figures at rest there), this
    round and round 1, searched 60 reference pixels either side of the neck's middle."""
    lens = cs.lens_of(room, take_of(frame))
    found: dict[str, dict] = {}
    for label, root in (("round_2", project), ("round_1", round1)):
        if root is None:
            continue
        entry = json.loads((root / "clay" / "render-room-0-190.json").read_text())["frames"][str(frame)]
        p, k = (cr.rgba(root / "clay" / "cache" / kind / entry[kind]) for kind in ("P", "K"))
        for who in ("mae", "bruno"):
            rig, seat = cs.RIGS[who], places[who]
            local = np.array([[cr.SEAT_X, rig.neck[1], 0.0], [cr.SEAT_X + 60.0, rig.neck[1], 0.0]])
            world, _ = cr._place(local, None, np.eye(4), seat)
            at, side = cr.project(world, lens)
            half = int(round(float(np.hypot(*(side - at)))))
            found.setdefault(who, {})[label] = dict(
                neck_px=[round(float(v), 1) for v in at], darkest_line=_darkest_line(p, k, (at[0], at[1]), half)
            )
    return found


GASP_AND_JUMP = {"gasp": ("bruno", 0, 30), "jump": ("mae", 86, 104)}  # the gasp from 0 s to 1 s, the jump at 3.75 s
VARIANTS = {"plain": "", "ink": "-ink"}


def gpu_peak(samples: Path) -> dict:
    """The most GPU memory used while the passes rendered, from nvidia-smi's samples (``timestamp, MiB`` rows)."""
    if not samples.exists():
        return dict(measured=False, why=f"no samples at {samples.name}")
    used = [float(row.split(",")[1]) for row in samples.read_text().splitlines()[1:] if row.count(",") == 1]
    return dict(measured=bool(used), samples=len(used), peak_mib=max(used) if used else None)


def steps(table: Path) -> list[dict]:
    """The finishing steps' exits and wall seconds (scenes, strict encodes), as the driver timed them."""
    if not table.exists():
        return []
    rows = [line.split("\t") for line in table.read_text().splitlines()[1:] if line.strip()]
    return [dict(step=name, exit=int(code), seconds=float(seconds)) for name, code, seconds in rows]


def cost(renders: dict) -> dict:
    """Engine seconds per pass kind for each clip, and per plate (one pass of one frame) where any ran."""
    out = {}
    for kind, record in renders.items():
        spent = record["spent"]
        out[kind] = dict(
            seconds=spent["seconds"],
            runs=spent["runs"],
            cached=spent["cached"],
            seconds_per_plate={
                k: round(v / spent["runs"][k], 3) for k, v in spent["seconds"].items() if spent["runs"][k]
            },
        )
    return out


def main(argv: list[str]) -> None:
    if len(argv) not in (4, 5):
        raise SystemExit(__doc__)
    master, project, out = (Path(a).resolve() for a in argv[1:4])
    round1 = Path(argv[4]).resolve() if len(argv) == 5 else None
    out.mkdir(parents=True, exist_ok=True)
    study = project / "study"
    flat_room, flat_push = study / "sofa-room.mp4", study / "sofa-push.mp4"
    room = Room.load(project / "plates" / "room.json")
    performance = pf.Performance.load(project / "clay" / "performance.json")
    places = cs.seats(room, performance)

    for variant, suffix in VARIANTS.items():
        clay_room, clay_push = study / f"clay-room{suffix}.mp4", study / f"clay-push{suffix}.mp4"
        there = out / variant
        there.mkdir(exist_ok=True)
        for name, (first, end) in CLIPS.items():
            rc.side_by_side(flat_room, first, clay_room, first, end - first, master, first, there / f"{name}.mp4")
        rc.side_by_side(flat_push, 0, clay_push, 0, cs.PUSH_FRAMES, master, 0, there / "3-push-in.mp4")
        for name, frame in STILLS.items():
            rc.pair(flat_room, clay_room, frame, there / f"pair-{name}-frame-{frame:03d}.png")
        for frame in PUSH_STILLS:
            rc.pair(flat_push, clay_push, frame, there / f"pair-push-frame-{frame:03d}.png")

    renders = {
        kind: json.loads((project / "clay" / f"render-{kind}-0-{count - 1}.json").read_text())
        for kind, count in (("room", ROOM_FRAMES), ("push", cs.PUSH_FRAMES))
    }
    rest = {who: cr.posed(who, cs.RIGS[who], cs.figure_of(who), performance.at(who, 0), places[who])
            for who in ("mae", "bruno")}  # fmt: skip
    measures = dict(
        spans=dict(room_frames=ROOM_FRAMES, push_frames=cs.PUSH_FRAMES, fps=pf.FPS, takes=FLAT_TAKES),
        variants={variant: f"{variant}/" for variant in VARIANTS},
        base_cover=dict(
            flat=flat_base(project, room),
            clay=dict(
                room=clay_base(performance, places, room, False), push=clay_base(performance, places, room, True)
            ),
        ),
        seat_contact=dict(
            clay_seats={
                who: dict(
                    at_m=[round(v / 100.0 * (-1 if i == 1 else 1), 4) for i, v in enumerate(seat.at)],
                    metres_per_ref_px=round(seat.per / 100.0, 6),
                    mirrored=seat.mirror,
                )  # fmt: skip
                for who, seat in places.items()
            },
            sink_m=cr.SINK,
            figure_gap_m=round(cr.clearance(rest["bruno"], rest["mae"]), 4),
            clay_shadow=dict(
                room=contact_shadow(project, renders["room"], splits_of(room, places, False)),
                push=contact_shadow(project, renders["push"], splits_of(room, places, True)),
            ),
        ),
        drift_on_the_push=dict(
            flat=rc.drift(project / "plates" / "push" / "track", project / "marks"),
            clay=clay_drift(room, project / "plates" / "push" / "track"),
        ),
        placement=placement(room, performance, places),
        arm_chains=arm_chains(performance),
        rest_arms=rest_arms(),
        chin_fall_per_ref_px=chin_fall(),
        hands_per_figure=dict(room=hands(renders["room"]), push=hands(renders["push"])),
        body_lift=body_lift(performance, places, GASP_AND_JUMP),
        neck_seam=neck_seam(project, round1, room, places),
        known_differences=list(cs.KNOWN_DIFFERENCES),
        ink=dict(colour=ci.ROOM_LINE.colour, heavy_px=ci.ROOM_LINE.heavy, fine_px=ci.ROOM_LINE.fine),
        render_seconds=dict(
            clay=cost(renders), plates=dict(stills=room.seconds, push=room.pushed()["seconds"])
        ),  # fmt: skip
        gpu=gpu_peak(out / "gpu-samples.csv"),
        finishing_steps=steps(out / "steps.tsv"),
        engine_sha256=room.engine_sha256,
        srlocations_commit=room.srlocations_commit,
        generated_by=dict(model="claude-opus-5-5", tool="Claude Code"),
    )
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")
    print(json.dumps(measures)[:2000])


if __name__ == "__main__":
    main(sys.argv)
