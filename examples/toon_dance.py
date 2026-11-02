"""The Toon dog dances the seated car groove (ADR 0190): a proof clip for the operator's review, never a release.

    PYTHONPATH=src python examples/toon_dance.py OUT --engine scene-render

builds ``OUT/dance-toon.scene.xml`` with its synthesised track, encodes ``OUT/dance-toon.mp4`` with the engine
(software H.264, ``--strict``), renders a small check of the seat groove picture by picture and reads the groove back
out of the drawn pixels, renders three stills (the dance at rest, the approved drawing drawn by its rig with its own
arms, and a raised arm) with the two rest arms side by side in ``OUT/arms.png``, and writes ``OUT/measurements.json``
and the review page ``OUT/index.html``, in Portuguese. ``--no-engine`` writes the scene and the numbers measured on the
drawing's own transforms only. The page plays a three-view video ``views.mp4`` beside the clip when one is there, and
links the previous version at ``../v1/index.html`` when there is one.
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

from srstudio import PEACH, Canvas, gpu, music, toon, toon_head
from srstudio import dance as dn
from srstudio import toon_dance as td
from srstudio.digest import sha256
from srstudio.head_motion import HeadPlan
from srstudio.toon import SCALE, Pose, fx, fy

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
RAISED_BAR = 6  # the still with the arm up: the first beat of bar 7, the arm held up since bar 5's transition
ARMS_BOX = (20.0, 640.0, 400.0, 830.0)  # the drawing's arms, reference pixels: the stills compared side by side


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


def still_scenes(out: Path) -> tuple[Path, Path]:
    """Two one-picture scenes of the dog alone on a plain ground: the dance at rest (every move at intensity 0, so
    the skeleton stays at its fitted rest) with the dance's own arms, and the approved drawing drawn by its rig with
    the rig's own desk arms. Returns their paths."""
    duration = 1.0
    rest = dn.Routine(1, (dn.Entry(0, 1, dn.moves()["seat-groove"], intensity=0.0),))
    performance = td.perform(FIT, rest, GROOVE, 0.0, duration)
    paths = []
    for name in ("rest", "approved"):
        scene, cv = _scene(1080, 1920, duration, PEACH.background)
        if name == "rest":
            td.draw(cv, cv.comp, performance)
        else:
            face = FIT.rest_face
            toon_head.figure(cv, cv.comp, FIT.rig, [Pose(0, face.eyes, face.mouth, "desk")], duration, HeadPlan())
        _checked(scene)
        path = out / f"{name}.scene.xml"
        path.write_bytes(scene.to_bytes(layout="pretty"))
        paths.append(path)
    return paths[0], paths[1]


def _picture(engine: str, scene: Path, frame: int, path: Path) -> Path:
    _run(
        [
            engine,
            "render",
            str(scene),
            "--frames",
            f"{frame}..{frame + 1}",
            "-o",
            str(path.with_suffix("")) + "_%04d.png",
        ]
    )
    rendered = path.with_name(f"{path.stem}_{frame:04d}.png")
    rendered.replace(path)
    return path


def stills(out: Path, engine: str, dance: Path) -> dict[str, Any]:
    """The rest still beside the approved still, their arms side by side in ``arms.png``, and a raised arm from the
    dance's scene ``dance``; returns how many pixels of the arms differ between the two rest stills."""
    from PIL import Image

    rest_scene, approved_scene = still_scenes(out)
    rest = _picture(engine, rest_scene, 0, out / "rest.png")
    approved = _picture(engine, approved_scene, 0, out / "approved.png")
    frame = round(GROOVE.at(RAISED_BAR) * td.FPS)
    _picture(engine, dance, frame, out / "raised.png")
    x0, y0, x1, y1 = ARMS_BOX
    box = (round(fx(x0)), round(fy(y0)), round(fx(x1)), round(fy(y1)))
    a = np.asarray(Image.open(rest).convert("RGB").crop(box)).astype(int)
    b = np.asarray(Image.open(approved).convert("RGB").crop(box)).astype(int)
    differ = int((np.abs(a - b).max(axis=2) > 32).sum())
    gap = 24
    side = Image.new("RGB", (2 * a.shape[1] + gap, a.shape[0]), (255, 255, 255))
    side.paste(Image.fromarray(b.astype(np.uint8)), (0, 0))
    side.paste(Image.fromarray(a.astype(np.uint8)), (a.shape[1] + gap, 0))
    side.save(out / "arms.png")
    for name in ("rest.png", "approved.png", "raised.png", "arms.png"):
        (out / name).chmod(0o600)
    return {"arm_pixels": int(a.shape[0] * a.shape[1]), "arm_pixels_differ": differ, "raised_frame": frame}


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
AXES = {"bob": "sobe e desce", "sway": "balanço lateral"}


def _rows(readings: dict[str, Any]) -> str:
    rows = []
    for axis in ("bob", "sway"):
        r = readings[axis]
        target = TARGETS[axis]
        verdict = "atinge a meta" if not r["misses"] else "; ".join(r["misses"])
        rows.append(
            f"<tr><th>{AXES[axis]}</th><td>{r['cycles_per_beat']:.3f} <small>({target[0]})</small></td>"
            f"<td>{r['onto_s']:.3f} <small>({target[1]})</small></td>"
            f"<td>{r['away_s']:.3f} <small>({target[2]})</small></td>"
            f"<td>{r['peak_to_peak']:.3f} <small>({target[3]})</small></td>"
            f"<td>{r['hit']} {r['hit_offset_s']:+.3f} s</td><td>{html.escape(verdict)}</td></tr>"
        )
    return "\n".join(rows)


def _stills(out: Path, numbers: dict[str, Any]) -> str:
    """The stills' section, or what was not rendered."""
    still = numbers.get("stills")
    if not still or not (out / "arms.png").is_file():
        return "<h2>Imagens paradas</h2><p>Não renderizadas: nenhum motor foi dado.</p>"
    share = 100 * still["arm_pixels_differ"] / still["arm_pixels"]
    return f"""<h2>Em repouso, lado a lado com a v2 aprovada</h2>
<figure><img src="arms.png" alt="Os braços da v2 aprovada à esquerda e os da dança em repouso à direita">
<figcaption>À esquerda, os braços do desenho aprovado (toon-dog@2), desenhados agora pelo próprio rig com os braços
dele. À direita, os braços da dança com o esqueleto parado na pose de repouso. Dos {still["arm_pixels"]} pixels deste
recorte, {still["arm_pixels_differ"]} diferem ({share:.2f}%).</figcaption></figure>
<div class="stills">
<figure><img src="approved.png" alt="O desenho aprovado inteiro"><figcaption>A v2 aprovada, inteira.</figcaption>
</figure>
<figure><img src="rest.png" alt="A dança em repouso inteira"><figcaption>A dança em repouso, inteira.</figcaption>
</figure>
<figure><img src="raised.png" alt="O braço esquerdo levantado"><figcaption>Do clipe, imagem {still["raised_frame"]}
(compasso {RAISED_BAR + 1}): o braço esquerdo levantado ao lado da cabeça.</figcaption></figure>
</div>"""


def page(out: Path, numbers: dict[str, Any]) -> Path:
    """The review page beside the clip, in Portuguese: it opens as a local file."""
    head = (
        "<tr><th></th><th>ciclos por batida</th><th>até o golpe, s</th><th>volta, s</th>"
        "<th>pico a pico, raios da cabeça</th><th>golpe</th><th>contra a meta</th></tr>"
    )
    sections = [
        f"<h2>Medido nas transformações do desenho</h2><table>{head}{_rows(numbers['numbers'])}</table>"
        "<p class=note>O centro da cabeça desenhada, levado pela transformação do corpo e pelos canais do rig da "
        "cabeça, nos primeiros oito compassos. Metas entre parênteses; os golpes valem até 0,02 s (balanço 0,025 s)."
        "</p>"
    ]
    if numbers.get("rendered"):
        r = numbers["rendered"]
        sections.append(
            f"<h2>Medido nas imagens renderizadas</h2><table>{head}{_rows(r)}</table>"
            f"<p class=note>{r['pictures']} imagens do balanço sentado renderizadas pelo motor a um quarto do tamanho; "
            f"o centroide de tudo o que está desenhado, sobre um raio de cabeça de {r['radius_px']} px. A descida "
            "precisa cair a até 0,02 s da batida.</p>"
        )
    else:
        sections.append("<h2>Medido nas imagens renderizadas</h2><p>Não renderizado: nenhum motor foi dado.</p>")
    views = (
        '<figure><video src="views.mp4" controls loop playsinline></video><figcaption>Os mesmos passos no esqueleto '
        "compartilhado, dois compassos cada. As linhas são os personagens de referência do esqueleto (realista, "
        "cartoon, palito), não o cão; as colunas são frente (x, y), lado esquerdo (z, y, virado para a direita da "
        "tela) e topo (x, z, a frente para baixo na tela).</figcaption></figure>"
        if (out / "views.mp4").is_file()
        else ""
    )
    previous = (
        '<p>A versão anterior, que você recusou, continua em <a href="../v1/index.html">v1</a>.</p>'
        if (out.parent / "v1" / "index.html").is_file()
        else ""
    )
    text = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Cão Toon dançando</title>
<style>
  :root {{ --bg: #f6f6f4; --fg: #1d1f24; --muted: #5b606b; --card: #ffffff; --line: #d9dbe0; --bad: #a3271f; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #16181d; --fg: #e8e9ec; --muted: #9aa0ab; --card: #1f2229;
    --line: #30343d; --bad: #ff8a80; }} }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.55 system-ui, sans-serif; }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.1rem; margin: 24px 0 8px; }}
  p.lead, .note, figcaption {{ color: var(--muted); }}
  a {{ color: inherit; }}
  .clips {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 16px; align-items: start; }}
  .stills {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 16px; }}
  @media (max-width: 760px) {{ .clips, .stills {{ grid-template-columns: 1fr; }} }}
  figure {{ margin: 0; }}
  video, img {{ width: 100%; border-radius: 8px; display: block; }}
  video {{ background: #000; }}
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
<h1>Cão Toon dançando, v2</h1>
<p class="lead">O cão aprovado (desenho v2 e rig da cabeça) dançando a 129 BPM, 25 imagens por segundo. São catorze
compassos: oito de balanço sentado, com o braço esquerdo levantado nos últimos quatro, e depois aceno de cabeça,
sacudida de ombros e braço bombeando, dois compassos cada. É uma proposta: nada entra sem a sua aprovação.</p>
{previous}
<div class="clips">
<figure><video src="dance-toon.mp4" controls loop playsinline></video>
<figcaption>O clipe com a trilha sintetizada.</figcaption></figure>
{views}
</div>
{_stills(out, numbers)}
<section>
<h2>O que mudou</h2>
<p>Na v1 os braços eram tubos da mesma largura do ombro à pata, com bolas nas juntas, e saíam de ombros fora do
contorno do corpo. Por isso pareciam patas de inseto. Agora cada braço é o braço aprovado da v2: o mesmo traço de
pelo que afina para dentro do corpo, uma só linha de tinta por baixo, a sombra sob o antebraço e a mesma pata. Ele
nasce do mesmo ponto dentro do tronco que o desenho aprovado usa, e não há bolas nas juntas.</p>
<p>A única diferença em relação à v2 é que o braço se move. O ombro, o cotovelo e o pulso seguem os ossos do
esqueleto, e a largura acompanha cada osso: um ponto no meio do antebraço tem a largura do meio do antebraço
aprovado, mesmo quando o osso aparece mais curto ou mais longo na tela. Cada imagem desenha o braço exatamente onde o
esqueleto está naquela imagem, sem suavizar, reamostrar nem segurar poses, então a velocidade e a aceleração de cada
gesto são as do esqueleto.</p>
<p>O esqueleto do cão foi reajustado ao desenho: os ombros ficam de 24 a 26 px dentro do corpo, e em repouso o
cotovelo, o pulso e a pata caem a menos de 1 px dos da v2. O balanço não mudou: as medidas abaixo são as mesmas da
v1.</p>
</section>
<section>
<h2>O que julgar</h2>
<ul>
<li>Em repouso: os braços da dança ao lado dos da v2 aprovada. Devem ser praticamente iguais.</li>
<li>Compassos 5 a 8: o braço esquerdo levantado ainda parece o braço da v2, saindo de dentro do corpo, com a pata
desenhada sobre o lado da cabeça; ele acompanha o corpo sem atraso.</li>
<li>Compassos 13 e 14, o braço bombeando: quando o antebraço aponta para a câmera ele fica curto na tela. Veja se
ainda lê como braço.</li>
<li>O sobe e desce: uma descida rápida em cada batida e uma subida mais lenta, o cão inteiro junto; a cabeça nunca
gira dentro de uma batida.</li>
<li>O balanço lateral: um golpe curto para o lado junto com a descida, e uma volta lenta.</li>
<li>Rostos mantidos por frase: sorriso, olhos fechados no aceno, sorriso de lado na sacudida, grito no braço
bombeando.</li>
<li>A sacudida de ombros é um movimento para frente e para trás: de frente, ela aparece sobretudo na pequena subida
dos ombros e no rosto deslizando para o lado.</li>
<li>O cão não tem pernas: dança só sentado.</li>
</ul>
</section>
{"".join(sections)}
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
        numbers["stills"] = stills(args.out, args.engine, scene)
    (args.out / "measurements.json").write_text(json.dumps(numbers, indent=2) + "\n")
    print(page(args.out, numbers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
