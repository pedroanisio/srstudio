#!/usr/bin/env python3
"""The scale: the recording, every line said by its ElevenLabs premade voice and heard back by speech-to-text.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_scale_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from srstudio.collage_sketch import MOUTH, recorder
from the_scale_data import NOTE, STAGING

main = recorder(STAGING, NOTE, __doc__, mouth=MOUTH)


if __name__ == "__main__":
    sys.exit(main())
