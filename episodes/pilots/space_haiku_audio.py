#!/usr/bin/env python3
"""The recording of space_haiku: every line said by its ElevenLabs voice, heard back, placed at the speakers' own
pace, with the sting and effects synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 space_haiku_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from space_haiku_data import MOUTH, NOTE, SEED, SKETCH, foley, validate

from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, foley_of=foley)


if __name__ == "__main__":
    sys.exit(main())
