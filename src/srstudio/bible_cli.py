"""``srstudio bible``: recount the cast, verify the bible against its reels, check a reel or a brief, write the folder.

Every subcommand is plain code and calls no model (ADR 0069). The exit status is 0 when nothing is wrong, 1 when a
check or a verification finds a fault, 2 when an input cannot be read.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from . import bible, bible_build, bible_check, bible_inventory, registry, releases
from .errors import SrstudioError

__all__ = ["add_parser", "run"]

REPO = Path(__file__).resolve().parent.parent.parent


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


def add_parser(sub: argparse._SubParsersAction) -> None:
    top = sub.add_parser("bible", help="the cast bible: inventory, verify, check a reel or a brief, render the folder")
    top.add_argument("--library", type=Path, default=REPO / "bible", help="the folder holding cast.json")
    top.add_argument("--releases", type=Path, default=REPO / "episodes" / "posts", help="one release file per reel")
    top.add_argument("--episodes", type=Path, default=_env_path("SRSTUDIO_EPISODES"), help="the episode projects")
    top.add_argument("--outbox", type=Path, help="outbox.json, the manifest of what is published")
    actions = top.add_subparsers(dest="action", required=True)
    inv = actions.add_parser("inventory", help="count who is on 2 or more published reels")
    inv.add_argument("--threshold", type=int, default=bible_inventory.THRESHOLD)
    actions.add_parser("verify", help="check every fact of the bible against the reel it cites")
    check = actions.add_parser("check", help="check the unpublished releases and any brief against the bible")
    check.add_argument("--brief", type=Path, action="append", default=[], help="a brief or script with a Cast: line")
    check.add_argument("--only", nargs="+", default=[], help="these release slugs alone")
    render = actions.add_parser("render", help="write the bible folder: sheets, pictures, diagram and pages")
    render.add_argument("out", type=Path)
    render.add_argument("--model", required=True, help="the model that wrote the pages, for their frontmatter")
    render.add_argument("--fonts", type=Path, default=_env_path("SRSTUDIO_FONTS"))
    render.add_argument("--engine", type=Path, default=_env_path("SRSTUDIO_ENGINE"))
    render.add_argument("--cache", type=Path, required=True, help="a copy of the catalog cache (specimens are drawn)")
    render.add_argument("--work", type=Path, required=True, help="scratch folder for the diagram")


def _outbox(args: argparse.Namespace) -> Path:
    if args.outbox:
        return args.outbox
    renders = _env_path("SRSTUDIO_RENDERS")
    if renders is None:
        raise bible_inventory.InventoryError("set --outbox, or SRSTUDIO_RENDERS (the manifest sits beside it)")
    return renders.parent / "outbox" / "outbox.json"


def _episodes(args: argparse.Namespace) -> Path:
    if args.episodes is None:
        raise bible_inventory.InventoryError("set --episodes or SRSTUDIO_EPISODES")
    return args.episodes


def run(args: argparse.Namespace) -> int:
    try:
        return _run(args)
    except SrstudioError as exc:
        print(f"srstudio bible {args.action}: {exc}", file=sys.stderr)
        return 2


def _run(args: argparse.Namespace) -> int:
    found = releases.load(args.releases)
    episodes = _episodes(args)
    published = bible_inventory.published(_outbox(args))
    characters = {e.name for e in registry.entries("character")}
    if args.action == "inventory":
        reels = bible_inventory.collect(
            found,
            published,
            episodes,
            characters=characters,
            vocabulary=bible_inventory.vocabulary(found, published, episodes),
        )
        listed = bible_inventory.candidates(reels, threshold=args.threshold)
        recurring = [c for c in listed if c.recurring]
        print(f"{len(reels)} published reels, {len(listed)} names, {len(recurring)} on {args.threshold} or more")
        for c in recurring:
            clash = bible_inventory.clashes(c)
            print(f"{c.name}\t{c.world}\t{len(c.reels)}" + (f"\t{' | '.join(clash)}" if clash else ""))
        return 0
    loaded = bible.load(args.library)
    if args.action == "verify":
        problems = bible.verify(loaded, found, published, episodes, characters=characters)
        for line in problems:
            print(line)
        seen = sum(1 for _, f in loaded.facts() if f.kind == "seen")
        print(f"{len(loaded.facts())} facts, {len(problems)} do not hold, {seen} rest on a frame seen, not checked")
        return 1 if problems else 0
    if args.action == "check":
        pending = {
            s: r for s, r in found.items() if s not in published and (not args.only or s in args.only)
        }  # a published reel is frozen: never checked
        findings = {
            s: bible_check.check_release(loaded, r, episodes, characters=characters) for s, r in pending.items()
        }
        for brief in args.brief:
            try:
                text = brief.read_text(encoding="utf-8")
            except OSError as exc:
                print(f"srstudio bible check: {brief}: {exc}", file=sys.stderr)
                return 2
            findings[str(brief)] = bible_check.check_brief(loaded, text, where=str(brief))
        for group in findings.values():
            for finding in group:
                print(finding)
        total = sum(len(g) for g in findings.values())
        print(f"{len(pending)} unpublished releases and {len(args.brief)} briefs checked, {total} findings")
        return 1 if total else 0
    return _render(args, loaded, found)


def _render(args: argparse.Namespace, loaded: bible.Bible, found: dict[str, releases.Release]) -> int:
    from .cast_card import Lettering

    engine = args.engine or (Path(p) if (p := shutil.which("scene-render")) else None)
    if args.fonts is None or engine is None:
        print("srstudio bible render: set --fonts and --engine, or SRSTUDIO_FONTS and SRSTUDIO_ENGINE", file=sys.stderr)
        return 2
    order = bible_inventory.added_order(args.releases.parent, found)
    shown = bible_build.specimens_of(engine, args.cache, _episodes(args))
    left = bible_build.build(
        args.library,
        args.out,
        loaded,
        model=args.model,
        order=order,
        specimens=shown,
        faces=Lettering.installed(args.fonts),
        engine=engine,
        work=args.work,
    )
    print(f"wrote {args.out}; crossings left: " + ", ".join(f"{w} {n}" for w, n in sorted(left.items())))
    return 0
