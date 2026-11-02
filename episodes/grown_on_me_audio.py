#!/usr/bin/env python3
"""It's Grown On Me — the recording: every line said by its ElevenLabs voice, heard back, placed at the speakers' own
pace, with the foley synthesized; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 grown_on_me_audio.py PROJECT [--variant] [--ffmpeg PATH] [--place-only]

--variant records the ending without the last "Fine.".

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from grown_on_me_data import MOUTH, NOTE, SEED, SKETCH, VARIANT, sounds, validate
from srstudio.toon_sketch import recorder


def main(argv: list[str]) -> int:
    variant = "--variant" in argv
    sk = VARIANT if variant else SKETCH
    run = recorder(sk, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, sounds=sounds)
    return run([a for a in argv if a != "--variant"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
