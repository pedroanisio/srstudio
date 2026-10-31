"""The readable files of the cast bible, written from ``cast.json`` and ``relationships.json`` (ADR 0069).

The data is the source; these pages never hold a fact the data does not, so they are regenerated, not edited:
``characters/<slug>.md`` (one persona sheet, with the drawing), ``canon.md``, ``world.md`` and ``open-decisions.md``.
Every page opens with a frontmatter naming the model and the tool that wrote it and the bible's version.
"""

from __future__ import annotations

from collections.abc import Sequence

from .bible import Bible, Character, Fact

__all__ = ["FRONTMATTER", "canon", "open_decisions", "sheet", "world"]

FRONTMATTER = "---\ngenerated-by: {model} in Claude Code\nbible-version: {version}\n---\n"
WORLD_TITLE = {
    "okayville": "Okayville",
    "saga": "Saga",
    "gloss": "Gloss",
    "news": "News Compiler",
    "host": "The talking-head host",
    "mind": "Mind",
    "maps": "Maps",
}


def _head(model: str, version: str) -> str:
    return FRONTMATTER.format(model=model, version=version)


def _text(value: str) -> str:
    """A persona field for a page: the text, with the mark made visible."""
    if value.startswith("open:"):
        return f"**Open.** {value.removeprefix('open:').strip()}"
    if value.startswith("proposal:"):
        return f"**Proposal.** {value.removeprefix('proposal:').strip()}"
    return value


def _cite(fact: Fact) -> str:
    return f"`{fact.reel}`"


def sheet(character: Character, *, model: str, version: str, order: Sequence[str], drawing: str | None = None) -> str:
    """One persona sheet. ``order`` lists the published reels oldest first; ``drawing`` is the picture's file name."""
    rank = {slug: i for i, slug in enumerate(order)}
    reels = sorted(character.reels, key=lambda s: rank.get(s, len(rank)))
    first = f"`{reels[0]}`" if reels else "open: no published reel yet"
    latest = f"`{reels[-1]}`" if reels else "open: no published reel yet"
    lines = [_head(model, version), f"# {character.name}", ""]
    if character.status == "placeholder":
        lines += ["> Placeholder. Nothing here is canon until a published reel establishes it.", ""]
    if drawing:
        lines += [f"![{character.name}]({drawing})", ""]
    lines += [
        "## Identity",
        "",
        f"- Name: {character.name}",
        f"- Slug: `{character.slug}`",
        f"- World: {WORLD_TITLE[character.world]}",
        f"- Kind: {character.kind}",
        f"- First reel: {first}",
        f"- Latest reel: {latest}",
        f"- Published reels: {len(reels)}",
        f"- In the bible since: {character.since}",
        "",
        "## Look",
        "",
    ]
    if character.look.drawing:
        shown = ", ".join(f"`{d.part}` version {d.version}" for d in character.look.drawing)
        lines.append(f"- Approved drawing: {shown}")
    else:
        lines.append("- Approved drawing: **Open.** No approved drawing yet.")
    lines += [
        f"- Palette: {_text(character.look.palette)}",
        f"- Usual outfits: {_text(character.look.outfits)}",
        f"- Never changes: {_text(character.look.never_changes)}",
        "",
        "## Voice",
        "",
    ]
    voice = character.voice
    for label, value in (
        ("Provider", voice.provider),
        ("Voice", voice.voice),
        ("Settings", voice.settings),
        ("Pace", voice.pace),
        ("Verbal tics", voice.tics),
        ("Words they use", voice.uses),
        ("Words they never use", voice.never_uses),
    ):
        lines.append(f"- {label}: {_text(value)}")
    lines += ["", "## Who they are", ""]
    who = character.who
    for label, value in (
        ("Age range", who.age_range),
        ("Job", who.job),
        ("Home", who.home),
        ("A normal day", who.normal_day),
        ("What they want", who.wants),
        ("Their flaw", who.flaw),
        ("Habit or running gag", who.habit),
        ("Point of view", who.pov),
    ):
        lines.append(f"- {label}: {_text(value)}")
    lines += ["", "## Comic role", ""]
    comic = character.comic
    lines += [
        f"- Role: {_text(comic.role)}",
        f"- Under pressure: {_text(comic.under_pressure)}",
        f"- What always gets them: {_text(comic.always_gets_them)}",
        "",
        "## Canon",
        "",
    ]
    lines += [f"- {f.fact} ({_cite(f)})" for f in character.canon] or ["- None yet."]
    lines += ["", "## Never", ""] + [f"- {_text(n)}" for n in character.never]
    lines += ["", "## Open", ""]
    lines += [f"- {o.question} Proposed: {o.proposal}" for o in character.open] or ["- Nothing open."]
    return "\n".join(lines) + "\n"


def canon(bible: Bible, *, model: str) -> str:
    """Every established fact, grouped by character, then by pair, with the reel that established it."""
    lines = [
        _head(model, bible.version),
        "# Canon",
        "",
        "Each fact is established by the published reel beside it.",
        "",
    ]
    for c in bible.characters:
        if not c.canon:
            continue
        lines += [f"## {c.name} ({WORLD_TITLE[c.world]})", ""]
        lines += [f"- {f.fact} ({_cite(f)})" for f in c.canon]
        lines.append("")
    pairs = [r for r in bible.relationships if r.history]
    if pairs:
        lines += ["## Pairs", ""]
        for r in pairs:
            lines += [f"### {r.a} and {r.b}", ""] + [f"- {f.fact} ({_cite(f)})" for f in r.history] + [""]
    return "\n".join(lines).rstrip() + "\n"


def world(bible: Bible, *, model: str) -> str:
    """The places that come back, the rules of each world, and what the bible says about time."""
    lines = [_head(model, bible.version), "# The world", ""]
    names = {c.slug: c.name for c in bible.characters}
    for w in WORLD_TITLE:
        places = [p for p in bible.places if p.world == w]
        if not places:
            continue
        lines += [f"## {WORLD_TITLE[w]}: places", ""]
        for p in places:
            who = ", ".join(names[s] for s in p.found) or "no one in particular"
            cites = ", ".join(sorted({_cite(f) for f in p.cites}))
            lines += [
                f"### {p.name}",
                "",
                p.description,
                "",
                f"Found here: {who}." + (f" Seen in {cites}." if cites else ""),
                "",
            ]
    canon_rules = [r for r in bible.rules if r.status == "canon"]
    proposals = [r for r in bible.rules if r.status == "proposal"]
    if canon_rules:
        lines += ["## Rules the reels establish", ""]
        for r in canon_rules:
            lines.append(f"- {r.rule} ({', '.join(sorted({_cite(f) for f in r.cites}))})")
        lines.append("")
    if proposals:
        lines += ["## Proposed rules", "", "These are not shown by two reels yet. They wait for the operator.", ""]
        for r in proposals:
            lines.append(
                f"- {r.rule}" + (f" (nearest: {', '.join(sorted({_cite(f) for f in r.cites}))})" if r.cites else "")
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def open_decisions(bible: Bible, *, model: str) -> str:
    """Every clash and every open question, each with a proposed resolution. None is resolved here."""
    lines = [
        _head(model, bible.version),
        "# Open decisions",
        "",
        "Each clash is for the operator to settle by renaming or retiring a character.",
        "Every resolution below is a proposal.",
        "",
        f"Clashes: {len(bible.clashes)}.",
        "",
    ]
    for kind in ("name", "drawing", "voice"):
        group = [c for c in bible.clashes if c.kind == kind]
        if not group:
            continue
        lines += [f"## {kind.capitalize()} clashes", ""]
        for c in group:
            lines += [f"### {c.subject}", "", f"- Scope: {c.scope.replace('-', ' ')}", f"- Id: `{c.id}`"]
            lines += [f"- Evidence: {f.fact} ({_cite(f)})" for f in c.evidence]
            lines += [f"- Proposed resolution: {c.proposal}", ""]
    open_items: list[tuple[str, str, str]] = []
    for person in bible.characters:
        open_items += [(person.name, o.question, o.proposal) for o in person.open]
    if open_items:
        lines += [f"## Open questions on characters ({len(open_items)})", ""]
        lines += [f"- {who}: {q} Proposed: {p}" for who, q, p in open_items]
        lines.append("")
    marked = 0
    for person in bible.characters:
        marked += sum(1 for v in person.persona_fields().values() if v.startswith(("open:", "proposal:")))
    lines += [f"Persona fields still marked open or proposal across the cast: {marked}.", ""]
    return "\n".join(lines)
