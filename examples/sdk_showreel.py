"""Five distinct six-second studies, rendered as a thirty-second SDK demonstration.

Build native chapters with ``python -m examples.sdk_showreel OUTPUT --hybrid SCENE``.
The hybrid input is the existing drawing_proof candidate and its portable assets.
Render each chapter under srstudio.gpu.held(), then join the five at 24 fps.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from examples.acting_continuity import carry_motion, cup_mesh
from examples.body_steps import document as body_document
from examples.drawing_proof import figure_performance
from sr_core.scene import Scene, read

from srstudio import Canvas, body
from srstudio._composition_text import scope
from srstudio.character_clips import Placement
from srstudio.digest import sha256
from srstudio.fonts import inspect_ttf
from srstudio.limbs import HUMAN, ArmProfile, Camera, CameraSample, CameraTrack, Frame, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.interaction import AttachedProp, Participant, PropDrawing, bake_interaction
from srstudio.limbs.motion import Action, Motion, MotionStyle
from srstudio.sample import SYSTEM_FONTS, copy_dejavu
from srstudio.toon import fx, fy
from srstudio.toon_cast import PIVOT

FPS, SECONDS = 24, 6
CHAPTERS = (
    ('face', 'O gesto começa no olhar.', 'Expressões que se transformam'),
    ('gestures', 'Um gesto. Três materiais.', 'Preparação, movimento e acomodação'),
    ('body', 'Antes do passo, o peso.', 'Apoio, quadril e articulações'),
    ('contact', 'A câmera corta. A ação segue.', 'Contato e continuidade'),
    ('hybrid', 'Tudo na mesma cena.', 'Desenho, volume e câmera'),
)
INK, MUTED, PAPER = '#24303B', '#56636D', '#F3EEE6'


def face_plan():
    return figure_performance()


def _canvas(output: Path, name: str):
    index = next(i for i, row in enumerate(CHAPTERS) if row[0] == name)
    _, title, subtitle = CHAPTERS[index]
    scene = Scene(version='auto')
    scene.add_project(width=1920, height=1080, fps=str(FPS), duration=SECONDS, background=PAPER, fontPolicy='pinned')
    scene.add_metadata(title=title, language='pt-BR', generator='srstudio; OpenAI Codex (GPT-6)')
    scene.add_output(
        id='main',
        path='chapter.mp4',
        codec='h264',
        width=1920,
        height=1080,
        fps=str(FPS),
        preset='fast',
        crf='18',
        faststart=True,
    )
    assets = output / 'assets'
    assets.mkdir(mode=0o700)
    font = next(p for p in SYSTEM_FONTS if p.is_file())
    copy_dejavu(font, assets, 'font.ttf')
    facts = inspect_ttf(font.read_bytes())
    cv = Canvas(scene, width=1920, height=1080, font_asset='show-font', local_time=True)
    cv.assets.add_font(
        id='show-font',
        src='assets/font.ttf',
        family=facts.family,
        weight=str(facts.weight),
        sha256=sha256(assets / 'font.ttf'),
        license='assets/FONT-LICENSE.txt',
    )
    cv.text(cv.comp, 'show-brand', 'srstudio  /  ESTUDOS DE MOVIMENTO', 70, 35, 1500, 45, 23, color=MUTED)
    cv.text(cv.comp, 'show-number', f'0{index + 1} / 05', 1700, 35, 180, 45, 23, color=MUTED)
    cv.text(cv.comp, 'show-title', title, 70, 96, 1780, 90, 58, color=INK)
    cv.text(cv.comp, 'show-subtitle', subtitle, 72, 190, 1760, 55, 28, color=MUTED)
    return scene, cv


def _face(cv):
    cv.ellipse(cv.comp, 880, 260, 820, 700, '#E4D7C3')
    plan = face_plan()
    for i, (start, end, scale) in enumerate(((0, 4, 0.60), (4, 6, 0.65))):
        plan.window(start, end).place(
            cv,
            cv.comp,
            at=start,
            id=f'face-{i}',
            placement=Placement(1290, 735, scale=scale, anchor=(fx(PIVOT[0]), fy(PIVOT[1]))),
        )
    for i, (a, b, label, detail) in enumerate(
        (
            (0, 2, 'UMA PAUSA.', 'O personagem observa.'),
            (2, 3.6, 'ALGO MUDOU.', 'Olhos, boca e postura respondem.'),
            (3.6, 6, 'SEM PALAVRAS.', 'A expressão continua durante o corte.'),
        )
    ):
        group = cv.group(cv.comp, f'face-label-{i}', start=a, end=b)
        cv.text(group, f'mood-{i}', label, 95, 460, 740, 90, 46, color=INK)
        cv.text(group, f'detail-{i}', detail, 95, 555, 740, 90, 25, color=MUTED)
    return {
        'cut': 4,
        'cut_state_equal': plan.window(4, 6).sample(0) == plan.sample(4),
        'scope': 'Authored neutral, concerned and deadpan facial blends; frontal Bento candidate.',
    }


def _gestures(cv):
    motion = Motion(
        ArmProfile(),
        HUMAN,
        tuple(
            Action(name, i * 2, 2, style=MotionStyle(overshoot=0.08, settling=0.12, arc=0.12))
            for i, name in enumerate(('point', 'present', 'shrug'))
        ),
    ).chain()
    records = {}
    for i, (style, color) in enumerate((('toon', '#DDEBE5'), ('gloss', '#E4DCEC'), ('collage', '#EBDCCD'))):
        left = 60 + 620 * i
        cv.rect(cv.comp, left, 290, 590, 610, color, radius=28)
        cv.text(cv.comp, 'style-' + style, style.upper(), left + 35, 330, 500, 55, 27, color=INK)
        result = compile_motion(
            cv,
            cv.comp,
            motion,
            id='arm-' + style,
            style=style,
            backend='baked',
            camera=Camera(projection='perspective', distance=5, focal=5, scale=260, origin=(left + 155, 500)),
            options=BakeOptions(fps=FPS, duration=SECONDS),
        )
        records[style] = result.report.to_dict()
    return {'motion': records, 'scope': 'One chained spatial arm performance in three drawing styles.'}


def _body(cv):
    plan = body.compile_body(body.parse_body(body_document()))
    view = Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.18) * Quaternion.axis_angle(Vec3(0, 1, 0), -0.5))
    for style, x, label in (('wire', 610, 'O APOIO'), ('solid', 1370, 'O CORPO')):
        cv.ellipse(cv.comp, x - 230, 872, 460, 75, '#DCD7CA')
        plan.window(0, 6).place(
            cv, cv.comp, camera=Camera(origin=(x, 910), scale=340, view=view), fps=FPS, style=style, id='body-' + style
        )
        cv.text(cv.comp, 'label-' + style, label, x - 220, 946, 520, 45, 23, color=MUTED)
    samples = [plan.sample(i / FPS) for i in range(145)]
    return {
        'min_support_margin': min(p.support_margin for p in samples),
        'scope': 'Two authored flat-foot steps with a static mass proxy; original study mannequin, not dance.',
    }


def _contact(cv):
    motion = carry_motion()
    cv.rect(cv.comp, 810, 280, 1040, 665, '#E4DCEC', radius=30)
    cv.text(cv.comp, 'contact-line-1', 'PEGAR.', 95, 440, 680, 90, 48, color=INK)
    cv.text(cv.comp, 'contact-line-2', 'CARREGAR.', 95, 535, 680, 90, 48, color=INK)
    cv.text(cv.comp, 'contact-line-3', 'DEVOLVER.', 95, 630, 680, 90, 48, color=INK)
    view = Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.25))
    camera = CameraTrack(
        6,
        (
            CameraSample(
                0, Camera(projection='perspective', distance=5, focal=5, scale=360, origin=(1030, 435), view=view)
            ),
            CameraSample(
                3, Camera(projection='perspective', distance=5, focal=5, scale=440, origin=(970, 405), view=view)
            ),
        ),
    )
    result = bake_interaction(
        cv,
        cv.comp,
        (Participant('hand', motion, 'gloss'),),
        (PropDrawing(cup_mesh(), AttachedProp(motion, 'cup')),),
        id='cup-performance',
        camera=camera,
        options=BakeOptions(fps=FPS, duration=SECONDS),
    )
    attachment = motion.attachments[0]
    error = max(
        motion.prop_frame('cup', t).origin.distance(motion.sample(t).hand.frame.compose(attachment.offset).origin)
        for t in (1.2, 2, 3, 4, 4.99)
    )
    return {
        'attachment_residual': error,
        'motion': result.reports[0][1].to_dict(),
        'scope': 'Isolated arm carrying an attached cup; camera cut at three seconds.',
    }


def _hybrid(root, output, source):
    original = ET.parse(source).getroot()
    project = original.find('project')
    if project is None or float(project.get('duration', '0')) != SECONDS:
        raise ValueError('hybrid input must be the complete six-second drawing proof')
    scope(original, 'hybrid')
    shelf = root.find('assets')
    for node in original.findall('assets/*'):
        for field in ('src', 'license'):
            relative = node.get(field)
            if relative is not None:
                resource = (source.parent / relative).resolve()
                if not resource.is_relative_to(source.parent.resolve()) or not resource.is_file():
                    raise ValueError('hybrid resources must be portable files inside its directory')
                target = output / 'assets' / ('hybrid-' + resource.name)
                shutil.copyfile(resource, target)
                node.set(field, 'assets/' + target.name)
        shelf.append(node)
    if root.find('paints') is None:
        root.insert(list(root).index(root.find('composition')), ET.Element('paints'))
    if original.find('paints') is not None:
        root.find('paints').extend(original.find('paints'))
    world = next((n for n in original.find('composition') if n.get('id') == 'hybrid__world'), None)
    if world is None:
        raise ValueError('hybrid input must contain the drawing_proof world')
    world.set('x', '940')
    world.set('y', '90')
    world.set('scaleX', '0.60')
    world.set('scaleY', '0.60')
    root.find('composition').insert(0, world)
    return {
        'input_sha256': sha256(source),
        'scope': 'Existing hybrid candidate: frontal figure, car and isolated hand.',
    }


def build_chapter(output: Path, name: str, *, hybrid: Path | None = None):
    if name not in {row[0] for row in CHAPTERS} or (name == 'hybrid' and hybrid is None):
        raise ValueError('choose a chapter and provide the hybrid scene for the final chapter')
    previous = os.umask(0o077)
    try:
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        scene, cv = _canvas(output, name)
        if name == 'hybrid':
            cv.text(cv.comp, 'hybrid-line-1', 'UM MESMO', 95, 440, 740, 90, 48, color=INK)
            cv.text(cv.comp, 'hybrid-line-2', 'MOMENTO.', 95, 535, 740, 90, 48, color=INK)
            cv.text(
                cv.comp, 'hybrid-detail', 'A perspectiva muda. A ação continua.', 95, 655, 740, 100, 25, color=MUTED
            )
            root = ET.fromstring(scene.to_bytes())
            detail = _hybrid(root, output, hybrid)
        else:
            detail = {'face': _face, 'gestures': _gestures, 'body': _body, 'contact': _contact}[name](cv)
            root = ET.fromstring(scene.to_bytes())
        path = output / 'scene.xml'
        path.write_bytes(ET.tostring(root))
        findings = read(path).check(schema=True)
        if findings:
            raise ValueError(findings)
        report = {
            'schema_version': '1.0.0',
            'generated_by': {'tool': 'OpenAI Codex', 'model': 'GPT-6'},
            'chapter': name,
            'duration': SECONDS,
            'fps': FPS,
            'drawing_approval': None,
            'source_sha256': sha256(Path(__file__)),
            'scene_sha256': sha256(path),
            **detail,
        }
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        return path, report
    finally:
        os.umask(previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--hybrid', type=Path, required=True)
    args = parser.parse_args()
    for name, _, _ in CHAPTERS:
        path, _ = build_chapter(args.output / name, name, hybrid=args.hybrid)
        print(path, flush=True)


if __name__ == '__main__':
    main()
