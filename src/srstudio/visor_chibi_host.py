"""Replacement plates on the host clock for the proposed visor chibi.

A frame is a typed rig pose and visor state. Only unique states are path-traced;
the timeline gates the resulting plates, including single-frame blinks.
"""

from __future__ import annotations

import math
import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import clay, plates
from . import visor_chibi as vc
from .canvas import Canvas

FPS, WIDTH, HEIGHT = 30, 1080, 1920


@dataclass(frozen=True)
class Frame:
    pose: vc.Pose = vc.REST
    face: vc.Face = vc.REST_FACE


def _blend(a: vc.Pose, b: vc.Pose, share: float) -> vc.Pose:
    first, last = dict(a.rotations), dict(b.rotations)
    blended: dict[str, vc.Point] = {}
    for joint in first.keys() | last.keys():
        x, y, z = first.get(joint, (0, 0, 0))
        xx, yy, zz = last.get(joint, (0, 0, 0))
        blended[joint.value] = (x + (xx - x) * share, y + (yy - y) * share, z + (zz - z) * share)
    return vc.Pose(blended)


def proof_frames() -> tuple[Frame, ...]:
    """Authored studio performance: finite plate steps with held landing poses."""
    rows = []
    beats = ('neutral', 'presenting', 'wave', 'hands_on_hips')
    for i in range(8 * FPS):
        t = i / FPS
        beat = min(3, int(t // 2))
        target = vc.pose(beats[beat])
        if beat and t % 2 < 0.4:
            # Four replacement inbetweens, on threes; the landing then holds.
            share = min(1.0, (int((t % 2) * 10) + 1) / 4)
            target = _blend(vc.pose(beats[beat - 1]), target, share)
            if beat == 3 and share < 1:
                # Fold through an upward arc: the linear elbow crossing would
                # briefly straighten the hand beyond the portrait frame.
                rotations = dict(target.rotations)
                x, y, z = rotations[vc.JointName.RIGHT_SHOULDER]
                rotations[vc.JointName.RIGHT_SHOULDER] = (x, y, z - 60 * math.sin(math.pi * share))
                target = vc.Pose(rotations)
        turn = (0, -12, 12, 0)[beat]
        nod = (0, -3, 0, 3)[beat]
        angles = dict(target.rotations)
        angles[vc.JointName.HEAD] = (nod, turn, 0)
        if beat == 2 and t % 2 >= 0.4:
            # The wrist waves without changing forearm length.
            angles[vc.JointName.RIGHT_WRIST] = (0, 0, -8 + (12 if int(t * 4) % 2 else -12))
        state = ('neutral', 'surprised', 'happy', 'smug')[beat]
        gaze = ('ahead', 'left', 'right', 'down')[beat]
        if i in (29, 83, 145, 207):
            state = 'blink'
        rows.append(Frame(vc.Pose(angles), vc.Face(state, gaze)))
    return tuple(rows)


def stage(frame: Frame) -> plates.Plate:
    """A plain studio with a real floor and contact shadow, under a fixed lens."""
    floor = clay.Model()
    # A continuous floor curves into the wall; no horizon crosses the puppet.
    theta = np.linspace(0, math.pi / 2, 40)
    y = np.r_[0, -350 * (1 - np.cos(theta)), -2000]
    z = np.r_[-2000, 300 + 350 * np.sin(theta), 650]
    normals = np.vstack(
        ((0, -1, 0), np.stack((np.zeros_like(theta), -np.cos(theta), -np.sin(theta)), axis=1), (0, 0, -1))
    )
    vertices = np.array([(x, yy, zz) for yy, zz in zip(y, z, strict=True) for x in (-2000, 2000)])
    tris = [t for i in range(len(y) - 1) for t in ((2 * i, 2 * i + 1, 2 * i + 3), (2 * i, 2 * i + 3, 2 * i + 2))]
    floor.surface('studio', vertices, np.repeat(normals, 2, axis=0), tris)
    used = vc.meshes(frame.pose, frame.face)
    return plates.Plate(
        WIDTH,
        HEIGHT,
        vc.CAMERA,
        plates.stage_lights(warm=False, rim=True),
        (plates.Placed(used), plates.Placed(floor.meshes())),
        (*plates.materials_of(used, vc.geometry.MATERIALS), plates.Material('studio', '#40434B', roughness=0.85)),
        '#353941',
        samples=16,
    )


def finish_plate(source: Path, drawing: plates.Plate) -> Path:
    """Composite warm optical bloom from visible emissive eye pixels only.

    Projecting the actual head-transformed triangles keeps the halo tied to the
    rig, excludes white armor, and preserves the path-traced silhouette alpha.
    """
    from PIL import Image, ImageDraw, ImageFilter

    from .rafa_host import project

    target = source.with_name(source.stem + '-eye-bloom-v1.png')
    if target.exists():
        return target
    image = Image.open(source).convert('RGBA')
    rgba = np.array(image)
    mask = Image.new('L', image.size)
    pen = ImageDraw.Draw(mask)
    for placed in drawing.placed:
        for mesh in placed.meshes:
            if mesh.material != 'eye':
                continue
            xy = project(mesh.vertices, lens=drawing.camera, width=image.width, height=image.height)
            for triangle in mesh.triangles:
                pen.polygon([tuple(point) for point in xy[triangle]], fill=255)
    visible = (np.array(mask) > 0) & (rgba[:, :, :3].min(axis=2) > 200) & (rgba[:, :, 3] > 0)
    glow = Image.fromarray(visible.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(max(1, image.width / 120)))
    rgb = rgba[:, :, :3].astype(float)
    rgb += np.array(glow)[:, :, None] * np.array((0.65, 0.48, 0.25))
    rgb[visible] = (255, 247, 228)
    rgba[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    Image.fromarray(rgba).save(target)
    return target


def sheet(rows: Sequence[Frame], *, engine: Path, cache: Path, fonts: Path) -> dict[Frame, Path]:
    made = {}
    for frame in dict.fromkeys(rows):
        drawing = stage(frame)
        made[frame] = finish_plate(plates.render(drawing, engine=engine, cache=cache, fonts=fonts), drawing)
    return made


def perform(cv: Canvas, parent, rows: Sequence[Frame], made: Mapping[Frame, Path], root: Path) -> None:
    """Gate the cached pictures on the host's frame clock; no new rendering."""
    folder = root / 'assets' / 'visor-chibi'
    folder.mkdir(parents=True, exist_ok=True)
    for n, frame in enumerate(dict.fromkeys(rows)):
        if frame not in made:
            raise vc.VisorChibiError('missing plate for a requested frame')
        source = made[frame]
        target = folder / source.name
        if not target.exists():
            try:
                os.link(source, target)
            except OSError:
                shutil.copyfile(source, target)
        asset = f'visor-{n}'
        cv.assets.add_image(id=asset, src=f'assets/visor-chibi/{source.name}', width=WIDTH, height=HEIGHT)
        shown = cv.group(parent, cv.uid('visor-plate'), opacity=0.0)
        spans = []
        start = None
        for i in range(len(rows) + 1):
            on = i < len(rows) and rows[i] == frame
            if on and start is None:
                start = i
            elif not on and start is not None:
                spans.append((start / FPS, i / FPS))
                start = None
        cv.gate(shown, spans)
        shown.add_layer(id=cv.uid('visor-image'), asset=asset, x=0, y=0)


def duration(rows: Sequence[Frame]) -> float:
    return math.ceil(len(rows)) / FPS
