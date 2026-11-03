"""Discovery publishes authored drawing semantics independently of inferred argument shapes."""

import inspect
import json

import pytest
from sr_core.scene import Group, Layer, Scene

from srstudio import Canvas, cli, cutout_counter, locations, registry
from srstudio.contracts import ContractError, ParameterContract, PartContract, describe_callable
from srstudio.signature import SignatureError


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=5)
    return Canvas(scene, font_asset=None)


def test_core_noncharacter_families_have_explicit_contracts():
    entries = [
        e for e in registry.entries() if e.module in ('srstudio.props', 'srstudio.locations', 'srstudio.graphics')
    ]
    assert len(entries) == 52
    assert not [e.name for e in entries if e.contract is None]
    for entry in entries:
        contract = entry.describe()['contract']
        assert contract['arguments']['properties']['cv']['x-status'] == 'runtime'
        if 'parent' in contract['arguments']['properties']:
            assert 'x-status' in str(contract['arguments']['properties']['parent'])
        assert contract['constraints']
        assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_cup_discloses_local_anchors_and_placement_without_claiming_spatial_attachment():
    info = registry.describe('prop', 'coffee-cup')['contract']
    params = info['arguments']['properties']
    assert params['x']['x-unit'] == params['y']['x-unit'] == 'parent units'
    assert params['rotation']['x-unit'] == 'degrees'
    assert params['shadow']['type'] == 'boolean'
    assert info['returns']['x-space'] == 'returned-group'
    assert info['returns']['x-anchors']['origin'] == [0, 0]
    assert info['returns']['x-anchors']['base'] == [0, 61.5]
    assert info['capabilities']['spatial_attachment'] is False
    assert 'shadow=False' in ' '.join(info['constraints'])
    cv = canvas()
    cup = registry.get('prop', 'coffee-cup')(cv, cv.comp, 120, 340, scale=2, rotation=12, shadow=False)
    assert isinstance(cup, Group)
    assert {k: cup.attributes()[k] for k in ('x', 'y', 'scaleX', 'rotation')} == {
        'x': '120',
        'y': '340',
        'scaleX': '2',
        'rotation': '12',
    }
    assert cv.scene.check(schema=True) == []


def test_return_metadata_is_inspected_without_invoking_the_builder():
    def builder():
        raise AssertionError('discovery must not execute a builder')

    contract = PartContract(
        returns=ParameterContract(type=Group, unit='drawing units', space='returned-group', anchors=(('grip', (2, 3)),))
    )
    result = describe_callable(builder, contract)
    assert result['returns']['x-python-type'].endswith('.Group')
    assert result['returns']['x-anchors'] == {'grip': [2, 3]}


@pytest.mark.parametrize(
    'anchors',
    [
        (('a', (1, float('nan'))),),
        (('a', (True, 0)),),
        (('a', (10**5000, 0)),),
        (('a', (0,)),),
        (('a', (0, 0)), ('a', (1, 1))),
    ],
)
def test_invalid_anchor_metadata_is_refused(anchors):
    with pytest.raises(ContractError):
        ParameterContract(unit='drawing units', space='returned-group', anchors=anchors)


@pytest.mark.parametrize('missing', ['unit', 'space'])
def test_anchors_require_explicit_units_and_space(missing):
    values = dict(unit='drawing units', space='returned-group', anchors=(('grip', (0, 0)),))
    del values[missing]
    with pytest.raises(ContractError):
        ParameterContract(**values)


def test_coverage_separates_declaration_from_shape_inference(monkeypatch, capsys):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    @registry.register('prop', 'annotated-only')
    def inferred(size: float) -> None:
        raise AssertionError('must not draw')

    @registry.register(
        'prop',
        'declared',
        contract=PartContract(parameters=(('size', ParameterContract(type=float, unit='parent units')),)),
    )
    def declared(size):
        raise AssertionError('must not draw')

    result = registry.contract_coverage(kind='prop')
    assert result['schema'] == 'srstudio.contract-coverage/1.0.0'
    assert result['kinds']['prop']['registered'] == 2
    assert result['kinds']['prop']['explicit_contracts'] == 1
    assert result['kinds']['prop']['shape_complete'] == 2
    assert result['kinds']['prop']['undeclared_parts'] == ['annotated-only']
    assert cli.main(['catalog', '--kind', 'prop', '--contract-coverage', '--json']) == 0
    assert json.loads(capsys.readouterr().out) == result


def test_reaching_hand_publishes_the_held_prop_slot_and_origin():
    info = registry.describe('prop', 'reaching-hand')['contract']
    assert info['arguments']['properties']['holds']['x-role'] == 'drawing-slot'
    assert info['returns']['x-anchors']['grip'] == [0, 0]
    assert info['capabilities']['spatial_attachment'] is False


@pytest.mark.parametrize('holds', [False, 123])
def test_reaching_hand_rejects_invalid_slot_before_drawing(holds):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(cutout_counter.CutoutCounterError) as caught:
        cutout_counter.reaching_hand(cv, cv.comp, holds=holds)
    assert caught.value.to_dict()['path'] == 'holds'
    assert caught.value.to_dict()['remedy']
    assert cv.scene.to_bytes() == before and cv._serial == 0


def test_cafe_menu_contract_matches_the_actual_boundary():
    info = registry.describe('location', 'cafe')['contract']
    assert f'at most {locations.MENU_CHARS} characters' in ' '.join(info['constraints'])
    cv = canvas()
    cv.font_asset = 'caption-font'
    locations.cafe(cv, cv.comp, menu=('x' * locations.MENU_CHARS,) * 3)
    bad = canvas()
    before = bad.scene.to_bytes()
    with pytest.raises(locations.LocationError):
        locations.cafe(bad, bad.comp, menu=('x' * (locations.MENU_CHARS + 1),) * 3)
    assert bad.scene.to_bytes() == before


def test_partial_coverage_is_explicit_and_style_filtered(capsys, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', dict(registry._REGISTRY['prop']))

    @registry.register('prop', 'coverage-cutout-probe', style='cutout')
    def undeclared():
        raise AssertionError('coverage inspection must not draw')

    info = registry.contract_coverage(style='cutout', kind='prop')
    rows = registry.entries('prop', 'cutout')
    assert info['kinds']['prop']['registered'] == len(rows)
    explicit = sum(entry.contract is not None for entry in rows)
    assert info['kinds']['prop']['explicit_contracts'] == explicit
    assert info['kinds']['prop']['undeclared_parts'] == ['coverage-cutout-probe']
    assert cli.main(['catalog', '--kind', 'prop', '--style', 'cutout', '--contract-coverage']) == 0
    assert str(explicit) in capsys.readouterr().out
    with pytest.raises(registry.RegistryError):
        registry.contract_coverage(kind='unknown')


def test_return_metadata_requires_a_parameter_contract():
    with pytest.raises(ContractError):
        PartContract(returns={'x-unit': 'pixels'})


def test_cup_relative_coordinate_shapes_are_discoverable():
    params = registry.describe('prop', 'coffee-cup')['contract']['arguments']['properties']
    assert {'type': 'string'} in params['x']['anyOf']
    assert params['x']['x-unit'] == 'parent units'


@pytest.mark.parametrize('kind,name,field', [('prop', 'reaching-hand', 'grip'), ('graphic', 'episode-slate', 'w')])
def test_local_geometry_dimensions_are_distinct_from_parent_placement(kind, name, field):
    params = registry.describe(kind, name)['contract']['arguments']['properties']
    assert params[field]['x-unit'] == 'drawing units'
    assert params['x']['x-unit'] == 'parent units'


CORE = [
    e
    for e in registry.entries()
    if e.module in ('srstudio.props', 'srstudio.locations', 'srstudio.graphics') or e.name == 'reaching-hand'
]


@pytest.mark.parametrize('entry', CORE, ids=lambda e: e.name)
def test_declared_return_shapes_agree_with_actual_builders(entry):
    cv = canvas()
    cv.font_asset = 'caption-font'
    values = {
        'cv': cv,
        'parent': cv.comp,
        'x': 120,
        'y': 340,
        'w': 400,
        'h': 300,
        'height': 200,
        'x0': 0,
        'x1': 900,
        'top': 1200,
        'bottom': 1600,
        'ground': 900,
        'toss': 1,
        'readings': ((0, '$12', 'TAP'),),
        'name': None,
        'number': '01',
        'title': 'TITLE',
        'label': 'LABEL',
        'question': 'Question?',
        'show': (1, 3),
        'value': '42',
        'heading': 'HEADING',
        'index': 0,
        'who': 'Sam',
        'status': 'READY',
        'password': 'secret',
        'footnote': 'FOOTNOTE',
        'text': 'TEXT',
        'specs': ((0, 1, 'Caption', 'first'),),
        'rows': (('LABEL', '42', '#FFFFFF'),) if entry.name == 'scorecard' else (('LABEL', '42'),),
    }
    signature = inspect.signature(entry.builder)
    args = {k: values[k] for k, p in signature.parameters.items() if p.default is inspect.Parameter.empty}
    result = entry.builder(**args)
    schema = entry.describe()['contract']['returns']
    if isinstance(result, Group):
        assert schema['x-python-type'].endswith('.Group')
        assert schema['x-space'] == 'returned-group'
    elif isinstance(result, list):
        assert all(isinstance(layer, Layer) for layer in result)
        assert schema['type'] == 'array' and schema['items']['x-python-type'].endswith('.Layer')
    else:
        assert result is None and schema['type'] == 'null'


def test_caption_lifetimes_and_graphic_keys_have_distinct_clock_contracts():
    captions = registry.describe('graphic', 'captions')['contract']
    graphic = registry.describe('graphic', 'quiz-card')['contract']
    assert captions['arguments']['properties']['specs']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    assert graphic['arguments']['properties']['show']['prefixItems'][0]['x-timebase'] == 'canvas'


@pytest.mark.parametrize(
    'name,options,error,code',
    [
        ('office-wide', {'instanced': True, 'depth': 12}, locations.LocationError, 'location.instanced_depth'),
        ('office-wide', {'instanced': True, 'cactus': lambda g: None}, SignatureError, 'location.instanced_cactus'),
        ('office-desk', {'instanced': True, 'cactus': lambda g: None}, SignatureError, 'location.instanced_cactus'),
    ],
)
def test_unsupported_instance_combinations_are_repairable_and_atomic(name, options, error, code):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(error) as caught:
        registry.get('location', name)(cv, cv.comp, **options)
    detail = caught.value.to_dict()
    assert detail['code'] == code and detail['path']
    assert detail['expected'] is not None and detail['remedy']
    assert cv.scene.to_bytes() == before and cv._serial == 0


def test_elevator_hallway_slot_receives_the_main_group_and_stays_outside_blur():
    cv = canvas()
    seen = []
    room = locations.elevator(cv, cv.comp, depth=12, hallway=seen.append)
    assert seen == [room] and room.effects is None
    info = registry.describe('location', 'elevator')['contract']
    assert 'main location group' in info['arguments']['properties']['hallway']['description']


def test_reception_desk_slot_receives_the_separate_props_group():
    cv = canvas()
    seen = []
    locations.reception(cv, cv.comp, on_desk=seen.append)
    assert len(seen) == 1 and seen[0].id == 'location-reception-desk'
    info = registry.describe('location', 'reception')['contract']
    assert 'desk-props group' in info['arguments']['properties']['on_desk']['description']


@pytest.mark.parametrize('same_signature', [True, False])
def test_direct_builder_swap_cannot_keep_the_previous_drawing_contract(monkeypatch, same_signature):
    entry = registry.get('prop', 'coffee-cup')
    declared = registry.contract_coverage(kind='prop')['kinds']['prop']['explicit_contracts']

    def replacement(cv, parent, x, y, scale=1, rotation=0, *, shadow=True):
        raise AssertionError('must not execute while inspecting')

    monkeypatch.setattr(entry, 'builder', replacement if same_signature else lambda: None)
    info = entry.describe()['contract']
    assert 'x-anchors' not in info['returns']
    assert info['capabilities'].get('spatial_attachment') is None
    assert info['declaration_status'] == 'builder-changed'
    coverage = registry.contract_coverage(kind='prop')['kinds']['prop']
    assert 'coffee-cup' in coverage['undeclared_parts']
    assert 'coffee-cup' in coverage['stale_contract_parts']
    assert coverage['explicit_contracts'] == declared - 1
