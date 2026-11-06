"""Render versioned numeric envelopes and a separate blinded, initially unrated review.

Uses canonical human arms, not whole characters. The production policy rejects the
compressed motions; only this evidence study deliberately renders them with policy=warn.
Choose a fresh output directory and an explicit private --seed. --engine encodes every
clip with --strict; --ratings consumes actual observations using the same review seed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import Camera, LimbError
from srstudio.limbs.adapters import Appearance
from srstudio.limbs.calibration import get_preset, list_presets, reference_cases
from srstudio.limbs.compile import BakeOptions, Compiled, compile_motion
from srstudio.limbs.evaluation import Pair, parse_ratings, plan_trials, summarize
from srstudio.limbs.serialization import motion_dict, read_document

WIDTH, HEIGHT, FPS = 1280, 720, 24


def _write(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)


def _json(path: Path, data: object) -> None:
    _write(path, (json.dumps(data, indent=2, allow_nan=False) + '\n').encode())


def study_case(name: str, case_name: str, *, compressed: bool = False) -> tuple[Scene, dict, dict]:
    """Compile one complete scene and preserve its production rejection independently of the drawing."""
    preset = get_preset(name)
    reference = next(case for case in reference_cases(name) if case.name == case_name)
    motion = reference.motion
    duration = motion.end
    if compressed:
        motion = replace(
            motion, actions=tuple(replace(a, start=a.start / 6, duration=a.duration / 6) for a in motion.actions)
        )
    scene = Scene(version='auto')
    scene.add_project(width=WIDTH, height=HEIGHT, fps=str(FPS), duration=duration, background='#f4f0e9')
    scene.add_metadata(generator='srstudio quality study; OpenAI Codex GPT-6')
    cv = Canvas(scene, width=WIDTH, height=HEIGHT, font_asset=None)
    options = replace(preset.options_for(motion, style=preset.style, fps=FPS), duration=duration)

    def compile_with(options: BakeOptions) -> Compiled:
        return compile_motion(
            cv,
            cv.comp,
            motion,
            id='performance',
            style=preset.style,
            backend='baked',
            options=options,
            camera=Camera(origin=(500, 180), scale=160),
            appearance=Appearance(skin='#d59b76', sleeve='#387b91', line_width=3),
        )

    failure = None
    if compressed:
        before = scene.to_bytes()
        try:
            compile_with(options)
        except LimbError as exc:
            if exc.code != 'quality.limit' or scene.to_bytes() != before:
                raise
            failure = exc.to_dict()
        else:
            raise LimbError('compressed example no longer demonstrates a production rejection', code='quality.study')
        assert options.quality is not None
        options = replace(options, quality=replace(options.quality, policy='warn'))
    compiled = compile_with(options)
    return (
        scene,
        {
            'preset': name,
            'reference_case': case_name,
            'rejected': compressed,
            'duration': duration,
            'expected_frames': round(duration * FPS),
            'production_failure': failure,
            'report': compiled.report.to_dict(),
        },
        motion_dict(motion),
    )


def _encode(engine: str, out: Path, cases: list[dict]) -> dict:
    version = subprocess.run(
        [engine, '--version'], capture_output=True, text=True, check=True, timeout=10
    ).stdout.strip()
    encoded = []
    for case in cases:
        command = [engine, 'encode', str((out / case['scene']).resolve()), '--strict', '--json']
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=180)
        evidence = json.loads(result.stdout)
        if not evidence.get('ok') or evidence.get('diagnostics') or evidence.get('error'):
            raise LimbError('strict encode did not return clean success evidence', code='quality.render')
        video = out / case['video']
        if not video.is_file() or not video.stat().st_size:
            raise LimbError('strict encode did not produce its video', code='quality.render')
        video.chmod(0o600)
        encoded.append(
            {
                'case': case['id'],
                'command': command,
                'exit_code': result.returncode,
                'engine_report': evidence,
                'video_sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
            }
        )
        print(f"Encoded {case['id']}", flush=True)
    return {'status': 'complete', 'engine': version, 'clips': encoded}


def build(out: Path, *, seed: str, engine: str | None = None, ratings: Path | None = None) -> Path:
    profiles = list_presets(latest=True)
    pairs = tuple(
        Pair(
            p['scope']['style'],
            'Point to the right with one arm',
            p['scope']['style'] + '-point-right',
            p['scope']['style'] + '-compressed',
        )
        for p in profiles
    )
    trials = plan_trials(pairs, seed=seed)
    observed = parse_ratings(read_document(ratings, 'rating')) if ratings else ()
    summary = summarize(trials, observed)
    if out.exists():
        raise FileExistsError(f'Use a fresh study directory; preserving existing files in {out}')
    missing = [p for p in out.parents if not p.exists()]
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    out.mkdir(mode=0o700)
    for folder in ('scenes', 'motions', 'review', 'renders'):
        (out / folder).mkdir(mode=0o700)
    videos = {getattr(trial, side): f'review/{trial.id}-{side.upper()}.mp4' for trial in trials for side in ('a', 'b')}
    records = []
    for profile in profiles:
        style = profile['scope']['style']
        cases = [(case.name, False) for case in reference_cases(profile['id'])] + [('point-right', True)]
        for case_name, compressed in cases:
            name = f'{style}-' + ('compressed' if compressed else case_name)
            scene, record, source = study_case(profile['id'], case_name, compressed=compressed)
            video = videos.get(name, f'renders/{name}.mp4')
            scene.add_output(
                id='main',
                path='../' + video,
                codec='h264',
                width=WIDTH,
                height=HEIGHT,
                fps=str(FPS),
                preset='fast',
                crf='18',
                faststart=True,
            )
            findings = scene.check(schema=True)
            if findings:
                raise LimbError('quality study failed SDK validation: ' + str(findings[0]), code='quality.study')
            raw = scene.to_bytes(layout='pretty')
            record.update(
                id=name,
                scene=f'scenes/{name}.scene.xml',
                motion=f'motions/{name}.json',
                video=video,
                scene_sha256=hashlib.sha256(raw).hexdigest(),
                sdk_findings=[],
            )
            _write(out / record['scene'], raw)
            _json(out / record['motion'], source)
            records.append(record)
    _json(out / 'private-key.json', {'seed': seed, 'trials': [asdict(t) for t in trials]})
    _json(
        out / 'review/trials.json',
        {'schema': 'srstudio.limbs.review/1.0.0', 'trials': [t.public_dict() for t in trials]},
    )
    _json(out / 'review/ratings-template.json', {'schema': 'srstudio.limbs.ratings/1.0.0', 'ratings': []})
    _write(
        out / 'review/instructions.txt',
        (
            b'Watch each pair at normal speed. Rate task clarity, movement naturalness and style fit from 1 to 5, '
            b'then choose a, b or tie. Use a stable anonymous reviewer ID. Each rating needs trial, reviewer, '
            b'preference, a and b; both a and b contain clarity, naturalness and style_fit. '
            b'Keep the engineering report and private key outside the review. Do not invent observations.\n'
        ),
    )
    render = _encode(engine, out, records) if engine else {'status': 'not_requested'}
    report = out / 'quality-study.json'
    _json(
        report,
        {
            'schema': 'srstudio.quality-study/1.0.0',
            'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
            'scope': 'Isolated canonical human arms at 24 Hz; no whole-body or perceptual certification.',
            'profiles': profiles,
            'cases': records,
            'review': summary,
            'render': render,
        },
    )
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--seed', required=True, help='private review ordering key')
    parser.add_argument('--engine', help='scene-render binary; encodes all 14 clips with --strict')
    parser.add_argument('--ratings', type=Path, help='observed reviews for this seed')
    args = parser.parse_args()
    print(build(args.out, seed=args.seed, engine=args.engine, ratings=args.ratings))
