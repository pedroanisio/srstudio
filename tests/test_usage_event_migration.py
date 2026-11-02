"""Explicit drawing events preserve attribution without a profiler or source files."""

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    Canvas,
    cast,
    collage,
    gloss,
    head_motion,
    host_kit,
    news_inked,
    news_kit,
    registry,
    toon,
    toon_head,
    usage,
)
from srstudio.rig import Performance
from srstudio.toon_critters import GOAT_RIG

FIXTURE = Path(__file__).with_name('data') / 'usage-event-compatibility.json'
CASES = ('actor', 'closure', 'gloss', 'news-vera', 'news-gus', 'inked-vera', 'inked-gus', 'host', 'rig')


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    return Canvas(scene, font_asset=None)


def draw(case, cv):
    if case == 'actor':
        cast.Manager(cv).build(cv.comp, 0, 0, end=2)
    elif case == 'closure':
        registry.get('character', 'collage-gary')(cv, cv.comp, [collage.Pose(0, 'wide', 'flat', 'down')], 2)
    elif case == 'gloss':
        gloss.nadia(cv, cv.comp, at=(540, 1000), end=2)
    elif case.startswith('news-'):
        news_kit.perform(cv, cv.comp, case.removeprefix('news-'), 540, ((0, news_kit.Pose()),), 0, 2)
    elif case.startswith('inked-'):
        news_inked.perform(cv, cv.comp, case.removeprefix('inked-'), 540, ((0, news_kit.Pose()),), 0, 2, number=4)
    elif case == 'host':
        host_kit.perform(cv, cv.comp, cv.comp, ((0, host_kit.Pose()),), 0, 2)
    else:
        toon_head.figure(cv, cv.comp, GOAT_RIG, [toon.Pose(0, 'wide', 'flat', 'desk')], 2, head_motion.HeadPlan.still())


def capture_case(case):
    cv, figures = canvas(), []
    with usage.trace(figures) as used:
        draw(case, cv)
    return {
        'used': sorted(used),
        'figures': [{'part': f.part, 'ids': f.ids} for f in figures],
        'xml_sha256': hashlib.sha256(cv.scene.to_bytes()).hexdigest(),
    }


def capture():
    return {
        'schema_version': '1.0.0',
        'source_commit': 'ea60f48d',
        'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
        'cases': {case: capture_case(case) for case in CASES},
    }


@pytest.mark.parametrize('case', CASES)
def test_registered_and_delegated_drawings_retain_usage_ids_and_xml(case):
    expected = json.loads(FIXTURE.read_text())['cases'][case]
    assert json.loads(json.dumps(capture_case(case))) == expected


def test_trace_does_not_install_a_profiler_or_read_python_source(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Drawing attribution must not depend on profiling or source inspection')

    monkeypatch.setattr(sys, 'setprofile', forbidden)
    monkeypatch.setattr(inspect, 'getsource', forbidden)
    cv = canvas()
    with usage.trace() as used:
        news_kit.perform(cv, cv.comp, 'vera', 540, ((0, news_kit.Pose()),), 0, 2)
    assert 'news-vera' in used


def test_active_profiler_keeps_receiving_calls_during_trace():
    calls = []

    def sentinel():
        return 42

    def profile(frame, event, arg):
        if event == 'call' and frame.f_code is sentinel.__code__:
            calls.append(event)

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        with usage.trace():
            sentinel()
            assert sys.getprofile() is profile
        assert calls == ['call']
    finally:
        sys.setprofile(previous)


def test_nested_traces_both_observe_inner_calls_without_leaking_outside():
    cv = canvas()
    with usage.trace() as outer:
        with usage.trace() as inner:
            cast.Manager(cv).draw_eyes(cv.comp, Performance())
    assert 'manager' in outer and inner == outer
    snapshot = set(outer)
    cast.Candidate(cv).draw_eyes(cv.comp, Performance())
    assert outer == snapshot


def test_failing_registered_drawer_closes_scope_before_the_next_figure(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', {})

    @registry.register('character', 'failed-figure')
    def failed(cv):
        cv.group(cv.comp, cv.uid('failed'))
        raise ValueError('drawing failed')

    @registry.register('character', 'next-figure')
    def next_figure(cv):
        cv.group(cv.comp, cv.uid('next'))

    cv, figures = canvas(), []
    with usage.trace(figures) as used:
        with pytest.raises(ValueError, match='drawing failed'):
            failed(cv)
        next_figure(cv)
    assert used == {'failed-figure', 'next-figure'}
    assert [f.part for f in figures] == ['failed-figure', 'next-figure']
    assert figures[0].ids != figures[1].ids


def test_replaced_builder_does_not_claim_the_new_registration(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})

    @registry.register('prop', 'replaceable')
    def original():
        return 'old'

    @registry.register('prop', 'replaceable', replace=True)
    def replacement():
        return 'new'

    with usage.trace() as used:
        original()
    assert not used
    with usage.trace() as used:
        replacement()
    assert used == {'replaceable'}


def test_explicit_performer_is_bound_to_its_original_builder_after_replacement(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    registry.register('character', 'host-lint', replace=True)(lambda: None)
    cv = canvas()
    with usage.trace() as used:
        host_kit.perform(cv, cv.comp, cv.comp, ((0, host_kit.Pose()),), 0, 2)
    assert 'host-lint' not in used


def test_class_registration_preserves_identity_descriptors_and_annotations(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', {})

    class Example:
        @staticmethod
        def static(value: int = 2) -> int:
            return value

        @classmethod
        def kind(cls):
            return cls

    original_signature = inspect.signature(Example.static)
    registered = registry.register('character', 'descriptor-example')(Example)
    assert registered is Example
    assert inspect.signature(registered.static) == original_signature
    with usage.trace() as used:
        assert registered.static() == 2
        assert registered.kind() is Example
    assert used == {'descriptor-example'}


def test_entry_call_attributes_an_explicitly_swapped_callable(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'prop', {})
    registry.register('prop', 'swapped')(lambda: None)
    entry = registry.get('prop', 'swapped')
    entry.builder = lambda: 'changed'
    with usage.trace() as used:
        assert entry() == 'changed'
    assert used == {'swapped'}


@pytest.mark.parametrize('who', ['vera', 'gus'])
@pytest.mark.parametrize('number', [2, 3, 4, 5])
def test_direct_inked_performer_attributes_the_requested_version(who, number):
    cv, figures = canvas(), []
    with usage.trace(figures) as used:
        news_inked.perform(cv, cv.comp, who, 540, ((0, news_kit.Pose()),), 0, 2, number=number)
    name = f'news-{who}@{number}'
    assert used == {name}
    assert len(figures) == 1 and figures[0].part == name and figures[0].ids
    assert cv.scene.check() == []
