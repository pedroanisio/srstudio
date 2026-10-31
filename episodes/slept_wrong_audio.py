#!/usr/bin/env python3
"""Slept wrong: the recording, every line said by its ElevenLabs premade voice and heard back by speech-to-text.

    SRSTUDIO_ALLOW_CLOUD=1 python3 slept_wrong_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from slept_wrong_data import MOUTH, NOTE, SEED, SKETCH, sounds, validate
from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, sounds=sounds)


if __name__ == "__main__":
    sys.exit(main())
