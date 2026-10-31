"""The cast bible: a typed loader for ``bible/cast.json`` and ``bible/relationships.json`` (ADR 0069).

Every script is written from the bible, so a build and a delivery read it as data. Both files are parsed into frozen
dataclasses that refuse unknown fields, and the loader asserts what a schema cannot say:

- a field of a persona is its own substantive text, or starts ``open:`` (the reels do not tell, and the question
  follows) or ``proposal:`` (a wording that fits every published reel but is new, so it is the operator's to approve);
- a substantive field names the fact behind it: some :class:`Fact` of that character has ``field`` equal to it;
- a canon character has at least one fact, a placeholder has none and says so in every field;
- a relationship joins two characters of the bible and each of its texts rests on a fact or is marked;
- the bible's version is the same in both files.

Whether a fact is true of its reel is checked against the reel, by :func:`verify`, with no model in the loop: a
quoted line must be among the reel's lines, captions or post text. Whether two facts contradict each other in prose is
beyond what code can prove, and nothing here pretends to.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping
from dataclasses import MISSING, dataclass, fields
from pathlib import Path
from typing import Any, ClassVar

from . import bible_inventory
from .errors import SrstudioError
from .releases import Release

__all__ = ["SCHEMA", "WORLDS", "Bible", "BibleError", "Character", "Fact", "Relationship", "load", "verify"]

SCHEMA = "1.0.0"  # the format of both files; its major changes only when a field is removed or renamed
WORLDS = ("okayville", "saga", "gloss", "news", "host", "mind", "maps")
STATUSES = ("canon", "placeholder")
PAIR_STATUSES = ("canon", "proposal")
KINDS = ("person", "animal", "object", "archetype")
ROLES = ("straight", "instigator", "victim", "chaos", "know-it-all")
FACT_KINDS = ("line", "drawn", "voice", "seen")
CLASH_KINDS = ("name", "drawing", "voice")
SCOPES = ("across-worlds", "within-world")
MARKS = ("open:", "proposal:")
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
FACT_FIELDS = (
    "identity",
    "look.palette",
    "look.outfits",
    "look.never_changes",
    "voice.provider",
    "voice.voice",
    "voice.settings",
    "voice.pace",
    "voice.tics",
    "voice.uses",
    "voice.never_uses",
    "who.age_range",
    "who.job",
    "who.home",
    "who.normal_day",
    "who.wants",
    "who.flaw",
    "who.habit",
    "who.pov",
    "comic.role",
    "comic.under_pressure",
    "comic.always_gets_them",
    "relationship",
    "world",
)


class BibleError(SrstudioError, ValueError):
    """A bible file cannot be trusted: unknown or missing fields, a wrong type, or a rule of the bible broken."""


def _fail(where: str, message: str) -> BibleError:
    return BibleError(f"{where}: {message}")


def _object(data: object, where: str, cls: type) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise _fail(where, f"expected an object, got {type(data).__name__}")
    names = {f.name for f in fields(cls)}
    unknown = sorted(set(data) - names)
    if unknown:
        raise _fail(where, f"unknown field(s) {', '.join(unknown)}; known: {', '.join(sorted(names))}")
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    missing = sorted(required - set(data))
    if missing:
        raise _fail(where, f"missing field(s) {', '.join(missing)}")
    return data


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _fail(where, f"expected nonempty text, got {value!r}")
    return value


def _texts(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _fail(where, f"expected a list, got {type(value).__name__}")
    return tuple(_text(v, f"{where}[{i}]") for i, v in enumerate(value))


def _slugs(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _fail(where, f"expected a list, got {type(value).__name__}")
    return tuple(_slug(v, f"{where}[{i}]") for i, v in enumerate(value))


def _choice(value: object, where: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise _fail(where, f"{value!r} is not one of {', '.join(allowed)}")
    return str(value)


def _slug(value: object, where: str) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise _fail(where, f"{value!r} is not a lowercase slug")
    return value


def _role(value: object, where: str) -> str:
    return _text(value, where) if isinstance(value, str) and _marked(value) else _choice(value, where, ROLES)


def _marked(text: str) -> bool:
    return text.startswith(MARKS)


@dataclass(frozen=True)
class Fact:
    """A fact established on screen, with the reel and the words or drawing that establish it."""

    fact: str
    field: str
    reel: str
    kind: str
    quote: str

    @classmethod
    def parse(cls, data: object, where: str) -> Fact:
        d = _object(data, where, cls)
        return cls(
            _text(d["fact"], f"{where}.fact"),
            _choice(d["field"], f"{where}.field", FACT_FIELDS),
            _slug(d["reel"], f"{where}.reel"),
            _choice(d["kind"], f"{where}.kind", FACT_KINDS),
            _text(d["quote"], f"{where}.quote"),
        )


def _facts(value: object, where: str) -> tuple[Fact, ...]:
    if not isinstance(value, list):
        raise _fail(where, f"expected a list, got {type(value).__name__}")
    return tuple(Fact.parse(v, f"{where}[{i}]") for i, v in enumerate(value))


@dataclass(frozen=True)
class Drawing:
    part: str
    version: int

    @classmethod
    def parse(cls, data: object, where: str) -> Drawing:
        d = _object(data, where, cls)
        version = d["version"]
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise _fail(f"{where}.version", f"expected a version number of 1 or more, got {version!r}")
        return cls(_slug(d["part"], f"{where}.part"), version)


@dataclass(frozen=True)
class Look:
    drawing: tuple[Drawing, ...]
    palette: str
    outfits: str
    never_changes: str


@dataclass(frozen=True)
class Voice:
    provider: str
    voice: str
    settings: str
    pace: str
    tics: str
    uses: str
    never_uses: str


@dataclass(frozen=True)
class Who:
    age_range: str
    job: str
    home: str
    normal_day: str
    wants: str
    flaw: str
    habit: str
    pov: str


@dataclass(frozen=True)
class Comic:
    role: str
    under_pressure: str
    always_gets_them: str


@dataclass(frozen=True)
class OpenItem:
    question: str
    proposal: str


def _section(data: object, where: str, cls: type, names: tuple[str, ...]) -> dict[str, str]:
    d = _object(data, where, cls)
    return {n: _text(d[n], f"{where}.{n}") for n in names}


@dataclass(frozen=True)
class Character:
    slug: str
    name: str
    world: str
    status: str
    kind: str
    reels: tuple[str, ...]
    look: Look
    voice: Voice
    who: Who
    comic: Comic
    canon: tuple[Fact, ...]
    never: tuple[str, ...]
    open: tuple[OpenItem, ...]
    since: str = "1.0.0"
    history: tuple[str, ...] = ()

    PERSONA: ClassVar[tuple[str, ...]] = ("look", "voice", "who", "comic")

    @classmethod
    def parse(cls, data: object, where: str) -> Character:
        d = _object(data, where, cls)
        look = _object(d["look"], f"{where}.look", Look)
        voice = _section(d["voice"], f"{where}.voice", Voice, tuple(f.name for f in fields(Voice)))
        who = _section(d["who"], f"{where}.who", Who, tuple(f.name for f in fields(Who)))
        comic = _object(d["comic"], f"{where}.comic", Comic)
        drawing = look["drawing"]
        if not isinstance(drawing, list):
            raise _fail(f"{where}.look.drawing", "expected a list of drawings")
        opened = d["open"]
        if not isinstance(opened, list):
            raise _fail(f"{where}.open", "expected a list")
        items = []
        for i, item in enumerate(opened):
            o = _object(item, f"{where}.open[{i}]", OpenItem)
            items.append(
                OpenItem(
                    _text(o["question"], f"{where}.open[{i}].question"),
                    _text(o["proposal"], f"{where}.open[{i}].proposal"),
                )
            )
        never = _texts(d["never"], f"{where}.never")
        since = d.get("since", "1.0.0")
        if not isinstance(since, str) or not SEMVER.fullmatch(since):
            raise _fail(f"{where}.since", f"{since!r} is not a semantic version")
        return cls(
            _slug(d["slug"], f"{where}.slug"),
            _text(d["name"], f"{where}.name"),
            _choice(d["world"], f"{where}.world", WORLDS),
            _choice(d["status"], f"{where}.status", STATUSES),
            _choice(d["kind"], f"{where}.kind", KINDS),
            _slugs(d["reels"], f"{where}.reels"),
            Look(
                tuple(Drawing.parse(x, f"{where}.look.drawing[{i}]") for i, x in enumerate(drawing)),
                _text(look["palette"], f"{where}.look.palette"),
                _text(look["outfits"], f"{where}.look.outfits"),
                _text(look["never_changes"], f"{where}.look.never_changes"),
            ),
            Voice(**voice),
            Who(**who),
            Comic(
                _role(comic["role"], f"{where}.comic.role"),
                _text(comic["under_pressure"], f"{where}.comic.under_pressure"),
                _text(comic["always_gets_them"], f"{where}.comic.always_gets_them"),
            ),
            _facts(d["canon"], f"{where}.canon"),
            never,
            tuple(items),
            since,
            _texts(d.get("history", []), f"{where}.history"),
        )

    def persona_fields(self) -> dict[str, str]:
        """Each text field of the persona by its fact name (``who.job``), the ones a fact must stand behind."""
        out = {
            "look.palette": self.look.palette,
            "look.outfits": self.look.outfits,
            "look.never_changes": self.look.never_changes,
            "comic.role": self.comic.role,
            "comic.under_pressure": self.comic.under_pressure,
            "comic.always_gets_them": self.comic.always_gets_them,
        }
        for section, value in (("voice", self.voice), ("who", self.who)):
            out.update({f"{section}.{f.name}": getattr(value, f.name) for f in fields(value)})
        return out

    def names(self) -> frozenset[str]:
        return frozenset({self.slug, self.name.lower()})


@dataclass(frozen=True)
class Relationship:
    a: str
    b: str
    relation: str
    how_they_know: str
    dynamic: str
    tension: str
    meet: str
    history: tuple[Fact, ...]
    status: str
    reels: tuple[str, ...]

    @classmethod
    def parse(cls, data: object, where: str) -> Relationship:
        d = _object(data, where, cls)
        a, b = _slug(d["a"], f"{where}.a"), _slug(d["b"], f"{where}.b")
        if a == b:
            raise _fail(where, f"{a} is paired with themself")
        if a > b:
            raise _fail(where, f"the pair is written alphabetically: {b} before {a}")
        texts = {n: _text(d[n], f"{where}.{n}") for n in ("relation", "how_they_know", "dynamic", "tension", "meet")}
        return cls(
            a,
            b,
            history=_facts(d["history"], f"{where}.history"),
            status=_choice(d["status"], f"{where}.status", PAIR_STATUSES),
            reels=_slugs(d["reels"], f"{where}.reels"),
            **texts,
        )

    def texts(self) -> tuple[str, ...]:
        return (self.relation, self.how_they_know, self.dynamic, self.tension, self.meet)


@dataclass(frozen=True)
class Place:
    slug: str
    name: str
    world: str
    description: str
    found: tuple[str, ...]
    cites: tuple[Fact, ...]


@dataclass(frozen=True)
class Rule:
    id: str
    rule: str
    status: str
    cites: tuple[Fact, ...]


@dataclass(frozen=True)
class Clash:
    id: str
    kind: str
    scope: str
    subject: str
    evidence: tuple[Fact, ...]
    proposal: str


@dataclass(frozen=True)
class Bible:
    version: str
    characters: tuple[Character, ...]
    roles: tuple[str, ...]
    places: tuple[Place, ...]
    rules: tuple[Rule, ...]
    clashes: tuple[Clash, ...]
    relationships: tuple[Relationship, ...]

    def character(self, slug: str) -> Character | None:
        return next((c for c in self.characters if c.slug == slug), None)

    def named(self, name: str) -> list[Character]:
        """Every character the name belongs to: its slug or its name, in any world."""
        key = name.strip().lower()
        return [c for c in self.characters if key in c.names()]

    def facts(self) -> list[tuple[str, Fact]]:
        """Every fact of the bible with the subject that owns it."""
        out = [(c.slug, f) for c in self.characters for f in c.canon]
        out += [(f"{r.a}+{r.b}", f) for r in self.relationships for f in r.history]
        out += [(p.slug, f) for p in self.places for f in p.cites]
        out += [(r.id, f) for r in self.rules for f in r.cites]
        out += [(c.id, f) for c in self.clashes for f in c.evidence]
        return out


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail(str(path), f"cannot read: {exc}") from exc
    if not isinstance(data, dict):
        raise _fail(str(path), "expected a JSON object")
    schema = data.get("schema")
    if not isinstance(schema, str) or schema.split(".")[0] != SCHEMA.split(".")[0] or not SEMVER.fullmatch(schema):
        raise _fail(str(path), f"schema {schema!r} is not a {SCHEMA.split('.')[0]}.x.y schema this loader reads")
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise _fail(str(path), f"version {version!r} is not a semantic version")
    label = data.get("generated_by", "x")
    if not isinstance(label, str) or not label.strip():
        raise _fail(str(path), "generated_by names the model and the tool that wrote the file; it is nonempty text")
    return data


def _top(data: dict[str, Any], where: str, allowed: tuple[str, ...]) -> None:
    unknown = sorted(set(data) - {"schema", "version", "generated_by", *allowed})
    if unknown:
        raise _fail(where, f"unknown field(s) {', '.join(unknown)}")
    missing = sorted(set(allowed) - set(data))
    if missing:
        raise _fail(where, f"missing field(s) {', '.join(missing)}")


def _list(data: dict[str, Any], key: str, where: str) -> list[Any]:
    value = data[key]
    if not isinstance(value, list):
        raise _fail(f"{where}.{key}", "expected a list")
    return value


def _simple(cls: type, data: object, where: str, **parsers: Any) -> Any:
    d = _object(data, where, cls)
    return cls(
        **{f.name: parsers.get(f.name, lambda v, w: _text(v, w))(d[f.name], f"{where}.{f.name}") for f in fields(cls)}
    )


def _place(data: object, where: str) -> Place:
    return _simple(Place, data, where, slug=_slug, world=lambda v, w: _choice(v, w, WORLDS), found=_slugs, cites=_facts)


def _rule(data: object, where: str) -> Rule:
    return _simple(Rule, data, where, status=lambda v, w: _choice(v, w, ("canon", "proposal")), cites=_facts)


def _clash(data: object, where: str) -> Clash:
    return _simple(
        Clash,
        data,
        where,
        kind=lambda v, w: _choice(v, w, CLASH_KINDS),
        scope=lambda v, w: _choice(v, w, SCOPES),
        evidence=_facts,
    )


def load(folder: Path) -> Bible:
    """Read ``cast.json`` and ``relationships.json`` of ``folder``; refuse anything the bible's rules do not allow."""
    cast = _read(Path(folder) / "cast.json")
    pairs = _read(Path(folder) / "relationships.json")
    _top(cast, "cast.json", ("characters", "roles", "places", "rules", "clashes"))
    _top(pairs, "relationships.json", ("relationships",))
    if cast["version"] != pairs["version"]:
        raise _fail("bible", f"cast.json is version {cast['version']} and relationships.json {pairs['version']}")
    characters = tuple(
        Character.parse(c, f"cast.json.characters[{i}]") for i, c in enumerate(_list(cast, "characters", "cast.json"))
    )
    bible = Bible(
        cast["version"],
        characters,
        _texts(cast["roles"], "cast.json.roles"),
        tuple(_place(p, f"cast.json.places[{i}]") for i, p in enumerate(_list(cast, "places", "cast.json"))),
        tuple(_rule(r, f"cast.json.rules[{i}]") for i, r in enumerate(_list(cast, "rules", "cast.json"))),
        tuple(_clash(c, f"cast.json.clashes[{i}]") for i, c in enumerate(_list(cast, "clashes", "cast.json"))),
        tuple(
            Relationship.parse(r, f"relationships.json.relationships[{i}]")
            for i, r in enumerate(_list(pairs, "relationships", "relationships.json"))
        ),
    )
    _rules(bible)
    return bible


def _unique(values: Collection[str], where: str, what: str) -> None:
    seen: set[str] = set()
    for v in values:
        if v in seen:
            raise _fail(where, f"{what} {v!r} appears twice")
        seen.add(v)


def _rules(bible: Bible) -> None:
    _unique([c.slug for c in bible.characters], "cast.json", "character")
    _unique([p.slug for p in bible.places], "cast.json", "place")
    _unique([r.id for r in bible.rules], "cast.json", "rule")
    _unique([c.id for c in bible.clashes], "cast.json", "clash")
    _unique([f"{r.a}+{r.b}" for r in bible.relationships], "relationships.json", "pair")
    for c in bible.characters:
        where = f"character {c.slug}"
        if len(c.never) != 3:
            raise _fail(where, f"never lists {len(c.never)} things; it lists exactly three")
        if c.status == "canon" and not c.canon:
            raise _fail(where, "a canon character has no fact; it is a placeholder until a reel establishes one")
        if c.status == "placeholder":
            if c.canon:
                raise _fail(where, "a placeholder holds no canon: it is waiting for the reel that makes it one")
            loud = [name for name, text in c.persona_fields().items() if not text.startswith("open:")]
            if loud:
                raise _fail(where, f"a placeholder leaves {', '.join(loud)} as open:, not as text")
            continue
        backed = {f.field for f in c.canon}
        for name, text in c.persona_fields().items():
            if not _marked(text) and name not in backed:
                raise _fail(where, f"{name} is stated with no fact behind it; cite one, or mark it open: or proposal:")
        for name, text in c.persona_fields().items():
            if _marked(text) and name in backed:
                raise _fail(where, f"{name} is marked yet has a fact behind it; state it, or drop the fact")
        if not c.look.drawing:
            raise _fail(where, "a canon character has no approved drawing")
    slugs = {c.slug for c in bible.characters}
    for place in bible.places:
        gone = sorted(set(place.found) - slugs)
        if gone:
            raise _fail(f"place {place.slug}", f"{', '.join(gone)} is not a character of the bible")
    for rel in bible.relationships:
        where = f"relationship {rel.a}+{rel.b}"
        gone = sorted({rel.a, rel.b} - slugs)
        if gone:
            raise _fail(where, f"{', '.join(gone)} is not a character of the bible")
        if rel.status == "canon" and any(not _marked(t) and not rel.history for t in rel.texts()):
            raise _fail(where, "a canon relationship has no history fact behind its texts")
        if rel.status == "canon" and any(_marked(t) for t in rel.texts()):
            raise _fail(where, "a canon relationship holds an open: or proposal: text; its status is proposal")


def verify(
    bible: Bible,
    releases: Mapping[str, Release],
    published: Collection[str],
    episodes: Path,
    *,
    characters: Collection[str],
) -> list[str]:
    """Every fact that does not hold against its reel, as ``subject: why``; an empty list means all hold.

    A ``seen`` fact is an observation of a render, which code cannot confirm: it is listed as such, so the count
    of what rests on a person's eye is never hidden."""
    problems = []
    for subject, fact in bible.facts():
        why = bible_inventory.cite(
            fact.reel,
            fact.kind,
            fact.quote,
            releases=releases,
            published_slugs=published,
            episodes=episodes,
            characters=characters,
        )
        if why and fact.kind != "seen":
            problems.append(f"{subject}: {why}")
    for c in bible.characters:
        gone = sorted(set(c.reels) - set(published))
        if gone:
            problems.append(f"{c.slug}: reels not published: {', '.join(gone)}")
    return problems
