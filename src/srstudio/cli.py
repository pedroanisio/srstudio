"""``srstudio catalog`` lists the registry, ``srstudio styles`` the styles, ``srstudio fonts add`` pins a Google
Font; ``srstudio build`` runs an episode, ``srstudio usage`` measures which parts the episodes use, ``srstudio lipsync``
scores the mouths over aligned takes, ``srstudio page`` rebuilds the catalog page."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import runpy
import shutil
import sys
from pathlib import Path

from . import catalog_page, fonts, lipsync, registry, usage
from .soundtrack import INK_MOUTH
from .styles import STYLES
from .timeline import Timeline


def main(argv=None):
    parser = argparse.ArgumentParser(prog="srstudio")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cat = sub.add_parser("catalog", help="list registered characters, locations, props and graphics")
    cat.add_argument("--kind", choices=registry.KINDS)
    cat.add_argument("--style", choices=sorted(STYLES), help="only the parts of one style (shared parts included)")
    cat.add_argument("--json", action="store_true")
    cat.add_argument("--plugins", nargs="*", default=(), help="extra modules to import before listing")
    styles = sub.add_parser("styles", help="list the named styles: frame, clock, palettes, parts")
    styles.add_argument("--json", action="store_true")
    font = sub.add_parser("fonts", help="Google Fonts: fetch, verify and pin a face for captions")
    font_sub = font.add_subparsers(dest="fonts_cmd", required=True)
    add = font_sub.add_parser("add", help="install one face into a folder (fonts.lock.json pins it)")
    add.add_argument("family")
    add.add_argument("--weight", type=int, default=400)
    add.add_argument("--italic", action="store_true")
    add.add_argument("--into", type=Path, required=True)
    page = sub.add_parser("page", help="rebuild the catalog page from the episode projects, renders and registry")
    page.add_argument("--base", type=Path, required=True, help="the packages catalog the page starts from")
    page.add_argument("--episodes", type=Path, required=True, help="folder of episode projects")
    page.add_argument("--renders", type=Path, required=True, help="folder holding <slug>.mp4 per project")
    page.add_argument("--out", type=Path, required=True)
    page.add_argument("--cache", type=Path, required=True, help="web encodes and pose renders, reused between runs")
    page.add_argument("--notes", type=Path, help="curated text per episode and style (JSON)")
    page.add_argument("--usage", type=Path, help="the parts each episode uses, from srstudio usage (JSON)")
    page.add_argument("--engine", type=Path, default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    use = sub.add_parser("usage", help="build every episode on a copy and record the registered parts it uses")
    use.add_argument("--episodes", type=Path, required=True, help="folder of episode projects")
    use.add_argument("--packages", type=Path, help="folder of extracted packages (<name>-<version>/project)")
    use.add_argument(
        "--scripts", type=Path, required=True, help="folder of episode scripts (<slug_with_underscores>.py)"
    )
    use.add_argument("--work", type=Path, required=True, help="scratch folder for the copies")
    use.add_argument("--out", type=Path, required=True, help="the usage report (JSON)")
    use.add_argument("--arg", action="append", default=[], metavar="SLUG=OPTION", help="an option for one episode")
    lips = sub.add_parser("lipsync", help="score the shipped and the speech mouth over the takes of timelines")
    lips.add_argument("timelines", nargs="+", type=Path, help="timeline.json files with character timestamps")
    build = sub.add_parser("build", help="run an episode script: python file or module, with its project root")
    build.add_argument("script")
    build.add_argument("root", nargs="?")
    args = parser.parse_args(argv)
    if args.cmd == "catalog":
        for mod in args.plugins:
            importlib.import_module(mod)
        rows = registry.entries(args.kind, args.style)
        if args.json:
            print(json.dumps(registry.catalog(args.style), indent=2, ensure_ascii=False))
            return 0
        width = max((len(e.name) for e in rows), default=4)
        for e in rows:
            eps = ",".join(e.episodes) or "-"
            print(f"{e.kind:<10} {e.style or 'any':<7} {e.name:<{width}}  [{eps}]  {e.summary}")
        return 0
    if args.cmd == "styles":
        if args.json:
            print(json.dumps([s.facts() for s in STYLES.values()], indent=2, ensure_ascii=False))
            return 0
        for s in STYLES.values():
            parts = registry.entries(style=s.slug)
            own = [e for e in parts if e.style == s.slug]
            palettes = ", ".join(p.name for p in s.palettes)
            print(
                f"{s.name:<8} {s.slug:<7} {s.frame:<22} {s.timing:<9} palettes: {palettes:<14} "
                f"parts: {len(own)} own + {len(parts) - len(own)} shared  ({s.summary})"
            )
        return 0
    if args.cmd == "fonts":
        try:
            got = fonts.install(fonts.GoogleFont(args.family, args.weight, args.italic), args.into)
        except fonts.FontError as exc:
            print(f"srstudio fonts: {exc}", file=sys.stderr)
            return 2
        style = " italic" if got.italic else ""
        print(f"{got.path}  {got.family} {got.weight}{style}  {got.license}  sha256 {got.sha256}")
        return 0
    if args.cmd == "page":
        try:
            notes = catalog_page.load_notes(args.notes) if args.notes else None
            measured = usage.Report.read(args.usage) if args.usage else None
            cards = catalog_page.build(
                base=args.base,
                episodes=args.episodes,
                renders=args.renders,
                out=args.out,
                cache=args.cache,
                engine=args.engine or Path("scene-render"),
                notes=notes,
                usage=measured,
            )
        except (catalog_page.CatalogError, usage.UsageError) as exc:
            print(f"srstudio page: {exc}", file=sys.stderr)
            return 2
        print(f"{args.out}  {len(cards)} episodes: {', '.join(c.slug for c in cards)}")
        return 0
    if args.cmd == "usage":
        extra: dict[str, list[str]] = {}
        for item in args.arg:
            slug, sep, option = item.partition("=")
            if not sep or not slug or not option:
                parser.error(f"--arg {item!r}: expected SLUG=OPTION")
            extra.setdefault(slug, []).append(option)
        runs, missing = usage.discover(args.episodes, args.packages, args.scripts, extra)
        try:
            report = usage.measure(runs, args.work, missing)
        except usage.UsageError as exc:
            print(f"srstudio usage: {exc}", file=sys.stderr)
            return 2
        report.write(args.out)
        for kind in ("character", "location", "prop"):
            unused = report.unused(kind)
            print(
                f"{kind}: {len(registry.entries(kind)) - len(unused)} used, {len(unused)} unused: {', '.join(unused)}"
            )
        if missing:
            print(f"not measured (no script): {', '.join(missing)}")
        return 0
    if args.cmd == "lipsync":
        try:
            takes = [
                (take.phones, take.duration, take.mood)
                for path in args.timelines
                for take in Timeline.load(path).takes
                if take.phones
            ]
            scores = {
                name: lipsync.score(takes, style)
                for name, style in (("INK_MOUTH", INK_MOUTH), ("SPEECH_MOUTH", lipsync.SPEECH_MOUTH))
            }
        except (OSError, ValueError, KeyError) as exc:
            print(f"srstudio lipsync: {exc}", file=sys.stderr)
            return 2
        print(f"{len(takes)} takes")
        for name, result in scores.items():
            print(f"{name:<13} {result.summary()}")
        return 0
    if args.cmd == "build":
        script = args.script
        if args.root:
            sys.argv = [script, args.root]
        if script.endswith(".py"):
            sys.path.insert(0, str(Path(script).resolve().parent))  # sibling helpers such as episodes/_common.py
            runpy.run_path(script, run_name="__main__")
        else:
            runpy.run_module(script, run_name="__main__")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
