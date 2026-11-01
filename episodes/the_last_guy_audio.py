#!/usr/bin/env python3
"""The Last Guy: the recording, every line said by its ElevenLabs premade voice and heard back by speech-to-text.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_last_guy_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from srstudio.toon_sketch import recorder
from the_last_guy_data import MOUTH, NOTE, SEED, SKETCH, sounds, validate

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, sounds=sounds)


if __name__ == "__main__":
    sys.exit(main())
