#!/usr/bin/env python3
"""Like Family — the recording: every line of the sketch said by its ElevenLabs voice, heard back, placed at the
speakers' own pace, with the keyboard and the sting synthesised; see _toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 like_family_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

from _toon_sketch import record_episode
from like_family_data import MOUTH, NOTE, SEED, SKETCH, validate


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args(argv)
    validate(SKETCH)
    environ = os.environ if env is None else env
    record_episode(SKETCH, args.project.resolve(), environ, args.ffmpeg, SEED, NOTE, mouth=MOUTH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
