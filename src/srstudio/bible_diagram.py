"""The relationship diagram of the cast bible, drawn through the engine with sr-core (ADR 0069).

One portrait picture, 1080 pixels wide, read on a phone: a name is set at :data:`NAME_SIZE` or larger, a line is
as thick as the pair has shared reels, and its colour says the kind of relation (the legend names each kind used).
Every world is its own panel, because Saga and Gloss share no canon with Okayville and a line between them would
be a claim the bible does not make.

The layout is plain code: a seeded spring layout run over many seeds, keeping the one with no overlapping names and
the fewest crossings. :func:`crossings` and :func:`overlaps` say what a layout leaves, and :func:`compose` refuses a
picture that leaves any name overlapping another.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sr_core.scene import Scene

from . import fonts
from .bible import Bible
from .canvas import OFFICE, Canvas, flat_counter
from .cast_card import DISPLAY_ASSET, DISPLAY_FILE, ENGINE_ARGS, TEXT_ASSET, TEXT_FILE, Lettering, contrast
from .errors import SrstudioError

__all__ = [
    "KINDS",
    "NAME_SIZE",
    "GAP",
    "SEEDS",
    "DiagramError",
    "Panel",
    "blocked",
    "compose",
    "crossings",
    "kind_of",
    "layout",
    "overlaps",
    "panels",
    "render",
]

WIDTH = 1080
MARGIN = 40
NAME_SIZE = 44
LEGEND_SIZE = 34
HEAD_SIZE = 52
PAD_X, PAD_Y = 22, 12
GAP = 40  # the least space between two names
SEEDS = 400  # layouts tried per panel; a tall dense group needs many to find few crossings
INK = "#1F1A17"
PAPER = "#FFF8EC"
WORLD_FILL = {
    "okayville": "#FFD27A",
    "saga": "#B9C4F2",
    "gloss": "#F6B8D0",
    "news": "#A8DCC8",
    "host": "#E4CFA8",
    "mind": "#CDE0A0",
    "maps": "#CDE0A0",
}
WORLD_TITLE = {
    "okayville": "Okayville",
    "saga": "Saga",
    "gloss": "Gloss",
    "news": "News Compiler",
    "host": "The host",
    "mind": "Mind",
    "maps": "Maps",
}
# the kind of a relation, by the first of these words its text holds; ``other`` when none
KINDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "family",
        "#C2410C",
        (
            "family",
            "father",
            "mother",
            "dad",
            "mom",
            "son",
            "daughter",
            "sibling",
            "brother",
            "sister",
            "parent",
            "child",
            "grand",
        ),
    ),
    ("couple", "#BE185D", ("couple", "dating", "partner", "spouse", "husband", "wife", "ex-", "date")),
    (
        "work",
        "#1D4ED8",
        ("cowork", "colleague", "boss", "manager", "employee", "interview", "candidate", "team", "office", "client"),
    ),
    ("friends", "#15803D", ("friend", "roommate", "neighbour", "neighbor", "flatmate", "housemate")),
    ("service", "#7C3AED", ("barista", "customer", "landlord", "tenant", "cleaner", "seller", "buyer", "waiter")),
)
OTHER = ("other", "#525252")
BOX = tuple[float, float, float, float]  # x, y, width, height


class DiagramError(SrstudioError, ValueError):
    """The picture cannot be made: a name overlaps another, a font is missing, or the engine cannot draw it."""


def kind_of(relation: str) -> tuple[str, str]:
    """The kind (name and colour) of a relation's text: the first kind whose word it holds, else ``other``."""
    text = relation.lower()
    for name, colour, words in KINDS:
        if any(word in text for word in words):
            return name, colour
    return OTHER


@dataclass(frozen=True)
class Panel:
    """One world's names and the pairs between them (slug pairs with the number of reels they share)."""

    world: str
    names: Mapping[str, str]  # slug -> name
    edges: Mapping[tuple[str, str], tuple[str, int]]  # (a, b) -> (kind, shared reels)
    first: bool = True  # the first panel of a world carries its heading; a later one is a group that stays apart


def panels(bible: Bible) -> list[Panel]:
    """One panel per world that has a pair, the characters with no pair left out, a pair across worlds refused."""
    world = {c.slug: c.world for c in bible.characters}
    name = {c.slug: c.name for c in bible.characters}
    edges: dict[str, dict[tuple[str, str], tuple[str, int]]] = {}
    for rel in bible.relationships:
        if world[rel.a] != world[rel.b]:
            raise DiagramError(f"{rel.a}+{rel.b} joins {world[rel.a]} to {world[rel.b]}: worlds share no canon")
        edges.setdefault(world[rel.a], {})[(rel.a, rel.b)] = (kind_of(rel.relation)[0], max(len(rel.reels), 1))
    out = []
    for w in WORLD_FILL:
        if w not in edges:
            continue
        for i, group in enumerate(_groups(edges[w])):
            kept = {pair: edge for pair, edge in edges[w].items() if pair[0] in group}
            out.append(Panel(w, {s: name[s] for s in sorted(group)}, kept, first=i == 0))
    return out


def _groups(edges: Mapping[tuple[str, str], tuple[str, int]]) -> list[set[str]]:
    """The connected groups of a world's pairs, the largest first: a group has its own area, so it stays readable."""
    near: dict[str, set[str]] = {}
    for a, b in edges:
        near.setdefault(a, set()).add(b)
        near.setdefault(b, set()).add(a)
    seen: set[str] = set()
    groups = []
    for start in sorted(near):
        if start in seen:
            continue
        group: set[str] = set()
        todo = [start]
        while todo:
            slug = todo.pop()
            if slug not in group:
                group.add(slug)
                todo.extend(near[slug] - group)
        seen |= group
        groups.append(group)
    return sorted(groups, key=lambda g: (-len(g), sorted(g)))


def sizes(panel: Panel, face: bytes) -> dict[str, tuple[float, float]]:
    return {
        s: (fonts.text_width(face, n, NAME_SIZE) + 2 * PAD_X, NAME_SIZE * 1.2 + 2 * PAD_Y)
        for s, n in panel.names.items()
    }


def _segments_cross(p: np.ndarray, q: np.ndarray, r: np.ndarray, s: np.ndarray) -> bool:
    def ccw(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
        return bool((c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0]))

    return ccw(p, r, s) != ccw(q, r, s) and ccw(p, q, r) != ccw(p, q, s)


def crossings(position: Mapping[str, tuple[float, float]], edges: Sequence[tuple[str, str]]) -> int:
    """Pairs of lines that cross away from a shared end."""
    count = 0
    for i, (a, b) in enumerate(edges):
        for c, d in edges[i + 1 :]:
            if len({a, b, c, d}) < 4:
                continue
            if _segments_cross(*(np.array(position[k]) for k in (a, b, c, d))):
                count += 1
    return count


def overlaps(
    position: Mapping[str, tuple[float, float]], size: Mapping[str, tuple[float, float]], gap: float = 14
) -> int:
    """Pairs of names whose boxes (centred on the positions, ``gap`` apart) overlap."""
    keys = sorted(position)
    count = 0
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            dx, dy = abs(position[a][0] - position[b][0]), abs(position[a][1] - position[b][1])
            if dx < (size[a][0] + size[b][0]) / 2 + gap and dy < (size[a][1] + size[b][1]) / 2 + gap:
                count += 1
    return count


def _hits(p: tuple[float, float], q: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
    """Whether the segment p-q passes through the box (x0, y0, x1, y1), by clipping it to the box."""
    lo, hi = 0.0, 1.0
    for start, delta, low, high in ((p[0], q[0] - p[0], box[0], box[2]), (p[1], q[1] - p[1], box[1], box[3])):
        if abs(delta) < 1e-9:
            if not low <= start <= high:
                return False
            continue
        a, b = (low - start) / delta, (high - start) / delta
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if lo > hi:
            return False
    return True


def blocked(
    position: Mapping[str, tuple[float, float]],
    size: Mapping[str, tuple[float, float]],
    edges: Sequence[tuple[str, str]],
    margin: float = 8,
) -> int:
    """Lines that pass through the name of a character they do not join (its box grown by ``margin``)."""
    count = 0
    for a, b in edges:
        for key, (cx, cy) in position.items():
            if key in (a, b):
                continue
            w, h = size[key]
            if _hits(
                position[a],
                position[b],
                (cx - w / 2 - margin, cy - h / 2 - margin, cx + w / 2 + margin, cy + h / 2 + margin),
            ):
                count += 1
    return count


def _spring(keys: list[str], edges: Sequence[tuple[str, str]], width: float, height: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(keys)
    index = {k: i for i, k in enumerate(keys)}
    pos = rng.uniform(0.1, 0.9, (n, 2)) * (width, height)
    k = 0.8 * np.sqrt(width * height / max(n, 1))
    for step in range(300):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(delta, axis=2) + 0.01
        push = (k * k / dist**2)[:, :, None] * delta
        move = push.sum(axis=1)
        for a, b in edges:
            d = pos[index[a]] - pos[index[b]]
            length = np.linalg.norm(d) + 0.01
            pull = d * (length / k)
            move[index[a]] -= pull
            move[index[b]] += pull
        cap = 40 * (1 - step / 300) + 1
        norm = np.linalg.norm(move, axis=1)[:, None] + 0.01
        pos += move / norm * np.minimum(norm, cap)
        pos[:, 0] = np.clip(pos[:, 0], 0, width)
        pos[:, 1] = np.clip(pos[:, 1], 0, height)
    return pos


def _separate(
    position: dict[str, tuple[float, float]],
    size: Mapping[str, tuple[float, float]],
    width: float,
    height: float,
    gap: float = 14,
) -> dict[str, tuple[float, float]]:
    """Push apart the names whose boxes are closer than ``gap``, along the shorter way out, inside the area."""
    keys = sorted(position)
    pos = {k: list(v) for k, v in position.items()}
    for _ in range(400):
        moved = False
        for i, a in enumerate(keys):
            for b in keys[i + 1 :]:
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                need_x = (size[a][0] + size[b][0]) / 2 + gap - abs(dx)
                need_y = (size[a][1] + size[b][1]) / 2 + gap - abs(dy)
                if need_x <= 0 or need_y <= 0:
                    continue
                moved = True
                if need_y <= need_x:
                    step = need_y / 2 + 0.5
                    sign = 1.0 if dy >= 0 else -1.0
                    pos[a][1] -= sign * step
                    pos[b][1] += sign * step
                else:
                    step = need_x / 2 + 0.5
                    sign = 1.0 if dx >= 0 else -1.0
                    pos[a][0] -= sign * step
                    pos[b][0] += sign * step
        for k in keys:
            pos[k][0] = min(max(pos[k][0], size[k][0] / 2), width - size[k][0] / 2)
            pos[k][1] = min(max(pos[k][1], size[k][1] / 2), height - size[k][1] / 2)
        if not moved:
            break
    return {k: (v[0], v[1]) for k, v in pos.items()}


def _spread(raw: np.ndarray, width: float, height: float) -> np.ndarray:
    """Stretch each axis to fill the area: an affine map, so no crossing is made or lost, but the names get room."""
    out = raw.copy()
    for axis, extent in ((0, width), (1, height)):
        low, high = out[:, axis].min(), out[:, axis].max()
        if high - low > 1e-6:
            out[:, axis] = (out[:, axis] - low) / (high - low) * extent
    return out


def layout(
    panel: Panel, size: Mapping[str, tuple[float, float]], width: float, height: float, seeds: int | None = None
) -> dict[str, tuple[float, float]]:
    """Positions (box centres) inside ``width`` x ``height``: the seed with no overlap and the fewest crossings.

    The same panel and sizes always give the same layout. A panel that fits no seed without overlap is refused, so
    a caller makes the area taller instead of drawing names over each other."""
    seeds = SEEDS if seeds is None else seeds
    keys = sorted(panel.names)
    edges = sorted(panel.edges)
    half_w = max(w for w, _ in size.values()) / 2
    half_h = max(h for _, h in size.values()) / 2
    best: tuple[tuple[int, float], dict[str, tuple[float, float]]] | None = None
    for seed in range(seeds):
        raw = _spread(
            _spring(keys, edges, width - 2 * half_w, height - 2 * half_h, seed), width - 2 * half_w, height - 2 * half_h
        )
        position = {k: (float(raw[i][0] + half_w), float(raw[i][1] + half_h)) for i, k in enumerate(keys)}
        position = _separate(position, size, width, height, GAP)
        if overlaps(position, size, GAP):
            continue
        length = sum(np.hypot(position[a][0] - position[b][0], position[a][1] - position[b][1]) for a, b in edges)
        score = (blocked(position, size, edges) * 3 + crossings(position, edges), float(length))
        if best is None or score < best[0]:
            best = (score, position)
    if best is None:
        raise DiagramError(f"{panel.world}: no layout of {len(keys)} names fits {width:g}x{height:g} without overlap")
    return best[1]


def _letter(
    cv: Canvas, id: str, text: str, box: BOX, size: int, asset: str, colour: str, align: str = "center"
) -> None:
    x, y, w, h = box
    cv.assets.add_text(id=id, text=text, width=round(w), height=round(h), size=str(size), fontAsset=asset, color=colour,
                       align=align, verticalAlign="middle", wrap="none")  # fmt: skip
    cv.comp.add_layer(id=f"{id}-layer", asset=id, x=round(x), y=round(y))


def panel_height(panel: Panel) -> int:
    """The drawing area a panel gets: taller for more names, so a dense world has room to avoid crossings."""
    return max(360, 120 * len(panel.names))


def compose(bible: Bible, faces: Lettering) -> tuple[Scene, dict[str, int]]:
    """The one-frame scene of the diagram, and the crossings left in each world's panel."""
    drawn = panels(bible)
    if not drawn:
        raise DiagramError("the bible has no relationship to draw")
    face = faces.display
    laid = []
    total = MARGIN
    for panel in drawn:
        size = sizes(panel, face)
        area = panel_height(panel)
        position = layout(panel, size, WIDTH - 2 * MARGIN, area)
        laid.append((panel, size, position, total))
        total += (HEAD_SIZE + 24 if panel.first else 0) + area + 40
    used = sorted({kind for panel in drawn for kind, _ in panel.edges.values()})
    legend = total
    height = legend + 70 + 60 * ((len(used) + 1) // 2) + MARGIN
    scene = Scene(version="auto")
    scene.add_project(width=WIDTH, height=height, fps="24", duration=1, background=PAPER)
    cv = Canvas(scene, OFFICE, font_asset=DISPLAY_ASSET, namer=flat_counter("n"), width=WIDTH, height=height)
    for asset, src, font in ((DISPLAY_ASSET, DISPLAY_FILE, faces.display), (TEXT_ASSET, TEXT_FILE, faces.text)):
        cv.assets.add_font(id=asset, src=src, family=fonts.inspect_ttf(font).family,
                           sha256=hashlib.sha256(font).hexdigest())  # fmt: skip
    colour = {name: hexa for name, hexa, _ in KINDS} | {OTHER[0]: OTHER[1]}
    left: dict[str, int] = {}
    for panel, size, position, top in laid:
        origin = top + (HEAD_SIZE + 24 if panel.first else 0)
        if panel.first:
            _letter(
                cv,
                f"head-{panel.world}",
                WORLD_TITLE[panel.world],
                (MARGIN, top, WIDTH - 2 * MARGIN, HEAD_SIZE),
                HEAD_SIZE,
                DISPLAY_ASSET,
                INK,
                "start",
            )
        cv.rect(
            cv.comp,
            MARGIN - 10,
            origin - 8,
            WIDTH - 2 * MARGIN + 20,
            panel_height(panel) + 16,
            "#FFFFFF",
            "#E7D9BF",
            3,
            radius=24,
        )
        for (a, b), (kind, shared) in sorted(panel.edges.items()):
            (x1, y1), (x2, y2) = position[a], position[b]
            cv.line(cv.comp, MARGIN + x1, origin + y1, MARGIN + x2, origin + y2, colour[kind], 4 + 1.5 * min(shared, 6))
        for slug, (cx, cy) in sorted(position.items()):
            w, h = size[slug]
            fill = WORLD_FILL[panel.world]
            if contrast(INK, fill) < 4.5:
                raise DiagramError(f"{slug}: the name does not read on {fill}")
            box = (MARGIN + cx - w / 2, origin + cy - h / 2, w, h)
            cv.rect(cv.comp, box[0], box[1], w, h, fill, INK, 3, radius=h / 2)
            _letter(cv, f"name-{panel.world}-{slug}", panel.names[slug], box, NAME_SIZE, DISPLAY_ASSET, INK)
        left[panel.world] = left.get(panel.world, 0) + crossings(position, sorted(panel.edges))
    _letter(
        cv, "legend-head", "Lines", (MARGIN, legend, WIDTH - 2 * MARGIN, 50), LEGEND_SIZE + 6, TEXT_ASSET, INK, "start"
    )
    for i, kind in enumerate(used):
        x = MARGIN + (i % 2) * 520
        y = legend + 70 + (i // 2) * 60
        cv.rect(cv.comp, x, y + 10, 70, 14, colour[kind], None, 0, radius=7)
        _letter(cv, f"legend-{kind}", kind, (x + 90, y, 400, 36), LEGEND_SIZE, TEXT_ASSET, INK, "start")
    return scene, left


def render(bible: Bible, out: Path, faces: Lettering, engine: str | Path, work: Path) -> dict[str, int]:
    """Draw the diagram to ``out`` and return the crossings left per world."""
    scene, left = compose(bible, faces)
    work.mkdir(parents=True, exist_ok=True)
    (work / DISPLAY_FILE).write_bytes(faces.display)
    (work / TEXT_FILE).write_bytes(faces.text)
    document, png = work / "relationships.scene.xml", work / "relationships.png"
    document.write_bytes(scene.to_bytes())
    try:
        subprocess.run(
            [str(engine), "render", document.name, *ENGINE_ARGS, "-o", png.name],
            cwd=work,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        raise DiagramError(
            f"the engine cannot draw the diagram: {detail.decode(errors='replace')[-400:] or exc}"
        ) from exc
    if not png.exists():
        raise DiagramError("the engine wrote no relationships.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    png.replace(out)
    out.chmod(0o600)
    return left
