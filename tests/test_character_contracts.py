"""Registered characters declare their actual drawing interface, clocks and supported performance data."""

import json
from dataclasses import dataclass

import pytest

from srstudio import registry
from srstudio.contracts import ParameterContract, PartContract, describe_callable


def test_builtin_character_contracts_have_explicit_capabilities_without_drawing():
    for entry in registry.entries('character'):
        if not entry.builder.__module__.startswith('srstudio.'):
            continue
        assert entry.contract is not None, entry.name
        contract = entry.describe()['contract']
        assert all(type(contract['capabilities'][key]) is bool for key in ('limbs', 'head_motion', 'expressions')), (
            entry.name
        )
        assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_nullable_tracks_and_tuples_can_describe_element_clocks():
    def builder(track: tuple[tuple[float, str], ...] | None = None, walk: tuple[float, float, float] | None = None):
        pytest.fail('inspection invoked a builder')

    second = ParameterContract(unit='seconds', timebase='canvas')
    spec = PartContract(
        parameters=(
            ('track', ParameterContract(items=ParameterContract(prefix_items=(second, ParameterContract())))),
            ('walk', ParameterContract(prefix_items=(second, second, ParameterContract(unit='parent units')))),
        )
    )
    props = describe_callable(builder, spec)['arguments']['properties']
    assert props['track']['anyOf'][0]['items']['prefixItems'][0]['x-timebase'] == 'canvas'
    assert props['walk']['anyOf'][0]['prefixItems'][2]['x-unit'] == 'parent units'
    assert props['track']['anyOf'][1] == props['walk']['anyOf'][1] == {'type': 'null'}


def test_a_shared_clock_can_decorate_every_record_in_a_pose_union():
    @dataclass
    class A:
        start: float

    @dataclass
    class B:
        start: float
        x: float

    def builder(pose: A | B):
        pytest.fail('inspection invoked a builder')

    metadata = PartContract(
        parameters=(
            ('pose', ParameterContract(fields=(('start', ParameterContract(unit='seconds', timebase='canvas')),))),
        )
    )
    branches = describe_callable(builder, metadata)['arguments']['properties']['pose']['anyOf']
    assert all(b['properties']['start']['x-timebase'] == 'canvas' for b in branches)


@pytest.mark.parametrize('name', ['toon-cat', 'toon-dog', 'toon-sloth', 'toon-fox@2', 'toon-dog@2', 'collage-brent'])
def test_pose_families_distinguish_relative_pose_times_from_project_exit(name):
    contract = registry.describe('character', name)['contract']
    props = contract['arguments']['properties']
    assert props['poses']['items']['properties']['start']['x-timebase'] == 'relative:enter'
    assert props['duration']['x-role'] == 'end'
    assert props['duration']['x-timebase'] == 'project'
    assert props['enter']['x-role'] == 'start'
    assert contract['vocabularies']['eyes']
    assert contract['vocabularies']['arms']
    assert contract['operations']['pose']['invocation'] == 'construct'


def test_traced_and_brush_toon_vocabularies_do_not_overpromise():
    cat = registry.describe('character', 'toon-cat')['contract']
    dog = registry.describe('character', 'toon-dog')['contract']
    assert 'hearts' not in cat['vocabularies']['eyes']
    assert 'hearts' in dog['vocabularies']['eyes']
    assert cat['capabilities']['limbs'] is False
    assert dog['capabilities']['limbs'] is True


def test_soft_exposes_existing_pose_tweening_foot_pinning_and_local_units():
    from srstudio import blob

    contract = registry.describe('character', 'pip')['contract']
    assert contract['capabilities']['pose_tweening'] is True
    assert contract['capabilities']['foot_pinning'] is True
    assert contract['vocabularies']['poses'] == list(blob.POSES)
    cue = contract['arguments']['properties']['cues']['items']['properties']
    assert cue['time']['x-timebase'] == 'canvas'
    assert cue['ease']['x-role'] == 'duration'
    assert cue['turn']['x-unit'] == 'degrees'
    assert cue['x']['x-unit'] == 'rig units'
    assert cue['pin']['enum'] == [None, *blob.FEET]


@pytest.mark.parametrize('name', ['gloss-nadia', 'gloss-sunny', 'saga-gloom', 'saga-juno'])
def test_lit_figures_declare_canvas_clock_and_placement(name):
    contract = registry.describe('character', name)['contract']
    props = contract['arguments']['properties']
    assert props['end']['x-timebase'] == 'canvas'
    assert props['at']['x-unit'] == 'parent units'
    assert props['talk']['items']['prefixItems'][0]['x-timebase'] == 'canvas'
    assert contract['vocabularies']['visemes']
    assert contract['capabilities']['limbs'] is (name == 'gloss-nadia')


def test_rafa_body_does_not_claim_the_separate_face_or_plate_animation_interface():
    from srstudio import rafa

    contract = registry.describe('character', 'rafa')['contract']
    assert contract['capabilities']['expressions'] is False
    assert contract['capabilities']['head_motion'] is False
    assert contract['arguments']['properties']['m']['x-unit'] == 'Rafa model units'
    face = contract['operations']['face']
    assert face['arguments']['properties']['mood']['enum'] == list(rafa.MOODS)
    assert face['arguments']['properties']['turn']['enum'] == list(rafa.TURNS)
    assert face['arguments']['properties']['turn']['x-unit'] == 'degrees'


@pytest.mark.parametrize('name', ['news-vera', 'news-gus@5', 'host-lint'])
def test_news_and_host_pose_helpers_expose_head_degrees_and_project_mouth_clock(name):
    contract = registry.describe('character', name)['contract']
    props = contract['arguments']['properties']
    assert props['start']['x-timebase'] == props['end']['x-timebase'] == 'project'
    assert props['mouths']['items']['prefixItems'][0]['x-timebase'] == 'project'
    assert props['pose']['anyOf'][0]['properties']['head']['x-unit'] == 'degrees'
    assert contract['operations']['pose']['arguments']['properties']['head']['maximum'] == 15


def test_ink_takes_keep_project_metadata_separate_from_local_animation():
    contract = registry.describe('character', 'talking-router')['contract']
    props = contract['arguments']['properties']
    assert props['take']['properties']['start']['x-timebase'] == 'project'
    assert props['take']['properties']['duration']['x-role'] == 'duration'
    assert props['drop_at']['x-timebase'] == 'relative:take'
    assert props['power']['enum'] == ['on', 'off', 'down', 'up']


def test_stick_pose_keys_have_a_clock_and_dynamic_pose_names_are_not_a_closed_enum():
    contract = registry.describe('character', 'stick-rig')['contract']
    props = contract['arguments']['properties']
    assert props['keys']['items']['properties']['start']['x-timebase'] == 'canvas'
    assert 'enum' not in props['keys']['items']['properties']['pose']
    assert contract['vocabularies']['default_poses']
    assert contract['capabilities']['limbs'] is True


@pytest.mark.parametrize('name', ['toon-cat', 'toon-dog', 'toon-sloth', 'toon-fox@2', 'toon-dog@2', 'collage-brent'])
def test_declared_pose_vocabulary_drives_real_drawings_and_refuses_an_unknown_expression(name):
    from dataclasses import replace

    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.errors import SrstudioError

    entry = registry.get('character', name)
    vocabulary = entry.describe()['contract']['vocabularies']
    pose_factory = entry.contract.operations[0].builder
    pose = pose_factory(0, vocabulary['eyes'][0], vocabulary['mouths'][0], vocabulary['arms'][0])
    cv = Canvas(Scene(version='auto'), font_asset=None)
    groups = entry.builder(cv, cv.comp, [pose], duration=4, enter=3)
    assert groups
    assert groups[0].attributes()['start'] == '3'
    assert groups[0].attributes()['end'] == '4'
    with pytest.raises((SrstudioError, KeyError)):
        entry.builder(cv, cv.comp, [replace(pose, eyes='not-a-real-eye')], duration=4, enter=3)


def test_soft_contract_pin_constraint_matches_sampling():
    from srstudio import blob

    blob.drawings([blob.Cue(0, 'stand'), blob.Cue(1, 'clasp', ease=0.2, pin=blob.FEET[0])], end=2)
    with pytest.raises(blob.BlobError, match='planted foot'):
        blob.drawings([blob.Cue(0, 'stand'), blob.Cue(1, 'clasp', pin=blob.FEET[0], x=1)], end=2)


@pytest.mark.parametrize('name', ['news-vera', 'news-gus@5', 'host-lint'])
def test_anchor_pose_metadata_bounds_are_enforced_by_the_real_constructor(name):
    from srstudio.errors import SrstudioError

    operation = registry.get('character', name).contract.operations[0]
    props = registry.describe('character', name)['contract']['operations']['pose']['arguments']['properties']
    assert operation.builder(head=props['head']['maximum']).head == 15
    with pytest.raises(SrstudioError):
        operation.builder(head=props['head']['maximum'] + 1)
    with pytest.raises(SrstudioError):
        operation.builder(mouth='invented-expression')


def test_lit_and_ink_contracts_drive_real_validation_and_drawing():
    from sr_core.scene import Scene

    from srstudio import Canvas, gloss, ink, saga
    from srstudio.timeline import Take

    cv = Canvas(Scene(version='auto'), font_asset=None)
    faces = registry.describe('character', 'gloss-nadia')['contract']['vocabularies']['faces']
    assert gloss.nadia(cv, cv.comp, at=(500, 1500), end=1, face=[(0, faces[0])]).group is not None
    with pytest.raises(gloss.GlossError, match='face'):
        gloss.nadia(cv, cv.comp, at=(500, 1500), end=1, face=[(0, 'unknown')])
    visemes = registry.describe('character', 'saga-juno')['contract']['vocabularies']['visemes']
    saga.check_talk([(0, visemes[0])])
    with pytest.raises(saga.SagaError, match='viseme'):
        saga.check_talk([(0, 'unknown')])
    take = Take('01', 'human', 'wide', 'Hello.', 3, 1)
    ink.router(cv, cv.comp, take, 0, 0, power='down', drop_at=0.5)
    with pytest.raises(ink.InkError, match='power'):
        ink.router(cv, cv.comp, take, 0, 0, power='invented')
    with pytest.raises(ink.InkError, match='drop_at'):
        ink.router(cv, cv.comp, take, 0, 0, drop_at=3.5)


def test_static_rafa_body_contract_exposes_validated_face_helper_without_claiming_animation():
    from srstudio import rafa

    operation = registry.get('character', 'rafa').contract.operations[0]
    props = registry.describe('character', 'rafa')['contract']['operations']['face']['arguments']['properties']
    assert operation.builder(turn=props['turn']['enum'][-1]).turn == rafa.TURNS[-1]
    with pytest.raises(rafa.RafaError):
        operation.builder(turn=props['turn']['enum'][-1] + 0.125)


def test_stick_custom_pose_mapping_and_traced_cel_references_are_validated():
    from sr_core.scene import Scene

    from srstudio import Canvas, cel, stick

    cv = Canvas(Scene(version='auto'), font_asset=None)
    poses = {'my-pose': next(iter(stick.SEATED.values()))}
    stick.rig(cv, cv.comp, [stick.RigKey(0, 'my-pose')], end=1, poses=poses)
    with pytest.raises(stick.StickDataError, match='unknown pose'):
        stick.rig(cv, cv.comp, [stick.RigKey(0, 'absent')], end=1, poses=poses)
    drawing = {'a': [cel.Fill('#000000', 'M0 0 L10 0 L10 10 Z')]}
    assert cel.traced(cv, cv.comp, [cel.Run('a', 3, 4)], drawing)
    with pytest.raises(cel.CelDataError, match='no drawing'):
        cel.traced(cv, cv.comp, [cel.Run('absent', 3, 4)], drawing)


def test_union_metadata_rejects_incompatible_alternatives_instead_of_hiding_them():
    from srstudio.contracts import ContractError

    def builder(value: tuple[float, ...] | str):
        pass

    with pytest.raises(ContractError, match='compatible non-null'):
        describe_callable(
            builder, PartContract(parameters=(('value', ParameterContract(items=ParameterContract(unit='seconds'))),))
        )
