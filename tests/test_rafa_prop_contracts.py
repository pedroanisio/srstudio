"""Rafa discovery must distinguish static model mutation from scene construction."""

import json
from pathlib import Path

import numpy as np
import pytest

from srstudio import clay, rafa
from support.rafa_prop_contracts import BUILDERS, ENTRIES, PRINTS, identity, meshes


def info(part):
    return part.describe()['contract']


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_rafa_model_contracts_preserve_all_meshes_and_describe_mutation(part):
    assert part.contract is not None
    baseline = json.loads(Path('tests/data/rafa-prop-contract-baseline.json').read_text())
    assert identity(part.name) == baseline['mesh_sha256'][part.name]
    contract = info(part)
    model = contract['arguments']['properties']['m']
    assert model['x-python-type'] == 'srstudio.clay.Model'
    assert model['x-unit'] == 'Rafa model units' and model['x-space'] == 'model-frame'
    assert model['x-role'] == 'mutable-model'
    assert contract['returns']['type'] == 'null'
    assert contract['returns']['x-role'] == 'model-mutation'
    assert contract['capabilities']['returns_scene_handle'] is False
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['animation'] is False
    assert 'static' in ' '.join(contract['constraints'])
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_all_seven_rafa_props_and_rooms_have_examples():
    assert len(ENTRIES) == 7 and {e.name for e in ENTRIES} == set(BUILDERS) == set(PRINTS)


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_material_dependencies_and_print_uvs_are_real_and_finishing_is_an_existing_operation(part):
    assert part.contract is not None
    op = next(o for o in part.contract.operations if o.name == 'finished')
    assert op.builder is rafa.finished
    contract = info(part)['operations']['finished']
    assert contract['arguments']['properties']['mesh']['x-unit'] == 'Rafa model units'
    assert contract['returns']['x-python-type'] == 'srstudio.clay.Mesh'
    built = meshes(part.name)
    assert {m.material for m in built} <= rafa.MATERIALS.keys()
    assert {m.material for m in built if m.material in rafa.PRINTS} == PRINTS[part.name]
    for mesh in built:
        material = rafa.MATERIALS[mesh.material]
        complete = op.builder(mesh)
        np.testing.assert_array_equal(complete.vertices, mesh.vertices)
        np.testing.assert_array_equal(complete.normals, mesh.normals)
        np.testing.assert_array_equal(complete.triangles, mesh.triangles)
        assert complete.material == mesh.material
        if material.print is not None:
            assert material.print is rafa.PRINTS[mesh.material]
            assert mesh.uvs is not None and complete is mesh
        elif material.normal_map is not None:
            assert complete.uvs is not None
        else:
            assert complete is mesh


@pytest.mark.parametrize('name', list(rafa.PROPS))
def test_props_bake_the_current_model_frame_and_leave_existing_geometry_intact(name):
    model = clay.Model()
    model.box('caller-owned', (0, 0, 0), (1, 1, 1))
    existing = model.meshes()[0].sha256
    with model.at(12, -23, 34, scale=1.5):
        assert BUILDERS[name](model) is None
    built = {m.material: m for m in model.meshes()}
    assert built.pop('caller-owned').sha256 == existing
    for original in meshes(name):
        np.testing.assert_allclose(built[original.material].vertices, original.vertices * 1.5 + (12, -23, 34))
        np.testing.assert_array_equal(built[original.material].triangles, original.triangles)
    model.box('after', (0, 0, 0), (1, 1, 1))
    after = next(m for m in model.meshes() if m.material == 'after')
    np.testing.assert_allclose(after.vertices.mean(axis=0), (0, 0, 0), atol=1e-12)


@pytest.mark.parametrize('name', list(rafa.ROOMS))
def test_room_plant_frames_are_explicitly_absolute_and_not_a_promised_whole_room_transform(name):
    part = next(e for e in ENTRIES if e.name == name)
    assert any('absolute' in c and 'plant' in c for c in info(part)['constraints'])
    model = clay.Model()
    with model.at(100, 0, 0):
        BUILDERS[name](model)
    moved = {m.material: m for m in model.meshes()}
    original = {m.material: m for m in meshes(name)}
    np.testing.assert_array_equal(moved['leaf'].vertices, original['leaf'].vertices)
    # Room walls use the active frame; plant helpers use their own frame.
    wall = 'wall' if name == 'rafa-kitchen' else 'office'
    np.testing.assert_allclose(moved[wall].vertices, original[wall].vertices + (100, 0, 0))


def test_rafa_model_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- rafa-model-discovery:start -->')[1].split('<!-- rafa-model-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<rafa-model-discovery>', 'exec'), {})
