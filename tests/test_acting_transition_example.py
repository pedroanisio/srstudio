"""The transition study exposes reproducible scores, real cut clocks and explicit quality limits."""

import importlib.util
import json
import stat
import subprocess
from pathlib import Path

from srstudio.acting import BENTO, compile_performance, parse_score


def example():
    path = Path(__file__).resolve().parents[1] / 'examples/acting_transitions.py'
    spec = importlib.util.spec_from_file_location('acting_transition_example', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_study_has_comparable_intent_with_observable_timing_and_real_cut_windows(tmp_path, scene_render):
    path = example().build(tmp_path / 'study')
    report = json.loads(path.with_name('transition-report.json').read_text())
    assert report['schema'] == 'srstudio.acting-transitions/1.0.0'
    assert report['cuts'] == [1.1, 2.1]
    assert report['human_ratings'] is None
    assert report['continuity']['velocity'] is False
    assert report['continuity']['acceleration'] is False
    assert len(report['variants']) == 3
    plans = {}
    for row in report['variants']:
        score = json.loads(path.with_name(row['score_file']).read_text())
        plans[row['name']] = compile_performance(BENTO, parse_score(score))
        assert all(row['cut_state_equal'])
    assert plans['legacy'].sample(1.4).emotion == 'neutral'
    assert plans['anticipation'].sample(1.4).emotion == 'happy'
    assert plans['anticipation'].sample(1.2).head.turn < plans['legacy'].sample(1.2).head.turn
    assert plans['spring'].sample(2.4).head.turn == plans['legacy'].sample(2.4).head.turn
    subprocess.run([str(scene_render), 'validate', str(path), '--deny-warnings'], capture_output=True, check=True)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_documented_policy_recipe_executes_with_explicit_timing():
    path = Path(__file__).resolve().parents[1] / 'docs/authoring-acting.md'
    section = path.read_text().split('<!-- acting-policy:start -->')[1].split('<!-- acting-policy:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'acting-policy-recipe', 'exec'), namespace)
    plan = namespace['plan']
    assert plan.sample(1.1).emotion == 'happy'
    assert plan.window(0.9, 3).sample(0.2) == plan.sample(1.1)
