"""Pixel review fails on changed repeated frames and altered protected information."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_proof_review')


def samples():
    base = np.zeros((1920, 1080, 4), dtype=np.uint8)
    moved = base.copy()
    moved[900:1200, 400:700] = (90, 120, 150, 255)
    return [base, base.copy(), moved, moved.copy(), base.copy()]


def test_measurements_allow_world_motion_and_require_identical_repeated_frames(review):
    result = review.measure(samples(), (0, 1, 24, 24, 0))
    assert result['repeated_frames_equal'] and result['held_initial_frame_equal']
    assert result['information_pixels_equal']
    assert result['world_changes_observed']


@pytest.mark.parametrize('defect', ['repeat', 'caption', 'held', 'size', 'no-motion', 'no-repeat'])
def test_pixel_defects_and_missing_evidence_are_refused(review, defect):
    images = samples()
    frames = (0, 1, 24, 24, 0)
    if defect == 'repeat':
        images[3][900, 400, 0] += 1
    elif defect == 'caption':
        images[2][1720, 200, 0] += 1
        images[3][1720, 200, 0] += 1
    elif defect == 'held':
        images[1][1000, 500, 0] += 1
    elif defect == 'size':
        images[0] = images[0][::2, ::2]
    elif defect == 'no-motion':
        images = [images[0]] * 5
    else:
        frames = (0, 1, 24, 60, 96)
    with pytest.raises(ValueError):
        review.measure(images, frames)


def test_failed_engine_command_preserves_diagnostics_without_a_passing_report(review, tmp_path, monkeypatch):
    import sys
    from contextlib import nullcontext

    from srstudio._bounded_process import BoundedProcessError

    # Python is deliberately not a renderer. Exercise a real subprocess error
    # without taking the shared GPU lock for this CPU-only failure fixture.
    monkeypatch.setattr(review.gpu, 'held', nullcontext)
    scene = tmp_path / 'scene.xml'
    scene.write_text('<scene/>')
    output = tmp_path / 'review'
    with pytest.raises(BoundedProcessError):
        review.review(scene, output, engine=Path(sys.executable))
    assert (output / 'validate.stderr').read_bytes()
    assert not (output / 'review.json').exists()
    assert not (output / 'proof.mp4').exists()


def test_existing_review_and_missing_inputs_are_preserved(review, tmp_path):
    import sys

    with pytest.raises(FileNotFoundError):
        review.review(tmp_path / 'missing.xml', tmp_path / 'out', engine=Path(sys.executable))
    assert not (tmp_path / 'out').exists()
    scene = tmp_path / 'scene.xml'
    scene.write_text('<scene/>')
    with pytest.raises(FileExistsError):
        review.review(scene, tmp_path, engine=Path(sys.executable))
    assert scene.read_text() == '<scene/>'
