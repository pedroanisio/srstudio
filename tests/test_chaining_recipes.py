"""Agent-facing action chaining recipes execute against the production API."""

from pathlib import Path


def test_documented_chaining_recipe_preserves_the_original_and_flows_between_gestures():
    text = (Path(__file__).resolve().parents[1] / 'docs/catalog/limbs.md').read_text()
    section = text.split('<!-- action-chain:start -->')[1].split('<!-- action-chain:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'action-chain-recipe', 'exec'), namespace)
    source, motion = namespace['source'], namespace['motion']
    assert source.joins == ()
    assert motion.sample(2).phase == 'transition'
    assert motion.sample(1) == source.sample(1)
    assert motion.sample(3.5) == source.sample(3.5)
