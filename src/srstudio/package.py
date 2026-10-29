"""Scene video packages for the original episodes: every published video ships its ``.vpkg.zip``.

The recreations arrived as packages; the episodes srstudio builds did not, so nobody else could rebuild them.
:func:`pack` turns an episode project (``<slug>/<slug>.scene.xml`` and the assets it names) into
``<slug>-<version>.vpkg.zip`` with the scene-render packaging tool (``scenerender-vpkg``, from ``sr-core``), then
proves the result: the package unpacks with every file matching its SHA-256, and the engine validates the unpacked
scene, so every file it references is inside. Packing is idempotent: while the scene is unchanged the existing
package is kept, and a changed scene gets the next patch version beside the earlier ones. A failure at any step is a
:class:`PackageError` and leaves no package behind.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from . import digest
from .layout import LayoutError, find_engine
from .outbox import latest_package
from .social import InstagramPost

__all__ = ["PackageError", "manifest", "pack", "scene_sha", "sha256"]

_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")  # vpkg.schema.json: package.id
_VERSION = re.compile(r"scene-render (\d+\.\d+\.\d+)")
_run: Callable[..., subprocess.CompletedProcess] = subprocess.run


class PackageError(ValueError):
    """A project that cannot be packed, a tool that fails, or a package that does not prove itself."""


sha256 = digest.sha256


def manifest(slug: str, post: InstagramPost, *, version: str, engine_version: str) -> dict:
    """The authoring ``vpkg.json`` of episode ``slug``: its primary scene and the step that renders it."""
    if not _ID.fullmatch(slug):
        raise PackageError(f"{slug!r} is not a package id (lower-case letters, digits, '.', '_' or '-')")
    scene = f"{slug}.scene.xml"
    summary = post.description.strip().split("\n\n")[0].strip()
    return {
        "$schema": "urn:scene-render:vpkg:1",
        "format": "scene-video-package",
        "formatVersion": "1.1",
        "package": {"id": slug, "version": version, "title": post.title.strip(), "languages": ["en"]}
        | ({"description": summary} if summary else {}),
        "scenes": [{"path": scene, "role": "primary", "generatedBy": "srstudio"}],
        "engines": [{"id": "rs", "version": engine_version, "tested": "full"}],
        "pipeline": {
            "steps": [
                {
                    "id": "render",
                    "kind": "render",
                    "render": {"scene": scene, "output": "main", "to": f"renders/{slug}.mp4"},
                }
            ],
            "deliverables": [{"path": f"renders/{slug}.mp4", "role": "master", "step": "render"}],
        },
    }


def scene_sha(path: Path) -> str:
    """The SHA-256 that package ``path`` records for its primary scene."""
    try:
        with zipfile.ZipFile(path) as z:
            data = json.loads(z.read("vpkg.json"))
    except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        raise PackageError(f"{path} is not a readable zip with a vpkg.json: {e}") from None
    try:
        primary = next(s["path"] for s in data["scenes"] if s.get("role") == "primary")
        return next(f["sha256"] for f in data["files"] if f.get("path") == primary)
    except (KeyError, TypeError, StopIteration):
        raise PackageError(f"{path}: vpkg.json lists no primary scene with its SHA-256") from None


def _tool(explicit: Path | str | None) -> Path:
    beside = Path(sys.executable).with_name("scenerender-vpkg")
    found = explicit or (beside if beside.is_file() else shutil.which("scenerender-vpkg"))
    if not found or not Path(found).is_file():
        raise PackageError(f"no scenerender-vpkg tool at {found or 'the PATH'} (install sr-core)")
    return Path(found)


def _step(run: Callable[..., subprocess.CompletedProcess], cmd: list, what: str) -> str:
    done = run([str(c) for c in cmd], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        lines = (done.stderr or done.stdout or "").strip().splitlines()
        raise PackageError(f"{what} ({done.returncode}): {lines[-1] if lines else 'no output'}")
    return done.stdout or ""


def _next(latest: Path | None, slug: str) -> str:
    if latest is None:
        return "1.0.0"
    major, minor, patch = (int(n) for n in latest.name[len(slug) + 1 : -len(".vpkg.zip")].split("."))
    return f"{major}.{minor}.{patch + 1}"


def pack(
    project: Path,
    out: Path,
    post: InstagramPost,
    *,
    tool: Path | str | None = None,
    engine: Path | str | None = None,
    run: Callable[..., subprocess.CompletedProcess] | None = None,
) -> Path:
    """The package of episode ``project`` in ``out``: the existing one while its scene is unchanged, else a new,
    proven ``<slug>-<next version>.vpkg.zip`` (mode 600 in a 700 folder)."""
    project, out = Path(project), Path(out)
    slug = project.name
    scene = project / f"{slug}.scene.xml"
    if not scene.is_file():
        raise PackageError(f"{project} has no scene {scene.name} to pack")
    vpkg = _tool(tool)
    try:
        renderer = find_engine(engine)
    except LayoutError as e:
        raise PackageError(f"no scene-render engine to validate the package: {e}") from None
    latest = latest_package(out, slug)
    if latest is not None and scene_sha(latest) == sha256(scene):
        return latest
    run = run or _run
    m = _VERSION.search(_step(run, [renderer, "--version"], "the engine did not report its version"))
    if not m:
        raise PackageError(f"{renderer} --version printed no scene-render version")
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    out.chmod(0o700)
    version = _next(latest, slug)
    work = Path(tempfile.mkdtemp(prefix=".pack-", dir=out))
    try:
        source = work / slug
        shutil.copytree(project, source, ignore=shutil.ignore_patterns("vpkg.json", "*.lock", "renders"))
        spec = manifest(slug, post, version=version, engine_version=m.group(1))
        (source / "vpkg.json").write_text(json.dumps(spec, indent=2) + "\n")
        _step(run, [vpkg, "pack", "-o", work, source], f"scenerender-vpkg pack failed for {slug}")
        built = work / f"{slug}-{version}.vpkg.zip"
        _step(run, [vpkg, "unpack", built, work / "unpacked"], f"verify failed: {built.name} does not unpack cleanly")
        unpacked = work / "unpacked" / "project" / scene.name
        _step(run, [renderer, "validate", unpacked], f"{built.name}: its unpacked scene is not valid")
        if scene_sha(built) != sha256(scene):
            raise PackageError(f"{built.name} does not hold the scene it was packed from")
        target = out / built.name
        built.replace(target)
        target.chmod(0o600)
        return target
    finally:
        shutil.rmtree(work, ignore_errors=True)
