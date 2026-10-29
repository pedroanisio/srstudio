#!/usr/bin/env python3
"""Final Broadcast — the recording: every line said by its ElevenLabs premade voice, heard back by speech-to-text,
placed
at the speakers' own pace, the effects synthesised; see _collage_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 final_broadcast_audio.py PROJECT [--ffmpeg PATH]

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

from _collage_sketch import MOUTH, record_episode
from final_broadcast_data import NOTE, STAGING


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args(argv)
    environ = os.environ if env is None else env
    record_episode(STAGING, args.project.resolve(), environ, args.ffmpeg, NOTE, mouth=MOUTH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
