#!/usr/bin/env python3
"""The quick gate before the full one (ADR 0141): format, lint, types, enhancement claims, and the tests a change can
plainly break.

    python3 tools/pregate.py [--base develop]

Runs the tests named for each changed module, every changed test, and the fast contract tests a merge most often
breaks. It stands in front of ``tools/gate.sh`` and never replaces it: passing here says nothing about the full suite.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Collection, Iterable, Sequence
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
ALWAYS = (
    "tests/test_agent_approved_recovery.py",
    "tests/test_catalog_app.py",
    "tests/test_catalog_coverage.py",
    "tests/test_character_contracts.py",
    "tests/test_skill.py",
)
PUBLISHING = "tests/test_social.py"  # what a change under episodes/ reaches first

Run = Callable[..., "subprocess.CompletedProcess[str]"]


def select(changed: Iterable[str], tests: Collection[str]) -> list[str]:
    """The tests to run for ``changed`` paths, each of them one of the existing ``tests``, in order."""
    chosen = set(ALWAYS) & set(tests)
    for name in changed:
        path = PurePosixPath(name)
        if path.suffix != ".py":
            continue
        own = f"tests/{path.name}" if path.parts[0] == "tests" else f"tests/test_{path.stem}.py"
        if own in tests:
            chosen.add(own)
        if path.parts[0] == "episodes" and PUBLISHING in tests:
            chosen.add(PUBLISHING)
    return sorted(chosen)


def changed_paths(base: str, run: Run) -> list[str]:
    """Every path that differs from where HEAD left ``base``, committed or not, and every new file."""
    common = run(["git", "merge-base", base, "HEAD"], capture_output=True, text=True, cwd=REPO, check=True).stdout
    argv = [["git", "diff", "--name-only", common.strip()], ["git", "ls-files", "-o", "--exclude-standard"]]
    lines = [run(a, capture_output=True, text=True, cwd=REPO, check=True).stdout.splitlines() for a in argv]
    return sorted({*lines[0], *lines[1]})


def plan(tests: Sequence[str], bin_dir: Path) -> list[tuple[str, list[str]]]:
    """Each step's name and its command; the tools come from the interpreter's own folder."""
    return [
        ("format", [str(bin_dir / "ruff"), "format", "--check", "src", "tests", "episodes", "tools"]),
        ("lint", [str(bin_dir / "ruff"), "check", "src", "tests", "episodes", "tools"]),
        ("mypy", [str(bin_dir / "mypy"), "src"]),
        ("enhance", [str(bin_dir / "python"), "-m", "srstudio.cli", "enhance", "check", "--scripts", "episodes"]),
        ("tests", [str(bin_dir / "python"), "-m", "pytest", "--no-cov", "-q", *tests]),
    ]


def main(argv: Sequence[str] | None = None, run: Run = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="develop")
    options = parser.parse_args(argv)
    existing = {f"tests/{p.name}" for p in (REPO / "tests").glob("test_*.py")}
    tests = select(changed_paths(options.base, run), existing)
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}  # the shared venv otherwise loads the main checkout
    failed = []
    for name, command in plan(tests, Path(sys.executable).parent):
        done = run(command, capture_output=True, text=True, cwd=REPO, env=env)
        last = (done.stdout + done.stderr).strip().splitlines()
        print(f"{name}: {last[-1] if last else 'no output'}")
        if done.returncode != 0:
            failed.append(name)
    print(f"pregate: {'failed: ' + ', '.join(failed) if failed else 'ok'} ({len(tests)} test files)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
