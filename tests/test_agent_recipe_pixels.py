"""Preview framing and prop visibility are rendered checks, not contract declarations."""

import runpy
import subprocess
from pathlib import Path

import numpy as np
import pytest

from srstudio import gpu
from srstudio._composition_png import decode


@pytest.mark.parametrize('recipe', ['pip', 'carry'])
def test_recipe_subject_is_in_frame_and_carry_prop_is_visible(scene_render, tmp_path, recipe):
    build = runpy.run_path(str(Path(__file__).parents[1] / 'examples/agent_authoring.py'))['build']
    scene = build(tmp_path / 'preview', recipe=recipe)[0]
    for time in (0, 1, 1.75):
        output = tmp_path / f'{time}.png'
        with gpu.held(wait=30):
            subprocess.run(
                [
                    str(scene_render),
                    'render',
                    str(scene),
                    '--time',
                    str(time),
                    '--output',
                    str(output),
                    '--strict',
                    '--quality',
                    'draft',
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        pixels = decode(output.read_bytes(), 540, 960)
        rgb = np.asarray(pixels).reshape(960, 540, 4)[:, :, :3].astype(int)
        foreground = np.max(np.abs(rgb - rgb[0, 0]), axis=2) > 20
        y, x = np.nonzero(foreground)
        assert len(x) > 500
        assert min(x) > 10 and max(x) < 529 and min(y) > 10 and max(y) < 949
        if recipe == 'carry':
            prop = np.max(np.abs(rgb - (108, 154, 188)), axis=2) < 5
            assert np.count_nonzero(prop) > 100, 'the attached prop must remain visibly distinct from the hand'
