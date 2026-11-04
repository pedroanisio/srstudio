"""Bounded discovery and diagnostics that identify the agent's incorrect field."""

import json

import pytest

from srstudio import registry
from srstudio.cli import main
from srstudio.contracts import PartContract


@pytest.mark.parametrize('lookup', [registry.get, registry.describe])
def test_unknown_kind_identifies_kind_instead_of_name(lookup):
    with pytest.raises(registry.RegistryError) as caught:
        lookup('porp', 'coffee-cup')
    error = caught.value.to_dict()
    assert error['path'] == 'kind' and error['actual'] == 'porp'
    assert error['expected'] == list(registry.KINDS)


@pytest.mark.parametrize('lookup', [registry.entries, registry.catalog, registry.contract_coverage])
def test_unknown_style_is_not_a_list_of_shared_parts(lookup):
    with pytest.raises(registry.RegistryError) as caught:
        lookup(style='tooon')
    error = caught.value.to_dict()
    assert error['path'] == 'style' and 'toon' in error['expected']


def test_custom_plugin_styles_remain_discoverable(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})
    registry.register('prop', 'demo', style='custom-style')(lambda: None)
    assert [p['name'] for p in registry.catalog(style='custom-style', kind='prop')] == ['demo']


def test_search_pages_are_stable_complete_and_compact():
    all_names = sorted((e.kind, e.name) for e in registry.entries())
    result = registry.search(limit=7)
    assert result['total'] == len(all_names)
    assert result['next_offset'] == 7
    assert [(r['kind'], r['name']) for r in result['items']] == all_names[:7]
    page = registry.search(limit=7, offset=result['next_offset'])
    assert [(r['kind'], r['name']) for r in page['items']] == all_names[7:14]
    assert len(json.dumps(result)) < 5000
    assert registry.search(offset=len(all_names))['next_offset'] is None


def test_search_only_claims_explicit_capabilities(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})
    for name, support in [('yes', True), ('no', False), ('unknown', None)]:
        registry.register('prop', name, contract=PartContract(capabilities=(('limbs', support),)))(lambda: None)
    result = registry.search(kind='prop', capabilities=('limbs',))
    assert [r['name'] for r in result['items']] == ['yes']


def test_cli_search_and_selected_inspection_fields(capsys):
    assert main(['catalog', '--search', 'coffee', '--kind', 'prop', '--limit', '3', '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert 0 < len(result['items']) <= 3
    assert main(['inspect', 'character', 'manager', '--fields', 'name,contract.capabilities', '--json']) == 0
    detail = json.loads(capsys.readouterr().out)
    assert set(detail) == {'name', 'contract'}
    assert set(detail['contract']) == {'capabilities'}


@pytest.mark.parametrize(
    'options, path',
    [
        (['--limit', '0'], 'limit'),
        (['--offset', '-1'], 'offset'),
        (['--capability', 'limbz'], 'capabilities'),
        (['--fields', 'nmae'], 'fields'),
    ],
)
def test_bad_discovery_options_are_repairable(options, path, capsys):
    assert main(['catalog', '--json', *options]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error['path'] == path and error['remedy']


def test_nested_selection_reports_a_scalar_parent_as_invalid(capsys):
    assert main(['inspect', 'prop', 'coffee-cup', '--fields', 'name,name.typo', '--json']) == 2
    assert json.loads(capsys.readouterr().err)['path'] == 'fields'


def test_cli_style_validation_matches_sdk(capsys):
    assert main(['catalog', '--style', 'tooon', '--json']) == 2
    error = json.loads(capsys.readouterr().err)
    assert error['path'] == 'style' and 'toon' in error['expected']


def test_selected_catalog_fields_have_identical_python_and_json_shapes(capsys):
    fields = ('name', 'tags', 'part_version')
    expected = registry.search('coffee', fields=fields)
    assert main(['catalog', '--search', 'coffee', '--fields', ','.join(fields), '--json']) == 0
    assert json.loads(capsys.readouterr().out) == expected
