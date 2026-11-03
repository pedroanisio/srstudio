#!/usr/bin/env python3
"""The sofa-room study against the approved 2D: three side-by-side clips, paired stills at full size, and the measures.

    python room_compare.py MASTER PROJECT OUT       # MASTER the delivered reel; PROJECT holds study/sofa-room.mp4,
                                                    # study/sofa-push.mp4, study/sofa-control.mp4, plates/, and the
                                                    # measuring frames cast-room/, cast-push/, marks/; OUT is private

The two-shot and the close-ups are the approved master left, the room right. The push is the approved set under a 2D
camera.push_in left, the camera moving through the room right, on the same frames and the same curve. The sound is the
master's own, cut to the same frames. Every measure runs over every frame of its span, for each rig on its own side of
the line halfway between the two seats: the base check against the front plate of that frame's camera, the rows of the
figure the seat's front edge covers, and on the push the rig drift as the distance between each dot on the seat,
projected by the room, and the same dot carried on the group that carries the rigs. A rig whose base comes into view
gets its worst frame paired as a still, named for the span, the rig and the frame.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import _lounge_set as lounge
import numpy as np
from _base_check import clearance, exposed_columns
from compare import SEAT_TOP, alpha, frames
from PIL import Image
from sofa_room_study import Room, centroid

os.umask(0o077)  # generated outputs are private: folders 700, files 600

WIDTH, HEIGHT = lounge.WIDTH, lounge.HEIGHT
FPS = lounge.PUSH_FPS
FRAMES = 190  # the study's picture: the two-shot, then both close-ups, up to Mae's next shot
TAKES = {  # the camera of each span, and its first and last frame: the reel cuts at 4.6 s and 6.65 s
    "two": (0, 110),
    "mae": (111, 159),
    "bruno": (160, 189),
}
CLIPS = {"1-two-shot": (0, 111), "2-close-ups": (111, 190)}
STILLS = {"two-shot": 60, "close-up-mae": 130, "close-up-bruno": 170}
PUSH_STILLS = (0, 54, 109)


def side_by_side(left: Path, left_first: int, right: Path, right_first: int, count: int, sound: Path, sound_first: int,
                 out: Path) -> None:  # fmt: skip
    """`count` frames of two pictures side by side, the sound of `sound` cut to the same frames."""

    def cut(index: int, first: int) -> str:
        return f"[{index}:v]trim=start_frame={first}:end_frame={first + count},setpts=PTS-STARTPTS[{'ab'[index]}];"

    start, seconds = sound_first / FPS, count / FPS
    graph = (
        cut(0, left_first) + cut(1, right_first) + "[a][b]hstack=inputs=2[v];"
        f"[2:a]atrim=start={start:.5f}:duration={seconds:.5f},asetpts=PTS-STARTPTS[s]"
    )
    command = ["ffmpeg", "-v", "error", "-y", "-i", str(left), "-i", str(right), "-i", str(sound)]
    command += ["-filter_complex", graph, "-map", "[v]", "-map", "[s]", "-c:v", "libx264", "-crf", "14"]
    command += ["-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    subprocess.run([*command, str(out)], check=True)


def picked(path: Path, frame: int) -> Image.Image:
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1"]
        + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
    )
    return Image.frombytes("RGB", (WIDTH, HEIGHT), done.stdout)


def pair(left: Path, right: Path, frame: int, out: Path) -> None:
    both = Image.new("RGB", (WIDTH * 2, HEIGHT))
    both.paste(picked(left, frame), (0, 0))
    both.paste(picked(right, frame), (WIDTH, 0))
    both.save(out)


def take_of(frame: int) -> str:
    return next(name for name, (first, last) in TAKES.items() if first <= frame <= last)


def base_cover(masks: list[np.ndarray], fronts: list[np.ndarray]) -> dict:
    """Over every frame: columns of the rigs' base in view, and the least overlap of the near edge on it."""
    exposed = [exposed_columns(mask, front) for mask, front in zip(masks, fronts, strict=True)]
    cover = [clearance(mask, front) for mask, front in zip(masks, fronts, strict=True)]
    return dict(
        frames=len(masks),
        base_columns_exposed=sum(exposed),
        frames_with_a_column_exposed=int(np.count_nonzero(exposed)),
        least_rows_of_cover=min(cover),
        frame_of_least_cover=int(np.argmin(cover)),
    )


def sides(mask: np.ndarray, split: float) -> dict[str, np.ndarray]:
    """The mask cut at column `split`: Mae sits left of it, Bruno right, on every camera of the room."""
    column = int(round(min(max(split, 0), mask.shape[1])))
    left, right = mask.copy(), mask.copy()
    left[:, column:] = 0
    right[:, :column] = 0
    return dict(mae=left, bruno=right)


def split_of(seats: dict) -> float:
    return (seats["mae"][0] + seats["bruno"][0]) / 2


def per_rig(masks: list[np.ndarray], fronts: list[np.ndarray], splits: list[float]) -> dict:
    cut = [sides(mask, split) for mask, split in zip(masks, splits, strict=True)]
    return {name: base_cover([c[name] for c in cut], fronts) for name in lounge.TRACK_COLOURS}


def covered_rows(mask: np.ndarray, front: np.ndarray, x: float, half: float) -> float:
    """Rows of the figure under the front plate, the median over the columns `half` either side of `x`."""
    figure, near = mask >= 128, front >= 128
    columns = slice(max(int(x - half), 0), min(int(x + half), mask.shape[1]))
    return float(np.median((figure[:, columns] & near[:, columns]).sum(axis=0)))


def seat_cover(masks: list[np.ndarray], fronts: list[np.ndarray], spots: list[dict], scales: list[float]) -> dict:
    """How many rows of each figure the seat's front edge covers, frame by frame, in pixels and in the figure's own
    units (pixels over the frame's scale): if the camera's nearing made the edge climb the figure, both would grow."""
    result: dict = {}
    for name in lounge.TRACK_COLOURS:
        rows = [
            covered_rows(mask, front, spot[name][0], 30 * scale)
            for mask, front, spot, scale in zip(masks, fronts, spots, scales, strict=True)
        ]
        units = [round(row / scale, 2) for row, scale in zip(rows, scales, strict=True)]
        result[name] = dict(
            pixels=dict(first=rows[0], last=rows[-1], least=min(rows), most=max(rows)),
            figure_units=dict(first=units[0], last=units[-1], least=min(units), most=max(units)),
            pixels_by_frame=rows,
        )
    return result


def rig_difference(left: np.ndarray, right: np.ndarray, cast: Path, indices: list[int], shift: int = 0) -> float:
    """Mean difference per channel over the rigs' inner pixels above the seat, `shift` frames apart."""
    total, seen = 0.0, 0
    for row, index in enumerate(indices):
        mask = alpha(cast / f"{index:04d}.png") == 255
        mask[SEAT_TOP:] = False
        inner = np.zeros_like(mask)
        inner[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
        total += np.abs(left[row][inner].astype(float) - right[row + shift][inner].astype(float)).sum()
        seen += int(inner.sum()) * 3
    return round(total / seen, 3)


def drift(track: Path, marks: Path) -> dict:
    """Pixels between where the room puts each dot and where the rigs' group carries it, on every frame of the push."""
    result: dict = {}
    for name, colour in lounge.TRACK_COLOURS.items():
        apart = []
        for frame in range(lounge.PUSH_FRAMES):
            x0, y0 = centroid(track / f"{frame:04d}.png", colour)
            x1, y1 = centroid(marks / f"{frame:04d}.png", colour)
            apart.append(float(np.hypot(x1 - x0, y1 - y0)))
        result[name] = dict(
            mean_px=round(float(np.mean(apart)), 3),
            max_px=round(max(apart), 3),
            worst_frame=int(np.argmax(apart)),
            first_frame_px=round(apart[0], 3),
        )
    return result


def stepping(room: Room) -> dict:
    """How far the room moves between frames, in pixels, from its projection: this fixes how many plates it needs."""
    rows = room.pushed()
    rig = np.array(rows["rig"])
    code = np.array([row["code"] for row in rows["spots"]])
    cactus = np.array([row["cactus"] for row in rows["spots"]])

    def step(points: np.ndarray) -> float:
        return round(float(np.hypot(*np.diff(points[:, :2], axis=0).T).max()), 3)

    def last(points: np.ndarray) -> float:
        return round(float(points[-1, 2] / points[0, 2]), 4)

    return dict(
        peak_px_per_frame=dict(rig_place=step(rig), cactus=step(cactus), code_on_the_floor=step(code)),
        magnification_at_the_end=dict(rig_plane=last(rig), cactus=last(cactus), code_on_the_floor=last(code)),
        magnification_2d=round(lounge.magnification(lounge.PUSH_FRAMES - 1), 4),
    )


def main(argv: list[str]) -> None:
    master, project, out = (Path(a).resolve() for a in argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    plates, study = project / "plates", project / "study"
    room_clip, push_clip, control_clip = (study / f"sofa-{n}.mp4" for n in ("room", "push", "control"))
    room = Room.load(plates / "room.json")

    for name, (first, end) in CLIPS.items():
        side_by_side(master, first, room_clip, first, end - first, master, first, out / f"{name}.mp4")
    side_by_side(control_clip, 0, push_clip, 0, lounge.PUSH_FRAMES, master, 0, out / "3-push-in.mp4")
    for name, frame in STILLS.items():
        pair(master, room_clip, frame, out / f"pair-{name}-frame-{frame:03d}.png")
    for frame in PUSH_STILLS:
        pair(control_clip, push_clip, frame, out / f"pair-push-frame-{frame:03d}.png")

    fronts = {take: alpha(plates / lounge.plate(take, "front")) for take in TAKES}
    masks = [alpha(project / "cast-room" / f"{frame:04d}.png") for frame in range(FRAMES)]
    static, static_cover = {}, {}
    for take, (first, last) in TAKES.items():
        count, seats = last + 1 - first, room.takes[take]["rigs"]
        static[take] = per_rig(masks[first : last + 1], [fronts[take]] * count, [split_of(seats)] * count)
        spot = {name: seat[:2] for name, seat in seats.items()}
        scale = seats["mae"][2] / room.takes["two"]["rigs"]["mae"][2]
        cover = seat_cover(masks[first : last + 1], [fronts[take]] * count, [spot] * count, [scale] * count)
        static_cover[take] = {name: dict(pixels=row["pixels"], scale=round(scale, 4)) for name, row in cover.items()}
    push_masks = [alpha(project / "cast-push" / f"{frame:04d}.png") for frame in range(lounge.PUSH_FRAMES)]
    push_fronts = [alpha(plates / lounge.push_plate(frame, "front")) for frame in range(lounge.PUSH_FRAMES)]
    rows = room.pushed()["rig"]
    push_spots = [
        {
            name: centroid(plates / "push" / "track" / f"{frame:04d}.png", colour)
            for name, colour in lounge.TRACK_COLOURS.items()
        }
        for frame in range(lounge.PUSH_FRAMES)
    ]
    push_scales = [row[2] / rows[0][2] for row in rows]

    left, right = frames(master, FRAMES + 1), frames(room_clip, FRAMES + 1)
    sync = {}
    for take, (first, last) in TAKES.items():
        indices = list(range(first, min(last, FRAMES - 2) + 1))
        sync[take] = dict(
            same_frame=rig_difference(left[first:], right[first:], project / "cast-room", indices),
            one_frame_apart=rig_difference(left[first:], right[first:], project / "cast-room", indices, 1),
        )
    measures = dict(
        spans=dict(room_frames=FRAMES, push_frames=lounge.PUSH_FRAMES, fps=FPS, push_seconds=lounge.PUSH_FRAMES / FPS),
        base_cover=dict(**static, push=per_rig(push_masks, push_fronts, [row[0] for row in rows])),
        seat_front_cover=dict(**static_cover, push=seat_cover(push_masks, push_fronts, push_spots, push_scales)),
        rig_difference=sync,
        rig_drift_on_the_push=drift(plates / "push" / "track", project / "marks"),
        room_motion=stepping(room),
        plate_seconds=dict(stills=room.seconds, push=room.pushed()["seconds"]),
        engine_sha256=room.engine_sha256,
        srlocations_commit=room.srlocations_commit,
    )
    for span, rigs in measures["base_cover"].items():  # a base in view is shown, not hidden: its worst frame, paired
        for name, cover in rigs.items():
            if cover["base_columns_exposed"]:
                frame = cover["frame_of_least_cover"] + (0 if span == "push" else TAKES[span][0])
                left, right = (control_clip, push_clip) if span == "push" else (master, room_clip)
                pair(left, right, frame, out / f"pair-base-in-view-{span}-{name}-frame-{frame:03d}.png")
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")
    print(json.dumps(measures))


if __name__ == "__main__":
    main(sys.argv)
