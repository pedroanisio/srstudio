"""A registry of everything that can be placed in a scene.

Builders register under a kind (``character``, ``location``, ``prop``, ``graphic``) and a
name. New modules extend the catalogue just by importing them; ``srstudio catalog`` lists
what is available with its summary, its style and the episodes it appeared in. The style is
taken from the module (see :func:`srstudio.styles.style_of_module`) unless ``register`` names one;
parts that adapt to any palette, like the signature marks, carry no style.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

KINDS = ("character", "location", "prop", "graphic")


@dataclass
class Entry:
    kind: str
    name: str
    builder: Callable[..., Any]
    summary: str = ""
    episodes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    module: str = ""
    style: str = ""  # style slug, or "" when the part serves every style

    def __call__(self, *args, **kwargs):
        return self.builder(*args, **kwargs)


_REGISTRY: dict[str, dict[str, Entry]] = {k: {} for k in KINDS}


def register(
    kind: str,
    name: str,
    *,
    summary: str = "",
    episodes: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    style: str | None = None,
):
    """Decorator: ``@register("prop", "coffee-cup", summary="...", episodes=("05",))``.

    ``style`` names the style the part belongs to; by default it is the style whose ``parts`` list the
    module, and ``""`` for a part shared by every style."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; one of {KINDS}")

    def wrap(obj):
        doc = summary
        if not doc and obj.__doc__:
            doc = obj.__doc__.strip().splitlines()[0]
        from .styles import style_of_module  # here, not at import: styles imports canvas and soundtrack

        resolved = style_of_module(obj.__module__) if style is None else style
        _REGISTRY[kind][name] = Entry(kind, name, obj, doc, tuple(episodes), tuple(tags), obj.__module__, resolved)
        return obj

    return wrap


def get(kind: str, name: str) -> Entry:
    try:
        return _REGISTRY[kind][name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY.get(kind, {})))
        raise KeyError(f"no {kind} named {name!r}; known: {known}") from None


def entries(kind: str | None = None, style: str | None = None) -> list[Entry]:
    """Registered parts, optionally of one kind and one style (shared parts are listed for every style)."""
    kinds = [kind] if kind else list(KINDS)
    out = [e for k in kinds for e in _REGISTRY[k].values()]
    if style is not None:
        out = [e for e in out if e.style in (style, "")]
    return out


def catalog(style: str | None = None) -> list[dict]:
    """The registry as plain data, for a listing or a page."""
    return [
        {
            "kind": e.kind,
            "name": e.name,
            "summary": e.summary,
            "episodes": list(e.episodes),
            "tags": list(e.tags),
            "module": e.module,
            "style": e.style,
        }
        for e in entries(style=style)
    ]
