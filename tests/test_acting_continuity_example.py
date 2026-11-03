"""Listening and carried props share a source clock, including inside sequence shots."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from srstudio.acting import BENTO, ActingError, compile_performance, gloss_actor, parse_score
from srstudio.limbs.serialization import load_motion
from srstudio.sample import SYSTEM_FONTS


def example():
    path = Path(__file__).resolve().parents[1] / 'examples/acting_continuity.py'
    spec = importlib.util.spec_from_file_location('acting_continuity', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sustained_listening_responds_to_each_line_without_speaking():
    score = example().listening_score()
    plan = compile_performance(BENTO, score)
    assert len(score.heard) == 3
    for line in score.heard:
        start, end = line.at, line.at + max(line.alignment.ends) + 0.6
        samples = [plan.sample(start + (end - start) * i / 40) for i in range(41)]
        assert all(s.mouth == 'closed' and s.gaze == 'right' for s in samples)
        assert max(s.head.nod for s in samples) > 0.5
    with pytest.raises(ActingError) as caught:
        compile_performance(gloss_actor('nadia'), score)
    assert caught.value.to_dict()['code'] == 'acting.unsupported'


def test_carried_prop_is_moving_at_the_cut_and_returns_to_its_support():
    motion = example().carry_motion()
    assert motion.prop_frame('cup', 3.01).origin.distance(motion.prop_frame('cup', 2.99).origin) > 1e-4
    for time in (4.1, 3, 1.2, 2.5):
        attachment = motion.attachments[0]
        assert motion.prop_frame('cup', time) == motion.sample(time).hand.frame.compose(attachment.offset)
    assert motion.prop_frame('cup', 0).origin.distance(motion.prop_frame('cup', 5.9).origin) < 1e-6


@pytest.mark.skipif(not any(p.is_file() for p in SYSTEM_FONTS), reason='DejaVu Sans is required')
def test_example_binds_hand_and_prop_to_the_same_cut_clock(tmp_path, scene_render):
    path = example().build(tmp_path / 'continuity', fps=6)
    report = json.loads(path.with_name('continuity-report.json').read_text())
    assert report['listening']['mouth_always_closed']
    assert report['continuity']['listener_equal'] and report['continuity']['prop_equal']
    assert report['motion']['max_contact_error'] < 1e-6
    assert report['source']['audio'] == 'none; silent synthetic planning fixture'
    assert report['validation'] == {'schema': True, 'findings': []}
    score = parse_score(json.loads(path.with_name('listening.score.json').read_text()))
    assert compile_performance(BENTO, score).sample(3) == compile_performance(
        BENTO, example().listening_score()
    ).sample(3)
    motion = load_motion(path.with_name('carry.motion.json'))
    assert motion.prop_frame('cup', 3).origin.distance(motion.prop_frame('cup', 2).origin) > 0.01
    subprocess.run([str(scene_render), 'validate', str(path), '--deny-warnings'], check=True, capture_output=True)
    for time in (3.25, 1.5, 5.25, 3):
        result = json.loads(
            subprocess.check_output([str(scene_render), 'eval', str(path), '--time', str(time), '--json'])
        )
        active = [
            n['id'] for n in result['result']['nodes'] if '-interaction-frame-' in n['id'] and n['world_opacity'] > 0.5
        ]
        shot = 'wide' if time < 3 else 'close'
        assert active == [f'{shot}-interaction-frame-{int(time * 6):06d}']


@pytest.mark.parametrize('recipe', ['listening', 'carrying'])
def test_cross_system_documentation_is_executable(recipe):
    path = Path(__file__).resolve().parents[1] / 'docs/authoring-acting.md'
    section = path.read_text().split(f'<!-- {recipe}:start -->')[1].split(f'<!-- {recipe}:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, f'{recipe}-recipe', 'exec'), namespace)
    if recipe == 'listening':
        assert namespace['listener'].sample(1.1).mouth == 'closed'
        assert namespace['diagnostic']['code'] == 'acting.unsupported'
    else:
        assert namespace['source'].sample(3) == namespace['after_cut'].sample(0)
