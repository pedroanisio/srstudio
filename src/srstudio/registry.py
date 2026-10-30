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
    character_version: CharacterVersionDetails | None


def _signature(builder: Callable[..., Any]) -> inspect.Signature:
    try:
        return inspect.signature(builder)
    except (TypeError, ValueError) as exc:
        raise RegistryError(f"cannot inspect this builder's signature: {exc}") from exc


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
    _registered_builder: Callable[..., Any] = field(init=False, repr=False, compare=False)
    _verified_builder: Callable[..., Any] | None = field(default=None, init=False, repr=False, compare=False)
    _verified_drawing: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._registered_builder = self.builder

    def __call__(self, *args, **kwargs):
        return self.builder(*args, **kwargs)

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
            "character_version": _character_version(self),
        }


def _character_version(entry: Entry) -> CharacterVersionDetails | None:
    """Version metadata for shipped characters; plugin characters may have no version record."""
    if entry.kind != "character":
        return None
    from . import characters

    base, separator, number = entry.name.partition("@")
    character = characters.load().get(base)
    if character is None or (separator and not number.isdecimal()):
        return None
    version_number = int(number) if separator else 1
    version = next((v for v in character.versions if v.number == version_number), None)
    if version is None:
        return None
    try:
        default = character.latest().number
    except characters.NotApprovedError:
        default = None
    default_name = characters.part_name(base, default) if default is not None else None
    default_entry = _REGISTRY["character"].get(default_name) if default_name is not None else None
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
        "character": base,
        "version": version.number,
        "status": "unverified" if _unverified(entry) else version.status,
        "record_status": version.status,
        "default_status": default_status,
        "default_version": default,
        "default_name": default_name,
    }


def _unverified(entry: Entry) -> bool:
    if not entry.replacement and entry.builder is entry._registered_builder:
        return False
    if entry.builder is not entry._verified_builder or entry._verified_drawing is None:
        return True
    from . import characters

    base, separator, number = entry.name.partition("@")
    character = characters.load().get(base)
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
) -> Callable[[_Builder], _Builder]:
    """Decorator: ``@register("prop", "coffee-cup", summary="...")``.

    ``style`` names the style the part belongs to; by default it is the style whose ``parts`` list the
    module, and ``""`` for a part shared by every style. Duplicate names are refused unless
    ``replace=True`` explicitly replaces the existing builder. ``slots`` declares location callbacks when
    they have no ``Slot`` annotation; ``examples`` supplies Python snippets using an existing ``ep`` Episode."""
    if kind not in KINDS:
        raise RegistryError(f"unknown kind {kind!r}; one of {KINDS}")

    def wrap(obj: _Builder) -> _Builder:
        if name in _REGISTRY[kind] and not replace:
            raise RegistryError(f"{kind} {name!r} is already registered; use replace=True to replace it")
        if slots:
            if kind != "location":
                raise RegistryError("only locations declare callback slots")
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
        _REGISTRY[kind][name] = Entry(
            kind, name, obj, doc, tuple(tags), obj.__module__, resolved, tuple(slots), tuple(examples), replace
        )
        return obj

    return wrap


def get(kind: str, name: str) -> Entry:
    try:
        return _REGISTRY[kind][name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY.get(kind, {})))
        raise NotRegisteredError(f"no {kind} named {name!r}; known: {known}") from None


def describe(kind: str, name: str) -> PartDetails:
    """Inspect a registered part without drawing: ``describe('location', 'office-wide')``."""
    return get(kind, name).describe()


def entries(kind: str | None = None, style: str | None = None) -> list[Entry]:
    """Registered parts, optionally of one kind and one style (shared parts are listed for every style)."""
    if kind is not None and kind not in KINDS:
        raise RegistryError(f"unknown kind {kind!r}; one of {KINDS}")
    kinds = [kind] if kind is not None else list(KINDS)
    out = [e for k in kinds for e in _REGISTRY[k].values()]
    if style is not None:
        out = [e for e in out if e.style in (style, "")]
    return out


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
            "character_version": _character_version(e),
        }
        for e in entries(kind, style)
    ]
