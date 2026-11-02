#!/usr/bin/env python3
"""The clay look study against the flat cards: three side-by-side clips, paired stills at full size, and the measures.

    python clay_compare.py MASTER PROJECT OUT       # MASTER the delivered reel (its sound); PROJECT the study's project
                                                    # (study/sofa-room.mp4, sofa-push.mp4, clay-room.mp4,
                                                    # clay-push.mp4, plates/, cast-room/, cast-push/, marks/, clay/);
                                                    # OUT is private

Every clip is the flat cards in the room left (examples/paintover_proof/sofa_room_study.py) and the clay right, on the
same frames, with the master's sound cut to them. The measures run over every frame of each span, for each figure:

- base cover: on the card side the columns of a card's base in view past the seat's front edge (room_compare's
  check); on the clay side whether any of the base's underside turns to the camera, and how far the base leaves the
  cushion (the reel's gasp and jump lift the figure).
- seat contact: the clay's lowest point against the cushion's top, and the shadow it lays on the sofa, darkest and how
  much of the frame it darkens past the renderer's noise, on each figure's side.
- drift on the push: on the card side the dots the rigs' group carries against the room's own (room_compare's); on
  the clay side the room's seat points through the clay's camera against the same dots of the room.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "paintover_proof")]

import _lounge_set as lounge  # noqa: E402
import clay_figure as cf  # noqa: E402
import clay_room as cr  # noqa: E402
import clay_sofa_study as cs  # noqa: E402
import numpy as np  # noqa: E402
import performance as pf  # noqa: E402
import room_compare as rc  # noqa: E402
from compare import alpha  # noqa: E402
from sofa_room_study import Room, centroid  # noqa: E402

os.umask(0o077)  # generated outputs are private: folders 700, files 600

CLIPS = {"1-two-shot": (0, 111), "2-close-ups": (111, cs.ROOM_FRAMES)}
STILLS = {"two-shot": 60, "close-up-mae": 130, "close-up-bruno": 170}
PUSH_STILLS = (0, 54, 109)
BASE_LEVEL = 0.05  # engine centimetres: a base vertex lies this close to the figure's lowest point
FLAT_TAKES = {"two": (0, 110), "mae": (111, 159), "bruno": (160, 190)}


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
    count = cs.PUSH_FRAMES if push else cs.ROOM_FRAMES
    gaps: dict[str, list[float]] = {"mae": [], "bruno": []}
    facing: dict[str, int] = {"mae": 0, "bruno": 0}
    for n in range(count):
        lens = cs.lens_of(room, "two", n) if push else cs.lens_of(room, cs.take_of(n))
        eye = np.array(lens.position, float)
        for who in ("mae", "bruno"):
            rig = cs.RIGS[who]
            meshes = cr.posed(who, rig, cf.figure(rig), performance.at(who, n), places[who], cs.COATS[who])
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
    masks = [alpha(project / "cast-room" / f"{frame:04d}.png") for frame in range(cs.ROOM_FRAMES)]
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
    count = cs.PUSH_FRAMES if push else cs.ROOM_FRAMES
    out = []
    for n in range(count):
        lens = cs.lens_of(room, "two", n) if push else cs.lens_of(room, cs.take_of(n))
        xs = cr.project([places["mae"].at, places["bruno"].at], lens)[:, 0]
        out.append(float(xs.mean()))
    return out


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise SystemExit(__doc__)
    master, project, out = (Path(a).resolve() for a in argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    study = project / "study"
    flat_room, flat_push = study / "sofa-room.mp4", study / "sofa-push.mp4"
    clay_room, clay_push = study / "clay-room.mp4", study / "clay-push.mp4"
    room = Room.load(project / "plates" / "room.json")
    performance = pf.Performance.load(project / "clay" / "performance.json")
    places = cs.seats(room, performance)

    for name, (first, end) in CLIPS.items():
        rc.side_by_side(flat_room, first, clay_room, first, end - first, master, first, out / f"{name}.mp4")
    rc.side_by_side(flat_push, 0, clay_push, 0, cs.PUSH_FRAMES, master, 0, out / "3-push-in.mp4")
    for name, frame in STILLS.items():
        rc.pair(flat_room, clay_room, frame, out / f"pair-{name}-frame-{frame:03d}.png")
    for frame in PUSH_STILLS:
        rc.pair(flat_push, clay_push, frame, out / f"pair-push-frame-{frame:03d}.png")

    renders = {
        kind: json.loads((project / "clay" / f"render-{kind}-0-{count - 1}.json").read_text())
        for kind, count in (("room", cs.ROOM_FRAMES), ("push", cs.PUSH_FRAMES))
    }
    measures = dict(
        spans=dict(room_frames=cs.ROOM_FRAMES, push_frames=cs.PUSH_FRAMES, fps=pf.FPS, takes=cs.TAKES),
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
            figure_gap_m=round(
                cr.clearance(
                    cr.posed(
                        "bruno",
                        cs.RIGS["bruno"],
                        cf.figure(cs.RIGS["bruno"]),
                        performance.at("bruno", 0),
                        places["bruno"],
                        cs.COATS["bruno"],
                    ),  # fmt: skip
                    cr.posed(
                        "mae",
                        cs.RIGS["mae"],
                        cf.figure(cs.RIGS["mae"]),
                        performance.at("mae", 0),
                        places["mae"],
                        cs.COATS["mae"],
                    ),  # fmt: skip
                ),
                4,
            ),
            clay_shadow=dict(
                room=contact_shadow(project, renders["room"], splits_of(room, places, False)),
                push=contact_shadow(project, renders["push"], splits_of(room, places, True)),
            ),
        ),
        drift_on_the_push=dict(
            flat=rc.drift(project / "plates" / "push" / "track", project / "marks"),
            clay=clay_drift(room, project / "plates" / "push" / "track"),
        ),
        render_seconds=dict(
            clay={kind: record["spent"] for kind, record in renders.items()},
            plates=dict(stills=room.seconds, push=room.pushed()["seconds"]),
        ),  # fmt: skip
        engine_sha256=room.engine_sha256,
        srlocations_commit=room.srlocations_commit,
        generated_by=dict(model="claude-opus-5-5", tool="Claude Code"),
    )
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")
    print(json.dumps(measures)[:2000])


if __name__ == "__main__":
    main(sys.argv)
