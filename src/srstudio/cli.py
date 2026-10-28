"""``srstudio catalog`` lists the registry, ``srstudio styles`` the styles, ``srstudio fonts add`` pins a Google
Font; ``srstudio build`` runs an episode."""

from __future__ import annotations

import argparse
import importlib
import json
import runpy
import sys
from pathlib import Path

from . import fonts, registry
from .styles import STYLES


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
