"""The discovery-to-drawing recipe uses the same public API an authoring agent receives."""

from pathlib import Path


def test_character_discovery_recipe_builds_on_a_nonzero_project_interval():
    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md').read_text()
    section = text.split('<!-- character-discovery:start -->')[1].split('<!-- character-discovery:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'character-discovery-recipe', 'exec'), namespace)
    assert namespace['groups'][0].attributes()['start'] == '3'
    assert namespace['groups'][0].attributes()['end'] == '4'
    assert namespace['pose'].start == 0


def test_helper_discovery_recipe_builds_an_animated_head():
    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md').read_text()
    section = text.split('<!-- helper-discovery:start -->')[1].split('<!-- helper-discovery:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'helper-discovery-recipe', 'exec'), namespace)
    assert list(namespace['group'].iter('animate'))
