"""Rig vocabulary constraints shared by the JSON schema and executable adapters."""

from dataclasses import fields

from . import registry
from ._authoring_records import FAMILIES, ActorInputs, StickInputs


def argument_constraints(name: str) -> dict:
    record = next(record for record, names in FAMILIES.values() if name in names)
    contract = registry.describe('character', name)['contract']
    properties = contract['arguments']['properties']
    if record is ActorInputs:
        performance = contract['operations']['build']['arguments']['properties']['perf']
        properties = next(branch['properties'] for branch in performance['anyOf'] if branch.get('type') == 'object')

    def enums(node):
        result = {}
        alternatives = node.get('anyOf', ())
        non_null = [branch for branch in alternatives if branch.get('type') != 'null']
        if len(non_null) == 1 and len(non_null) < len(alternatives):
            # Adapter records already specify whether null is allowed. Keep the
            # vocabulary of the actual array/object inside a legacy Optional.
            result.update(enums(non_null[0]))
        if 'enum' in node:
            result['enum'] = node['enum']
        if 'properties' in node:
            result['properties'] = {key: enums(value) for key, value in node['properties'].items()}
        if 'items' in node:
            result['items'] = enums(node['items'])
        if 'prefixItems' in node:
            result['prefixItems'] = [enums(child) for child in node['prefixItems']]
        return result

    result = {'properties': {f.name: enums(properties.get(f.name, {})) for f in fields(record)}}
    if record is StickInputs:
        # The closed adapter uses the builder's default pose sheet.
        result['properties']['keys']['items']['properties']['pose']['enum'] = contract['vocabularies']['default_poses']
    return result


def validate_vocabularies(value, constraints, fail, path='arguments'):
    if 'enum' in constraints and value not in constraints['enum']:
        raise fail(path, value, constraints['enum'])
    if isinstance(value, dict):
        for name, child in value.items():
            validate_vocabularies(child, constraints.get('properties', {}).get(name, {}), fail, f'{path}.{name}')
    elif isinstance(value, (list, tuple)):
        prefix = constraints.get('prefixItems', ())
        for i, child in enumerate(value):
            shape = prefix[i] if i < len(prefix) else constraints.get('items', {})
            validate_vocabularies(child, shape, fail, f'{path}[{i}]')
