"""Tube caps must face the same outward direction as their vertex normals."""

import importlib
import inspect

import numpy as np
import pytest

from srstudio import clay


@pytest.mark.parametrize('shape', ['rod', 'cylinder', 'ribbon', 'tube', 'sweep'])
def test_every_tube_cap_has_outward_winding(shape):
    model = clay.Model()
    if shape == 'rod':
        model.rod('solid', (1, 2, 3), (4, -8, 6), 2)
    elif shape == 'cylinder':
        model.cylinder('solid', (1, 2, 3), 2, 10)
    elif shape == 'ribbon':
        model.ribbon('solid', ((1, 2, 3), (4, -8, 6), (7, -18, 9)), (2, 1.8, 1.5), sides=8)
    elif shape == 'tube':
        model.tube('solid', ((1, 2, 3), (4, -8, 6), (7, -18, 9)), 2, n=8, sides=8)
    else:
        model.sweep('solid', ((1, 2, 3), (4, -8, 6), (7, -18, 9)), (2, 1.5), n=8, sides=8)
    mesh = model.meshes()[0]
    vertices = mesh.vertices[mesh.triangles]
    geometric = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    normals = mesh.normals[mesh.triangles].mean(axis=1)
    assert np.linalg.norm(geometric, axis=1).min() > 1e-8
    assert np.einsum('ij,ij->i', geometric, normals).min() > 0


def _start_cap_facing(model):
    """The sign of the starting cap's winding against its normal: 1 outward, -1 inward."""
    mesh = model.meshes()[0]
    sides = 8
    rows = (len(mesh.vertices) - 2) // sides
    cap = mesh.triangles[(rows - 1) * sides * 2 : (rows - 1) * sides * 2 + sides]
    v = mesh.vertices[cap]
    geometric = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    return np.sign(np.einsum('ij,ij->i', geometric, mesh.normals[cap].mean(axis=1)))


PATH = ((1, 2, 3), (4, -8, 6), (7, -18, 9))
BEFORE_THE_CAP_FIX = '7d2c6933308f4a26a4e45bbed1564fdaf34797b6a3a59e52240bafa10e56b484'


def test_a_model_winds_its_starting_caps_outward_unless_told_the_first_way():
    assert clay.Model().caps_winding is clay.Caps.OUTWARD
    outward, first = clay.Model(), clay.Model()
    outward.tube('solid', PATH, 2, n=8, sides=8)
    with first.caps(clay.Caps.FIRST) as same:
        assert same is first and first.caps_winding is clay.Caps.FIRST
        first.tube('solid', PATH, 2, n=8, sides=8)
    assert first.caps_winding is clay.Caps.OUTWARD
    assert (_start_cap_facing(outward) == 1).all()
    assert (_start_cap_facing(first) == -1).all()
    a, b = outward.meshes()[0], first.meshes()[0]
    assert np.array_equal(a.vertices, b.vertices) and np.array_equal(a.normals, b.normals)
    assert a.sha256 != b.sha256


def test_the_first_winding_is_the_winding_approved_drawings_were_baked_with():
    """The tube that the cap fix changed, baked the first way, is the bytes from before the fix."""
    first = clay.Model()
    with first.caps(clay.Caps.FIRST):
        first.tube('solid', PATH, 2, n=8, sides=8)
    assert first.meshes()[0].sha256 == BEFORE_THE_CAP_FIX


def test_a_scoped_winding_comes_back_when_the_build_fails():
    model = clay.Model()
    with pytest.raises(clay.ClayError):
        with model.caps(clay.Caps.FIRST):
            model.tube('', PATH, 2)
    assert model.caps_winding is clay.Caps.OUTWARD


@pytest.mark.parametrize('bad', ['first', None, 1])
def test_a_winding_must_be_one_of_the_caps(bad):
    with pytest.raises(clay.ClayError, match='winding'):
        with clay.Model().caps(bad):
            pass


def test_a_builder_pinned_to_the_first_caps_bakes_them_and_hands_the_model_back_as_it_was():
    seen = []

    @clay.first_caps
    def build(m, r):
        """A rod."""
        seen.append(m.caps_winding)
        m.tube('solid', PATH, r, n=8, sides=8)
        return 'built'

    model = clay.Model()
    assert build(model, 2) == 'built' and seen == [clay.Caps.FIRST]
    assert model.caps_winding is clay.Caps.OUTWARD
    assert build.__name__ == 'build' and build.__doc__ == 'A rod.'
    assert list(inspect.signature(build).parameters) == ['m', 'r'] and build.pinned_caps is clay.Caps.FIRST


@pytest.mark.parametrize(
    'builder',
    [
        'rafa.skull',
        'rafa.eyes',
        'rafa.brows',
        'rafa.mouth',
        'rafa.body',
        'rafa.reach',
        'rafa.hold',
        'rafa.rest',
        'rafa.mug',
        'rafa.phone',
        'rafa.bills',
        'rafa.lunchbox',
        'rafa.tote',
        'rafa.kitchen',
        'rafa.breakroom',
        'rafa.counter',
        'rafa.near',
        'pedro.body',
        'pedro_wardrobe.tee',
        'pedro_wardrobe.blazer',
        'pedro_wardrobe.puffer',
        'pedro_wardrobe.body',
    ],
)
def test_every_builder_of_an_approved_first_version_keeps_the_first_caps(builder):
    """Rafa v1 and Pedro v1 are approved drawings: they keep the caps they were approved with (ADR 0047)."""
    module, name = builder.split('.')
    fn = getattr(importlib.import_module(f'srstudio.{module}'), name)
    assert getattr(fn, 'pinned_caps', None) is clay.Caps.FIRST, f'{builder} is not pinned to the first caps'
