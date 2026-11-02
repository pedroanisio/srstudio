#!/usr/bin/env python3
"""Dance Stick Study — the Stick style dancing on the shared skeleton (ADR 0189), for the operator to judge.

    python3 dance_stick_study.py PROJECT                # → PROJECT/dance-stick-study.scene.xml (PROJECT holds
                                                        #   assets/Inter-Bold.ttf; the music and script are written)
    python3 dance_stick_study.py PROJECT --master OUT   # also reads the drawn groove back from engine frames, encodes
                                                        #   OUT/dance-stick-study.mp4 and writes OUT/index.html

Sixteen bars at 129 beats a minute, synthesised by music.render. Shot one, eight bars: two friends in a parked car
dance seat-groove, the passenger raising her outer arm for the last four bars, faces held per phrase. Shot two, eight
bars: one figure standing in the study dances bob, sway, arm-pump and step-touch, two bars each. The groove is the one
measured from a reference reel (ADR 0186); nothing of that reel is read or embedded. A study kept to prove the
adapter, never a release: it declares no post and no part, and stays out of episodes/ so nothing ships it.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import string
import subprocess
import sys
import tempfile
from pathlib import Path

from srstudio import STICK, Episode, EpisodeSpec, dance, digest, gpu, master, music, stick
from srstudio import stick_dance as sd
from srstudio import stick_windshield as sw

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "dance-stick-study"
HERE = Path(__file__).resolve().parent
FPS = 25
GROOVE = music.Groove(129)
MOVES = dance.moves()
CAR_BARS = 8
ROOM_BARS = 8
RAISED = (("left_upper_arm.down_up", 2.0), ("left_lower_arm.stretch", 0.8))  # the passenger's outer arm, up and out
STANDING = ("bob", "sway", "arm-pump", "step-touch")
MEASURED_BARS = 2  # engine frames read back from the car shot's start
BLINK_EVERY = 3.1
# The standing figure stands on the study's floor in front of the desk, between its near leg (x 606..631, down to the
# frame's foot) and the frame's right edge: at the cast's size the routine spans 151 px left of its hips' x and 279
# right (arm-pump's near hand), 430 px of the 449 between them. A step further back, at 0.95, leaves 20 px each side.
ROOM_FEET = (795.0, 1810.0)
ROOM_SCALE = 0.95
FRAME_WIDTH = 1080
DESK_LEGS = stick.LEGS[2:]  # stick.room's desk legs (x, y, height), 25 px wide; the chair's are the first two
HALVES = {"noor": (0, 0, 540, 1920), "dev": (540, 0, 1080, 1920)}  # each friend's head is read in its own half

NOOR = dance.Routine(
    CAR_BARS,
    (
        dance.Entry(0, 2, MOVES["seat-groove"], expression="smile"),
        dance.Entry(2, 4, MOVES["seat-groove"], expression="eyes-closed"),
        dance.Entry(4, 8, MOVES["seat-groove"], transition_beats=1, expression="grin", hold=RAISED),
    ),
)
DEV = dance.Routine(
    CAR_BARS,
    (
        dance.Entry(0, 4, MOVES["seat-groove"], expression="cool"),
        dance.Entry(4, 8, MOVES["seat-groove"], expression="grin", hold=(("head.turn_left_right", -0.35),)),
    ),
)
SOLO = dance.Routine(  # on the track's own bars: the room shot opens at bar CAR_BARS
    CAR_BARS + ROOM_BARS,
    tuple(
        dance.Entry(
            CAR_BARS + 2 * i, CAR_BARS + 2 * i + 2, MOVES[name], transition_beats=1 if i else 0, expression=face
        )
        for i, (name, face) in enumerate(zip(STANDING, ("smile", "cool", "grin", "smirk"), strict=True))
    ),
)
TARGETS = {"bob": dance.SEAT_GROOVE_BOB, "sway": dance.SEAT_GROOVE_SWAY}


def blinks(start: float, end: float) -> tuple[float, ...]:
    count = int((end - start) / BLINK_EVERY)
    return tuple(round(start + 1.3 + k * BLINK_EVERY, 3) for k in range(count) if start + 1.3 + k * BLINK_EVERY < end)


def build(root: Path) -> tuple[Path, dict]:
    """The scene, and the numbers read from the performances it draws."""
    car_end = CAR_BARS * GROOVE.bar
    end = car_end + ROOM_BARS * GROOVE.bar
    (root / "audio").mkdir(parents=True, exist_ok=True)
    sections = [
        music.Section(0, 2, frozenset({"kick", "hat", "bass"})),
        music.Section(2, CAR_BARS + ROOM_BARS + 1, frozenset(music.PARTS)),
    ]
    samples = music.render(GROOVE, sections, seed=2026, peak=0.6)[: round(end * 48000)]
    music.write_wav(root / "audio" / "groove.wav", samples, 48000)
    cues = [
        dict(start=0.0, end=car_end, text="Seat groove, in step", speaker="narrator"),
        dict(start=car_end, end=end, text="Bob, sway, arm pump, step touch", speaker="narrator"),
    ]
    (root / "script.json").write_text(json.dumps(cues))
    ep = Episode(
        EpisodeSpec(
            slug=SLUG,
            title="Dance Stick Study",
            description="Stick figures dance on the shared skeleton: seat-groove in a car, then four standing moves.",
            root=root,
            seed=2026,
            style=STICK,
            fps=FPS,
            local_time=False,
            language="en-US",
            output=f"{SLUG}.mp4",
            output_options=dict(
                codec="h264",
                container="mp4",
                fps=str(FPS),
                crf="18",
                preset="medium",
                pixelFormat="yuv420p",
                faststart=True,
            ),  # fmt: skip
            accessibility=dict(description="Two stick figures dance in a parked car, then one dances standing."),
        )
    )
    cv = ep.cv
    ep.cv.assets.add_audio(id="groove", src="audio/groove.wav", sha256=digest.sha256(root / "audio" / "groove.wav"))
    ep.add_track("track-groove", "groove", role="music")
    ep.master()

    noor = sd.perform(NOOR, GROOVE, 0.0, car_end)
    dev = sd.perform(DEV, GROOVE, 0.0, car_end)
    car = cv.group(ep.comp, "shot-car")
    cv.gate(car, [(0.0, car_end)])
    sw.windshield(cv, car, end, speed=0)
    sd.draw(cv, car, noor, end=end, look=sw.NOOR, at=sw.PASSENGER_AT, prefix="noor", blinks=blinks(0.0, car_end))
    sd.draw(cv, car, dev, end=end, at=sw.DRIVER_AT, prefix="dev", blinks=blinks(0.7, car_end))
    sw.dashboard(cv, car, end)

    solo = sd.perform(SOLO, GROOVE, car_end, end)
    room = cv.group(ep.comp, "shot-room")
    cv.gate(room, [(car_end, end)])
    stick.room(cv, room)
    at = (ROOM_FEET[0] - ROOM_SCALE * sd.SEAT[0], ROOM_FEET[1] - ROOM_SCALE * sd.FLOOR)
    sd.draw(cv, room, solo, end=end, at=at, scale=ROOM_SCALE, prefix="solo", blinks=blinks(car_end, end))

    scene = ep.finish(root / f"{SLUG}.scene.xml", root / "qa" / "sdk-validation.json")
    numbers = {
        "dev": _readings(dev, 0, CAR_BARS),
        "noor": _readings(noor, 0, CAR_BARS),
        "noor_raised_hand": _reading(
            [-p.hands[0][1] / stick.HEAD_R for p in noor.poses[_at(5) :]], start=noor.times[_at(5)]
        ),
        "solo": {name: _solo(solo, i, name) for i, name in enumerate(STANDING)},
        "solo_reach_px": solo.reach,
        "room_clearance": clearance(solo, at),
        "pictures": {"car": len(noor.poses), "room": len(solo.poses)},
    }
    return scene, numbers


def clearance(performance: sd.StickDance, at: tuple[float, float]) -> dict:
    """Where the standing figure is drawn against the study's desk: its leftmost and rightmost strokes (the head's edge
    included) against the near desk leg's right edge and the frame's, and its feet against the floor line of the desk
    legs behind it."""
    s = ROOM_SCALE
    xs, feet = [], []
    for p in performance.poses:
        points = (p.neck, p.hip, *p.knees, *p.feet, *p.elbows, *p.hands)
        xs.append(min(min(x for x, _ in points), p.head[0] - stick.HEAD_R))
        xs.append(max(max(x for x, _ in points), p.head[0] + stick.HEAD_R))
        feet.extend(y for _, y in p.feet)
    near = max(DESK_LEGS, key=lambda leg: leg[1] + leg[2])
    behind = max(y + h for x, y, h in DESK_LEGS if (x, y, h) != near)
    return {
        "left_px": round(at[0] + s * min(xs), 1),
        "right_px": round(at[0] + s * max(xs), 1),
        "frame_right_px": FRAME_WIDTH,
        "near_leg_right_px": near[0] + 25,
        "feet_y_px": [round(at[1] + s * min(feet), 1), round(at[1] + s * max(feet), 1)],
        "desk_legs_floor_px": behind,
        "floor_px": ROOM_FEET[1],
    }


def _at(bar: int) -> int:
    return round(GROOVE.at(bar) * FPS)


SOLO_CHANNEL = {  # what each standing move moves most, read in head radii
    "bob": ("head", "up", lambda p: -p.head[1]),
    "sway": ("hips", "right", lambda p: p.hip[0]),
    "arm-pump": ("near hand", "up", lambda p: -p.hands[1][1]),
    "step-touch": ("hips", "right", lambda p: p.hip[0]),
}


def _solo(performance: sd.StickDance, i: int, name: str) -> dict:
    """The standing move ``name``, danced over bars ``2i``..``2i + 2``, read on the channel it moves most."""
    point, axis, read = SOLO_CHANNEL[name]
    first, last = _at(2 * i), _at(2 * i + 2)
    series = [read(p) / stick.HEAD_R for p in performance.poses[first:last]]
    try:
        reading = _reading(series, start=performance.times[first])
    except dance.DanceMeasureError as exc:
        reading = {"error": str(exc)}
    return {"channel": f"{point} {axis}", **reading}


def _reading(series, start: float = 0.0) -> dict:
    r = dance.measure_dance(list(series), FPS, GROOVE, start=start)
    return {
        "cycles_per_beat": round(r.cycles_per_beat, 4),
        "onto_s": round(r.fall if r.hit == "min" else r.rise, 4),
        "away_s": round(r.rise if r.hit == "min" else r.fall, 4),
        "peak_to_peak": round(r.peak_to_peak, 4),
        "hit": r.hit,
        "hit_offset_s": round(r.hit_offset * GROOVE.beat, 4),
    }


def _readings(performance: sd.StickDance, first: int, last: int) -> dict:
    out = {}
    for name, point, axis in (("bob", "head", "up"), ("sway", "hip", "right")):
        series = list(performance.track(point, axis)[_at(first) : _at(last)])
        out[name] = {**_reading(series), "misses": TARGETS[name].misses(dance.measure_dance(series, FPS, GROOVE))}
    return out


def rendered(scene: Path, engine: str, bars: int) -> dict:
    """Each friend's head read from the engine's own frames over the car shot's first ``bars``, in its own half of the
    frame, and both heads pooled: the pooled centre moves with how many pixels of each head read as skin."""
    count = _at(bars)
    with tempfile.TemporaryDirectory(dir=scene.parent) as folder:
        with gpu.held():
            done = subprocess.run(
                [engine, "render", scene.name, "--frames", f"0..{count}", "--output", f"{folder}/f%04d.png"],
                cwd=scene.parent,
                capture_output=True,
                text=True,
            )
        if done.returncode != 0:
            raise SystemExit(f"the engine did not render the frames: {done.stderr[-400:]}")
        paths = sorted(Path(folder).glob("f*.png"))
        heads = {who: sd.head_centroids(paths, box=box) for who, box in HALVES.items()}
        heads["pooled"] = sd.head_centroids(paths)
    out: dict = {"frames": count}
    for who, centres in heads.items():
        up = [-y / stick.HEAD_R for _, y in centres]
        right = [x / stick.HEAD_R for x, _ in centres]
        out[who] = {"bob": _reading(up), "sway": _reading(right)}
    return out


def page(out: Path, clip: str, views: str | None, numbers: dict) -> Path:
    """The local page the operator judges the clip on: the clip, the three-plane views and the numbers."""
    car_end = CAR_BARS * GROOVE.bar
    marks = [
        (0.0, "car: seat-groove, both"),
        (GROOVE.at(4), "car: passenger raises her arm, driver turns his head"),
        (car_end, "standing: bob"),
        (car_end + GROOVE.at(2), "standing: sway"),
        (car_end + GROOVE.at(4), "standing: arm-pump"),
        (car_end + GROOVE.at(6), "standing: step-touch"),
    ]
    bob, sway = dance.SEAT_GROOVE_BOB, dance.SEAT_GROOVE_SWAY

    def row(label: str, r: dict, target) -> str:
        cells = (
            f"{r['cycles_per_beat']:.3f}",
            f"{r['onto_s']:.3f} s",
            f"{r['away_s']:.3f} s",
            f"{r['peak_to_peak']:.3f}",
            f"{r['hit']} {r['hit_offset_s'] * 1000:+.0f} ms",
        )
        want = (
            f"{target.cycles_per_beat:g}",
            f"{target.onto:g} s",
            f"{target.away:g} s",
            f"{target.peak_to_peak[0]:g}..{target.peak_to_peak[1]:g}",
            "min, on the beat" if target.hit == "min" else "on the beat",
        )
        tds = "".join(f"<td>{c}<br><span class=muted>{w}</span></td>" for c, w in zip(cells, want, strict=True))
        return f"<tr><th>{html.escape(label)}</th>{tds}</tr>"

    car, ren = numbers["numbers"], numbers["rendered"]
    rows = "".join(
        [
            row("Driver head bob (drawn)", car["dev"]["bob"], bob),
            row("Driver hip sway (drawn)", car["dev"]["sway"], sway),
            row("Passenger head bob (drawn)", car["noor"]["bob"], bob),
            row("Passenger hip sway (drawn)", car["noor"]["sway"], sway),
            row(f"Driver head bob, engine frames ({ren['frames']})", ren["dev"]["bob"], bob),
            row(f"Driver head sway, engine frames ({ren['frames']})", ren["dev"]["sway"], sway),
            row(f"Passenger head bob, engine frames ({ren['frames']})", ren["noor"]["bob"], bob),
            row(f"Passenger head sway, engine frames ({ren['frames']})", ren["noor"]["sway"], sway),
        ]
    )
    pooled = ren["pooled"]["sway"]["hit_offset_s"] * 1000
    alone = max(abs(ren[who]["sway"]["hit_offset_s"]) for who in HALVES) * 1000
    room = car["room_clearance"]
    hand = car["noor_raised_hand"]
    solo = "".join(
        f"<li>{html.escape(name)}, {r['channel']}: {r['cycles_per_beat']:.3f} cycles a beat, "
        f"{r['peak_to_peak']:.2f} head radius peak to peak, {r['hit']} {r['hit_offset_s'] * 1000:+.0f} ms from the "
        "beat</li>"
        if "error" not in r
        else f"<li>{html.escape(name)}, {r['channel']}: not read ({html.escape(r['error'])})</li>"
        for name, r in car["solo"].items()
    )
    views_figure = (
        f'<h2>Three planes</h2><video src="./{html.escape(views)}" controls playsinline preload="metadata" '
        'class="wide"></video><p class="muted">Rows are characters. Columns are front (x, y), left (z, y, facing '
        "screen right) and top (x, z, front down the screen). The moves play in the clip's order, two bars each, on "
        'the stick skeleton preset standing.</p><h2 style="margin-top:16px">Jump to</h2>'
        if views
        else "<h2>Jump to</h2>"
    )
    fields = {
        "clip": html.escape(clip),
        "views_figure": views_figure,
        "frames": ren["frames"],
        "rows": rows,
        "hand_cycles": f"{hand['cycles_per_beat']:.3f}",
        "hand_p2p": f"{hand['peak_to_peak']:.2f}",
        "head_p2p": f"{car['noor']['bob']['peak_to_peak']:.2f}",
        "hand_offset": f"{hand['hit_offset_s'] * 1000:+.0f}",
        "solo": solo,
        "reach": f"{car['solo_reach_px']:.1f}",
        "pooled": f"{pooled:+.0f}",
        "alone": f"{alone:.0f}",
        "room_left": f"{room['left_px']:.0f}",
        "room_right": f"{room['right_px']:.0f}",
        "near_leg": f"{room['near_leg_right_px']}",
        "feet_low": f"{room['feet_y_px'][0]:.0f}",
        "feet_floor": f"{room['feet_y_px'][1]:.0f}",
        "desk_floor": f"{room['desk_legs_floor_px']}",
        "marks": json.dumps([{"start": round(t, 3), "label": label} for t, label in marks]),
    }
    text = string.Template((HERE / "proof_page.html").read_text()).substitute(fields)
    path = out / "index.html"
    path.write_text(text)
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--master", type=Path, help="encode the clip here and write the proof page beside it")
    parser.add_argument("--views", help="the three-plane video's file name in the --master folder, if there is one")
    parser.add_argument("--page", type=Path, help="only rewrite the page in this folder from its numbers.json")
    args = parser.parse_args(argv)
    if args.page is not None:
        out = args.page.resolve()
        page(out, f"{SLUG}.mp4", args.views, json.loads((out / "numbers.json").read_text()))
        return 0
    root = args.project.resolve()
    scene, numbers = build(root)
    record = {"numbers": numbers}
    if args.master is not None:
        engine = os.environ.get("SRSTUDIO_ENGINE")
        if not engine:
            raise SystemExit("--master runs the engine: set SRSTUDIO_ENGINE to a scene-render binary")
        out = args.master.resolve()
        record["rendered"] = rendered(scene, engine, MEASURED_BARS)
        encoded = master.encode(scene, out, engine=engine, args=("--strict", "--hw", "software"))
        record["encode"] = {"returncode": encoded.returncode, "paths": [p.name for p in encoded.paths]}
        (out / "numbers.json").write_text(json.dumps(record, indent=2, default=list))
        page(out, f"{SLUG}.mp4", args.views, record)
    json.dump(record, sys.stdout, indent=2, default=list)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
