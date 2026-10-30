#!/usr/bin/env python3
"""Who Touched It — the recording: every line of the sketch said by its ElevenLabs voice, heard back, placed at the
speakers' own pace, with the click and the floorboard synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 who_touched_it_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from srstudio.toon_sketch import recorder
from who_touched_it_data import MOUTH, NOTE, SEED, SKETCH, foley, validate

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, foley_of=foley)


if __name__ == "__main__":
    sys.exit(main())
