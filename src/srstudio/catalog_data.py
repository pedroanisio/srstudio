"""``catalog.json``: the structure the catalog site's app reads, as typed values (ADR 0046).

``srstudio page`` generates the file from the cards, the notes, the registry and the measured usage; nobody edits
it. :func:`parse` turns a document back into :class:`Catalog` and refuses unknown fields, missing fields and wrong
types. :func:`validate` asserts what a schema cannot express: every cross-reference resolves in both directions, and
a video that was not measured claims no parts. The build runs both over its own output, so a site is never written
with a document its reader would refuse.

Fields ending in ``_html`` are curated markup from the notes; every other text is plain and the app escapes it.
"""

from __future__ import annotations

import json
import math
import re
import types
import typing
from dataclasses import MISSING, asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, TypeVar, Union

from .errors import SrstudioError

SCHEMA_VERSION = "1.1.0"
SOURCES = ("library", "package", "no-render")  # a card with a render, an original package, a project without one
KINDS = ("character", "location", "prop", "graphic")
_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_MEDIA = re.compile(r"media/[0-9a-f]{32}\.[a-z0-9]+")

T = TypeVar("T")


class CatalogError(SrstudioError):
    """A notes file, project, base page, media step or catalog document the site cannot be built from."""


@dataclass(frozen=True)
class Line:
    t: float
    who: str
    voice: str
    text: str
    sfx: bool = False


@dataclass(frozen=True)
class Still:
    src: str
    width: int
    height: int
    label: str = ""
    video: str = ""  # the video it was cut from; "" for the pose sheet, which the engine rendered


@dataclass(frozen=True)
class GalleryEntry:
    name: str
    note_html: str
    voice: str
    still: Still
    poses: tuple[Still, ...] = ()


@dataclass(frozen=True)
class Part:
    name: str  # the registered name: unique across kinds, and the part's route
    kind: str
    title: str  # what the notes call this part alone, or a title from its registered summary until they do
    style: str  # "" for a part shared by every style
    summary: str
    videos: tuple[str, ...]  # measured
    gallery: tuple[GalleryEntry, ...] = ()
    sheet: tuple[Still, ...] = ()  # the pose sheet the engine renders, on Pip
    specimen: Still | None = None  # the part alone, drawn by the engine: its picture on every card
    refused: str = ""  # why it has no specimen; a part has exactly one of the two


@dataclass(frozen=True)
class Video:
    slug: str
    title: str
    number: str
    lede: str
    highlights_html: tuple[str, ...]
    style: str  # "" when nothing was measured to tell
    source: str  # one of SOURCES
    measured: bool
    parts: tuple[str, ...]  # measured; empty and meaningless when measured is false
    format: str
    fps: float
    duration: float
    width: int
    height: int
    effects: int
    src: str | None = None
    poster: str | None = None
    lines: tuple[Line, ...] = ()


@dataclass(frozen=True)
class Style:
    slug: str
    name: str
    title: str
    text_html: str
    summary: str
    videos: tuple[str, ...]
    parts: tuple[str, ...]


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    measured: bool  # whether a usage report was given at all
    unmeasured: tuple[str, ...]  # episodes the report could not measure
    engine: tuple[str, ...]  # the topics of the engine inventory, for the search
    styles: tuple[Style, ...]
    videos: tuple[Video, ...]
    parts: tuple[Part, ...]


def _value(where: str, hint: Any, raw: object) -> Any:
    """``raw`` as a value of the type ``hint``, or :class:`CatalogError`. There is no coercion: an int is accepted
    for a float, as JSON does not tell them apart, and nothing else changes type."""
    origin = typing.get_origin(hint)
    if origin in (Union, types.UnionType):
        options = typing.get_args(hint)
        if raw is None and type(None) in options:
            return None
        return _value(where, next(o for o in options if o is not type(None)), raw)
    if origin is tuple:
        if not isinstance(raw, list):
            raise CatalogError(f"{where}: expected a list, got {type(raw).__name__}")
        item = typing.get_args(hint)[0]
        return tuple(_value(f"{where}[{i}]", item, x) for i, x in enumerate(raw))
    if is_dataclass(hint):
        return _parse(where, typing.cast(type, hint), raw)
    if hint is float:
        if type(raw) not in (int, float) or not math.isfinite(typing.cast(float, raw)):
            raise CatalogError(f"{where}: expected a finite number, got {raw!r}")
        return float(typing.cast(float, raw))
    if type(raw) is not hint:  # bool is not an int here
        raise CatalogError(f"{where}: expected {hint.__name__}, got {type(raw).__name__}")
    return raw


def _parse(where: str, cls: type[T], raw: object) -> T:
    if not isinstance(raw, dict):
        raise CatalogError(f"{where}: expected an object, got {type(raw).__name__}")
    hints = typing.get_type_hints(cls)
    known = fields(typing.cast(Any, cls))
    unknown = set(raw) - {f.name for f in known}
    if unknown:
        raise CatalogError(f"{where}: unknown fields {sorted(unknown)}")
    required = {f.name for f in known if f.default is MISSING}
    missing = required - set(raw)
    if missing:
        raise CatalogError(f"{where}: missing fields {sorted(missing)}")
    return cls(**{name: _value(f"{where}.{name}", hints[name], value) for name, value in raw.items()})


def _unique(where: str, names: list[str]) -> None:
    seen = set()
    for name in names:
        if name in seen:
            raise CatalogError(f"{where}: {name!r} appears twice")
        seen.add(name)


def _media(where: str, url: str) -> str:
    if not _MEDIA.fullmatch(url):
        raise CatalogError(f"{where}: {url!r} is not a media/<content-hash>.<ext> URL")
    return url


def stills_of(part: Part) -> list[Still]:
    own = [part.specimen] if part.specimen else []
    return own + [s for g in part.gallery for s in (g.still, *g.poses)] + list(part.sheet)


def media_of(catalog: Catalog) -> set[str]:
    """Every media URL the document references."""
    urls = {u for v in catalog.videos for u in (v.src, v.poster) if u}
    return urls | {s.src for p in catalog.parts for s in stills_of(p)}


def _check_video(v: Video, styles: set[str], parts: dict[str, Part]) -> None:
    where = f"video {v.slug!r}"
    if v.source not in SOURCES:
        raise CatalogError(f"{where}: source {v.source!r} is not one of {', '.join(SOURCES)}")
    if v.style and v.style not in styles:
        raise CatalogError(f"{where}: style {v.style!r} is not in the catalog")
    if v.duration < 0 or v.fps < 0 or v.width < 0 or v.height < 0 or v.effects < 0:
        raise CatalogError(f"{where}: a negative fact")
    if any(x.t < 0 for x in v.lines):
        raise CatalogError(f"{where}: a line before the start")
    if v.source == "library":
        if not v.src or not v.poster:
            raise CatalogError(f"{where}: a library video needs its src and poster")
        _media(where, v.src)
        _media(where, v.poster)
    elif v.src or (v.poster and v.source != "package"):
        raise CatalogError(f"{where}: a {v.source} video has no file on this site")
    elif v.source == "package":
        if not v.poster:
            raise CatalogError(f"{where}: a package video needs its poster")
        _media(where, v.poster)
    if not v.measured and v.parts:
        raise CatalogError(f"{where}: it was not measured, so it cannot claim parts")
    _unique(f"{where} parts", list(v.parts))
    for name in v.parts:
        if name not in parts:
            raise CatalogError(f"{where}: part {name!r} is not in the catalog")
        if v.slug not in parts[name].videos:
            raise CatalogError(f"{where}: part {name!r} does not list it back")


def _check_part(p: Part, styles: set[str], videos: dict[str, Video]) -> None:
    where = f"part {p.name!r}"
    if p.kind not in KINDS:
        raise CatalogError(f"{where}: kind {p.kind!r} is not one of {', '.join(KINDS)}")
    if p.style and p.style not in styles:
        raise CatalogError(f"{where}: style {p.style!r} is not in the catalog")
    if p.specimen and p.refused:
        raise CatalogError(f"{where}: both a specimen and a reason for having none")
    if not p.specimen and not p.refused:
        raise CatalogError(f"{where}: neither a specimen nor a reason for having none")
    _unique(f"{where} videos", list(p.videos))
    for slug in p.videos:
        if slug not in videos:
            raise CatalogError(f"{where}: video {slug!r} is not in the catalog")
        if p.name not in videos[slug].parts:
            raise CatalogError(f"{where}: video {slug!r} does not list it back")
    for s in stills_of(p):
        _media(where, s.src)
        if s.width <= 0 or s.height <= 0:
            raise CatalogError(f"{where}: a still of {s.width}x{s.height}")
        if s.video and s.video not in videos:
            raise CatalogError(f"{where}: still from {s.video!r}, which is not in the catalog")


def validate(catalog: Catalog) -> Catalog:
    """The constraints a schema cannot express; :class:`CatalogError` names the first one broken."""
    m = _SEMVER.fullmatch(catalog.schema_version)
    if m is None:
        raise CatalogError(f"schema_version {catalog.schema_version!r} is not major.minor.patch")
    if m[1] != SCHEMA_VERSION.split(".")[0]:
        raise CatalogError(f"schema_version {catalog.schema_version}: this reader knows {SCHEMA_VERSION}")
    _unique("styles", [s.slug for s in catalog.styles])
    _unique("videos", [v.slug for v in catalog.videos])
    _unique("parts", [p.name for p in catalog.parts])
    styles = {s.slug for s in catalog.styles}
    videos = {v.slug: v for v in catalog.videos}
    parts = {p.name: p for p in catalog.parts}
    for v in catalog.videos:
        _check_video(v, styles, parts)
    for p in catalog.parts:
        _check_part(p, styles, videos)
    for s in catalog.styles:
        if sorted(s.videos) != sorted(v.slug for v in catalog.videos if v.style == s.slug):
            raise CatalogError(f"style {s.slug!r}: its videos are not the videos of that style")
        if sorted(s.parts) != sorted(p.name for p in catalog.parts if p.style == s.slug):
            raise CatalogError(f"style {s.slug!r}: its parts are not the parts of that style")
    for slug in catalog.unmeasured:
        if slug not in videos:
            raise CatalogError(f"unmeasured episode {slug!r} is not in the catalog")
        if videos[slug].measured:
            raise CatalogError(f"episode {slug!r} is listed as unmeasured and marked measured")
    return catalog


def parse(doc: object, where: str = "catalog") -> Catalog:
    """A catalog document as typed, checked values."""
    return validate(_parse(where, Catalog, doc))


def dumps(catalog: Catalog) -> str:
    """The document as text, in a stable form: the same catalog gives the same bytes."""
    return json.dumps(asdict(catalog), ensure_ascii=False, separators=(",", ":"))


def load(path: Path) -> Catalog:
    """Read ``catalog.json`` and check that the media it references sit beside it."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"{path}: {exc}") from None
    catalog = parse(doc, str(path))
    root = Path(path).parent
    missing = sorted(u for u in media_of(catalog) if not (root / u).is_file())
    if missing:
        raise CatalogError(f"{path}: {len(missing)} media file(s) missing, the first {missing[0]}")
    return catalog
