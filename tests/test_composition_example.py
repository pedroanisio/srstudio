"""The manifest example prepares its actual approved part and declares conservative source bounds."""

import importlib.util
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def test_real_prepared_papers_fit_the_declared_source_bounds_and_rebuild_identically():
    path = Path(__file__).parents[1] / 'examples' / 'composition_preflight.py'
    spec = importlib.util.spec_from_file_location('composition_preflight_example', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plan, xml = module.build_manifest()
    assert module.build_manifest() == (plan, xml)
    root = ET.fromstring(xml)
    binding = plan.bindings[0]
    assert binding.nodes == sum(1 for _ in root.iter())
    assert binding.memory_bytes == len(xml) * 8
    assert plan.cost.frames == 24 and plan.cost.unique_plates == 0
    paths = root.findall(".//shape[@shape='path']")
    assert paths
    for node in paths:
        data = node.attrib['path']
        assert set(re.findall('[A-Za-z]', data)) <= set('MLQZ')
        numbers = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', data)]
        assert len(numbers) % 2 == 0
        stroke = float(node.get('strokeWidth', 0))
        for x, y in zip(numbers[::2], numbers[1::2], strict=True):
            assert binding.bounds.minimum[0] <= x - stroke <= x + stroke <= binding.bounds.maximum[0]
            assert binding.bounds.minimum[1] <= y - stroke <= y + stroke <= binding.bounds.maximum[1]
