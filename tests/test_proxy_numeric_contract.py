"""Cel conversion remains finite at hard tone boundaries and at the smallest valid view."""

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import proxy

TONES = ('#102030', '#506070', '#90A0B0', '#D0E0F0')


def planes(shape, level, recipe):
    lit = np.full((*shape, 4), level, np.uint8)
    lit[..., 3] = 255
    ids = np.empty_like(lit)
    ids[..., :3] = np.array(recipe.ids['body']) * proxy.ID_GAIN
    ids[..., 3] = 255
    return lit, ids


@pytest.mark.parametrize('level,tone', [(0, 1), (127, 1), (129, 2), (255, 3)])
def test_zero_soft_edge_is_a_finite_upper_inclusive_tone_step(level, tone):
    recipe = proxy.Recipe(tones={'body': TONES}, thresholds=(0, 128 / 255, 1), soft_edge=0, oversample=1)
    lit, ids = planes((40, 40), level, recipe)
    with np.errstate(all='raise'):
        rgba, part = proxy.composite(lit, ids, recipe)
    assert np.isfinite(rgba).all()
    assert rgba[20, 20, :3] == pytest.approx(proxy.rgb(TONES[tone]), abs=1e-12)
    assert (rgba[..., 3] == 1).all() and (part == 0).all()


def test_tiny_positive_soft_edge_does_not_overflow_before_clamping_to_a_band():
    recipe = proxy.Recipe(tones={'body': TONES}, thresholds=(0, 0.5, 1), soft_edge=1e-320)
    lit, ids = planes((40, 40), 129, recipe)
    with np.errstate(all='raise'):
        rgba, _ = proxy.composite(lit, ids, recipe)
    assert np.isfinite(rgba).all()
    assert rgba[20, 20, :3] == pytest.approx(proxy.rgb(TONES[2]), abs=1e-12)


@pytest.mark.parametrize('thresholds,edge', [((0, 0.5, 1), 1e308), ((-1e308, 0, 1e308), 1e308)])
def test_unrepresentable_transition_intervals_fail_when_recipe_is_created(thresholds, edge):
    with pytest.raises(proxy.ProxyError) as error:
        proxy.Recipe(tones={'body': TONES}, thresholds=thresholds, soft_edge=edge)
    assert error.value.to_dict()['code'] == 'proxy.recipe.soft_edge'


@pytest.mark.parametrize('grain', [0, 0.2, 2])
def test_smallest_even_view_has_finite_seeded_ink_when_grain_has_no_variance(grain):
    view = proxy.View((0, 0, -10), (0, 0, 0), 20, size=(2, 2))
    recipe = proxy.Recipe(tones={'body': TONES}, ink=proxy.Ink(grain=grain), oversample=1)
    lit, ids = planes(view.size, 255, recipe)
    with np.errstate(all='raise'):
        first, parts = proxy.composite(lit, ids, recipe)
        second, _ = proxy.composite(lit, ids, recipe)
    assert np.isfinite(first).all() and np.array_equal(first, second)
    assert (parts == 0).all() and (first[..., 3] == 1).all()


@pytest.mark.parametrize('seed', [None, True, -1, 0.5, float('nan'), 'random', [], {}])
def test_invalid_or_nondeterministic_grain_seeds_are_refused_when_recipe_is_created(seed):
    with pytest.raises(proxy.ProxyError) as error:
        proxy.Recipe(tones={'body': TONES}, grain_seed=seed)
    diagnostic = error.value.to_dict()
    assert diagnostic['code'] == 'proxy.recipe.grain_seed'
    assert diagnostic['path'] == 'recipe.grain_seed' and diagnostic['expected'] and diagnostic['remedy']


@pytest.mark.parametrize('bad', [{'quiet': ((),)}, {'oversample': True}, {'ink': None}, {'ink': {}}])
def test_undrawable_recipe_settings_are_refused_before_rendering(bad):
    with pytest.raises(proxy.ProxyError) as error:
        proxy.Recipe(tones={'body': TONES}, **bad)
    field = next(iter(bad))
    assert error.value.to_dict()['code'] == 'proxy.recipe.' + field
    assert error.value.to_dict()['path'] == 'recipe.' + field


@pytest.mark.parametrize('seed', [0, 7, 2**80])
def test_valid_seeded_conversion_is_independent_of_sampling_order(seed):
    recipe = proxy.Recipe(tones={'body': TONES}, grain_seed=seed)
    lit, ids = planes((40, 40), 180, recipe)
    ids[:4, :, 3] = 0
    first, _ = proxy.composite(lit, ids, recipe)
    proxy.composite(lit, ids, replace(recipe, grain_seed=seed + 1))
    second, _ = proxy.composite(lit, ids, recipe)
    assert np.array_equal(first, second) and np.isfinite(first).all()


def ordinary_outputs():
    """Existing soft bands, varied normals/light, quiet families and layer separation."""
    recipe = proxy.Recipe(
        tones={'body': TONES, 'wheel': TONES[::-1], 'trim': TONES},
        quiet=(('body', 'trim'),),
        behind=frozenset({'body'}),
        under=frozenset({'wheel'}),
    )
    yy, xx = np.indices((48, 64))
    lit = np.empty((48, 64, 4), np.uint8)
    lit[..., :3] = ((xx * 3 + yy * 2) % 256)[..., None]
    lit[..., 3] = 255
    labels = (xx // 22 + yy // 17) % 3
    ids = np.empty_like(lit)
    ids[..., :3] = (np.array([recipe.ids[n] for n in recipe.names]) * proxy.ID_GAIN)[labels]
    ids[..., 3] = np.where((xx < 4) | (yy < 4), 0, 255)
    result = {}
    for seed in (0, 7, 12345):
        selected = replace(recipe, grain_seed=seed)
        rgba, part = proxy.composite(lit, ids, selected)
        back, front = proxy.split(rgba, part, selected)
        result[str(seed)] = [hashlib.sha256(a.tobytes()).hexdigest() for a in (rgba, part, back, front)]
    return result


def test_existing_soft_bands_grain_and_layer_pixels_remain_identical():
    baseline = json.loads((Path(__file__).parent / 'data/proxy-numeric-baseline.json').read_text())
    assert ordinary_outputs() == baseline['outputs']


def test_authoring_recipe_declares_deterministic_hard_bands():
    text = (Path(__file__).parents[1] / 'docs/authoring-parts.md').read_text()
    section = text.split('## Rigid proxies and deterministic tone conversion', 1)[1].split('\n## ', 1)[0]
    code = re.search(r'```python\n(.*?)\n```', section, re.S).group(1)
    namespace = {}
    exec(compile(code, 'authoring-parts.md', 'exec'), namespace)
    recipe = namespace['recipe']
    assert recipe.soft_edge == 0 and recipe.grain_seed == 7 and recipe.oversample == 2
    lit, ids = planes((40, 40), 255, recipe)
    with np.errstate(all='raise'):
        rgba, _ = proxy.composite(lit, ids, recipe)
    assert np.isfinite(rgba).all()
