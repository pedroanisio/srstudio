"""``srstudio catalog`` lists the registry, ``srstudio styles`` the styles, ``srstudio fonts add`` pins a Google
Font; ``srstudio build`` runs an episode, ``srstudio usage`` measures which parts the episodes use, ``srstudio lipsync``
scores the mouths over aligned takes, ``srstudio craft`` measures camera moves and pauses, ``srstudio overlap`` finds
lines another episode already said, ``srstudio page`` rebuilds the catalog site, ``srstudio serve`` serves it,
``srstudio parts`` lists the part versions and checks the pins, ``srstudio enhance`` shows the auto-enhance mode and
ledger, and ``srstudio strict`` lists the reels shipped with findings proven false."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import runpy
import shutil
import sys
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import NoReturn

from sr_core.scene import SchemaValueError

from . import (
    auto_enhance,
    bible_cli,
    catalog_page,
    catalog_server,
    catalog_specimens,
    catalog_versions,
    craft,
    fonts,
    frames,
    interview,
    lip_proof,
    lipsync,
    music,
    outbox,
    overlap,
    parts,
    proof,
    registry,
    releases,
    show,
    show_numbers,
    strict_gate,
    usage,
)
from .episode import SceneCheckError
from .errors import SrstudioError, diagnostic
from .social import MANIFEST, DeliveryError, read_manifest
from .soundtrack import INK_MOUTH
from .styles import STYLES
from .takes import refuse_rehearsal as refuse_takes_rehearsal
from .thumbnail import ShowCover
from .timeline import Timeline


def _error(command: str, error: BaseException, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(diagnostic(error, command=command), allow_nan=False, ensure_ascii=False), file=sys.stderr)
    else:
        print(f'srstudio {command}: {error}', file=sys.stderr)


def _load_plugins(modules, command: str, json_output: bool = False) -> bool:
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError as exc:
            _error(
                command,
                SrstudioError(
                    f'cannot import plugin {module!r}: {exc}',
                    code='plugin.import',
                    path='plugins',
                    actual=module,
                    remedy='Install the plugin or remove it from --plugins.',
                ),
                json_output,
            )
            return False
        except SrstudioError as exc:
            _error(command, exc, json_output)
            return False
    return True


def _version_text(info: registry.PartVersionDetails | None) -> str:
    if info is None:
        return ""
    default = info["default_name"] or "none approved"
    status = info["status"]
    record = f", record: {info['record_status']}" if status == "unverified" else ""
    default_status = f" ({info['default_status']})" if info["default_status"] in ("unverified", "unavailable") else ""
    return f"version {info['version']} ({status}{record}); default: {default}{default_status}"


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)

    class Parser(argparse.ArgumentParser):
        def error(self, message: str) -> NoReturn:
            if '--json' in arguments:
                _error(
                    self.prog.removeprefix('srstudio '),
                    SrstudioError(
                        message,
                        code='cli.arguments',
                        path='argv',
                        remedy=f'Check the arguments with {self.prog} --help.',
                    ),
                    True,
                )
                self.exit(2)
            super().error(message)

    parser = Parser(prog="srstudio")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cat = sub.add_parser(
        "catalog",
        help="list registered characters, locations, props and graphics",
        epilog="Use srstudio inspect KIND NAME for a part's signature, callback slots and usage examples.",
    )
    cat.add_argument("--kind", choices=registry.KINDS)
    cat.add_argument("--style", choices=sorted(STYLES), help="only the parts of one style (shared parts included)")
    cat.add_argument("--json", action="store_true")
    cat.add_argument("--plugins", nargs="*", default=(), help="extra modules to import before listing")
    catalog_mode = cat.add_mutually_exclusive_group()
    catalog_mode.add_argument(
        "--usage", type=Path, help="a report from srstudio usage: show the episodes each part is used in"
    )
    catalog_mode.add_argument(
        '--contract-coverage', action='store_true', help='report declared semantics and argument shapes by kind'
    )
    detail = sub.add_parser("inspect", help="show a part's signature, callback slots, documentation and usage")
    detail.add_argument("kind", choices=registry.KINDS)
    detail.add_argument("name")
    detail.add_argument("--json", action="store_true")
    detail.add_argument("--plugins", nargs="*", default=(), help="extra modules to import before inspection")
    number = sub.add_parser(
        "number", help="the show's numbers: set the count, claim or release a reel's number, list (ADR 0074, ADR 0080)"
    )
    number.add_argument("action", choices=("list", "base", "claim", "release"))
    number.add_argument("value", nargs="?", help="base: the count; claim, release: the reel's slug")
    number.add_argument("--series", default="", help="the series, as Saga")
    number.add_argument("--brief", default="", help="claim: the brief the reel was made to, as send-v1")
    number.add_argument("--post-by", default="", help="claim: the day a timely reel is due, as 2026-11-02")
    number.add_argument("--not-before", default="", help="claim: the first day a timely reel may post, as 2026-11-20")
    number.add_argument("--ledger", type=Path, default=_ledger_default(), help="the ledger file")
    strict = sub.add_parser("strict", help="list the reels shipped with findings proven false (ADR 0078)")
    strict.add_argument("--scripts", type=Path, default=_scripts_default(), help="the episodes folder")
    strict.add_argument("--delivery", type=Path, default=_delivery_default(), help="the delivery folder")
    enhance = sub.add_parser(
        "enhance", help="the auto-enhance mode, its ledger, its kinds and a check of this branch's claims (ADR 0056)"
    )
    enhance.add_argument("action", nargs="?", choices=("status", "kinds", "check", "on", "off"), default="status")
    enhance.add_argument("--scripts", type=Path, default=_scripts_default(), help="folder of episode scripts")
    versions = sub.add_parser("parts", help="list each part's versions, print a digest, check the pins")
    versions.add_argument("--json", action="store_true")
    versions.add_argument("--digest", metavar="NAME[@N]", help="the digest of a drawing, for its version record")
    versions.add_argument("--usage", type=Path, help="a report from srstudio usage: is every measured part pinned?")
    versions.add_argument("--refused", action="store_true", help="the parts with no drawing of their own, and why")
    versions.add_argument("--scripts", type=Path, default=_scripts_default(), help="folder of episode scripts")
    versions.add_argument(
        "--episodes",
        type=Path,
        default=Path(os.environ.get("SRSTUDIO_EPISODES") or "generated/episodes"),
        help="folder of projects, for a part's font and traced data",
    )
    lip = sub.add_parser("lip-proof", help="the mid-word instants of a recorded reel, and their frames of its master")
    lip.add_argument("project", type=Path)
    lip.add_argument("--count", type=int, default=lip_proof.COUNT, help="how many instants, spread over the reel")
    lip.add_argument("--master", type=Path, help="the final mp4; with --out, pull each instant's frame")
    lip.add_argument("--out", type=Path, help="folder for the frames")
    lip.add_argument("--crop", help="ffmpeg crop of each frame, w:h:x:y")
    measured = sub.add_parser("proof", help="a master's measures (ffprobe, ebur128) and a sheet of frames to look at")
    measured.add_argument("video", type=Path)
    measured.add_argument("--at", type=float, action="append", default=[], help="a moment to look at, in seconds")
    measured.add_argument("--sheet", type=Path, help="write the frames, in one row, to this image")
    measured.add_argument("--arm", choices=("a", "b"), help="fail unless the master shows this sp-hook_motion arm")
    measured.add_argument("--json", action="store_true")
    beat = sub.add_parser("beat", help="measure a recorded track's tempo and where its bars open")
    beat.add_argument("audio", type=Path, help="any file ffmpeg reads; the bar line needs at least eight bars")
    beat.add_argument("--seconds", type=float, help="measure only the first seconds")
    beat.add_argument("--beats-per-bar", type=int, default=4)
    beat.add_argument("--near", type=float, default=120.0, help="the tempo to lean toward: settles double or half time")
    beat.add_argument("--json", action="store_true")
    split = sub.add_parser("arms", help="how an A/B test's releases split, and what keeps the split from being fair")
    split.add_argument("test", choices=releases.TESTS)
    split.add_argument("--order", type=Path, help="the delivery order: a file of slugs, one a line")
    split.add_argument("--share", type=float, default=0.5, help="the part of the test on arm a, if not half")
    split.add_argument("--scripts", type=Path, default=_scripts_default(), help="folder of episode scripts")
    styles = sub.add_parser("styles", help="list the named styles: frame, clock, palettes, parts")
    styles.add_argument("--json", action="store_true")
    font = sub.add_parser("fonts", help="Google Fonts: fetch, verify and pin a face for captions")
    font_sub = font.add_subparsers(dest="fonts_cmd", required=True)
    add = font_sub.add_parser("add", help="install one face into a folder (fonts.lock.json pins it)")
    add.add_argument("family")
    add.add_argument("--weight", type=int, default=400)
    add.add_argument("--italic", action="store_true")
    add.add_argument("--into", type=Path, required=True)
    page = sub.add_parser("page", help="rebuild the catalog site from the episode projects, renders and registry")
    page.add_argument("--base", type=Path, required=True, help="the packages catalog the page starts from")
    page.add_argument("--episodes", type=Path, required=True, help="folder of episode projects")
    page.add_argument("--renders", type=Path, required=True, help="folder holding <slug>.mp4 per project")
    page.add_argument("--site", type=Path, required=True, help="the folder to write: index.html and media/")
    page.add_argument("--cache", type=Path, required=True, help="web encodes and pose renders, reused between runs")
    page.add_argument("--notes", type=Path, help="curated text per episode and style (JSON)")
    page.add_argument("--usage", type=Path, help="the parts each episode uses, from srstudio usage (JSON)")
    page.add_argument("--releases", type=Path, help="folder of release files: which reels pin which version")
    page.add_argument(
        "--proof-root", type=Path, default=Path(), help="the folder that version records' proof paths start from"
    )
    page.add_argument("--engine", type=Path, default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    packages = os.environ.get("SRSTUDIO_PACKAGES")
    page.add_argument(
        "--packages", type=Path, default=packages, required=not packages, help="folder of <name>-<version> packages"
    )
    bible_cli.add_parser(sub)
    cards = sub.add_parser("cards", help="write the cast's story cards, drawn through the engine")
    cards.add_argument("out", type=Path, help="the folder the <name>.png files go in")
    cards.add_argument("--fonts", type=Path, default=os.environ.get("SRSTUDIO_FONTS"), help="the pinned fonts folder")
    cards.add_argument("--engine", type=Path, default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render"))
    cards.add_argument("--only", nargs="+", default=[], help="these names alone, lower-case")
    web = sub.add_parser("serve", help="serve a catalog site, read-only, with the byte ranges video seeking needs")
    web.add_argument("site", type=Path, help="the folder srstudio page --site wrote")
    web.add_argument("--host", default=catalog_server.HOST, help="there is no authentication: keep it on loopback")
    web.add_argument("--port", type=int, default=catalog_server.PORT)
    use = sub.add_parser("usage", help="build every episode on a copy and record the registered parts it uses")
    use.add_argument("--episodes", type=Path, required=True, help="folder of episode projects")
    use.add_argument("--packages", type=Path, help="folder of extracted packages (<name>-<version>/project)")
    use.add_argument(
        "--scripts", type=Path, required=True, help="folder of episode scripts (<slug_with_underscores>.py)"
    )
    use.add_argument("--work", type=Path, required=True, help="scratch folder for the copies")
    use.add_argument("--out", type=Path, required=True, help="the usage report (JSON)")
    use.add_argument("--arg", action="append", default=[], metavar="SLUG=OPTION", help="an option for one episode")
    use.add_argument(
        "--skip", action="append", default=[], metavar="SLUG", help="a project not to build (still in progress)"
    )
    lips = sub.add_parser("lipsync", help="score the shipped and the speech mouth over the takes of timelines")
    lips.add_argument("timelines", nargs="+", type=Path, help="timeline.json files with character timestamps")
    framed = sub.add_parser("frames", help="list, or render at full size, the frames to review in a voiced project")
    framed.add_argument("project", type=Path, help="the project folder (<slug>/voiced/beats.json)")
    framed.add_argument("--payoff", type=float, help="the payoff's second, else the last beat with an event")
    framed.add_argument("--out", type=Path, help="render each frame into this folder")
    framed.add_argument(
        "--engine", type=Path, default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    )
    crafted = sub.add_parser("craft", help="measure the camera moves and the pauses between lines of episode projects")
    crafted.add_argument("projects", nargs="+", type=Path, help="episode project folders (<slug>/<slug>.scene.xml)")
    crafted.add_argument("--renders", type=Path, help="folder of renders (<slug>.mp4): measure the sound in each pause")
    crafted.add_argument("--threshold", type=float, default=craft.PAUSE, help="seconds between lines that make a pause")
    crafted.add_argument("--json", action="store_true", help="print the reports as JSON")
    shared = sub.add_parser("overlap", help="find the lines of an episode that other episodes already said")
    shared.add_argument("project", type=Path, help="the episode project folder (its recorded script)")
    shared.add_argument("--episodes", type=Path, required=True, help="the folder of episode projects to compare with")
    shared.add_argument("--least", type=int, default=overlap.LEAST, help="words in a row that count as a repeat")
    build = sub.add_parser(
        "build", help="run an episode script: an episode's slug, a python file or a module, with its project root"
    )
    build.add_argument("--scripts", type=Path, default=_scripts_default(), help="folder of episode scripts")
    build.add_argument("script")
    build.add_argument("root", nargs="?")
    build.add_argument("options", nargs=argparse.REMAINDER, help="passed to the episode (--voice, ...)")
    record = sub.add_parser("record", help="run an episode's recording script (<builder>_audio.py) by its slug")
    record.add_argument("--scripts", type=Path, default=_scripts_default(), help="folder of episode scripts")
    record.add_argument("slug")
    record.add_argument("options", nargs=argparse.REMAINDER, help="the project and the recorder's own options")
    args = parser.parse_args(arguments)
    if args.cmd == "inspect":
        if not _load_plugins(args.plugins, "inspect", getattr(args, "json", False)):
            return 2
        try:
            info = registry.describe(args.kind, args.name)
        except (registry.RegistryError, registry.NotRegisteredError) as exc:
            _error("inspect", exc, getattr(args, "json", False))
            return 2
        if args.json:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            return 0
        print(f"{info['kind']} {info['name']} ({info['style'] or 'any'}): {info['summary']}")
        if version := _version_text(info["part_version"]):
            print(f"{'Character' if info['kind'] == 'character' else 'Part'}: {version}")
        print(f"Module: {info['module']}")
        print(f"Signature: {info['signature']}")
        print(f"Callback slots (receive the parent group): {', '.join(info['slots']) or 'none'}")
        print(f"Call template: {info['call_template']}")
        print(f"  part = srstudio.get({info['kind']!r}, {info['name']!r}); supply the named arguments above.")
        if info['documentation']:
            print(f"\n{info['documentation']}")
        for example in info['examples']:
            print(f"\nExample (ep is an existing Episode):\n{example}")
        return 0
    if args.cmd == "number":
        return _number(args)
    if args.cmd == "strict":
        return _strict(args)
    if args.cmd == "enhance":
        return _enhance(args.action, args.scripts.resolve().parent)
    if args.cmd == "lip-proof":
        return _lip_proof(args)
    if args.cmd == "beat":
        return _beat(args)
    if args.cmd == "proof":
        return _proof(args)
    if args.cmd == "arms":
        return _arms(args)
    if args.cmd == "parts":
        return _parts(args)
    if args.cmd == "catalog":
        if not _load_plugins(args.plugins, "catalog", getattr(args, "json", False)):
            return 2
        if args.contract_coverage:
            coverage = registry.contract_coverage(args.style, kind=args.kind)
            if args.json:
                print(json.dumps(coverage, indent=2, ensure_ascii=False))
            else:
                for kind, counts in coverage['kinds'].items():
                    print(
                        f"{kind}: {counts['explicit_contracts']}/{counts['registered']} explicit contracts; "
                        f"{counts['shape_complete']} complete argument shapes; "
                        f"{counts['with_units']} with units, {counts['with_clocks']} with clocks, "
                        f"{counts['with_anchors']} with anchors"
                    )
                print(coverage['qualification'])
            return 0
        try:
            measured = usage.Report.read(args.usage) if args.usage else None
        except usage.UsageError as exc:
            _error("catalog", exc, getattr(args, "json", False))
            return 2
        rows = registry.entries(args.kind, args.style)
        if args.json:
            data = registry.catalog(args.style, kind=args.kind)
            if measured is not None:
                data = [row | {"episodes": measured.used_by(row["name"])} for row in data]
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return 0
        width = max((len(e.name) for e in rows), default=4)
        for e in rows:
            eps = f"  [{','.join(measured.used_by(e.name)) or '-'}]" if measured is not None else ""
            version = _version_text(registry._part_version(e))
            suffix = f"  ({version})" if version else ""
            print(f"{e.kind:<10} {e.style or 'any':<7} {e.name:<{width}}{eps}  {e.summary}{suffix}")
        return 0
    if args.cmd == "styles":
        if args.json:
            print(json.dumps([s.facts() for s in STYLES.values()], indent=2, ensure_ascii=False))
            return 0
        for s in STYLES.values():
            entries = registry.entries(style=s.slug)
            own = [e for e in entries if e.style == s.slug]
            palettes = ", ".join(p.name for p in s.palettes)
            print(
                f"{s.name:<8} {s.slug:<7} {s.frame:<22} {s.timing:<9} palettes: {palettes:<14} "
                f"parts: {len(own)} own + {len(entries) - len(own)} shared  ({s.summary})"
            )
        return 0
    if args.cmd == "fonts":
        try:
            got = fonts.install(fonts.GoogleFont(args.family, args.weight, args.italic), args.into)
        except fonts.FontError as exc:
            _error("fonts", exc, getattr(args, "json", False))
            return 2
        style = " italic" if got.italic else ""
        print(f"{got.path}  {got.family} {got.weight}{style}  {got.license}  sha256 {got.sha256}")
        return 0
    if args.cmd == "bible":
        return bible_cli.run(args)
    if args.cmd == "cards":
        return _cards(args)
    if args.cmd == "page":
        try:
            notes = catalog_page.load_notes(args.notes) if args.notes else None
            measured = usage.Report.read(args.usage) if args.usage else None
            pins = catalog_versions.read_pins(args.releases) if args.releases else None
            built = catalog_page.build(
                base=args.base,
                episodes=args.episodes,
                renders=args.renders,
                site=args.site,
                cache=args.cache,
                engine=args.engine or Path("scene-render"),
                packages=args.packages,
                notes=notes,
                usage=measured,
                pins=pins,
                proof_root=args.proof_root,
            )
        except (catalog_page.CatalogError, usage.UsageError) as exc:
            _error("page", exc, getattr(args, "json", False))
            return 2
        print(f"{args.site}  {len(built.cards)} episodes: {', '.join(c.slug for c in built.cards)}")
        drawn, made = len(built.pictures.stills), built.pictures.made
        print(f"{drawn} specimens: {made} rendered, {drawn - made} cached, {len(built.pictures.refused)} refused")
        return 0
    if args.cmd == "serve":
        try:
            catalog_server.serve(args.site, args.host, args.port)
        except (catalog_server.ServeError, OSError) as exc:
            _error("serve", exc, getattr(args, "json", False))
            return 2
        return 0
    if args.cmd == "usage":
        extra: dict[str, list[str]] = {}
        for item in args.arg:
            slug, sep, option = item.partition("=")
            if not sep or not slug or not option:
                parser.error(f"--arg {item!r}: expected SLUG=OPTION")
            extra.setdefault(slug, []).append(option)
        try:
            runs, missing = usage.discover(args.episodes, args.packages, args.scripts, extra, skip=args.skip)
            report = usage.measure(runs, args.work, missing)
        except usage.UsageError as exc:
            _error("usage", exc, getattr(args, "json", False))
            return 2
        report.write(args.out)
        for kind in ("character", "location", "prop"):
            unused = report.unused(kind)
            print(
                f"{kind}: {len(registry.entries(kind)) - len(unused)} used, {len(unused)} unused: {', '.join(unused)}"
            )
        no_script = [slug for slug in missing if slug not in args.skip]
        if no_script:
            print(f"not measured (no script): {', '.join(no_script)}")
        if args.skip:
            print(f"not measured (skipped): {', '.join(sorted(args.skip))}")
        for slug, reason in report.failures.items():
            print(f"not measured (failed): {slug}: {reason}")
        return 1 if report.failures else 0  # the report is written; a failed build is named, never silent
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
            _error("lipsync", exc, getattr(args, "json", False))
            return 2
        print(f"{len(takes)} takes")
        for name, result in scores.items():
            print(f"{name:<13} {result.summary()}")
        return 0
    if args.cmd == "frames":
        try:
            listed = frames.project_frames(args.project, args.payoff)
            for frame in listed:
                print(f"{frame.at:8.2f}  {frame.why}")
            if args.out is not None:
                if args.engine is None:
                    raise frames.FrameError("set --engine or SRSTUDIO_ENGINE to render the frames")
                scene = args.project / f"{args.project.name}.scene.xml"
                print(f"{len(frames.at_size(scene, listed, args.out, args.engine))} frames in {args.out}")
        except (frames.FrameError, SrstudioError) as exc:
            _error("frames", exc, getattr(args, "json", False))
            return 2
        return 0
    if args.cmd == "craft":
        try:
            reports = []
            for project in args.projects:
                render = args.renders / f"{project.name}.mp4" if args.renders else None
                video = render if render is not None and render.is_file() else None
                reports.append(craft.measure(project, video=video, threshold=args.threshold))
        except (craft.CraftError, ValueError) as exc:
            _error("craft", exc, getattr(args, "json", False))
            return 2
        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2))
            return 0
        for r in reports:
            print(f"{r.slug}: {len(r.moves)} moves ({sum(m.camera for m in r.moves)} camera), {len(r.pauses)} pauses")
            same: dict[tuple, list[str]] = {}  # groups that make one move together print as one line
            for m in r.moves:
                same.setdefault((m.kind, m.ratio, m.start, m.end, m.camera), []).append(m.group)
            for (kind, ratio, start, end, camera), groups in same.items():
                where = groups[0] + (f" +{len(groups) - 1} more" if len(groups) > 1 else "")
                print(f"  {kind:<8} x{ratio:<5} {start:6.2f}–{end:<6.2f} {where}{' (camera)' if camera else ''}")
            for p in r.pauses:
                level = (
                    "unmeasured" if p.level_db is None else f"{p.level_db:.1f} dB, {'quiet' if p.quiet else 'filled'}"
                )
                print(f"  pause {p.start:.2f}–{p.end:.2f}  {p.end - p.start:.2f} s  {level}")
            for line, lost in r.clipped:
                print(f"  clipped line {line}: {lost:.2f} s of speech lost")
            for at, gap in r.crowded:
                print(f"  crowded line at {at:.2f}: {gap:.2f} s after the line before")
            for t in r.short:
                print(f"  short text at {t.start:.2f}: {t.text!r} for {t.seconds:.3f} s, under {craft.MIN_DISPLAY} s")
            for start, end in r.opening:
                print(f"  opening silence {start:.2f}–{end:.2f}  {end - start:.2f} s")
            if not r.opening:
                print(f"  opening: no silence of {craft.OPENING_LIMIT:g} s or more in the first {craft.OPENING:g} s")
            for f in r.flashes:
                print(f"  flash {f.start:.2f}–{f.end:.2f}  {f.share:.0%} of the picture at worst")
            for h in r.holds:
                print(f"  hold {h.start:.2f}–{h.end:.2f}  {h.end - h.start:.2f} s")
            if r.hardware:
                print(f"  two passes asked, one taken by {r.hardware}: encode again with --hw software")
        return 0
    if args.cmd == "overlap":
        try:
            lines = overlap.read_lines(overlap.project_script(args.project))
            found = overlap.overlaps(lines, overlap.scripts(args.episodes, skip=args.project.name), args.least)
        except overlap.OverlapError as exc:
            _error("overlap", exc, getattr(args, "json", False))
            return 2
        for hit in found:
            print(f"{hit.slug}: {hit.words} ({hit.line!r} / {hit.other!r})")
        if not found:
            print(f"no overlap of {args.least} words or more")
        return 0
    if args.cmd == "record":
        try:
            recorder = _episode_script(args.scripts, args.slug, "_audio")
        except releases.ReleaseError as exc:
            _error("record", exc, getattr(args, "json", False))
            return 2
        if recorder is None:
            print(f"srstudio record: no episode {args.slug!r} in {args.scripts}", file=sys.stderr)
            return 2
        return _run_script(recorder, [str(recorder), *args.options])
    if args.cmd == "build":
        script = args.script
        try:
            episode = _episode_script(args.scripts, script, "")
        except releases.ReleaseError as exc:
            _error("build", exc, getattr(args, "json", False))
            return 2
        number = None
        if episode is None and "-" in script and not script.endswith(".py"):
            print(f"srstudio build: no episode {script!r} in {args.scripts}", file=sys.stderr)
            return 2
        if episode is not None:
            number = _show_number(args.scripts, script)
            script = str(episode)
        sys.argv = [script, *([args.root] if args.root else []), *args.options]  # never srstudio's own words
        try:
            if args.root and "--voice" in args.options:
                interview.refuse_rehearsal(Path(args.root))
                refuse_takes_rehearsal(Path(args.root))
            with usage.recorded(Path(args.root)) if args.root else nullcontext(), show.stamping(number):
                if script.endswith(".py"):
                    sys.path.insert(
                        0, str(Path(script).resolve().parent)
                    )  # sibling helpers such as episodes/_common.py
                    runpy.run_path(script, run_name="__main__")
                else:
                    runpy.run_module(script, run_name="__main__")
        except (SceneCheckError, parts.PartError) as exc:
            print(exc, file=sys.stderr)
            return 1
        except (SrstudioError, SchemaValueError, OSError) as exc:
            _error("build", exc, getattr(args, "json", False))
            return 1
        return 0


def _arms(args: argparse.Namespace) -> int:
    order = args.order.read_text().split() if args.order else []
    try:
        loaded = releases.load(args.scripts / "posts")
        problems = releases.arm_problems(loaded, args.test, order, args.share)
    except releases.ReleaseError as exc:
        _error("arms", exc, getattr(args, "json", False))
        return 1
    for arm, slugs in releases.arms(loaded, args.test).items():
        print(f"{arm} {len(slugs):>3}  {' '.join(slugs)}")
    for problem in problems:
        print(f"srstudio arms: {problem}", file=sys.stderr)
    return 1 if problems else 0


def _beat(args: argparse.Namespace) -> int:
    try:
        read = music.reading(args.audio, seconds=args.seconds, beats_per_bar=args.beats_per_bar, near=args.near)
    except music.MusicError as exc:
        _error("beat", exc, args.json)
        return 1
    groove = read.groove
    if args.json:
        print(json.dumps({**asdict(groove), "bars": round(read.bars, 2), "sure": read.sure}))
    else:
        print(f"{groove.bpm:g} BPM, {groove.beats_per_bar} beats to the bar, a bar opens at {groove.offset:g} s")
    if not read.sure:
        print(f"srstudio beat: only {read.bars:.1f} bars heard, the bars may open on another beat", file=sys.stderr)
    return 0


def _proof(args: argparse.Namespace) -> int:
    try:
        made = proof.report(args.video, args.at, args.sheet, arm=args.arm)
    except proof.ProofError as exc:
        _error("proof", exc, getattr(args, "json", False))
        return 1
    if args.json:
        print(json.dumps(made))
    else:
        print(" ".join(f"{k}={v}" for k, v in made.items()))
    return 0


def _lip_proof(args: argparse.Namespace) -> int:
    try:
        picks = lip_proof.instants(args.project, count=args.count)
        made = lip_proof.frames(picks, args.master, args.out, crop=args.crop) if args.master and args.out else []
    except lip_proof.LipProofError as exc:
        _error("lip-proof", exc, getattr(args, "json", False))
        return 2
    for pick in picks:
        flag = "  <- vowel on a shut mouth" if pick.suspect else ""
        print(f"{pick.at:7.3f}  {pick.who:10} {pick.word:14} {pick.letter}  {pick.shown}{flag}")
    shut = sum(pick.suspect for pick in picks)
    print(f"{len(picks)} instants, {shut} vowel{'' if shut == 1 else 's'} on a shut mouth, {len(made)} frames written")
    return 0


def _parts(args: argparse.Namespace) -> int:
    try:
        if args.digest:
            name, _, number = args.digest.partition("@")
            version = parts.get(name).version(int(number or 1))
            print(catalog_specimens.digest(name, version.number, args.episodes))
            return 0
        if args.usage:
            measured = usage.Report.read(args.usage)
            drift = measured.pin_drift(releases.load(args.scripts / "posts"))
            for line in drift:
                print(line)
            verdict = f"{len(drift)} pins off" if drift else "every part pinned"
            print(f"{len(measured.episodes)} episodes measured, {verdict}")
            return 1 if drift else 0
    except (ValueError, usage.UsageError, catalog_specimens.SpecimenRenderError) as exc:
        _error("parts", exc, getattr(args, "json", False))
        return 2
    table = parts.load()
    if args.json:
        data = {
            n: {
                "kind": p.kind,
                "style": p.style,
                "default": p.default,
                "refused": {"reason": p.refused.reason.value, "detail": p.refused.detail} if p.refused else None,
                "versions": [asdict(v) for v in p.versions],
            }
            for n, p in table.items()
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    if args.refused:
        for name, part in table.items():
            if part.refused:
                print(f"{name}: {part.refused.reason.value}: {part.refused.detail}")
        return 0
    width = max(len(n) for n in table)
    for name, part in table.items():
        numbers = ",".join(f"{v.number}{'' if v.status == 'approved' else '?'}" for v in part.versions)
        print(f"{name:<{width}} {part.kind:<9} {part.style:<7} {part.default or '-':<3} {numbers}")
    return 0


def _enhance(action: str, repo: Path) -> int:
    if action == "kinds":
        for kind, what in auto_enhance.KINDS.items():
            print(f"{kind:<10} {what}")
        return 0
    try:
        if action == "check":
            rows = auto_enhance.unsound(repo)
        else:
            if action != "status":
                auto_enhance.set_mode(repo, on=action == "on")
            print(f"auto-enhance: {'on' if auto_enhance.enabled(repo) else 'off'}")
            rows = auto_enhance.ledger(repo) if action == "status" else []
    except auto_enhance.EnhanceError as exc:
        _error("enhance", exc)
        return 2
    for row in rows:
        verdict = "; ".join(row.problems) or "counts"
        print(f"{row.commit[:7]} {','.join(row.slugs)} [{','.join(row.kinds)}] {row.subject}: {verdict}")
    return 1 if action == "check" and rows else 0


def _cards(args) -> int:
    from . import cast_card  # the card table imports every style: only this command pays for that

    if args.fonts is None or args.engine is None:
        print("srstudio cards: set --fonts and --engine, or SRSTUDIO_FONTS and SRSTUDIO_ENGINE", file=sys.stderr)
        return 2
    try:
        written = cast_card.render_all(
            args.out, cast_card.Lettering.installed(args.fonts), args.engine, frozenset(args.only)
        )
    except SrstudioError as exc:
        _error("cards", exc, getattr(args, "json", False))
        return 1
    for path in written:
        print(path)
    return 0


def _scripts_default() -> Path:
    return Path(os.environ.get("SRSTUDIO_SCRIPTS") or "episodes")


def _episode_script(scripts: Path, slug: str, suffix: str) -> Path | None:
    """The script ``<builder><suffix>.py`` of the episode ``slug`` in ``scripts`` (the builder named by its release
    when it has one), or None when ``scripts`` holds no episode by that name;
    :class:`~srstudio.releases.ReleaseError` when the episode is there but this script is not."""
    if not releases.SLUG.fullmatch(slug):
        return None
    stem = slug.replace("-", "_")
    known = (scripts / "posts" / "__init__.py").is_file() and (scripts / "posts" / f"{stem}.py").is_file()
    if known:
        stem = releases.load(scripts / "posts")[slug].builder_name
    script = scripts / f"{stem}{suffix}.py"
    if script.is_file():
        return script
    if known or (suffix and (scripts / f"{stem}.py").is_file()):
        raise releases.ReleaseError(f"episode {slug!r} has no {script.name} in {scripts}")
    return None


def _ledger_default() -> Path:
    return show_numbers.ledger_path(Path(os.environ.get("SRSTUDIO_RENDERS") or "generated/renders"))


def _claimed(slug: str, claim: show_numbers.Claim) -> str:
    series = f" {claim.series} #{claim.series_number}" if claim.series else ""
    return f"{slug} #{claim.number}{series}" + "".join(
        f" {tag}" for tag in (claim.brief, claim.post_by, claim.not_before) if tag
    )


def _number(args: argparse.Namespace) -> int:
    try:
        if args.action == "base":
            if not (args.value or "").isdecimal():
                raise show_numbers.NumberError(f"base takes a count, got {args.value!r}")
            show_numbers.set_base(args.ledger, int(args.value), args.series)
        elif args.action == "claim":
            if not args.value:
                raise show_numbers.NumberError("claim takes the reel's slug")
            held = show_numbers.claim(args.ledger, args.value, args.series, args.brief, args.post_by, args.not_before)
            print(_claimed(args.value, held))
            return 0
        elif args.action == "release":
            if not args.value:
                raise show_numbers.NumberError("release takes the reel's slug")
            root = args.ledger.resolve().parent.parent  # the ledger sits under the folder the renders and outbox are in
            shown = outbox.delivered_names(root / "renders" / "ig", root / "outbox")
            print(f"released {_claimed(args.value, show_numbers.release_claim(args.ledger, args.value, shown))}")
            return 0
        ledger = show_numbers.read(args.ledger)
    except SrstudioError as exc:
        _error("number", exc, getattr(args, "json", False))
        return 2
    print(f"base {'not set' if ledger.base is None else ledger.base}")
    for series, base in sorted(ledger.series.items()):
        print(f"{series} base {base}")
    for slug, claim in sorted(ledger.reels.items(), key=lambda kv: kv[1].number):
        print(_claimed(slug, claim))
    return 0


def _show_number(scripts: Path, slug: str) -> int | None:
    """The number the release of the episode ``slug`` carries on the show's cover, or None for any other cover."""
    stem = slug.replace("-", "_")
    if not (scripts / "posts" / "__init__.py").is_file() or not (scripts / "posts" / f"{stem}.py").is_file():
        return None
    cover = releases.load(scripts / "posts")[slug].post.thumbnail
    return cover.number if isinstance(cover, ShowCover) else None


def _delivery_default() -> Path:
    return Path(os.environ.get("SRSTUDIO_RENDERS") or "generated/renders") / "ig"


def _strict(args: argparse.Namespace) -> int:
    try:
        if not (args.delivery / MANIFEST).is_file():
            raise DeliveryError(f"no delivery manifest in {args.delivery}")
        known = releases.load(args.scripts / "posts")
        lines = strict_gate.listing(
            strict_gate.read_all(args.scripts / "strict", known), known, read_manifest(args.delivery)
        )
    except (DeliveryError, releases.ReleaseError) as exc:
        print(f"srstudio strict: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


def _run_script(script: Path, argv: list[str]) -> int:
    """Run ``script`` as ``__main__`` with ``argv`` and its folder first on the path; its exit status (1 for a
    reason, which goes to stderr)."""
    sys.argv = argv
    sys.path.insert(0, str(script.resolve().parent))
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as stop:
        if stop.code is None or isinstance(stop.code, int):
            return stop.code or 0
        print(stop.code, file=sys.stderr)  # a reason, as Python prints it for an exit it does not catch
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
