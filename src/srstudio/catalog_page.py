"""The catalog page, rebuilt from what is on disk: ``srstudio page``.

The page starts from a frozen *base*, the self-contained catalog of the six original packages, and adds the
library's own part to it: one card per episode project that has a render (its video, facts and a line list that
seeks the video), a card for every registered style the base does not show yet, Pip's pose sheet rendered by the
engine and the whole parts registry. Nothing about an episode is typed in here. Title, description, frame, fps and
duration come from its ``.scene.xml``, the lines from whichever script the project has (``dialogue.json``,
``timeline.json`` or ``narration.json``) and the style from the registry. An optional *notes* file adds curated text
(number, lede, highlights) per episode and per style, and the library's cast, locations, props and graphics: each
item names the registered parts it shows and a still cut from an episode render (a time and an optional crop box).
When the notes curate that gallery, every part a rendered library episode is registered with must be shown by an
item, so a new episode cannot leave the gallery behind.

Videos are re-encoded for the web once per render (keyed by size and modification time) and embedded with the pose
sheet as data URIs, so the page is one file that opens offline. It is written atomically with mode 600.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from . import checks, registry
from .errors import SrstudioError
from .styles import STYLES
from .usage import Report

NOTES_SCHEMA = "1.1.0"
SCHEMAS = ("1.0.0", NOTES_SCHEMA)  # 1.1.0 adds the optional gallery
SCRIPTS = ("dialogue.json", "timeline.json", "narration.json")


class CatalogError(SrstudioError):
    """A notes file, project, base page or media step the page cannot be built from."""


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


# section: (the base page's host div, the card class, its image class)
SECTIONS = {
    "cast": ("cast", "char", "char-main"),
    "locations": ("locs", "loc", "loc-img"),
    "props": ("props", "prop", "prop-img"),
    "graphics": ("graphics", "prop", "prop-img"),
}


@dataclass(frozen=True)
class Notes:
    episodes: dict[str, EpisodeNote] = field(default_factory=dict)
    styles: dict[str, StyleNote] = field(default_factory=dict)
    gallery: tuple[GalleryItem, ...] | None = None  # None: the notes do not curate the gallery

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
    top = _fields(str(path), doc, {"schema", "episodes", "styles"}, {"gallery"})
    if top["schema"] not in SCHEMAS:
        raise CatalogError(f"{path}: schema {top['schema']!r}, expected one of {', '.join(SCHEMAS)}")
    if "gallery" in top and top["schema"] == "1.0.0":
        raise CatalogError(f"{path}: a gallery needs schema {NOTES_SCHEMA}")
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
    return Notes(episodes, styles, gallery)


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
class Line:
    t: float
    who: str
    voice: str
    text: str
    sfx: bool = False


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
                fmt="1:1" if w == h else ("9:16" if h > w else "16:9"),
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


# -- the page ---------------------------------------------------------------------------------------------
def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def _card(c: Card, media: Callable[[Path], str], poster: Callable[[Path], str] | None) -> str:
    e = html.escape
    spoken = [x for x in c.lines if not x.sfx]
    voices = ", ".join(sorted({x.voice for x in c.lines if x.voice})) or "—"
    facts = [
        (_num(c.duration) + " s", "duração"),
        (c.fmt, "formato"),
        (f"{c.fps:g} fps", "quadros"),
        (str(len(spoken)), "falas"),
        (str(c.effects), "efeitos"),
        (voices, "vozes"),
    ]
    rows = "".join(
        f'<button class="line" data-t="{x.t:.3f}"><span class="t">{_clock(x.t)}</span>'
        f'<span class="who">{e(x.who)}<small>{e(x.voice)}</small></span>'
        f'<span class="txt">{f"<span class=sfx>{e(x.text)}</span>" if x.sfx else e(x.text)}</span></button>'
        for x in c.lines
    )
    tag = f'<span class="style-tag {c.style}">{e(STYLES[c.style].name)}</span>' if c.style in STYLES else ""
    poster_attr = f' poster="{poster(c.render)}"' if poster else ""
    return (
        f'\n<article class="ep" id="lib-{e(c.slug)}">'
        f'<div class="ep-head"><div class="ep-no">{e(c.number or "·")}</div><div><h3>{e(c.title)}{tag}</h3>'
        f"<p>{e(c.lede)}</p></div></div>"
        f'<div class="ep-grid"><div><div class="phone{" sq" if c.fmt == "1:1" else ""}">'
        f'<video controls playsinline preload="metadata"{poster_attr} src="{media(c.render)}" '
        f'aria-label="{e(c.title)}"></video></div></div>'
        f'<div class="ep-info"><div class="facts">'
        + "".join(f'<div class="fact"><b>{e(v)}</b><span>{k}</span></div>' for v, k in facts)
        + "</div>"
        + (f'<ul class="hl">{"".join(f"<li>{h}</li>" for h in c.highlights)}</ul>' if c.highlights else "")
        + f'<div class="dialog lib-dialog">{rows}</div></div></div></article>'
    )


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


USAGE_KINDS = {"character": "Personagens", "location": "Locações", "prop": "Props"}


def _usage_lists(usage: Report) -> str:
    """Every character, location and prop: the used ones with the episodes that use them, then the unused ones."""
    e = html.escape
    blocks = []
    for kind, title in USAGE_KINDS.items():
        parts = sorted(registry.entries(kind), key=lambda x: (x.style or "~", x.name))
        used = [(x, usage.used_by(x.name)) for x in parts if usage.used_by(x.name)]
        unused = [x for x in parts if not usage.used_by(x.name)]
        used_html = "".join(f"<li><code>{e(x.name)}</code> <small>{e(', '.join(eps))}</small></li>" for x, eps in used)
        unused_html = "".join(f"<li><code>{e(x.name)}</code> <small>{e(x.summary)}</small></li>" for x in unused)
        blocks.append(
            f'<div class="lib-usage-kind" id="usage-{kind}"><h3>{title}</h3>'
            f"<p><b>{len(used)}</b> usados · <b>{len(unused)}</b> não usados</p>"
            f"<ul>{used_html}</ul><p><b>Não usados</b></p><ul>{unused_html or '<li>nenhum</li>'}</ul></div>"
        )
    measured = ", ".join(e(slug) for slug in usage.episodes)
    unmeasured = f" Sem script, não medidos: {e(', '.join(usage.unmeasured))}." if usage.unmeasured else ""
    return (
        '<div class="sub">Peças usadas e não usadas</div><div class="lib-usage" id="lib-usage">'
        f"<p>Medido por <code>srstudio usage</code>, que reconstrói cada episódio e registra as peças chamadas: "
        f"{measured}.{unmeasured}</p>" + "".join(blocks) + "</div>"
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


def _gallery(
    items: Sequence[GalleryItem], cards: Sequence[Card], stills: Callable[[Shot], str], usage: Report | None = None
) -> dict[str, str]:
    """The cards of each section, in the base page's markup."""
    e = html.escape
    by_slug = {c.slug: c for c in cards}
    sizes: dict[str, str] = {k: "" for k in SECTIONS}
    for g in items:
        parts = [x for x in registry.entries() if x.name in g.parts]
        shown = {g.shot.episode, *(p.shot.episode for p in g.poses)}
        chips = "".join(
            f'<span class="chip on">{e(c.number or c.slug)}</span>'
            for c in cards
            if c.slug in shown or any(_keys(c) & set(_episodes_of(x, usage)) for x in parts)
        )
        img = f'<img src="{stills(g.shot)}" alt="{e(g.name)}" loading="lazy">'
        _, card, frame = SECTIONS[g.section]
        if g.section == "cast":
            voice = f"<span>voz {e(g.voice)} (ElevenLabs)</span><span>·</span>" if g.voice else ""
            poses = "".join(
                f'<div class="pose"><div class="pose-img"><img src="{stills(p.shot)}" alt="{e(g.name)}, '
                f'{e(p.label)}" loading="lazy"></div><small>{e(p.label)}</small></div>'
                for p in g.poses
            )
            sizes[g.section] += (
                f'<div class="{card}"><div class="{frame}">{img}</div><h3>{e(g.name)}</h3>'
                f'<div class="char-meta">{voice}{chips}</div><p class="note">{g.text}</p>'
                + (f'<div class="poses">{poses}</div>' if poses else "")
                + "</div>"
            )
            continue
        w, h = g.shot.box[2:] if g.shot.box else by_slug[g.shot.episode].size
        title = f"<h3>{e(g.name)}</h3>" if g.section == "locations" else f"<b>{e(g.name)}</b>"
        sizes[g.section] += (
            f'<div class="{card}"><div class="{frame}" style="aspect-ratio:{w}/{h}">{img}</div>{title}'
            f'<div class="char-meta">{chips}</div><p>{g.text}</p></div>'
        )
    return sizes


_CSS = """
.phone video{ width:100%; height:100%; display:block; border-radius:11px; object-fit:contain; background:#000 }
.phone.sq{ aspect-ratio:1/1 }
.lib-dialog{ max-height:420px; overflow-y:auto; padding-right:4px }
.lib-poses{ grid-template-columns:repeat(auto-fill,minmax(96px,1fr)) }
.lib-poses .pose-img{ aspect-ratio:15/16 }
.lib-poses img{ width:100%; height:100%; display:block; object-fit:cover }
.lib-gal{ margin-top:14px }
.lib-gal .loc,.lib-gal .prop{ align-content:start }
.lib-gal img{ width:100%; height:100%; display:block; object-fit:cover }
.lib-usage{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)) }
.lib-usage > p{ grid-column:1/-1 }
.lib-usage ul{ margin:6px 0 10px; padding-left:18px }
.lib-usage li{ margin:2px 0; overflow-wrap:anywhere }
"""

_JS = """
<script>
(function(){
  'use strict';
  document.querySelectorAll('#biblioteca .ep').forEach(function(card){
    var video = card.querySelector('video');
    var lines = Array.prototype.slice.call(card.querySelectorAll('.line'));
    lines.forEach(function(b){
      b.addEventListener('click', function(){
        video.currentTime = parseFloat(b.dataset.t); video.play().catch(function(){});
      });
    });
    video.addEventListener('timeupdate', function(){
      var now = video.currentTime, active = null;
      lines.forEach(function(b){ if (!b.querySelector('.sfx') && parseFloat(b.dataset.t) <= now + 0.05) active = b; });
      lines.forEach(function(b){ b.classList.toggle('active', b === active); });
    });
  });
})();
</script>
"""

_ANCHORS = {
    "style": "</style>",
    "styles": '\n      </div>\n    </div>\n    <div class="specs"',
    "spec": '<div class="spec"><b>95,7 s</b><span>6 episódios</span></div>',
    "section": '\n<section id="elenco">',
    "elenco": "Tudo que aparece nos seis vídeos,",
    **{
        f"host-{k}": f'<div class="{"props" if k == "graphics" else k}" id="{k}"></div>'
        for k in ("cast", "locs", "props", "graphics")
    },
    "footer": "</footer>",
    "body": "</body>",
}


def check_base(page: str) -> None:
    missing = [name for name, anchor in _ANCHORS.items() if anchor not in page]
    if not re.search(r'<p class="lede">Seis curtas reconstruídos.*?</p>', page, flags=re.S):
        missing.append("lede")
    if missing:
        raise CatalogError(f"the base page lost its anchor(s) {missing}; it is not the packages catalog")


def inject(
    page: str,
    cards: Sequence[Card],
    notes: Notes,
    *,
    media: Callable[[Path], str],
    poses: Sequence[tuple[str, str]],
    poster: Callable[[Path], str] | None = None,
    stills: Callable[[Shot], str] | None = None,
    usage: Report | None = None,
) -> str:
    """The base page with the library's part added; :class:`CatalogError` when the base lost an anchor, or when
    the notes curate a gallery that :func:`check_gallery` refuses, that has no ``usage`` to check its coverage
    against or no ``stills`` to show."""
    check_base(page)
    if notes.gallery is not None:
        if usage is None:
            raise CatalogError(
                "the notes curate a gallery, and its coverage check needs a usage report (srstudio usage; --usage)"
            )
        check_gallery(notes.gallery, cards, usage)
        if stills is None:
            raise CatalogError("the notes curate a gallery but no stills were given to show it")
        for key, cards_html in _gallery(notes.gallery, cards, stills, usage).items():
            host = SECTIONS[key][0]
            div = f'<div class="{"props" if host == "graphics" else host} lib-gal" id="lib-{host}">{cards_html}</div>'
            anchor = _ANCHORS[f"host-{host}"]
            page = page.replace(anchor, anchor + "\n  " + div, 1)
        page = page.replace(
            _ANCHORS["elenco"],
            f"Tudo que aparece nos seis vídeos originais e nos {len(cards)} episódios da biblioteca,",
            1,
        )
    e = html.escape
    page = re.sub(
        r'<div class="eyebrow">Parte (\d+)</div>',
        lambda m: f'<div class="eyebrow">Parte {int(m[1]) + 1 if int(m[1]) >= 2 else m[1]}</div>',
        page,
    )
    new_styles = [s for s in STYLES.values() if f'class="style-tag {s.slug}"' not in page]
    css = _CSS + "".join(
        f".style-tag.{s.slug}{{ background:{s.palettes[0].background or s.palettes[0].shade}; "
        f"color:{s.palettes[0].ink} }}\n"
        for s in new_styles
    )
    page = page.replace(_ANCHORS["style"], css + _ANCHORS["style"], 1)
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
    pose_tiles = "".join(
        f'<div class="pose"><div class="pose-img"><img src="{uri}" alt="Pip, pose {e(name)}" loading="lazy"></div>'
        f"<small>{e(name)}</small></div>"
        for name, uri in poses
    )
    section = (
        '\n<section id="biblioteca"><div class="sec-head"><div class="eyebrow">Parte 2</div>'
        "<h2>Os episódios da biblioteca</h2>"
        f'<p class="lede">{len(cards)} curtas feitos com a <code>srstudio</code>, lidos dos projetos em disco e dos '
        "renders do motor, reduzidos para a web. Clique numa fala para pular até ela.</p></div>"
        + "".join(_card(c, media, poster) for c in cards)
        + (
            f'<div class="sub">Folha de poses do Pip</div><div class="poses lib-poses">{pose_tiles}</div>'
            if poses
            else ""
        )
        + f'<div class="sub">Registro de peças</div>{_registry_table(usage)}'
        + (_usage_lists(usage) if usage is not None else "")
        + "</section>\n"
    )
    page = page.replace(_ANCHORS["section"], section + _ANCHORS["section"], 1)
    page = page.replace(
        _ANCHORS["footer"],
        "  <p>Episódios da biblioteca: projetos em <code>generated/episodes/</code> e renders em "
        "<code>generated/renders/</code>; página gerada por <code>srstudio page</code>.</p>\n" + _ANCHORS["footer"],
        1,
    )
    return page.replace(_ANCHORS["body"], _JS + _ANCHORS["body"], 1)


# -- media and the build ----------------------------------------------------------------------------------
def _run(args: Sequence[str]) -> None:
    try:
        subprocess.run(list(args), check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        err = getattr(exc, "stderr", b"") or b""
        raise CatalogError(f"{Path(args[0]).name} failed: {exc} {err.decode(errors='replace')[-400:]}") from None


def data_uri(path: Path) -> str:
    kind = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".png": "image/png"}[path.suffix]
    return f"data:{kind};base64," + base64.b64encode(path.read_bytes()).decode()


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
    scene.add_project(width=300, height=320, fps="1", duration=len(names), background=WARM.background)
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


def build(
    *,
    base: Path,
    episodes: Path,
    renders: Path,
    out: Path,
    cache: Path,
    engine: Path,
    notes: Notes | None = None,
    usage: Report | None = None,
) -> list[Card]:
    """Write the page to ``out`` (file 600, a new folder 700) and return its cards."""
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
        poses = [(n, data_uri(p)) for n, p in pose_sheet(Path(engine), cache)]
        renders_of = {c.slug: c.render for c in cards}
        result = inject(
            page,
            cards,
            notes,
            media=lambda r: data_uri(web[r][0]),
            poster=lambda r: data_uri(web[r][1]),
            poses=poses,
            stills=lambda s: data_uri(still(renders_of[s.episode], s, cache)),
            usage=usage,
        )
        out.parent.mkdir(parents=True, exist_ok=True)  # a new folder is 700; an existing one is left as it is
        fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=f".{out.name}.")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(result)
        os.chmod(tmp, 0o600)
        os.replace(tmp, out)
    finally:
        os.umask(old)
    return cards
