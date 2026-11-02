"""What Mae and Bruno do on every frame of the span, read from the reel's own staging and sampled the way its drawing
is keyed: the pose of the beat, the head plan's channels, the gaze, the blink, the viseme heard, the gasp, the jump and
his late hands.

The reel draws one character per close-up; the clay keeps both on the sofa, so the one the close-up leaves out is
sampled from the same shot with the same functions: their acts, their head plan from what was said, their own lip track.

    capture(project) -> Performance     # a flat build of the reel with its figure calls recorded, then sampled
    Performance.load(path)              # the written record, parsed strictly: unknown or missing fields refuse
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

from srstudio.scripting import at

SCHEMA = "clay-sofa.performance/1.1.0"
FPS = 24
CHARACTERS = {"rabbit": "mae", "bear": "bruno"}
SHOT_OF = {"hamster": "two", "goat": "mae", "sloth": "bruno"}  # the reel's shot names, as it_autoplayed_data has them


class PerformanceError(ValueError):
    """A performance record that is not the one this study wrote: a field missing or unknown, a value out of range."""


@dataclass(frozen=True)
class Arm:
    """One of Bruno's late hands at a frame: its shoulder and its angle, in his own drawing's reference pixels."""

    root: tuple[float, float]
    degrees: float  # 0 points right, turning clockwise, as toon_bed.swung_arm reads it
    length: float
    width: float


@dataclass(frozen=True)
class Frame:
    """One character at one frame. Lengths are the character's reference pixels, angles degrees clockwise on screen,
    all in the unmirrored drawing."""

    eyes: str
    gaze: str
    blink: bool
    mouth: str  # the pose's mouth, or the viseme heard
    pose_mouth: str
    pose_arms: str  # the pose's arms at rest, as toon_head draws them under the face
    lift: float  # the whole figure up (negative) or down, from the gasp and the jump
    tilt: float  # the whole figure about its seat, from the gasp
    lean: float  # toon_head's channels, as its groups are keyed
    breath: float
    turn: float  # the rig's tilt plus the plan's turn
    roll: float
    nod: float
    idle_roll: float
    idle_y: float
    face_x: float
    arms: tuple[Arm, ...]


@dataclass(frozen=True)
class Performance:
    schema: str
    fps: int
    frames: int
    shots: list[dict[str, Any]]  # each shot of the span: name, start, end
    cast: dict[str, list[Frame]]  # mae, bruno

    def at(self, who: str, frame: int) -> Frame:
        return self.cast[who][frame]

    def shot(self, frame: int) -> str:
        t = frame / self.fps
        for row in self.shots:
            if row["start"] - 1e-9 <= t < row["end"] - 1e-9:
                return row["name"]
        return self.shots[-1]["name"]

    def dump(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=0, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: Path) -> Performance:
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise PerformanceError(f"{path}: not a readable performance record: {error}") from error
        return cls.parse(data)

    @classmethod
    def parse(cls, data: Any) -> Performance:
        _fields(data, cls, "performance")
        if data["schema"] != SCHEMA:
            raise PerformanceError(f"schema {data['schema']!r}, not {SCHEMA}")
        if data["fps"] != FPS or not (isinstance(data["frames"], int) and data["frames"] > 0):
            raise PerformanceError(f"a performance is {FPS} fps over a positive count of frames")
        shots = data["shots"]
        if not (isinstance(shots, list) and shots):
            raise PerformanceError("a performance names its shots")
        for row in shots:
            if not (isinstance(row, dict) and set(row) == {"name", "start", "end"} and row["name"] in SHOT_OF.values()):
                raise PerformanceError(f"a shot is name, start and end, its name one of {sorted(SHOT_OF.values())}")
            if not (_number(row["start"]) and _number(row["end"]) and 0 <= row["start"] < row["end"]):
                raise PerformanceError(f"shot {row['name']} runs from {row['start']} to {row['end']}")
        if set(data["cast"]) != set(CHARACTERS.values()):
            raise PerformanceError(f"the cast is {sorted(CHARACTERS.values())}, got {sorted(data['cast'])}")
        cast = {}
        for who, rows in data["cast"].items():
            if not (isinstance(rows, list) and len(rows) == data["frames"]):
                raise PerformanceError(f"{who} has {len(rows) if isinstance(rows, list) else rows!r} frames")
            cast[who] = [_frame(row, f"{who} frame {n}") for n, row in enumerate(rows)]
        return cls(data["schema"], data["fps"], data["frames"], shots, cast)


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _fields(data: Any, kind, what: str) -> None:
    names = {f.name for f in fields(kind)}
    if not isinstance(data, dict) or set(data) != names:
        found = sorted(data) if isinstance(data, dict) else type(data).__name__
        raise PerformanceError(f"{what}: expected the fields {sorted(names)}, found {found}")


EYES = ("wide", "left", "narrow", "half", "down", "up", "sleepy", "closed", "wince", "hearts")
POSE_ARMS = ("desk", "type", "crossed", "sigh", "lean", "face", "face2")  # srstudio.toon.ARMS
MOUTHS = ("flat", "o", "smirk", "smile", "open", "round", "teeth", "frown", "grin")
LIMITS = {"lift": 200.0, "tilt": 30.0, "lean": 20.0, "breath": 2.0, "turn": 30.0, "roll": 20.0, "nod": 40.0}
LIMITS.update(idle_roll=10.0, idle_y=20.0, face_x=40.0)


def _frame(row: Any, what: str) -> Frame:
    _fields(row, Frame, what)
    if row["eyes"] not in EYES or row["mouth"] not in MOUTHS or row["pose_mouth"] not in MOUTHS:
        raise PerformanceError(f"{what}: eyes {row['eyes']!r}, mouth {row['mouth']!r} are not the rig's")
    if row["gaze"] not in ("ahead", "left", "right", "up") or not isinstance(row["blink"], bool):
        raise PerformanceError(f"{what}: gaze {row['gaze']!r}, blink {row['blink']!r}")
    if row["pose_arms"] not in POSE_ARMS:
        raise PerformanceError(f"{what}: arms {row['pose_arms']!r} is not one of {POSE_ARMS}")
    for name, bound in LIMITS.items():
        if not (_number(row[name]) and abs(row[name]) <= bound):
            raise PerformanceError(f"{what}: {name} {row[name]!r} is not a number within ±{bound}")
    arms = []
    for arm in row["arms"]:
        _fields(arm, Arm, f"{what} arm")
        root = arm["root"]
        if not (isinstance(root, list) and len(root) == 2 and all(_number(v) for v in root)):
            raise PerformanceError(f"{what}: an arm's root is two numbers")
        if not all(_number(arm[k]) for k in ("degrees", "length", "width")) or arm["length"] <= 0 or arm["width"] <= 0:
            raise PerformanceError(f"{what}: an arm has an angle and a positive length and width")
        arms.append(
            Arm((float(root[0]), float(root[1])), float(arm["degrees"]), float(arm["length"]), float(arm["width"]))
        )
    values = {k: row[k] for k in row if k != "arms"}
    return Frame(**values, arms=tuple(arms))


# --- capture ----------------------------------------------------------------------------------------------------------


@dataclass
class _Call:
    shot: Any
    who: str
    at: tuple[float, float]
    scale: float
    mirror: bool


def _state(keys: dict[str, list[tuple[float, int]]], t: float, default: str) -> str:
    """Which of hold-keyed layers shows at ``t``: the one whose last key at or before ``t`` is on."""
    shown, when = default, -math.inf
    for name, rows in keys.items():
        for key, on in rows:
            if key <= t + 1e-9 and key >= when:
                if on:
                    shown, when = name, key
                elif shown == name:
                    shown, when = default, key
    return shown


@dataclass(frozen=True)
class Prepared:
    """One character through one shot, as toon_pair.figure prepares it for toon_head: the rig, the pose runs in project
    seconds, the head plan baked as it is emitted, the lip track."""

    rig: Any
    spans: list
    plan: Any
    mouths: tuple


def prepare(reel, shot, who: str) -> Prepared:
    from srstudio import head_motion, sketch, toon, toon_pair, toon_rigs
    from srstudio.toon_head import CHANNELS, _bake_spring

    app = shot.app
    rig = toon_rigs.rig_of(sketch.part_of(who), shot.versions)
    poses = toon.parse_poses(toon_pair.poses_of(shot.beats, reel.ACTS[who], app.start, app.end), f"{who} {app.start}")
    said = shot.said()
    own = [speech for by, speech in said if by == who]
    heard = [speech for by, speech in said if by != who]
    plan = head_motion.plan(rig.style, own, shot.end, heard=heard).during(app.start, app.end)
    baked: dict[str, Any] = {name: _bake_spring(getattr(plan, name)) for name in CHANNELS}
    plan = replace(plan, **baked)
    mouths = tuple(sketch.drawer_extras(who, None, shot.mouths).get("mouths", ()))
    spans = [(p, round(s + app.start, 6), round(e + app.start, 6)) for p, s, e in toon.runs(poses, app.end - app.start)]
    return Prepared(rig, spans, plan, mouths)


def sample(prepared: Prepared, t: float) -> dict[str, Any]:
    """The character at project second ``t``, as toon_head keys it: the run's pose, the gaze and viseme layers shown,
    a blink's lids, and every head channel."""
    from srstudio.toon_cast import BLINK_HOLD, SHUT, blink_times, viseme_keys
    from srstudio.toon_head import _PUPIL_FREE, gaze_states

    rig, plan, spans = prepared.rig, prepared.plan, prepared.spans
    pose, start, end = next(((p, s, e) for p, s, e in spans if s - 1e-9 <= t < e), spans[-1])
    gaze = "ahead"
    if pose.eyes not in _PUPIL_FREE:
        gaze = _state(gaze_states(plan.gaze, start, end), t, "ahead")
    keys = viseme_keys(prepared.mouths, start, end)
    mouth = _state(keys, t, "closed") if keys else "closed"
    shut = pose.eyes in SHUT
    blinks = [] if shut or pose.eyes == "sleepy" else blink_times(start, end, rig.look.blink, BLINK_HOLD)
    return dict(
        eyes=pose.eyes,
        gaze=gaze,
        blink=any(b - 1e-9 <= t < b + BLINK_HOLD - 1e-9 for b in blinks),
        mouth=pose.mouth if mouth == "closed" else mouth,
        pose_mouth=pose.mouth,
        pose_arms=pose.arms,
        lean=plan.lean.sample(t),
        breath=plan.breath.sample(t),
        turn=rig.tilt + plan.turn.sample(t),
        roll=plan.roll.sample(t),
        nod=plan.nod.sample(t),
        idle_roll=plan.idle_roll.sample(t),
        idle_y=plan.idle_y.sample(t),
        face_x=plan.face_x.sample(t),
    )


def _eased(keys: list[tuple[float, float]], t: float, curve: str) -> float:
    from srstudio._curves import progress

    if t <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:], strict=False):
        if t < b:
            return va + (vb - va) * progress(curve, (t - a) / (b - a))
    return keys[-1][1]


def body_motion(reel, beats, who: str, t: float, shot_name: str, frame_px: float) -> tuple[float, float]:
    """The whole figure's lift and tilt at ``t``: the reel keys the gasp and the jump on the two-shot's figure group in
    frame pixels, here in the figure's reference pixels (``frame_px`` of them to one)."""
    if shot_name != "two":
        return 0.0, 0.0
    if who == "bruno":
        keys = [0.0, reel.GASP_SNAPS, reel.GASP_HOLDS, reel.GASP_ENDS]
        lift = _eased(list(zip(keys, (0.0, -reel.GASP_LIFT, -reel.GASP_LIFT, 0.0), strict=True)), t, "sine-out")
        tilt = _eased(list(zip(keys, (0.0, reel.GASP_TILT, reel.GASP_TILT, 0.0), strict=True)), t, "sine-out")
        return lift / frame_px, tilt
    sting = at(beats, "sting")
    keys = [(sting, 0.0), (sting + 0.1, -reel.JUMP), (sting + 0.34, 0.0)]
    return _eased(keys, t, "sine-out") / frame_px, 0.0


def late_hands(reel, beats, t: float) -> tuple[Arm, ...]:
    """Bruno's hands up after the sting, as the two-shot draws them behind him: shoulder and target in his own drawing's
    reference pixels, the swing eased as toon_bed keys it."""
    from srstudio import toon_bed, toon_pair, toon_sketch

    sting = at(beats, "sting")
    start, end = sting + reel.WOW_LATE, sting + reel.WOW_DOWN
    if not (start - 1e-9 <= t < end - 1e-9):
        return ()
    arms = []
    sx, sy = toon_sketch.SEAT
    for root, target in reel.WOW_HANDS:
        degrees, length = toon_pair.aim(root, target)
        swing = [(start, degrees + 40.0), (start + 0.14, degrees)]
        local = (
            (root[0] - reel.BRUNO_AT[0]) / reel.PAIR_SCALE + sx,
            (root[1] - reel.BRUNO_AT[1]) / reel.PAIR_SCALE + sy,
        )
        angle = _eased(swing, t, "cubic-out")
        arms.append(Arm(local, angle, length / reel.PAIR_SCALE, toon_bed.ARM_WIDTH))
    return tuple(arms)


def capture(root: Path, frames: int) -> Performance:
    """Build the reel's flat control in ``root`` with its figure calls recorded, and sample both characters on every
    frame of ``frames`` from the shots recorded."""
    import sofa_room_study as study

    from srstudio import toon, toon_pair
    from srstudio.toon_sketch import build

    reel = study.reel
    calls: list[_Call] = []
    original = toon_pair.figure

    def recorded(shot, parent, who, at, acts, *, scale=1.0, mirror=False, moving=True):
        calls.append(_Call(shot, who, tuple(at), scale, mirror))
        return original(shot, parent, who, at, acts, scale=scale, mirror=mirror, moving=moving)

    toon_pair.figure = recorded
    try:
        staging, _ = study.staging_of(root, {"--control"})
        build(root, staging, {"--voice"})
    finally:
        toon_pair.figure = original
    end = frames / FPS
    shots: dict[float, Any] = {}
    for call in calls:
        if call.shot.app.start < end and call.shot.app.who in SHOT_OF:
            shots.setdefault(call.shot.app.start, call.shot)
    ordered = [shots[k] for k in sorted(shots)]
    if not ordered or ordered[0].app.start != 0.0:
        raise PerformanceError("the build drew no shot from the span's start")
    rows = [dict(name=SHOT_OF[s.app.who], start=s.app.start, end=s.app.end) for s in ordered]
    frame_px = toon.SCALE * reel.PAIR_SCALE
    cast: dict[str, list[Frame]] = {name: [] for name in CHARACTERS.values()}
    prepared = {(id(s), part): prepare(reel, s, part) for s in ordered for part in CHARACTERS}
    for n in range(frames):
        t = n / FPS
        shot = next((s for s in ordered if s.app.start - 1e-9 <= t < s.app.end - 1e-9), ordered[-1])
        name = SHOT_OF[shot.app.who]
        for part, who in CHARACTERS.items():
            values = sample(prepared[id(shot), part], t)
            lift, tilt = body_motion(reel, shot.beats, who, t, name, frame_px)
            arms = late_hands(reel, shot.beats, t) if who == "bruno" else ()
            cast[who].append(Frame(**values, lift=lift, tilt=tilt, arms=arms))
    return Performance(SCHEMA, FPS, frames, rows, cast)


def main(argv: list[str]) -> None:
    root, out = Path(argv[1]).resolve(), Path(argv[2]).resolve()
    frames = int(argv[3]) if len(argv) > 3 else 191
    performance = capture(root, frames)
    performance.dump(out)
    Performance.load(out)  # what was written reads back under the same rules
    print(json.dumps(performance.shots))
