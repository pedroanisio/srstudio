"""Agents discover callable helpers without attributing their capabilities to static builders."""

import json

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, registry
from srstudio.cli import main
from srstudio.contracts import Operation, PartContract
from srstudio.head_motion import Channel, HeadPlan
from srstudio.toon import Pose
from srstudio.toon_bento import pose_of


@pytest.mark.parametrize('name', ['toon-lyra', 'toon-fox@2', 'toon-sloth', 'toon-goat', 'toon-hamster'])
def test_each_supported_head_rig_has_an_executable_operation(name):
    page = registry.search(name, kind='character', capabilities=('head_motion',), operations=True)
    assert page['total'] == 1
    row = page['items'][0]
    assert row['name'] == name and row['operation'] == 'head_performance'
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None)
    result = registry.get('character', name).operation('head_performance')(
        cv,
        cv.comp,
        [Pose(0, 'wide', 'flat', 'desk')],
        duration=2,
        plan=HeadPlan(nod=Channel(((0, 0), (1, 1)), curve='sine-in-out')),
    )
    assert result is not None and list(result.iter('animate'))
    assert not scene.check()


def test_head_performance_operations_are_paged_and_executable(capsys):
    first = registry.search('bento', kind='character', capabilities=('head_motion',), operations=True, limit=1)
    assert first['scope'] == 'operations'
    assert first['total'] == 2 and first['next_offset'] == 1
    second = registry.search('bento', kind='character', capabilities=('head_motion',), operations=True, offset=1)
    assert second['next_offset'] is None
    for row in [*first['items'], *second['items']]:
        entry = registry.get(row['kind'], row['name'])
        info = entry.describe()['contract']
        assert info['capabilities']['head_motion'] is False
        operation = info['operations'][row['operation']]
        assert operation['capabilities']['head_motion'] is True
        assert operation['arguments']['properties']['duration']['x-role'] == 'end'
        scene = Scene(version='auto')
        scene.add_project(width=1080, height=1920, fps='24', duration=2)
        cv = Canvas(scene, font_asset=None)
        group = entry.operation(row['operation'])(
            cv,
            cv.comp,
            [pose_of(0, 'neutral')],
            duration=2,
            plan=HeadPlan(nod=Channel(((0, 0), (1, 1)), curve='sine-in-out')),
        )
        assert group is not None and list(group.iter('animate'))
        assert not scene.check()
    assert registry.search('bento', capabilities=('head_motion',))['total'] == 0
    assert (
        main(
            [
                'catalog',
                '--operations',
                '--search',
                'bento',
                '--kind',
                'character',
                '--capability',
                'head_motion',
                '--limit',
                '1',
                '--json',
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == first


def test_operation_filters_do_not_combine_capabilities_of_different_helpers(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    def helper():
        return None

    contract = PartContract(
        operations=(
            Operation('head', helper, PartContract(capabilities=(('head_motion', True),))),
            Operation('arms', helper, PartContract(capabilities=(('limbs', True),))),
        )
    )
    registry.register('prop', 'helpers', contract=contract)(helper)
    assert registry.search(kind='prop', operations=True, capabilities=('head_motion', 'limbs'))['total'] == 0
    entry = registry.get('prop', 'helpers')
    entry.builder = lambda: None
    assert registry.search(kind='prop', operations=True)['total'] == 0
    with pytest.raises(registry.RegistryError) as caught:
        entry.operation('head')
    assert caught.value.to_dict()['path'] == 'operation'


def test_operation_lookup_failure_lists_supported_helpers():
    with pytest.raises(registry.RegistryError) as caught:
        registry.get('character', 'toon-bento').operation('typo')
    diagnostic = caught.value.to_dict()
    assert diagnostic['path'] == 'operation' and 'head_performance' in diagnostic['expected']


def test_operation_only_capabilities_are_known_to_search(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    def helper():
        return None

    registry.register(
        'prop',
        'helpers',
        contract=PartContract(
            operations=(Operation('custom', helper, PartContract(capabilities=(('custom-motion', True),))),)
        ),
    )(helper)
    assert registry.search(kind='prop', operations=True, capabilities=('custom-motion',))['total'] == 1


def test_non_boolean_operation_scope_is_a_repairable_error():
    with pytest.raises(registry.RegistryError) as caught:
        registry.search(operations='yes')
    assert caught.value.to_dict()['path'] == 'operations'
