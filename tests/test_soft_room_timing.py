"""Soft room framing and prop visibility must honor the supplied timeline."""

import hashlib
import json
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from srstudio import soft_front, soft_sets
from support.acting import evaluate
from support.soft_props import canvas

BUILDERS = (soft_sets.park, soft_sets.bedroom, soft_sets.playroom, soft_front.front_room)


def groups(cv):
    return {g.get('id'): g for g in ET.fromstring(cv.scene.to_bytes()).iter('group')}


@pytest.mark.parametrize('builder', BUILDERS, ids=lambda b: b.__name__)
def test_one_shot_frames_the_cast_and_leaves_foreground_untransformed(builder):
    cv = canvas()
    shot = soft_sets.Shot(0, 1.4, 300, 900)
    builder(cv, cv.comp, shots=(shot,), cast=lambda g: cv.group(g, 'cast'), id='set')
    nodes = groups(cv)
    room = nodes['set-room']
    assert [
        float(room.get(k, '1' if k.startswith('scale') else '0')) for k in ('x', 'y', 'scaleX', 'scaleY')
    ] == pytest.approx([120, -300, 1.4, 1.4])
    assert any(g.get('id') == 'cast' for g in room)
    front = nodes['set-front']
    assert not list(front.iter('animate'))
    assert all(front.get(k) is None for k in ('x', 'y', 'scaleX', 'scaleY'))


BAD_SHOTS = [
    (),
    (soft_sets.Shot(1),),
    (soft_sets.Shot(0, 0),),
    (soft_sets.Shot(0, True),),
    (soft_sets.Shot(0, x=float('nan')),),
    (soft_sets.Shot(0, y=float('inf')),),
    (soft_sets.Shot(0, x=True),),
    (soft_sets.Shot(0, 1e308, 1e308, 0),),
    (soft_sets.Shot(0), soft_sets.Shot(1, x=float('inf'))),
    (soft_sets.Shot(0), soft_sets.Shot(0.0000001, 2)),
]


@pytest.mark.parametrize('builder', BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize('shots', BAD_SHOTS)
def test_bad_framing_fails_before_scene_or_callback_mutation_and_allows_repair(builder, shots):
    cv = canvas()
    before = cv.scene.to_bytes()
    callbacks = []
    with pytest.raises(soft_sets.SoftSetError):
        builder(cv, cv.comp, shots=shots, cast=callbacks.append)
    assert cv.scene.to_bytes() == before and callbacks == []
    good = (soft_sets.Shot(0, 1.4, 300, 900),)
    builder(cv, cv.comp, shots=good)
    fresh = canvas()
    builder(fresh, fresh.comp, shots=good)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


@pytest.mark.parametrize('local', [False, True])
def test_wedged_sofa_has_one_held_visibility_track_for_its_intervals(local):
    cv = canvas()
    cv.local_time = local
    soft_front.front_room(cv, cv.comp, wedged=((1, 2), (4, 5)))
    sofa = groups(cv)['soft-front-room-sofa']
    animations = list(sofa.findall('animate'))
    assert len(animations) == 1
    a = animations[0]
    assert a.get('property') == 'opacity' and a.get('defaultInterpolation') == 'hold'
    assert a.get('timeBase', 'composition') == ('local' if local else 'composition')
    assert [(float(k.get('time')), float(k.get('value'))) for k in a] == [(0, 0), (1, 1), (2, 0), (4, 1), (5, 0)]


@pytest.mark.parametrize('builder', BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize('animated', [False, True])
def test_default_and_existing_multiple_shot_drawings_stay_unchanged(builder, animated):
    baseline = json.loads(Path('tests/data/soft-room-timing-baseline.json').read_text())
    cv = canvas()
    options = dict(shots=(soft_sets.Shot(0), soft_sets.Shot(2, 1.4, 300, 900))) if animated else {}
    builder(cv, cv.comp, **options)
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][f'{builder.__name__}:{animated}']


@pytest.mark.parametrize('local', [False, True])
def test_sofa_visibility_in_sequence_matches_real_engine_boundaries_and_random_access(local, scene_render, tmp_path):
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=2)
    shot = sequence.add_group(id='shot', end=7)
    soft_front.front_room(cv, shot, wedged=((3, 4), (5, 6)))
    path = tmp_path / 'sofa.xml'
    path.write_bytes(cv.scene.to_bytes())
    # Local animation time is measured from this sequence shot's start at composition second 2.
    shift = 2 if local else 0
    cases = [(5.5, 1), (2.5, 0), (3, 1), (4, 0), (4.5, 0), (6, 0), (5.5, 1)]
    states = []
    for time, opacity in cases:
        node = next(n for n in evaluate(scene_render, path, time + shift) if n['id'] == 'soft-front-room-sofa')
        assert node['world_opacity'] == pytest.approx(opacity)
        states.append(node)
    assert states[0] == states[-1]


@pytest.mark.parametrize('builder', BUILDERS, ids=lambda b: b.__name__)
def test_single_frame_matches_repeated_identical_shots_in_real_engine(builder, scene_render, tmp_path):
    shot = soft_sets.Shot(0, 1.4, 300, 900)
    outputs = []
    for index, shots in enumerate(((shot,), (shot, soft_sets.Shot(4, 1.4, 300, 900)))):
        cv = canvas()

        def cast(g, drawing=cv):
            drawing.group(g, 'actor', x=300, y=900)

        builder(cv, cv.comp, shots=shots, cast=cast, id='set')
        path = tmp_path / f'frame-{index}.xml'
        path.write_bytes(cv.scene.to_bytes())
        samples = []
        for time in (5, 1, 4, 5):
            nodes = evaluate(scene_render, path, time)
            actor = next(n for n in nodes if n['id'] == 'actor')
            front = next(n for n in nodes if n['id'] == 'set-front')
            assert actor['world'][4:6] == pytest.approx([540, 960])
            assert front['world'] == [1, 0, 0, 1, 0, 0]
            samples.append((actor['world'], front['world']))
        outputs.append(samples)
    assert outputs[0] == outputs[1]


def test_sofa_pixels_disappear_between_spans_and_return_on_random_access(scene_render, tmp_path):
    cv = canvas()
    soft_front.front_room(cv, cv.comp, wedged=((1, 2),))
    path = tmp_path / 'sofa.xml'
    path.write_bytes(cv.scene.to_bytes())
    frames = []
    for index, frame in enumerate((75, 45, 15, 45)):
        output = tmp_path / f'sofa-{index}.png'
        subprocess.run(
            [str(scene_render), 'render', str(path), '-f', str(frame), '-o', str(output)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        with Image.open(output) as image:
            frames.append(np.asarray(image.convert('RGB')))
    assert np.array_equal(frames[0], frames[2])
    assert np.array_equal(frames[1], frames[3])
    difference = np.any(frames[1] != frames[0], axis=2)
    x, y, width, height = map(int, soft_front.DOOR)
    assert difference[y : y + height, x : x + width].sum() > 1000
    # Everything outside the doorway belongs to the unchanged room, wall and foreground.
    difference[y : y + height, x : x + width] = False
    assert not difference.any()


def test_soft_room_framing_guide_executes():
    doc = Path('docs/authoring-styles.md').read_text()
    block = doc.split('<!-- soft-room-framing:start -->')[1].split('<!-- soft-room-framing:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<soft-room-framing>', 'exec'), {})
