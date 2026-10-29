#!/usr/bin/env python3
"""Out of Office — the recording: every line of the sketch said by its ElevenLabs voice, heard back, placed at the
speakers' own pace, with the keyboard and the sting synthesised; see _toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 out_of_office_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from _toon_sketch import recorder
from out_of_office_data import MOUTH, NOTE, SEED, SKETCH, validate

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate)


if __name__ == "__main__":
    sys.exit(main())
