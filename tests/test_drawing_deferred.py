"""Registered deferred drawings retain attribution only while their bodies execute."""

import asyncio
import inspect
from contextvars import copy_context

import pytest

from srstudio import drawing_events, registry, usage


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry, '_REGISTRY', {kind: dict(rows) for kind, rows in registry._REGISTRY.items()})


def ids(figures, name):
    return tuple(identifier for figure in figures if figure.part == name for identifier in figure.ids)


def test_generator_creation_does_not_claim_usage_or_capture_caller_ids():
    @registry.register('character', 'deferred', style='')
    def draw():
        drawing_events.allocated('first')
        received = yield 1
        drawing_events.allocated(received)
        return 3

    assert inspect.isgeneratorfunction(draw)
    figures = []
    with usage.trace(figures) as used:
        iterator = draw()
        assert used == set()
        assert next(iterator) == 1
        drawing_events.allocated('caller')
        with pytest.raises(StopIteration) as stopped:
            iterator.send('second')
        assert stopped.value.value == 3
    assert used == {'deferred'}
    assert ids(figures, 'deferred') == ('first', 'second')


def test_generator_throw_close_and_failure_leave_no_scope_behind():
    @registry.register('character', 'deferred', style='')
    def draw():
        try:
            drawing_events.allocated('first')
            try:
                yield 1
            except ValueError:
                drawing_events.allocated('recovered')
                yield 2
            raise RuntimeError('draw failed')
        finally:
            drawing_events.allocated('finally')

    figures = []
    with usage.trace(figures):
        a = draw()
        assert next(a) == 1
        assert a.throw(ValueError('repair')) == 2
        a.close()
        b = draw()
        next(b)
        with pytest.raises(RuntimeError, match='draw failed'):
            next(b)
        drawing_events.allocated('outside')
    assert ids(figures, 'deferred') == ('first', 'recovered', 'finally', 'first', 'finally')


def test_interleaved_coroutines_keep_independent_figure_ownership():
    @registry.register('character', 'deferred-a', style='')
    async def first(entered, release):
        drawing_events.allocated('a-start')
        entered.set()
        await release.wait()
        drawing_events.allocated('a-end')

    @registry.register('character', 'deferred-b', style='')
    async def second(entered, release):
        await entered.wait()
        drawing_events.allocated('b-start')
        release.set()
        await asyncio.sleep(0)
        drawing_events.allocated('b-end')

    assert inspect.iscoroutinefunction(first)
    figures = []

    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        with usage.trace(figures) as used:
            await asyncio.gather(first(entered, release), second(entered, release))
        return used

    assert asyncio.run(run()) == {'deferred-a', 'deferred-b'}
    assert ids(figures, 'deferred-a') == ('a-start', 'a-end')
    assert ids(figures, 'deferred-b') == ('b-start', 'b-end')


def test_coroutine_cancellation_records_cleanup_without_leaking():
    @registry.register('character', 'deferred', style='')
    async def draw(entered):
        try:
            drawing_events.allocated('started')
            entered.set()
            await asyncio.Event().wait()
        finally:
            drawing_events.allocated('cancelled')

    figures = []

    async def run():
        entered = asyncio.Event()
        with usage.trace(figures):
            task = asyncio.create_task(draw(entered))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            drawing_events.allocated('caller')

    asyncio.run(run())
    assert ids(figures, 'deferred') == ('started', 'cancelled')


def test_async_generator_preserves_send_throw_close_and_execution_scopes():
    @registry.register('character', 'deferred', style='')
    async def draw():
        try:
            drawing_events.allocated('first')
            received = yield 1
            drawing_events.allocated(received)
            try:
                yield 2
            except ValueError:
                drawing_events.allocated('recovered')
                yield 3
        finally:
            drawing_events.allocated('finally')

    assert inspect.isasyncgenfunction(draw)
    figures = []

    async def run():
        with usage.trace(figures) as used:
            iterator = draw()
            assert not used
            assert await iterator.__anext__() == 1
            drawing_events.allocated('caller')
            assert await iterator.asend('second') == 2
            assert await iterator.athrow(ValueError('repair')) == 3
            await iterator.aclose()

    asyncio.run(run())
    assert ids(figures, 'deferred') == ('first', 'second', 'recovered', 'finally')


def test_async_generator_normal_completion_and_failure():
    @registry.register('character', 'deferred', style='')
    async def draw(fail=False):
        drawing_events.allocated('first')
        yield 1
        drawing_events.allocated('second')
        if fail:
            raise RuntimeError('draw failed')

    figures = []

    async def run():
        with usage.trace(figures):
            assert [item async for item in draw()] == [1]
            with pytest.raises(RuntimeError, match='draw failed'):
                _ = [item async for item in draw(True)]
            drawing_events.allocated('outside')

    asyncio.run(run())
    assert ids(figures, 'deferred') == ('first', 'second', 'first', 'second')


def test_copied_context_cannot_write_to_an_observer_after_it_closes():
    events = []
    with drawing_events.observe(events.append):
        context = copy_context()
        context.run(drawing_events.allocated, 'inside')
    context.run(drawing_events.allocated, 'outside')
    assert [event.identifier for event in events] == ['inside']


@pytest.mark.parametrize('replacement', [False, True])
@pytest.mark.parametrize('kind', ['generator', 'coroutine', 'async-generator'])
@pytest.mark.parametrize('create_before_trace', [False, True])
def test_catalog_entry_defers_attribution_until_execution(kind, replacement, create_before_trace):
    def generator():
        drawing_events.allocated('body')
        yield 1

    async def coroutine():
        drawing_events.allocated('body')
        return 1

    async def async_generator():
        drawing_events.allocated('body')
        yield 1

    original = {'generator': generator, 'coroutine': coroutine, 'async-generator': async_generator}[kind]
    registry.register('character', 'deferred', style='')(original)
    entry = registry.get('character', 'deferred')
    if replacement:
        entry.builder = original
    figures = []

    async def collect(iterator):
        return [item async for item in iterator]

    deferred = entry() if create_before_trace else None
    with usage.trace(figures) as used:
        if deferred is None:
            deferred = entry()
        try:
            assert not used
            if kind == 'generator':
                assert list(deferred) == [1]
            elif kind == 'coroutine':
                assert asyncio.run(deferred) == 1
            else:
                assert asyncio.run(collect(deferred)) == [1]
        finally:
            if kind == 'coroutine':
                deferred.close()
    assert used == {'deferred'}
    assert ids(figures, 'deferred') == ('body',)


def test_deferred_class_methods_keep_class_identity_and_descriptors():
    class Example:
        @staticmethod
        def generate():
            drawing_events.allocated('static')
            yield 1

        @classmethod
        async def draw(cls):
            drawing_events.allocated('class')
            return cls

    assert registry.register('character', 'deferred', style='')(Example) is Example
    assert inspect.isgeneratorfunction(Example.generate)
    assert inspect.iscoroutinefunction(Example.draw)
    figures = []
    with usage.trace(figures):
        assert list(Example.generate()) == [1]
        assert asyncio.run(Example.draw()) is Example
    assert ids(figures, 'deferred') == ('static', 'class')


@pytest.mark.parametrize('kind', ['ordinary', 'generator', 'coroutine', 'async-generator'])
def test_registered_function_defaults_remain_inspectable(kind):
    def ordinary(value=1, *, option='plain'):
        return value, option

    def generator(value=1, *, option='plain'):
        yield value, option

    async def coroutine(value=1, *, option='plain'):
        return value, option

    async def async_generator(value=1, *, option='plain'):
        yield value, option

    original = {
        'ordinary': ordinary,
        'generator': generator,
        'coroutine': coroutine,
        'async-generator': async_generator,
    }[kind]
    wrapped = registry.register('prop', 'defaults', style='')(original)
    assert inspect.signature(wrapped) == inspect.signature(original)
    assert wrapped.__defaults__ == original.__defaults__
    assert wrapped.__kwdefaults__ == original.__kwdefaults__


def test_reregistering_the_current_builder_does_not_wrap_it_again():
    class Drawn:
        @staticmethod
        def draw():
            return 'drawn'

    def draw():
        return 'drawn'

    for kind, name, source in (('prop', 'rewrapped-function', draw), ('character', 'rewrapped-class', Drawn)):
        registered = registry.register(kind, name)(source)
        method = vars(Drawn)['draw'].__func__
        assert registry.register(kind, name, replace=True)(registered) is registered
        assert registry.get(kind, name).builder is registered
        assert vars(Drawn)['draw'].__func__ is method


def test_a_function_registered_under_two_names_keeps_one_scope_for_each():
    def draw():
        return 'drawn'

    first = registry.register('prop', 'first-name')(draw)
    second = registry.register('prop', 'second-name')(draw)
    assert first is not second
