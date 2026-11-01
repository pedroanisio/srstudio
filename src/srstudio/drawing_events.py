"""Explicit drawing instrumentation, scoped to the current execution context.

Emit a drawing scope around a rig or registered part name and allocate IDs through Canvas.uid. Observers receive
begin/ID/end events without inspecting a renderer function's name, signature, stack frame or private code object.
Events are ephemeral; observers choose how to persist them. No observer means no event objects are allocated.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import WRAPPER_ASSIGNMENTS, wraps
from typing import Any, Literal, TypeVar, cast


@dataclass(frozen=True)
class DrawEvent:
    kind: Literal['begin', 'id', 'end']
    subject: object = None
    token: object = None
    identifier: str | None = None
    successful: bool = False


Observer = Callable[[DrawEvent], None]
_observers: ContextVar[tuple[Observer, ...]] = ContextVar('srstudio_drawing_observers', default=())

_Builder = TypeVar('_Builder', bound=Callable[..., Any])
_FUNCTION_ATTRIBUTES = (*WRAPPER_ASSIGNMENTS, '__defaults__', '__kwdefaults__')


class _DrawingGenerator(Generator[Any, Any, Any]):
    """Delegate the generator protocol with a scope per resume, never across yield."""

    def __init__(self, iterator: Generator[Any, Any, Any], subject: object) -> None:
        self.iterator = iterator
        self.subject = subject

    def send(self, value: Any) -> Any:
        with drawing(self.subject):
            return self.iterator.send(value)

    def throw(self, *args) -> Any:
        with drawing(self.subject):
            return self.iterator.throw(*args)

    def close(self) -> None:
        with drawing(self.subject):
            self.iterator.close()


def _instrument_function(function, subject=None):
    """One explicit call boundary, preserving signatures and the original module's annotations."""

    if inspect.isgeneratorfunction(function):

        @wraps(function, assigned=_FUNCTION_ATTRIBUTES)
        def generator(*args, **kwargs):
            return (yield from _DrawingGenerator(function(*args, **kwargs), generator if subject is None else subject))

        return generator

    if inspect.iscoroutinefunction(function):

        @wraps(function, assigned=_FUNCTION_ATTRIBUTES)
        async def coroutine(*args, **kwargs):
            with drawing(coroutine if subject is None else subject):
                return await function(*args, **kwargs)

        return coroutine

    if inspect.isasyncgenfunction(function):

        @wraps(function, assigned=_FUNCTION_ATTRIBUTES)
        async def async_generator(*args, **kwargs):
            iterator = function(*args, **kwargs)
            owner = async_generator if subject is None else subject
            operation, arguments = iterator.__anext__, ()
            while True:
                try:
                    with drawing(owner):
                        item = await operation(*arguments)
                except StopAsyncIteration:
                    return
                try:
                    value = yield item
                except GeneratorExit:
                    with drawing(owner):
                        await iterator.aclose()
                    raise
                except BaseException as error:
                    operation, arguments = iterator.athrow, (error,)
                else:
                    operation, arguments = iterator.asend, (value,)

        return async_generator

    @wraps(function, assigned=_FUNCTION_ATTRIBUTES)
    def wrapped(*args, **kwargs):
        if not _observers.get():
            return function(*args, **kwargs)
        with drawing(wrapped if subject is None else subject):
            return function(*args, **kwargs)

    return wrapped


def instrument(builder: _Builder) -> _Builder:
    """Instrument a registered builder without replacing a class's identity.

    Class-owned methods retain their descriptors. Inherited methods are left with
    their defining class, matching which drawing was actually called. Function
    scopes identify their callable, so a replaced registration cannot claim old calls.
    Deferred functions retain their function kind. Generators scope each resume;
    coroutines scope execution in their task's context, including cancellation.
    """
    if inspect.isclass(builder):
        for name, value in tuple(vars(builder).items()):
            function = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
            if inspect.isfunction(function):
                wrapped = _instrument_function(function, builder)
                if isinstance(value, staticmethod):
                    wrapped = staticmethod(wrapped)
                elif isinstance(value, classmethod):
                    wrapped = classmethod(wrapped)
                setattr(builder, name, wrapped)
        return builder
    return cast(_Builder, _instrument_function(builder))


def call(builder: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Invoke an entry's current callable, attributing deferred work when it executes.

    Classes already attribute their own methods. Entry replacement can install a
    raw function, so this boundary explicitly binds events to that callable too.
    """
    if inspect.isclass(builder):
        return builder(*args, **kwargs)
    return _instrument_function(builder, builder)(*args, **kwargs)


@contextmanager
def observe(observer: Observer) -> Iterator[None]:
    """Receive events in this context; nested observation and exceptional exits restore previous observers."""
    active = True

    def scoped(event: DrawEvent) -> None:
        if active:
            observer(event)

    token = _observers.set((*_observers.get(), scoped))
    try:
        yield
    finally:
        active = False
        _observers.reset(token)


def _emit(event: DrawEvent) -> None:
    for observer in _observers.get():
        observer(event)


@contextmanager
def drawing(subject: object) -> Iterator[None]:
    """Bracket a rig object or registered part name. The end event identifies whether drawing completed."""
    if not _observers.get():
        yield
        return
    token = object()
    successful = False
    try:
        _emit(DrawEvent('begin', subject, token))
        yield
        successful = True
    finally:
        _emit(DrawEvent('end', subject, token, successful=successful))


def allocated(identifier: str) -> str:
    """Record an allocated drawing ID without changing it; Canvas uses this for built-in and custom namers."""
    if _observers.get():
        _emit(DrawEvent('id', identifier=identifier))
    return identifier
