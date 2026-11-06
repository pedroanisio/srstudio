"""Build local review boards and an unapproved animated proof; never publish.

Run with PYTHONPATH pointing to this checkout. All temporary output belongs in
--scratch; --out contains only the review media and a standalone HTML index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sr_core.scene import Scene

from srstudio import gpu, plates, rafa, rafa_host
from srstudio import visor_chibi as vc
from srstudio import visor_chibi_host as host
from srstudio.canvas import Canvas
from srstudio.layout import VERTICAL


def run(engine: Path, fonts: Path, out: Path, scratch: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(fonts / 'dm-sans-700.ttf'), 24)
    title = ImageFont.truetype(str(fonts / 'dm-sans-700.ttf'), 34)
    started = time.monotonic()

    def render(plate: plates.Plate) -> Path:
        path = plates.render(plate, engine=engine, cache=scratch / 'plates', fonts=fonts)
        if any(m.material == 'visor' for placed in plate.placed for m in placed.meshes):
            path = host.finish_plate(path, plate)
        print(f'plate {path.name}: elapsed {time.monotonic() - started:.1f}s', flush=True)
        return path

    def board(name: str, labels: tuple[str, ...], pictures: list[Path], *, cols: int, size: tuple[int, int]) -> None:
        w, h = size
        rows = (len(labels) + cols - 1) // cols
        sheet = Image.new('RGB', (w * cols, (h + 52) * rows + 88), '#282D35')
        draw = ImageDraw.Draw(sheet)
        draw.text((26, 20), f'VISOR / {name.upper()} / PROPOSED', font=title, fill='#F4F0E6')
        for i, (label, path) in enumerate(zip(labels, pictures, strict=True)):
            x, y = i % cols * w, 88 + i // cols * (h + 52)
            image = Image.open(path).convert('RGBA').resize((w, h), Image.Resampling.LANCZOS)
            sheet.paste(image, (x, y), image)
            draw.text((x + w / 2, y + h + 10), label.replace('_', ' '), font=font, anchor='mt', fill='#F4F0E6')
        sheet.save(out / f'{name}.png')

    expressions = [render(vc.plate(face=vc.Face(e), head_only=True, width=512, height=512)) for e in vc.EYES]
    board('expressions', vc.EYES, expressions, cols=4, size=(512, 512))
    gazes = [
        expressions[0],
        *(render(vc.plate(face=vc.Face(gaze=g), head_only=True, width=512, height=512)) for g in vc.GAZES[1:]),
    ]
    board('gaze', vc.GAZES, gazes, cols=5, size=(400, 400))
    poses = [render(vc.plate(vc.pose(p), width=540, height=960)) for p in vc.POSES]
    board('poses', vc.POSES, poses, cols=6, size=(360, 640))
    # Same lens, output scale, world units and sole plane for both characters.
    # Use Rafa's canonical pressed skull/mouth pairing. The software adapter
    # cannot bind his complete primitive buffer, so keep geometry intact and
    # path-trace body and head separately through exactly the same camera.
    whole = replace(
        rafa_host._whole(rafa.Face()),
        width=540,
        height=960,
        camera=vc.CAMERA,
        lights=plates.stage_lights(warm=False, rim=True),
    )
    palette = {m.id: m for m in whole.materials}
    rafa_image = Image.new('RGBA', (540, 960))
    for placed in whole.placed:
        print('Rafa pass triangles:', sum(len(mesh.triangles) for mesh in placed.meshes), flush=True)
        picture = render(replace(whole, placed=(placed,), materials=plates.materials_of(placed.meshes, palette)))
        rafa_image.alpha_composite(Image.open(picture).convert('RGBA'))
    rafa_picture = scratch / 'rafa-lineup.png'
    rafa_image.save(rafa_picture)
    lineup = Image.new('RGB', (2160, 1080), '#E8E7E3')
    draw = ImageDraw.Draw(lineup)
    draw.text((28, 20), 'SAME WORLD SCALE / RAFA + VISOR / PROPOSED', font=title, fill='#252A33')
    for col, path in enumerate((rafa_picture, poses[0], rafa_picture, poses[0])):
        img = Image.open(path).convert('RGBA').resize((540, 960), Image.Resampling.LANCZOS)
        if col >= 2:
            alpha = img.getchannel('A').point(lambda value: 255 if value >= 128 else 0)
            img = Image.new('RGBA', img.size, '#000000')
            img.putalpha(alpha)
        lineup.paste(img, (col * 540, 80), img)
        draw.text(
            (col * 540 + 270, 1040),
            ('Rafa', 'Visor', 'Rafa silhouette', 'Visor silhouette')[col],
            anchor='mt',
            font=font,
            fill='#252A33',
        )
    lineup.save(out / 'lineup.png')
    rows = host.proof_frames()
    made = {}
    for n, frame in enumerate(dict.fromkeys(rows)):
        made[frame] = render(host.stage(frame))
        print(f'video state {n + 1}/{len(set(rows))}', flush=True)
    scene = Scene(version='auto')
    project = scene.add_project(
        width=host.WIDTH,
        height=host.HEIGHT,
        fps=str(host.FPS),
        duration=host.duration(rows),
        background='#353941',
        quality='final',
    )
    VERTICAL.declare(scene, project)
    cv = Canvas(scene, held_frames=True)
    host.perform(cv, cv.comp, rows, made, scratch)
    source = scratch / 'proof.scene.xml'
    source.write_bytes(scene.to_bytes(layout='pretty'))
    with gpu.held():
        subprocess.run(
            [
                str(engine),
                'encode',
                str(source),
                '--hw',
                'software',
                '--parallel',
                '1',
                '--no-upload',
                '-o',
                str(out / 'proof.mp4'),
            ],
            cwd=scratch,
            check=True,
        )
    # Full-size review stills extracted from the encoded artifact itself.
    for at in (0, 29 / 30, 2.5, 4.5, 6.5):
        subprocess.run(
            [
                'ffmpeg',
                '-hide_banner',
                '-loglevel',
                'error',
                '-y',
                '-ss',
                str(at),
                '-i',
                str(out / 'proof.mp4'),
                '-frames:v',
                '1',
                str(scratch / f'review-{at:.3f}.png'),
            ],
            check=True,
        )
    # Phone-size blink comparison is a review aid, not an alternate proof plate.
    phone = Image.new('RGB', (720, 640), '#353941')
    for col, i in enumerate((28, 29)):
        img = Image.open(made[rows[i]]).resize((360, 640), Image.Resampling.LANCZOS)
        phone.paste(img, (360 * col, 0))
    phone.save(scratch / 'phone-blink.png')
    timeline = [
        {
            'frame': i,
            'eyes': f.face.eyes,
            'gaze': f.face.gaze,
            'rotations': {name.value: list(angles) for name, angles in f.pose.rotations},
        }
        for i, f in enumerate(rows)
    ]
    (scratch / 'timeline.json').write_text(json.dumps(timeline, indent=2) + '\n')
    (out / 'index.html').write_text('''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visor chibi — proposed clay rig</title>
<style>body{margin:auto;max-width:1300px;padding:32px;background:#20252d;color:#f4f0e6;font:18px system-ui}
h1{font-size:40px}p{line-height:1.5}figure{margin:40px 0}img{width:100%;height:auto}
video{width:min(100%,450px);display:block;margin:auto}a{color:#b5d9f5}figcaption{margin:12px 0}</style>
<h1>Visor chibi <small>· proposed</small></h1>
<p>A clay puppet with white armor over a black suit, a dark glossy visor and glowing white eye shapes.
Inspired design under videos.op.inspired.001. Look approval is pending arc4d3's review of this animation.
There is no approval record.</p>
<video controls loop playsinline preload="metadata" src="proof.mp4"></video>
<p>Neutral → presenting → wave → hands on hips. Head turns, gaze changes, four expressions and closed-frame blinks.
Plain studio; no audio. Replacement clay plates composited on the host clock.</p>
<figure><figcaption>Every eye expression · one neutral head and one scale</figcaption>
<img src="expressions.png"
alt="Neutral, blink, suspicious, surprised, smug, happy, sad and angry visor eyes"></figure>
<figure><figcaption>Every gaze · one neutral expression</figcaption>
<img src="gaze.png" alt="Ahead, left, right, up and down"></figure>
<figure><figcaption>Every named pose · fixed lens, world scale and sole baseline</figcaption>
<img src="poses.png"
alt="Neutral, presenting, hands on hips, wave, shrug and point"></figure>
<figure><figcaption>Rafa and Visor · same world units, lens, baseline and scale, then filled silhouettes</figcaption>
<img src="lineup.png" alt="Rafa beside Visor, in clay and in black silhouette"></figure>
<details><summary>Source reference</summary><img src="reference.png" alt="Supplied armored chibi reference"></details>
<p>Differences retained for review: fewer armor seams and simpler glove articulation;
the reference has more finely sculpted compound curves and finger poses.
The animated transitions use discrete replacement poses.</p>
<p>Rafa's body and head are path-traced in separate passes through this same camera to fit the software adapter's
primitive-buffer limit. World scale is preserved; shadows between those passes are absent.</p></html>''')
    names = ('expressions.png', 'gaze.png', 'poses.png', 'lineup.png', 'proof.mp4', 'index.html')
    manifest = {
        name: {'sha256': hashlib.sha256((out / name).read_bytes()).hexdigest(), 'bytes': (out / name).stat().st_size}
        for name in names
    }
    (scratch / 'proof-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2), flush=True)
    print(f'Proof build seconds: {time.monotonic() - started:.1f}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--fonts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    run(args.engine.resolve(), args.fonts.resolve(), args.out.resolve(), args.scratch.resolve())
