"""Tube caps must face the same outward direction as their vertex normals."""

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
