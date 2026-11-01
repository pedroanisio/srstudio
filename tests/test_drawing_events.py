"""Usage follows explicit drawing events across emitter and ID allocator refactors."""

import sys

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, specimens, toon_head, usage


def test_rig_usage_survives_a_wrapper_without_a_named_rig_parameter(monkeypatch):
    original = toon_head._draw_figure

    def wrapped(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(toon_head, '_draw_figure', wrapped)
    figures = []
    with usage.trace(figures) as used:
        specimens.rig_digest('toon-fox', 2)
    assert 'toon-fox@2' in used
    assert [figure.part for figure in figures] == ['toon-fox@2']
    assert figures[0].ids


def test_id_events_survive_replacing_canvas_uid_with_a_wrapper(monkeypatch):
    original = Canvas.uid

    def wrapped(self, *args, **kwargs):
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Canvas, 'uid', wrapped)
    figures = []
    with usage.trace(figures):
        specimens.rig_digest('toon-fox', 2)
    assert len(figures) == 1 and figures[0].ids
    assert len(figures[0].ids) == len(set(figures[0].ids))


def test_explicit_part_drawing_records_ids_and_restores_observers_on_failure():
    from srstudio import drawing_events

    cv = Canvas(Scene(version='auto'), font_asset=None)
    events = []
    previous = sys.getprofile()
    with drawing_events.observe(events.append):
        figures = []
        with usage.trace(figures) as used:
            with drawing_events.drawing('toon-fox@2'):
                identifier = cv.uid('figure')
                cv.group(cv.comp, identifier)
        assert used == {'toon-fox@2'}
        assert figures[0].ids == (identifier,)
        with pytest.raises(ValueError), drawing_events.drawing('toon-fox@2'):
            raise ValueError('failed drawing')
    assert sys.getprofile() is previous
    before = list(events)
    cv.uid('outside')
    assert events == before
    assert events[-1].kind == 'end' and not events[-1].successful


def test_nested_drawings_record_each_part_and_only_outermost_figure():
    from srstudio import drawing_events

    cv = Canvas(Scene(version='auto'), font_asset=None)
    figures = []
    with usage.trace(figures) as used:
        with drawing_events.drawing('toon-fox@2'):
            first = cv.uid('outer')
            with drawing_events.drawing('toon-goat'):
                second = cv.uid('inner')
    assert used == {'toon-fox@2', 'toon-goat'}
    assert len(figures) == 1 and figures[0].ids == (first, second)


def test_unknown_explicit_part_fails_before_drawing_and_restores_trace():
    from srstudio import drawing_events

    previous = sys.getprofile()
    with pytest.raises(usage.UsageError, match='registered'), usage.trace():
        with drawing_events.drawing('missing-part'):
            pytest.fail('unknown part must fail at entry')
    assert sys.getprofile() is previous
    with usage.trace() as used:
        with drawing_events.drawing('toon-goat'):
            pass
    assert used == {'toon-goat'}


def test_observers_do_not_leak_into_an_independent_context():
    from contextvars import Context

    from srstudio import drawing_events

    events = []
    with drawing_events.observe(events.append):
        Context().run(drawing_events.allocated, 'other-context')
        drawing_events.allocated('this-context')
    assert [event.identifier for event in events] == ['this-context']
