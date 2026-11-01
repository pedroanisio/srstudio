"""Agents can inspect shapes and semantics without constructing or drawing a part."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import pytest

from srstudio import parts, registry, toon_bento


def test_every_part_exposes_a_serializable_versioned_contract():
    for entry in registry.entries():
        contract = entry.describe()['contract']
        assert contract['schema'] == 'srstudio.part-contract/1.0.0'
        assert 'additionalProperties' in contract['arguments']
        assert contract['validation'] == 'runtime-required'
        assert json.loads(json.dumps(contract, allow_nan=False)) == contract


@dataclass
class Cue:
    time: float
    mode: Literal['hold', 'pass']
    offset: tuple[float, float] = (0, 0)


def test_nested_records_literals_nullable_sequences_and_tuple_arity(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    @registry.register('prop', 'cues')
    def builder(cues: Sequence[Cue], label: str | None = None) -> int:
        raise AssertionError('inspection cannot call a builder')

    contract = registry.describe('prop', 'cues')['contract']
    arguments = contract['arguments']
    assert arguments['required'] == ['cues']
    cue = arguments['properties']['cues']['items']
    assert cue['required'] == ['time', 'mode']
    assert cue['additionalProperties'] is False
    assert cue['properties']['mode']['enum'] == ['hold', 'pass']
    offset = cue['properties']['offset']
    assert offset['prefixItems'] == [{'type': 'number'}, {'type': 'number'}]
    assert offset['minItems'] == 2 and offset['maxItems'] == 2
    assert arguments['properties']['label']['anyOf'] == [{'type': 'string'}, {'type': 'null'}]
    assert arguments['properties']['label']['default'] is None
    assert contract['returns'] == {'type': 'integer'}
    assert contract['shape_complete'] is True


def test_explicit_constraints_units_and_clocks_reach_the_cli(monkeypatch, capsys):
    from srstudio.cli import main
    from srstudio.contracts import ParameterContract, PartContract

    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    @registry.register(
        'prop',
        'timed',
        contract=PartContract(
            parameters=(
                ('end', ParameterContract(unit='seconds', timebase='project', role='end', minimum=0)),
                ('gain', ParameterContract(minimum=0, maximum=1)),
            ),
            capabilities=(('head_motion', False),),
        ),
    )
    def builder(end: float, gain: float = 0.5):
        raise AssertionError('inspection cannot draw')

    assert main(['inspect', 'prop', 'timed', '--json']) == 0
    contract = json.loads(capsys.readouterr().out)['contract']
    end = contract['arguments']['properties']['end']
    assert (end['x-unit'], end['x-timebase'], end['x-role']) == ('seconds', 'project', 'end')
    assert end['minimum'] == 0
    assert contract['arguments']['properties']['gain']['maximum'] == 1
    assert contract['capabilities']['head_motion'] is False
    assert contract['capabilities']['limbs'] is None


def test_unknown_annotations_do_not_hide_resolvable_fields_or_invent_types(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    @registry.register('prop', 'partial')
    def builder(size=1, known: float = 0, unavailable: 'MissingPluginType' = None):  # noqa: F821
        pass

    contract = registry.describe('prop', 'partial')['contract']
    properties = contract['arguments']['properties']
    assert properties['size']['x-status'] == 'unknown'
    assert 'type' not in properties['size']
    assert properties['known']['type'] == 'number'
    assert properties['unavailable']['x-status'] == 'unknown'
    assert contract['shape_complete'] is False


def test_recursive_types_are_bounded_and_default_factories_are_never_called(monkeypatch):
    from srstudio.contracts import describe_callable

    @dataclass
    class Recursive:
        children: list['Recursive'] = field(default_factory=lambda: pytest.fail('factory called'))

    def builder(node: Recursive):
        pytest.fail('builder called')

    # Resolve the local type explicitly, as a plugin would expose its public records at module scope.
    monkeypatch.setitem(globals(), 'Recursive', Recursive)
    contract = describe_callable(builder)
    assert len(json.dumps(contract)) < 10000
    assert contract['shape_complete'] is False


def test_bad_metadata_is_rejected_before_replacing_a_registered_builder(monkeypatch):
    from srstudio.contracts import ContractError, ParameterContract, PartContract

    monkeypatch.setitem(registry._REGISTRY, 'prop', {})
    original = registry.register('prop', 'safe')(lambda size: None)
    with pytest.raises(ContractError, match='missing'):
        registry.register(
            'prop',
            'safe',
            replace=True,
            contract=PartContract(parameters=(('missing', ParameterContract(unit='pixels')),)),
        )(lambda size: None)
    assert registry.get('prop', 'safe').builder is original


def test_restore_restores_contract_metadata_with_the_original_builder(monkeypatch):
    from srstudio.contracts import PartContract

    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    before = registry.describe('character', 'manager')['contract']
    registry.register('character', 'manager', replace=True, contract=PartContract(capabilities=(('limbs', False),)))(
        lambda cv: None
    )
    assert registry.describe('character', 'manager')['contract']['capabilities']['limbs'] is False
    parts.restore('manager')
    assert registry.describe('character', 'manager')['contract'] == before


def test_actor_contract_distinguishes_construction_from_build_and_lists_capabilities():
    contract = registry.describe('character', 'manager')['contract']
    assert contract['invocation'] == 'construct'
    assert contract['capabilities']['limbs'] is True
    assert contract['arguments']['properties']['canvas']['x-status'] == 'runtime'
    build = contract['operations']['build']
    assert 'self' not in build['arguments']['properties']
    assert build['arguments']['properties']['x']['x-unit'] == 'parent units'
    assert build['arguments']['properties']['scale']['x-unit'] == 'ratio'
    assert 'facepalm' in contract['vocabularies']['extras']
    performance = build['arguments']['properties']['perf']['anyOf'][0]['properties']
    nod_key = performance['nods']['items']['prefixItems']
    assert nod_key[0]['x-timebase'] == 'canvas'
    assert nod_key[0]['x-unit'] == 'seconds'
    assert nod_key[1]['x-unit'] == 'degrees'
    assert performance['mouth']['items']['prefixItems'][1]['enum'] == contract['vocabularies']['mouths']


def test_bento_contract_exposes_real_pose_vocabulary_and_mixed_clocks():
    contract = registry.describe('character', 'toon-bento')['contract']
    properties = contract['arguments']['properties']
    assert properties['duration']['x-role'] == 'end'
    assert properties['duration']['x-timebase'] == 'project'
    start = properties['poses']['items']['properties']['start']
    assert start['x-timebase'] == 'relative:enter'
    assert start['x-unit'] == 'seconds'
    assert contract['capabilities']['limbs'] is False
    assert contract['capabilities']['head_motion'] is False
    pose = contract['operations']['pose_of']['arguments']['properties']
    assert pose['name']['enum'] == list(toon_bento.MOODS)
    assert pose['eyes']['enum'] == [None, *toon_bento.EYE_STATES]
    assert contract['operations']['pose_of']['returns']['properties']['start']['type'] == 'number'


@pytest.mark.parametrize(
    'options', [{'minimum': 2, 'maximum': 1}, {'minimum': float('nan')}, {'enum': ('ok', object())}]
)
def test_invalid_parameter_metadata_is_a_typed_error(options):
    from srstudio.contracts import ContractError, ParameterContract

    with pytest.raises(ContractError):
        ParameterContract(**options)


def test_typed_dictionaries_and_annotated_values_keep_field_constraints():
    from srstudio.contracts import ParameterContract, describe_callable

    class Options(TypedDict):
        intensity: Annotated[float, ParameterContract(minimum=0, maximum=1)]

    def builder(options: Options):
        pass

    schema = describe_callable(builder)['arguments']['properties']['options']
    assert schema['type'] == 'object' and schema['required'] == ['intensity']
    assert schema['properties']['intensity'] == {'type': 'number', 'minimum': 0, 'maximum': 1}
    assert schema['additionalProperties'] is False


def test_variadic_keywords_remain_explicit_instead_of_claiming_a_closed_contract():
    from srstudio.contracts import describe_callable

    def builder(name: str, **attributes: float):
        pass

    schema = describe_callable(builder)['arguments']
    assert schema['additionalProperties']['type'] == 'number'
    assert schema['additionalProperties']['x-python-kind'] == 'VAR_KEYWORD'
    assert 'attributes' not in schema['properties']


def test_actor_overriding_build_is_not_given_the_base_placement_contract(monkeypatch):
    from srstudio import cast

    monkeypatch.setitem(registry._REGISTRY, 'character', {})

    @registry.register('character', 'custom-actor')
    class Custom(cast.Manager):
        def build(self, parent, position: tuple[float, float]):
            raise AssertionError('inspection cannot draw')

    properties = registry.describe('character', 'custom-actor')['contract']['operations']['build']['arguments'][
        'properties'
    ]
    assert set(properties) == {'parent', 'position'}
    assert properties['position']['minItems'] == 2


def test_documented_plugin_contract_matches_its_success_and_failure_paths(monkeypatch):
    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.canvas import CanvasError

    monkeypatch.setitem(registry._REGISTRY, 'prop', {})
    document = Path('docs/authoring-discovery.md').read_text()
    example = document.split('<!-- contract-plugin:start -->', 1)[1].split('<!-- contract-plugin:end -->', 1)[0]
    source = example.split('```python\n', 1)[1].split('```', 1)[0]
    exec(compile(source, '<contract-plugin>', 'exec'), {'__name__': __name__})
    entry = registry.get('prop', 'agent-marker')
    opacity = entry.describe()['contract']['arguments']['properties']['opacity']
    assert opacity['minimum'] == 0 and opacity['maximum'] == 1
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None)
    group = entry(cv, cv.comp, opacity=0.5)
    assert group.opacity == 0.5
    before = scene.to_bytes()
    with pytest.raises(CanvasError) as caught:
        entry(cv, cv.comp, opacity=2)
    assert caught.value.to_dict()['code'] == 'marker.opacity'
    assert scene.to_bytes() == before


def test_inherited_record_fields_resolve_their_annotations():
    from srstudio.contracts import describe_callable

    @dataclass
    class Base:
        time: 'float'

    @dataclass
    class Extended(Base):
        strength: float = 1

    def builder(record: Extended):
        pass

    record = describe_callable(builder)['arguments']['properties']['record']
    assert record['properties']['time']['type'] == 'number'


def test_invalid_operation_metadata_is_rejected_with_a_typed_error():
    from srstudio.contracts import ContractError, Operation

    with pytest.raises(ContractError):
        Operation(1, lambda: None)
