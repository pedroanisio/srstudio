"""Closed, bounded parsing for composition records; no coercion of booleans or unknown fields."""

from __future__ import annotations

import json
import math
import types
from collections.abc import Iterable
from dataclasses import MISSING, fields
from functools import lru_cache
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints

from . import composition as c


@lru_cache(maxsize=32)
def _hints(cls: type[Any]) -> dict:
    return get_type_hints(cls)


def _value(value: Any, kind: Any, path: str, *, parsing: bool, depth: int = 0) -> Any:
    if depth > 16:
        raise c._fail(path, depth, 'at most 16 nested records')
    origin, args = get_origin(kind), get_args(kind)
    if origin is Literal:
        if not any(type(value) is type(option) and value == option for option in args):
            raise c._fail(path, value, args)
        return value
    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        for option in args:
            if option is not type(None):
                try:
                    return _value(value, option, path, parsing=parsing, depth=depth + 1)
                except c.CompositionError:
                    continue
        raise c._fail(path, value, str(kind))
    if origin is tuple:
        allowed = (tuple, list) if parsing else (tuple,)
        if type(value) not in allowed or len(value) > c.MAX_RECORD_ITEMS:
            raise c._fail(path, value, f'an immutable sequence with at most {c.MAX_RECORD_ITEMS} items')
        repeated = len(args) == 2 and args[1] is Ellipsis
        if not repeated and len(value) != len(args):
            raise c._fail(path, value, f'exactly {len(args)} items')
        return tuple(
            _value(v, args[0] if repeated else args[i], f'{path}[{i}]', parsing=parsing, depth=depth + 1)
            for i, v in enumerate(value)
        )
    if isinstance(kind, type) and issubclass(kind, c._Record):
        if parsing:
            return _record(kind, value, path, depth=depth + 1)
        if type(value) is not kind:
            raise c._fail(path, type(value).__name__, kind.__name__)
        return value
    valid = (
        kind is str
        and type(value) is str
        and len(value) <= 4096
        and '\x00' not in value
        or kind is int
        and type(value) is int
        and abs(value) <= 2**53
        or kind is float
        and type(value) in (int, float)
        and abs(value) <= 2**53
        and math.isfinite(value)
    )
    if not valid:
        raise c._fail(path, value, str(kind))
    return value


def validate_record(value: c._Record) -> None:
    # Classes are hashable; mypy confuses the instance hash signature on this dataclass base.
    hints = _hints(cast(Any, type(value)))
    for f in fields(value):
        item = getattr(value, f.name)
        _value(item, hints[f.name], f'{type(value).__name__}.{f.name}', parsing=False)
        if f.metadata and not f.metadata['minimum'] <= item <= f.metadata['maximum']:
            raise c._fail(f'{type(value).__name__}.{f.name}', item, dict(f.metadata))


def _record(cls: type, value: object, path: str, *, depth: int = 0):
    if type(value) is not dict:
        raise c._fail(path, value, f'a {cls.__name__} object')
    declared = {f.name: f for f in fields(cls)}
    unknown = set(value) - set(declared)
    if unknown:
        name = sorted(unknown, key=str)[0]
        raise c._fail(f'{path}.{name}', value[name], 'a declared field')
    missing = [
        name
        for name, f in declared.items()
        if name not in value and f.default is MISSING and f.default_factory is MISSING
    ]
    if missing:
        raise c._fail(f'{path}.{missing[0]}', None, 'a required field')
    hints = _hints(cls)
    return cls(
        **{name: _value(item, hints[name], f'{path}.{name}', parsing=True, depth=depth) for name, item in value.items()}
    )


def _string_bytes(value: str) -> int:
    try:
        return len(value.encode('utf-8'))
    except UnicodeError as error:
        raise c._fail('scene', None, 'valid UTF-8 text') from error


def _bounded_tree(value: Any, seen: set[int], count: list[int], depth: int = 0) -> None:
    count[0] += 1
    if count[0] > c.MAX_GRAPH_ITEMS or depth > 16:
        raise c._fail('scene', count[0], 'a bounded, shallow input graph')
    if type(value) in (dict, list, tuple):
        if id(value) in seen:
            raise c._fail('scene', None, 'an acyclic input graph')
        seen.add(id(value))
        children: Iterable[Any]
        if type(value) is dict:
            if any(type(k) is not str or len(k) > 128 for k in value):
                raise c._fail('scene', None, 'short string field names')
            count[1] += sum(_string_bytes(k) for k in value)
            if count[1] > c.MAX_INPUT_BYTES:
                raise c._fail('scene', count[1], f'at most {c.MAX_INPUT_BYTES} string bytes')
            children = value.values()
        else:
            children = value
        if len(value) > c.MAX_RECORD_ITEMS:
            raise c._fail('scene', len(value), 'a bounded collection')
        for child in children:
            _bounded_tree(child, seen, count, depth + 1)
        seen.remove(id(value))
    elif type(value) is str:
        if len(value) > 4096:
            raise c._fail('scene', len(value), 'strings no longer than 4096 characters')
        count[1] += _string_bytes(value)
        if count[1] > c.MAX_INPUT_BYTES:
            raise c._fail('scene', count[1], f'at most {c.MAX_INPUT_BYTES} string bytes')


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for name, value in pairs:
        if name in result:
            raise c._fail(name, None, 'a field declared only once')
        result[name] = value
    return result


def parse_scene(value: str | dict) -> c.ScenePlan:
    if type(value) is str:
        if len(value) > c.MAX_INPUT_BYTES or _string_bytes(value) > c.MAX_INPUT_BYTES:
            raise c._fail('scene', len(value), f'at most {c.MAX_INPUT_BYTES} encoded bytes')
        try:
            value = json.loads(value, object_pairs_hook=_unique)
        except (ValueError, RecursionError) as error:
            if isinstance(error, c.CompositionError):
                raise
            raise c._fail('scene', None, 'valid bounded JSON') from error
    _bounded_tree(value, set(), [0, 0])
    return _record(c.ScenePlan, value, 'scene')
