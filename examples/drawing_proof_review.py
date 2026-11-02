"""Strict encode and scoped pixel checks for the full-size drawing candidate.

Run python -m examples.drawing_proof_review SCENE OUTPUT --engine ENGINE.
The measurements do not grant style approval or replace temporal visual review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
from pathlib import Path

import numpy as np

from srstudio import gpu, plates
from srstudio._bounded_process import BoundedProcessError, ProcessLimits, run
from srstudio.digest import sha256

FRAMES = (0, 1, 24, 60, 78, 96, 132, 60, 0)


def measure(images: list[np.ndarray], frames: tuple[int, ...]) -> dict:
    if len(images) != len(frames) or not images:
        raise ValueError('each requested frame needs one decoded image')
    if any(image.shape != (1920, 1080, 4) or image.dtype != np.uint8 for image in images):
        raise ValueError('pixel evidence must be full-size 1080x1920 RGBA8')
    seen: dict[int, np.ndarray] = {}
    repeats = 0
    for frame, image in zip(frames, images, strict=True):
        if frame in seen:
            repeats += 1
            if not np.array_equal(image, seen[frame]):
                raise ValueError(f'repeated frame {frame} changed pixels')
        seen[frame] = image
    if repeats < 2 or 0 not in seen or 1 not in seen:
        raise ValueError('review requires two repeated samples and initial held frames 0 and 1')
    if not np.array_equal(seen[0], seen[1]):
        raise ValueError('the initial held frame changed pixels')
    # The example owns these explicit protected screen rectangles. This checks
    # invariance through picture changes, not equivalence to an approved caption.
    for image in images[1:]:
        for start, end in ((0, 320), (1680, 1810)):
            if not np.array_equal(images[0][start:end], image[start:end]):
                raise ValueError('protected information changed pixels')
    if not any(not np.array_equal(images[0], image) for image in images[1:]):
        raise ValueError('no moving-world evidence was observed')
    return {
        'size': [1080, 1920],
        'repeated_frames_equal': True,
        'repeat_comparisons': repeats,
        'held_initial_frame_equal': True,
        'information_pixels_equal': True,
        'world_changes_observed': True,
        'decoded_rgba_sha256': [hashlib.sha256(image.tobytes()).hexdigest() for image in images],
    }


def review(scene: Path, output: Path, *, engine: Path) -> Path:
    scene, output, engine = scene.resolve(), output.resolve(), engine.resolve()
    if not scene.is_file() or not engine.is_file():
        raise FileNotFoundError('review needs an existing scene and engine')
    if output.exists():
        raise FileExistsError(output)
    previous = os.umask(0o077)
    try:
        output.mkdir(parents=True, mode=0o700)
        commands = []

        def execute(name: str, arguments: tuple[str, ...]) -> None:
            command = (str(engine), *arguments)
            try:
                with gpu.held():
                    result = run(command, input=b'', limits=ProcessLimits(timeout=600, stdout_bytes=2 * 1024**2))
            except BoundedProcessError as error:
                (output / f'{name}.stdout').write_bytes(error.stdout)
                (output / f'{name}.stderr').write_bytes(error.stderr)
                raise
            (output / f'{name}.stdout').write_bytes(result.stdout)
            (output / f'{name}.stderr').write_bytes(result.stderr)
            commands.append({'name': name, 'command': command, 'exit_code': 0})
            print(f'Passed {name}', flush=True)

        execute('validate', ('validate', str(scene), '--deny-warnings', '--json'))
        images = []
        for index, frame in enumerate(FRAMES):
            target = output / f'{index:02d}-frame-{frame:03d}.png'
            execute(
                f'frame-{index:02d}',
                (
                    'render',
                    str(scene),
                    '--frame',
                    str(frame),
                    '--output',
                    str(target),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
            )
            images.append(plates.pixels(target))
        measurements = measure(images, FRAMES)
        execute(
            'encode',
            (
                'encode',
                str(scene),
                '--output',
                'main',
                '--path',
                str(output / 'proof.mp4'),
                '--strict',
                '--quality',
                'final',
                '--no-upload',
                '--parallel',
                '1',
                '--report',
                str(output / 'encode-report.json'),
                '--json',
            ),
        )
        report = {
            'schema': 'srstudio.drawing-candidate-review/1.0.0',
            'generated_by': {'tool': 'OpenAI Codex', 'model': 'GPT-6'},
            'scene_sha256': sha256(scene),
            'engine_sha256': sha256(engine),
            'reviewer_sha256': sha256(Path(__file__)),
            'commands': commands,
            'frames': FRAMES,
            'measurements': measurements,
            'child_peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            'status': 'scoped automated checks passed; full acceptance and visual review remain separate',
        }
        path = output / 'review.json'
        path.write_text(json.dumps(report, indent=2) + '\n')
        return path
    finally:
        os.umask(previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--engine', required=True, type=Path)
    args = parser.parse_args()
    print(review(args.scene, args.output, engine=args.engine))
