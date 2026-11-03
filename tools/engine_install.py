#!/usr/bin/env python3
"""Install a scene-render engine from its published image, and optionally make it the one in use (ADR 0224).

    python3 tools/engine_install.py 0.9.0 [--activate] [--image pedroanisio/scene-render] [--bin-dir DIR]

Pulls ``IMAGE:VERSION``, copies the engine and its commit out of a stopped container, and installs them at
``BIN_DIR/scene-render-vVERSION`` only after the binary reports VERSION, its commit is the commit of the tag vVERSION in
the image's source repository, and it renders a smoke scene on this machine. ``engine.json`` beside it records the
image digest. An installed version is never replaced by another image. ``--activate`` points ``BIN_DIR/scene-render``,
the engine every srstudio tool, gate and unit runs, at the installed version in one rename; the previous version stays
for a switch back. The engine then runs on the host, with no container per call.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

DEFAULT_IMAGE = "pedroanisio/scene-render"
LINK = "scene-render"
BINARY = "/usr/local/bin/scene-render"
COMMIT_FILE = "/usr/share/doc/scene-render/COMMIT"
SMOKE = (
    '<scene version="1.2"><project width="64" height="36" fps="10" duration="0.2" background="#000000"/>'
    '<composition><shape id="box" shape="rect" width="16" height="16" fill="#FFFFFF"/></composition></scene>\n'
)
INSPECT = (
    '{"digest": {{json (index .RepoDigests 0)}},'
    ' "source": {{json (index .Config.Labels "org.opencontainers.image.source")}}}'
)

Run = Callable[..., "subprocess.CompletedProcess[str]"]


class EngineInstallError(Exception):
    """A step failed or a check refused the engine; nothing was installed or switched."""


def _call(run: Run, argv: Sequence[str | os.PathLike[str]], what: str) -> str:
    try:
        done = run([str(a) for a in argv], capture_output=True, text=True, check=False)
    except OSError as e:
        raise EngineInstallError(f"{what}: {e}") from None
    if done.returncode != 0:
        raise EngineInstallError(f"{what} failed (exit {done.returncode}): {(done.stderr or done.stdout)[-400:]}")
    return done.stdout


def _image(run: Run, ref: str) -> tuple[str, str]:
    """The pulled image's digest and the repository it says it was built from."""
    _call(run, ["docker", "pull", "-q", ref], f"docker pull {ref}")
    text = _call(run, ["docker", "image", "inspect", "--format", INSPECT, ref], f"docker image inspect {ref}")
    try:
        found = json.loads(text)
        digest, source = found["digest"], found["source"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise EngineInstallError(f"{ref} has no digest or source label: {text[-200:]!r}") from None
    if not isinstance(digest, str) or "@sha256:" not in digest or not isinstance(source, str) or not source:
        raise EngineInstallError(f"{ref} has no digest or source label: {text[-200:]!r}")
    return digest, source


def _tag_commit(run: Run, source: str, version: str) -> str:
    """The commit the tag vVERSION names in ``source``, peeled when the tag is annotated."""
    tag = f"refs/tags/v{version}"
    lines = _call(run, ["git", "ls-remote", source, tag, tag + "^{}"], f"git ls-remote {source}").splitlines()
    refs: dict[str, str] = {}
    for line in lines:
        sha, _, name = line.partition("\t")
        refs[name.strip()] = sha.strip()
    commit = refs.get(tag + "^{}") or refs.get(tag)
    if not commit:
        raise EngineInstallError(f"{source} has no tag v{version}")
    return commit


def _extract(run: Run, ref: str, stage: Path) -> None:
    container = _call(run, ["docker", "create", ref], f"docker create {ref}").strip()
    try:
        _call(run, ["docker", "cp", f"{container}:{BINARY}", stage / "scene-render"], "docker cp of the engine")
        _call(run, ["docker", "cp", f"{container}:{COMMIT_FILE}", stage / "COMMIT"], "docker cp of its commit")
    finally:
        run(["docker", "rm", "-f", container], capture_output=True, text=True, check=False)


def _check(run: Run, stage: Path, version: str, tag_commit: str) -> str:
    engine = stage / "scene-render"
    said = _call(run, [engine, "--version"], "the engine's --version").strip()
    if said != f"scene-render {version}":
        raise EngineInstallError(f"the image's engine reports {said}, not scene-render {version}")
    commit = (stage / "COMMIT").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise EngineInstallError(f"the image's commit file holds {commit[:60]!r}, not a commit")
    if commit != tag_commit:
        raise EngineInstallError(f"the image was built from {commit}, but tag v{version} is {tag_commit}")
    scene, png = stage / "smoke.scene.xml", stage / "smoke.png"
    scene.write_text(SMOKE)
    try:
        _call(run, [engine, "render", scene, "-o", png, "--strict"], "the smoke render")
    except EngineInstallError as e:
        raise EngineInstallError(f"the smoke render failed on this machine: {e}") from None
    if not png.is_file():
        raise EngineInstallError("the smoke render failed on this machine: it wrote no frame")
    scene.unlink()
    png.unlink()
    return commit


def _activate(bin_dir: Path, installed: Path) -> None:
    tmp = bin_dir / f".{LINK}.{os.getpid()}"
    tmp.unlink(missing_ok=True)
    tmp.symlink_to(f"{installed.name}/scene-render")
    os.replace(tmp, bin_dir / LINK)


def install(
    version: str, *, bin_dir: Path, image: str = DEFAULT_IMAGE, activate: bool = False, run: Run = subprocess.run
) -> Path:
    """Install ``image:version`` under ``bin_dir`` and return its folder; with ``activate``, make it the engine in use.

    Raises :class:`EngineInstallError` when a step fails or a check refuses the engine, before anything is installed
    or switched."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise EngineInstallError(f"version {version!r} is not major.minor.patch")
    link = bin_dir / LINK
    if activate and link.exists() and not link.is_symlink():
        raise EngineInstallError(f"{link} is not a symbolic link; move it away before activating an engine")
    ref = f"{image}:{version}"
    digest, source = _image(run, ref)
    target = bin_dir / f"scene-render-v{version}"
    if target.exists():
        try:
            held = json.loads((target / "engine.json").read_text()).get("digest")
        except (OSError, json.JSONDecodeError, AttributeError):
            held = None
        if held != digest:
            raise EngineInstallError(f"{target} already holds another image ({held}); {ref} is {digest}")
    else:
        bin_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".engine-", dir=bin_dir))
        try:
            _extract(run, ref, stage)
            commit = _check(run, stage, version, _tag_commit(run, source, version))
            record = {"schema_version": "1.0.0", "version": version, "image": ref, "digest": digest}
            (stage / "engine.json").write_text(json.dumps({**record, "commit": commit, "source": source}, indent=1))
            (stage / "engine.json").chmod(0o600)
            (stage / "COMMIT").chmod(0o600)
            (stage / "scene-render").chmod(0o700)
            stage.chmod(0o700)
            stage.rename(target)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    if activate:
        _activate(bin_dir, target)
    return target


def _workspace_bin(run: Run) -> Path:
    """``generated/bin`` of the workspace that holds this repository, from a worktree as from the main checkout."""
    here = Path(__file__).resolve().parent
    common = _call(run, ["git", "-C", here, "rev-parse", "--path-format=absolute", "--git-common-dir"], "git")
    return Path(common.strip()).parent.parent / "generated" / "bin"


def main(argv: Sequence[str] | None = None, run: Run = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("version", help="the engine version, as 0.9.0")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help=f"the image repository (default {DEFAULT_IMAGE})")
    parser.add_argument("--bin-dir", type=Path, help="where engines live (default: the workspace's generated/bin)")
    parser.add_argument("--activate", action="store_true", help="make it the engine in use")
    args = parser.parse_args(argv)
    try:
        bin_dir = args.bin_dir or _workspace_bin(run)
        installed = install(args.version, bin_dir=bin_dir, image=args.image, activate=args.activate, run=run)
    except EngineInstallError as e:
        print(f"engine_install: {e}", file=sys.stderr)
        return 1
    record = json.loads((installed / "engine.json").read_text())
    state = "active" if args.activate else "installed, not active"
    print(f"scene-render {record['version']} at {installed} ({state}); commit {record['commit']}, {record['digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
