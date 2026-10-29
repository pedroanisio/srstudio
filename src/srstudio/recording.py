"""The command line every episode's recording script shares: ``python3 <episode>_audio.py PROJECT [--ffmpeg PATH]``.

A recording script names what it records (a sketch, its staging, its voices) and hands :func:`main` the function
that records it; :func:`main` parses the arguments, resolves the project and passes the environment through, so
the key and ``SRSTUDIO_ALLOW_CLOUD`` are read where the recording checks them, never here; a recording refused
for want of consent (:class:`~srstudio.errors.ConsentError`) is the script's exit, with the reason. A script
with flags of its own (``--font``, ``--key-stdin``) adds them with ``options`` and receives their values as
keywords.
"""

from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .errors import ConsentError

__all__ = ["Options", "Record", "main"]

Record = Callable[..., object]  # (project, environment, ffmpeg, **options) -> anything
Options = Callable[[argparse.ArgumentParser], object]
SHARED = ("project", "ffmpeg")


def main(
    record: Record,
    doc: str | None,
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    options: Options | None = None,
) -> int:
    """Parse ``PROJECT [--ffmpeg PATH]`` from ``argv`` and run ``record`` with the resolved project, ``env`` (the
    process environment when None) and the ffmpeg to use; the help shows the first line of ``doc``. ``options``
    adds the script's own flags to the parser, and their values reach ``record`` as keywords."""
    parser = argparse.ArgumentParser(description=(doc or "").splitlines()[0] if doc else None)
    parser.add_argument("project", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    if options is not None:
        options(parser)
        dests = [action.dest for action in parser._actions]
        for name in SHARED:
            if dests.count(name) > 1:
                raise ValueError(f"an option of the script shadows the shared argument {name!r}")
    args = vars(parser.parse_args(argv))
    project, ffmpeg = args.pop("project"), args.pop("ffmpeg")
    try:
        record(project.resolve(), os.environ if env is None else env, ffmpeg, **args)
    except ConsentError as exc:
        raise SystemExit(str(exc)) from None
    return 0
