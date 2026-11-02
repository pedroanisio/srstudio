"""Synthetic ``srstudio.pose-track/1.0.0`` records: a standing figure with a known bob, never a real person."""

from __future__ import annotations

import copy
import math

from srstudio import pose_track

DIGEST = "ab" * 32
MODEL = "cd" * 32

# A standing figure facing the camera, in the estimator's world axes (x image right, y down, z away; metres from the
# hips' centre). The dancer's left is on the image's right.
STAND = {
    "nose": (0.0, -0.62, -0.08),
    "left_ear": (0.07, -0.6, 0.0),
    "right_ear": (-0.07, -0.6, 0.0),
    "left_shoulder": (0.2, -0.5, 0.0),
    "right_shoulder": (-0.2, -0.5, 0.0),
    "left_elbow": (0.26, -0.22, 0.0),
    "right_elbow": (-0.26, -0.22, 0.0),
    "left_wrist": (0.3, 0.03, -0.02),
    "right_wrist": (-0.3, 0.03, -0.02),
    "left_hip": (0.09, 0.0, 0.0),
    "right_hip": (-0.09, 0.0, 0.0),
    "left_knee": (0.1, 0.42, -0.02),
    "right_knee": (-0.1, 0.42, -0.02),
    "left_ankle": (0.1, 0.85, 0.0),
    "right_ankle": (-0.1, 0.85, 0.0),
}


def landmark(name: str) -> tuple[float, float, float]:
    """Where a landmark stands at rest; landmarks the figure does not place sit on the nearest one it does."""
    if name in STAND:
        return STAND[name]
    for part in ("ankle", "wrist", "ear"):
        for side in ("left", "right"):
            if name.startswith(side) and (part == "ankle" and ("heel" in name or "foot" in name)):
                return STAND[f"{side}_ankle"]
            if name.startswith(side) and part == "wrist" and any(f in name for f in ("pinky", "index", "thumb")):
                return STAND[f"{side}_wrist"]
    return STAND["nose"]


def world(t: float, bob: float = 0.0, hz: float = 2.0) -> list[list[float]]:
    """The figure at second ``t``, its upper body dropping by ``bob`` metres ``hz`` times a second."""
    drop = bob * 0.5 * (1 - math.cos(2 * math.pi * hz * t))
    out = []
    for name in pose_track.LANDMARKS:
        x, y, z = landmark(name)
        if not any(part in name for part in ("ankle", "heel", "foot")):
            y += drop
        out.append([round(x, 5), round(y, 5), round(z, 5)])
    return out


def image(rows: list[list[float]], seen: float = 0.95) -> list[list[float]]:
    return [[round(0.5 + x / 2.5, 5), round(0.45 + y / 2.5, 5), round(z, 5), seen, seen] for x, y, z in rows]


def record(
    frames: int = 40,
    fps: float = 30.0,
    *,
    lost: tuple[int, ...] = (),
    bob: float = 0.0,
    hz: float = 2.0,
    repeat: tuple[int, ...] | None = None,
):
    """A record of ``frames`` frames from frame 0, the dancer lost in ``lost``. With ``repeat`` it is a ``1.1.0``
    record whose frames in ``repeat`` repeat the last distinct picture; without, a ``1.0.0`` one."""
    out = []
    for i in range(frames):
        t = i / fps
        if repeat is not None and i in repeat:
            out.append({k: None for k in pose_track.FRAME_KEYS} | {"index": i, "t_s": round(t, 6), "repeat": True})
            continue
        if i in lost:
            out.append({k: None for k in pose_track.FRAME_KEYS} | {"index": i, "t_s": round(t, 6)})
            continue
        rows = world(t, bob, hz)
        out.append(
            {
                "index": i,
                "t_s": round(t, 6),
                "image": image(rows),
                "world": rows,
                "box": [0.3, 0.1, 0.7, 0.9],
                "position": 0.01,
                "appearance": 0.1,
            }
        )
    if repeat is not None:
        for frame in out:
            frame.setdefault("repeat", False)
    first = next((i for i in range(frames) if i not in lost and i not in (repeat or ())), None)
    return {
        "schema": "srstudio.pose-track/1.0.0" if repeat is None else "srstudio.pose-track/1.1.0",
        "tool": "tests/support/pose_records.py",
        "estimator": {
            "name": "synthetic",
            "version": "1.0.0",
            "model": "none",
            "model_sha256": MODEL,
            "licence": "Apache-2.0",
        },
        "source": {"sha256": DIGEST, "bytes": 1000, "width": 760, "height": 776, "fps": fps, "frames": frames},
        "subject": {"pick": "central", "point": None, "first_frame": first},
        "axes": dict(pose_track.AXES),
        "landmarks": list(pose_track.LANDMARKS),
        "start_frame": 0,
        "frames": out,
    }


def edited(data: dict, path: str, value: object) -> dict:
    """A deep copy of ``data`` with the value at a dotted ``path`` (list indices as numbers) replaced; ``...`` as the
    value deletes the key."""
    out = copy.deepcopy(data)
    keys: list[str | int] = [int(k) if k.isdigit() else k for k in path.split(".")]
    here = out
    for key in keys[:-1]:
        here = here[key]
    if value is ...:
        del here[keys[-1]]
    else:
        here[keys[-1]] = value
    return out
