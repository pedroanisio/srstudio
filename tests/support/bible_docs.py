"""Builders of small, valid cast and relationship documents, for the bible tests to break one rule at a time."""

import json
from pathlib import Path


def fact(field: str, quote: str = "Teamwork!", reel: str = "cleaning-fee", kind: str = "line") -> dict:
    return {"fact": f"{field} fact", "field": field, "reel": reel, "kind": kind, "quote": quote}


STATED = {
    "voice.provider": "ElevenLabs",
    "voice.voice": "Charlie",
    "voice.settings": "stability 0.5",
    "voice.pace": "quick",
    "voice.tics": "says teamwork",
    "voice.uses": "teamwork",
    "voice.never_uses": "proposal: never swears",
    "who.age_range": "adult",
    "who.job": "open: what does he do?",
    "who.home": "proposal: a flat",
    "who.normal_day": "open: unknown",
    "who.wants": "to win",
    "who.flaw": "never listens",
    "who.habit": "proposal: pacing",
    "who.pov": "everything is a team",
    "comic.role": "instigator",
    "comic.under_pressure": "cheers",
    "comic.always_gets_them": "the fence",
    "look.palette": "brown",
    "look.outfits": "a badge",
    "look.never_changes": "the ears",
}


def character(slug: str = "rex", **over: object) -> dict:
    backed = [fact(name) for name, text in STATED.items() if not text.startswith(("open:", "proposal:"))]
    base = {
        "slug": slug,
        "name": slug.capitalize(),
        "world": "okayville",
        "status": "canon",
        "kind": "animal",
        "reels": ["cleaning-fee"],
        "look": {
            "drawing": [{"part": "toon-dog", "version": 1}],
            "palette": STATED["look.palette"],
            "outfits": STATED["look.outfits"],
            "never_changes": STATED["look.never_changes"],
        },
        "voice": {k.split(".")[1]: v for k, v in STATED.items() if k.startswith("voice.")},
        "who": {k.split(".")[1]: v for k, v in STATED.items() if k.startswith("who.")},
        "comic": {k.split(".")[1]: v for k, v in STATED.items() if k.startswith("comic.")},
        "canon": backed,
        "never": ["proposal: lie", "proposal: leave", "proposal: whisper"],
        "open": [{"question": "who is his boss?", "proposal": "the cleaner"}],
    }
    base.update(over)
    return base


def pair(a: str = "fern", b: str = "rex", **over: object) -> dict:
    base = {
        "a": a,
        "b": b,
        "relation": "neighbours",
        "how_they_know": "the fence",
        "dynamic": "Fern wins",
        "tension": "the fee",
        "meet": "the rental",
        "history": [fact("relationship")],
        "status": "canon",
        "reels": ["cleaning-fee"],
    }
    base.update(over)
    return base


def cast_document() -> dict:
    return {
        "schema": "1.0.0",
        "version": "1.0.0",
        "characters": [character("rex"), character("fern")],
        "roles": ["narrator"],
        "places": [
            {
                "slug": "rental",
                "name": "The rental",
                "world": "okayville",
                "description": "a holiday rental",
                "found": ["rex", "fern"],
                "cites": [fact("world")],
            }
        ],
        "rules": [{"id": "talk", "rule": "animals talk", "status": "proposal", "cites": []}],
        "clashes": [
            {
                "id": "rex-name",
                "kind": "name",
                "scope": "within-world",
                "subject": "Rex",
                "evidence": [fact("identity")],
                "proposal": "rename the other",
            }
        ],
    }


def pairs_document() -> dict:
    return {"schema": "1.0.0", "version": "1.0.0", "relationships": [pair()]}


def write(folder: Path, cast: dict | None = None, pairs: dict | None = None) -> Path:
    folder.mkdir(exist_ok=True)
    (folder / "cast.json").write_text(json.dumps(cast if cast is not None else cast_document()))
    (folder / "relationships.json").write_text(json.dumps(pairs if pairs is not None else pairs_document()))
    return folder


def placeholder(slug: str) -> dict:
    marked = {k: "open: waiting for the reel" for k in STATED}
    return character(
        slug,
        status="placeholder",
        canon=[],
        look={
            "drawing": [],
            "palette": marked["look.palette"],
            "outfits": marked["look.outfits"],
            "never_changes": marked["look.never_changes"],
        },
        voice={k.split(".")[1]: v for k, v in marked.items() if k.startswith("voice.")},
        who={k.split(".")[1]: v for k, v in marked.items() if k.startswith("who.")},
        comic={k.split(".")[1]: v for k, v in marked.items() if k.startswith("comic.")},
    )
