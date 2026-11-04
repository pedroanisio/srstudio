"""A registry of everything that can be placed in a scene.

Builders register under a kind (``character``, ``location``, ``prop``, ``graphic``) and a
name. New modules extend the catalogue just by importing them; ``srstudio catalog`` lists
what is available with its summary and its style. The style is taken from the module (see
:func:`srstudio.styles.style_of_module`) unless ``register`` names one; parts that adapt to any palette, like the
signature marks, carry no style. Which episodes use a part is measured, not declared: ``srstudio usage`` builds
every episode and records the parts it calls (ADR 0017, ADR 0032).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict, TypeVar

from . import drawing_events
from .contracts import PartContract, describe_callable, describe_part
from .errors import SrstudioError

KINDS = ("character", "location", "prop", "graphic")
_Builder = TypeVar("_Builder", bound=Callable[..., Any])


class RegistryError(SrstudioError, ValueError):
    """An unknown kind or an attempt to replace a registered part without opting in."""


class NotRegisteredError(SrstudioError, KeyError):
    """No part of that kind is registered under that name."""


class ParameterDetails(TypedDict):
    name: str
    kind: str
    annotation: str | None
    required: bool
    default: str | None


class CharacterVersionDetails(TypedDict):
    character: str
    version: int
    status: str
    record_status: str
    default_status: str | None
    default_version: int | None
    default_name: str | None


class PartVersionDetails(TypedDict):
    part: str
    version: int
    status: str
    record_status: str
    default_status: str | None
    default_version: int | None
    default_name: str | None


class PartDetails(TypedDict):
    kind: str
    name: str
    summary: str
    module: str
    style: str
    tags: list[str]
    signature: str
    parameters: list[ParameterDetails]
    slots: list[str]
    documentation: str
    call_template: str
    examples: list[str]
    part_version: PartVersionDetails | None
    character_version: CharacterVersionDetails | None
    contract: dict[str, Any]


def _signature(builder: Callable[..., Any]) -> inspect.Signature:
    try:
        return inspect.signature(builder)
    except (TypeError, ValueError) as exc:
        raise RegistryError(f"cannot inspect this builder's signature: {exc}") from exc


@dataclass(frozen=True)
class _OriginalEntry:
    builder: Callable[..., Any]
    summary: str
    tags: tuple[str, ...]
    module: str
    style: str
    slots: tuple[str, ...]
    examples: tuple[str, ...]
    contract: PartContract | None


@dataclass
class Entry:
    kind: str
    name: str
    builder: Callable[..., Any]
    summary: str = ""
    tags: tuple[str, ...] = ()
    module: str = ""
    style: str = ""  # style slug, or "" when the part serves every style
    slots: tuple[str, ...] = ()  # extra callback names for builders without Slot annotations
    examples: tuple[str, ...] = ()  # Python snippets; ep is an existing Episode
    replacement: bool = False
    contract: PartContract | None = None
    _registered_builder: Callable[..., Any] = field(init=False, repr=False, compare=False)
    _original: _OriginalEntry | None = field(init=False, repr=False, compare=False)
    _verified_builder: Callable[..., Any] | None = field(default=None, init=False, repr=False, compare=False)
    _verified_drawing: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._registered_builder = self.builder
        self._original = (
            None
            if self.replacement
            else _OriginalEntry(
                self.builder, self.summary, self.tags, self.module, self.style, self.slots, self.examples, self.contract
            )
        )

    def __call__(self, *args, **kwargs):
        return drawing_events.call(self.builder, *args, **kwargs)

    @property
    def _current_contract(self) -> PartContract | None:
        """Authored metadata belongs to its registered callable, including when signatures happen to match."""
        return self.contract if self.builder is self._registered_builder else None

    def _describe_contract(self) -> dict[str, Any]:
        result = describe_part(self.builder, self._current_contract)
        if self.contract is not None and self._current_contract is None:
            result['declaration_status'] = 'builder-changed'
        return result

    def describe(self) -> PartDetails:
        """Signature, callback slots, documentation and usage; never calls the builder."""
        signature = _signature(self.builder)
        parameters: list[ParameterDetails] = []
        slots = []
        arguments = []
        for p in signature.parameters.values():
            variadic = p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            required = p.default is p.empty and not variadic
            annotation = None if p.annotation is p.empty else inspect.formatannotation(p.annotation)
            parameters.append(
                {
                    "name": p.name,
                    "kind": p.kind.name,
                    "annotation": annotation,
                    "required": required,
                    "default": None if p.default is p.empty else repr(p.default),
                }
            )
            # Slot is the library's callback alias. Explicit metadata covers unannotated plugins.
            if p.name in self.slots or (
                self.kind == "location" and p.annotation in ("Slot", "'Slot'", Callable[[object], None] | None)
            ):
                slots.append(p.name)
            if required:
                arguments.append(f"{p.name}={p.name}" if p.kind is p.KEYWORD_ONLY else p.name)
        return {
            "kind": self.kind,
            "name": self.name,
            "summary": self.summary,
            "module": self.module,
            "style": self.style,
            "tags": list(self.tags),
            "signature": str(signature),
            "parameters": parameters,
            "slots": slots,
            "documentation": inspect.getdoc(self.builder) or "",
            "call_template": f"part({', '.join(arguments)})",
            "examples": list(self.examples),
            "part_version": _part_version(self),
            "character_version": _character_version(self),
            "contract": self._describe_contract(),
        }


def _part_version(entry: Entry) -> PartVersionDetails | None:
    """Version metadata for a recorded part; plugins may have no matching record."""
    from . import parts

    base, separator, number = entry.name.partition("@")
    part = parts.load().get(base)
    if part is None or part.kind != entry.kind or (separator and not number.isdecimal()):
        return None
    version_number = int(number) if separator else 1
    version = next((v for v in part.versions if v.number == version_number), None)
    if version is None:
        return None
    try:
        default = part.latest().number
    except parts.NotApprovedError:
        default = None
    default_name = parts.part_name(base, default) if default is not None else None
    default_entry = _REGISTRY[entry.kind].get(default_name) if default_name is not None else None
    default_status = (
        None
        if default is None
        else "unavailable"
        if default_entry is None
        else "unverified"
        if _unverified(default_entry)
        else "approved"
    )
    return {
        "part": base,
        "version": version.number,
        "status": "unverified" if _unverified(entry) else version.status,
        "record_status": version.status,
        "default_status": default_status,
        "default_version": default,
        "default_name": default_name,
    }


def _character_version(entry: Entry) -> CharacterVersionDetails | None:
    """Legacy character-only view retained for existing catalog clients."""
    if entry.kind != "character":
        return None
    info = _part_version(entry)
    if info is None:
        return None
    return {
        "character": info["part"],
        "version": info["version"],
        "status": info["status"],
        "record_status": info["record_status"],
        "default_status": info["default_status"],
        "default_version": info["default_version"],
        "default_name": info["default_name"],
    }


def _unverified(entry: Entry) -> bool:
    if not entry.replacement and entry.builder is entry._registered_builder:
        return False
    if entry.builder is not entry._verified_builder or entry._verified_drawing is None:
        return True
    from . import parts

    base, separator, number = entry.name.partition("@")
    character = parts.load().get(base)
    if character is None or (separator and not number.isdecimal()):
        return True
    version_number = int(number) if separator else 1
    return not any(
        version.number == version_number and version.status == "approved" and version.drawing == entry._verified_drawing
        for version in character.versions
    )


_REGISTRY: dict[str, dict[str, Entry]] = {k: {} for k in KINDS}


def register(
    kind: str,
    name: str,
    *,
    summary: str = "",
    tags: tuple[str, ...] = (),
    style: str | None = None,
    replace: bool = False,
    slots: tuple[str, ...] = (),
    examples: tuple[str, ...] = (),
    contract: PartContract | None = None,
) -> Callable[[_Builder], _Builder]:
    """Decorator: ``@register("prop", "coffee-cup", summary="...")``.

    ``style`` names the style the part belongs to; by default it is the style whose ``parts`` list the
    module, and ``""`` for a part shared by every style. Duplicate names are refused unless
    ``replace=True`` explicitly replaces the existing builder. ``slots`` declares drawing callbacks when
    they have no ``Slot`` annotation; ``examples`` supplies Python snippets using an existing ``ep`` Episode.
    ``contract`` adds structured discovery semantics without replacing the builder's runtime validation.

    Use the returned callable: it emits explicit usage events while preserving its signature and function kind.
    Class registration retains the class identity and instruments only methods declared on that class.
    Deferred builders are attributed when their bodies execute, not when their generator/coroutine is created.
    Shared performers can identify their owning registered callable with ``drawing_events.drawing(owner)``."""
    if kind not in KINDS:
        raise RegistryError(f"unknown kind {kind!r}; one of {KINDS}")

    def wrap(obj: _Builder) -> _Builder:
        if name in _REGISTRY[kind] and not replace:
            raise RegistryError(f"{kind} {name!r} is already registered; use replace=True to replace it")
        if contract is not None:
            describe_callable(obj, contract)  # Refuse invalid metadata before mutating the registry.
        if slots:
            parameters = _signature(obj).parameters
            for slot in slots:
                if slot not in parameters or parameters[slot].kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ):
                    raise RegistryError(f"{name}: callback slot {slot!r} must name an explicit builder parameter")
        doc = summary
        if not doc and obj.__doc__:
            doc = obj.__doc__.strip().splitlines()[0]
        from .styles import style_of_module  # here, not at import: styles imports canvas and soundtrack

        resolved = style_of_module(obj.__module__) if style is None else style
        previous = _REGISTRY[kind].get(name)
        if previous is None or obj is not previous.builder:  # the current builder is already instrumented
            obj = drawing_events.instrument(obj)
        entry = Entry(
            kind,
            name,
            obj,
            doc,
            tuple(tags),
            obj.__module__,
            resolved,
            tuple(slots),
            tuple(examples),
            replace,
            contract,
        )
        if previous is not None:
            entry._original = previous._original
        _REGISTRY[kind][name] = entry
        return obj

    return wrap


def get(kind: str, name: str) -> Entry:
    _kind(kind)
    try:
        return _REGISTRY[kind][name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY.get(kind, {})))
        raise NotRegisteredError(
            f"no {kind} named {name!r}; known: {known}",
            code='registry.not_found',
            path='name',
            actual=name,
            expected=sorted(_REGISTRY.get(kind, {})),
            remedy='Choose a name from srstudio catalog for this kind.',
        ) from None


def describe(kind: str, name: str) -> PartDetails:
    """Inspect a registered part without drawing: ``describe('location', 'office-wide')``."""
    return get(kind, name).describe()


def entries(kind: str | None = None, style: str | None = None) -> list[Entry]:
    """Registered parts, optionally of one kind and one style (shared parts are listed for every style)."""
    if kind is not None:
        _kind(kind)
    if style is not None:
        from .styles import STYLES

        known = sorted(set(STYLES) | {e.style for group in _REGISTRY.values() for e in group.values()})
        if style not in known:
            raise _option('style', style, known)
    kinds = [kind] if kind is not None else list(KINDS)
    out = [e for k in kinds for e in _REGISTRY[k].values()]
    if style is not None:
        out = [e for e in out if e.style in (style, "")]
    return out


def _option(path: str, actual: object, expected: object) -> RegistryError:
    return RegistryError(
        f'unknown {path} {actual!r}; expected {expected}',
        code=f'registry.{path}',
        path=path,
        actual=actual,
        expected=expected,
        remedy=f'Choose a supported {path} from expected.',
    )


def _kind(kind: str) -> None:
    if kind not in KINDS:
        raise _option('kind', kind, list(KINDS))


def select_fields(data: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Select explicit dotted dictionary paths; a typo never silently drops requested information."""
    result: dict[str, Any] = {}
    for field_name in fields:
        source, destination = data, result
        pieces = field_name.split('.')
        for i, piece in enumerate(pieces):
            if not isinstance(source, dict) or piece not in source:
                raise _option(
                    'fields', field_name, sorted(source) if isinstance(source, dict) else 'a dictionary field'
                )
            if i == len(pieces) - 1:
                destination[piece] = source[piece]
            else:
                if not isinstance(source[piece], dict):
                    raise _option('fields', field_name, f'{piece} has no nested fields')
                # Copies avoid changing the source if a broad field and its child are both selected.
                destination[piece] = dict(destination.get(piece, {}))
                destination = destination[piece]
                source = source[piece]
    return result


def search(
    query: str = '',
    *,
    kind: str | None = None,
    style: str | None = None,
    capabilities: tuple[str, ...] = (),
    limit: int = 20,
    offset: int = 0,
    fields: tuple[str, ...] = ('kind', 'name', 'style', 'summary'),
) -> dict[str, Any]:
    """Bounded, stable discovery. Capabilities match explicit True declarations only.

    Pages are sorted by (kind, name); offsets are relative to the current registry state.
    Import plugins before paging and keep that state unchanged until all pages are read.
    """
    if not isinstance(query, str):
        raise _option('query', query, 'string')
    for name, value, low, high in (('limit', limit, 1, 100), ('offset', offset, 0, 1_000_000)):
        if type(value) is not int or not low <= value <= high:
            raise _option(name, value, f'integer in {low}..{high}')
    selected = entries(kind, style)
    known = {'limbs', 'head_motion', 'expressions'} | {
        name
        for group in _REGISTRY.values()
        for entry in group.values()
        if entry._current_contract
        for name, _ in entry._current_contract.capabilities
    }
    for capability in capabilities:
        if capability not in known:
            raise _option('capabilities', capability, sorted(known))
    allowed = {'kind', 'name', 'style', 'summary', 'tags', 'module', 'part_version', 'character_version'}
    if not fields or any(name not in allowed for name in fields):
        raise _option('fields', fields, sorted(allowed))
    words = query.casefold().split()
    selected = [e for e in selected if all(word in ' '.join((e.name, e.summary, *e.tags)).casefold() for word in words)]
    if capabilities:
        selected = [
            e for e in selected if all(e._describe_contract()['capabilities'].get(c) is True for c in capabilities)
        ]
    selected.sort(key=lambda e: (e.kind, e.name))
    rows = []
    for entry in selected[offset : offset + limit]:
        row = {name: getattr(entry, name) for name in fields if name not in ('part_version', 'character_version')}
        if 'tags' in fields:
            row['tags'] = list(entry.tags)
        if 'part_version' in fields:
            row['part_version'] = _part_version(entry)
        if 'character_version' in fields:
            row['character_version'] = _character_version(entry)
        rows.append(row)
    return {
        'schema': 'srstudio.catalog-page/1.0.0',
        'items': rows,
        'total': len(selected),
        'offset': offset,
        'limit': limit,
        'next_offset': offset + limit if offset + limit < len(selected) else None,
    }


def catalog(style: str | None = None, *, kind: str | None = None) -> list[dict]:
    """The registry as plain data, for a listing or a page; the same parts :func:`entries` lists."""
    return [
        {
            "kind": e.kind,
            "name": e.name,
            "summary": e.summary,
            "tags": list(e.tags),
            "module": e.module,
            "style": e.style,
            "part_version": _part_version(e),
            "character_version": _character_version(e),
        }
        for e in entries(kind, style)
    ]


def contract_coverage(style: str | None = None, *, kind: str | None = None) -> dict:
    """Report declared semantics separately from argument shape inference; never invoke builders.

    Explicit metadata may still be partial. A complete argument shape is not proof of
    units, clocks, capabilities, return types or runtime semantic validation.
    """
    selected = entries(kind, style)

    def contains(value: object, key: str) -> bool:
        if isinstance(value, dict):
            return key in value or any(contains(v, key) for v in value.values())
        return isinstance(value, list) and any(contains(v, key) for v in value)

    kinds = {}
    for name in (kind,) if kind else KINDS:
        rows = [e for e in selected if e.kind == name]
        contracts = [e._describe_contract() for e in rows]
        kinds[name] = {
            'registered': len(rows),
            'explicit_contracts': sum(e._current_contract is not None for e in rows),
            'shape_complete': sum(c['shape_complete'] for c in contracts),
            'with_units': sum(contains(c, 'x-unit') for c in contracts),
            'with_clocks': sum(contains(c, 'x-timebase') for c in contracts),
            'with_anchors': sum(contains(c, 'x-anchors') for c in contracts),
            'undeclared_parts': sorted(e.name for e in rows if e._current_contract is None),
            'stale_contract_parts': sorted(
                e.name for e in rows if e.contract is not None and e._current_contract is None
            ),
        }
    return {
        'schema': 'srstudio.contract-coverage/1.0.0',
        'kind': kind,
        'style': style,
        'kinds': kinds,
        'qualification': (
            'Declared metadata and complete argument shapes do not certify semantic completeness or validity.'
        ),
    }
