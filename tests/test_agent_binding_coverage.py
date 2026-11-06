"""Agents can distinguish runtime dependencies from unresolved authoring data."""

from dataclasses import dataclass
from typing import Any

from srstudio import Canvas, registry
from srstudio.contracts import describe_callable


@dataclass
class Settings:
    gain: float
    extra: Any = None


def complete(cv: Canvas, amount: float = 1) -> None:
    pass


def incomplete(cv: Canvas, settings: Settings) -> None:
    pass


def test_runtime_binding_does_not_make_data_shape_incomplete():
    contract = describe_callable(complete)
    assert not contract['shape_complete']
    binding = contract['binding']
    assert binding['data_shape_complete']
    assert binding['unresolved_fields'] == []
    assert binding['runtime_bindings'] == [
        {
            'path': '/arguments/properties/cv',
            'required': True,
            'conditional': False,
            'python_type': 'srstudio.canvas.Canvas',
        }
    ]


def test_unknown_nested_data_identifies_its_schema_path():
    binding = describe_callable(incomplete)['binding']
    assert not binding['data_shape_complete']
    assert binding['unresolved_fields'][0]['path'] == '/arguments/properties/settings/properties/extra'
    assert not binding['unresolved_fields'][0]['required']


def test_coverage_separates_data_gaps_runtime_bindings_and_examples():
    report = registry.contract_coverage(kind='character')
    counts = report['kinds']['character']
    contracts = [entry.describe() for entry in registry.entries('character')]
    assert counts['data_shape_complete'] == sum(c['contract']['binding']['data_shape_complete'] for c in contracts)
    assert counts['with_runtime_bindings'] > 0
    assert counts['with_examples'] == sum(bool(c['examples']) for c in contracts)
    assert counts['unresolved_parts'] == sorted(
        c['name'] for c in contracts if c['contract']['binding']['unresolved_fields']
    )
