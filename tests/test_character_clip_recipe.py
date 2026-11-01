"""The normalized character-placement recipe remains executable public Python."""

from pathlib import Path


def test_two_family_recipe_has_one_local_clock_and_distinct_source_anchors():
    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-clips.md').read_text()
    section = text.split('<!-- character-clips:start -->')[1].split('<!-- character-clips:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'character-clip-recipe', 'exec'), namespace)
    assert namespace['scene'].check(schema=True) == []
    for name in ('speaker', 'listener'):
        group = namespace[name]
        assert group.start == 3
        assert group.end == 5
        assert group.timeOffset == 3
    assert namespace['listener'].anchorY == 0
