"""The held cup rests on fixed geometry before pickup and after release."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_cup_support')


@pytest.mark.parametrize('time', [0, 0.7, 1.2, 5, 5.5, 6])
def test_cup_bottom_contacts_the_authored_support_and_its_base_touches_ground(example, time):
    from examples.drawing_body import body_transform

    meshes = {mesh.material: mesh for mesh in example.supported_mesh(time, placement=body_transform)}
    cup, stand = meshes['cup'], meshes['support']
    bottom = cup.vertices[-16:]
    normal = cup.normals[-1]
    center = bottom.mean(axis=0)
    distances = (stand.vertices - center) @ normal
    assert distances.min() >= -1e-8
    cap = stand.vertices[np.abs(distances) < 1e-8]
    assert len(cap) >= 16
    assert np.allclose((bottom - center) @ normal, 0, atol=1e-8)
    assert np.linalg.norm(cap - center, axis=1).max() > np.linalg.norm(bottom - center, axis=1).max()
    assert stand.vertices[:, 1].max() == pytest.approx(0, abs=1e-9)
    assert np.isfinite(stand.vertices).all() and np.isfinite(stand.normals).all()
    assert np.allclose(np.linalg.norm(stand.normals, axis=1), 1)
    triangles = stand.vertices[stand.triangles]
    geometric = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    assert np.einsum('ij,ij->i', geometric, stand.normals[stand.triangles].mean(axis=1)).min() > 0


@pytest.mark.parametrize('times', [(0, 0.7, 1.2, 2.9), (3, 4, 5, 6)])
def test_support_stays_in_world_space_for_its_entire_painter_window(example, times):
    from examples.drawing_body import body_transform

    stands = [
        next(mesh for mesh in example.supported_mesh(t, placement=body_transform) if mesh.material == 'support')
        for t in times
    ]
    assert all(np.array_equal(mesh.vertices, stands[0].vertices) for mesh in stands)
    assert all(np.array_equal(mesh.triangles, stands[0].triangles) for mesh in stands)


def test_carried_cup_clears_the_fixed_rest_on_lift_and_return(example):
    from examples.drawing_body import body_transform

    for time in np.linspace(0, 6, 121):
        meshes = {mesh.material: mesh for mesh in example.supported_mesh(float(time), placement=body_transform)}
        cup = meshes['cup']
        reference = 1.2 if time < 3 else 5
        rest = next(
            mesh for mesh in example.supported_mesh(reference, placement=body_transform) if mesh.material == 'cup'
        )
        center, normal = rest.vertices[-16:].mean(axis=0), rest.normals[-1]
        assert np.max((cup.vertices - center) @ normal) <= 1e-7, time


def test_support_adds_one_explicit_palette_without_changing_existing_hand_colors(example):
    from examples.drawing_hand import hand_recipe

    original, supported = hand_recipe(), example.supported_recipe()
    assert set(supported.tones) == {*original.tones, 'support'}
    assert all(supported.tones[name] == tones for name, tones in original.tones.items())
    assert (supported.oversample, supported.grain_seed) == (original.oversample, original.grain_seed)


def test_clearance_preserves_the_shoulder_bones_and_finger_cup_registration(example):
    from examples.drawing_attached import attached_mesh, shoulder_frame
    from examples.drawing_body import body_transform

    time = 1.3  # The uncorrected cup passes through the pickup surface here.
    original = {mesh.material: mesh for mesh in attached_mesh(time, placement=body_transform)}
    corrected = {mesh.material: mesh for mesh in example.supported_mesh(time, placement=body_transform)}
    assert not np.array_equal(original['cup'].vertices, corrected['cup'].vertices)
    point = shoulder_frame(time, placement=body_transform(time)).origin
    assert corrected['sleeve'].vertices[:8].mean(axis=0) == pytest.approx((point.x, point.y, -point.z), abs=1e-9)
    for before, after in ((0, 8), (8, 16)):
        centers = [
            mesh.vertices[before : before + 8].mean(axis=0) - mesh.vertices[after : after + 8].mean(axis=0)
            for mesh in (original['sleeve'], corrected['sleeve'])
        ]
        assert np.linalg.norm(centers[0]) == pytest.approx(np.linalg.norm(centers[1]), abs=1e-9)
    for finger, cup in ((0, 0), (8, 16), (16, 32)):
        distances = [
            np.linalg.norm(meshes['skin'].vertices[finger] - meshes['cup'].vertices[cup])
            for meshes in (original, corrected)
        ]
        assert distances[0] == pytest.approx(distances[1], abs=1e-9)


@pytest.mark.parametrize('case', ['below-ground', 'excessive-clearance'])
def test_unsupported_rest_or_reach_fails_instead_of_detaching_the_arm(example, case):
    from dataclasses import replace

    from examples.drawing_body import body_transform

    def placement(time):
        transform = body_transform(time)
        x, y, z = transform.translation
        shift = 200 if case == 'below-ground' else 20 if time == 1.3 else 0
        return replace(transform, translation=(x, y + shift, z))

    with pytest.raises(ValueError, match='ground|swing envelope'):
        example.supported_mesh(1.3, placement=placement)


@pytest.mark.parametrize('time', [True, -0.1, 6.1, float('nan')])
def test_invalid_support_time_is_rejected_before_sampling_placement(example, time):
    def unexpected(_):
        pytest.fail('invalid time reached the placement callback')

    with pytest.raises(ValueError, match='time'):
        example.supported_mesh(time, placement=unexpected)


# 1.0 s: the cup on its rest as the paw arrives. From 1.15 s to about 1.5 s the closing paw covers the cup from this
# camera (about 20 of its pixels show), so a frame there cannot show that every material draws.
@pytest.mark.parametrize('time', [1.0, 5.3])
def test_real_rest_and_cup_render_in_the_shared_world_and_reuse_cache(example, time, scene_render, tmp_path):
    from examples.drawing_body import body_transform
    from examples.drawing_proof import sample
    from examples.drawing_world import _camera, _floor, _lights

    from srstudio import composition as c
    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    size = (1080, 1920)
    recipe = example.supported_recipe()
    meshes = example.supported_mesh(time, placement=body_transform)
    source = c.proxy_source('hand', meshes, recipe, basis='clay', lighting='scene', meters_per_unit=0.01)
    points = np.concatenate([mesh.vertices for mesh in meshes]) * (1, 1, -1)
    binding = c.AssetBinding(
        'hand',
        'candidate.supported-cup-snapshot',
        1,
        'proxy',
        c.Bounds(tuple(points.min(axis=0).tolist()), tuple(points.max(axis=0).tolist())),
        nodes=128,
        memory_bytes=64 * 1024**2 + size[0] * size[1] * (64 * len(recipe.tones) + 512),
        plates=c.proxy_jobs(source, width=size[0], height=size[1], memory_bytes=256 * 1024**2),
        candidate=c.CandidateSource('toon', c.proxy_source_digest(source)),
    )
    floor, vector = _floor(size)
    view = sample(time)
    clock = c.TemporalPolicy(0, 1)
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        *size,
        c.FrameRate(24),
        1,
        17,
        'centimeter',
        _camera(view),
        _lights(view),
        (c.LayerSpec('floor', 'floor', 1, clock), c.LayerSpec('hand', 'hand', 1, clock)),
        c.RenderBudget(max_new_plates=2, max_engine_invocations=2, timeout=120),
        background='#efe8df',
    )
    scene = m.plan_scene(spec, (floor, binding), m.SceneMotion(), rasters=(source,), purpose='candidate-review')
    cold = m.emit_timeline(scene, (vector,), tmp_path / 'cold', engine=scene_render, cache=tmp_path / 'cache')
    assert cold.work.engine_invocations == 2
    with plates.render_session(max_invocations=0):
        warm = m.emit_timeline(scene, (vector,), tmp_path / 'warm', engine=scene_render, cache=tmp_path / 'cache')
    assert warm.work.engine_invocations == 0
    assert (cold.xml, cold.resources, cold.digest) == (warm.xml, warm.resources, warm.digest)
    frames = []
    for name in ('cold', 'warm'):
        output = tmp_path / (name + '.png')
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / name / 'scene.xml'),
                    '--time',
                    '0',
                    '--output',
                    str(output),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        pixels = plates.pixels(output)
        assert pixels.shape == (1920, 1080, 4) and np.all(pixels[..., 3] == 255)
        for material in ('support', 'cup', 'skin'):
            palette = [tuple(bytes.fromhex(color[1:])) for color in recipe.tones[material]]
            assert sum(np.count_nonzero(np.all(pixels[..., :3] == color, axis=2)) for color in palette) > 100
        frames.append(pixels)
    assert np.array_equal(*frames)
