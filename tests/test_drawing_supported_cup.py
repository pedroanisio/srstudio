"""The candidate's cup stands on fixed floor rests before pickup and after its early release."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_body')


def _resting(meshes):
    cup, stand = meshes['cup'], meshes['support']
    bottom, normal = cup.vertices[-16:], cup.normals[-1]
    center = bottom.mean(axis=0)
    distances = (stand.vertices - center) @ normal
    return distances.min(), int(np.count_nonzero(np.abs(distances) < 1e-8)), stand.vertices[:, 1].max()


@pytest.mark.parametrize('time', [0, 0.6, 1.2, 3.6, 3.999, 4, 5, 6])
def test_released_cup_stands_on_a_rest_whose_foot_meets_the_floor(example, time):
    meshes = {mesh.material: mesh for mesh in example.candidate_mesh(time)}
    lowest, touching, floor = _resting(meshes)
    assert lowest >= -1e-8  # The rest never enters the cup.
    assert touching >= 16  # The whole cup base sits on the rest's top.
    assert floor == pytest.approx(0, abs=1e-9)  # Canonical y is down; the rest's foot is on the floor.


@pytest.mark.parametrize('times', [(0, 0.6, 1.2, 2.99), (3, 3.6, 3.999, 4, 6)])
def test_each_rest_is_fixed_in_world_space_through_its_painter_window_and_the_cut(example, times):
    stands = [{m.material: m for m in example.candidate_mesh(t)}['support'].vertices for t in times]
    assert all(np.array_equal(stands[0], stand) for stand in stands[1:])


def test_front_rest_holds_the_cup_where_the_early_release_set_it_down(example):
    released = {m.material: m.vertices for m in example.candidate_mesh(3.6)}
    for time in (4, 5, 6):
        later = {m.material: m.vertices for m in example.candidate_mesh(time)}
        assert np.array_equal(later['cup'], released['cup'])


def test_carried_cup_never_enters_either_rest(example):
    for time in np.linspace(0, 6, 145):
        meshes = {m.material: m for m in example.candidate_mesh(float(time))}
        reference = {m.material: m for m in example.candidate_mesh(1.2 if time < 3 else 3.6)}['cup']
        center, normal = reference.vertices[-16:].mean(axis=0), reference.normals[-1]
        assert np.max((meshes['cup'].vertices - center) @ normal) <= 1e-7, time


def test_supported_scene_draws_the_rests_with_their_declared_palette(example):
    from examples.drawing_cup_support import supported_recipe

    study = example.body_scene(fps=2, size=(216, 384))
    hand = next(source for source in study.timeline.rasters if source.id == 'hand')
    tones = supported_recipe().tones['support']
    for frame in hand.frames:
        assert 'support' in {mesh.material for mesh in frame.source.meshes}
        assert tuple(next(p for p in frame.source.recipe.parts if p.name == 'support').tones) == tones
