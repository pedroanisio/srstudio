#!/usr/bin/env python3
"""Your Rent — the recording: every line said by its ElevenLabs voice, heard back, placed at the speakers' own pace,
with the room synthesized; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 your_rent_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from srstudio.toon_sketch import recorder
from your_rent_data import MOUTH, NOTE, SEED, SKETCH, sounds, validate

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, sounds=sounds)


if __name__ == "__main__":
    sys.exit(main())
