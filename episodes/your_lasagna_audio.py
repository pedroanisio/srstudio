#!/usr/bin/env python3
"""Your Lasagna — the recording: every line said by its ElevenLabs premade voice, heard back by speech-to-text,
placed at the speakers' own pace, the effects synthesized; see collage_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 your_lasagna_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from srstudio.collage_sketch import MOUTH, recorder
from your_lasagna_data import NOTE, STAGING

main = recorder(STAGING, NOTE, __doc__, mouth=MOUTH)


if __name__ == "__main__":
    sys.exit(main())
