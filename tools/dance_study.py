#!/usr/bin/env python3
"""Measure a reference dancer's style, check our dances against it, and build the local proof page (ADR 0203).

    python tools/dance_study.py measure TRACK.json --audio VIDEO --name NAME --description TEXT --out STYLE.json
    python tools/dance_study.py check STYLE.json --out FINDINGS.json [--bars 8] [--fps 30] [--audio VIDEO]
    python tools/dance_study.py page TRACK.json STYLE.json FINDINGS.json --video VIDEO --out DIR

``measure`` reads a ``srstudio.pose-track`` record (``tools/pose_extract.py`` writes it), measures it on the track's
beat grid (``music.reading`` of ``--audio``, or ``--bpm`` and ``--offset``), and writes the ``srstudio.dance-style``
record: numbers only. ``check`` dances every preset move for ``--bars`` bars on the style's grid, on the realistic
skeleton, and, with ``--audio``, a routine ``choreograph`` makes for the song, and writes each one's ranked misses and
the misses all of them share. ``page`` writes a standalone page in Portuguese for the operator: the footage beside the
dancer's extracted skeleton, the style in plain numbers, the ranking, and the three-plane views of the closest preset.
The page and its videos show a real person: they stay under the workspace's ``generated/`` (directory 700, files 600)
on this machine and are never committed or published.

The skeleton draws what the footage measured apart from what the estimator inferred (ADR 0202): a bone between two
landmarks the estimator saw is a solid line (``measured-2d``); a bone twist the world landmarks hold is a translucent
band in the side's colour with a stripe along the direction it was read from, solid on the half toward the camera and
dashed on the far half (``estimated-3d``); a twist they cannot hold is a grey band with no stripe (``unobserved``); a
legend says so in the frame. The world landmarks' x and y run as the picture's (``pose_track.AXES``), so their
directions place the stripe on the picture.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import subprocess
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from srstudio import choreograph, dance, dance_style, music
from srstudio import dance_study as ds
from srstudio import pose_track as pt

REPO = Path(__file__).resolve().parents[1]
MODEL = "Claude Opus 5.5 (claude-opus-5-5) in Claude Code"
TOOL = "tools/dance_study.py"
BONES_2D = (
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_ankle", "left_foot_index"),
    ("right_ankle", "right_foot_index"),
)
# BGR, as OpenCV draws: the dancer's left orange, her right blue.
LEFT, RIGHT, MID, FAINT = (60, 170, 255), (255, 170, 60), (235, 235, 235), (90, 90, 90)
GREY, STRIPE, BACKGROUND = (128, 128, 128), (255, 255, 255), 24
TRUNK = (150, 210, 90)  # the torso's and the head's estimated twist: a colour of its own, never the grey of unobserved
LEGEND_FONT = "dm-sans-700.ttf"  # in SRSTUDIO_FONTS, the pinned fonts: it has Portuguese's accents
SEEN = 0.5
BAND_ALPHA = 0.35  # how much a twist band covers the ground under it
# A band's half width as a share of the torso's length in the picture (hips' centre to shoulders' centre): about the
# body's own half widths on a standing adult, enough to read a stripe on.
HALF = {"spine": 0.30, "head": 0.16}
LIMB_HALF = 0.09
STRIPE_SPAN = (0.15, 0.85)  # the stripe runs along this share of its bone, clear of the joints
DASH_PX = (10, 7)
LEGEND_PT = {
    pt.MEASURED_2D: "linha cheia: posição medida na imagem (2D)",
    pt.ESTIMATED_3D: "faixa colorida e listra: giro estimado em 3D (listra cheia na frente, tracejada atrás)",
    pt.UNOBSERVED: "faixa cinza sem listra: giro não observado",
    "hidden": "linha cinza fina: ponto mal visto",
}


class StudyError(RuntimeError):
    """An input the study tool cannot use."""


def private(path: Path) -> Path:
    """``path``'s folder made with mode 700, outside the repository."""
    path = path.resolve()
    if path.is_relative_to(REPO.resolve()) and "assets/dance/styles" not in str(path):
        raise StyleOutside(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


class StyleOutside(StudyError):
    def __init__(self, path: Path):
        super().__init__(f"{path} is inside the repository: only a style record goes there, under assets/dance/styles")


def write_private(path: Path, text: str | bytes) -> Path:
    path = private(path)
    data = text.encode() if isinstance(text, str) else text
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    os.chmod(path, 0o600)
    return path


# --- measure -------------------------------------------------------------------------------------------------------


def grid(audio: Path | None, bpm: float | None, offset: float | None) -> music.Groove:
    if bpm is not None:
        return music.Groove(bpm, 4, offset or 0.0)
    if audio is None:
        raise StudyError("the grid comes from --audio, or from --bpm and --offset")
    return music.reading(audio).groove


def measure(track: pt.PoseTrack, groove: music.Groove, *, name: str, description: str) -> dance_style.DanceStyle:
    body = ds.reference_body(track)
    reading = ds.measure_style(body, groove)
    reference = dance_style.Reference(
        description=description,
        source_sha256=track.source.sha256,
        estimator=track.estimator.name,
        estimator_version=track.estimator.version,
        model_sha256=track.estimator.model_sha256,
        seconds=round(len(track.frames) / track.fps, 3),
        frames=len(track.frames),
        used=body.used,
        rejected=dict(body.rejected) | {"repeat": body.repeats},
        bpm=groove.bpm,
        beats_per_bar=groove.beats_per_bar,
        offset_s=groove.offset,
    )
    return dance_style.derive(
        reading, name=name, description=description, reference=reference, generated_by={"tool": TOOL, "model": MODEL}
    )


# --- check ---------------------------------------------------------------------------------------------------------


def candidates(groove: music.Groove, audio: Path | None) -> dict[str, dance.Move | dance.Routine]:
    """Every preset move a standing dancer can dance, on its own (the reference stands), and, with ``audio``, a
    standing routine ``choreograph`` makes for the song."""
    standing = ("feet", "either")
    found: dict[str, dance.Move | dance.Routine] = {n: m for n, m in dance.moves().items() if m.support in standing}
    if audio is not None:
        found["routine (choreograph, seed 7)"] = choreograph.choreograph_track(audio, groove, support="feet", seed=7)
    return found


def check_all(
    style: dance_style.DanceStyle, groove: music.Groove, *, bars: int, fps: int, audio: Path | None = None
) -> dict:
    """Each candidate's score and misses, the closest first, and the misses they share, ranked."""
    results = []
    for name, source in candidates(groove, audio).items():
        bars_danced = bars if isinstance(source, dance.Move) else source.track_bars
        frames = list(dance.frames(source, groove, groove.at(0), groove.at(bars_danced), fps))
        found = dance_style.check(style, frames, groove, fps)
        results.append(
            {
                "name": name,
                "support": source.support,
                "score": found.score,
                "misses": [
                    {
                        "channel": m.channel,
                        "measure": m.measure,
                        "ours": None if m.ours is None else round(m.ours, 4),
                        "low": m.low,
                        "high": m.high,
                        "severity": m.severity,
                        # what the miss weighs by: the confidence the channel's provenance holds it at (ADR 0202), or
                        # its trust in a record older than 1.2, which stated no provenance
                        "confidence": m.trust,
                        "words": m.words,
                    }
                    for m in found.misses
                ],
            }
        )
    results.sort(key=lambda r: (r["score"], r["name"]))
    return {"style": style.name, "bars": bars, "fps": fps, "candidates": results, "shared": shared(results)}


def shared(results: Sequence[dict]) -> list[dict]:
    """The misses across candidates: how many miss each channel and measure, which way, and their mean severity over
    all candidates (a candidate that meets it adds zero), the one that matters most first."""
    tally: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for result in results:
        for miss in result["misses"]:
            tally[(miss["channel"], miss["measure"])].append(miss)
    out = []
    for (channel, measure), misses in tally.items():
        ours = [m["ours"] for m in misses if m["ours"] is not None]
        below = sum(1 for m in misses if m["ours"] is not None and m["ours"] < m["low"])
        out.append(
            {
                "channel": channel,
                "measure": measure,
                "missed_by": len(misses),
                "of": len(results),
                "below": below,
                "above": len(ours) - below,
                "none": len(misses) - len(ours),
                "low": misses[0]["low"],
                "high": misses[0]["high"],
                "ours_median": None if not ours else round(float(np.median(ours)), 4),
                "confidence": misses[0]["confidence"],
                "weight": round(sum(m["severity"] for m in misses) / max(1, len(results)), 4),
            }
        )
    return sorted(out, key=lambda m: (-m["weight"], m["channel"], m["measure"]))


# --- the page ------------------------------------------------------------------------------------------------------


Point = tuple[float, float]


@dataclass(frozen=True)
class Band:
    """One bone's twist as drawn: its axis ``start`` to ``end`` and ``half`` width, pixels; the twist's provenance;
    the stripe (None unless ``estimated-3d``) and whether it is on the half toward the camera."""

    bone: str
    provenance: str
    start: Point
    end: Point
    half: float
    colour: tuple[int, int, int]
    stripe: tuple[Point, Point] | None
    near: bool | None


def twist_bands(frame: pt.PoseFrame, width: int, height: int) -> tuple[Band, ...]:
    """Each bone twist of a found frame, placed on a ``width`` by ``height`` picture with its provenance
    (``pose_track.frame_provenance``). The neck is left out: it shares the head's axis, and its twist is never
    observed. A bone shorter than a pixel in the picture has no band."""
    picture = frame.image
    if picture is None:
        return ()
    held = pt.frame_provenance(picture, frame.world)
    index = {name: i for i, name in enumerate(pt.LANDMARKS)}

    def mean(rows: Sequence[Sequence[float]], names: tuple[str, ...], axes: int) -> tuple[float, ...]:
        return tuple(sum(rows[index[n]][k] for n in names) / len(names) for k in range(axes))

    def px(names: tuple[str, ...]) -> Point:
        x, y = mean(picture, names, 2)
        return x * width, y * height

    hips, shoulders = px(("left_hip", "right_hip")), px(("left_shoulder", "right_shoulder"))
    torso = math.dist(hips, shoulders)
    out = []
    for rule in pt.TWIST_RULES:
        if rule.bone == "neck":
            continue
        start, end = px(rule.axis[0]), px(rule.axis[1])
        length = math.dist(start, end)
        if length < 1.0:
            continue
        half = max(3.0, HALF.get(rule.bone, LIMB_HALF) * torso)
        provenance = held.twists[rule.bone].provenance
        colour = _side_colour(rule.bone) if provenance == pt.ESTIMATED_3D else GREY
        stripe, near = None, None
        if provenance == pt.ESTIMATED_3D and frame.world is not None and rule.across is not None:
            a0, a1 = mean(frame.world, rule.axis[0], 3), mean(frame.world, rule.axis[1], 3)
            c0, c1 = mean(frame.world, rule.across[0], 3), mean(frame.world, rule.across[1], 3)
            axis = np.subtract(a1, a0) / np.linalg.norm(np.subtract(a1, a0))
            across = np.subtract(c1, c0)
            across = across - axis * float(across @ axis)
            across = across / np.linalg.norm(across)  # estimated-3d: its part across the bone is well above noise
            normal = (-(end[1] - start[1]) / length, (end[0] - start[0]) / length)
            shift = half * float(across[0] * normal[0] + across[1] * normal[1])
            ends = [(start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f) for f in STRIPE_SPAN]
            stripe = (
                (ends[0][0] + normal[0] * shift, ends[0][1] + normal[1] * shift),
                (ends[1][0] + normal[0] * shift, ends[1][1] + normal[1] * shift),
            )
            near = bool(across[2] <= 0.0)  # the world's z runs away from the camera
        out.append(Band(rule.bone, provenance, start, end, half, colour, stripe, near))
    return tuple(out)


def _side_colour(bone: str) -> tuple[int, int, int]:
    return LEFT if bone.startswith("left") else RIGHT if bone.startswith("right") else TRUNK


def _legend_font(size: int) -> tuple[ImageFont.ImageFont | ImageFont.FreeTypeFont, bool]:
    """The legend's font and whether it has the accents: the pinned font when ``SRSTUDIO_FONTS`` names its folder,
    else Pillow's own, which has none, so the words lose theirs rather than show empty boxes."""
    folder = os.environ.get("SRSTUDIO_FONTS")
    if folder and (Path(folder) / LEGEND_FONT).is_file():
        return ImageFont.truetype(str(Path(folder) / LEGEND_FONT), size), True
    return ImageFont.load_default(size=size), False


def _plain_words(words: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", words) if not unicodedata.combining(c))


def legend_height(height: int) -> int:
    """The strip the legend takes at the bottom of a ``height`` frame, pixels."""
    return len(LEGEND_PT) * _legend_size(height) * 3 // 2 + _legend_size(height)


def _legend_size(height: int) -> int:
    return max(11, height // 52)


def _dashed(canvas: np.ndarray, a: Point, b: Point, colour: tuple[int, int, int], thickness: int) -> None:
    length = math.dist(a, b)
    on, off = DASH_PX
    at = 0.0
    while at < length:
        stop = min(length, at + on)
        p = (a[0] + (b[0] - a[0]) * at / length, a[1] + (b[1] - a[1]) * at / length)
        q = (a[0] + (b[0] - a[0]) * stop / length, a[1] + (b[1] - a[1]) * stop / length)
        cv2.line(canvas, _px_abs(p), _px_abs(q), colour, thickness, cv2.LINE_AA)
        at = stop + off


def _px_abs(point: Point) -> tuple[int, int]:
    return int(round(point[0])), int(round(point[1]))


def _legend(canvas: np.ndarray) -> np.ndarray:
    height, width = canvas.shape[:2]
    size = _legend_size(height)
    top = height - legend_height(height)
    picture = Image.fromarray(np.ascontiguousarray(canvas[:, :, ::-1]))
    draw = ImageDraw.Draw(picture)
    draw.rectangle((0, top, width, height), fill=(BACKGROUND,) * 3)
    font, accents = _legend_font(size)
    swatch = {pt.MEASURED_2D: MID, pt.ESTIMATED_3D: TRUNK, pt.UNOBSERVED: GREY, "hidden": FAINT}
    for row, (key, words) in enumerate(LEGEND_PT.items()):
        y = top + size // 2 + row * size * 3 // 2
        b, g, r = swatch[key]
        draw.rectangle((size // 2, y + size // 4, size * 2, y + size * 3 // 4), fill=(r, g, b))
        draw.text((size * 5 // 2, y), words if accents else _plain_words(words), fill=STRIPE, font=font)
    return np.asarray(picture)[:, :, ::-1].copy()


def skeleton_frame(frame: pt.PoseFrame, width: int, height: int) -> np.ndarray:
    """The dancer's skeleton drawn on a dark frame (BGR), each bone twist by its provenance and a legend saying how;
    a lost frame says so."""
    canvas = np.full((height, width, 3), BACKGROUND, np.uint8)
    if frame.image is None:
        cv2.putText(canvas, "perdido", (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, FAINT, 2, cv2.LINE_AA)
        return canvas
    bands = twist_bands(frame, width, height)
    cover = canvas.copy()
    for band in bands:
        thick = max(1, int(round(2 * band.half)))
        cv2.line(cover, _px_abs(band.start), _px_abs(band.end), band.colour, thick, cv2.LINE_8)
    canvas = cv2.addWeighted(cover, BAND_ALPHA, canvas, 1 - BAND_ALPHA, 0.0)
    at = {name: frame.image[i] for i, name in enumerate(pt.LANDMARKS)}
    for a, b in BONES_2D:
        pa, pb = at[a], at[b]
        colour = (
            LEFT
            if a.startswith("left") and b.startswith("left")
            else RIGHT
            if a.startswith("right") and b.startswith("right")
            else MID
        )
        if min(pa[3], pb[3]) < SEEN:
            colour = FAINT
        cv2.line(canvas, _px(pa, width, height), _px(pb, width, height), colour, 4, cv2.LINE_AA)
    ears = [at["left_ear"], at["right_ear"]]
    head = ((ears[0][0] + ears[1][0]) / 2, (ears[0][1] + ears[1][1]) / 2)
    radius = max(6, int(abs(ears[0][0] - ears[1][0]) * width * 0.8))
    cv2.circle(canvas, _px(head, width, height), radius, MID, 3, cv2.LINE_AA)
    for band in bands:
        if band.stripe is not None:
            if band.near:
                cv2.line(canvas, _px_abs(band.stripe[0]), _px_abs(band.stripe[1]), STRIPE, 3, cv2.LINE_AA)
            else:
                _dashed(canvas, band.stripe[0], band.stripe[1], STRIPE, 2)
    return _legend(canvas)


def _px(point: Sequence[float], width: int, height: int) -> tuple[int, int]:
    return int(round(point[0] * width)), int(round(point[1] * height))


def shown_frames(track: pt.PoseTrack) -> dict[int, pt.PoseFrame]:
    """The frame drawn for each frame index: a frame that repeats the last distinct picture (ADR 0204) draws that
    picture's frame, since it holds no landmarks of its own and its dancer was not lost."""
    out: dict[int, pt.PoseFrame] = {}
    last: pt.PoseFrame | None = None
    for frame in track.frames:
        if not frame.repeat or last is None:
            last = frame
        out[frame.index] = last
    return out


def skeleton_video(track: pt.PoseTrack, video: Path, out: Path) -> Path:  # pragma: no cover - ffmpeg and the footage
    """The footage beside the dancer's skeleton, with the footage's sound."""
    capture = cv2.VideoCapture(str(video))
    width, height = track.source.width, track.source.height
    side = (width * 2 + 1) // 2 * 2, height // 2 * 2
    out = private(out)
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{side[0]}x{side[1]}",
        "-r", str(track.fps), "-i", "-", "-i", str(video), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-crf", "23", "-c:a", "aac", "-shortest", str(out),
    ]  # fmt: skip
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    frames = shown_frames(track)
    index = 0
    while True:
        ok, bgr = capture.read()
        if not ok:
            break
        frame = frames.get(index)
        drawn = skeleton_frame(frame, width, height) if frame else np.full_like(bgr, 24)
        encoder.stdin.write(np.hstack([bgr, drawn])[: side[1], : side[0]].tobytes())
        index += 1
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise StudyError("ffmpeg could not write the skeleton video")
    os.chmod(out, 0o600)
    return out


LABELS = {
    "hips.bounce": "quique do quadril (altura do quadril sobre o tornozelo mais baixo)",
    "knees.bend": "dobra dos joelhos",
    "torso.lean": "inclinação do tronco para frente e para trás",
    "torso.roll": "inclinação do tronco para os lados",
    "torso.twist": "giro dos ombros sobre o quadril",
    "shoulders.tilt": "ombros inclinados em relação ao quadril",
    "head.bob": "cabeça subindo e descendo sobre os ombros",
    "head.sway": "cabeça indo para os lados",
    "arms.height": "altura das mãos acima dos ombros",
    "arms.reach": "braço esticado (1 = todo esticado)",
    "hands.travel": "caminho das mãos em volta do quadril, por batida",
    "feet.travel": "caminho dos pés em volta do quadril, por batida",
    "stance.width": "abertura das pernas (distância entre os tornozelos)",
}
UNITS = {"head_radii": "raios de cabeça", "rad": "graus", "ratio": "", "head_radii_per_beat": "raios de cabeça/batida"}
TRUST_PT = {"good": "boa", "fair": "média", "poor": "fraca"}
PROVENANCE_PT = {
    pt.MEASURED_2D: "medido na imagem (2D)",
    pt.ESTIMATED_3D: "estimado em 3D",
    pt.UNOBSERVED: "não observado",
}
UNSTATED_PT = "não registrada (registro anterior à versão 1.2)"
MEASURE_PT = {
    "level": "valor típico",
    "peak_to_peak": "tamanho do balanço",
    "range": "quanto percorre em 8 tempos",
    "cycles_per_beat": "ciclos por batida",
    "snap_ratio": "subida/descida",
    "hit_offset": "acento antes(−)/depois(+) da batida",
    "lag": "atraso",
    "peak_speed_phase": "momento mais rápido (fração do ciclo depois do acento)",
    "attack": "chegada ao acento (batidas)",
    "release": "saída do acento (batidas)",
    "peak_acceleration": "aceleração máxima (amplitudes por batida²)",
    "profile_distance": "diferença do perfil de velocidade",
}


def _num(value: float | None, unit: str = "") -> str:
    if value is None:
        return "—"
    if unit == "rad":
        return f"{math.degrees(value):.0f}°"
    return f"{value:.2f}".replace(".", ",")


def _span(span: tuple[float, float] | None, unit: str = "") -> str:
    if span is None:
        return "sem dados suficientes"
    if unit == "rad":
        return f"{math.degrees(span[0]):.0f}° a {math.degrees(span[1]):.0f}°"
    return f"{_num(span[0])} a {_num(span[1])}"


def _gesture(c: dance_style.ChannelTarget) -> str:
    """The channel's gesture timing in words, or how many windows read more than a sine when too few did."""
    timed = c.evidence.get("timed", 0)
    if c.attack is None or c.release is None:
        return f"sem dados suficientes ({timed} janelas com mais que um seno)"
    profile = "perfil medido" if c.velocity is not None else "janelas discordam do perfil"
    return f"chegada {_span(c.attack)}, saída {_span(c.release)} batidas; {profile} ({timed} janelas)"


def page(style: dance_style.DanceStyle, findings: dict, *, footage: str | None, views: str | None, closest: str) -> str:
    """The proof page, standalone HTML in Portuguese."""
    e = html.escape
    ref = style.reference
    rows = []
    for c in style.channels:
        unit = c.unit
        rows.append(
            "<tr>"
            f"<td><b>{e(c.name)}</b><br><small>{e(LABELS[c.name])}</small></td>"
            f"<td>{UNSTATED_PT if c.provenance is None else PROVENANCE_PT[c.provenance]}</td>"
            f"<td>{'—' if c.held is None else TRUST_PT[c.held]}</td>"
            f"<td>{_span(c.level, unit)}</td>"
            f"<td>{_span(c.peak_to_peak, unit)}</td>"
            f"<td>{_span(c.cycles_per_beat)}</td>"
            f"<td>{_span(c.hit_offset)}</td>"
            f"<td>{_span(c.snap_ratio)}</td>"
            f"<td>{_num(c.noise, unit)}</td>"
            f"<td>{c.evidence['read']}/{c.evidence['windows']}</td>"
            f"<td>{_gesture(c)}</td>"
            "</tr>"
        )
    lags = "".join(
        f"<tr><td>{e(g.lead)} → {e(g.follow)}</td><td>{_span(g.beats)}</td>"
        f"<td>{g.evidence['read']}/{g.evidence['windows']}</td></tr>"
        for g in style.lags
    )
    ranking = "".join(
        f"<tr><td>{i + 1}</td><td>{e(r['name'])}</td><td>{e(r['support'])}</td><td>{_num(r['score'])}</td>"
        f"<td>{len(r['misses'])}</td></tr>"
        for i, r in enumerate(findings["candidates"])
    )
    misses = "".join(
        f"<tr><td>{e(m['channel'])}</td><td>{MEASURE_PT[m['measure']]}</td>"
        f"<td>{m['missed_by']} de {m['of']}</td>"
        f"<td>{_explain(m)}</td><td>{TRUST_PT[m['confidence']]}</td><td>{_num(m['weight'])}</td></tr>"
        for m in findings["shared"][:15]
    )
    unmeasured = "".join(f"<li><b>{e(k)}</b>: {e(_UNMEASURED_PT.get(k, v))}</li>" for k, v in style.unmeasured.items())
    rejected = ref.rejected
    video = (
        f'<video controls preload="metadata" src="{e(footage)}"></video>'
        if footage
        else "<p>O vídeo lado a lado não foi gerado.</p>"
    )
    plane = f'<video controls preload="metadata" src="{e(views)}"></video>' if views else ""
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estudo de dança</title>
<style>
:root {{ --bg: #f7f7f5; --fg: #1c1c1c; --muted: #666; --line: #ddd; --accent: #b3261e; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #17181b; --fg: #eee; --muted: #aaa; --line: #333; --accent: #ff8a80; }}
}}
body {{ background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif;
  margin: 0 auto; max-width: 1100px; padding: 16px; }}
h1, h2 {{ line-height: 1.2; }} small, .muted {{ color: var(--muted); }}
video {{ width: 100%; max-width: 1100px; background: #000; }}
.table {{ overflow-x: auto; }} table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
td, th {{ border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }}
.note {{ border-left: 4px solid var(--accent); padding: 4px 12px; }}
</style></head><body>
<h1>Estudo de dança: o que a aula de hip-hop faz e os nossos bonecos não</h1>
<p class="note">Página local, só para você. Ela mostra a gravação de pessoas reais: não publique,
não envie ao Drive nem ao Slack. No repositório entram só os números do estilo, nunca imagens nem o
esqueleto quadro a quadro.</p>

<h2>1. A gravação e o esqueleto extraído</h2>
<p>À esquerda, a gravação. À direita, o esqueleto da dançarina do centro, como o estimador de pose
({e(ref.estimator)} {e(ref.estimator_version)}) o leu. Azul é o lado direito dela, laranja o esquerdo,
cinza o que ele viu com pouca confiança; “perdido” é um quadro em que a dançarina não foi encontrada
com segurança.</p>
<p>O esqueleto separa o que a imagem mede do que o estimador deduz. A posição de cada ponto na imagem é
medida (linha cheia). O giro de um osso em torno do próprio eixo não aparece na imagem: quando os pontos
em volta permitem, o estimador o deduz em 3D (faixa colorida com uma listra na direção de onde o giro foi
lido, cheia quando essa direção aponta para a câmera e tracejada quando aponta para longe; verde no
tronco e na cabeça); quando não
permitem, o giro fica não observado (faixa cinza, sem listra). A legenda no pé do quadro repete isso.</p>
{video}
<p class="muted">{ref.frames} quadros ({_num(ref.seconds)} s). Usados: {ref.used}. Recusados:
{rejected["lost"]} perdidos ou trocados por outra pessoa, {rejected["low_confidence"]} com quadril ou
ombro mal vistos, {rejected["implausible"]} com osso de tamanho impossível, {rejected["jump"]} com um
ponto que pulou longe demais. Em {rejected["arm"]} quadros só um braço foi descartado. Nada foi
preenchido: cada medida usa só os quadros vistos.</p>

<h2>2. O estilo medido</h2>
<p>Música a {_num(ref.bpm)} batidas por minuto, compasso de {ref.beats_per_bar}. Tamanhos em
<b>raios de cabeça</b> de um corpo de proporções reais (medidos pelo tronco, então a distância da câmera
não conta); ângulos em graus. Cada medida é uma faixa: a metade do meio das janelas de 8 tempos,
alargada pelo ruído da estimativa. “Origem” diz de onde a medida vem: da posição medida na imagem ou da
estimativa 3D do estimador. “Confiança” diz o quanto a câmera e a profundidade podem enganar aquela
medida; o que vem da estimativa 3D fica no máximo em “média”, e uma falta pesa conforme essa confiança.</p>
<div class="table"><table>
<tr><th>Canal</th><th>Origem</th><th>Confiança</th><th>Valor típico</th><th>Tamanho do balanço</th>
<th>Ciclos por batida</th><th>Acento (batidas)</th><th>Subida/descida</th><th>Ruído por quadro</th>
<th>Janelas lidas</th><th>Tempo do gesto</th></tr>
{"".join(rows)}
</table></div>
<h3>Atrasos em cadeia (quanto uma parte se mexe depois da outra, em batidas)</h3>
<div class="table"><table><tr><th>De → para</th><th>Atraso</th><th>Janelas lidas</th></tr>
{lags}</table></div>
<h3>O que não dá para medir nesta gravação</h3><ul>{unmeasured}</ul>

<h2>3. Os nossos movimentos contra a referência</h2>
<p>Cada movimento pronto dançou {findings["bars"]} compassos no esqueleto realista, na mesma batida,
e foi medido com o mesmo código. Nota menor é mais perto do estilo.</p>
<div class="table"><table>
<tr><th>#</th><th>Movimento</th><th>Apoio</th><th>Nota</th><th>Faltas</th></tr>
{ranking}</table></div>
<h3>O que quase todos erram, do mais importante para o menos</h3>
<div class="table"><table>
<tr><th>Canal</th><th>Medida</th><th>Erram</th><th>Como</th><th>Confiança</th><th>Peso</th></tr>
{misses}</table></div>

<h2>4. O mais próximo, nas três vistas</h2>
<p>“{e(closest)}” nas vistas de frente, de lado e de cima, nos três tipos de corpo, só ossos.</p>
{plane}
<p class="muted">Gerado por {e(TOOL)} ({e(MODEL)}).</p>
</body></html>
"""


_UNMEASURED_PT = {
    "root.travel": "o caminho do quadril no chão. A câmera acompanha a dançarina, e o estimador mede tudo a partir do "
    "quadril, então nada na imagem fica parado no chão para servir de régua."
}


def _explain(miss: dict) -> str:
    low, high, ours = miss["low"], miss["high"], miss["ours_median"]
    unit = "rad" if miss["channel"] in _RAD and miss["measure"] in ("level", "peak_to_peak", "range") else ""
    parts = []
    if miss["below"]:
        parts.append(f"{miss['below']} abaixo")
    if miss["above"]:
        parts.append(f"{miss['above']} acima")
    if miss["none"]:
        parts.append(f"{miss['none']} sem ciclo nenhum")
    caveat = _CAVEATS_PT.get((miss["channel"], miss["measure"]), "")
    return f"referência {_span((low, high), unit)}; nossos ~{_num(ours, unit)} ({', '.join(parts)}){caveat}"


_RAD = {"knees.bend", "torso.lean", "torso.roll", "torso.twist", "shoulders.tilt"}
_CAVEATS_PT = {  # misses that are partly how the estimator places a point, not how the dancer moves
    ("head.bob", "level"): ". Em parte é onde o estimador põe a cabeça (entre as orelhas): não é meta."
}


def views_video(move: str, bpm: float, out: Path) -> Path:  # pragma: no cover - renders with tools/dance_views.py
    out = private(out)
    command = [sys.executable, str(REPO / "tools" / "dance_views.py"), str(out), "--moves", move, "--bars-each", "4",
               "--bpm", f"{bpm}", "--fps", "25"]  # fmt: skip
    subprocess.run(command, check=True, env=os.environ | {"PYTHONPATH": str(REPO / "src")})
    os.chmod(out, 0o600)
    return out


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - the command line
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure")
    m.add_argument("track", type=Path)
    m.add_argument("--audio", type=Path)
    m.add_argument("--bpm", type=float)
    m.add_argument("--offset", type=float)
    m.add_argument("--name", required=True)
    m.add_argument("--description", required=True)
    m.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("check")
    c.add_argument("style", type=Path)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--bars", type=int, default=8)
    c.add_argument("--fps", type=int, default=30)
    c.add_argument("--audio", type=Path)
    p = sub.add_parser("page")
    p.add_argument("track", type=Path)
    p.add_argument("style", type=Path)
    p.add_argument("findings", type=Path)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.command == "measure":
        track = pt.load(args.track)
        style = measure(track, grid(args.audio, args.bpm, args.offset), name=args.name, description=args.description)
        out = args.out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(dance_style.dump_style(style))
        out.chmod(0o644)  # numbers only, committed: readable like the rest of the repository
        print(out)
    elif args.command == "check":
        style = dance_style.load_style(args.style)
        ref = style.reference
        groove = music.Groove(ref.bpm, ref.beats_per_bar, ref.offset_s)
        found = check_all(style, groove, bars=args.bars, fps=args.fps, audio=args.audio)
        print(write_private(args.out, json.dumps(found, indent=1, ensure_ascii=False)))
    else:
        track, style = pt.load(args.track), dance_style.load_style(args.style)
        findings = json.loads(args.findings.read_text())
        out = args.out.resolve()
        out.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(out, 0o700)
        skeleton_video(track, args.video, out / "skeleton.mp4")
        closest = next(r["name"] for r in findings["candidates"] if r["name"] in dance.moves())
        views_video(closest, style.reference.bpm, out / "views.mp4")
        text = page(style, findings, footage="skeleton.mp4", views="views.mp4", closest=closest)
        print(write_private(out / "index.html", text))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
