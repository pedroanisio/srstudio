"""The catalog site, rebuilt from what is on disk: ``srstudio page``.

The site is ``index.html``, ``catalog.json`` and ``media/<content-hash>.<ext>``, served by ``srstudio serve``
(ADR 0046). ``index.html`` is the frozen *base* page, the catalog of the six original packages, as the shell of a small
client-side app: a navigation bar, the base page's sections shown by route, and a script that renders everything else
from ``catalog.json``. That document (:mod:`srstudio.catalog_data`) is generated here and never hand-maintained. It
holds one video per episode project that has a render, with its facts and lines; the six packages and any measured
episode without a render, marked as such; every registered style; and every registered part, with the stills the
notes curate, the videos ``srstudio usage`` measured and its version history (:mod:`srstudio.catalog_versions`).

Nothing about an episode is typed in here. Title, description, frame, fps and duration come from its ``.scene.xml``,
the lines from whichever script the project has (``dialogue.json``, ``timeline.json`` or ``narration.json``) and the
style from the measured usage. An optional *notes* file adds curated text (number, lede, highlights) per episode and
per style, a title per part, and the library's cast, locations, props and graphics: each item names the registered
parts it shows and a still cut from an episode render (a time and an optional crop box). When the notes curate that
gallery, every part a rendered library episode is registered with must be shown by an item, so a new episode cannot
leave the gallery behind.

A part's picture comes from its own definition, not from the notes or a reel: every registered part is drawn alone by
the engine (:mod:`srstudio.catalog_specimens`), so a part added to the registry shows in the next build, titled from
its registered summary (:func:`title_of`) until the notes title it (:func:`curated_titles`). A part that cannot stand
alone carries the reason, and one with neither stops the build by name. Each package's poster is likewise rendered from
its scene spec.

Videos are re-encoded for the web once per render (keyed by size and modification time). They, the stills, the pose
sheet, the app and everything the base page embedded are files with relative URLs, and neither the page nor the
document holds a data URI. Names follow the content, so a rebuild writes only what changed. Media are placed first,
then ``catalog.json``, and the index replaces the old one last, atomically, so a failed build leaves the previous site
working; only then are the files nothing references removed. Folders are mode 700 and files 600.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import html
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from . import catalog_data, catalog_server, catalog_specimens, catalog_versions, characters, checks, digest, registry
from .catalog_data import CatalogError, GalleryEntry, Line, Still
from .styles import STYLES
from .usage import Report

NOTES_SCHEMA = "1.2.0"
SCHEMAS = ("1.0.0", "1.1.0", NOTES_SCHEMA)  # 1.1.0 adds the optional gallery, 1.2.0 the optional part titles
SCRIPTS = ("dialogue.json", "timeline.json", "narration.json")


# -- notes ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EpisodeNote:
    number: str = ""
    lede: str = ""
    highlights: tuple[str, ...] = ()


@dataclass(frozen=True)
class StyleNote:
    title: str
    text: str


@dataclass(frozen=True)
class PartNote:
    title: str


@dataclass(frozen=True)
class Shot:
    """A still of an episode render: the frame at ``at`` seconds, cropped to ``box`` (x, y, w, h) when given."""

    episode: str
    at: float
    box: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class Pose:
    label: str
    shot: Shot


@dataclass(frozen=True)
class GalleryItem:
    section: str  # one of SECTIONS
    name: str
    parts: tuple[str, ...]  # the registered parts the item shows
    shot: Shot
    text: str
    voice: str = ""
    poses: tuple[Pose, ...] = ()  # cast only


SECTIONS = ("cast", "locations", "props", "graphics")


@dataclass(frozen=True)
class Notes:
    episodes: dict[str, EpisodeNote] = field(default_factory=dict)
    styles: dict[str, StyleNote] = field(default_factory=dict)
    gallery: tuple[GalleryItem, ...] | None = None  # None: the notes do not curate the gallery
    parts: dict[str, PartNote] = field(default_factory=dict)

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(self.episodes)


def _fields(where: str, obj: object, required: set[str], optional: set[str]) -> dict:
    if not isinstance(obj, dict):
        raise CatalogError(f"{where}: expected an object")
    unknown = set(obj) - required - optional
    if unknown:
        raise CatalogError(f"{where}: unknown fields {sorted(unknown)}")
    missing = required - set(obj)
    if missing:
        raise CatalogError(f"{where}: missing fields {sorted(missing)}")
    return obj


def _text(where: str, value: object) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"{where}: expected text, got {type(value).__name__}")
    return value


def load_notes(path: Path) -> Notes:
    """Curated text for the page. Unknown fields and wrong types are refused, not ignored."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"{path}: {exc}") from None
    top = _fields(str(path), doc, {"schema", "episodes", "styles"}, {"gallery", "parts"})
    if top["schema"] not in SCHEMAS:
        raise CatalogError(f"{path}: schema {top['schema']!r}, expected one of {', '.join(SCHEMAS)}")
    if "gallery" in top and top["schema"] == "1.0.0":
        raise CatalogError(f"{path}: a gallery needs schema 1.1.0 or later")
    if "parts" in top and top["schema"] != NOTES_SCHEMA:
        raise CatalogError(f"{path}: parts need schema {NOTES_SCHEMA}")
    episodes = {}
    for slug, raw in _fields(f"{path} episodes", top["episodes"], set(), set(top["episodes"])).items():
        where = f"{path} episodes.{slug}"
        e = _fields(where, raw, set(), {"number", "lede", "highlights"})
        highlights = e.get("highlights", [])
        if not isinstance(highlights, list):
            raise CatalogError(f"{where}.highlights: expected a list of text")
        episodes[slug] = EpisodeNote(
            number=_text(f"{where}.number", e.get("number", "")),
            lede=_text(f"{where}.lede", e.get("lede", "")),
            highlights=tuple(_text(f"{where}.highlights", h) for h in highlights),
        )
    styles = {}
    for slug, raw in _fields(f"{path} styles", top["styles"], set(), set(top["styles"])).items():
        s = _fields(f"{path} styles.{slug}", raw, {"title", "text"}, set())
        styles[slug] = StyleNote(_text(f"styles.{slug}.title", s["title"]), _text(f"styles.{slug}.text", s["text"]))
    gallery = None
    if "gallery" in top:
        if not isinstance(top["gallery"], list):
            raise CatalogError(f"{path} gallery: expected a list of items")
        gallery = tuple(_item(f"{path} gallery[{i}]", raw) for i, raw in enumerate(top["gallery"]))
    parts = {}
    for name, raw in _fields(f"{path} parts", top.get("parts", {}), set(), set(top.get("parts", {}))).items():
        where = f"{path} parts.{name}"
        title = _text(f"{where}.title", _fields(where, raw, {"title"}, set())["title"])
        if not title.strip():
            raise CatalogError(f"{where}.title: empty")
        parts[name] = PartNote(title)
    return Notes(episodes, styles, gallery, parts)


def _shot(where: str, raw: object) -> Shot:
    s = _fields(where, raw, {"episode", "at"}, {"box"})
    at = s["at"]
    if not checks.number(at) or at < 0:
        raise CatalogError(f"{where}.at: expected finite seconds >= 0, got {at!r}")
    box = s.get("box")
    if box is not None:
        ok = isinstance(box, list) and len(box) == 4 and all(type(v) is int and v >= 0 for v in box)
        if not ok or box[2] == 0 or box[3] == 0:
            raise CatalogError(f"{where}.box: expected [x, y, w, h] in whole pixels, w and h > 0, got {box!r}")
        box = tuple(box)
    return Shot(_text(f"{where}.episode", s["episode"]), float(at), box)


def _item(where: str, raw: object) -> GalleryItem:
    g = _fields(where, raw, {"section", "name", "parts", "shot", "text"}, {"voice", "poses"})
    if g["section"] not in SECTIONS:
        raise CatalogError(f"{where}.section: {g['section']!r} is not one of {', '.join(SECTIONS)}")
    name = _text(f"{where}.name", g["name"])
    if not name.strip():
        raise CatalogError(f"{where}.name: empty")
    parts = g["parts"]
    if not isinstance(parts, list) or not parts:
        raise CatalogError(f"{where}.parts: expected a non-empty list of part names")
    poses = g.get("poses", [])
    if not isinstance(poses, list) or (poses and g["section"] != "cast"):
        raise CatalogError(f"{where}.poses: expected a list, and only for the cast")
    return GalleryItem(
        section=g["section"],
        name=name,
        parts=tuple(_text(f"{where}.parts", x) for x in parts),
        shot=_shot(f"{where}.shot", g["shot"]),
        text=_text(f"{where}.text", g["text"]),
        voice=_text(f"{where}.voice", g.get("voice", "")),
        poses=tuple(
            Pose(_text(f"{where}.poses[{i}].label", p["label"]), _shot(f"{where}.poses[{i}].shot", p["shot"]))
            for i, p in ((i, _fields(f"{where}.poses[{i}]", p, {"label", "shot"}, set())) for i, p in enumerate(poses))
        ),
    )


# -- projects ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Card:
    slug: str
    title: str
    description: str
    style: str
    number: str
    lede: str
    highlights: tuple[str, ...]
    fmt: str
    fps: float
    duration: float
    lines: tuple[Line, ...]
    effects: int
    render: Path
    size: tuple[int, int] = (1080, 1920)  # the frame, in pixels


def plain(docstring: str) -> str:
    """A docstring's first line as a reader sees it: Sphinx roles and literals reduced to the name they mark."""
    return re.sub(r"``(.+?)``", r"\1", re.sub(r":[a-z]+:`[~.]*([^`]+)`", r"\1", docstring))


def _format(width: int, height: int) -> str:
    return "1:1" if width == height else ("9:16" if height > width else "16:9")


def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def lines_of(project: Path) -> tuple[list[Line], int]:
    """The timed lines and the number of sound effects, from the first script the project has."""
    for name in SCRIPTS:
        path = project / name
        if path.exists():
            break
    else:
        return [], 0
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if name == "dialogue.json":
            lines = [
                Line(float(p["start"]), str(p["role"]), str(p.get("voice_name", "")), str(p["text"]))
                for p in doc["phrases"]
            ]
            fx = [
                Line(float(e["start"]), "sfx", "", str(e["name"]).replace("-", " "), sfx=True)
                for e in doc.get("sound_effects", [])
            ]
            return sorted([*lines, *fx], key=lambda x: x.t), len(fx)
        if name == "timeline.json":
            lines = [
                Line(
                    float(x["start"]),
                    str(x["actor"]),
                    "" if x["actor"] == "sfx" else str(x.get("voice_name", "")),
                    str(x["text"]),
                    sfx=x["actor"] == "sfx",
                )
                for x in doc["items"]
            ]
            return lines, sum(1 for x in lines if x.sfx)
        voice = str(doc.get("voice", {}).get("name", "")).split(" - ")[0]
        return [Line(float(x["start"]), "narration", voice, str(x["text"])) for x in doc["items"]], 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise CatalogError(f"{path}: {type(exc).__name__} {exc}") from None


def style_of(slug: str, usage: Report | None) -> str:
    """The style most of the episode's measured parts belong to (a tie goes to the first by name; shared parts
    count for none), or "" when the episode was not measured."""
    if usage is None:
        return ""
    styles = {e.name: e.style for e in registry.entries()}
    counts = Counter(styles[name] for name in usage.episodes.get(slug, ()) if styles.get(name))
    return min(counts, key=lambda style: (-counts[style], style)) if counts else ""


def _scene(project: Path) -> Path | None:
    found = sorted(p for p in project.glob("*.xml") if p.name.endswith("scene.xml") and ".audio." not in p.name)
    return found[0] if found else None


def discover(episodes: Path, renders: Path, notes: Notes, usage: Report | None = None) -> list[Card]:
    """One card per project folder with a scene document and a ``renders/<slug>.mp4``: noted episodes first, in
    the notes' order, then the rest by name; each card's style comes from the parts ``usage`` measured."""
    cards = []
    for project in sorted(p for p in Path(episodes).iterdir() if p.is_dir()):
        slug, render, scene = project.name, Path(renders) / f"{project.name}.mp4", _scene(project)
        if scene is None or not render.exists():
            continue
        try:
            root = ET.parse(scene).getroot()
            spec = root.find("project")
            meta = root.find("metadata")
            if spec is None:
                raise ValueError("no <project>")
            w, h = int(spec.get("width", "")), int(spec.get("height", ""))
            fps, duration = float(spec.get("fps", "")), float(spec.get("duration", ""))
        except (OSError, ET.ParseError, ValueError) as exc:
            raise CatalogError(f"{slug}: {scene.name}: {exc}") from None
        title = (meta.get("title") if meta is not None else None) or slug
        description = (meta.get("description") if meta is not None else None) or ""
        note = notes.episodes.get(slug, EpisodeNote())
        lines, effects = lines_of(project)
        cards.append(
            Card(
                slug=slug,
                title=title,
                description=description,
                style=style_of(slug, usage),
                number=note.number,
                lede=note.lede or description,
                highlights=note.highlights,
                fmt=_format(w, h),
                fps=fps,
                duration=duration,
                lines=tuple(lines),
                effects=effects,
                render=render,
                size=(w, h),
            )
        )
    rank = {slug: i for i, slug in enumerate(notes.order)}
    return sorted(cards, key=lambda c: (rank.get(c.slug, len(rank)), c.slug))


# -- the document -----------------------------------------------------------------------------------------
def _episodes_of(entry: registry.Entry, usage: Report | None) -> list[str]:
    """The episodes a part appears in, as measured; none are claimed without a usage report."""
    return usage.used_by(entry.name) if usage is not None else []


def _registry_table(usage: Report | None = None) -> str:
    e = html.escape
    rows = sorted(registry.entries(), key=lambda x: (x.style or "~", x.kind, x.name))
    body = "".join(
        f"<tr><td><code>{e(x.name)}</code></td><td>{e(STYLES[x.style].name if x.style in STYLES else 'todos')}</td>"
        f"<td>{e(x.kind)}</td><td>{e(x.summary)}</td><td>{e(', '.join(_episodes_of(x, usage)) or '—')}</td></tr>"
        for x in rows
    )
    return (
        '<div class="tbl"><table class="lib-registry"><thead><tr><th>Peça</th><th>Estilo</th><th>Tipo</th>'
        f"<th>Resumo</th><th>Episódios</th></tr></thead><tbody>{body}</tbody></table></div>"
    )


def _keys(c: Card) -> set[str]:
    return {c.slug, c.number} - {""}


def check_gallery(gallery: Sequence[GalleryItem], cards: Sequence[Card], usage: Report) -> None:
    """Every item shows registered parts in a still that exists; every part a rendered library episode uses, as
    measured in ``usage``, is shown. :class:`CatalogError` names the first item or part that is not."""
    known = {x.name: x for x in registry.entries()}
    by_slug = {c.slug: c for c in cards}
    for g in gallery:
        unknown = [p for p in g.parts if p not in known]
        if unknown:
            raise CatalogError(f"gallery {g.name!r}: no registered part {unknown}")
        for label, s in [("shot", g.shot)] + [(f"pose {p.label!r}", p.shot) for p in g.poses]:
            where = f"gallery {g.name!r} {label}"
            card = by_slug.get(s.episode)
            if card is None:
                raise CatalogError(f"{where}: {s.episode!r} is not a rendered library episode")
            if s.at >= card.duration:
                raise CatalogError(f"{where}: at {s.at:g} s is past the end ({card.duration:g} s)")
            if s.box is not None:
                x, y, w, h = s.box
                if x + w > card.size[0] or y + h > card.size[1]:
                    raise CatalogError(f"{where}: box {list(s.box)} leaves the {card.size[0]}x{card.size[1]} frame")
    shown = {p for g in gallery for p in g.parts}
    library = set().union(*(_keys(c) for c in cards)) if cards else set()
    missing = [x.name for x in registry.entries() if library & set(_episodes_of(x, usage)) and x.name not in shown]
    if missing:
        raise CatalogError(f"the gallery shows no item for the registered part(s) {missing}")


@dataclass(frozen=True)
class Package:
    """An original package: the base page plays it as SVG, so it has facts here and no file."""

    slug: str
    title: str
    number: str
    lede: str
    fmt: str
    fps: float
    duration: float
    width: int
    height: int


_SCENES = re.compile(r'<script id="scenes-data" type="application/json">(.*?)</script>', re.DOTALL)
_PACKAGE_TEXT = re.compile(r"'([a-z-]+)':\{no:'(\d+)', pt:'([^']*)', desc:'((?:[^'\\]|\\.)*)'")
_ENGINE = re.compile(r"const ENGINE = \[(.*?)\n\];", re.DOTALL)


def packages_of(page: str) -> list[Package]:
    """The six packages, from the scene data the base page plays them with and its Portuguese titles."""
    m = _SCENES.search(page)
    if m is None:
        return []
    text = {slug: (no, pt, desc.replace("\\'", "'")) for slug, no, pt, desc in _PACKAGE_TEXT.findall(page)}
    try:
        out = []
        for scene in json.loads(m[1]):
            no, pt, desc = text.get(scene["id"], ("", scene["title"], scene["description"]))
            w, h = int(scene["width"]), int(scene["height"])
            out.append(
                Package(scene["id"], pt, no, desc, _format(w, h), float(scene["fps"]), float(scene["duration"]), w, h)
            )
    except (ValueError, KeyError, TypeError) as exc:
        raise CatalogError(f"the base page's scene data: {type(exc).__name__} {exc}") from None
    return out


def engine_topics(page: str) -> tuple[str, ...]:
    """The headings of the base page's engine inventory, for the search."""
    m = _ENGINE.search(page)
    return tuple(re.findall(r"\{h:'([^']+)'", m[1])) if m else ()


def _still(shot: Shot, cards: dict[str, Card], stills: Callable[[Shot], str], label: str = "") -> Still:
    w, h = shot.box[2:] if shot.box else cards[shot.episode].size
    return Still(src=stills(shot), width=w, height=h, label=label, video=shot.episode)


def _gallery_of(
    items: Sequence[GalleryItem], cards: dict[str, Card], stills: Callable[[Shot], str]
) -> dict[str, list[GalleryEntry]]:
    """The gallery items that show each part, in the notes' order."""
    shown: dict[str, list[GalleryEntry]] = defaultdict(list)
    for g in items:
        entry = GalleryEntry(
            name=g.name,
            note_html=g.text,
            voice=g.voice,
            still=_still(g.shot, cards, stills),
            poses=tuple(_still(p.shot, cards, stills, p.label) for p in g.poses),
        )
        for name in g.parts:
            shown[name].append(entry)
    return shown


def _video_of_card(c: Card, media: Callable[[Path], str], poster: Callable[[Path], str], usage: Report | None):
    measured = usage is not None and c.slug in usage.episodes
    return catalog_data.Video(
        slug=c.slug,
        title=c.title,
        number=c.number,
        lede=c.lede,
        highlights_html=c.highlights,
        style=c.style,
        source="library",
        measured=measured,
        parts=tuple(usage.episodes[c.slug]) if usage is not None and measured else (),
        format=c.fmt,
        fps=c.fps,
        duration=c.duration,
        width=c.size[0],
        height=c.size[1],
        effects=c.effects,
        src=media(c.render),
        poster=poster(c.render),
        lines=c.lines,
    )


def _video_elsewhere(
    slug: str, package: Package | None, usage: Report | None, poster: str | None
) -> catalog_data.Video:
    """A video with no render on the site: a package, with the poster of its spec, or a project usage knows of."""
    measured = usage is not None and slug in usage.episodes
    return catalog_data.Video(
        slug=slug,
        title=package.title if package else slug,
        number=package.number if package else "",
        lede=package.lede if package else "",
        highlights_html=(),
        style=style_of(slug, usage),
        source="package" if package else "no-render",
        measured=measured,
        parts=tuple(usage.episodes[slug]) if usage is not None and measured else (),
        format=package.fmt if package else "",
        fps=package.fps if package else 0.0,
        duration=package.duration if package else 0.0,
        width=package.width if package else 0,
        height=package.height if package else 0,
        effects=0,
        poster=poster,
    )


TITLE_LIMIT = 60
_REFERENCE = re.compile(r"[\s,]*\b(?:at|on|of|in|by|from|to|for|with)?\s*(?::[a-z]+:`[^`]*`|``[^`]*``)")  # to code
_CLAUSE = re.compile(r"(?<=\w{3})\.(?:\s|$)|[:;]\s|\s[—–]\s|\s\(")


def curated_titles(notes: Notes) -> dict[str, str]:
    """The title the notes give each part: its own entry, or the name of a gallery item that shows it alone.

    An item that shows several parts names a shot, and that says nothing about any one of them on its own."""
    titles: dict[str, str] = {}
    for item in notes.gallery or ():
        if len(item.parts) == 1:
            titles.setdefault(item.parts[0], item.name)
    return titles | {name: note.title for name, note in notes.parts.items()}


def check_titles(titles: dict[str, str]) -> None:
    """Refuse a title for an unregistered part, or one that two parts of a kind share, by name.

    A registered summary's title is left out on purpose: a part the notes do not know yet must still build."""
    kinds = {x.name: x.kind for x in registry.entries()}
    unknown = sorted(set(titles) - set(kinds))
    if unknown:
        raise CatalogError(f"the notes title unregistered parts: {', '.join(unknown)}")
    holders: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name, title in titles.items():
        holders[kinds[name], title].append(name)
    repeated = [f"{title!r} on {', '.join(sorted(names))}" for (_, title), names in holders.items() if len(names) > 1]
    if repeated:
        raise CatalogError(f"curated titles repeat within a kind: {'; '.join(sorted(repeated))}")


def title_of(entry: registry.Entry) -> str:
    """What a part with no curated title is called: the first clause of its registered summary, the only display text
    an entry offers. No name is invented, so a part the summary does not name reads as its description."""
    text = _REFERENCE.sub("", entry.summary).strip()
    if not text:
        raise CatalogError(f"{entry.kind} {entry.name} has no summary or docstring to title it with")
    title = _CLAUSE.split(text, maxsplit=1)[0].strip()
    if len(title) <= TITLE_LIMIT:
        return title
    if ", " in title and len(head := title.split(", ")[0]) <= TITLE_LIMIT:
        return head
    words = title[: TITLE_LIMIT + 1].rsplit(" ", 1)[0]
    return f"{words.rstrip(' ,')}…"


def assemble(
    cards: Sequence[Card],
    notes: Notes,
    *,
    media: Callable[[Path], str],
    poster: Callable[[Path], str],
    poses: Sequence[tuple[str, str]],
    pictures: Mapping[str, Still],
    refused: Mapping[str, str] | None = None,
    posters: Mapping[str, str] | None = None,
    stills: Callable[[Shot], str] | None = None,
    usage: Report | None = None,
    packages: Sequence[Package] = (),
    engine: Sequence[str] = (),
    histories: catalog_versions.Histories | None = None,
    pinned: bool = False,
) -> catalog_data.Catalog:
    """The site's document, checked; :class:`CatalogError` when a registered part has neither a picture nor a reason
    in ``refused``, when the notes curate a gallery that :func:`check_gallery` refuses, that has no ``usage`` to check
    its coverage against or no ``stills`` to show, or when ``usage`` names a part the registry no longer has."""
    known = {x.name: x for x in registry.entries()}
    refused = refused or {}
    posters = posters or {}
    unaccounted = sorted(set(known) - set(pictures) - set(refused))
    if unaccounted:
        raise CatalogError(f"registered parts with neither a specimen nor a typed reason: {unaccounted}")
    if usage is not None:
        stale = sorted({p for parts in usage.episodes.values() for p in parts} - set(known))
        if stale:
            raise CatalogError(f"the usage report names unregistered parts {stale}: run srstudio usage again")
    by_slug = {c.slug: c for c in cards}
    shown: dict[str, list[GalleryEntry]] = {}
    if notes.gallery is not None:
        if usage is None:
            raise CatalogError(
                "the notes curate a gallery, and its coverage check needs a usage report (srstudio usage; --usage)"
            )
        check_gallery(notes.gallery, cards, usage)
        if stills is None:
            raise CatalogError("the notes curate a gallery but no stills were given to show it")
        shown = _gallery_of(notes.gallery, by_slug, stills)
    videos = [_video_of_card(c, media, poster, usage) for c in cards]
    by_package = {p.slug: p for p in packages}
    elsewhere = [*by_package, *(usage.episodes if usage else ()), *(usage.unmeasured if usage else ())]
    for slug in dict.fromkeys(elsewhere):
        if slug not in by_slug:
            videos.append(_video_elsewhere(slug, by_package.get(slug), usage, posters.get(slug)))
    sheet = tuple(Still(src=uri, width=POSE_SIZE[0], height=POSE_SIZE[1], label=name) for name, uri in poses)
    if sheet and "pip" not in known:
        raise CatalogError("the pose sheet is Pip's, and no part is registered as pip")
    titles = curated_titles(notes)
    check_titles(titles)
    histories = histories or {}
    belongs = catalog_versions.owners(histories)
    parts = [
        catalog_data.Part(
            name=x.name,
            kind=x.kind,
            title=titles[x.name] if x.name in titles else title_of(x),
            style=x.style,
            summary=plain(x.summary),
            videos=tuple(_episodes_of(x, usage)),
            gallery=tuple(shown.get(x.name, ())),
            sheet=sheet if x.name == "pip" else (),
            specimen=pictures.get(x.name),
            refused=refused.get(x.name, ""),
            versions=histories.get(x.name, ()),
            version_of=belongs.get(x.name, ""),
        )
        for x in sorted(known.values(), key=lambda x: (x.kind, x.style or "~", x.name))
    ]
    styles = [
        catalog_data.Style(
            slug=s.slug,
            name=s.name,
            title=notes.styles[s.slug].title if s.slug in notes.styles else s.name,
            text_html=notes.styles[s.slug].text if s.slug in notes.styles else html.escape(s.summary),
            summary=s.summary,
            videos=tuple(v.slug for v in videos if v.style == s.slug),
            parts=tuple(p.name for p in parts if p.style == s.slug),
        )
        for s in STYLES.values()
    ]
    return catalog_data.validate(
        catalog_data.Catalog(
            schema_version=catalog_data.SCHEMA_VERSION,
            measured=usage is not None,
            unmeasured=tuple(usage.unmeasured) if usage else (),
            engine=tuple(engine),
            styles=tuple(styles),
            videos=tuple(videos),
            parts=tuple(parts),
            pinned=pinned,
        )
    )


# -- the page ---------------------------------------------------------------------------------------------
_ANCHORS = {
    "style": "</style>",
    "head": "</head>",
    "wrap": '<div class="wrap">',
    "styles": '\n      </div>\n    </div>\n    <div class="specs"',
    "spec": '<div class="spec"><b>95,7 s</b><span>6 episódios</span></div>',
    "app": "<footer>",
    "footer": "</footer>",
    "script": "(function(){\n'use strict';\nconst AUDIO_SRC",
    "script-end": "})();\n</script>\n\n</body>",
    "engine": "const ENGINE = [",
    "body": "</body>",
}

_NAV = """<nav id="nav" aria-label="Seções do catálogo">
  <a class="nav-home" href="#/">Catálogo</a>
  <input id="search" type="search" placeholder="Buscar por nome" aria-label="Buscar por nome" autocomplete="off">
  <div class="nav-links">
    <a href="#/">Visão geral</a>
    <span class="nav-label">Biblioteca</span>
    <a href="#/estilos">Estilos</a>
    <a href="#/videos">Vídeos</a>
    <a href="#/personagens">Personagens</a>
    <a href="#/locacoes">Locações</a>
    <a href="#/objetos">Objetos</a>
    <a href="#/graficos">Gráficos</a>
    <span class="nav-label">Referência</span>
    <a href="#/registro">Registro</a>
    <a href="#/pacotes">Pacotes</a>
    <a href="#/motor">Motor</a>
  </div>
</nav>
"""


def check_base(page: str) -> None:
    missing = [name for name, anchor in _ANCHORS.items() if anchor not in page]
    if not re.search(r'<p class="lede">Seis curtas reconstruídos.*?</p>', page, flags=re.S):
        missing.append("lede")
    if missing:
        raise CatalogError(f"the base page lost its anchor(s) {missing}; it is not the packages catalog")


def inject(page: str, cards: Sequence[Card], notes: Notes, *, stylesheet: str, script: str) -> str:
    """The base page as the app's shell: its hero brought up to date, the navigation and the app's host added, and
    its own script held back until a route needs it, since it builds six SVG players and every package still.
    :class:`CatalogError` when the base lost an anchor."""
    check_base(page)
    e = html.escape
    new_styles = [s for s in STYLES.values() if f'class="style-tag {s.slug}"' not in page]
    css = "".join(
        f".style-tag.{s.slug}{{ background:{s.palettes[0].background or s.palettes[0].shade}; "
        f"color:{s.palettes[0].ink} }}\n"
        for s in new_styles
    )
    page = page.replace(_ANCHORS["style"], css + _ANCHORS["style"], 1)
    page = page.replace(_ANCHORS["head"], f'<link rel="stylesheet" href="{stylesheet}">\n' + _ANCHORS["head"], 1)
    style_cards = "".join(
        f'\n        <div class="style-card"><span class="style-tag {s.slug}">{e(s.name)}</span>'
        f"<b>{e(notes.styles[s.slug].title if s.slug in notes.styles else s.name)}</b>"
        f"<span>{notes.styles[s.slug].text if s.slug in notes.styles else e(s.summary)}</span></div>"
        for s in new_styles
    )
    page = page.replace(_ANCHORS["styles"], style_cards + _ANCHORS["styles"], 1)
    names = ", ".join(f"<b>{e(s.name)}</b>" for s in STYLES.values())
    page = re.sub(
        r'<p class="lede">Seis curtas reconstruídos.*?</p>',
        lambda _m: (
            '<p class="lede">Seis curtas reconstruídos aqui a partir dos próprios arquivos de cena, com áudio, '
            f"e mais {len(cards)} episódios feitos depois com a biblioteca <code>srstudio</code>. Estilos nomeados: "
            f"{names}. Depois, o inventário do que o motor permite além deles.</p>"
        ),
        page,
        count=1,
        flags=re.S,
    )
    page = page.replace(
        _ANCHORS["spec"],
        '<div class="spec"><b>95,7 s</b><span>6 pacotes</span></div>\n'
        f'      <div class="spec"><b>{_num(sum(c.duration for c in cards))} s</b>'
        f"<span>{len(cards)} episódios novos</span></div>\n"
        f'      <div class="spec"><b>{len(STYLES)}</b><span>estilos nomeados</span></div>\n'
        f'      <div class="spec"><b>{len(registry.entries())}</b><span>peças registradas</span></div>',
        1,
    )
    page = page.replace(_ANCHORS["wrap"], _NAV + '<div class="wrap" id="base">', 1)
    page = page.replace(
        _ANCHORS["app"],
        '<main id="app" class="on"><noscript>Este catálogo precisa de JavaScript.</noscript></main>\n'
        + _ANCHORS["app"],
        1,
    )
    page = page.replace(
        _ANCHORS["footer"],
        "  <p>Episódios da biblioteca: projetos em <code>generated/episodes/</code> e renders em "
        "<code>generated/renders/</code>; site gerado por <code>srstudio page</code>.</p>\n" + _ANCHORS["footer"],
        1,
    )
    page = page.replace(_ANCHORS["script"], "window.srstudioBase = " + _ANCHORS["script"], 1)
    page = page.replace(_ANCHORS["script-end"], f'}});\n</script>\n<script src="{script}" defer></script>\n</body>', 1)
    return page


# -- media and the build ----------------------------------------------------------------------------------
INDEX_LIMIT = 1 << 20  # bytes (the real page is 0.63 MB); the heavy things are files, so past this one is embedded
_EXTENSIONS = {"audio/mpeg": ".mp3", "font/ttf": ".ttf", "image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4"}
_BASE64_URI = re.compile(r"\bdata:([a-z0-9.+-]+/[a-z0-9.+-]+);base64,([A-Za-z0-9+/]*={0,2})", re.IGNORECASE)
_ANY_URI = re.compile(r"\bdata:(?:[a-z0-9.+-]+/[a-z0-9.+-]+)?[;,][^\s\"'<>)]{0,40}", re.IGNORECASE)


def _place(source: Path, target: Path) -> None:
    """``source`` at ``target``, whole or not at all, mode 600: hard-linked where it can be, so the site costs no
    second copy, and copied where it cannot: another device, or a mode a link would have to change on the source."""
    tmp = target.with_name(f".{target.name}.{os.getpid()}")
    tmp.unlink(missing_ok=True)
    try:
        if stat.S_IMODE(source.stat().st_mode) != 0o600:
            shutil.copyfile(source, tmp)
        else:
            try:
                os.link(source, tmp)
            except OSError:
                shutil.copyfile(source, tmp)
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


class MediaStore:
    """The ``media/`` folder of a site: each file named by its content, so what is already there is not written
    again. A file is hard-linked from the cache where it can be, so the site costs no second copy of the videos, and
    copied where it cannot: another device, or a mode that is not the site's 600, which a link would have to change
    on the cached file itself."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.kept: set[str] = set()
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)

    def _keep(self, name: str) -> str:
        self.kept.add(name)
        return f"media/{name}"

    def add(self, source: Path) -> str:
        """The relative URL of ``source``, placed in the folder when it is not there yet."""
        name = digest.sha256(source)[:32] + source.suffix.lower()
        target = self.folder / name
        if not target.exists() or target.stat().st_size != source.stat().st_size:
            _place(source, target)
        return self._keep(name)

    def add_bytes(self, data: bytes, suffix: str) -> str:
        name = hashlib.sha256(data).hexdigest()[:32] + suffix
        target = self.folder / name
        if not target.exists() or target.stat().st_size != len(data):
            fd, tmp = tempfile.mkstemp(dir=self.folder, prefix=f".{name}.")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                os.chmod(tmp, 0o600)
                os.replace(tmp, target)
            finally:
                Path(tmp).unlink(missing_ok=True)
        return self._keep(name)

    def prune(self) -> None:
        """Remove every file nothing referenced in this build, and what a killed build left behind."""
        for path in self.folder.iterdir():
            if path.is_file() and path.name not in self.kept:
                path.unlink()


class Proofs:
    """The proofs a site links, which live outside it, under ``root``. A browser will not follow a ``file:`` link from
    a served page, so a proof has to be in the site. A single file is a media file. A proof page reads the files beside
    it, some named only by its script, so it comes with its folder, in ``proofs/<hash of the folder>/``."""

    def __init__(self, root: Path, folder: Path, add: Callable[[Path], str]) -> None:
        self.root = Path(root).resolve()
        self.folder = folder
        self.add = add
        self.kept: set[str] = set()
        self.urls: dict[str, str] = {}
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)

    def url(self, pointer: str) -> str:
        """The URL of the proof at ``pointer``, or "" when no such file is under the root on this machine."""
        if pointer not in self.urls:
            source = (self.root / pointer).resolve()
            if not (source.is_relative_to(self.root) and source.is_file()):
                self.urls[pointer] = ""
            elif source.suffix.lower() == ".html":
                self.urls[pointer] = self._page(source)
            else:
                self.urls[pointer] = self.add(source)
        return self.urls[pointer]

    def _page(self, page: Path) -> str:
        key = hashlib.sha256(str(page.parent.relative_to(self.root)).encode()).hexdigest()[:16]
        target = self.folder / key
        target.mkdir(exist_ok=True)
        os.chmod(target, 0o700)
        wanted = [
            f
            for f in page.parent.iterdir()
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in catalog_server.TYPES
        ]
        for f in wanted:
            there = target / f.name
            st = f.stat()
            if not there.exists() or there.stat().st_size != st.st_size or there.stat().st_mtime_ns < st.st_mtime_ns:
                _place(f, there)
        names = {f.name for f in wanted}
        for old in target.iterdir():
            if old.name not in names:
                old.unlink()
        self.kept.add(key)
        return f"proofs/{key}/{page.name}"

    def prune(self) -> None:
        """Remove every proof folder nothing linked in this build."""
        for path in self.folder.iterdir():
            if path.name not in self.kept:
                shutil.rmtree(path)


def _run(args: Sequence[str]) -> None:
    try:
        subprocess.run(list(args), check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        err = getattr(exc, "stderr", b"") or b""
        raise CatalogError(f"{Path(args[0]).name} failed: {exc} {err.decode(errors='replace')[-400:]}") from None


def _cache(out: Path, args: Sequence[str]) -> None:
    """Run ``args`` with a hidden partial file beside ``out`` as their last argument, and move it onto ``out`` only
    once the run succeeded: a failed or killed encode leaves nothing that a later run would take as cached."""
    part = out.with_name(f".{out.stem}.part{out.suffix}")  # the same extension: the tools read the format from it
    try:
        _run([*args, str(part)])
        if part.exists():
            part.replace(out)
    finally:
        part.unlink(missing_ok=True)


def web_video(render: Path, cache: Path) -> tuple[Path, Path]:
    """A 540-wide H.264 copy (720 when wider than tall) and a poster frame of ``render``, made once per render
    version."""
    st = render.stat()
    stem = cache / "video" / f"{render.stem}-{st.st_size}-{st.st_mtime_ns}"
    video, poster = stem.with_suffix(".mp4"), stem.with_suffix(".jpg")
    if not video.exists():
        video.parent.mkdir(parents=True, exist_ok=True)
        scale = ["-vf", "scale='if(gt(iw,ih),720,540)':-2"]
        _cache(video, ["ffmpeg", "-v", "error", "-y", "-i", str(render), *scale, "-c:v", "libx264", "-crf", "27",
                       "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a",
                       "96k"])  # fmt: skip
    if not poster.exists():
        _cache(poster, ["ffmpeg", "-v", "error", "-y", "-i", str(render), "-frames:v", "1", "-vf",
                        "select=gte(t\\,1.2)+eq(n\\,0),scale='if(gt(iw,ih),720,540)':-2", "-q:v", "4"])  # fmt: skip
    return video, poster


def still(render: Path, shot: Shot, cache: Path) -> Path:
    """The frame of ``render`` at ``shot.at``, cropped to ``shot.box`` and at most 480 wide; cut once per render
    version, time and box."""
    st = render.stat()
    box = "x".join(map(str, shot.box)) if shot.box else "full"
    out = cache / "stills" / f"{render.stem}-{st.st_size}-{st.st_mtime_ns}-{shot.at:.3f}-{box}.jpg"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        crop = "crop={2}:{3}:{0}:{1},".format(*shot.box) if shot.box else ""
        _cache(out, ["ffmpeg", "-v", "error", "-y", "-ss", f"{shot.at:.3f}", "-i", str(render), "-frames:v", "1",
                     "-vf", f"{crop}scale='min(iw,480)':-2", "-q:v", "3"])  # fmt: skip
        if not out.exists():
            raise CatalogError(f"{render.name}: no frame at {shot.at:g} s")
    return out


POSE_SIZE = (300, 320)


def pose_sheet(engine: Path, cache: Path) -> list[tuple[str, Path]]:
    """One PNG per pose in :data:`blob.POSES`, rendered by the engine; re-rendered only when the poses change."""
    from sr_core.scene import Scene

    from . import blob
    from .canvas import WARM, Canvas

    names = list(blob.POSES)
    key = hashlib.sha256(repr([blob.POSES[n] for n in names]).encode()).hexdigest()[:16]
    folder = cache / f"poses-{key}"
    pngs = [(n, folder / f"pose-{n}.png") for n in names]
    if all(p.exists() for _, p in pngs):
        return pngs
    folder.mkdir(parents=True, exist_ok=True)
    scene = Scene(version="auto")
    scene.add_project(width=POSE_SIZE[0], height=POSE_SIZE[1], fps="1", duration=len(names), background=WARM.background)
    cv = Canvas(scene, WARM)
    seated = {"sit", "type-a", "type-b", "nod"}
    happy = ("cheer", "wave", "groove")
    cues = [
        blob.Cue(
            i,
            n,
            x=(150 + (20 if n in seated else 0)) / 0.45,
            y=(280 if n not in seated else 235) / 0.45,
            eyes="happy" if n.startswith(happy) else "look",
            mouth="grin" if n.startswith(happy) else "smile",
        )
        for i, n in enumerate(names)
    ]
    blob.pip(cv, cv.comp, cues, end=len(names), scale=0.45, shadow=True)
    doc = folder / "poses.scene.xml"
    doc.write_bytes(scene.to_bytes())
    for i, (_, png) in enumerate(pngs):
        _cache(png.resolve(), [str(engine), "render", str(doc), "-f", str(i), "-o"])
    return pngs


REFUSAL_TEXT = {
    catalog_specimens.Reason.OVERLAY: "Só existe sobre uma cena: é uma camada, sem desenho próprio.",
    catalog_specimens.Reason.MOTION: "É um movimento aplicado a outra peça, sem desenho próprio.",
    catalog_specimens.Reason.WORN: "Só existe vestido em um personagem.",
    catalog_specimens.Reason.CHARACTER_SHOT: "O plano já traz um personagem: não existe vazio.",
    catalog_specimens.Reason.PLACEHOLDER: "Só desenha com os traços de um projeto; sozinho, não há personagem.",
}


@dataclass(frozen=True)
class Pictures:
    """The cards' pictures, in the site: what a build hands :func:`assemble`, and the counts it reports."""

    stills: dict[str, Still]
    refused: dict[str, str]
    made: int


def pictures_of(engine: Path, cache: Path, episodes: Path, add: Callable[[Path], str]) -> Pictures:
    """Every registered part drawn alone, each file placed by ``add``. A part the library cannot draw stops the build,
    by name."""
    try:
        shelf = catalog_specimens.render_all(engine, cache, episodes)
    except catalog_specimens.SpecimenRenderError as exc:
        raise CatalogError(str(exc)) from None
    return Pictures(
        {n: Still(src=add(s.png), width=s.width, height=s.height) for n, s in shelf.done.items()},
        {n: REFUSAL_TEXT[why.reason] for n, why in shelf.refused.items()},
        shelf.made,
    )


def posters_of(
    slugs: Sequence[str], folder: Path, engine: Path, cache: Path, add: Callable[[Path], str]
) -> dict[str, str]:
    """One poster per package, rendered from its spec. A package that has none stops the build, by name."""
    try:
        return {slug: add(catalog_specimens.poster(folder, slug, engine, cache)) for slug in slugs}
    except catalog_specimens.SpecimenRenderError as exc:
        raise CatalogError(str(exc)) from None


def embedded(page: str) -> list[str]:
    """Every data URI in ``page``, of any type or encoding."""
    return _ANY_URI.findall(page)


def require_no_embedded(page: str) -> None:
    found = embedded(page)
    if found:
        raise CatalogError(f"the page still holds {len(found)} data URI(s), the first {found[0]!r}")


def extract_embedded(page: str, store: MediaStore) -> str:
    """``page`` with every base64 data URI moved into ``store``. A URL in CSS or a script's string resolves against
    the document, so the text around the URI needs no change."""

    def moved(m: re.Match[str]) -> str:
        kind = m[1].lower()
        if kind not in _EXTENSIONS:
            raise CatalogError(f"the base page embeds {kind}, which has no media extension")
        try:
            return store.add_bytes(base64.b64decode(m[2], validate=True), _EXTENSIONS[kind])
        except binascii.Error as exc:
            raise CatalogError(f"the base page embeds bad base64 for {kind}: {exc}") from None

    return _BASE64_URI.sub(moved, page)


def _write_text(path: Path, text: str) -> None:
    """Replace ``path`` in one step: a reader sees the old file or the new one, never part of it."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


@dataclass(frozen=True)
class Built:
    cards: list[Card]
    pictures: Pictures


def build(
    *,
    base: Path,
    episodes: Path,
    renders: Path,
    site: Path,
    cache: Path,
    engine: Path,
    packages: Path,
    notes: Notes | None = None,
    usage: Report | None = None,
    pins: catalog_versions.Pins | None = None,
    table: Mapping[str, characters.Character] | None = None,
    proof_root: Path = Path(),
) -> Built:
    """Write the site to ``site`` (files 600, folders 700) and say what it holds: media first, then ``catalog.json``,
    ``index.html`` last, and only then the removal of media nothing references. A failure at any step leaves the
    previous site working. ``pins`` is what the releases pin, None when they were not read. ``table`` is the versions
    record, by default the one this srstudio ships, and the proofs it names are looked up under ``proof_root``."""
    notes = notes or Notes()
    try:
        page = Path(base).read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"base page: {exc}") from None
    check_base(page)
    cards = discover(episodes, renders, notes, usage)
    old = os.umask(0o077)
    try:
        cache.mkdir(parents=True, exist_ok=True)
        web = {c.render: web_video(c.render, cache) for c in cards}
        site.mkdir(parents=True, exist_ok=True)
        os.chmod(site, 0o700)
        store = MediaStore(site / "media")
        renders_of = {c.slug: c.render for c in cards}
        originals = packages_of(page)
        shown = pictures_of(Path(engine), cache, episodes, store.add)
        proofs = Proofs(proof_root, site / "proofs", store.add)
        histories = catalog_versions.history(
            characters.load() if table is None else table, {x.name for x in registry.entries()}, pins, proofs.url
        )
        missing = [p.slug for p in originals if p.slug not in renders_of]
        catalog = assemble(
            cards,
            notes,
            media=lambda r: store.add(web[r][0]),
            poster=lambda r: store.add(web[r][1]),
            poses=[(n, store.add(p)) for n, p in pose_sheet(Path(engine), cache)],
            pictures=shown.stills,
            refused=shown.refused,
            posters=posters_of(missing, Path(packages), Path(engine), cache, store.add),
            stills=lambda s: store.add(still(renders_of[s.episode], s, cache)),
            usage=usage,
            packages=originals,
            engine=engine_topics(page),
            histories=histories,
            pinned=pins is not None,
        )
        document = catalog_data.dumps(catalog)
        catalog_data.parse(json.loads(document))  # what is written is what the reader accepts
        assets = files("srstudio") / "assets" / "catalog"
        result = inject(
            extract_embedded(page, store),
            cards,
            notes,
            stylesheet=store.add_bytes((assets / "app.css").read_bytes(), ".css"),
            script=store.add_bytes((assets / "app.js").read_bytes(), ".js"),
        )
        require_no_embedded(document)
        require_no_embedded(result)
        size = len(result.encode("utf-8"))
        if size > INDEX_LIMIT:
            raise CatalogError(f"index.html is {size} bytes, past the bound of {INDEX_LIMIT}")
        _write_text(site / "catalog.json", document)
        _write_text(site / "index.html", result)
        store.prune()
        proofs.prune()
    except OSError as exc:
        raise CatalogError(f"site {site}: {exc}") from None
    finally:
        os.umask(old)
    return Built(cards, shown)
