#!/usr/bin/env python3
"""Logo Bigger — the recording: every line of the sketch said by its ElevenLabs voice, heard back, placed at the
speakers' own pace, with the keyboard, the phone and the sting synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 logo_bigger_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from logo_bigger_data import NOTE, SEED, SKETCH, validate
from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, validate=validate)


if __name__ == "__main__":
    sys.exit(main())
