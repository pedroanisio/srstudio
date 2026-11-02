"""The Toon dog dances the seated car groove (ADR 0190): a proof clip for the operator's review, never a release.

    PYTHONPATH=src python examples/toon_dance.py OUT --engine scene-render

builds ``OUT/dance-toon.scene.xml`` with its synthesised track, encodes ``OUT/dance-toon.mp4`` with the engine
(software H.264, ``--strict``), renders a small check of the seat groove picture by picture and reads the groove back
out of the drawn pixels, and writes ``OUT/measurements.json`` and the review page ``OUT/index.html``. ``--no-engine``
writes the scene and the numbers measured on the drawing's own transforms only. The page plays a three-view video
``views.mp4`` beside the clip when one is there.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, gpu, music, toon
from srstudio import dance as dn
from srstudio import toon_dance as td
from srstudio.digest import sha256
from srstudio.toon import SCALE

GROOVE = music.Groove(129)
BARS = 14
CHECK_BEATS = 16  # the rendered check: four bars of the seat groove
CHECK_SCALE = 0.25  # the check renders a quarter of the reel's size
GENERATOR = "Claude Opus 5.5 (claude-opus-5-5) in Claude Code"
FIT = td.DOG_FIT
RAISED = FIT.hold(  # the left arm up and out beside the head (screen-right, clear of the frame's edge)
    {
        "left_upper_arm.down_up": 1.2,
        "left_upper_arm.front_back": 0.0,
        "left_upper_arm.twist_in_out": 0.0,
        "left_lower_arm.stretch": -0.3,
    }
)
PUMPED = FIT.hold(  # the arm-pump's arm lifted to the side and unbent, so the pump rises from shoulder height
    {
        "left_upper_arm.down_up": -0.6,
        "left_upper_arm.front_back": 0.0,
        "left_upper_arm.twist_in_out": 0.0,
        "left_lower_arm.stretch": 0.0,
    }
)


def routine() -> dn.Routine:
    """Eight bars of the seat groove, the arm raised for the last four, then a seated routine of two bars a move."""
    moves = dn.moves()
    return dn.Routine(
        BARS,
        (
            dn.Entry(0, 4, moves["seat-groove"], expression="grin"),
            dn.Entry(4, 8, moves["seat-groove"], transition_beats=1, expression="grin", hold=RAISED),
            dn.Entry(8, 10, moves["head-nod"], transition_beats=1, expression="eyes-closed"),
            dn.Entry(10, 12, moves["shoulder-shimmy"], intensity=0.9, transition_beats=1, expression="smirk"),
            dn.Entry(12, 14, moves["arm-pump"], mirror=True, transition_beats=1, expression="shout", hold=PUMPED),
        ),
    )


def _scene(width: int, height: int, duration: float, background: str) -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=width, height=height, fps="25", duration=duration, background=background)
    scene.add_metadata(
        title="The Toon dog dances",
        generator=f"srstudio.toon_dance; example authored with {GENERATOR}",
        description="Proof of the Toon dance adapter: the dog@2 drawing on the seat groove at 129 BPM.",
        language="en",
    )
    return scene, Canvas(scene, PEACH, width=width, height=height, font_asset=None)


def build(out: Path) -> tuple[Path, td.ToonDance]:
    """The proof scene and its track in ``out``; returns the scene's path and the performance."""
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    duration = GROOVE.at(BARS)
    performance = td.perform(FIT, routine(), GROOVE, 0.0, duration)
    track = out / "track.wav"
    music.write_wav(track, music.render(GROOVE, [music.Section(0, BARS)]), 48000)
    scene, cv = _scene(1080, 1920, duration, PEACH.background)
    scene.add_output(
        id="main", path="dance-toon.mp4", codec="h264", width=1080, height=1920, fps="25", crf="18", faststart=True
    )
    cv.assets.add_audio(id="track", src="track.wav", sha256=sha256(track))
    toon.room(cv, cv.comp)
    td.draw(cv, cv.comp, performance)
    toon.desk(cv, cv.comp)
    mix = scene.add_audioMix(sampleRate=48000, channels=2)
    mix.add_audioTrack(id="music", asset="track", role="music")
    mix.add_master()
    _checked(scene)
    path = out / "dance-toon.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    return path, performance


def check_scene(out: Path) -> tuple[Path, td.ToonDance, float]:
    """The dog alone on a plain ground at a quarter size, dancing the seat groove: what the rendered check reads.
    Returns the scene, its performance and the head radius in its pixels."""
    duration = CHECK_BEATS * GROOVE.beat
    performance = td.perform(FIT, dn.moves()["seat-groove"], GROOVE, 0.0, duration)
    width, height = round(1080 * CHECK_SCALE), round(1920 * CHECK_SCALE)
    scene, cv = _scene(width, height, duration, PEACH.background)
    root = cv.group(cv.comp, "check", scaleX=CHECK_SCALE, scaleY=CHECK_SCALE)
    td.draw(cv, root, performance)
    _checked(scene)
    path = out / "check.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    return path, performance, FIT.radius * SCALE * CHECK_SCALE


def _checked(scene: Scene) -> None:
    errors = [f for f in scene.check() if f.severity == "error"]
    if errors:
        raise td.ToonDanceError("the proof scene is invalid: " + "; ".join(str(f) for f in errors[:5]))


def _run(command: list[str]) -> None:
    with gpu.held():
        done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        raise td.ToonDanceError(f"{command[1]} failed: {(done.stderr or done.stdout).strip()[-400:]}")


def encode(scene: Path, engine: str) -> Path:
    _run([engine, "encode", str(scene), "--hw", "software", "--strict"])
    return scene.parent / "dance-toon.mp4"


def rendered(out: Path, engine: str) -> dict[str, Any]:
    """Render the check picture by picture and read the groove out of the pixels."""
    from PIL import Image

    scene, performance, radius = check_scene(out)
    frames = out / "check-frames"
    frames.mkdir(exist_ok=True, mode=0o700)
    count = len(performance.pictures)
    _run([engine, "render", str(scene), "--frames", f"0..{count}", "-o", str(frames / "f_%04d.png")])
    pictures = [Image.open(frames / f"f_{i:04d}.png").convert("RGB") for i in range(count)]
    ground = PEACH.background.lstrip("#")
    background = (int(ground[0:2], 16), int(ground[2:4], 16), int(ground[4:6], 16))
    bob, sway = td.silhouette_series([np.asarray(p) for p in pictures], background, radius)
    return {
        "bob": _reading(dn.measure_dance(bob, td.FPS, GROOVE, hit="min"), dn.SEAT_GROOVE_BOB),
        "sway": _reading(dn.measure_dance(sway, td.FPS, GROOVE), dn.SEAT_GROOVE_SWAY),
        "pictures": count,
        "radius_px": round(radius, 2),
    }


def _reading(reading: dn.DanceReading, target: dn.DanceTarget) -> dict[str, Any]:
    return {
        "cycles_per_beat": round(reading.cycles_per_beat, 4),
        "onto_s": round(reading.onto, 4),
        "away_s": round(reading.away, 4),
        "peak_to_peak": round(reading.peak_to_peak, 4),
        "hit": reading.hit,
        "hit_offset_s": round(reading.hit_offset * GROOVE.beat, 4),
        "misses": list(target.misses(reading)),
    }


def measured(performance: td.ToonDance) -> dict[str, Any]:
    """The groove of the drawn head in the proof's first eight bars, on the drawing's own transforms."""
    seated = performance.during(0.0, GROOVE.at(8))
    return {
        "bob": _reading(seated.measure("bob", hit="min"), dn.SEAT_GROOVE_BOB),
        "sway": _reading(seated.measure("sway"), dn.SEAT_GROOVE_SWAY),
        "dropped": sorted(performance.dropped),
        "clamped": performance.clamped,
    }


TARGETS = {"bob": ("1", "0.19", "0.26", "0.26..0.50", "min"), "sway": ("1", "0.12", "0.32", "0.17..0.23", "either")}


def _rows(readings: dict[str, Any]) -> str:
    rows = []
    for axis in ("bob", "sway"):
        r = readings[axis]
        target = TARGETS[axis]
        verdict = "meets the target" if not r["misses"] else "; ".join(r["misses"])
        rows.append(
            f"<tr><th>{axis}</th><td>{r['cycles_per_beat']:.3f} <small>({target[0]})</small></td>"
            f"<td>{r['onto_s']:.3f} <small>({target[1]})</small></td>"
            f"<td>{r['away_s']:.3f} <small>({target[2]})</small></td>"
            f"<td>{r['peak_to_peak']:.3f} <small>({target[3]})</small></td>"
            f"<td>{r['hit']} {r['hit_offset_s']:+.3f} s</td><td>{html.escape(verdict)}</td></tr>"
        )
    return "\n".join(rows)


def page(out: Path, numbers: dict[str, Any]) -> Path:
    """The review page beside the clip: it opens as a local file."""
    head = (
        "<tr><th></th><th>cycles / beat</th><th>onto the hit, s</th><th>away, s</th>"
        "<th>peak to peak, head radii</th><th>hit</th><th>against the target</th></tr>"
    )
    sections = [
        f'<h2>Measured on the drawing\'s transforms</h2><table>{head}{_rows(numbers["numbers"])}</table>'
        "<p class=note>The drawn head's centre, carried by the body transform and the head rig's channels, over the "
        "first eight bars. Targets in brackets; strokes are held to 0.02 s (sway 0.025 s).</p>"
    ]
    if numbers.get("rendered"):
        r = numbers["rendered"]
        sections.append(
            f"<h2>Measured on rendered pictures</h2><table>{head}{_rows(r)}</table>"
            f"<p class=note>{r['pictures']} pictures of the seat groove rendered by the engine at a quarter size; the "
            f"centroid of everything drawn, over a head radius of {r['radius_px']} px. The drop must land within "
            "0.02 s of the beat.</p>"
        )
    else:
        sections.append("<h2>Measured on rendered pictures</h2><p>Not rendered: no engine was given.</p>")
    views = (
        '<figure><video src="views.mp4" controls loop playsinline></video><figcaption>The same moves on the shared '
        "skeleton, two bars each. Rows are characters; columns are front (x, y), left (z, y, facing screen right) "
        "and top (x, z, front down the screen).</figcaption></figure>"
        if (out / "views.mp4").is_file()
        else ""
    )
    text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Toon dog dancing</title>
<style>
  :root {{ --bg: #f6f6f4; --fg: #1d1f24; --muted: #5b606b; --card: #ffffff; --line: #d9dbe0; --bad: #a3271f; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #16181d; --fg: #e8e9ec; --muted: #9aa0ab; --card: #1f2229;
    --line: #30343d; --bad: #ff8a80; }} }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.55 system-ui, sans-serif; }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.1rem; margin: 24px 0 8px; }}
  p.lead, .note, figcaption {{ color: var(--muted); }}
  .clips {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 16px; align-items: start; }}
  @media (max-width: 760px) {{ .clips {{ grid-template-columns: 1fr; }} }}
  figure {{ margin: 0; }}
  video {{ width: 100%; border-radius: 8px; background: #000; display: block; }}
  table {{ border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }}
  th, td {{ border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; }}
  td {{ font-variant-numeric: tabular-nums; }}
  small {{ color: var(--muted); }}
  section {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; }}
  section {{ padding: 16px 20px; margin-top: 24px; }}
  li {{ margin: 4px 0; }}
</style>
</head>
<body>
<main>
<h1>Toon dog dancing</h1>
<p class="lead">The approved dog (v2 drawing and head rig) on the dance SDK, at 129 BPM and 25 pictures a second.
Fourteen bars: the seat groove for eight, the left arm raised for the last four, then head nod, shoulder shimmy and arm
pump for two bars each. Proposed: nothing merges until you approve the look.</p>
<div class="clips">
<figure><video src="dance-toon.mp4" controls loop playsinline></video>
<figcaption>The styled clip, with its synthesised track.</figcaption></figure>
{views}
</div>
{"".join(sections)}
<section>
<h2>What to judge</h2>
<ul>
<li>The bob: a quick drop onto every beat and a slower rise, the whole dog together; the head never rotates within a
beat.</li>
<li>The sway: a short snap sideways that lands with the drop, then a slow return.</li>
<li>Bars 5 to 8: the raised left arm rides the body with no lag; the paw drawn over the side of the head.</li>
<li>The arms: the approved drawing's own arms posed on the skeleton all through, so the paws lift off the desk with
the bob.</li>
<li>Faces held per phrase: grin, eyes closed on the nod, smirk on the shimmy, shout on the pump.</li>
<li>The shoulder shimmy is a forward-back motion: seen from the front it reads mostly through the shoulders' small
lift and the face sliding sideways.</li>
<li>The dog has no legs: it dances seated only, so no standing routine follows.</li>
</ul>
</section>
</main>
</body>
</html>
"""
    path = out / "index.html"
    path.write_text(text)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--engine", default=os.environ.get("SRSTUDIO_ENGINE"))
    parser.add_argument("--no-engine", action="store_true", help="write the scene and the drawing's numbers only")
    args = parser.parse_args(argv)
    scene, performance = build(args.out)
    numbers: dict[str, Any] = {"numbers": measured(performance), "generator": GENERATOR}
    if not args.no_engine:
        if not args.engine:
            parser.error("give --engine (or SRSTUDIO_ENGINE), or --no-engine")
        encode(scene, args.engine)
        numbers["rendered"] = rendered(args.out, args.engine)
    (args.out / "measurements.json").write_text(json.dumps(numbers, indent=2) + "\n")
    print(page(args.out, numbers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
