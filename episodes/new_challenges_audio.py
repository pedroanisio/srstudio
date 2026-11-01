#!/usr/bin/env python3
"""New Challenges — the sketch as data — the recording: every line said by its ElevenLabs voice, heard back, placed at
the speakers' own pace,
with the foley synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 new_challenges_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from new_challenges_data import MOUTH, NOTE, SEED, SKETCH, sounds, validate
from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, sounds=sounds)


if __name__ == "__main__":
    sys.exit(main())
