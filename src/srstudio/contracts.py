"""Bounded, read-only part contracts for agent discovery.

Argument shapes use JSON Schema 2020-12. They describe data representations, not a JSON-to-Python executor.
Runtime objects, unresolved types and recursive limits are marked explicitly; builders still own semantic
validation. Inspection never calls a builder or a dataclass default factory. Imported plugin Python is trusted.
"""

from __future__ import annotations

import enum
import inspect
import math
import types
from collections.abc import Callable, Mapping, Sequence
from dataclasses import MISSING, dataclass, fields, is_dataclass
from types import SimpleNamespace
from typing import Annotated, Any, Literal, NoReturn, Union, get_args, get_origin, get_type_hints, is_typeddict

from . import checks
from .errors import SrstudioError

SCHEMA = 'srstudio.part-contract/1.0.0'
JSON_SCHEMA = 'https://json-schema.org/draft/2020-12/schema'
_EMPTY = inspect.Signature.empty


class ContractError(SrstudioError, ValueError):
    """Explicit discovery metadata is inconsistent with its builder or contains invalid values."""


def _fail(message: str) -> NoReturn:
    raise ContractError(message, code='contract.metadata', remedy='Correct the declared part contract.')


def _pairs(values: tuple, label: str) -> None:
    if not isinstance(values, tuple) or len(values) > 1000:
        _fail(f'{label}: expected at most 1000 named entries in a tuple')
    names = []
    for pair in values:
        if not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], str) or not pair[0]:
            _fail(f'{label}: expected (nonempty name, value) pairs')
        names.append(pair[0])
    if len(names) != len(set(names)):
        _fail(f'{label}: duplicate names')


def _scalar(value: object) -> bool:
    return value is None or type(value) in (str, bool, int) or (type(value) is float and math.isfinite(value))


@dataclass(frozen=True)
class ParameterContract:
    """Explicit semantics supplement annotations; units and clocks are never inferred from names or defaults.

    ``fields`` decorates record properties and ``items`` decorates sequence elements. ``type`` supplies a missing
    Python annotation. Bounds and enums are authored claims about the builder, not newly imposed validation.
    """

    type: Any = _EMPTY
    description: str = ''
    unit: str | None = None
    timebase: str | None = None
    role: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    enum: tuple[str | float | int | bool | None, ...] = ()
    fields: tuple[tuple[str, ParameterContract], ...] = ()
    items: ParameterContract | None = None
    prefix_items: tuple[ParameterContract, ...] = ()
    space: str | None = None
    anchors: tuple[tuple[str, tuple[float, float]], ...] = ()

    def __post_init__(self) -> None:
        for name in ('description', 'unit', 'timebase', 'role', 'space'):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or len(value) > 4096):
                _fail(f'{name}: expected a string of at most 4096 characters')
        for name in ('minimum', 'maximum'):
            value = getattr(self, name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                _fail(f'{name}: expected a finite number')
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            _fail('minimum cannot exceed maximum')
        if not isinstance(self.enum, tuple) or len(self.enum) > 1000 or any(not _scalar(v) for v in self.enum):
            _fail('enum: expected at most 1000 finite JSON scalars')
        _pairs(self.fields, 'fields')
        if any(not isinstance(value, ParameterContract) for _, value in self.fields):
            _fail('fields: expected ParameterContract values')
        if self.items is not None and not isinstance(self.items, ParameterContract):
            _fail('items: expected a ParameterContract')
        if (
            not isinstance(self.prefix_items, tuple)
            or len(self.prefix_items) > 100
            or any(not isinstance(value, ParameterContract) for value in self.prefix_items)
        ):
            _fail('prefix_items: expected at most 100 ParameterContracts')
        _pairs(self.anchors, 'anchors')
        if self.anchors and (not self.unit or not self.space):
            _fail('anchors: declare the coordinate unit and space')
        for name, point in self.anchors:
            if (
                len(name) > 128
                or not isinstance(point, tuple)
                or len(point) != 2
                or not all(checks.number(value) for value in point)
            ):
                _fail('anchors: expected named finite 2D points')

    def apply(self, schema: dict) -> dict:
        result = dict(schema)
        for name, key in (
            ('description', 'description'),
            ('unit', 'x-unit'),
            ('timebase', 'x-timebase'),
            ('role', 'x-role'),
            ('space', 'x-space'),
            ('minimum', 'minimum'),
            ('maximum', 'maximum'),
        ):
            value = getattr(self, name)
            if value is not None and value != '':
                result[key] = value
        if self.enum:
            result['enum'] = list(self.enum)
        if self.anchors:
            result['x-anchors'] = {name: list(point) for name, point in self.anchors}
        nested = [
            key
            for key, active in (
                ('properties', bool(self.fields)),
                ('items', self.items is not None),
                ('prefixItems', bool(self.prefix_items)),
            )
            if active
        ]
        if nested and 'anyOf' in result:
            # Common metadata applies to every non-null alternative; never silently leave a branch undescribed.
            branches = result['anyOf']
            candidates = [b for b in branches if b.get('type') != 'null']
            if not candidates or any(not all(key in b for key in nested) for b in candidates):
                _fail(f'{nested}: requires compatible non-null branches')
            result['anyOf'] = [self.apply(b) if b.get('type') != 'null' else b for b in branches]
            return result
        if self.fields:
            properties = dict(result.get('properties', {}))
            for name, contract in self.fields:
                if name not in properties:
                    _fail(f'fields: missing record property {name!r}')
                properties[name] = contract.apply(properties[name])
            result['properties'] = properties
        if self.items is not None:
            if not isinstance(result.get('items'), dict):
                _fail('items: requires a homogeneous sequence annotation')
            result['items'] = self.items.apply(result['items'])
        if self.prefix_items:
            positions = result.get('prefixItems')
            if not isinstance(positions, list) or len(positions) != len(self.prefix_items):
                _fail('prefix_items: must match the annotated tuple arity')
            result['prefixItems'] = [c.apply(s) for c, s in zip(self.prefix_items, positions, strict=True)]
        return result


@dataclass(frozen=True)
class Operation:
    """A discoverable method or helper, with its own independent invocation contract."""

    name: str
    builder: Callable[..., Any]
    contract: PartContract | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 128 or not callable(self.builder):
            _fail('operation: expected a name of 1..128 characters and a callable')
        if self.contract is not None and not isinstance(self.contract, PartContract):
            _fail('operation: expected a PartContract or None')


@dataclass(frozen=True)
class PartContract:
    parameters: tuple[tuple[str, ParameterContract], ...] = ()
    capabilities: tuple[tuple[str, bool | None], ...] = ()
    vocabularies: tuple[tuple[str, tuple[str, ...]], ...] = ()
    constraints: tuple[str, ...] = ()
    operations: tuple[Operation, ...] = ()
    returns: ParameterContract | None = None

    def __post_init__(self) -> None:
        if self.returns is not None and not isinstance(self.returns, ParameterContract):
            _fail('returns: expected a ParameterContract or None')
        for name in ('parameters', 'capabilities', 'vocabularies'):
            _pairs(getattr(self, name), name)
        if any(not isinstance(value, ParameterContract) for _, value in self.parameters):
            _fail('parameters: expected ParameterContract values')
        if any(value is not None and type(value) is not bool for _, value in self.capabilities):
            _fail('capabilities: expected true, false or unknown (None)')
        if any(
            not isinstance(v, tuple) or len(v) > 1000 or any(not isinstance(s, str) for s in v)
            for _, v in self.vocabularies
        ):
            _fail('vocabularies: expected tuples of at most 1000 strings')
        if (
            not isinstance(self.constraints, tuple)
            or len(self.constraints) > 100
            or any(not isinstance(c, str) or len(c) > 4096 for c in self.constraints)
        ):
            _fail('constraints: expected at most 100 strings of at most 4096 characters')
        if (
            not isinstance(self.operations, tuple)
            or len(self.operations) > 20
            or any(not isinstance(o, Operation) or not o.name or not callable(o.builder) for o in self.operations)
        ):
            _fail('operations: expected at most 20 named callable operations')
        if len({o.name for o in self.operations}) != len(self.operations):
            _fail('operations: duplicate names')


def _named_tuple(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, tuple) and isinstance(getattr(obj, '_fields', None), tuple)


def _hints(obj: Any) -> dict[str, Any]:
    target = (
        obj.__init__
        if inspect.isclass(obj) and not (is_dataclass(obj) or is_typeddict(obj) or _named_tuple(obj))
        else obj
    )
    result = {}
    owners = tuple(reversed(target.__mro__)) if inspect.isclass(target) else (target,)
    for owner in owners:
        module = inspect.getmodule(owner)
        namespace = vars(module) if module is not None else {}
        for name, annotation in getattr(owner, '__annotations__', {}).items():
            try:
                # A TYPE_CHECKING-only name must not erase the other resolvable annotations. Inherited fields
                # resolve in their defining module, which may differ from the subclass's module.
                result[name] = get_type_hints(
                    SimpleNamespace(__annotations__={name: annotation}), globalns=namespace, include_extras=True
                )[name]
            except (NameError, TypeError, SyntaxError):
                result[name] = annotation
    return result


def _name(value: Any) -> str:
    if isinstance(value, str):
        return value[:4096]
    return f'{getattr(value, "__module__", "")}.{getattr(value, "__qualname__", type(value).__name__)}'


class _Shapes:
    def __init__(self) -> None:
        self.remaining = 2000

    def shape(self, annotation: Any, seen: tuple = ()) -> dict:
        self.remaining -= 1
        if self.remaining < 0 or len(seen) >= 8 or any(annotation is previous for previous in seen):
            return {'x-status': 'unknown', 'x-reason': 'recursive-or-budget-limit'}
        if annotation is _EMPTY or annotation is Any or isinstance(annotation, str):
            return {'x-status': 'unknown', 'x-python-type': _name(annotation)}
        primitives = {str: 'string', float: 'number', int: 'integer', bool: 'boolean', type(None): 'null'}
        if annotation in primitives:
            return {'type': primitives[annotation]}
        origin, args = get_origin(annotation), get_args(annotation)
        if origin is Annotated:
            result = self.shape(args[0], seen)
            for metadata in args[1:]:
                if isinstance(metadata, ParameterContract):
                    result = metadata.apply(result)
            return result
        if origin in (Union, types.UnionType):
            return {'anyOf': [self.shape(a, (*seen, annotation)) for a in args]}
        if origin is Literal and all(_scalar(a) for a in args):
            return {'enum': list(args)}
        if inspect.isclass(annotation) and issubclass(annotation, enum.Enum):
            values = tuple(a.value for a in annotation)
            if all(_scalar(v) for v in values):
                return {'enum': list(values)}
        if origin in (list, tuple, Sequence) or annotation in (list, tuple):
            if origin is tuple and args and args[-1] is not Ellipsis:
                return {
                    'type': 'array',
                    'prefixItems': [self.shape(a, (*seen, annotation)) for a in args],
                    'minItems': len(args),
                    'maxItems': len(args),
                }
            return {'type': 'array', 'items': self.shape(args[0] if args else Any, (*seen, annotation))}
        if origin in (dict, Mapping) or annotation is dict:
            if args and args[0] is not str:
                return {'x-status': 'runtime', 'x-python-type': _name(annotation)}
            return {'type': 'object', 'additionalProperties': self.shape(args[1] if args else Any, (*seen, annotation))}
        if is_typeddict(annotation):
            hints = _hints(annotation)
            return {
                'type': 'object',
                'properties': {name: self.shape(value, (*seen, annotation)) for name, value in hints.items()},
                'required': [name for name in hints if name in annotation.__required_keys__],
                'additionalProperties': False,
                'x-python-type': _name(annotation),
            }
        if _named_tuple(annotation):
            hints = _hints(annotation)
            properties, required = {}, []
            defaults = annotation._field_defaults
            for name in annotation._fields:
                properties[name] = self.shape(hints.get(name, Any), (*seen, annotation))
                if name not in defaults:
                    required.append(name)
                elif _scalar(defaults[name]):
                    properties[name]['default'] = defaults[name]
            return {
                'type': 'object',
                'properties': properties,
                'required': required,
                'additionalProperties': False,
                'x-python-type': _name(annotation),
            }
        if inspect.isclass(annotation) and is_dataclass(annotation):
            hints = _hints(annotation)
            properties, required = {}, []
            for f in fields(annotation):
                if not f.init:
                    continue
                properties[f.name] = self.shape(hints.get(f.name, f.type), (*seen, annotation))
                if f.default is MISSING and f.default_factory is MISSING:
                    required.append(f.name)
                elif f.default is not MISSING and _scalar(f.default):
                    properties[f.name]['default'] = f.default
            return {
                'type': 'object',
                'properties': properties,
                'required': required,
                'additionalProperties': False,
                'x-python-type': _name(annotation),
            }
        return {'x-status': 'runtime', 'x-python-type': _name(annotation)}


def _complete(value: Any) -> bool:
    if isinstance(value, dict):
        return 'x-status' not in value and all(_complete(v) for v in value.values())
    return all(_complete(v) for v in value) if isinstance(value, list) else True


def describe_callable(
    builder: Callable[..., Any], contract: PartContract | None = None, *, method: bool = False, _depth: int = 0
) -> dict[str, Any]:
    """Describe a Python call, without executing it; ``method`` omits the bound receiver parameter."""
    if _depth > 4:
        _fail('operations exceed the nesting limit of four')
    if contract is not None and not isinstance(contract, PartContract):
        _fail('contract: expected a PartContract')
    metadata = contract or PartContract()
    try:
        signature = inspect.signature(builder)
    except (ValueError, TypeError) as exc:
        raise ContractError(f'cannot inspect contract signature: {exc}', code='contract.signature') from exc
    declared = dict(metadata.parameters)
    missing = declared.keys() - signature.parameters.keys()
    if missing:
        _fail(f'parameters: missing builder parameter(s) {sorted(missing)}')
    shapes = _Shapes()
    hints = _hints(builder)
    properties, required = {}, []
    additional: bool | dict = False
    for i, p in enumerate(signature.parameters.values()):
        if method and i == 0:
            continue
        spec = declared.get(p.name, ParameterContract())
        annotation = spec.type if spec.type is not _EMPTY else hints.get(p.name, p.annotation)
        shape = spec.apply(shapes.shape(annotation))
        shape['x-python-kind'] = p.kind.name
        if p.kind is p.VAR_KEYWORD:
            additional = shape
            continue
        if p.kind is p.VAR_POSITIONAL:
            shape = {'type': 'array', 'items': shape, 'x-python-kind': p.kind.name}
        elif p.default is p.empty:
            required.append(p.name)
        elif _scalar(p.default):
            shape['default'] = p.default
        properties[p.name] = shape
    arguments = {
        '$schema': JSON_SCHEMA,
        'type': 'object',
        'properties': properties,
        'required': required,
        'additionalProperties': additional,
    }
    result_spec = metadata.returns or ParameterContract()
    result_type = (
        result_spec.type
        if result_spec.type is not _EMPTY
        else builder
        if inspect.isclass(builder)
        else hints.get('return', signature.return_annotation)
    )
    returns = result_spec.apply(shapes.shape(result_type))
    capabilities = {'limbs': None, 'head_motion': None, 'expressions': None, **dict(metadata.capabilities)}
    return {
        'schema': SCHEMA,
        'invocation': 'construct' if inspect.isclass(builder) else 'call',
        'arguments': arguments,
        'returns': returns,
        'shape_complete': _complete(arguments),
        'validation': 'runtime-required',
        'capabilities': capabilities,
        'vocabularies': {name: list(values) for name, values in metadata.vocabularies},
        'constraints': list(metadata.constraints),
        'operations': {
            o.name: describe_callable(o.builder, o.contract, _depth=_depth + 1) for o in metadata.operations
        },
    }


def describe_part(builder: Callable[..., Any], contract: PartContract | None = None) -> dict[str, Any]:
    """Add the known Actor lifecycle; other builders must declare capabilities explicitly."""
    from .rig import Actor

    result = describe_callable(builder, contract)
    if inspect.isclass(builder) and issubclass(builder, Actor):
        # These properties are part of Actor's public interface, not guesses from a builder's parameter names.
        result['capabilities']['limbs'] = builder.supports_limbs
        if builder.build is Actor.build:
            result['capabilities'].update(mouths=True, blinks=True, nods=True)
        result['capabilities'].update(dict(contract.capabilities) if contract else {})
        result['vocabularies']['mouths'] = list(builder.mouth_poses)
        if hasattr(builder, 'extra_options'):
            result['vocabularies']['extras'] = sorted(builder.extra_options)
        time = ParameterContract(unit='seconds', timebase='canvas', minimum=0)
        placement = PartContract(
            parameters=(
                ('x', ParameterContract(unit='parent units')),
                ('y', ParameterContract(unit='parent units')),
                ('scale', ParameterContract(unit='ratio')),
                ('end', ParameterContract(unit='seconds', timebase='canvas', role='end', minimum=0)),
                (
                    'perf',
                    ParameterContract(
                        fields=(
                            (
                                'mouth',
                                ParameterContract(
                                    items=ParameterContract(
                                        prefix_items=(time, ParameterContract(enum=builder.mouth_poses))
                                    )
                                ),
                            ),
                            ('blinks', ParameterContract(items=ParameterContract(prefix_items=(time, time)))),
                            (
                                'nods',
                                ParameterContract(
                                    items=ParameterContract(
                                        prefix_items=(
                                            ParameterContract(unit='seconds', timebase='canvas'),
                                            ParameterContract(unit='degrees'),
                                        )
                                    )
                                ),
                            ),
                            ('limbs', ParameterContract(description='Typed LimbTracks use motion seconds.')),
                            (
                                'extras',
                                ParameterContract(
                                    description='Rig-specific options; see vocabularies.extras and builder validation.'
                                ),
                            ),
                        )
                    ),
                ),
            )
        )
        if 'build' not in result['operations']:
            result['operations']['build'] = describe_callable(
                builder.build, placement if builder.build is Actor.build else None, method=True
            )
    return result
