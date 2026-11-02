#!/usr/bin/env python3
"""Follow one dancer through a video with a pose estimator and write the reading as one record srstudio reads
(ADR 0203).

The estimator is MediaPipe's Pose Landmarker (Apache-2.0, 33 BlazePose landmarks in the image and in metres). It runs
in its own interpreter, so srstudio gains no dependency; build it once, as docs/authoring-dance.md says:

    uv venv --python 3.12 $WS/generated/venvs/pose
    uv pip install --python $WS/generated/venvs/pose/bin/python mediapipe==1.2.0
    $WS/generated/venvs/pose/bin/python -I tools/pose_extract.py --fetch-models
    $WS/generated/venvs/pose/bin/python -I tools/pose_extract.py VIDEO --out TRACK

with TRACK under the workspace, such as ``$WS/generated/dance-study/NAME/pose-track.json``.

A class video holds several dancers and the camera moves. Every frame the estimator looks for up to five bodies in the
whole frame and for one in a crop around where the dancer is expected, at a higher resolution. The tracker keeps the
dancer by place (a jump measured in body sizes from where the dancer should be) and by the colours of their clothes
(the torso and the legs, compared with the dancer's own: the mean of the first ``SETTLE`` matches, then learned slowly
from close ones). When the clothes cannot be seen (a hip or knee
too faint), the body where the dancer should be is kept by place alone, for at most ``BLIND_RUN`` frames in a row and
only when no other body stands near it; the record says so with a null appearance. A frame where no body passes is
written as lost, never filled in. The first frame picks the dancer: the most central large body
(``--pick central``), or the body nearest a point (``--pick 0.4,0.5``, shares of the frame). A central pick assumes the
camera follows the dancer, so after a jump the dancer is found only near the middle of the frame: in a class, the
dancers beside the lead wear the same clothes often enough that colours alone do not tell them apart.

The record holds per-frame landmarks of a real person, so it is written only outside this repository, under the
workspace's ``generated/`` (directory 700, file 600), and never committed. It is checked with ``srstudio.pose_track``,
loaded by path, before it is written.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import sys
import tempfile
import types
import urllib.request
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
TOOL = "tools/pose_extract.py"
LICENCE = "Apache-2.0"
POSE_VENV = "generated/venvs/pose"  # under the workspace, beside the other generated outputs
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{0}/float16/1/pose_landmarker_{0}.task"
MODELS = {  # the pinned model files: version 1 of each, float16
    "heavy": "64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b",
    "full": "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1",
}
FULL_POSES = 5  # bodies looked for in the whole frame
CROP_POSES = 2  # in the crop: the dancer and a neighbour stepping in
CROP_SIDE = 1.5  # the crop's side, in body sizes
CROP_PIXELS = 640  # a crop smaller than this is enlarged to it
MIN_SEEN = 0.3  # a landmark below this visibility does not place the box or sample the clothes
BODY = 3.2  # a body is this many torso lengths tall, near enough to size a box
POSITION_LIMIT = 0.5  # body sizes a dancer can move between two frames at 30 fps, with a camera that follows
POSITION_GROWTH = 0.15  # the limit widens by this much for every frame the dancer is lost
POSITION_CAP = 2.0
JUMP = 0.25  # body sizes: a step longer than this is a jump, not the dancer moving on
CENTRAL_BAND = 0.2  # with --pick central the camera follows the dancer: a jump lands this near the middle
SHRINK = 0.8  # a jump never lands on a body smaller than this share of the dancer: the dancers behind are
SIZES = 15  # smaller; the dancer's size is the median of the last this many matches
APPEARANCE_LIMIT = 0.45  # Bhattacharyya distance of the clothes' colours
APPEARANCE_WEIGHT = 2.0
REACQUIRE_AFTER = 10  # frames lost before the dancer may be found anywhere, by clothes alone
REACQUIRE_LIMIT = 0.3
BLIND_LIMIT = 0.2  # body sizes: a body this near where the dancer should be is kept when its clothes cannot be seen
BLIND_RUN = 45  # frames kept by place alone in a row, at most, before the clothes must be seen again
CLEAR = 0.5  # body sizes: a body kept by place alone has no other body this near it
SAME = 0.15  # body sizes: two readings this near are one body, seen whole and in the crop
LEARN = 0.05  # how much a confident match updates the dancer's colours
SETTLE = 15  # the dancer's colours are the mean of their first matches with clothes seen, not one frame's
LEARN_LIMIT = 0.25
CROP_BONUS = 0.02  # a crop's landmarks are read at a higher resolution: prefer them on a tie
HUE_BINS, SAT_BINS, VAL_BINS = 12, 6, 6
IMAGE_DECIMALS, WORLD_DECIMALS, COST_DECIMALS = 5, 4, 4


class ExtractError(RuntimeError):
    """The video, the estimator, the model or the output cannot be used."""


def _location_export() -> types.ModuleType:
    """``tools/location_export.py``: its ``load_srstudio`` loads one stdlib-only srstudio module in any interpreter."""
    if "location_export" in sys.modules:
        return sys.modules["location_export"]
    found = importlib.util.spec_from_file_location("location_export", REPO / "tools" / "location_export.py")
    if found is None or found.loader is None:
        raise ExtractError(f"cannot load {REPO / 'tools' / 'location_export.py'}")
    module = importlib.util.module_from_spec(found)
    sys.modules[found.name] = module
    found.loader.exec_module(module)
    return module


pose_track = _location_export().load_srstudio("pose_track")
NAMES: tuple[str, ...] = pose_track.LANDMARKS
LANDMARK = {name: i for i, name in enumerate(NAMES)}
TORSO = ("left_shoulder", "right_shoulder", "right_hip", "left_hip")
LEGS = ("left_hip", "right_hip", "right_knee", "left_knee")


# --- one body, and the dancer among them ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One body the estimator found: ``image`` (33 x 5: x, y in pixels of the whole frame, depth, visibility,
    presence), ``world`` (33 x 3, metres from the hips), and whether it came from the ``crop``."""

    image: np.ndarray
    world: np.ndarray
    crop: bool = False

    def _mid(self, a: str, b: str) -> np.ndarray:
        return (self.image[LANDMARK[a], :2] + self.image[LANDMARK[b], :2]) / 2

    @property
    def centre(self) -> np.ndarray:
        """The middle of the torso, in pixels."""
        return (self._mid("left_shoulder", "right_shoulder") + self._mid("left_hip", "right_hip")) / 2

    @property
    def size(self) -> float:
        """The body's height in pixels, from its torso: arms and legs fly about, the torso does not."""
        torso = float(np.linalg.norm(self._mid("left_shoulder", "right_shoulder") - self._mid("left_hip", "right_hip")))
        return max(torso * BODY, 1.0)

    def box(self, width: int, height: int) -> tuple[float, float, float, float]:
        """The seen landmarks' extent, as shares of the frame."""
        seen = self.image[self.image[:, 3] >= MIN_SEEN]
        points = seen if len(seen) >= 2 else self.image
        x0, y0 = points[:, 0].min(), points[:, 1].min()
        x1, y1 = max(points[:, 0].max(), x0 + 1), max(points[:, 1].max(), y0 + 1)
        return (float(x0 / width), float(y0 / height), float(x1 / width), float(y1 / height))


@dataclass(frozen=True)
class Colours:
    """The colours of a body's torso and of its legs, each a normalised hue-saturation-value histogram, or None when
    that region is not seen."""

    torso: np.ndarray | None
    legs: np.ndarray | None

    @property
    def seen(self) -> bool:
        return self.torso is not None or self.legs is not None

    def blend(self, other: Colours, share: float) -> Colours:
        """These colours moved ``share`` of the way to ``other``, region by region where both are seen."""

        def mix(a: np.ndarray | None, b: np.ndarray | None) -> np.ndarray | None:
            if a is None or b is None:
                return a if b is None else (b if a is None else None)
            return ((1 - share) * a + share * b).astype(np.float32)

        return Colours(mix(self.torso, other.torso), mix(self.legs, other.legs))

    def fill(self, other: Colours) -> Colours:
        """These colours, with the regions they lack taken from ``other``."""
        return Colours(
            other.torso if self.torso is None else self.torso, other.legs if self.legs is None else self.legs
        )


def _histogram(hsv: np.ndarray, body: Candidate, region: tuple[str, ...]) -> np.ndarray | None:
    corners = body.image[[LANDMARK[n] for n in region]]
    if corners[:, 3].min() < MIN_SEEN:
        return None
    mask = np.zeros(hsv.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(corners[:, :2]).astype(np.int32)], 255)
    if int(mask.sum()) == 0:
        return None
    hist = cv2.calcHist([hsv], [0, 1, 2], mask, [HUE_BINS, SAT_BINS, VAL_BINS], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(hist, None, 1.0, 0.0, cv2.NORM_L1).flatten().astype(np.float32)


def signature(rgb: np.ndarray, body: Candidate) -> Colours:
    """The colours of the body's torso and legs, each where its four corners are seen."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    return Colours(_histogram(hsv, body, TORSO), _histogram(hsv, body, LEGS))


def distance(a: Colours, b: Colours) -> float | None:
    """How unlike two bodies' colours are, over the regions both show: 0 the same, 1 none in common; None when they
    show no region in common."""
    pairs = [(x, y) for x, y in ((a.torso, b.torso), (a.legs, b.legs)) if x is not None and y is not None]
    if not pairs:
        return None
    return float(np.mean([cv2.compareHist(x, y, cv2.HISTCMP_BHATTACHARYYA) for x, y in pairs]))


@dataclass(frozen=True)
class Match:
    """The dancer's body this frame: its index, the jump in body sizes, and the colours' distance (None when kept by
    place alone)."""

    index: int
    position: float
    appearance: float | None


class Tracker:
    """The dancer from frame to frame: where they are, how big, how fast they move in the picture, and their colours.
    Nothing here asks the estimator whether to go on: every bound is a constant above."""

    def __init__(self, width: int, height: int, pick: str = "central", point: tuple[float, float] | None = None):
        if pick not in ("central", "point") or (pick == "point") != (point is not None):
            raise ExtractError("pick is central, or point with a point")
        self.width, self.height, self.pick, self.point = width, height, pick, point
        self.centre: np.ndarray | None = None
        self.velocity = np.zeros(2)
        self.size = 0.0
        self.sizes: deque[float] = deque(maxlen=SIZES)
        self.colours: Colours | None = None
        self.lost = 0
        self.blind = 0
        self.settled = 0

    @property
    def started(self) -> bool:
        return self.centre is not None

    def predicted(self) -> np.ndarray:
        if self.centre is None:
            raise ExtractError("the tracker has not found the dancer yet")
        return self.centre + self.velocity * min(self.lost + 1, 3)

    def crop(self) -> tuple[int, int, int, int] | None:
        """Where to look closer next frame (x0, y0, x1, y1 in pixels), or None before the dancer is found."""
        if self.centre is None:
            return None
        cx, cy = self.predicted()
        half = self.size * CROP_SIDE / 2
        x0, y0 = int(max(0, cx - half)), int(max(0, cy - half))
        x1, y1 = int(min(self.width, cx + half)), int(min(self.height, cy + half))
        return (x0, y0, x1, y1) if x1 - x0 >= 32 and y1 - y0 >= 32 else None

    def _first(self, bodies: Sequence[Candidate]) -> int:
        frame = np.array([self.width, self.height], float)
        if self.point is not None:
            target = np.array(self.point) * frame
            return int(np.argmin([np.linalg.norm(b.centre - target) / b.size for b in bodies]))
        middle = frame / 2
        return int(np.argmax([b.size * (1 - abs(b.centre[0] - middle[0]) / middle[0]) for b in bodies]))

    def step(self, bodies: Sequence[Candidate], colours: Sequence[Colours]) -> Match | None:
        """The dancer among ``bodies`` this frame, or None (lost)."""
        if len(bodies) != len(colours):
            raise ExtractError("one signature for each body")
        if not bodies:
            self._miss()
            return None
        if self.centre is None:
            first = self._first(bodies)
            if not colours[first].seen:
                return None  # a dancer whose clothes cannot be seen yet cannot be followed
            self._take(bodies[first], colours[first], 0.0)
            return Match(first, 0.0, 0.0)
        assert self.colours is not None
        here = self.predicted()
        limit = min(POSITION_CAP, POSITION_LIMIT + POSITION_GROWTH * self.lost)
        best: tuple[float, Match] | None = None
        hidden = []
        for i, (body, seen) in enumerate(zip(bodies, colours, strict=True)):
            position = float(np.linalg.norm(body.centre - here)) / self.size
            appearance = distance(self.colours, seen)
            if appearance is None:
                hidden.append(i)
                continue
            if self.pick == "central" and position > JUMP and abs(body.centre[0] / self.width - 0.5) > CENTRAL_BAND:
                continue  # the camera follows the dancer, so a jump to the frame's side is a neighbour
            if position > JUMP and body.size < SHRINK * float(np.median(self.sizes)):
                continue  # a jump onto a smaller body is a dancer further back
            near = position <= limit and appearance <= APPEARANCE_LIMIT
            again = self.lost >= REACQUIRE_AFTER and appearance <= REACQUIRE_LIMIT and 0.6 < body.size / self.size < 1.6
            if not (near or again):
                continue
            cost = position + APPEARANCE_WEIGHT * appearance - (CROP_BONUS if body.crop else 0.0)
            if best is None or cost < best[0]:
                best = (cost, Match(i, position, appearance))
        if best is None:
            return self._blind(bodies, hidden, here)
        match = best[1]
        self._take(bodies[match.index], colours[match.index], match.appearance)
        return match

    def _blind(self, bodies: Sequence[Candidate], hidden: Sequence[int], here: np.ndarray) -> Match | None:
        """A body whose clothes cannot be compared, where the dancer should be, kept by place alone: only when it is
        near, no other body is, and the clothes were seen within the last ``BLIND_RUN`` frames. A body whose clothes
        were compared and refused is never kept."""
        if self.blind >= BLIND_RUN or not hidden:
            self._miss()
            return None
        place = [float(np.linalg.norm(b.centre - here)) / self.size for b in bodies]
        i = min(hidden, key=lambda j: place[j])
        others = [
            p
            for j, (p, b) in enumerate(zip(place, bodies, strict=True))
            if float(np.linalg.norm(b.centre - bodies[i].centre)) / self.size > SAME and j != i
        ]
        if place[i] > BLIND_LIMIT or any(p < CLEAR for p in others):
            self._miss()
            return None
        crop = [
            j
            for j in hidden
            if bodies[j].crop and float(np.linalg.norm(bodies[j].centre - bodies[i].centre)) / self.size <= SAME
        ]
        i = crop[0] if crop else i
        self._take(bodies[i], None, None)
        return Match(i, place[i], None)

    def _miss(self) -> None:
        if self.centre is not None:
            self.lost += 1
            self.velocity *= 0.5

    def _take(self, body: Candidate, colours: Colours | None, appearance: float | None) -> None:
        if self.centre is not None and self.lost == 0:
            self.velocity = 0.5 * self.velocity + 0.5 * (body.centre - self.centre)
        else:
            self.velocity = np.zeros(2)
        self.centre, self.size, self.lost = body.centre, body.size, 0
        self.sizes.append(body.size)
        if colours is None:
            self.blind += 1
            return
        self.blind = 0
        self.settled += 1
        if self.colours is None:
            self.colours = colours
        elif self.settled <= SETTLE:
            self.colours = self.colours.blend(colours, 1 / self.settled)
        elif appearance is not None and appearance <= LEARN_LIMIT:
            self.colours = self.colours.blend(colours, LEARN)
        else:
            self.colours = self.colours.fill(colours)


# --- the record ----------------------------------------------------------------------------------------------------


def frame_entry(index: int, fps: float, body: Candidate | None, match: Match | None, width: int, height: int) -> dict:
    """One frame of the record; a lost frame carries its clock and nothing else."""
    entry: dict = {"index": index, "t_s": round(index / fps, 6)}
    if body is None or match is None:
        return entry | {"image": None, "world": None, "box": None, "position": None, "appearance": None}
    image = [
        [
            round(float(x) / width, IMAGE_DECIMALS),
            round(float(y) / height, IMAGE_DECIMALS),
            round(float(z), IMAGE_DECIMALS),
            round(float(np.clip(v, 0, 1)), 4),
            round(float(np.clip(p, 0, 1)), 4),
        ]
        for x, y, z, v, p in body.image
    ]
    world = [[round(float(v), WORLD_DECIMALS) for v in row] for row in body.world]
    box = [round(v, IMAGE_DECIMALS) for v in body.box(width, height)]
    return entry | {
        "image": image,
        "world": world,
        "box": box,
        "position": round(match.position, COST_DECIMALS),
        "appearance": None if match.appearance is None else round(min(1.0, match.appearance), COST_DECIMALS),
    }


def record(
    *, estimator: dict, source: dict, pick: str, point: tuple[float, float] | None, start_frame: int, frames: list[dict]
) -> dict:
    first = next((f["index"] for f in frames if f["world"] is not None), None)
    return {
        "schema": f"{pose_track.SCHEMA}/{pose_track.SCHEMA_VERSION}",
        "tool": TOOL,
        "estimator": estimator,
        "source": source,
        "subject": {"pick": pick, "point": list(point) if point else None, "first_frame": first},
        "axes": dict(pose_track.AXES),
        "landmarks": list(NAMES),
        "start_frame": start_frame,
        "frames": frames,
    }


def write(data: dict, out: Path) -> Path:
    """Check ``data`` with srstudio's reader and write it at ``out``, outside this repository, directory 700 and file
    600, atomically."""
    out = out.resolve()
    if out.is_relative_to(REPO.resolve()):
        raise ExtractError(f"{out} is inside the srstudio repository: a dancer's landmarks are never committed")
    text = json.dumps(data, separators=(",", ":"))
    pose_track.parse(text)
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out.parent, 0o700)
    handle, temporary = tempfile.mkstemp(dir=out.parent, prefix=".pose-track-", suffix=".json")
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, out)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def model_file(models: Path, name: str) -> Path:
    """The pinned model ``name``, checked against its digest."""
    if name not in MODELS:
        raise ExtractError(f"model is one of {sorted(MODELS)}, not {name!r}")
    path = models / f"pose_landmarker_{name}.task"
    if not path.is_file():
        raise ExtractError(f"{path} is missing: run with --fetch-models in the estimator's interpreter")
    found = sha256(path)
    if found != MODELS[name]:
        raise ExtractError(f"{path} has SHA-256 {found}, not the pinned {MODELS[name]}")
    return path


def fetch_models(models: Path) -> None:  # pragma: no cover - needs the network
    models.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in MODELS:
        path = models / f"pose_landmarker_{name}.task"
        if not path.is_file():
            urllib.request.urlretrieve(MODEL_URL.format(name), path)
            os.chmod(path, 0o600)
        model_file(models, name)


def parse_pick(text: str) -> tuple[str, tuple[float, float] | None]:
    if text == "central":
        return "central", None
    try:
        x, y = (float(v) for v in text.split(","))
    except ValueError:
        raise ExtractError(f"--pick is central or X,Y in shares of the frame, not {text!r}") from None
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ExtractError(f"--pick {text} lies inside the frame: both shares in 0..1")
    return "point", (x, y)


def bodies_from(result: object, width: int, height: int, offset=(0, 0, 1.0, 1.0), crop=False) -> list[Candidate]:
    """The estimator's poses as candidates in pixels of the whole frame; ``offset`` is the crop's (x0, y0) and its
    width and height in pixels when the poses were read on a crop."""
    x0, y0, w, h = offset if crop else (0, 0, width, height)
    out = []
    for marks, world in zip(result.pose_landmarks, result.pose_world_landmarks, strict=True):  # type: ignore[attr-defined]
        image = np.array(
            [[x0 + m.x * w, y0 + m.y * h, m.z, m.visibility or 0.0, m.presence or 0.0] for m in marks], float
        )
        out.append(Candidate(image, np.array([[m.x, m.y, m.z] for m in world], float), crop))
    return out


def extract(  # pragma: no cover - runs the estimator, in its own interpreter
    video: Path, model: Path, model_name: str, pick: str, point, start: int, count: int | None
) -> dict:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    def landmarker(poses: int):
        return vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=poses,
                min_pose_detection_confidence=0.3,
                min_pose_presence_confidence=0.3,
            )
        )

    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ExtractError(f"cannot open {video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tracker = Tracker(width, height, pick, point)
    frames, index = [], 0
    with landmarker(FULL_POSES) as full, landmarker(CROP_POSES) as close:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            if index < start or (count is not None and index >= start + count):
                index += 1
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            bodies = bodies_from(full.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)), width, height)
            box = tracker.crop()
            if box is not None:
                x0, y0, x1, y1 = box
                sub = np.ascontiguousarray(rgb[y0:y1, x0:x1])
                scale = max(1.0, CROP_PIXELS / max(sub.shape[:2]))
                if scale > 1:
                    sub = cv2.resize(sub, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                found = close.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=sub))
                bodies += bodies_from(found, width, height, (x0, y0, x1 - x0, y1 - y0), crop=True)
            colours = [signature(rgb, body) for body in bodies]
            match = tracker.step(bodies, colours)
            body = bodies[match.index] if match else None
            frames.append(frame_entry(index, fps, body, match, width, height))
            index += 1
            if index % 150 == 0:
                print(
                    f"frame {index}: {sum(f['world'] is not None for f in frames)} of {len(frames)} found", flush=True
                )
    capture.release()
    estimator = {
        "name": f"mediapipe-pose-landmarker-{model_name}",
        "version": importlib.metadata.version("mediapipe"),
        "model": model.name,
        "model_sha256": MODELS[model_name],
        "licence": LICENCE,
    }
    source = {
        "sha256": sha256(video),
        "bytes": video.stat().st_size,
        "width": width,
        "height": height,
        "fps": fps,
        "frames": index,
    }
    return record(estimator=estimator, source=source, pick=pick, point=point, start_frame=start, frames=frames)


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - the command line around extract()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("video", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--model", default="heavy", choices=sorted(MODELS))
    parser.add_argument("--models", type=Path, default=Path(sys.prefix) / "models")
    parser.add_argument("--pick", default="central")
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--fetch-models", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.fetch_models:
        fetch_models(args.models)
        return 0
    if args.video is None or args.out is None:
        parser.error("VIDEO and --out are needed")
    pick, point = parse_pick(args.pick)
    data = extract(
        args.video, model_file(args.models, args.model), args.model, pick, point, args.start_frame, args.frames
    )
    out = write(data, args.out)
    found = sum(f["world"] is not None for f in data["frames"])
    print(f"{out}: {found} of {len(data['frames'])} frames hold the dancer")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
