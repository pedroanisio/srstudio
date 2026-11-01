"""Explicit drawing instrumentation, scoped to the current execution context.

Emit a drawing scope around a rig or registered part name and allocate IDs through Canvas.uid. Observers receive
begin/ID/end events without inspecting a renderer function's name, signature, stack frame or private code object.
Events are ephemeral; observers choose how to persist them. No observer means no event objects are allocated.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class DrawEvent:
    kind: Literal['begin', 'id', 'end']
    subject: object = None
    token: object = None
    identifier: str | None = None
    successful: bool = False


Observer = Callable[[DrawEvent], None]
_observers: ContextVar[tuple[Observer, ...]] = ContextVar('srstudio_drawing_observers', default=())


@contextmanager
def observe(observer: Observer) -> Iterator[None]:
    """Receive events in this context; nested observation and exceptional exits restore previous observers."""
    token = _observers.set((*_observers.get(), observer))
    try:
        yield
    finally:
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
